"""A3's checks: the Shopify read paths land facts idempotently, split
settlement at landing, convert money exactly, and record sync_state.
plus A8's: the widened product pull lands metafields, media, seo,
collections, and description length — queryably and in raw — so the
audit scores all 7 dimensions; THROTTLED pages retry bounded.
fixture-driven — green without credentials; the live checks skip cleanly
when the Keychain has no entry, and when it does they prove local count
equals the store's own productsCount."""

import json
from pathlib import Path

import pytest

from commerceos.catalog import audit as audit_mod
from commerceos.catalog import lifecycle as L
from commerceos.db import connect
from commerceos.spine.connector_shopify import (
    THROTTLE_BASE_SLEEP,
    THROTTLE_RETRIES,
    rate_for,
    sync_orders,
    sync_products,
    to_minor,
)
from commerceos.spine.schema import ensure_schema
from commerceos.spine.shopify_client import (
    ShopifyClient,
    ShopifyError,
    credentials_available,
    load_config,
)

FIXTURES = Path(__file__).parent / "fixtures"
RATES = {"default_bps": 3250, "vendors": {"CampCo": 3000}}


def _fixture(name):
    with open(FIXTURES / name) as f:
        return json.load(f)["data"]


class FakeClient:
    """serves fixture pages keyed by the cursor variable; records calls."""

    def __init__(self, pages_by_cursor):
        self.pages = pages_by_cursor
        self.calls = []

    def graphql(self, query, variables=None):
        self.calls.append((query, variables))
        return self.pages[(variables or {}).get("cursor")]


class ExplodingClient:
    def graphql(self, query, variables=None):
        raise ShopifyError("boom: simulated transport failure")


def products_client():
    return FakeClient(
        {
            None: _fixture("shopify_products_page1.json"),
            "cursor-page-1": _fixture("shopify_products_page2.json"),
        }
    )


def orders_client():
    return FakeClient({None: _fixture("shopify_orders_page.json")})


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "test.db")
    ensure_schema(c)
    yield c
    c.close()


def _count(conn, table):
    return conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]


# ---------- paging + upsert idempotence ----------


def test_products_sync_pages_and_lands_all_rows(conn):
    client = products_client()
    counts = sync_products(conn, client=client)
    assert counts == {"products": 3, "variants": 4, "metafields": 7}
    assert len(client.calls) == 2  # page 1 (cursor None) then page 2
    assert client.calls[1][1] == {"cursor": "cursor-page-1"}


def test_two_syncs_of_the_same_fixture_land_the_same_row_count(conn):
    sync_products(conn, client=products_client())
    sync_products(conn, client=products_client())
    assert _count(conn, "products") == 3
    assert _count(conn, "variants") == 4


def test_a_rerun_updates_in_place_never_duplicates(conn):
    sync_products(conn, client=products_client())
    changed = products_client()
    changed.pages[None]["products"]["nodes"][0]["title"] = "Alpine Tent 2P (2026)"
    sync_products(conn, client=changed)
    row = conn.execute(
        "SELECT title FROM products WHERE shopify_id = 'gid://shopify/Product/1001'"
    ).fetchone()
    assert row["title"] == "Alpine Tent 2P (2026)"
    assert _count(conn, "products") == 3


def test_every_landed_row_carries_source_and_fetched_at(conn):
    sync_products(conn, client=products_client())
    sync_orders(conn, client=orders_client(), rates=RATES)
    for table in ("products", "variants", "orders"):
        rows = conn.execute(f"SELECT source, fetched_at FROM {table}").fetchall()
        assert rows
        for r in rows:
            assert r["source"] and r["fetched_at"]
    src = conn.execute(
        "SELECT source FROM products WHERE shopify_id = 'gid://shopify/Product/1001'"
    ).fetchone()["source"]
    assert src.startswith("shopify:product/1001@")  # the spec's source-ref shape


# ---------- CL1c: a sync auto-registers new products into the lifecycle ----------


