"""the ledger — one record per action, append-only by construction.

part: the gate + the record (spec/parts/gate-and-record.md). sole writer
of the "ledger" table-set: ledger (the records), handles (one-use write
capabilities), events (the shared event log the web surface feeds from).

append-only means three things here, all enforced:
  - no delete path — DB triggers abort any DELETE, and the module has none.
  - the claim never rewrites — id, ts, agent, function, action_type,
    intent, rationale, impact, provenance, proposal are frozen at mint
    (trigger-enforced).
  - the only mutations are the lifecycle, each exactly once and one-way:
    gate resolve (pending -> approved | rejected), execution begin
    (approved -> executing, tied to consuming the handle), outcome fill
    (executing -> executed | failed), expiry (pending -> expired).
    a second outcome fill or a second resolve is refused, in code and by
    trigger.

the record id is minted at gate time and IS the idempotency key.

beside the DB sits <name>.ledger.jsonl — the audit mirror, opened
append-only, one line per operation, cheap and git-diffable (v0's
pattern, kept; named after the DB since M3 so stores never share one).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from commerceos.db import connect, migrate

TABLE_SET = "ledger"

ACTION_TYPES = ("reversible", "consequential", "fit_critical")
# lifecycle: pending -> approved -> executing -> executed | failed ; or -> rejected | expired
STATUSES = ("pending", "approved", "rejected", "executing", "executed", "failed", "expired")

MIGRATIONS = [
    """
    CREATE TABLE ledger (
        id          TEXT PRIMARY KEY,       -- minted at gate time; the idempotency key
        ts          TEXT NOT NULL,
        agent       TEXT NOT NULL,
        function    TEXT NOT NULL,
        action_type TEXT NOT NULL CHECK (action_type IN
                        ('reversible','consequential','fit_critical')),
        intent      TEXT NOT NULL DEFAULT '',
        rationale   TEXT NOT NULL DEFAULT '',
        impact      TEXT,                   -- JSON: money, scope, risk
        provenance  TEXT NOT NULL,          -- JSON: a cite, or {"unverified": true}
        proposal    TEXT NOT NULL,          -- JSON: connector, method, args, args_hash, declared_type
        status      TEXT NOT NULL CHECK (status IN
                        ('pending','approved','rejected','executing','executed','failed','expired')),
        expires_at  TEXT,                   -- gated records only; pending past this reads expired
        gate        TEXT NOT NULL,          -- JSON: required, decision, by, ts, flag
        outcome     TEXT                    -- JSON; NULL until the one-time fill
    );
    CREATE INDEX ledger_function ON ledger (function);
    CREATE INDEX ledger_agent    ON ledger (agent);
    CREATE INDEX ledger_status   ON ledger (status);

    -- append-only by construction: no delete, and the claim never rewrites.
    CREATE TRIGGER ledger_no_delete BEFORE DELETE ON ledger
    BEGIN SELECT RAISE(ABORT, 'ledger is append-only: no delete path'); END;
    CREATE TRIGGER ledger_no_rewrite BEFORE UPDATE OF
        id, ts, agent, function, action_type, intent, rationale,
        impact, provenance, proposal, expires_at ON ledger
    BEGIN SELECT RAISE(ABORT, 'ledger is append-only: the claim never rewrites'); END;
    CREATE TRIGGER ledger_outcome_once BEFORE UPDATE OF outcome ON ledger
        WHEN OLD.outcome IS NOT NULL
    BEGIN SELECT RAISE(ABORT, 'the outcome fills exactly once'); END;
    CREATE TRIGGER ledger_gate_once BEFORE UPDATE OF gate ON ledger
        WHEN json_extract(OLD.gate, '$.decision') NOT IN ('pending')
    BEGIN SELECT RAISE(ABORT, 'the gate resolves exactly once'); END;

    CREATE TABLE handles (
        ledger_id   TEXT PRIMARY KEY REFERENCES ledger(id),
        method      TEXT NOT NULL,
        args_hash   TEXT NOT NULL,          -- binds the handle to the exact approved call
        expires_at  TEXT,
        minted_at   TEXT NOT NULL,
        consumed_at TEXT                    -- set exactly once, on use; never cleared
    );
    CREATE TRIGGER handles_no_delete BEFORE DELETE ON handles
    BEGIN SELECT RAISE(ABORT, 'handles are append-only: no delete path'); END;
    CREATE TRIGGER handles_binding_frozen BEFORE UPDATE OF
        ledger_id, method, args_hash, expires_at, minted_at ON handles
    BEGIN SELECT RAISE(ABORT, 'a handle binding never rewrites'); END;
    CREATE TRIGGER handles_consume_once BEFORE UPDATE OF consumed_at ON handles
        WHEN OLD.consumed_at IS NOT NULL
    BEGIN SELECT RAISE(ABORT, 'a handle consumes exactly once'); END;

    CREATE TABLE events (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        ts      TEXT NOT NULL,
        kind    TEXT NOT NULL,              -- gate.pending, gate.approved, action.executed, ...
        actor   TEXT,
        subject TEXT,                       -- usually a ledger id
        payload TEXT                        -- JSON
    );
    CREATE INDEX events_kind ON events (kind);
    CREATE TRIGGER events_no_delete BEFORE DELETE ON events
    BEGIN SELECT RAISE(ABORT, 'the event log is append-only: no delete path'); END;
    CREATE TRIGGER events_no_update BEFORE UPDATE ON events
    BEGIN SELECT RAISE(ABORT, 'the event log is append-only: no rewrite'); END;
    """
]


class LedgerError(Exception):
    """A refused ledger operation."""


class AppendOnlyError(LedgerError):
    """A second fill, a rewrite, or any other append-only violation."""


class StateError(LedgerError):
    """A lifecycle move from the wrong state (resolve twice, execute unapproved, ...)."""


def ensure_schema(conn=None):
    """Create the ledger table-set if it doesn't exist. Returns the connection."""
    conn = conn or connect()
    migrate(conn, TABLE_SET, MIGRATIONS)
    return conn


