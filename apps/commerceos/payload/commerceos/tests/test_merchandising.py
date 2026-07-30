"""CW5 merchandising / smart collections — the engine + module pins.

the laws proven here: the ~20 definitions are DATA derived from the locked
taxonomy (product_type rules, the honest fallback); the queue proposes only
collections not yet on the store; collection-coverage is honest at 0 and moves
on a synced fixture (membership lags until sync — the create receipt never
fakes it); the create batch RIDES the hold loop (parks, one run, one glance-
approve executes through the one door + verify-renders); and the nav-placement
flow is SEPARATE and consequential — one mutate_menu proposal that parks with
its plain WHY, never auto-lands.
"""

import json

import pytest

from commerceos.catalog import merchandising as M
from commerceos.catalog import runs as R
from commerceos.catalog import workflows as W
from commerceos.db import connect
from commerceos.gate import gate, ledger, policy
from commerceos.spine import writes
from commerceos.spine.schema import ensure_schema

# the CW4 scripted store — a real store is never touched (reused verbatim).
from tests.test_collection_executor import FakeStore


@pytest.fixture()
def conn(tmp_path, monkeypatch):
    db = tmp_path / "merch.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    c = connect(db)
    ensure_schema(c)
    ledger.ensure_schema(c)
    yield c
    c.close()


def seed(c, pid, product_type="Flashlights", collections=None):
    c.execute(
        "INSERT INTO products (shopify_id, handle, title, status, vendor,"
        " product_type, tags, collections, raw, source, fetched_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (pid, f"h-{pid}", f"P {pid}", "ACTIVE", "V", product_type, "[]",
         json.dumps(collections or []), "{}", "test", "2026-07-19T00:00:00Z"))


# ---------- the definitions are DATA, derived from the locked taxonomy ----------

def test_definitions_are_config_derived_from_the_taxonomy_categories():
    cfg = M.load_config()
    defs = cfg["collections"]
    # ~20, one per major category — the taxonomy's classifier categories
    assert 18 <= len(defs) <= 22
    titles = {d["title"] for d in defs}
    for cat in ("Lighting", "Tents & Shelters", "Camp Kitchen", "Apparel"):
        assert cat in titles
    # the honest fallback: product_type rules, NOT a metafield rule (the schema
    # enum offers PRODUCT_METAFIELD_DEFINITION but it needs a definition +
    # conditionObjectId the shipped executor never sends — see collections.json)
    assert cfg["rule_basis"] == "product_type"
    for d in defs:
        assert d["rules"], f"{d['title']} carries at least one membership rule"
        for r in d["rules"]:
            assert r["column"] == "TYPE"
            assert r["relation"] == "CONTAINS"
            assert r["condition"]


# ---------- the queue proposes only collections not yet on the store ----------

def test_queue_is_every_definition_on_an_empty_store(conn):
    seed(conn, "p1", "Flashlights")
    conn.commit()
    q = M.merch_queue(conn)
    assert len(q) == len(M.definitions())
    # each item carries the create_collection args the door reads
    item = next(i for i in q if i["title"] == "Lighting")
    assert item["args"]["title"] == "Lighting"
    assert item["args"]["handle"] == "lighting"
    assert item["args"]["rules"] and item["args"]["applied_disjunctively"] is True
    # the display reads in plain words for the preview (no column/relation code)
    assert item["display"].startswith("new collection: Lighting")
    assert "TYPE" not in item["display"] and "CONTAINS" not in item["display"]


def test_queue_excludes_collections_already_live_on_the_store(conn):
    # a fake-synced fixture: p1's membership already names Lighting, so that
    # shelf EXISTS — the queue must not re-propose it
    seed(conn, "p1", "Flashlights", collections=["Lighting"])
    seed(conn, "p2", "Tents")
    conn.commit()
    titles = {i["title"] for i in M.merch_queue(conn)}
    assert "Lighting" not in titles
    assert "Tents & Shelters" in titles
    assert len(M.merch_queue(conn)) == len(M.definitions()) - 1


# ---------- coverage: honest at 0, moving on a synced fixture ----------

def test_coverage_is_honest_at_zero_before_any_collection_lands(conn):
    seed(conn, "p1", "Flashlights")
    seed(conn, "p2", "Tents")
    conn.commit()
    prog = M.merch_progress(conn)
    assert prog["covered"] == 0 and prog["total"] == 2 and prog["rate"] == 0.0
    assert prog["collections_live"] == 0
    assert prog["to_create"] == prog["collections_total"] == len(M.definitions())


def test_coverage_moves_on_a_fake_synced_fixture(conn):
    # the sync landed memberships: p1 in Lighting, p2 in nothing yet
    seed(conn, "p1", "Flashlights", collections=["Lighting"])
    seed(conn, "p2", "Tents", collections=[])
    conn.commit()
    prog = M.merch_progress(conn)
    assert prog["covered"] == 1 and prog["total"] == 2 and prog["rate"] == 0.5
    assert prog["collections_live"] == 1
    assert prog["to_create"] == len(M.definitions()) - 1


