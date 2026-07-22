"""C2+A6 fixture checks: the control loop end to end with a fake client —
reversible auto-executes, consequential parks then approves through the
web's only approve verb, the handle consumes exactly once."""

import pytest
from fastapi.testclient import TestClient

from commerceos.db import connect
from commerceos.gate import gate, ledger
from commerceos.spine import writes


class FakeClient:
    """scripted GraphQL: product tags update + readback, price + readback."""

    def __init__(self):
        self.tags = ["Camping"]
        self.price = "164.00"
        self.calls = []

    def graphql(self, query, variables=None):
        self.calls.append(query.split("(")[0].strip())
        if "productUpdate" in query:
            self.tags = variables["input"]["tags"]
            return {"productUpdate": {"product": {"id": "gid://x/1", "tags": self.tags},
                                      "userErrors": []}}
        if "productVariantsBulkUpdate" in query:
            self.price = variables["variants"][0]["price"]
            return {"productVariantsBulkUpdate": {"productVariants": [{"id": "v1", "price": self.price}],
                                                  "userErrors": []}}
        if "query product" in query:
            return {"product": {"id": "gid://x/1", "tags": self.tags, "title": "T"}}
        if "query variant" in query:
            return {"node": {"id": "v1", "price": self.price}}
        raise AssertionError(f"unexpected query: {query[:60]}")


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "loop.db")
    ledger.ensure_schema(c)
    yield c
    c.close()


def test_reversible_auto_executes_and_lands_outcome(conn):
    res = gate.submit(conn, {
        "agent": "catalog", "function": "catalog-enrichment",
        "method": "mutate_product_field",
        "args": {"product_id": "gid://x/1", "field": "tags", "value": ["Camping", "Hike"]},
        "declared_type": "reversible", "intent": "tag cleanup",
        "rationale": "normalize activity tags", "provenance": [{"source": "test"}],
    })
    assert res["decision"] == "allow" and res["status"] == "executing"
    out = writes.execute(conn, res["record_id"], client=FakeClient())
    assert out["ok"] is True and out["verified_rendered"] is True
    rec = ledger.get(conn, res["record_id"])
    assert rec["status"] == "executed"


def test_consequential_parks_then_approves_via_web_and_replay_refused(conn, tmp_path, monkeypatch):
    res = gate.submit(conn, {
        "agent": "pricing-draft", "function": "pricing", "method": "mutate_price",
        "args": {"product_id": "gid://x/1", "variant_id": "v1", "price": "180.00"},
        "declared_type": "consequential", "intent": "reprice test variant",
        "rationale": "A6 proof", "impact": {"money_minor": 1600},
    })
    assert res["decision"] == "parked"
    rid = res["record_id"]

    # the web surface is the only approve path; confirm is required
    monkeypatch.setenv("COMMERCEOS_DB", str(tmp_path / "loop.db"))
    from commerceos.web.app import app
    client = TestClient(app)
    denied = client.post(f"/api/approvals/{rid}", json={"decision": "approved"})
    assert denied.status_code == 400  # no confirm

    fake = FakeClient()
    monkeypatch.setattr("commerceos.spine.writes.ShopifyClient", lambda *a, **k: fake)
    ok = client.post(f"/api/approvals/{rid}", json={"decision": "approved", "confirm": True})
    assert ok.status_code == 200
    body = ok.json()
    assert body["outcome"]["ok"] is True and fake.price == "180.00"
    assert body["record"]["status"] == "executed"

    # replay: the handle consumed exactly once
    with pytest.raises(writes.WriteRefused):
        writes.execute(conn, rid, client=fake)


def test_record_and_approvals_pages_render_the_loop(conn, tmp_path, monkeypatch):
    gate.submit(conn, {
        "agent": "catalog", "function": "catalog-enrichment",
        "method": "mutate_product_field",
        "args": {"product_id": "gid://x/9", "field": "publish", "value": "publish",
                 "state": "publish"},
        "declared_type": "reversible",  # self-downgrade attempt -> gated stricter
        "intent": "publish nine", "rationale": "page render test",
    })
    monkeypatch.setenv("COMMERCEOS_DB", str(tmp_path / "loop.db"))
    from commerceos.web.app import app
    client = TestClient(app)
    approvals = client.get("/approvals")
    assert "publish nine" in approvals.text and "confirm" in approvals.text
    record = client.get("/record")
    # the record card speaks plain words — never the raw method identifier
    # (coldread 2026-07-18: mutate_variant_field reached the screen once)
    assert "product detail changed" in record.text
    assert "mutate_product_field" not in record.text
