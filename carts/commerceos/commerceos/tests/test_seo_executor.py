"""S1: the listing-text executor (mutate_seo) — the registered-but-not-
runnable trap closed. reversible by the store's policy, so the auto lane
carries it (submit mints AND consumes the handle in one motion); the
executor writes the search listing and reads it back as the receipt; a
dishonest read-back returns ok=False; a replay is refused at the wall."""

import pytest

from commerceos.db import connect
from commerceos.gate import gate, ledger, policy
from commerceos.spine import writes


class FakeClient:
    """scripted GraphQL: productUpdate(seo) + a seo readback.

    forced_readback makes the live surface disagree with the write, so a
    dishonest store is caught by the receipt, not trusted."""

    def __init__(self, forced_readback=None):
        self.seo = {"title": None, "description": None}
        self._forced = forced_readback
        self.calls = []

    def graphql(self, query, variables=None):
        self.calls.append(query.split("(")[0].strip())
        if "mutation productSeo" in query:
            self.seo.update(variables["input"]["seo"])
            return {"productUpdate": {
                "product": {"id": variables["input"]["id"], "seo": dict(self.seo)},
                "userErrors": []}}
        if "query productSeo" in query:
            return {"product": {"id": "gid://x/1",
                                "seo": self._forced or dict(self.seo)}}
        raise AssertionError(f"unexpected query: {query[:60]}")


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "seo.db")
    ledger.ensure_schema(c)
    yield c
    c.close()


def _seo_proposal(title="Torch X — 900 lm rechargeable torch",
                  description="A rechargeable torch for wadi nights."):
    return {
        "agent": "content", "function": "content-geo",
        "method": "mutate_seo",
        "args": {"product_id": "gid://x/1", "title": title,
                 "description": description},
        "declared_type": "reversible",
        "intent": "write the search listing",
        "rationale": "listing text drafted from catalog facts",
        "provenance": [{"source": "canonical:spec_claims"}],
    }


def test_seo_classifies_reversible():
    action_type, _ = policy.classify(
        "mutate_seo", {"product_id": "gid://x/1", "title": "t"})
    assert action_type == policy.REVERSIBLE


def test_auto_lane_executes_and_verifies_rendered(conn):
    res = gate.submit(conn, _seo_proposal())
    assert res["decision"] == "allow"
    client = FakeClient()
    out = writes.execute(conn, res["record_id"], client)
    assert out["ok"] and out["verified_rendered"]
    assert out["seo"]["title"].startswith("Torch X")
    assert ledger.get(conn, res["record_id"])["status"] == "executed"


def test_dishonest_readback_fails_honestly(conn):
    res = gate.submit(conn, _seo_proposal())
    client = FakeClient(forced_readback={"title": "something else",
                                         "description": None})
    out = writes.execute(conn, res["record_id"], client)
    assert out["ok"] is False and out["verified_rendered"] is False


def test_replay_refused(conn):
    res = gate.submit(conn, _seo_proposal())
    writes.execute(conn, res["record_id"], FakeClient())
    with pytest.raises(writes.WriteRefused):
        writes.execute(conn, res["record_id"], FakeClient())


def test_empty_seo_refuses(conn):
    prop = _seo_proposal()
    prop["args"] = {"product_id": "gid://x/1"}
    res = gate.submit(conn, prop)
    out = writes.execute(conn, res["record_id"], FakeClient())
    assert out["ok"] is False and "title or a description" in out["error"]
