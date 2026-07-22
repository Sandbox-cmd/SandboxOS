"""the fleet's manifest reader — the agent files ARE the manifest.

RULED 2026-07-18 [owner]: each fleet agent is one markdown file in
`.claude/agents/`, and that file's YAML frontmatter ALONE is the source
of truth for scope, writer-class, and autonomy per function. the web
roster surface renders from the files; no duplicate config row anywhere.

the frontmatter schema — flat, strict, one line per value:

    ---
    name: catalog-proposer
    description: when to raise this agent (the workshop reads this too)
    scope: one plain sentence — what it works on
    writer_class: the one field-class it may write, in plain words
    status: built | building
    functions:
      - barcode-repair: acts
      - publish-state: parks
    ---
    plain prose about how the agent works. this body doubles as the
    agent's own instructions when the workshop raises it.

required keys: name (must match the filename), description, scope,
writer_class, status, functions. optional: tools (the workshop's tool
grant). each functions item is `- <function>: <autonomy>` where autonomy
is acts | parks | proposes-only.

no yaml library on purpose: pyyaml is not a dependency of this repo, and
this flat subset does not need one. a file outside the subset is refused
loudly — ManifestError names the file and the reason — never silently
skipped. the track record is computed from the ledger at render time,
never stored.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO / ".claude" / "agents"

REQUIRED = ("name", "description", "scope", "writer_class", "status", "functions")
OPTIONAL = ("tools",)
STATUSES = ("built", "building")
AUTONOMY = ("acts", "parks", "proposes-only")

_KEY = re.compile(r"^([a-z_]+):[ \t]*(.*)$")
_ITEM = re.compile(r"^[ \t]+-[ \t]*([A-Za-z0-9-]+):[ \t]*(\S.*)$")


class ManifestError(Exception):
    """a refused manifest file — malformed, incomplete, or dishonest."""


def read_manifest(path) -> dict:
    """parse one agent file. returns the manifest dict (frontmatter keys,
    functions as [{name, autonomy}], plus body and path). anything outside
    the strict flat subset is refused loudly, naming the file."""
    path = Path(path)

    def refuse(why: str):
        raise ManifestError(f"{path.name}: {why}")

    text = path.read_text()
    if not text.startswith("---\n"):
        refuse("no frontmatter fence at the top")
    try:
        fm, body = text[4:].split("\n---\n", 1)
    except ValueError:
        refuse("the frontmatter never closes (no second '---')")

    data: dict = {}
    in_functions = False
    for lineno, line in enumerate(fm.splitlines(), start=2):
        if not line.strip():
            continue
        item = _ITEM.match(line)
        if item:
            if not in_functions:
                refuse(f"line {lineno}: a list item outside 'functions:'")
            fname, auto = item.group(1), item.group(2).strip()
            if auto not in AUTONOMY:
                refuse(f"line {lineno}: autonomy {auto!r} is not one of "
                       f"{'|'.join(AUTONOMY)}")
            data["functions"].append({"name": fname, "autonomy": auto})
            continue
        kv = _KEY.match(line)
        if not kv:
            refuse(f"line {lineno}: not a 'key: value' line — this reader "
                   "is strict on purpose")
        key, value = kv.group(1), kv.group(2).strip()
        if key in data:
            refuse(f"line {lineno}: duplicate key {key!r}")
        if key not in REQUIRED and key not in OPTIONAL:
            refuse(f"line {lineno}: unknown key {key!r}")
        if key == "functions":
            if value:
                refuse("functions must be a list of '- name: autonomy' lines")
            data["functions"] = []
            in_functions = True
            continue
        in_functions = False
        if not value:
            refuse(f"line {lineno}: {key!r} has no value")
        data[key] = value

    missing = [k for k in REQUIRED if k not in data]
    if missing:
        refuse("missing required keys: " + ", ".join(missing))
    if data["status"] not in STATUSES:
        refuse(f"status {data['status']!r} is not one of {'|'.join(STATUSES)}")
    if not data["functions"]:
        refuse("functions lists no function")
    if data["name"] != path.stem:
        refuse(f"name {data['name']!r} does not match the filename")
    data["body"] = body.strip()
    data["path"] = str(path)
    return data


def roster(dir=None) -> list[dict]:
    """every agent manifest in the directory, sorted by name. a malformed
    file raises ManifestError (named, never skipped); the README is the
    one non-agent file that lives there."""
    d = Path(dir) if dir else AGENTS_DIR
    files = sorted(p for p in d.glob("*.md") if p.name != "README.md")
    return [read_manifest(p) for p in files]


def track_record(conn, agent: str) -> dict:
    """the agent's evidence card, computed from the ledger at render time —
    proposals made / approved / executed / rejected / reversed (a record
    whose proposal marks reverts:<id> — undone AFTER execution, the number
    autonomy widening rests on), plus the live waits (pending, unexpired)
    and the lapsed ones (pending past expiry — no longer approvable).
    never stored: the ledger rows carry the agent name; this is just the
    count."""
    from commerceos.gate import ledger as _ledger

    row = conn.execute(
        """
        SELECT COUNT(*) AS proposals,
               COALESCE(SUM(json_extract(gate, '$.decision') = 'approved'), 0) AS approved,
               COALESCE(SUM(status = 'executed'), 0) AS executed,
               COALESCE(SUM(json_extract(gate, '$.decision') = 'rejected'), 0) AS rejected,
               COALESCE(SUM(json_extract(proposal, '$.reverts') IS NOT NULL), 0) AS reversed
        FROM ledger WHERE agent = ?
        """,
        (agent,),
    ).fetchone()
    out = dict(row)
    waits = conn.execute(
        "SELECT expires_at FROM ledger WHERE agent = ? AND status = 'pending'",
        (agent,),
    ).fetchall()
    lapsed = sum(1 for w in waits if _ledger.expired(w["expires_at"]))
    out["pending"] = len(waits) - lapsed
    out["lapsed"] = lapsed
    return out
