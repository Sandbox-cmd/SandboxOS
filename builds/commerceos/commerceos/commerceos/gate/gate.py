"""the gate — one wall. decides what runs now and what waits for the owner.

part: the gate + the record (spec/parts/gate-and-record.md, serves O2/O4).

the agent-facing surface is submit() and nothing else. there is NO approve
verb on it — v0's hard invariant re-keyed: headless cannot approve its own
action. resolve() is the system's only approve path and belongs to the web
surface (part 7); it is never wired into any agent-facing API.

the seven behaviors (spec ## behavior):
  1. reversible pass-through   -> submit(): approved record, handle minted
     and consumed in one motion, status executing; caller writes, then
     report_outcome(). never silent.
  2. consequential park        -> submit(): pending record with an expiry,
     into the queue, event emitted. the agent files and moves on.
  3. approve -> mint -> execute -> resolve(approved) mints the one-use
     handle; the executor runs the exact stored proposal through
     handles.validate_and_consume, writes, fills the outcome.
  4. reject                    -> resolve(rejected): reason on the record,
     nothing executes.
  5. expiry                    -> expire_sweep() / a lapsed resolve():
     pending past expires_at reads expired — no longer approvable.
  6. threshold move            -> move_threshold(): owner-only, and itself
     a recorded action on this same ledger (old, new, by whom, why).
  7. anti-bypass wall          -> check_grant(): this part ships the check;
     the fleet (part 4) enforces it at wiring time.
"""

from __future__ import annotations

import json
from pathlib import Path

from commerceos.gate import handles, ledger, policy

# pending approvals lapse rather than fire on changed conditions.
# config per store (policy-table.json expiry_seconds); these are the defaults.
DEFAULT_EXPIRY_SECONDS = 3600   # one hour
MONEY_EXPIRY_SECONDS = 1800     # money moves wait half as long

# tools that are never grantable to an agent, gated or not.
NEVER_GRANTABLE = {"Bash"}


def submit(conn, proposal: dict, table: dict | None = None, now_ts=None,
           hold: bool = False) -> dict:
    """The gate check API — the only agent-facing verb. A proposal either
    runs now (reversible / under-threshold: allow) or parks pending. It is
    never approved here, and the proposing agent cannot resolve its own
    gate — it files and moves on.

    proposal: agent, function, method, args, and the why — declared_type,
    intent, rationale, impact, provenance (cite or it lands unverified).

    hold=True (WF-approve, RULED: every front has an approval step) makes
    even an auto-lane proposal PARK pending — the batch-approve loop stages
    a preview and a person lands it; nothing auto-lands on a held submit.
    The parked record is ordinary: same expiry, same resolve path, so the
    approval that follows is honestly a person's, never policy:auto.
    """
    table = table or policy.load_table()
    agent, function, method = proposal["agent"], proposal["function"], proposal["method"]
    args = proposal.get("args") or {}
    declared = proposal.get("declared_type")

    # reads are free — no record, no gate. provenance lives on the read.
    if policy.is_read(method, table):
        return {"decision": "allow", "record_id": None, "action_type": policy.REVERSIBLE,
                "flag": None, "status": None, "reason": f"read ({method}) — free path"}

    action_type, flag = policy.classify(method, args, declared, table)
    ahash = policy.args_hash(method, args)
    verdict = policy.decide(function, action_type, method, args, table)
    tsnow = ledger.now(now_ts)
    base = {
        "agent": agent, "function": function, "action_type": action_type,
        "intent": proposal.get("intent", ""), "rationale": proposal.get("rationale", ""),
        "impact": proposal.get("impact"), "provenance": proposal.get("provenance"),
        "proposal": {"connector": proposal.get("connector", "commerce"), "method": method,
                     "args": args, "args_hash": ahash, "declared_type": declared},
        "ts": tsnow,
    }

    if verdict == "auto" and not hold:
        # behavior 1: approved record, handle minted and consumed in one
        # motion — the same code path every connector uses, so even the
        # auto lane never writes without a consumed handle.
        gate_json = {"required": False, "decision": "approved", "by": "policy:auto", "ts": tsnow}
        if flag:
            gate_json["flag"] = flag
        rid = ledger.mint(conn, {**base, "status": "approved", "gate": gate_json})
        handles.mint(conn, rid, method, ahash, expires_at=None, ts=now_ts)
        took = handles.validate_and_consume(conn, rid, method, args, ts=now_ts)
        if not took["ok"]:  # pragma: no cover - construction bug, not a flow
            raise RuntimeError(f"auto path failed to consume its own handle: {took['reason']}")
        ledger.emit_event(conn, "gate.auto_approved", actor=agent, subject=rid,
                          payload={"function": function, "method": method,
                                   "action_type": action_type}, ts=now_ts)
        return {"decision": "allow", "record_id": rid, "action_type": action_type,
                "flag": flag, "status": "executing",
                "reason": f"{action_type} ({method}) — auto-approved, recorded {rid[:8]}"}

    # behavior 2: park pending with an expiry, into the queue.
    expires_at = _expiry(table, method, tsnow)
    gate_json = {"required": True, "decision": "pending", "by": None, "ts": None}
    if flag:
        gate_json["flag"] = flag
    rid = ledger.mint(conn, {**base, "status": "pending",
                             "expires_at": expires_at, "gate": gate_json})
    ledger.emit_event(conn, "gate.pending", actor=agent, subject=rid,
                      payload={"function": function, "method": method,
                               "action_type": action_type, "expires_at": expires_at,
                               "flag": flag}, ts=now_ts)
    return {"decision": "parked", "record_id": rid, "action_type": action_type,
            "flag": flag, "status": "pending", "expires_at": expires_at,
            "reason": f"{action_type} ({method}) — parked pending approval, "
                      f"expires {expires_at}"}


