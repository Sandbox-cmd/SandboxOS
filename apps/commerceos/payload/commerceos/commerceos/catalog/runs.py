"""the workflow-run object — one row per batch run (WF-approve, RULED:
every front has an approval step; nothing auto-lands).

the run is the unit the dashboard card counts and the record remembers: a
held batch stages its proposals PARKED at the gate (each one a normal
pending ledger record with its own expiry), and this row groups them so
one glance approves the lot. the approve leg walks the same walls every
approval walks — gate.resolve per record, the one-use handle, the one
write door, the feature's verify-render check — so the ledger honestly
reads who approved, never policy:auto for something a person glanced.

statuses: staged -> executing -> done | rejected. a staged run whose
records all lapsed reads lapsed at render time (a render truth computed
from the ledger, not a stored status — the UI-truth law).

owner: the catalog-workflows part (one writer per table-set).
"""

from __future__ import annotations

import json
import sqlite3
import uuid

from commerceos.gate import gate, ledger
from commerceos.spine import writes

_SCHEMA = """
CREATE TABLE IF NOT EXISTS workflow_runs (
    id            TEXT PRIMARY KEY,
    feature       TEXT NOT NULL,
    ts            TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'staged',
    batch         INTEGER NOT NULL,
    items         TEXT NOT NULL,   -- [{display, record_id, state, rendered?}]
    approved_by   TEXT,
    approved_ts   TEXT,
    reason        TEXT,            -- the why on a rejection
    outcome       TEXT             -- counts json after the execute leg
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def _row(conn, run_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM workflow_runs WHERE id = ?",
                        (run_id,)).fetchone()


def get(conn, run_id: str) -> dict | None:
    r = _row(conn, run_id)
    return _shape(conn, r) if r else None


def list_runs(conn, status: str | None = None, limit: int = 50) -> list[dict]:
    q = "SELECT * FROM workflow_runs"
    args: tuple = ()
    if status:
        q += " WHERE status = ?"
        args = (status,)
    q += " ORDER BY ts DESC LIMIT ?"
    return [_shape(conn, r) for r in conn.execute(q, args + (limit,))]


def _shape(conn, r: sqlite3.Row) -> dict:
    run = dict(r)
    run["items"] = json.loads(run["items"])
    run["outcome"] = json.loads(run["outcome"]) if run["outcome"] else None
    if run["status"] == "staged":
        # lapsed is a render truth: a staged run is approvable only while
        # at least one of its parked records still waits live.
        live = 0
        for it in run["items"]:
            rec = ledger.get(conn, it["record_id"])
            if rec and rec["status"] == "pending" and not ledger.expired(rec["expires_at"]):
                live += 1
        run["live"] = live
        run["lapsed"] = len(run["items"]) - live
        if live == 0:
            run["status"] = "lapsed"
    return run


def create(conn, feature_name: str, items: list[dict], now_ts=None) -> str:
    """persist a staged run grouping the held (parked) proposals."""
    run_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO workflow_runs (id, feature, ts, status, batch, items)"
        " VALUES (?, ?, ?, 'staged', ?, ?)",
        (run_id, feature_name, ledger.now(now_ts), len(items),
         json.dumps(items)))
    conn.commit()
    return run_id


def approve(conn, run_id: str, feature, by: str, client=None,
            now_ts=None) -> dict:
    """the glance-approve: one action lands the whole held batch.

    walks every record through the standard walls — gate.resolve(approved,
    by=<the person>) mints the one-use handle, writes.execute performs the
    store write through the one door, the feature's verify decides whether
    it counts, a verified count routes back into the facts. a record that
    lapsed while the run waited is skipped and named lapsed, never executed
    late. one item's failure never kills the batch.
    """
    r = _row(conn, run_id)
    if r is None:
        raise KeyError(f"no workflow run {run_id}")
    if r["status"] != "staged":
        raise ledger.StateError(f"run is {r['status']} — only a staged run approves")
    if feature.declared_type != "reversible":
        raise ledger.StateError(
            "batch approve is the reversible lane — this front rules per item")
    items = json.loads(r["items"])
    counts = {"approved": 0, "executed": 0, "counted": 0, "failed": 0,
              "errored": 0, "lapsed": 0}
    conn.execute("UPDATE workflow_runs SET status='executing', approved_by=?,"
                 " approved_ts=? WHERE id=?", (by, ledger.now(now_ts), run_id))
    conn.commit()
    for it in items:
        rid = it["record_id"]
        try:
            gate.resolve(conn, rid, "approved", by=by, now_ts=now_ts)
        except ledger.StateError:
            counts["lapsed"] += 1
            it["state"] = "lapsed — expired before your approve, not executed"
            continue
        counts["approved"] += 1
        try:
            # client=None lets the write door construct the real store
            # client — the same one-door law as every other approval
            out = writes.execute(conn, rid, client)
        except Exception as e:  # one item's failure never kills the batch
            counts["errored"] += 1
            it["state"] = f"errored — {str(e)[:80]}"
            continue
        counts["executed"] += 1
        ok = feature.verify(out, it)
        counts["counted" if ok else "failed"] += 1
        it["state"] = "counted" if ok else "executed, not verified — not counted"
        it["rendered"] = out
        if ok and feature.writeback is not None:
            feature.writeback(conn, it, out)
    conn.execute("UPDATE workflow_runs SET status='done', items=?, outcome=?"
                 " WHERE id=?", (json.dumps(items), json.dumps(counts), run_id))
    conn.commit()
    ledger.emit_event(conn, "workflow_run.approved", actor=by, subject=run_id,
                      payload={"feature": r["feature"], **counts}, ts=now_ts)
    return {"run_id": run_id, "status": "done", **counts, "items": items}


def reject(conn, run_id: str, by: str, why: str, now_ts=None) -> dict:
    """decline the whole held batch — the why lands on every record."""
    r = _row(conn, run_id)
    if r is None:
        raise KeyError(f"no workflow run {run_id}")
    if r["status"] != "staged":
        raise ledger.StateError(f"run is {r['status']} — only a staged run rejects")
    items = json.loads(r["items"])
    n = 0
    for it in items:
        try:
            gate.resolve(conn, it["record_id"], "rejected", by=by,
                         reason=why, now_ts=now_ts)
            n += 1
            it["state"] = "declined — nothing executed"
        except ledger.StateError:
            it["state"] = "lapsed — expired before your call"
    conn.execute("UPDATE workflow_runs SET status='rejected', approved_by=?,"
                 " approved_ts=?, reason=?, items=? WHERE id=?",
                 (by, ledger.now(now_ts), why, json.dumps(items), run_id))
    conn.commit()
    ledger.emit_event(conn, "workflow_run.rejected", actor=by, subject=run_id,
                      payload={"feature": r["feature"], "declined": n,
                               "why": why}, ts=now_ts)
    return {"run_id": run_id, "status": "rejected", "declined": n}
