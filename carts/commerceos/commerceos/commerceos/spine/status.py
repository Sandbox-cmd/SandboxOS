"""the spine's self-report — its own row, through the shared helper."""

from commerceos.web import registry


def report_status(conn) -> None:
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    counts, last = {}, None
    if "products" in tables:
        counts["products"] = conn.execute("SELECT count(*) c FROM products").fetchone()["c"]
        counts["orders"] = conn.execute("SELECT count(*) c FROM orders").fetchone()["c"]
        counts["money_lines"] = conn.execute("SELECT count(*) c FROM money_lines").fetchone()["c"]
        rows = conn.execute("SELECT connector, last_run, status FROM sync_state").fetchall()
        state = "failed" if any(r["status"] == "error" for r in rows) else "idle"
        last = {"summary": " · ".join(
            f"{r['connector']}: {r['status']} @ {r['last_run']}" for r in rows) or "no syncs yet",
            "ok": state != "failed", "counts": counts}
    else:
        state = "starting"
    registry.report(
        conn, "data-spine",
        "one local store of landed facts, and the only wires that touch the world (serves every job row)",
        state=state, functions=["sync", "books-import", "gated-writes"], last_run=last)