def now(ts=None) -> str:
    """ISO-8601 UTC to the second. Pass a datetime (tests) or nothing (wall clock)."""
    if ts is None:
        ts = datetime.now(timezone.utc)
    if isinstance(ts, str):
        return ts
    return ts.astimezone(timezone.utc).isoformat(timespec="seconds")


def expired(expires_at: str | None, ts=None) -> bool:
    """Past the expiry? No expiry means no. Unparseable fails safe: expired."""
    if not expires_at:
        return False
    try:
        t = datetime.fromisoformat(expires_at)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    ref = ts if isinstance(ts, datetime) else (
        datetime.fromisoformat(ts) if isinstance(ts, str) else datetime.now(timezone.utc))
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    return ref > t


# ---------- the appends ----------

def mint(conn, rec: dict) -> str:
    """Append one record. Returns its id — minted here, at gate time; the
    idempotency key. A record is born pending or approved (the auto path);
    everything after is lifecycle, never a rewrite."""
    rid = rec.get("id") or str(uuid.uuid4())
    action_type = rec["action_type"]
    if action_type not in ACTION_TYPES:
        raise ValueError(f"unknown action_type: {action_type!r}")
    status = rec.get("status", "pending")
    if status not in ("pending", "approved"):
        raise ValueError("a record is born pending or approved; the rest is lifecycle")
    gate = rec.get("gate") or {"required": True, "decision": "pending", "by": None, "ts": None}
    want = "approved" if status == "approved" else "pending"
    if gate.get("decision") != want:
        raise ValueError(f"gate.decision must be {want!r} at birth, got {gate.get('decision')!r}")
    record = {
        "id": rid,
        "ts": now(rec.get("ts")),
        "agent": rec["agent"],
        "function": rec["function"],
        "action_type": action_type,
        "intent": rec.get("intent", ""),
        "rationale": rec.get("rationale", ""),
        "impact": rec.get("impact"),
        "provenance": rec.get("provenance") or {"unverified": True},  # cite, or say so
        "proposal": rec["proposal"],
        "status": status,
        "expires_at": rec.get("expires_at"),
        "gate": gate,
        "outcome": None,
    }
    conn.execute(
        "INSERT INTO ledger (id, ts, agent, function, action_type, intent, rationale,"
        " impact, provenance, proposal, status, expires_at, gate, outcome)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        (record["id"], record["ts"], record["agent"], record["function"],
         record["action_type"], record["intent"], record["rationale"],
         _j(record["impact"]), _j(record["provenance"]), _j(record["proposal"]),
         record["status"], record["expires_at"], _j(record["gate"])),
    )
    conn.commit()
    _mirror(conn, "mint", record)
    return rid


