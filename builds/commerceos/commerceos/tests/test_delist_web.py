"""CW8w: the web approve path's return leg — approving a parked delist must
flip the store AND record the product's lifecycle move in the same act.

before this pack: api_resolve routed every non-verification approved method
to the bare writes.execute door, so delist.execute_and_record (the seam
built exactly for this) was never called — the store flipped but the
product's history never gained a row. these pins prove the missing branch
closes the hole, on both callers (form + JSON), honestly on the unverified
leg, and seen on the product drill page.
"""

import pytest
from fastapi.testclient import TestClient

from commerceos.catalog import lifecycle as L
from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.spine import writes
from commerceos.spine.schema import ensure_schema
from commerceos.web.app import app

from tests.test_catalog_delist import FakeClient, _add_product, _submit_delist


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    db = tmp_path / "web.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    conn = connect(db)
    ensure_schema(conn)
    ledger.ensure_schema(conn)
    yield conn, TestClient(app)
    conn.close()


def _seed_active_product(conn, pid="gid://x/1"):
    _add_product(conn, pid, "storm-shelter-tent", "Storm Shelter Tent", "Vango", "Tents")
    conn.commit()
    L.set_initial(conn, pid, "ACTIVE")
    return pid


def test_web_approve_of_a_parked_delist_flips_store_and_records_the_move(rig, monkeypatch):
    conn, client = rig
    pid = _seed_active_product(conn)
    store = FakeClient(status="ACTIVE")
    monkeypatch.setattr(writes, "ShopifyClient", lambda: store)

    res = _submit_delist(conn, pid)
    rid = res["record_id"]

    r = client.post(f"/api/approvals/{rid}",
                     data={"decision": "approved", "confirm": "true"},
                     follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/approvals?flash=")
    assert "landed" in r.headers["location"]

    # the store flipped and verify-rendered.
    assert store.status == "DRAFT"
    # lifecycle recorded the move — the seam that was never called before.
    assert L.state_of(conn, pid) == "delisted"
    rows = L.history(conn, pid)
    assert len(rows) == 2                       # sync + delist
    tail = rows[-1]
    assert tail["ledger_id"] == rid
    assert tail["by"] == "catalog-delist"       # the record's agent, not the approver
    assert ledger.get(conn, rid)["status"] == "executed"


def test_json_approve_answers_with_a_truthful_outcome(rig, monkeypatch):
    conn, client = rig
    pid = _seed_active_product(conn)
    store = FakeClient(status="ACTIVE")
    monkeypatch.setattr(writes, "ShopifyClient", lambda: store)

    res = _submit_delist(conn, pid)
    rid = res["record_id"]

    r = client.post(f"/api/approvals/{rid}",
                     json={"decision": "approved", "confirm": "true"})
    assert r.status_code == 200
    body = r.json()
    assert body["record"]["id"] == rid
    outcome = body["outcome"]
    assert outcome["ok"] is True
    assert outcome["verified_rendered"] is True
    assert outcome["recorded"] is True


def test_unverified_store_readback_records_no_move_and_says_so(rig, monkeypatch):
    conn, client = rig
    pid = _seed_active_product(conn)
    store = FakeClient(status="ACTIVE", readback_status="ACTIVE")
    monkeypatch.setattr(writes, "ShopifyClient", lambda: store)

    res = _submit_delist(conn, pid)
    rid = res["record_id"]

    r = client.post(f"/api/approvals/{rid}",
                     data={"decision": "approved", "confirm": "true"},
                     follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert "refused" in loc
    assert "landed" not in loc

    assert L.state_of(conn, pid) == "active"
    assert len(L.history(conn, pid)) == 1


def test_the_drill_page_shows_the_move(rig, monkeypatch):
    conn, client = rig
    pid = _seed_active_product(conn)
    store = FakeClient(status="ACTIVE")
    monkeypatch.setattr(writes, "ShopifyClient", lambda: store)

    res = _submit_delist(conn, pid)
    rid = res["record_id"]
    client.post(f"/api/approvals/{rid}",
                data={"decision": "approved", "confirm": "true"},
                follow_redirects=False)

    page = client.get(f"/catalog/products/{pid}").text
    assert "removed from store" in page
    # the history timeline carries the new row (who/when/why)
    assert "catalog-delist" in page