def test_products_sync_places_every_product_in_the_lifecycle(conn):
    sync_products(conn, client=products_client())
    # fixture facts: page1 has 2 ACTIVE (1001, 1002), page2 has 1 DRAFT (1003)
    assert L.state_of(conn, "gid://shopify/Product/1001") == "active"
    assert L.state_of(conn, "gid://shopify/Product/1002") == "active"
    assert L.state_of(conn, "gid://shopify/Product/1003") == "draft"
    for pid in (
        "gid://shopify/Product/1001",
        "gid://shopify/Product/1002",
        "gid://shopify/Product/1003",
    ):
        rows = L.history(conn, pid)
        assert len(rows) == 1
        assert rows[0]["from_state"] is None
        assert rows[0]["by"] == "sync"


def test_a_resync_never_duplicates_placement(conn):
    sync_products(conn, client=products_client())
    sync_products(conn, client=products_client())  # fresh client — cursor is consumed
    for pid in (
        "gid://shopify/Product/1001",
        "gid://shopify/Product/1002",
        "gid://shopify/Product/1003",
    ):
        assert len(L.history(conn, pid)) == 1
    assert L.state_of(conn, "gid://shopify/Product/1001") == "active"
    assert L.state_of(conn, "gid://shopify/Product/1003") == "draft"


def test_a_resync_never_stomps_a_recorded_move(conn):
    sync_products(conn, client=products_client())
    pid = "gid://shopify/Product/1001"
    L.delist(conn, pid, reason="operator pulled it", by="operator")
    assert L.state_of(conn, pid) == "delisted"

    sync_products(conn, client=products_client())  # a re-sync still says ACTIVE

    assert L.state_of(conn, pid) == "delisted"  # the operator's move stands
    rows = L.history(conn, pid)
    assert len(rows) == 2  # the sync placement + the delist — no third row
    assert rows[-1]["to_state"] == "delisted"
    assert rows[-1]["by"] == "operator"


def test_an_unknown_status_fails_the_sync_loudly(conn):
    bogus_page = {
        "products": {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {
                    "id": "gid://shopify/Product/9999",
                    "handle": "mystery-item",
                    "title": "Mystery Item",
                    "status": "PENDING",  # not a real Shopify product status
                    "vendor": "Nobody",
                    "productType": "Unknown",
                    "tags": [],
                    "descriptionHtml": "",
                    "seo": {"title": None, "description": None},
                    "mediaCount": {"count": 0},
                    "featuredMedia": None,
                    "collections": {"pageInfo": {"hasNextPage": False}, "nodes": []},
                    "metafields": {"pageInfo": {"hasNextPage": False}, "nodes": []},
                    "variants": {"pageInfo": {"hasNextPage": False}, "nodes": []},
                }
            ],
        }
    }
    client = FakeClient({None: bogus_page})
    with pytest.raises(L.LifecycleError):
        sync_products(conn, client=client)
    row = conn.execute(
        "SELECT status, error FROM sync_state WHERE connector = 'shopify:products'"
    ).fetchone()
    assert row["status"] == "error"
    assert row["error"]  # the LifecycleError text is recorded, never swallowed


# ---------- the A8 wide pull: metafields, media, seo, collections ----------