def emit_event(conn, kind: str, actor: str | None = None, subject: str | None = None,
               payload: dict | None = None, ts=None) -> int:
    """Append one line to the shared event log (the web surface's SSE feed)."""
    cur = conn.execute(
        "INSERT INTO events (ts, kind, actor, subject, payload) VALUES (?, ?, ?, ?, ?)",
        (now(ts), kind, actor, subject, _j(payload)),
    )
    conn.commit()
    return cur.lastrowid


# ---------- the lifecycle (each exactly once, one-way) ----------

def resolve_gate(conn, record_id: str, decision: str, by: str,
                 reason: str | None = None, ts=None) -> dict:
    """pending -> approved | rejected, exactly once. This is the raw flip;
    gate.resolve() is the only caller and the only approve path — never
    exposed on any agent-facing surface."""
    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be approved|rejected")
    if not by or not str(by).strip():
        raise ValueError("a resolution carries a name")
    rec = get(conn, record_id)
    if rec is None:
        raise KeyError(f"no ledger record {record_id}")
    if rec["status"] != "pending":
        raise StateError(f"gate already resolved: record is {rec['status']}")
    gate = {**rec["gate"], "decision": decision, "by": by, "ts": now(ts)}
    if reason:
        gate["reason"] = reason
    cur = conn.execute(
        "UPDATE ledger SET gate = ?, status = ? WHERE id = ? AND status = 'pending'",
        (_j(gate), decision, record_id),
    )
    if cur.rowcount == 0:
        conn.rollback()
        raise StateError("gate already resolved")
    conn.commit()
    _mirror(conn, "resolve", {"id": record_id, "gate": gate, "status": decision})
    return get(conn, record_id)


def begin_execution(conn, record_id: str, ts=None, commit: bool = True) -> None:
    """approved -> executing, exactly once — tied to consuming the handle
    (handles.validate_and_consume is the only caller)."""
    cur = conn.execute(
        "UPDATE ledger SET status = 'executing' WHERE id = ? AND status = 'approved'",
        (record_id,),
    )
    if cur.rowcount == 0:
        if commit:
            conn.rollback()
        raise StateError(f"record {record_id} is not approved; nothing to execute")
    if commit:
        conn.commit()
        _mirror(conn, "execute", {"id": record_id, "ts": now(ts)})


def fill_outcome(conn, record_id: str, outcome: dict, status: str, ts=None) -> dict:
    """The one-time outcome fill: executing -> executed | failed. A second
    fill is refused (AppendOnlyError), here and by trigger."""
    if status not in ("executed", "failed"):
        raise ValueError("outcome status must be executed|failed")
    rec = get(conn, record_id)
    if rec is None:
        raise KeyError(f"no ledger record {record_id}")
    if rec["outcome"] is not None:
        raise AppendOnlyError("the outcome fills exactly once; refused")
    if rec["status"] != "executing":
        raise StateError(f"outcome fills from executing, not {rec['status']}")
    filled = {**outcome, "ts": now(ts)}
    cur = conn.execute(
        "UPDATE ledger SET outcome = ?, status = ?"
        " WHERE id = ? AND status = 'executing' AND outcome IS NULL",
        (_j(filled), status, record_id),
    )
    if cur.rowcount == 0:
        conn.rollback()
        raise AppendOnlyError("the outcome fills exactly once; refused")
    conn.commit()
    _mirror(conn, "outcome", {"id": record_id, "outcome": filled, "status": status})
    return get(conn, record_id)


def expire(conn, record_id: str, ts=None) -> dict:
    """pending -> expired, one-way. An expired record is no longer
    approvable or executable; still wanted means re-proposed."""
    rec = get(conn, record_id)
    if rec is None:
        raise KeyError(f"no ledger record {record_id}")
    if rec["status"] != "pending":
        raise StateError(f"only pending expires; record is {rec['status']}")
    gate = {**rec["gate"], "decision": "expired", "by": "sweep", "ts": now(ts)}
    cur = conn.execute(
        "UPDATE ledger SET gate = ?, status = 'expired' WHERE id = ? AND status = 'pending'",
        (_j(gate), record_id),
    )
    if cur.rowcount == 0:
        conn.rollback()
        raise StateError("record moved while expiring")
    conn.commit()
    _mirror(conn, "expire", {"id": record_id, "ts": now(ts)})
    return get(conn, record_id)


# ---------- the queries ("why did X happen", in under a minute) ----------

