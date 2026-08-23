"""the catalog loop's self-report — its own row, through the shared helper."""

import json
from pathlib import Path

from commerceos.web import registry

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"
IS = "the standing loop that keeps the catalog true — audit phase live; ingest, act, verify to come (O3)"


def report_status(conn, reports_dir: Path | str | None = None) -> None:
    d = Path(reports_dir) if reports_dir else REPORTS_DIR
    latest = d / "health-latest.json"
    if not latest.exists():
        registry.report(conn, "catalog-loop", IS, state="starting", functions=["audit"])
        return
    s = json.loads(latest.read_text())
    dims = s.get("dimensions", {})
    scored = {k: v["rate"] for k, v in dims.items() if v.get("scorable")}
    skipped = sorted(k for k, v in dims.items() if not v.get("scorable"))
    summary = (
        f"health {s['overall_score']}/100 on {s['total']} products @ {s['date']} · "
        + " · ".join(f"{k} {v}%" for k, v in sorted(scored.items(), key=lambda kv: -kv[1]))
        + (f" · not scorable yet (signal not landed): {', '.join(skipped)}" if skipped else "")
    )
    registry.report(
        conn, "catalog-loop", IS,
        state="idle", functions=["audit"],
        last_run={
            "summary": summary, "ok": True,
            "overall": s["overall_score"],
            "dimensions": {k: (v["rate"] if v.get("scorable") else None) for k, v in dims.items()},
            "report": str(d / f"health-{s['date']}.md"),
        },
    )