def test_wide_product_fields_land_queryably(conn):
    sync_products(conn, client=products_client())
    p = conn.execute(
        "SELECT * FROM products WHERE shopify_id = 'gid://shopify/Product/1001'"
    ).fetchone()
    assert p["seo_title"] == "Alpine Tent 2P — SummitWorks"
    assert p["seo_description"] == "A two-person, four-season alpine tent."
    assert json.loads(p["collections"]) == ["Tents & Shelters", "New Arrivals"]
    assert p["description_len"] == len("<p>Two-person alpine tent with aluminium poles.</p>")
    m = conn.execute(
        "SELECT * FROM product_media WHERE product_id = 'gid://shopify/Product/1001'"
    ).fetchone()
    assert m["media_count"] == 3
    assert m["first_image_url"] == "https://cdn.example.test/alpine-tent-2p.jpg"
    assert m["source"].startswith("shopify:product/1001@") and m["fetched_at"]
    meta = {
        (r["namespace"], r["key"]): (r["type"], r["value"])
        for r in conn.execute(
            "SELECT * FROM product_meta WHERE product_id = 'gid://shopify/Product/1001'"
        )
    }
    assert meta[("commerceos", "capacity_persons")] == ("number_integer", "2")
    assert ("commerceos", "capacity_persons_provenance") in meta
    assert ("global", "title_tag") in meta  # foreign namespaces land too — the audit decides
    rows = conn.execute("SELECT source, fetched_at FROM product_meta").fetchall()
    assert rows and all(r["source"] and r["fetched_at"] for r in rows)


def test_a_product_with_nothing_wide_lands_honest_empties(conn):
    # requested-and-empty is a landed fact (a real gap), never an absent key
    sync_products(conn, client=products_client())
    p = conn.execute(
        "SELECT * FROM products WHERE shopify_id = 'gid://shopify/Product/1002'"
    ).fetchone()
    assert p["seo_title"] is None and p["seo_description"] is None
    assert json.loads(p["collections"]) == []
    assert p["description_len"] == 0
    m = conn.execute(
        "SELECT * FROM product_media WHERE product_id = 'gid://shopify/Product/1002'"
    ).fetchone()
    assert m["media_count"] == 0 and m["first_image_url"] is None
    raw = json.loads(p["raw"])
    for key in ("metafields", "seo", "featuredMedia", "mediaCount", "collections"):
        assert key in raw  # the signal was requested — the audit may score it


def test_wide_resync_is_idempotent_and_drops_stale_meta(conn):
    sync_products(conn, client=products_client())
    sync_products(conn, client=products_client())
    assert _count(conn, "product_media") == 3
    assert _count(conn, "product_meta") == 7
    shrunk = products_client()
    node = shrunk.pages["cursor-page-1"]["products"]["nodes"][0]
    node["metafields"]["nodes"] = [
        n for n in node["metafields"]["nodes"] if n["key"] != "max_lumens"
    ]
    sync_products(conn, client=shrunk)
    left = {
        r["key"]
        for r in conn.execute(
            "SELECT key FROM product_meta WHERE product_id = 'gid://shopify/Product/1003'"
        )
    }
    assert left == {"max_lumens_provenance"}  # the deleted metafield is gone locally too


def test_a_truncated_nested_connection_is_refused(conn):
    overflowing = products_client()
    node = overflowing.pages[None]["products"]["nodes"][0]
    node["metafields"]["pageInfo"]["hasNextPage"] = True
    with pytest.raises(ShopifyError, match="metafields overflow"):
        sync_products(conn, client=overflowing)


# ---------- THROTTLED: pacing, not failure — bounded backoff ----------


THROTTLED_ERR = 'graphql errors: [{"message": "Throttled", "extensions": {"code": "THROTTLED"}}]'


class ThrottlingClient:
    """raises THROTTLED n times, then serves fixture pages; records calls."""

    def __init__(self, pages_by_cursor, throttles):
        self.pages = pages_by_cursor
        self.throttles = throttles
        self.calls = 0

    def graphql(self, query, variables=None):
        self.calls += 1
        if self.throttles > 0:
            self.throttles -= 1
            raise ShopifyError(THROTTLED_ERR)
        return self.pages[(variables or {}).get("cursor")]


@pytest.fixture()
def sleeps(monkeypatch):
    slept = []
    monkeypatch.setattr(
        "commerceos.spine.connector_shopify.time.sleep", lambda s: slept.append(s)
    )
    return slept


