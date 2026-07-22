"""A5's checks: the ledger schema creates clean; append-only holds by
construction (no delete path, the claim never rewrites, the outcome fills
exactly once, the gate resolves exactly once); queries answer by function,
agent, status, day; the track record math is right; the jsonl audit mirror
grows beside the DB."""

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from commerceos.db import connect, migrate
from commerceos.gate import handles, ledger
from commerceos.gate.ledger import MIGRATIONS, TABLE_SET, AppendOnlyError, StateError

T0 = datetime(2026, 7, 11, 8, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "test.db")
    ledger.ensure_schema(c)
    yield c
    c.close()


def mint_pending(conn, **over):
    rec = {
        "agent": "pricing-agent",
        "function": "pricing",
        "action_type": "consequential",
        "intent": "raise the tent price",
        "rationale": "margin below floor per landed orders",
        "impact": {"money_minor": 9900},
        "provenance": {"cite": "facts:orders@2026-07-10"},
        "proposal": {"connector": "commerce", "method": "mutate_price",
                     "args": {"variant": "v1", "amount_minor": 9900}, "args_hash": "h-v1"},
        "ts": ledger.now(T0),
    }
    rec.update(over)
    return ledger.mint(conn, rec)


def mint_approved(conn, **over):
    gate = {"required": False, "decision": "approved", "by": "policy:auto",
            "ts": over.pop("gate_ts", ledger.now(T0))}
    return mint_pending(conn, status="approved", gate=gate, **over)


# ---------- schema ----------

def test_schema_creates_clean_and_is_idempotent(tmp_path):
    c = connect(tmp_path / "fresh.db")
    assert migrate(c, TABLE_SET, MIGRATIONS) == len(MIGRATIONS)
    assert migrate(c, TABLE_SET, MIGRATIONS) == 0  # re-run: no-op
    tables = {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"ledger", "handles", "events"} <= tables
    c.close()


def test_mint_lands_the_specs_fields_and_the_id_is_the_idempotency_key(conn):
    rid = mint_pending(conn, provenance=None)  # no cite -> marked unverified
    uuid.UUID(rid)  # minted at gate time, a real uuid
    rec = ledger.get(conn, rid)
    assert rec["ts"] == ledger.now(T0)
    assert rec["agent"] == "pricing-agent" and rec["function"] == "pricing"
    assert rec["action_type"] == "consequential"
    assert rec["intent"] and rec["rationale"]
    assert rec["impact"] == {"money_minor": 9900}
    assert rec["provenance"] == {"unverified": True}
    assert rec["proposal"]["args_hash"] == "h-v1"
    assert rec["status"] == "pending"
    assert rec["gate"]["decision"] == "pending"
    assert rec["outcome"] is None


def test_a_record_is_born_pending_or_approved_only(conn):
    with pytest.raises(ValueError):
        mint_pending(conn, status="executing")
    with pytest.raises(ValueError):
        mint_pending(conn, action_type="harmless")  # unknown class refused
    with pytest.raises(ValueError):  # gate.decision must match the birth status
        mint_pending(conn, status="approved")


# ---------- append-only by construction ----------

def test_no_delete_path_anywhere(conn):
    rid = mint_approved(conn)
    handles.mint(conn, rid, "mutate_price", "h-v1")
    ledger.emit_event(conn, "gate.auto_approved", subject=rid)
    for sql in ("DELETE FROM ledger", "DELETE FROM handles", "DELETE FROM events"):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql)


def test_the_claim_never_rewrites(conn):
    rid = mint_pending(conn)
    for sql in (
        "UPDATE ledger SET intent = 'something else' WHERE id = ?",
        "UPDATE ledger SET proposal = '{}' WHERE id = ?",
        "UPDATE ledger SET action_type = 'reversible' WHERE id = ?",
    ):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, (rid,))


def test_the_gate_resolves_exactly_once(conn):
    rid = mint_pending(conn)
    rec = ledger.resolve_gate(conn, rid, "approved", "owner", ts=T0 + timedelta(minutes=5))
    assert rec["status"] == "approved"
    assert rec["gate"] == {"required": True, "decision": "approved",
                           "by": "owner", "ts": ledger.now(T0 + timedelta(minutes=5))}
    with pytest.raises(StateError):  # never re-decide
        ledger.resolve_gate(conn, rid, "rejected", "owner")
    with pytest.raises(sqlite3.IntegrityError):  # and the trigger backs the code
        conn.execute("UPDATE ledger SET gate = '{\"decision\":\"pending\"}' WHERE id = ?", (rid,))


def test_reject_stores_the_reason_and_nothing_executes(conn):
    rid = mint_pending(conn)
    rec = ledger.resolve_gate(conn, rid, "rejected", "owner", reason="wrong sku", ts=T0)
    assert rec["status"] == "rejected" and rec["gate"]["reason"] == "wrong sku"
    with pytest.raises(StateError):
        ledger.begin_execution(conn, rid)  # rejected never executes


