"""CW2: the product-state executor (delist / relist / archive).

modeled on test_control_loop.py: a state change is consequential, so it
PARKS (never auto-executes); the owner's approve mints the one-use handle;
writes.execute flips the store status and verify-renders (readback ==
mapped target); a replay of the same handle is refused at the wall; a
readback that disagrees returns ok=False (verify-render fails honestly).

the executor performs ONLY the store write + receipt — it writes no local
lifecycle table. catalog-lifecycle commits state + history on this receipt.
"""

import pytest

from commerceos.db import connect
from commerceos.gate import gate, ledger, policy
from commerceos.spine import writes


class FakeClient:
    """scripted GraphQL: productUpdate(status) + a status readback.

    readback_status forces the read-back to disagree with the write, so a
    dishonest store (write said ok, live surface says otherwise) is caught.
    """

    def __init__(self, status="ACTIVE", readback_status=None):
        self.status = status
        self._forced_readback = readback_status
        self.calls = []

    def graphql(self, query, variables=None):
        self.calls.append(query.split("(")[0].strip())
        if "productUpdate" in query:
            self.status = variables["input"]["status"]
            return {"productUpdate": {
                "product": {"id": variables["input"]["id"], "status": self.status},
                "userErrors": []}}
        if "query productStatus" in query:
            return {"product": {"id": "gid://x/1",
                                "status": self._forced_readback or self.status}}
        raise AssertionError(f"unexpected query: {query[:60]}")


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "state.db")
    ledger.ensure_schema(c)
    yield c
    c.close()


def _delist_proposal(product_id="gid://x/1", state="delisted"):
    return {
        "agent": "catalog", "function": "catalog-enrichment",
        "method": "mutate_product_state",
        "args": {"product_id": product_id, "state": state},
        "declared_type": "consequential",
        "intent": f"{state} the product",
        "rationale": "quality flag ruled — pull it",
        "provenance": [{"source": "quality.py"}],
    }


def test_state_change_classifies_consequential():
    # the mechanism default: a shipped state method the store table omits
    # still parks — it never silently falls to fit_critical, and it is not
    # reversible-by-default.
    action_type, _flag = policy.classify(
        "mutate_product_state", {"product_id": "gid://x/1", "state": "delisted"})
    assert action_type == policy.CONSEQUENTIAL


def test_state_change_parks_and_does_not_auto_execute(conn):
    res = gate.submit(conn, _delist_proposal())
    assert res["decision"] == "parked"
    assert res["action_type"] == policy.CONSEQUENTIAL
    assert res["status"] == "pending"
    # parked means nothing executed: the record has no outcome yet.
    rec = ledger.get(conn, res["record_id"])
    assert rec["status"] == "pending"


def test_approved_state_change_flips_store_and_verify_renders(conn):
    res = gate.submit(conn, _delist_proposal())
    rid = res["record_id"]
    assert res["decision"] == "parked"

    # the owner's only approve path mints the one-use handle.
    gate.resolve(conn, rid, "approved", by="owner", reason="pull it")

    fake = FakeClient(status="ACTIVE")
    out = writes.execute(conn, rid, client=fake)

    # delisted maps to DRAFT; the store flipped and the read-back confirms it.
    assert fake.status == "DRAFT"
    assert out["ok"] is True and out["verified_rendered"] is True
    assert out["status"] == "DRAFT"

    rec = ledger.get(conn, rid)
    assert rec["status"] == "executed"

    # replay: the handle consumed exactly once — the wall refuses the second.
    with pytest.raises(writes.WriteRefused):
        writes.execute(conn, rid, client=fake)


def test_relist_is_just_state_active(conn):
    # the executor is state-agnostic: relist = state="active" -> ACTIVE.
    res = gate.submit(conn, _delist_proposal(state="active"))
    rid = res["record_id"]
    gate.resolve(conn, rid, "approved", by="owner", reason="clear cleared — put it back")
    fake = FakeClient(status="DRAFT")
    out = writes.execute(conn, rid, client=fake)
    assert fake.status == "ACTIVE"
    assert out["ok"] is True and out["status"] == "ACTIVE"


def test_readback_mismatch_returns_ok_false(conn):
    res = gate.submit(conn, _delist_proposal(state="archived"))
    rid = res["record_id"]
    gate.resolve(conn, rid, "approved", by="owner", reason="gone for good")

    # the write claims ARCHIVED but the live surface still reads ACTIVE.
    fake = FakeClient(status="ACTIVE", readback_status="ACTIVE")
    out = writes.execute(conn, rid, client=fake)

    assert out["ok"] is False and out["verified_rendered"] is False
    assert out["status"] == "ACTIVE"