def resolve(conn, record_id: str, decision: str, by: str,
            reason: str | None = None, now_ts=None) -> dict:
    """The system's ONLY approve path. Called by the web surface (part 7)
    on the owner's keypress — never exposed on any agent-facing API.

    approved -> mints the one-use handle (behavior 3); the executor then
    runs the exact stored proposal through handles.validate_and_consume.
    rejected -> reason on the record, nothing executes (behavior 4).
    pending past its expiry cannot be resolved: it flips to expired and the
    resolve is refused (behavior 5).
    """
    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be approved|rejected")
    rec = ledger.get(conn, record_id)
    if rec is None:
        raise KeyError(f"no ledger record {record_id}")
    if rec["status"] == "pending" and ledger.expired(rec["expires_at"], now_ts):
        ledger.expire(conn, record_id, ts=now_ts)
        ledger.emit_event(conn, "gate.expired", actor="sweep", subject=record_id,
                          payload={"function": rec["function"]}, ts=now_ts)
        raise ledger.StateError(
            "approval window lapsed — the record reads expired; "
            "still wanted means re-proposed with current numbers")
    rec = ledger.resolve_gate(conn, record_id, decision, by, reason=reason, ts=now_ts)
    if decision == "approved":
        prop = rec["proposal"]
        handles.mint(conn, record_id, prop["method"], prop["args_hash"],
                     expires_at=rec["expires_at"], ts=now_ts)
    ledger.emit_event(conn, f"gate.{decision}", actor=by, subject=record_id,
                      payload={"function": rec["function"], "reason": reason}, ts=now_ts)
    return rec


def report_outcome(conn, record_id: str, outcome: dict,
                   status: str = "executed", now_ts=None) -> dict:
    """The connector reports what the world said: the one-time outcome fill
    plus the event. status is executed or failed."""
    rec = ledger.fill_outcome(conn, record_id, outcome, status, ts=now_ts)
    ledger.emit_event(conn, f"action.{status}", actor=rec["agent"], subject=record_id,
                      payload={"function": rec["function"]}, ts=now_ts)
    return rec


def expire_sweep(conn, now_ts=None) -> list[str]:
    """Flip every pending record past its expiry to expired (behavior 5).
    Returns the ids swept. An expired record is no longer approvable."""
    swept = []
    for rec in ledger.lapsed_queue(conn, now_ts):
        ledger.expire(conn, rec["id"], ts=now_ts)
        ledger.emit_event(conn, "gate.expired", actor="sweep", subject=rec["id"],
                          payload={"function": rec["function"]}, ts=now_ts)
        swept.append(rec["id"])
    return swept


