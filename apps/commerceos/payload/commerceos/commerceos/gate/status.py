"""the gate + record's self-report — its own row, through the shared helper."""

from commerceos.web import registry


def report_status(conn) -> None:
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if "ledger" not in tables:
        registry.report(conn, "gate-and-record",
                        "one wall, one memory: the gate decides, the ledger remembers (O2, O4)",
                        state="starting", functions=["gate", "ledger"])
        return
    by_status = {r["status"]: r["c"] for r in conn.execute(
        "SELECT status, count(*) c FROM ledger GROUP BY status")}
    # "pending" on this cassette must mean what /fleet and decisions mean:
    # a LIVE wait. a pending row past its expiry is lapsed — counting it as
    # pending here contradicted the adjacent pages (UI-truth, 2026-07-19).
    from commerceos.gate import ledger as _ledger
    live = len(_ledger.pending_queue(conn))
    lapsed = by_status.get("pending", 0) - live
    if lapsed > 0:
        by_status["pending"] = live
        by_status["lapsed"] = by_status.pop("expired", 0) + lapsed
        if not by_status["pending"]:
            by_status.pop("pending")
    registry.report(
        conn, "gate-and-record",
        "one wall, one memory: the gate decides, the ledger remembers (O2, O4)",
        state="running" if live else "idle",
        functions=["gate", "ledger"],
        last_run={"summary": " · ".join(f"{k}: {v}" for k, v in sorted(by_status.items()))
                  or "no actions yet", "ok": True, "pending": live})
