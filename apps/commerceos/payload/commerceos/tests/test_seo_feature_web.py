"""F4b: the listing-text front on the web surface, with the repair round's
rulings pinned — the /catalog row (B5 amber), the missing-or-weak board filter
+ no-stage banner (B4), the preview that reads both fields in plain words, the
one glance-approve that reads back live, the landed-run block (B3), the parked
draft's plain per-item card (B2), and the held-back list (M2).

rig: the content-agent seeded catalog on a scratch COMMERCEOS_DB + TestClient.
"""

import pytest
from fastapi.testclient import TestClient

from commerceos.catalog import canonical
from commerceos.db import connect
from commerceos.fleet import content
from commerceos.gate import gate, ledger
from commerceos.spine import writes
from commerceos.spine.schema import ensure_schema
from commerceos.web.app import app

from tests.test_seo_feature import FakeSeoClient, seed_catalog, P1


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    db = tmp_path / "seo-web.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    conn = connect(db)
    ensure_schema(conn)
    ledger.ensure_schema(conn)
    canonical.ensure_schema(conn)
    seed_catalog(conn)
    yield conn, TestClient(app)
    conn.close()


def _park_consequential(conn):
    """stage the spec-quoting draft (product 1) per item — F4a's lane — so it
    sits in decisions and colours the overview's call block."""
    for d in content.compute_listing_drafts(conn):
        if d["product"] == P1:
            gate.submit(conn, {
                "agent": content.AGENT, "function": content.FUNCTION,
                "method": "mutate_seo",
                "args": {"product_id": d["product_id"], "title": d["title"],
                         "description": d["description"]},
                "declared_type": d["declared_type"],
                "intent": f"draft the search listing for {d['product']} ({d['weak_reason']})",
                "rationale": "listing text drafted from catalog facts only (F4a)",
                "provenance": d["provenance"]})
    conn.commit()


