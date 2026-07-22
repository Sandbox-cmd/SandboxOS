"""the part registry — the no-blackbox contract.

two tables (table-set "registry"): parts + part_config. each part is the
only writer of its own row, through report() here. track record is never
self-reported — the web surface computes it from the gate's ledger, so a
part never grades itself. a silent part renders stale, never vanishes.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from commerceos.db import migrate

TABLE_SET = "registry"

MIGRATIONS = [
    """
    CREATE TABLE parts (
        part        TEXT PRIMARY KEY,
        is_         TEXT NOT NULL,
        state       TEXT NOT NULL DEFAULT 'idle',
        functions   TEXT NOT NULL DEFAULT '[]',
        last_run    TEXT,
        next_run    TEXT,
        reported_at TEXT NOT NULL
    );
    CREATE TABLE part_config (
        part      TEXT NOT NULL,
        key       TEXT NOT NULL,
        value     TEXT,
        kind      TEXT NOT NULL DEFAULT 'str',
        safe_edit INTEGER NOT NULL DEFAULT 0,
        note      TEXT,
        PRIMARY KEY (part, key)
    );
    """
]


def ensure_schema(conn: sqlite3.Connection) -> sqlite3.Connection:
    migrate(conn, TABLE_SET, MIGRATIONS)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def report(
    conn: sqlite3.Connection,
    part: str,
    is_: str,
    state: str = "idle",
    functions: list[str] | None = None,
    last_run: dict | None = None,
    next_run: str | None = None,
) -> None:
    """upsert this part's row. registration on startup, refresh after runs."""
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO parts (part, is_, state, functions, last_run, next_run, reported_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(part) DO UPDATE SET is_=excluded.is_, state=excluded.state,"
        " functions=excluded.functions, last_run=excluded.last_run,"
        " next_run=excluded.next_run, reported_at=excluded.reported_at",
        (
            part,
            is_,
            state,
            json.dumps(functions or []),
            json.dumps(last_run) if last_run else None,
            next_run,
            _now(),
        ),
    )
    conn.commit()


def seed_config(conn: sqlite3.Connection, part: str, rows: list[dict]) -> None:
    """insert-if-missing config rows: {key, value, kind, safe_edit, note}."""
    ensure_schema(conn)
    for r in rows:
        conn.execute(
            "INSERT OR IGNORE INTO part_config (part, key, value, kind, safe_edit, note)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (part, r["key"], str(r.get("value", "")), r.get("kind", "str"),
             int(r.get("safe_edit", 0)), r.get("note")),
        )
    conn.commit()


def all_parts(conn: sqlite3.Connection) -> list[dict]:
    ensure_schema(conn)
    out = []
    for row in conn.execute("SELECT * FROM parts ORDER BY part"):
        d = dict(row)
        d["functions"] = json.loads(d["functions"])
        d["last_run"] = json.loads(d["last_run"]) if d["last_run"] else None
        out.append(d)
    return out


def config_for(conn: sqlite3.Connection, part: str) -> list[dict]:
    ensure_schema(conn)
    return [dict(r) for r in conn.execute(
        "SELECT * FROM part_config WHERE part = ? ORDER BY key", (part,))]
