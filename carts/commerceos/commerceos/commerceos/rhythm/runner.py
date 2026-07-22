"""the standing rhythm's runner — one tick, every due job, honest outcomes.

the rhythm orchestrates; it never reimplements. each job calls a part's
public function. which jobs run, and in what order, is the job registry
(spec/parts/fleet.md behavior 1): the store's rhythm.json job rows —
name, what it calls ("calls", defaulting to the built-in of the row's
own name), cadence, enabled — run in row order, expire_sweep first if
present. a per-agent job joins by adding a row, no code edit. one job's
failure never stops the others; every outcome lands in the rhythm's own
state table (table-set "rhythm") and the parts' registry rows are
refreshed after every tick.

nothing arms itself (spec/build.md standing constraints): a tick runs
only because the owner armed the schedule (arm.py --yes) or typed it
himself. every job ships disabled in stores/<store>/rhythm.json; the
launchd tick fires every 15 minutes and each job gates itself by its
own cadence here.

  uv run python -m commerceos.rhythm.runner tick        # run every due job
  uv run python -m commerceos.rhythm.runner run <job>   # one-off manual run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from commerceos import stores
from commerceos.db import connect, migrate
from commerceos.gate import ledger
from commerceos.rhythm import notify
from commerceos.catalog.status import report_status as catalog_report
from commerceos.gate.status import report_status as gate_report
from commerceos.spine.status import report_status as spine_report
from commerceos.watching.status import report_status as watching_report

REPO = Path(__file__).resolve().parents[2]


def default_config_path() -> Path:
    return stores.resolve(stores.active_store(), "rhythm.json")


TABLE_SET = "rhythm"

MIGRATIONS = [
    """
    CREATE TABLE rhythm_state (
        job         TEXT PRIMARY KEY,   -- a job name, or 'tick' for the tick itself
        last_run    TEXT NOT NULL,
        ok          INTEGER NOT NULL,
        summary     TEXT,
        error       TEXT,
        duration_ms INTEGER
    );
    """
]

_CADENCE_RE = re.compile(r"^(\d+)\s*([mhd])$")
_UNIT_SECONDS = {"m": 60, "h": 3600, "d": 86400}


# ---------- config + due math ----------

def load_config(path: Path | str | None = None) -> dict:
    return json.loads(Path(path or default_config_path()).read_text())


def job_configs(cfg: dict) -> dict:
    """the job rows, minus doc keys."""
    return {k: v for k, v in (cfg.get("jobs") or {}).items()
            if not k.startswith("_") and isinstance(v, dict)}


def parse_cadence(text) -> int:
    """'15m' | '6h' | '2d' -> seconds. anything else is refused."""
    m = _CADENCE_RE.match(str(text).strip().lower())
    if not m or int(m.group(1)) < 1:
        raise ValueError(f"a cadence reads like '15m', '6h' or '2d' — got {text!r}")
    return int(m.group(1)) * _UNIT_SECONDS[m.group(2)]


def _parse_ts(text: str) -> datetime:
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def is_due(last_run: str | None, cadence_seconds: int, now: datetime) -> bool:
    """never ran -> due. else due when a full cadence has passed."""
    if not last_run:
        return True
    return (now - _parse_ts(last_run)).total_seconds() >= cadence_seconds


def next_due(last_run: str | None, cadence_seconds: int) -> str | None:
    """the ISO moment the job comes due — None means due now (never ran)."""
    if not last_run:
        return None
    return (_parse_ts(last_run) + timedelta(seconds=cadence_seconds)).isoformat(
        timespec="seconds")


# ---------- the rhythm's own state (table-set "rhythm") ----------

def ensure_schema(conn):
    migrate(conn, TABLE_SET, MIGRATIONS)
    return conn


def state_rows(conn) -> dict:
    ensure_schema(conn)
    return {r["job"]: dict(r) for r in conn.execute("SELECT * FROM rhythm_state")}


def record_run(conn, job: str, ts_iso: str, ok: bool, summary: str | None = None,
               error: str | None = None, duration_ms: int | None = None) -> None:
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO rhythm_state (job, last_run, ok, summary, error, duration_ms)"
        " VALUES (?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(job) DO UPDATE SET last_run=excluded.last_run, ok=excluded.ok,"
        " summary=excluded.summary, error=excluded.error,"
        " duration_ms=excluded.duration_ms",
        (job, ts_iso, int(bool(ok)), summary, error, duration_ms),
    )
    conn.commit()


# ---------- the jobs: each one a part's public function, never a rewrite ----------
#
# every job takes (conn, jcfg): jcfg is its own row from the config the
# TICK was given — no job may call load_config() or read the default
# path itself, or a tick pointed at one store leaks another store's
# config into the work.

def _job_expire_sweep(conn, jcfg: dict) -> dict:
    from commerceos.gate import gate
    ledger.ensure_schema(conn)
    swept = gate.expire_sweep(conn)
    return {"summary": f"{len(swept)} pending flipped to expired" if swept
            else "nothing past expiry"}


def _job_sync(conn, jcfg: dict) -> dict:
    from commerceos.spine import connector_shopify
    from commerceos.spine.schema import ensure_schema as ensure_facts
    ensure_facts(conn)
    p = connector_shopify.sync_products(conn)
    o = connector_shopify.sync_orders(conn)
    return {"summary": f"landed {p.get('products', 0)} products · "
                       f"{p.get('variants', 0)} variants · {o.get('orders', 0)} orders · "
                       f"{o.get('lines', 0)} lines"}


def _job_propose(conn, jcfg: dict) -> dict:
    """the workers\' standing turn: bounded delegated batches through the
    gate. reversible acts execute with verify-rendered receipts; anything
    consequential parks for the owner. kind and batch size come from the
    row this job was given — its own config, never a re-read of the
    default path."""
    from commerceos.fleet import proposer

    kind = jcfg.get("kind", "gtin_normalize")
    limit = int(jcfg.get("batch", 50))
    res = proposer.propose_and_run(conn, kind, limit=limit)
    return {"ok": res["failed"] == 0,
            "summary": (f"{kind}: {res['executed']} executed, "
                        f"{res['parked']} parked, {res['failed']} failed "
                        f"of {res['computed']} computed")}


def _job_audit(conn, jcfg: dict) -> dict:
    from commerceos.catalog import audit as catalog_audit
    from commerceos.spine.schema import ensure_schema as ensure_facts
    ensure_facts(conn)  # an empty store audits "no landed products", not "no such table"
    state = catalog_audit.audit(
        conn,
        json.loads(catalog_audit.default_taxonomy_path().read_text()),
        json.loads(catalog_audit.default_config_path().read_text()),
    )
    # the CLI stamps this provenance key (audit.py:520); a rhythm-run mirror
    # carries the same honesty — which db it measured, not just its numbers.
    state["db"] = str(catalog_audit.default_db())
    md_path, _ = catalog_audit.write_reports(state, catalog_audit.DEFAULT_OUT)
    return {"summary": f"health {state['overall_score']}/100 on {state['total']}"
                       f" products -> {md_path.name}"}


def _job_evaluate(conn, jcfg: dict) -> dict:
    from commerceos.spine.schema import ensure_schema as ensure_facts
    from commerceos.watching import engine
    ensure_facts(conn)  # facts never landed evaluate as stale, honestly — not a crash
    s = engine.evaluate(conn, engine.load_watch_list())
    return {"summary": f"{s['metrics']} metrics · {s['evaluations']} evaluations · "
                       f"{s['findings_minted']} findings minted · "
                       f"{s['findings_refreshed']} refreshed · {s['aged_out']} aged out"}


def _job_analyst(conn, jcfg: dict) -> dict:
    """the analyst's standing turn (F3): the six ruled hunts over landed
    facts, findings only through the one door — no store writes. the
    hunts and their knobs come from the row this job was given."""
    from commerceos.spine.schema import ensure_schema as ensure_facts
    from commerceos.watching import analyst
    ensure_facts(conn)  # an empty store hunts "not enough data", not "no such table"
    tally = analyst.run_hunts(conn, jcfg)
    total = {k: sum(t[k] for t in tally.values())
             for k in ("found", "minted", "refreshed", "skipped_no_evidence",
                       "not_enough_data")}
    return {"summary": f"{len(tally)} hunts · {total['found']} patterns · "
                       f"{total['minted']} findings minted · "
                       f"{total['refreshed']} refreshed · "
                       f"{total['skipped_no_evidence']} dropped without evidence · "
                       f"{total['not_enough_data']} thin-data passes"}


# the built-in jobs a config row's "calls" key resolves against. a
# per-agent job joins by adding its entry here and a row in the store's
# rhythm.json — nothing else changes ("analyst" landed exactly that way).
BUILTIN_JOBS = {"expire_sweep": _job_expire_sweep, "sync": _job_sync,
                "propose": _job_propose,
                "audit": _job_audit, "evaluate": _job_evaluate,
                "analyst": _job_analyst}


# ---------- the job registry (spec/parts/fleet.md behavior 1) ----------

def registry_rows(cfg: dict) -> list[tuple[str, dict]]:
    """the config's job rows in the order a tick runs them: row order as
    written in the file, except expire_sweep runs first if present. that
    exception is a safety rule, not a preference: expire_sweep flips
    pending approvals past their expiry to expired, and it must land
    before any other job — or this tick's own push — reads the pending
    queue, so a lapsed proposal is never worked or pushed as approvable."""
    rows = list(job_configs(cfg).items())
    rows.sort(key=lambda kv: kv[0] != "expire_sweep")  # stable: file order otherwise
    return rows


def resolve_job(name: str, jcfg: dict, jobs: dict | None = None):
    """a row's callable: its "calls" key resolved against the built-in
    map, defaulting to the built-in of the row's own name — that
    defaulting rule is why a config carrying no "calls" keys (store #1's
    today) keeps ticking unchanged. None means the row names nothing
    this runner knows."""
    return (jobs or BUILTIN_JOBS).get(jcfg.get("calls", name))


def _run_job(conn, name: str, fn, jcfg: dict | None = None) -> dict:
    """run one job, catch everything — a failure is an outcome, not a stop."""
    t0 = time.monotonic()
    try:
        out = fn(conn, jcfg or {}) or {}
        return {"ok": True, "summary": out.get("summary", "ran"), "error": None,
                "duration_ms": int((time.monotonic() - t0) * 1000)}
    except Exception as e:
        try:
            conn.rollback()  # clear any half-open transaction so the next job runs clean
        except Exception:
            pass
        return {"ok": False, "summary": None, "error": f"{type(e).__name__}: {e}",
                "duration_ms": int((time.monotonic() - t0) * 1000)}


# ---------- the tick ----------

def tick(conn, config: dict | None = None, now: datetime | None = None,
         jobs: dict | None = None) -> dict:
    """one tick: run every enabled job that has come due, in registry
    order (registry_rows), each outcome recorded — one job's failure
    never stops the others, and a row whose callable resolves to nothing
    is refused loudly, not crashed on. then push what needs the owner
    (notify-only) and refresh the parts' registry rows. returns
    {ts, results, failed, notifications}."""
    cfg = config if config is not None else load_config()
    now = now or datetime.now(timezone.utc)
    now_iso = now.isoformat(timespec="seconds")
    ensure_schema(conn)

    state = state_rows(conn)
    prev = state.get("tick")
    prev_ts = prev["last_run"] if prev else None  # 'new since' horizon for the pushes

    results: dict[str, dict] = {}
    failed: list[str] = []
    for name, jcfg in registry_rows(cfg):
        if not jcfg.get("enabled", False):
            results[name] = {"ran": False, "why": "disabled (arming is the owner's keystroke)"}
            print(f"[rhythm] {name}: skipped — disabled")
            continue
        cadence = parse_cadence(jcfg["cadence"])
        last = (state.get(name) or {}).get("last_run")
        if not is_due(last, cadence, now):
            due_at = next_due(last, cadence)
            results[name] = {"ran": False, "why": f"not due until {due_at}"}
            print(f"[rhythm] {name}: skipped — not due until {due_at}")
            continue
        fn = resolve_job(name, jcfg, jobs)
        if fn is None:  # a refusal is an outcome, recorded like a failure
            error = (f"refused: row names no job this runner knows "
                     f"(calls {jcfg.get('calls', name)!r}; built-ins: "
                     f"{', '.join(BUILTIN_JOBS)})")
            record_run(conn, name, now_iso, False, None, error)
            results[name] = {"ran": False, "refused": True, "error": error, "why": error}
            failed.append(name)
            print(f"[rhythm] {name}: REFUSED — {error}")
            continue
        outcome = _run_job(conn, name, fn, jcfg)
        record_run(conn, name, now_iso, outcome["ok"], outcome["summary"],
                   outcome["error"], outcome["duration_ms"])
        results[name] = {"ran": True, **outcome}
        if outcome["ok"]:
            print(f"[rhythm] {name}: ran — {outcome['summary']}")
        else:
            failed.append(name)
            print(f"[rhythm] {name}: FAILED — {outcome['error']}")

    notifications = _push(conn, cfg.get("ntfy") or {}, results, failed, prev_ts, now)

    ran = sum(1 for r in results.values() if r.get("ran"))
    skipped = sum(1 for r in results.values() if not r.get("ran") and not r.get("refused"))
    record_run(conn, "tick", now_iso, not failed,
               f"{ran} ran · {len(failed)} failed · {skipped} skipped",
               "; ".join(f"{n}: {results[n]['error']}" for n in failed) or None)
    _refresh_registry(conn, cfg, now)
    return {"ts": now_iso, "results": results, "failed": failed,
            "notifications": notifications}


def run_one(conn, name: str, config: dict | None = None,
            now: datetime | None = None, jobs: dict | None = None) -> dict:
    """a one-off manual run — the owner's own keystroke, so it runs whether
    or not the job is enabled or due. recorded like any run. no push: he
    is at the keyboard and the outcome is right here on stdout."""
    cfg = config if config is not None else load_config()
    now = now or datetime.now(timezone.utc)
    ensure_schema(conn)
    jcfg = job_configs(cfg).get(name, {})  # a built-in may run without a row
    fn = resolve_job(name, jcfg, jobs)
    if fn is None:
        raise ValueError(f"unknown job {name!r} — no config row's callable and no"
                         f" built-in matches (built-ins: {', '.join(BUILTIN_JOBS)})")
    outcome = _run_job(conn, name, fn, jcfg)
    record_run(conn, name, now.isoformat(timespec="seconds"), outcome["ok"],
               outcome["summary"], outcome["error"], outcome["duration_ms"])
    if outcome["ok"]:
        print(f"[rhythm] {name}: ran — {outcome['summary']}")
    else:
        print(f"[rhythm] {name}: FAILED — {outcome['error']}")
    _refresh_registry(conn, cfg, now)
    return outcome


# ---------- the pushes (notify-only; the three triggers) ----------

def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _push(conn, ntfy: dict, results: dict, failed: list, prev_ts: str | None,
          now=None) -> dict:
    """the three triggers (spec/experience.md — the item + a deep link,
    never the decision): a failed job, new pending approvals, a new risk
    finding. 'new' means since the previous tick; the first tick ever
    counts everything currently open."""
    sent = skipped = 0

    def tally(ok: bool) -> None:
        nonlocal sent, skipped
        if ok:
            sent += 1
        else:
            skipped += 1

    for name in failed:
        tally(notify.job_failed(ntfy, name, results[name].get("error") or "failed"))

    if _table_exists(conn, "ledger"):
        # live waits at THIS tick's clock — a lapsed proposal is never pushed
        # as a pending approval (it expires; still wanted means re-proposed).
        pending = ledger.pending_queue(conn, ts=now)
        new = [r for r in pending if prev_ts is None or r["ts"] > prev_ts]
        if new:
            tally(notify.pending_approvals(ntfy, len(new), len(pending)))

    if _table_exists(conn, "findings"):
        rows = conn.execute(
            "SELECT sentence FROM findings WHERE direction = 'risk'"
            " AND disposition IN ('noticed', 'routed') AND noticed_at > ?"
            " ORDER BY noticed_at",
            (prev_ts or "",),
        ).fetchall()
        if rows:
            tally(notify.risk_finding(ntfy, [r["sentence"] for r in rows]))

    return {"sent": sent, "skipped": skipped}


# ---------- the registry refresh: every tick, every orchestrated part ----------

def _refresh_registry(conn, cfg: dict, now: datetime) -> None:
    """call each part's own status report — the rhythm keeps the rows
    fresh, it never writes another part's row itself. a reporter's error
    is logged, never fatal."""
    reporters = (
        ("data-spine", spine_report),
        ("gate-and-record", gate_report),
        ("catalog-loop", catalog_report),
        ("watching", watching_report),
    )
    for part, fn in reporters:
        try:
            fn(conn)
        except Exception as e:
            print(f"[rhythm] {part} status refresh failed — {type(e).__name__}: {e}")
    try:
        from commerceos.rhythm import status as rhythm_status
        rhythm_status.report_status(conn, cfg, now=now)
    except Exception as e:
        print(f"[rhythm] own status refresh failed — {type(e).__name__}: {e}")


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m commerceos.rhythm.runner",
        description="the standing rhythm: run due jobs (tick) or one job by hand (run)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tick", help="run every enabled job that has come due, in order")
    r = sub.add_parser("run", help="one-off manual run of a single job (ignores enabled/due)")
    r.add_argument("job", help="a job row from the config, or a built-in job name")
    for p in (t, r):
        p.add_argument("--config", default=None, help="rhythm.json path (default: the active store's)")
        p.add_argument("--db", default=None, help="database path (default: the active store's)")
    args = ap.parse_args(argv)

    conn = connect(args.db)
    try:
        cfg = load_config(args.config)
        if args.cmd == "tick":
            out = tick(conn, cfg)
            return 1 if out["failed"] else 0
        try:
            outcome = run_one(conn, args.job, cfg)
        except ValueError as e:
            print(f"[rhythm] refused — {e}")
            return 2
        return 0 if outcome["ok"] else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
