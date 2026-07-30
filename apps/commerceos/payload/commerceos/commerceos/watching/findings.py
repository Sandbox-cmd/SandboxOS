"""findings — first-class records of what the watching noticed.

the law (spec/parts/watching.md): no provenance, no finding — a claim
naming no evaluation or fact ids is refused at the door. every finding
carries a direction (risk | opportunity | insight), a suggested route,
and a disposition that walks noticed -> routed -> decided -> done, or
ages out. aged-out findings are marked, never deleted — an ignored
opportunity stays visible as ignored.

mint() is the only write door; the engine and the analyst agent both
come through it. the watching never acts on a finding — anything
consequential the route wants goes through the gate.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from commerceos.watching.schema import ensure_schema

DIRECTIONS = ("risk", "opportunity", "insight")
OPEN_DISPOSITIONS = ("noticed", "routed")

# the lifecycle, as a map: from-state -> the states it may move to.
TRANSITIONS = {
    "noticed": {"routed", "decided", "aged_out"},
    "routed": {"decided", "aged_out"},
    "decided": {"done"},
    "done": set(),
    "aged_out": set(),
}

# aging limits, days, per direction — overridable from the watch-list
# (age_out_days). a stale opening is gone faster than a stale risk bites.
DEFAULT_AGE_OUT_DAYS = {"risk": 30, "opportunity": 14, "insight": 14}


def _ts(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")


def _parse_ts(text: str) -> datetime:
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _clean_evidence(evidence) -> dict:
    """Validate evidence; raise ValueError if it names nothing."""
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a dict of {evaluations, facts}")
    evaluations = list(evidence.get("evaluations") or [])
    facts = list(evidence.get("facts") or [])
    if not evaluations and not facts:
        raise ValueError(
            "no provenance, no finding: a claim naming no evaluation or fact ids is refused"
        )
    return {"evaluations": evaluations, "facts": facts}


def mint(
    conn: sqlite3.Connection,
    sentence: str,
    direction: str,
    evidence: dict,
    route: str = "owner",
    metric: str | None = None,
    slice_: str = "",
    now: datetime | None = None,
) -> str:
    """Write a new finding. Refuses empty sentences, unknown directions,
    and — the law — evidence that names no evaluation or fact ids."""
    ensure_schema(conn)
    if not sentence or not sentence.strip():
        raise ValueError("a finding is one plain sentence — an empty one is refused")
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}, not {direction!r}")
    clean = _clean_evidence(evidence)
    fid = str(uuid.uuid4())
    ts = _ts(now)
    conn.execute(
        "INSERT INTO findings (id, metric, slice, sentence, direction, evidence,"
        " route, disposition, decided_reason, noticed_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, 'noticed', NULL, ?, ?)",
        (fid, metric, slice_, sentence.strip(), direction, json.dumps(clean), route, ts, ts),
    )
    conn.commit()
    return fid


def refresh(
    conn: sqlite3.Connection,
    finding_id: str,
    evidence: dict,
    sentence: str | None = None,
    now: datetime | None = None,
) -> None:
    """A persisting breach refreshes the open finding — merged evidence,
    fresh sentence, updated_at moved. noticed_at stays: age keeps counting."""
    row = get(conn, finding_id)
    if row is None:
        raise ValueError(f"no finding {finding_id}")
    if row["disposition"] not in OPEN_DISPOSITIONS:
        raise ValueError(f"finding {finding_id} is {row['disposition']} — refresh only touches open findings")
    incoming = _clean_evidence(evidence)
    merged = dict(row["evidence"])
    for key in ("evaluations", "facts"):
        seen = list(merged.get(key) or [])
        for ref in incoming[key]:
            if ref not in seen:
                seen.append(ref)
        merged[key] = seen
    conn.execute(
        "UPDATE findings SET evidence = ?, sentence = COALESCE(?, sentence), updated_at = ?"
        " WHERE id = ?",
        (json.dumps(merged), sentence, _ts(now), finding_id),
    )
    conn.commit()


def transition(
    conn: sqlite3.Connection,
    finding_id: str,
    to: str,
    reason: str | None = None,
    now: datetime | None = None,
) -> None:
    """Move a finding along its lifecycle; anything off the map is refused."""
    row = get(conn, finding_id)
    if row is None:
        raise ValueError(f"no finding {finding_id}")
    allowed = TRANSITIONS[row["disposition"]]
    if to not in allowed:
        raise ValueError(
            f"a {row['disposition']} finding cannot become {to!r}"
            f" (allowed: {sorted(allowed) or 'none — terminal'})"
        )
    if to == "decided" and not (reason and reason.strip()):
        raise ValueError("a decision carries its reason — acted or dismissed, and why")
    conn.execute(
        "UPDATE findings SET disposition = ?, decided_reason = COALESCE(?, decided_reason),"
        " updated_at = ? WHERE id = ?",
        (to, reason, _ts(now), finding_id),
    )
    conn.commit()


def route_to(conn: sqlite3.Connection, finding_id: str, route: str, now: datetime | None = None) -> None:
    """noticed -> routed, and the route recorded (a named agent or the owner)."""
    transition(conn, finding_id, "routed", now=now)
    conn.execute("UPDATE findings SET route = ? WHERE id = ?", (route, finding_id))
    conn.commit()


def decide(conn: sqlite3.Connection, finding_id: str, reason: str, now: datetime | None = None) -> None:
    transition(conn, finding_id, "decided", reason=reason, now=now)


def complete(conn: sqlite3.Connection, finding_id: str, now: datetime | None = None) -> None:
    transition(conn, finding_id, "done", now=now)


def age_days(row: dict, now: datetime | None = None) -> float:
    """Age since noticed, in days — shown everywhere a finding appears."""
    ref = now or datetime.now(timezone.utc)
    return (ref - _parse_ts(row["noticed_at"])).total_seconds() / 86400.0


def age_out(
    conn: sqlite3.Connection,
    limits: dict | None = None,
    now: datetime | None = None,
) -> int:
    """Mark open findings past their direction's limit aged_out. Never deletes.
    Returns how many aged out this pass."""
    ensure_schema(conn)
    limits = {**DEFAULT_AGE_OUT_DAYS, **(limits or {})}
    ref = now or datetime.now(timezone.utc)
    ts = _ts(now)
    aged = 0
    for row in conn.execute(
        "SELECT id, direction, noticed_at FROM findings WHERE disposition IN (?, ?)",
        OPEN_DISPOSITIONS,
    ).fetchall():
        limit = float(limits.get(row["direction"], DEFAULT_AGE_OUT_DAYS[row["direction"]]))
        if (ref - _parse_ts(row["noticed_at"])).total_seconds() / 86400.0 > limit:
            conn.execute(
                "UPDATE findings SET disposition = 'aged_out', updated_at = ? WHERE id = ?",
                (ts, row["id"]),
            )
            aged += 1
    conn.commit()
    return aged


def _to_dict(row: sqlite3.Row, now: datetime | None = None) -> dict:
    d = dict(row)
    d["evidence"] = json.loads(d["evidence"])
    d["age_days"] = age_days(d, now)
    return d


def get(conn: sqlite3.Connection, finding_id: str, now: datetime | None = None) -> dict | None:
    ensure_schema(conn)
    row = conn.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
    return _to_dict(row, now) if row else None


def open_finding_for(
    conn: sqlite3.Connection, metric: str, slice_: str, direction: str
) -> dict | None:
    """The dedup lookup: the open finding this metric+slice+direction already has."""
    ensure_schema(conn)
    row = conn.execute(
        "SELECT * FROM findings WHERE metric = ? AND slice = ? AND direction = ?"
        " AND disposition IN (?, ?) ORDER BY noticed_at LIMIT 1",
        (metric, slice_, direction, *OPEN_DISPOSITIONS),
    ).fetchone()
    return _to_dict(row) if row else None


def open_findings(
    conn: sqlite3.Connection, direction: str | None = None, now: datetime | None = None
) -> list[dict]:
    """The brief's flag feed: open findings, both directions, oldest-aging first."""
    ensure_schema(conn)
    sql = "SELECT * FROM findings WHERE disposition IN (?, ?)"
    args: list = list(OPEN_DISPOSITIONS)
    if direction:
        sql += " AND direction = ?"
        args.append(direction)
    sql += " ORDER BY noticed_at"
    return [_to_dict(r, now) for r in conn.execute(sql, args)]


def query(
    conn: sqlite3.Connection,
    direction: str | None = None,
    disposition: str | None = None,
    metric: str | None = None,
    limit: int = 200,
    now: datetime | None = None,
) -> list[dict]:
    """The findings page: everything, filterable by direction, area, status."""
    ensure_schema(conn)
    sql, args = "SELECT * FROM findings WHERE 1=1", []
    for column, value in (("direction", direction), ("disposition", disposition), ("metric", metric)):
        if value:
            sql += f" AND {column} = ?"
            args.append(value)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    args.append(limit)
    return [_to_dict(r, now) for r in conn.execute(sql, args)]


def direction_mix(conn: sqlite3.Connection) -> dict:
    """direction x disposition counts — the health of the watching itself."""
    ensure_schema(conn)
    return {
        f"{r['direction']}/{r['disposition']}": r["c"]
        for r in conn.execute(
            "SELECT direction, disposition, count(*) c FROM findings"
            " GROUP BY direction, disposition"
        )
    }
