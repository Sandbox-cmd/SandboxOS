"""CW4: the two collection-placement executors on the ONE write door.

`create_collection` makes a smart (rule-based) collection — reversible by
the store's policy, so the auto lane carries it (submit mints AND consumes
the handle in one motion); the executor creates the collection, reads it
back, and the read-back rules ARE the receipt. `mutate_menu` places
collections into the store navigation — CONSEQUENTIAL, so it parks for the
owner and only executes under an approved, consumed handle.

the house laws proven here: a dishonest read-back never counts; a replay is
refused at the wall; provenance rides every proposal; and an off-store leg
never constructs a real Shopify client (the injected fake is used or the
test bombs)."""

import pytest

from commerceos.db import connect
from commerceos.gate import gate, ledger, policy
from commerceos.spine import writes


class FakeStore:
    """scripted Admin GraphQL for collections + menus — a real store is never
    touched. forced_readback makes the live surface DISAGREE with the write,
    so a dishonest store is caught by the receipt, never trusted."""

    def __init__(self, forced_collection=None, forced_menu=None):
        self._collection = None       # what collectionCreate stored
        self._menu = None             # what menu(Create|Update) stored
        self._forced_collection = forced_collection
        self._forced_menu = forced_menu
        self.calls = []

    def graphql(self, query, variables=None):
        self.calls.append(query.split("(")[0].strip().split()[-1])
        variables = variables or {}

        if "mutation collectionCreate" in query:
            ci = variables["input"]
            self._collection = {
                "id": "gid://shopify/Collection/9001",
                "handle": ci.get("handle") or ci["title"].lower().replace(" ", "-"),
                "title": ci["title"],
                "ruleSet": ci.get("ruleSet"),
            }
            return {"collectionCreate": {"collection": dict(self._collection),
                                         "userErrors": []}}
        if "query collection" in query:
            return {"collection": self._forced_collection or self._collection}

        if "mutation menuCreate" in query:
            self._menu = {
                "id": "gid://shopify/Menu/7001",
                "handle": variables["handle"], "title": variables["title"],
                "isDefault": False, "items": _echo_items(variables["items"]),
            }
            return {"menuCreate": {"menu": dict(self._menu), "userErrors": []}}
        if "mutation menuUpdate" in query:
            self._menu = {
                "id": variables["id"], "handle": "main-menu",
                "title": variables["title"], "isDefault": True,
                "items": _echo_items(variables["items"]),
            }
            return {"menuUpdate": {"menu": dict(self._menu), "userErrors": []}}
        if "query menu" in query:
            return {"menu": self._forced_menu or self._menu}

        raise AssertionError(f"unexpected query: {query[:60]}")


def _echo_items(items):
    """what the store hands back — each item gains a server id."""
    out = []
    for i, it in enumerate(items or []):
        out.append({"id": f"gid://shopify/MenuItem/{i}", "title": it["title"],
                    "type": it.get("type"), "url": it.get("url")})
    return out


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "collections.db")
    ledger.ensure_schema(c)
    yield c
    c.close()


# ---------- create_collection: a smart collection through the door ----------

def _collection_proposal(**over):
    p = {
        "agent": "catalog", "function": "catalog-enrichment",
        "method": "create_collection",
        "args": {
            "title": "Head Torches",
            "handle": "head-torches",
            "rules": [{"column": "TYPE", "relation": "EQUALS",
                       "condition": "Head Torch"}],
            "applied_disjunctively": False,
        },
        "declared_type": "reversible",
        "intent": "make the head-torch smart collection",
        "rationale": "the merchandising taxonomy names this leaf",
        "provenance": [{"source": "stores/demostore/taxonomy.json"}],
    }
    p.update(over)
    return p


def test_create_collection_classifies_reversible():
    action_type, flag = policy.classify(
        "create_collection", _collection_proposal()["args"])
    assert action_type == policy.REVERSIBLE
    assert flag is None  # registered, not an unknown-method park


def test_create_collection_auto_lane_executes_and_verifies_rendered(conn):
    res = gate.submit(conn, _collection_proposal())
    assert res["decision"] == "allow" and res["action_type"] == "reversible"
    out = writes.execute(conn, res["record_id"], FakeStore())
    assert out["ok"] and out["verified_rendered"]
    assert out["handle"] == "head-torches" and out["rule_count"] == 1
    rec = ledger.get(conn, res["record_id"])
    assert rec["status"] == "executed"
    assert rec["provenance"]  # provenance rides the record


def test_create_collection_dishonest_readback_never_counts(conn):
    res = gate.submit(conn, _collection_proposal())
    # the store echoes a DIFFERENT title than we wrote — the receipt catches it
    liar = FakeStore(forced_collection={
        "id": "gid://shopify/Collection/9001", "handle": "head-torches",
        "title": "Something Else",
        "ruleSet": {"appliedDisjunctively": False,
                    "rules": [{"column": "TYPE", "relation": "EQUALS",
                               "condition": "Head Torch"}]}})
    out = writes.execute(conn, res["record_id"], liar)
    assert out["ok"] is False and out["verified_rendered"] is False


