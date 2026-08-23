"""the watching's self-report — its own row, through the shared helper."""

from datetime import datetime

from commerceos.web import registry

from commerceos.watching import findings


def _plain_date(ts: str | None) -> str:
    """an ISO timestamp as the date a person reads ('jul 11') — the summary
    is a rendered line, so no raw timestamp rides in it."""
    if not ts:
        return "never"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%b %d").lower().replace(" 0", " ")
    except ValueError:
        return ts

_IS = ("standing attention over the whole business — notices both directions,"
       " routes findings with evidence, never acts (O1, O6)")
_FUNCTIONS = ["evaluate", "findings", "aging"]


def report_status(conn, watch_list=None) -> None:
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"evaluations", "findings"} <= tables:
        registry.report(conn, "watching", _IS, state="starting", functions=_FUNCTIONS)
        return

    active = (len(watch_list.get("metrics", [])) if watch_list is not None
              else conn.execute("SELECT count(DISTINCT metric) c FROM evaluations").fetchone()["c"])
    last = conn.execute("SELECT max(ts) t FROM evaluations").fetchone()["t"]
    mix = findings.direction_mix(conn)
    aged = sum(c for k, c in mix.items() if k.endswith("/aged_out"))
    open_rows = findings.open_findings(conn)
    oldest = round(open_rows[0]["age_days"], 1) if open_rows else None
    # a metric whose most recent evaluation says stale is a stale-fact warning
    stale_metrics = [r["metric"] for r in conn.execute(
        "SELECT DISTINCT metric FROM evaluations e WHERE stale = 1 AND period ="
        " (SELECT max(period) FROM evaluations WHERE metric = e.metric AND slice = e.slice)"
        " ORDER BY metric")]
    # each row states its drift mode (the 2026-07-18 ruling): "banded" once
    # its own history suffices, "warming up (n of N)" until then.
    drift_modes = {}
    if any(c["name"] == "drift_mode" for c in conn.execute("PRAGMA table_info(evaluations)")):
        for r in conn.execute(
            "SELECT metric, slice, drift_mode FROM evaluations e"
            " WHERE drift_mode IS NOT NULL AND period ="
            " (SELECT max(period) FROM evaluations WHERE metric = e.metric"
            "  AND slice = e.slice AND drift_mode IS NOT NULL)"
            " ORDER BY metric, slice"):
            label = f"{r['metric']}[{r['slice']}]" if r["slice"] else r["metric"]
            drift_modes[label] = r["drift_mode"]

    if active == 0:
        summary = "empty watch-list — evaluating nothing, and saying so"
    else:
        mix_line = " · ".join(f"{k}: {v}" for k, v in sorted(mix.items())) or "no findings yet"
        summary = f"{active} watch rows · last evaluation {_plain_date(last)} · {mix_line}"
        if drift_modes:
            banded = sum(1 for m in drift_modes.values() if m == "banded")
            warming = len(drift_modes) - banded
            summary += f" · drift: {banded} banded, {warming} warming up"
        if aged:
            summary += f" · {aged} aged out"
        if stale_metrics:
            plain = ", ".join(
                m.replace("-", " ").replace("_", " ") for m in stale_metrics)
            summary += f" · stale facts: {plain}"

    registry.report(
        conn, "watching", _IS,
        state="idle",
        functions=_FUNCTIONS,
        last_run={
            "summary": summary,
            "ok": True,
            "active_rows": active,
            "last_evaluation": last,
            "directions": mix,        # direction x status — the mix is the health
            "open": len(open_rows),
            "oldest_open_days": oldest,
            "aged_out": aged,
            "stale_metrics": stale_metrics,
            "drift_modes": drift_modes,  # per row: banded, or warming up (n of N)
        })