def get(conn, record_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM ledger WHERE id = ?", (record_id,)).fetchone()
    return _record(row) if row else None


def query(conn, function: str | None = None, agent: str | None = None,
          status: str | None = None, day: str | None = None, limit: int = 100) -> list[dict]:
    """Records by function, agent, status, and/or day (YYYY-MM-DD), newest first."""
    where, params = [], []
    if function:
        where.append("function = ?"); params.append(function)
    if agent:
        where.append("agent = ?"); params.append(agent)
    if status:
        where.append("status = ?"); params.append(status)
    if day:
        where.append("substr(ts, 1, 10) = ?"); params.append(day)
    sql = "SELECT * FROM ledger"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY ts DESC, id LIMIT ?"
    params.append(int(limit))
    return [_record(r) for r in conn.execute(sql, params)]


def _pending_rows(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM ledger WHERE status = 'pending' ORDER BY ts, id")
    return [_record(r) for r in rows]


def pending_queue(conn, ts=None) -> list[dict]:
    """The approval queue: LIVE pending records only, oldest first, expiry
    visible. A pending row past its expiry is not a live wait — resolve()
    refuses it and the sweep flips it to expired — so it never shows here as
    approvable; lapsed_queue surfaces it separately."""
    return [r for r in _pending_rows(conn) if not expired(r["expires_at"], ts)]


def lapsed_queue(conn, ts=None) -> list[dict]:
    """Pending records past their expiry — lapsed, not live. Still status
    'pending' in the table until expire_sweep flips them, but no longer
    approvable; surfaced separately so no view renders them as live waits.
    Still wanted means re-proposed with current numbers."""
    return [r for r in _pending_rows(conn) if expired(r["expires_at"], ts)]


def events(conn, kind: str | None = None, since: str | None = None, limit: int = 200) -> list[dict]:
    where, params = [], []
    if kind:
        where.append("kind = ?"); params.append(kind)
    if since:
        where.append("ts >= ?"); params.append(since)
    sql = "SELECT * FROM events"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(int(limit))
    out = []
    for r in conn.execute(sql, params):
        e = dict(r)
        e["payload"] = json.loads(e["payload"]) if e["payload"] else None
        out.append(e)
    return out


def track_record(conn, function: str, ts=None) -> dict:
    """The per-function evidence card: proposals, approved, rejected,
    reversed (records whose proposal marks reverts:<id> — a reversal is its
    own recorded action), and time since the last gate resolve."""
    row = conn.execute(
        """
        SELECT COUNT(*) AS proposals,
               COALESCE(SUM(json_extract(gate, '$.decision') = 'approved'), 0) AS approved,
               COALESCE(SUM(json_extract(gate, '$.decision') = 'rejected'), 0) AS rejected,
               COALESCE(SUM(json_extract(proposal, '$.reverts') IS NOT NULL), 0) AS reversed,
               MAX(CASE WHEN json_extract(gate, '$.decision') IN ('approved', 'rejected')
                        THEN json_extract(gate, '$.ts') END) AS last_resolved_at
        FROM ledger WHERE function = ?
        """,
        (function,),
    ).fetchone()
    out = dict(row)
    last = out.get("last_resolved_at")
    if last:
        delta = None
        try:
            ref = datetime.fromisoformat(now(ts))
            delta = int((ref - datetime.fromisoformat(last)).total_seconds())
        except ValueError:
            pass
        out["seconds_since_last_resolve"] = delta
    else:
        out["seconds_since_last_resolve"] = None
    return out


# ---------- plumbing ----------

def _record(row) -> dict:
    r = dict(row)
    for k in ("impact", "provenance", "proposal", "gate", "outcome"):
        r[k] = json.loads(r[k]) if r[k] else None
    return r


def _j(obj) -> str | None:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True) if obj is not None else None


def mirror_path(conn) -> Path | None:
    """The jsonl audit mirror lives beside the DB file, named after it —
    <name>.db gets <name>.ledger.jsonl — so two stores never interleave
    what their databases keep apart (None for :memory:)."""
    row = conn.execute("PRAGMA database_list").fetchone()
    f = row["file"] if row else ""
    return Path(f).with_name(f"{Path(f).stem}.ledger.jsonl") if f else None


def _mirror(conn, op: str, obj: dict) -> None:
    """One line per operation, append-only by construction: open('a') only, ever."""
    p = mirror_path(conn)
    if p is None:
        return
    with open(p, "a") as f:
        f.write(json.dumps({"op": op, **obj}, separators=(",", ":"), sort_keys=True) + "\n")