def _arm(client) -> str:
    r = client.post("/catalog/run/seo", follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert loc.startswith("/catalog/runs/")
    return loc


def test_overview_carries_the_listing_front_in_plain_words(rig):
    conn, client = rig
    page = client.get("/catalog").text
    assert "listing text" in page
    assert "feature=seo" in page
    assert "209" in page
    # listing text no longer sits in the doorless mirror block (M4)
    assert "p202" in page and page.count("listing text") == 1


def test_the_queue_link_lands_on_the_missing_or_weak_board(rig):
    conn, client = rig
    page = client.get("/catalog/products?feature=seo").text
    assert "needs listing text" in page                     # the listing gap filter is active
    # B4: loaded products with no stage are named, not silently zero
    assert "not yet placed in a stage" in page


def test_the_preview_reads_both_fields_in_plain_words(rig):
    conn, client = rig
    loc = _arm(client)
    page = client.get(loc).text
    assert "a batch waiting for your glance" in page
    assert page.count("becomes") >= 2                        # title + description was -> becomes
    assert "listing text" in page
    assert "seo_title" not in page and "seo_description" not in page


def test_glance_approve_reads_back_live_and_identity_is_plain(rig, monkeypatch):
    conn, client = rig
    fake = FakeSeoClient()
    monkeypatch.setattr(writes, "ShopifyClient", lambda: fake)
    loc = _arm(client)
    r = client.post(f"{loc}/approve", follow_redirects=False)
    assert r.status_code == 303
    page = client.get(loc).text
    assert "the batch landed" in page
    assert "showed up live? yes" in page
    assert "you, at this desk" in page and "localhost" not in page
    # the your-call header reads past-tense once landed (polish)
    assert "the call you made" in page


def test_the_front_page_shows_the_landed_run(rig, monkeypatch):
    conn, client = rig
    fake = FakeSeoClient()
    monkeypatch.setattr(writes, "ShopifyClient", lambda: fake)
    loc = _arm(client)
    client.post(f"{loc}/approve", follow_redirects=False)
    page = client.get("/catalog/workflows/seo").text
    # B3: the last-batch block names the run that landed and links it, never
    # "nothing run yet"
    assert "the last batch landed" in page
    assert loc in page
    assert "no batch has run through this surface yet" not in page


def test_a_parked_listing_draft_reads_as_a_plain_card(rig):
    import re
    conn, client = rig
    _park_consequential(conn)
    page = client.get("/approvals").text
    # B2: the product by its REAL name (looked up on the full-gid key), the
    # was -> becomes change, and WHY it parks
    assert "Torch X" in page                          # the live name, not "the product"
    assert "becomes" in page and "waits until" in page
    assert "quotes a checked detail" in page and "beam output: 900 lm" in page
    # the drill link carries the gid in its href (the route takes it), but the
    # gid, the raw dump, the codes and the tense lie never reach VISIBLE text.
    visible = re.sub(r"<[^>]+>", " ", page)
    for bad in ["gid://", '"product_id"', "no-seo-title", "content geo",
                "(F4a)", "listing text written", "localhost"]:
        assert bad not in visible, f"decisions leaked {bad!r}"
    # and the drill link points at the real product (the full-gid path)
    assert f"/catalog/products/{P1}" in page


def test_the_overview_call_block_goes_amber_over_a_waiting_draft(rig):
    conn, client = rig
    _park_consequential(conn)
    page = client.get("/catalog").text
    # B5: a real per-item wait colours the single call block, links decisions
    assert "listing draft" in page and "waits on you, item by item" in page
    assert "nothing needs your call" not in page


def test_held_back_opens_to_a_named_list(rig):
    conn, client = rig
    page = client.get("/catalog/workflows/seo").text
    # M2: held back opens to a real list — each product by name, one plain reason
    assert "held back" in page and "id='held-back'" in page
    assert "Ultimate Lantern" in page and "Gizmo" in page
    assert "too thin" in page and "sales word" in page


def test_pre_park_meter_line_names_the_unproposed_draft(rig):
    conn, client = rig
    # pre-park: the writer hasn't proposed yet, so the meter line names the gap
    front = client.get("/catalog/workflows/seo").text
    assert "writes item by item when the writer next runs" in front
    # once the consequential draft is parked per item, the phrase clears — the
    # live per-item wait covers it (the walk2 parked state is unchanged)
    _park_consequential(conn)
    front2 = client.get("/catalog/workflows/seo").text
    assert "writes item by item when the writer next runs" not in front2
    assert "waiting on you, item by item" in front2


def test_still_to_do_count_equals_the_products_its_link_renders(rig):
    conn, client = rig
    import re
    front = client.get("/catalog/workflows/seo").text
    m = re.search(r"still to do.*?feature=seo'>([\d,]+)</a>", front, re.S)
    assert m, "still-to-do count not found on the front page"
    n = int(m.group(1).replace(",", ""))
    board = client.get("/catalog/products?feature=seo").text
    shown = set(re.findall(r"/catalog/products/(gid://shopify/Product/\d+)", board))
    assert n == len(shown), f"still-to-do says {n} but its link renders {len(shown)}"
    assert n == 6                                    # the missing-or-weak set (P3 is strong)
    # the overview row opens to the same door with the same count
    over = client.get("/catalog").text
    mo = re.search(r"feature=seo'>([\d,]+)</a>\s*products? needs? this", over)
    assert mo and int(mo.group(1).replace(",", "")) == n


def test_the_listing_surfaces_speak_plain_words(rig):
    conn, client = rig
    _park_consequential(conn)
    import re
    loc = _arm(client)
    snake = re.compile(r"[a-z]{2,}_[a-z_]{2,}")
    banned = ["seo_title", "seo_description", "weak_reason", "declared_type",
              "writeback:", "content-geo", "content geo", "mutate_seo"]
    for path in ["/catalog", "/catalog/workflows/seo", "/approvals", loc]:
        text = client.get(path).text
        for term in banned:
            assert term not in text, f"{path}: insider term {term!r} reached the screen"