def test_create_collection_dishonest_rules_never_count(conn):
    res = gate.submit(conn, _collection_proposal())
    # title matches but the live rules differ from what we sent — still caught
    liar = FakeStore(forced_collection={
        "id": "gid://shopify/Collection/9001", "handle": "head-torches",
        "title": "Head Torches",
        "ruleSet": {"appliedDisjunctively": False,
                    "rules": [{"column": "TAG", "relation": "EQUALS",
                               "condition": "clearance"}]}})
    out = writes.execute(conn, res["record_id"], liar)
    assert out["ok"] is False and out["verified_rendered"] is False


def test_create_collection_replay_refused(conn):
    res = gate.submit(conn, _collection_proposal())
    writes.execute(conn, res["record_id"], FakeStore())
    with pytest.raises(writes.WriteRefused):
        writes.execute(conn, res["record_id"], FakeStore())


def test_create_collection_without_a_rule_refuses(conn):
    prop = _collection_proposal()
    prop["args"] = {"title": "Empty", "rules": []}
    res = gate.submit(conn, prop)
    out = writes.execute(conn, res["record_id"], FakeStore())
    assert out["ok"] is False and "membership rule" in out["error"]


# ---------- mutate_menu: main-nav placement, consequential, parks ----------

def _menu_proposal(**over):
    p = {
        "agent": "catalog", "function": "catalog-enrichment",
        "method": "mutate_menu",
        "args": {
            "menu_id": "gid://shopify/Menu/1",
            "title": "Main menu",
            "items": [
                {"title": "Head Torches", "type": "COLLECTION",
                 "resource_id": "gid://shopify/Collection/9001"},
                {"title": "Lanterns", "type": "COLLECTION",
                 "resource_id": "gid://shopify/Collection/9002"},
            ],
        },
        "declared_type": "consequential",
        "intent": "place the smart collections into the main navigation",
        "rationale": "the ~20 collections become the store's nav tree",
        "provenance": [{"source": "owner:cw4-placement-ruling"}],
    }
    p.update(over)
    return p


def test_mutate_menu_classifies_consequential():
    action_type, flag = policy.classify(
        "mutate_menu", _menu_proposal()["args"], declared="consequential")
    assert action_type == policy.CONSEQUENTIAL
    assert flag is None


def test_mutate_menu_parks_for_the_owner_then_executes_on_approval(conn):
    res = gate.submit(conn, _menu_proposal())
    # consequential: a nav rewrite parks per item, it never auto-lands
    assert res["decision"] == "parked" and res["action_type"] == "consequential"
    rec = ledger.get(conn, res["record_id"])
    assert rec["status"] == "pending" and rec["provenance"]

    gate.resolve(conn, res["record_id"], "approved", by="owner")
    out = writes.execute(conn, res["record_id"], FakeStore())
    assert out["ok"] and out["verified_rendered"]
    assert out["item_titles"] == ["Head Torches", "Lanterns"]
    assert ledger.get(conn, res["record_id"])["status"] == "executed"


def test_mutate_menu_dishonest_readback_never_counts(conn):
    res = gate.submit(conn, _menu_proposal())
    gate.resolve(conn, res["record_id"], "approved", by="owner")
    # the store drops an item on read-back — the wholesale-replace risk, caught
    liar = FakeStore(forced_menu={
        "id": "gid://shopify/Menu/1", "handle": "main-menu", "title": "Main menu",
        "isDefault": True,
        "items": [{"id": "x", "title": "Head Torches", "type": "COLLECTION",
                   "url": None}]})
    out = writes.execute(conn, res["record_id"], liar)
    assert out["ok"] is False and out["verified_rendered"] is False


def test_mutate_menu_replay_refused(conn):
    res = gate.submit(conn, _menu_proposal())
    gate.resolve(conn, res["record_id"], "approved", by="owner")
    writes.execute(conn, res["record_id"], FakeStore())
    with pytest.raises(writes.WriteRefused):
        writes.execute(conn, res["record_id"], FakeStore())


def test_mutate_menu_create_path_needs_a_handle(conn):
    prop = _menu_proposal()
    prop["args"] = {"title": "Footer", "items": [{"title": "About"}]}  # no menu_id, no handle
    res = gate.submit(conn, prop)
    gate.resolve(conn, res["record_id"], "approved", by="owner")
    out = writes.execute(conn, res["record_id"], FakeStore())
    assert out["ok"] is False and "handle" in out["error"]


# ---------- the pin: an off-store leg never builds a real client ----------

def test_injected_client_is_used_no_real_client_constructed(conn, monkeypatch):
    """both store-touching executors run only through the injected client;
    if execute ever fell back to ShopifyClient() the bomb would fire."""
    def _bomb(*a, **k):
        raise AssertionError("a real ShopifyClient was constructed — the door leaked")
    monkeypatch.setattr(writes, "ShopifyClient", _bomb)

    cres = gate.submit(conn, _collection_proposal())
    assert writes.execute(conn, cres["record_id"], FakeStore())["ok"]

    mres = gate.submit(conn, _menu_proposal())
    gate.resolve(conn, mres["record_id"], "approved", by="owner")
    assert writes.execute(conn, mres["record_id"], FakeStore())["ok"]