def test_the_outcome_fills_exactly_once(conn):
    rid = mint_pending(conn)
    ledger.resolve_gate(conn, rid, "approved", "owner", ts=T0)
    with pytest.raises(StateError):  # approved but not executing yet
        ledger.fill_outcome(conn, rid, {"ok": True}, "executed")
    ledger.begin_execution(conn, rid)
    rec = ledger.fill_outcome(conn, rid, {"ok": True, "shopify_id": "v1"}, "executed",
                              ts=T0 + timedelta(minutes=6))
    assert rec["status"] == "executed" and rec["outcome"]["ok"] is True
    with pytest.raises(AppendOnlyError):  # the second fill is refused
        ledger.fill_outcome(conn, rid, {"ok": False}, "failed")
    with pytest.raises(sqlite3.IntegrityError):  # and the trigger backs the code
        conn.execute("UPDATE ledger SET outcome = '{}' WHERE id = ?", (rid,))


def test_lifecycle_guards_hold(conn):
    rid = mint_pending(conn)
    with pytest.raises(StateError):
        ledger.begin_execution(conn, rid)  # pending cannot execute
    with pytest.raises(ValueError):
        ledger.resolve_gate(conn, rid, "maybe", "owner")
    with pytest.raises(ValueError):
        ledger.resolve_gate(conn, rid, "approved", "  ")  # a resolution carries a name
    with pytest.raises(ValueError):
        ledger.fill_outcome(conn, rid, {}, "done")  # executed|failed only
    with pytest.raises(StateError):
        ledger.expire(conn, mint_approved(conn))  # only pending expires


# ---------- queries ----------

def test_query_by_function_agent_status_day(conn):
    a = mint_pending(conn, ts="2026-07-10T09:00:00+00:00")
    b = mint_pending(conn, function="catalog-enrichment", agent="listing-writer",
                     ts="2026-07-11T09:00:00+00:00")
    c = mint_pending(conn, ts="2026-07-11T10:00:00+00:00")
    ledger.resolve_gate(conn, a, "approved", "owner", ts=T0)

    assert {r["id"] for r in ledger.query(conn, function="pricing")} == {a, c}
    assert [r["id"] for r in ledger.query(conn, agent="listing-writer")] == [b]
    assert [r["id"] for r in ledger.query(conn, status="approved")] == [a]
    assert [r["id"] for r in ledger.query(conn, day="2026-07-10")] == [a]
    assert len(ledger.query(conn, function="pricing", status="pending")) == 1


def test_pending_queue_is_oldest_first(conn):
    b = mint_pending(conn, ts=ledger.now(T0 + timedelta(minutes=1)))
    a = mint_pending(conn, ts=ledger.now(T0))
    assert [r["id"] for r in ledger.pending_queue(conn)] == [a, b]


def test_track_record_math(conn):
    r1 = mint_pending(conn)
    ledger.resolve_gate(conn, r1, "approved", "owner", ts=T0 + timedelta(minutes=10))
    ledger.begin_execution(conn, r1)
    ledger.fill_outcome(conn, r1, {"ok": True}, "executed", ts=T0 + timedelta(minutes=11))
    r2 = mint_pending(conn)
    ledger.resolve_gate(conn, r2, "rejected", "owner", reason="too steep",
                        ts=T0 + timedelta(minutes=20))
    mint_pending(conn)  # r3 stays pending
    # r4: the reversal of r1 — a reversal is its own recorded action
    mint_approved(conn, gate_ts=ledger.now(T0 + timedelta(minutes=30)),
                  proposal={"connector": "commerce", "method": "mutate_price",
                            "args": {"variant": "v1", "amount_minor": 8900},
                            "args_hash": "h-v1-back", "reverts": r1})

    tr = ledger.track_record(conn, "pricing", ts=T0 + timedelta(minutes=40))
    assert tr["proposals"] == 4
    assert tr["approved"] == 2
    assert tr["rejected"] == 1
    assert tr["reversed"] == 1
    assert tr["last_resolved_at"] == ledger.now(T0 + timedelta(minutes=30))
    assert tr["seconds_since_last_resolve"] == 600
    empty = ledger.track_record(conn, "ads-pacing")
    assert empty["proposals"] == 0 and empty["seconds_since_last_resolve"] is None


def test_the_event_log_appends_and_answers(conn):
    ledger.emit_event(conn, "gate.pending", actor="pricing-agent", subject="x1",
                      payload={"function": "pricing"}, ts=T0)
    ledger.emit_event(conn, "gate.approved", actor="owner", subject="x1", ts=T0)
    assert len(ledger.events(conn)) == 2
    got = ledger.events(conn, kind="gate.pending")
    assert got[0]["payload"] == {"function": "pricing"}
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE events SET kind = 'gate.rejected'")


# ---------- the audit mirror ----------

def test_the_jsonl_mirror_grows_beside_the_db(conn, tmp_path):
    assert ledger.mirror_path(conn) == tmp_path / "test.ledger.jsonl"
    rid = mint_pending(conn)
    ledger.resolve_gate(conn, rid, "approved", "owner", ts=T0)
    ledger.begin_execution(conn, rid)
    ledger.fill_outcome(conn, rid, {"ok": True}, "executed", ts=T0)
    lines = [json.loads(l) for l in (tmp_path / "test.ledger.jsonl").read_text().splitlines()]
    assert [l["op"] for l in lines] == ["mint", "resolve", "execute", "outcome"]
    assert lines[0]["id"] == rid and lines[0]["intent"] == "raise the tent price"