def test_only_our_smart_collections_count_toward_coverage(conn):
    # a pre-existing UNRELATED collection on a product does not fake coverage
    seed(conn, "p1", "Flashlights", collections=["Clearance"])
    conn.commit()
    assert M.merch_progress(conn)["covered"] == 0


# ---------- verify: only an honest read-back counts ----------

def test_verify_counts_only_a_true_readback():
    item = {"handle": "lighting", "rules": [{"column": "TYPE"}, {"column": "TYPE"}]}
    assert M.merch_verify(
        {"ok": True, "verified_rendered": True, "handle": "lighting", "rule_count": 2},
        item)
    # a store that echoed a different handle, or fewer rules, never counts
    assert not M.merch_verify(
        {"ok": True, "verified_rendered": True, "handle": "other", "rule_count": 2}, item)
    assert not M.merch_verify(
        {"ok": True, "verified_rendered": True, "handle": "lighting", "rule_count": 1}, item)
    assert not M.merch_verify(
        {"ok": False, "verified_rendered": False}, item)


# ---------- the create batch rides the hold loop (WF-approve) ----------

def test_create_batch_holds_one_run_and_lands_on_one_glance_approve(conn):
    seed(conn, "p1", "Flashlights")
    conn.commit()
    feat = W.MERCHANDISING
    n_defs = len(M.definitions())

    # hold: every proposal PARKS, grouped into ONE run — nothing executes,
    # nothing auto-approves (the reversible batch waits for one glance)
    rep = W.run_feature(conn, feat, hold=True)
    assert rep["parked"] == min(n_defs, feat.batch_default)
    assert rep.get("run_id")
    assert conn.execute("SELECT COUNT(*) FROM handles").fetchone()[0] == 0
    assert {r[0] for r in conn.execute("SELECT status FROM ledger")} == {"pending"}

    # the glance-approve walks each record through the one write door + verify
    out = R.approve(conn, rep["run_id"], feat, by="owner", client=FakeStore())
    assert out["status"] == "done"
    assert out["counted"] == out["executed"] == min(n_defs, feat.batch_default)
    assert out["failed"] == 0 and out["errored"] == 0
    # the ledger honestly reads approved-by-a-person, never policy:auto
    execed = conn.execute(
        "SELECT COUNT(*) FROM ledger WHERE status = 'executed'").fetchone()[0]
    assert execed == min(n_defs, feat.batch_default)


def test_coverage_still_lags_after_creates_until_the_next_sync(conn):
    # the honesty pin: creating collections does NOT move coverage — membership
    # settles on the store and lands on the next sync (writeback is None by
    # design), so the card stays honest "as of the last sync"
    seed(conn, "p1", "Flashlights")
    conn.commit()
    rep = W.run_feature(conn, W.MERCHANDISING, hold=True)
    R.approve(conn, rep["run_id"], W.MERCHANDISING, by="owner", client=FakeStore())
    assert M.merch_progress(conn)["covered"] == 0  # still lagging, honestly


# ---------- the nav-placement flow: SEPARATE, consequential, parks ----------

def test_nav_proposal_is_none_with_no_live_collections(conn):
    seed(conn, "p1", "Flashlights")           # nothing synced live yet
    conn.commit()
    assert M.nav_proposal(conn) is None


def test_nav_proposal_parks_consequential_with_its_why(conn):
    seed(conn, "p1", "Flashlights", collections=["Lighting"])
    conn.commit()
    prop = M.nav_proposal(conn)
    assert prop is not None and prop["method"] == "mutate_menu"
    # the WHY a person reads on the parked card
    assert "waits on you" in prop["rationale"]
    assert prop["args"]["items"][0]["title"] == "Lighting"
    # the intent agrees in number with its count — one collection, singular
    assert prop["intent"] == "place 1 smart collection into your store's main menu"

    # classed consequential — the door + policy agree it parks
    action_type, flag = policy.classify(
        "mutate_menu", prop["args"], declared="consequential")
    assert action_type == policy.CONSEQUENTIAL and flag is None

    # gate.submit PARKS it (never auto-lands) — one pending record, no handle
    res = gate.submit(conn, prop)
    assert res["decision"] == "parked" and res["action_type"] == "consequential"
    rec = ledger.get(conn, res["record_id"])
    assert rec["status"] == "pending" and rec["provenance"]
    assert conn.execute("SELECT COUNT(*) FROM handles").fetchone()[0] == 0

    # and on the owner's approval it executes through the one door + reads back
    gate.resolve(conn, res["record_id"], "approved", by="owner")
    out = writes.execute(conn, res["record_id"], FakeStore())
    assert out["ok"] and out["verified_rendered"]
    assert out["item_titles"] == ["Lighting"]
