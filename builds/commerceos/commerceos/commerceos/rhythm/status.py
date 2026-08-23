"""the rhythm's self-report — its own row, through the shared helper.

armed or disarmed (the plist under ~/Library/LaunchAgents is the fact),
per-job last run + next due, and whether push has anywhere to go.
"""

from __future__ import annotations

from datetime import datetime, timezone

from commerceos.rhythm import arm, notify, runner
from commerceos.web import registry

IS = ("the standing rhythm — owner-armed cadence over the parts; pushes what"
      " needs him, notify-only (nothing arms itself)")
FUNCTIONS = ["tick", "run", "notify", "arm"]


def report_status(conn, config: dict | None = None, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    now_iso = now.isoformat(timespec="seconds")
    cfg = config if config is not None else runner.load_config()
    state = runner.state_rows(conn)
    armed = arm.plist_path().exists()
    ntfy_ok = notify.configured(cfg.get("ntfy"))

    jobs, soonest = {}, None
    for name, jcfg in runner.registry_rows(cfg):  # the job registry, in run order
        row = state.get(name)
        enabled = bool(jcfg.get("enabled"))
        entry = {
            "cadence": jcfg.get("cadence"),
            "enabled": enabled,
            "last_run": row["last_run"] if row else None,
            "ok": bool(row["ok"]) if row else None,
            "next_due": None,
        }
        if enabled:
            due_at = runner.next_due(entry["last_run"], runner.parse_cadence(jcfg["cadence"]))
            entry["next_due"] = due_at or "next tick"
            effective = due_at or now_iso  # never ran = due at the next tick
            if soonest is None or effective < soonest:
                soonest = effective
        jobs[name] = entry

    tick_row = state.get("tick")
    enabled_n = sum(1 for j in jobs.values() if j["enabled"])
    if armed:
        head = f"armed — launchd tick every {arm.TICK_EVERY_SECONDS // 60}m"
    else:
        head = ("disarmed — nothing arms itself; arming is the owner's keystroke"
                " (python -m commerceos.rhythm.arm --yes)")
    summary = (f"{head} · {enabled_n}/{len(jobs)} jobs enabled · "
               f"ntfy {'configured' if ntfy_ok else 'not configured — pushes skipped, honestly'}")
    if tick_row:
        summary += f" · last tick {tick_row['last_run']}"

    registry.report(
        conn, "rhythm", IS,
        state="armed" if armed else "disarmed",
        functions=FUNCTIONS,
        last_run={
            "summary": summary,
            "ok": bool(tick_row["ok"]) if tick_row else True,
            "armed": armed,
            "ntfy_configured": ntfy_ok,
            "jobs": jobs,
            "last_tick": tick_row["last_run"] if tick_row else None,
        },
        next_run=soonest if armed else None,
    )
