"""one SQLite database, one writer per table-set.

table-sets and their sole writers (spec/parts/data-spine.md):
  facts            -> the spine
  canonical record -> the catalog loop
  ledger + events  -> the gate + record part
  registry         -> each part its own row, via the web helper

each part registers its migrations under its own table-set name; this
module runs them and remembers what ran. re-running is a no-op.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from commerceos import stores


def default_path() -> Path:
    """The active store's database, resolved at call time (COMMERCEOS_DB wins first)."""
    return stores.resolve(stores.active_store(), stores.DB)


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """Open the database with the pragmas every part relies on."""
    p = Path(path) if path else default_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p, check_same_thread=False)  # per-request conns cross FastAPI's threadpool/event-loop seam
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _migrations ("
        " table_set TEXT NOT NULL, version INTEGER NOT NULL,"
        " applied_at TEXT NOT NULL DEFAULT (datetime('now')),"
        " PRIMARY KEY (table_set, version))"
    )
    return conn


def migrate(conn: sqlite3.Connection, table_set: str, migrations: list[str]) -> int:
    """Apply the table-set's numbered migrations that haven't run yet.

    Returns how many ran. Numbering is positional (index = version).
    """
    done = {
        row["version"]
        for row in conn.execute(
            "SELECT version FROM _migrations WHERE table_set = ?", (table_set,)
        )
    }
    ran = 0
    for version, ddl in enumerate(migrations):
        if version in done:
            continue
        conn.executescript(ddl)
        conn.execute(
            "INSERT INTO _migrations (table_set, version) VALUES (?, ?)",
            (table_set, version),
        )
        ran += 1
    conn.commit()
    return ran
