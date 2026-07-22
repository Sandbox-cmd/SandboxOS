"""carry-over: suppliers land from the FTA purchase listing, idempotently,
with take rates NULL (contracts, not history, set rates)."""

from commerceos.db import connect
from commerceos.spine.schema import ensure_schema
from commerceos.spine.seeds import seed_suppliers_from_fta

FIXTURE = "tests/fixtures/fta_mini.csv"


def test_suppliers_seed_idempotent_and_rateless(tmp_path):
    conn = connect(tmp_path / "s.db")
    ensure_schema(conn)
    r1 = seed_suppliers_from_fta(conn, FIXTURE)
    assert r1["landed"] == r1["suppliers_seen"] > 0
    r2 = seed_suppliers_from_fta(conn, FIXTURE)
    assert r2["landed"] == 0  # idempotent
    row = conn.execute("SELECT * FROM suppliers LIMIT 1").fetchone()
    assert row["default_take_rate_bps"] is None and row["source"].startswith("fta:")
