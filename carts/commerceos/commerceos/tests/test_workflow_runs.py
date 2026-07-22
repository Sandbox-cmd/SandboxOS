"""WF-approve's checks: the batch-approve loop (RULED — every front has an
approval step; nothing auto-lands).

a held run PARKS every proposal, even reversible ones, and groups them into
one workflow-run row; nothing touches the store until one glance-approve.
the approve walks the standard walls per record — gate.resolve by a PERSON
(the ledger never reads policy:auto for a held batch), the one-use handle,
the one write door, verify-render before a fix counts. a record that lapsed
while the run waited is named lapsed and never executed late. reject lands
the why on every record. the consequential lane refuses the batch verb —
it rules per item, as ruled.
"""

import pytest

from commerceos.catalog import runs as R
from commerceos.catalog import workflows as W
from commerceos.db import connect
from commerceos.gate import gate, ledger
from commerceos.spine.schema import ensure_schema

from tests.test_catalog_workflows import FakeStore, seed_variant, VALID12, VALID13


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "runs.db")
    ensure_schema(c)
    ledger.ensure_schema(c)
    R.ensure_schema(c)
    yield c
    c.close()


def _stage(conn, **kw):
    seed_variant(conn, "p1", "'" + VALID13)
    seed_variant(conn, "p2", VALID12[1:])
    return W.run_feature(conn, W.GTIN, hold=True, **kw)


# --- the hold: parks, groups, executes nothing ---------------------------


def test_a_held_run_parks_reversible_proposals_and_stages_one_run(conn):
    rep = _stage(conn)
    assert rep["parked"] == 2 and rep["executed"] == 0
    assert rep["run_id"]
    run = R.get(conn, rep["run_id"])
    assert run["status"] == "staged" and run["batch"] == 2
    # every grouped record is an ordinary pending ledger row with an expiry
    for it in run["items"]:
        rec = ledger.get(conn, it["record_id"])
        assert rec["status"] == "pending" and rec["expires_at"]
    # and the store was never touched — no handle minted, nothing executed
    assert conn.execute("SELECT COUNT(*) FROM handles").fetchone()[0] == 0


def test_hold_never_applies(conn):
    with pytest.raises(ValueError):
        W.run_feature(conn, W.GTIN, client=FakeStore(), apply=True, hold=True)


# --- the glance-approve: one action, every wall intact -------------------


def test_one_approve_lands_the_batch_verified_and_by_a_person(conn):
    rep = _stage(conn)
    store = FakeStore()
    out = R.approve(conn, rep["run_id"], W.GTIN, by="localhost", client=store)
    assert out["approved"] == 2 and out["executed"] == 2 and out["counted"] == 2
    run = R.get(conn, rep["run_id"])
    assert run["status"] == "done" and run["approved_by"] == "localhost"
    # the ledger reads a person's approval on every record — never policy:auto
    for it in run["items"]:
        rec = ledger.get(conn, it["record_id"])
        assert rec["gate"]["by"] == "localhost"
        assert rec["status"] == "executed"
    # the verified value was written back into the facts
    row = conn.execute("SELECT barcode FROM variants WHERE product_id='p1'").fetchone()
    assert row[0] == VALID13


def test_an_unrendered_write_does_not_count_but_the_batch_continues(conn):
    rep = _stage(conn)
    out = R.approve(conn, rep["run_id"], W.GTIN, by="localhost",
                    client=FakeStore(reject={"v-p2"}))
    assert out["executed"] == 2 and out["counted"] == 1 and out["failed"] == 1


def test_a_done_run_never_approves_twice(conn):
    rep = _stage(conn)
    R.approve(conn, rep["run_id"], W.GTIN, by="localhost", client=FakeStore())
    with pytest.raises(ledger.StateError):
        R.approve(conn, rep["run_id"], W.GTIN, by="localhost", client=FakeStore())


def test_the_consequential_lane_refuses_the_batch_verb(conn):
    rep = _stage(conn)
    with pytest.raises(ledger.StateError):
        R.approve(conn, rep["run_id"], W.DELIST, by="localhost")


# --- reject: the why lands on every record -------------------------------


def test_reject_lands_the_why_on_every_record_and_nothing_executes(conn):
    rep = _stage(conn)
    out = R.reject(conn, rep["run_id"], by="localhost", why="wrong batch")
    assert out["declined"] == 2
    run = R.get(conn, rep["run_id"])
    assert run["status"] == "rejected" and run["reason"] == "wrong batch"
    for it in run["items"]:
        rec = ledger.get(conn, it["record_id"])
        assert rec["status"] == "rejected"
        assert rec["gate"]["reason"] == "wrong batch"
    # the store untouched
    row = conn.execute("SELECT barcode FROM variants WHERE product_id='p1'").fetchone()
    assert row[0] == "'" + VALID13


# --- lapse: expired waits never execute late -----------------------------


OLD = "2026-01-01T00:00:00+00:00"   # a staging time whose window has passed


def _held(conn, item, now_ts=None):
    res = gate.submit(conn, {
        "agent": W.GTIN.agent, "function": "catalog-enrichment",
        "method": W.GTIN.method, "args": item["args"],
        "declared_type": "reversible", "intent": W.GTIN.intent,
        "rationale": item["display"],
    }, now_ts=now_ts, hold=True)
    return {**item, "record_id": res["record_id"]}


def test_a_lapsed_record_is_named_lapsed_and_never_executed(conn):
    # one record staged in a window long closed, one staged live — the
    # append-only ledger is never rewritten; the ages are honest
    seed_variant(conn, "p1", "'" + VALID13)
    seed_variant(conn, "p2", VALID12[1:])
    stale_item, live_item = W._gtin_queue(conn)
    stale = _held(conn, stale_item, now_ts=OLD)
    live = _held(conn, live_item)
    run_id = R.create(conn, "gtin", [stale, live])
    out = R.approve(conn, run_id, W.GTIN, by="localhost", client=FakeStore())
    assert out["lapsed"] == 1 and out["executed"] == 1 and out["counted"] == 1
    states = {it["record_id"]: it["state"] for it in out["items"]}
    assert states[stale["record_id"]].startswith("lapsed")


def test_a_fully_lapsed_run_reads_lapsed_at_render_time(conn):
    seed_variant(conn, "p1", "'" + VALID13)
    seed_variant(conn, "p2", VALID12[1:])
    rep = W.run_feature(conn, W.GTIN, hold=True, now_ts=OLD)
    run = R.get(conn, rep["run_id"])
    assert run["status"] == "lapsed" and run["live"] == 0


# --- the gate's hold contract, unit-level --------------------------------


def test_gate_hold_parks_what_would_auto_approve(conn):
    res = gate.submit(conn, {
        "agent": "catalog-gtin", "function": "catalog-enrichment",
        "method": "mutate_variant_field", "args": {"x": 1},
        "declared_type": "reversible", "intent": "t", "rationale": "t",
    }, hold=True)
    assert res["decision"] == "parked" and res["status"] == "pending"
    rec = ledger.get(conn, res["record_id"])
    assert rec["gate"]["required"] is True and rec["gate"]["decision"] == "pending"
