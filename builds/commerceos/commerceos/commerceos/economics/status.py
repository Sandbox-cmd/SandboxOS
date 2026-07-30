"""the economics part's self-report — its own row, through the shared helper.

the row states both lanes plainly (the fresh-start ruling, 2026-07-11):
- learnings: from the newest learnings reconcile sidecar
  (reports/econ-reconcile-learnings-*.json) — the engine proof against the
  old company's books. reference, never company P&L.
- company: computed live from the fresh company's landed facts — zero
  orders reads as "no orders landed yet", never as measured zeros. at zero
  today, awaiting the new entity.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from commerceos.economics import engine
from commerceos.web import registry

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def latest_reconciliation(reports_dir: Path | str | None = None,
                          lane: str = "learnings") -> dict | None:
    """the newest econ-reconcile-*.json sidecar FOR THE LANE, or None.

    sidecars written before the lanes split carry no lane field — those
    were all learnings-lane runs (the FTA history) and read as such.
    """
    d = Path(reports_dir) if reports_dir else REPORTS_DIR
    files = list(d.glob("econ-reconcile-*.json")) if d.is_dir() else []
    for p in sorted(files, key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("lane", "learnings") == lane:
            return data
    return None


def report_status(conn, reports_dir: Path | str | None = None,
                  period: str | None = None) -> None:
    period = period or str(datetime.now(timezone.utc).year)
    pnl = engine.assemble(conn, period, lane="company")
    cells, gaps = pnl["cells"], pnl["gaps"]

    rec = latest_reconciliation(reports_dir, lane="learnings")
    if rec:
        sales = next((ln for ln in rec.get("lines", []) if ln.get("kind") == "minor"), None)
        delta = ""
        if sales and sales.get("delta_minor") is not None:
            delta = (f" ({rec['period']} sales {sales['delta_minor']:+} fils,"
                     f" {sales['delta_bps']:.4f} bps)")
        verdict = "proven" if rec["ok"] else "FAILED"
        learnings_line = (f"learnings lane: engine proof against the old company's"
                          f" books — {verdict}{delta}")
    else:
        learnings_line = "learnings lane: no engine proof run yet"

    if "take_earned" in cells:
        company_line = (f"company lane: take {cells['take_earned']['value']}"
                        f" · payable {cells['payable_outstanding']['value']} fils")
    elif cells:
        company_line = (f"company lane: {len(cells)} measured cells,"
                        " no settlement facts yet")
    else:
        company_line = ("company lane: at zero — no orders, no books yet;"
                        " awaiting the new entity's first facts")

    gap_names = ", ".join(g["name"] for g in gaps) or "none"
    summary = f"{learnings_line} · {company_line} · company gaps: {gap_names}"
    registry.report(
        conn, "economics",
        "steer the money from landed facts — two lanes: company P&L (the fresh"
        " entity) and learnings (the old company's books, reference only) (O5)",
        state="failed" if rec and not rec["ok"] else "idle",
        functions=["pnl", "settlement", "reconcile", "lanes"],
        last_run={"summary": summary, "ok": (rec or {}).get("ok", True),
                  "period": period, "lane": "company",
                  "gaps": [g["name"] for g in gaps]})
