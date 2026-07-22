"""the watching tables — the watching part is their sole writer.

table-set "watching" (db.py law: one writer per table-set). two tables:

evaluations — one row per metric x dimension slice x period. re-running a
pass refreshes the row in place (the unique index below), so baselines
over "prior evaluations" count each period once. value NULL means no
number: stale=1 says the facts behind it were too old; stale=0 with NULL
says no data matched — neither pretends. drift_mode records which drift
detection governed the row (the 2026-07-18 ruling): "banded" once the
metric's own history suffices, "warming up (n of N)" until then; NULL
when there was no number to judge.

findings — first-class records, never deleted. evidence is JSON naming
evaluation ids and fact references; findings.mint() is the only door and
refuses an empty claim. disposition walks noticed -> routed -> decided ->
done, or ages out along the way.

the facts tables the engine reads (spine/schema.py) are read-only here —
the watching writes no facts.
"""

from commerceos.db import connect, migrate

TABLE_SET = "watching"

MIGRATIONS = [
    """
    CREATE TABLE evaluations (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        metric       TEXT NOT NULL,
        slice        TEXT NOT NULL DEFAULT '',  -- 'vendor=Acme' or '' for the whole store
        period       TEXT NOT NULL,             -- '2025-07' (month) or '2025-07-11' (day)
        value        REAL,                      -- NULL = no number (stale or no data)
        baseline     REAL,                      -- NULL = forming (window not filled yet)
        delta        REAL,                      -- (value - baseline) / baseline
        facts_window TEXT,                      -- JSON: what facts fed this number
        stale        INTEGER NOT NULL DEFAULT 0,
        ts           TEXT NOT NULL
    );
    CREATE UNIQUE INDEX evaluations_one_per_period
        ON evaluations (metric, slice, period);
    CREATE TABLE findings (
        id             TEXT PRIMARY KEY,
        metric         TEXT,                    -- the watch-list row that noticed it
        slice          TEXT NOT NULL DEFAULT '',
        sentence       TEXT NOT NULL,
        direction      TEXT NOT NULL
                       CHECK (direction IN ('risk','opportunity','insight')),
        evidence       TEXT NOT NULL,           -- JSON {evaluations: [...], facts: [...]}
        route          TEXT NOT NULL DEFAULT 'owner',
        disposition    TEXT NOT NULL DEFAULT 'noticed'
                       CHECK (disposition IN ('noticed','routed','decided','done','aged_out')),
        decided_reason TEXT,
        noticed_at     TEXT NOT NULL,
        updated_at     TEXT NOT NULL
    );
    CREATE INDEX findings_open ON findings (disposition, noticed_at);
    """,
    # the 2026-07-18 drift ruling: each evaluation records which drift
    # detection governed it — statistical bands or the warm-up percentage.
    """
    ALTER TABLE evaluations ADD COLUMN drift_mode TEXT;
    """,
]


def ensure_schema(conn=None):
    """Create the watching tables if they don't exist. Returns the connection."""
    conn = conn or connect()
    migrate(conn, TABLE_SET, MIGRATIONS)
    return conn
