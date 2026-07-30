"""the register sweep (the voicer's flagged non-seo capitals, same fix shape
as the seo pass): sentence-case chrome went lowercase across the delist
evidence headlines, the flags page intro/cards, the product-drill preview
lines, and the verification evidence empty state — the house rule (_page's
own docstring: "lowercase chrome throughout; UPPERCASE only for the one slap
a view may carry"). product names and proper nouns (Shopify) keep their caps."""

import pytest
from fastapi.testclient import TestClient

from commerceos.catalog import lifecycle as L
from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.spine.schema import ensure_schema
from commerceos.web.app import app, read_evidence


def test_delist_evidence_headlines_are_lowercase_chrome():
    headline, _ = read_evidence(["decor_keyword"])
    assert headline.startswith("looks like home decor")
    assert "Looks like" not in headline
    headline, _ = read_evidence(["demo_handle"])
    assert headline.startswith("looks like leftover demo")
    assert "Looks like" not in headline


def test_the_generic_flag_headline_is_lowercase():
    headline, _ = read_evidence(["some-unmapped-signal"])
    assert headline == "flagged for your review: matched 1 signal"


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    db = tmp_path / "register.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    conn = connect(db)
    ensure_schema(conn)
    ledger.ensure_schema(conn)
    yield conn, TestClient(app)
    conn.close()


def test_flags_empty_state_is_lowercase(rig):
    conn, client = rig
    page = client.get("/catalog/flags").text
    assert "nothing flagged right now" in page
    assert "Nothing flagged" not in page


def test_product_drill_empty_states_are_lowercase(rig):
    conn, client = rig
    conn.execute(
        "INSERT INTO products (shopify_id, handle, title, status, vendor, product_type,"
        " tags, source, fetched_at) VALUES (?,?,?,?,?,?,?,?,?)",
        ("gid://x/1", "h1", "A Product", "ACTIVE", "V", "Tents", "[]", "test", "t"))
    conn.commit()
    L.set_initial(conn, "gid://x/1", "ACTIVE")
    page = client.get("/catalog/products/gid://x/1").text
    assert "nothing recorded for this product yet" in page
    # L.set_initial already lays a sync row, so history is never empty here —
    # the "no history yet" empty state is pinned directly against the
    # renderer instead (below). likewise a fresh product carries real gaps
    # (no gtin/seo/etc filled), so the "no gaps" empty branch isn't reachable
    # here — its stale capitalized form is still checked absent, below.
    assert "no store preview yet" in page
    # Shopify is a product name — it keeps its capital even inside a
    # lowercase-chrome sentence.
    assert "stay in Shopify" in page
    # no sentence-case leftovers from the pre-sweep copy
    for stale in ("Nothing recorded", "No gaps",
                  "No store preview yet", "Any change here", "This product isn't"):
        assert stale not in page, stale


def test_history_empty_state_is_lowercase(rig):
    conn, client = rig
    # the product_lifecycle table is never created (no L.set_initial call) —
    # the drill's has_lc guard is False, so history renders its empty branch.
    conn.execute(
        "INSERT INTO products (shopify_id, handle, title, status, vendor, product_type,"
        " tags, source, fetched_at) VALUES (?,?,?,?,?,?,?,?,?)",
        ("gid://x/2", "h2", "B Product", "ACTIVE", "V", "Tents", "[]", "test", "t"))
    conn.commit()
    page = client.get("/catalog/products/gid://x/2").text
    assert "no history yet" in page
    assert "No history" not in page
