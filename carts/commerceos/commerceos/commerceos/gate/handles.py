"""capability handles — the one key that writes the world.

part: the gate + the record (spec/parts/gate-and-record.md).

approval mints a one-use handle: a row keyed to the ledger id, bound to
the exact call by the args hash, carrying the record's expiry. the one
law at every connector: no valid handle, no write — consumed on use,
exactly once. a replay, a method swap, an args tweak, or a stale handle
is refused with the reason.

even an auto-approved reversible goes through validate_and_consume — one
code path for every write, so the connector never grows a second door.

v1 handles are rows in SQLite consumed transactionally, not loose JSON
files (v0's replay-tolerant files are deliberately not ported).
"""

from __future__ import annotations

from commerceos.gate import ledger, policy


def mint(conn, ledger_id: str, method: str, args_hash: str,
         expires_at: str | None = None, ts=None) -> dict:
    """Mint the one-use handle for an approved record. Called on approval
    (gate.resolve) and inline on the auto path (gate.submit) — never bare."""
    conn.execute(
        "INSERT INTO handles (ledger_id, method, args_hash, expires_at, minted_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (ledger_id, method, args_hash, expires_at, ledger.now(ts)),
    )
    conn.commit()
    ledger._mirror(conn, "handle_mint", {"id": ledger_id, "method": method,
                                         "args_hash": args_hash, "expires_at": expires_at})
    return get(conn, ledger_id)


def get(conn, ledger_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM handles WHERE ledger_id = ?", (ledger_id,)).fetchone()
    return dict(row) if row else None


def validate_and_consume(conn, ledger_id: str, method: str,
                         args: dict | None = None, ts=None) -> dict:
    """The connector's law, in one call: validate the handle against the
    exact call about to run, then consume it — transactionally, exactly
    once. Returns {"ok": bool, "reason": str, "ledger_id": str}; a refusal
    never raises, it just means no write.

    Checks, in order: the handle exists · unconsumed (a replay is refused) ·
    unexpired · method matches · args-hash matches (metadata stripped, so
    notes don't break the binding) · the record is approved. On success the
    record moves approved -> executing in the same transaction.
    """
    def refuse(reason: str) -> dict:
        return {"ok": False, "reason": reason, "ledger_id": ledger_id}

    h = get(conn, ledger_id)
    if h is None:
        return refuse("no handle for this record — approval mints it")
    if h["consumed_at"]:
        return refuse("handle already consumed — a replay is refused")
    if ledger.expired(h["expires_at"], ts):
        return refuse("handle expired — still wanted means re-proposed with current numbers")
    if h["method"] != method:
        return refuse(f"method mismatch — the handle is bound to {h['method']}, not {method}")
    if policy.args_hash(method, args) != h["args_hash"]:
        return refuse("args-hash mismatch — the handle binds the exact approved call")
    rec = ledger.get(conn, ledger_id)
    if rec is None or rec["status"] != "approved":
        return refuse(f"record is {rec['status'] if rec else 'missing'}, not approved")

    cur = conn.execute(
        "UPDATE handles SET consumed_at = ? WHERE ledger_id = ? AND consumed_at IS NULL",
        (ledger.now(ts), ledger_id),
    )
    if cur.rowcount == 0:
        conn.rollback()
        return refuse("handle already consumed — a replay is refused")
    try:
        ledger.begin_execution(conn, ledger_id, ts=ts, commit=False)
    except ledger.StateError:
        conn.rollback()
        return refuse("record moved while consuming; nothing executed")
    conn.commit()
    ledger._mirror(conn, "handle_consume", {"id": ledger_id, "ts": ledger.now(ts)})
    return {"ok": True, "reason": "consumed", "ledger_id": ledger_id}