def test_throttled_pages_retry_with_backoff_then_land(conn, sleeps):
    client = ThrottlingClient(products_client().pages, throttles=2)
    counts = sync_products(conn, client=client)
    assert counts["products"] == 3
    assert sleeps == [THROTTLE_BASE_SLEEP, THROTTLE_BASE_SLEEP * 2]  # exponential
    assert client.calls == 4  # 2 throttled + 2 pages
    row = conn.execute(
        "SELECT status FROM sync_state WHERE connector = 'shopify:products'"
    ).fetchone()
    assert row["status"] == "ok"


def test_throttling_that_never_clears_is_bounded_and_lands_error(conn, sleeps):
    client = ThrottlingClient({}, throttles=10**9)
    with pytest.raises(ShopifyError, match="THROTTLED"):
        sync_products(conn, client=client)
    assert client.calls == THROTTLE_RETRIES + 1  # bounded, never a spin
    assert len(sleeps) == THROTTLE_RETRIES
    row = conn.execute(
        "SELECT status, error FROM sync_state WHERE connector = 'shopify:products'"
    ).fetchone()
    assert row["status"] == "error" and "THROTTLED" in row["error"]


def test_a_non_throttle_error_is_not_retried(conn, sleeps):
    with pytest.raises(ShopifyError, match="boom"):
        sync_products(conn, client=ExplodingClient())
    assert sleeps == []  # fail closed at once; backoff is for pacing only


# ---------- the point of A8: landed facts score all 7 audit dimensions ----------


AUDIT_TAXONOMY = {
    "version": 0,
    "status": "test",
    "categories": {
        "Tents & Shelters": {
            "subcategories": ["Tents"],
            "spec_schema": [{"key": "capacity_persons", "fc": True}],
        },
        "Camp Kitchen": {
            "subcategories": ["Cooking"],
            "spec_schema": [{"key": "fuel_type", "fc": False}],
        },
        "Lighting": {
            "subcategories": ["Headlamps", "Lighting"],
            "spec_schema": [{"key": "max_lumens", "fc": False}],
        },
    },
}

STORE_AUDIT_CONFIG = Path(__file__).resolve().parents[1] / "stores" / "demostore" / "audit-config.json"


def test_landed_wide_facts_make_all_seven_audit_dimensions_scorable(conn):
    sync_products(conn, client=products_client())
    state = audit_mod.audit(conn, AUDIT_TAXONOMY, json.loads(STORE_AUDIT_CONFIG.read_text()))
    assert state["scored_dimensions"] == 7 and state["configured_dimensions"] == 7
    d = state["dimensions"]
    assert all(v["scorable"] for v in d.values())
    # 1002's only metafield is global.title_tag — a foreign namespace, not a spec
    assert d["specs_structured"]["passed"] == 2
    # 1003's spec is flagged verified WITHOUT a source — the refuse-to-guess breach
    assert d["provenance"]["passed"] == 2
    assert state["facts"]["verified_without_source"] == 1
    assert d["seo"]["passed"] == 2     # 1002 landed seo null/null
    assert d["images"]["passed"] == 2  # 1002 landed featuredMedia null, count 0


# ---------- settlement split at landing ----------


def test_order_lines_split_at_landing_and_the_identity_holds(conn):
    sync_orders(conn, client=orders_client(), rates=RATES)
    lines = conn.execute("SELECT * FROM order_lines ORDER BY id").fetchall()
    assert len(lines) == 2
    for line in lines:
        assert line["take_minor"] + line["payable_minor"] == line["net_minor"]
    by_vendor = {ln["vendor"]: ln for ln in lines}
    default = by_vendor["SummitWorks"]  # no vendor row -> default rate
    assert default["rate_source"] == "default"
    assert default["take_rate_bps"] == 3250
    assert (default["net_minor"], default["take_minor"], default["payable_minor"]) == (
        60500,
        19663,
        40837,
    )
    vendor = by_vendor["CampCo"]  # named vendor row applies, and is recorded
    assert vendor["rate_source"] == "vendor:CampCo"
    assert vendor["take_rate_bps"] == 3000
    assert (vendor["net_minor"], vendor["take_minor"], vendor["payable_minor"]) == (
        16400,
        4920,
        11480,
    )