def move_threshold(conn, function: str, key: str, value, by: str, why: str,
                   table_path: Path | str | None = None, now_ts=None) -> dict:
    """Behavior 6: move a policy-table value — owner-only, never silent.

    The move is itself a recorded action on this same ledger: old value,
    new value, by whom, why — and it goes through the same mint-a-handle,
    consume-a-handle motion as every other write. Movable keys:
    money_threshold (minor units, >= 0) and auto_approve (classes;
    fit_critical is never auto-approvable, whatever anyone asks)."""
    if not by or not str(by).strip():
        raise ValueError("owner-only: the move carries a name")
    if not why or not str(why).strip():
        raise ValueError("never silent: the move carries its why")
    path = Path(table_path) if table_path else policy.table_path()
    table = json.loads(path.read_text())
    functions = table.get("functions", {})
    if function not in functions:
        raise ValueError(f"unknown function: {function!r}")
    if key == "money_threshold":
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("money_threshold is minor units: an integer >= 0")
    elif key == "auto_approve":
        if (not isinstance(value, list)
                or any(c not in policy.ORDER for c in value)
                or policy.FIT_CRITICAL in value):
            raise ValueError("auto_approve lists classes; fit_critical is always human-gated")
    else:
        raise ValueError(f"not a movable key: {key!r}")

    old = functions[function].get(key)
    method = "policy.move_threshold"
    args = {"function": function, "key": key, "old": old, "new": value}
    ahash = policy.args_hash(method, args)
    tsnow = ledger.now(now_ts)
    rid = ledger.mint(conn, {
        "agent": by, "function": "policy", "action_type": policy.CONSEQUENTIAL,
        "intent": f"move {function}.{key}: {old} -> {value}", "rationale": why,
        "impact": {"scope": "policy-table", "function": function, "key": key},
        "provenance": {"cite": str(path)},
        "proposal": {"connector": "policy", "method": method,
                     "args": args, "args_hash": ahash, "declared_type": None},
        "status": "approved",
        "gate": {"required": True, "decision": "approved", "by": by, "ts": tsnow},
        "ts": tsnow,
    })
    handles.mint(conn, rid, method, ahash, expires_at=None, ts=now_ts)
    took = handles.validate_and_consume(conn, rid, method, args, ts=now_ts)
    if not took["ok"]:  # pragma: no cover - construction bug, not a flow
        raise RuntimeError(f"threshold move failed to consume its handle: {took['reason']}")
    functions[function][key] = value
    path.write_text(json.dumps(table, indent=2) + "\n")
    ledger.fill_outcome(conn, rid, {"ok": True, "old": old, "new": value,
                                    "path": str(path)}, "executed", ts=now_ts)
    ledger.emit_event(conn, "policy.threshold_moved", actor=by, subject=rid,
                      payload=args, ts=now_ts)
    return ledger.get(conn, rid)


def check_grant(granted, gated_tools=(), read_tools=()) -> list[str]:
    """Behavior 7, the anti-bypass wall: the gate holds only if the gated
    connectors are the only write path in an agent's hands. This part ships
    the check; the fleet (part 4) enforces it at wiring time.

    Returns the violations — every granted tool that is neither a gated
    connector tool nor a read. Raw Bash is never grantable, even if someone
    lists it as gated (v0's red team walked straight through that door)."""
    allowed = (set(gated_tools) | set(read_tools)) - NEVER_GRANTABLE
    return sorted(t for t in granted if t not in allowed)


def _expiry(table: dict, method: str, tsnow: str) -> str:
    from datetime import datetime, timedelta
    cfg = table.get("expiry_seconds") or {}
    money = bool(table.get("methods", {}).get(method, {}).get("_money"))
    seconds = cfg.get("money", MONEY_EXPIRY_SECONDS) if money \
        else cfg.get("default", DEFAULT_EXPIRY_SECONDS)
    return ledger.now(datetime.fromisoformat(tsnow) + timedelta(seconds=int(seconds)))