def test_order_totals_land_in_minor_units(conn):
    sync_orders(conn, client=orders_client(), rates=RATES)
    o = conn.execute("SELECT * FROM orders").fetchone()
    assert o["number"] == "#1001"
    assert o["currency"] == "AED"
    assert (o["gross_minor"], o["discount_minor"], o["net_minor"]) == (76900, 0, 76900)
    assert (o["shipping_minor"], o["tax_minor"]) == (2500, 3970)
    assert o["customer_ref"] == "gid://shopify/Customer/9001"  # reference only, no PII


def test_orders_resync_replaces_lines_never_duplicates(conn):
    sync_orders(conn, client=orders_client(), rates=RATES)
    sync_orders(conn, client=orders_client(), rates=RATES)
    assert _count(conn, "orders") == 1
    assert _count(conn, "order_lines") == 2


def test_an_empty_store_lands_zero_rows_and_status_ok(conn):
    empty = {"orders": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": []}}
    counts = sync_orders(conn, client=FakeClient({None: empty}), rates=RATES)
    assert counts == {"orders": 0, "lines": 0}
    row = conn.execute(
        "SELECT status FROM sync_state WHERE connector = 'shopify:orders'"
    ).fetchone()
    assert row["status"] == "ok"


def test_rate_for_reads_the_table():
    assert rate_for("CampCo", RATES) == (3000, "vendor:CampCo")
    assert rate_for("SummitWorks", RATES) == (3250, "default")
    assert rate_for(None, RATES) == (3250, "default")


# ---------- money conversion: Decimal, exact ----------


def test_money_to_minor_is_exact():
    assert to_minor("164.00") == 16400
    assert to_minor("605.00") == 60500
    assert to_minor("89.50") == 8950
    assert to_minor("0.05") == 5
    assert to_minor("0.00") == 0
    assert to_minor("1234.56") == 123456


def test_money_with_fractional_fils_is_refused():
    with pytest.raises(ValueError):
        to_minor("164.005")


# ---------- sync_state ----------


def test_sync_state_records_cursor_and_last_run(conn):
    sync_products(conn, client=products_client())
    row = conn.execute(
        "SELECT * FROM sync_state WHERE connector = 'shopify:products'"
    ).fetchone()
    assert row["status"] == "ok"
    assert row["cursor"] == "cursor-page-2"
    assert row["last_run"]
    assert row["error"] is None


def test_a_failed_sync_lands_status_error_never_half_silent(conn):
    with pytest.raises(ShopifyError):
        sync_orders(conn, client=ExplodingClient(), rates=RATES)
    row = conn.execute(
        "SELECT * FROM sync_state WHERE connector = 'shopify:orders'"
    ).fetchone()
    assert row["status"] == "error"
    assert "boom" in row["error"]
    assert row["last_run"]


# ---------- live checks: skip cleanly without credentials ----------


def _live_ready():
    try:
        return credentials_available(load_config())
    except Exception:
        return False


live = pytest.mark.skipif(
    not _live_ready(), reason="live check parked: no credentials in Keychain"
)


@live
def test_live_shop_responds():
    data = ShopifyClient().graphql("query { shop { name } }")
    assert data["shop"]["name"]


@live
def test_live_products_count_matches_the_store(tmp_path):
    c = connect(tmp_path / "live.db")
    ensure_schema(c)
    client = ShopifyClient()
    sync_products(c, client=client)
    store_count = client.graphql("query { productsCount { count } }")["productsCount"]["count"]
    local = c.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    assert local == store_count
    assert (
        c.execute(
            "SELECT COUNT(*) AS c FROM products WHERE source IS NULL OR fetched_at IS NULL"
        ).fetchone()["c"]
        == 0
    )
    c.close()
