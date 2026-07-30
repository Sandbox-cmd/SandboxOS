"""B1+B2+B3 — the watching part's checks (spec/parts/watching.md ## checks),
executable: (1) seeded facts fire a risk finding AND an opportunity finding
in one pass — the both-directions law; (2) a finding with no evidence is
refused; (3) a July dip matching the Gulf curve is not a false alarm;
(4) adding a metric is a row, not code; (5) an unactioned finding ages
visibly and ends aged_out, still queryable. plus: staleness says stale
instead of pretending, forming baselines fire bands only, a persisting
breach refreshes instead of flooding, and the real landed books history
(store #1's live db, read-only via a tmp copy) produces real evaluations."""

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from commerceos.db import connect
from commerceos.spine.schema import ensure_schema as ensure_facts
from commerceos.watching import engine, findings
from commerceos.watching.schema import MIGRATIONS, TABLE_SET, ensure_schema
from commerceos.db import migrate

REPO_ROOT = Path(__file__).resolve().parents[1]
WATCH_LIST_PATH = REPO_ROOT / "stores" / "demostore" / "watch-list.json"
REAL_DB = REPO_ROOT / "data" / "demostore.db"

NOW = datetime(2026, 7, 11, 12, 0, 0, tzinfo=timezone.utc)
FRESH = NOW.isoformat(timespec="seconds")


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "test.db")
    ensure_facts(c)
    ensure_schema(c)
    yield c
    c.close()


def seed_order(conn, oid, placed, net_minor):
    conn.execute(
        "INSERT INTO orders (shopify_id, number, placed_at, gross_minor, net_minor,"
        " source, fetched_at) VALUES (?, ?, ?, ?, ?, 'shopify:test', ?)",
        (oid, oid, placed, net_minor, net_minor, FRESH),
    )


def seed_return(conn, rid, oid, refunded, amount_minor):
    conn.execute(
        "INSERT INTO returns (shopify_id, order_id, refunded_at, amount_minor,"
        " source, fetched_at) VALUES (?, ?, ?, ?, 'shopify:test', ?)",
        (rid, oid, refunded, amount_minor, FRESH),
    )


def seed_sales(conn, month, amount_minor):
    conn.execute(
        "INSERT INTO money_lines (date, kind, account, amount_minor, external_ref,"
        " import_batch, source, fetched_at)"
        " VALUES (?, 'books', 'sales', ?, ?, 'seed', 'test:seed', ?)",
        (f"{month}-15", amount_minor, f"seed/{month}", FRESH),
    )


def sales_metric(**over):
    row = {
        "name": "monthly-sales",
        "formula": {"op": "sum", "table": "money_lines", "column": "amount_minor",
                    "where": "kind='books' AND account='sales'", "date": "date",
                    "period": "month", "freshness": ["money_lines"]},
        "cadence": "monthly",
        "baseline": {"method": "rolling", "window": 3},
        "drift_pct": 20,
    }
    row.update(over)
    return row


RETURN_RATE = {
    "name": "return-rate",
    "formula": {"op": "ratio", "period": "month", "freshness": ["orders"],
                "numerator": {"table": "returns", "column": "amount_minor",
                              "date": "refunded_at"},
                "denominator": {"table": "orders", "column": "net_minor",
                                "date": "placed_at"}},
    "cadence": "daily",
    "baseline": {"method": "rolling", "window": 3},
    "bands": [{"edge": 0.12, "side": "above", "direction": "risk"}],
}


# ---------- schema ----------

def test_schema_creates_clean_and_is_idempotent(tmp_path):
    c = connect(tmp_path / "fresh.db")
    assert migrate(c, TABLE_SET, MIGRATIONS) == len(MIGRATIONS)
    assert migrate(c, TABLE_SET, MIGRATIONS) == 0  # re-run: no-op
    tables = {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"evaluations", "findings"} <= tables
    c.close()


# ---------- check 1: both directions, one pass ----------

def test_a_breach_and_a_surge_fire_both_directions_in_one_pass(conn):
    for i, month in enumerate(["2026-03", "2026-04", "2026-05"]):
        seed_order(conn, f"o{i}", f"{month}-10T09:00:00Z", 100_000)
    seed_order(conn, "o9", "2026-06-10T09:00:00Z", 160_000)  # +60% vs the 100k mean
    seed_return(conn, "r1", "o9", "2026-06-20T09:00:00Z", 25_600)  # 16% of June net

    watch_list = {"metrics": [RETURN_RATE, sales_metric(
        formula={"op": "sum", "table": "orders", "column": "net_minor",
                 "date": "placed_at", "period": "month", "freshness": ["orders"]})]}
    out = engine.evaluate(conn, watch_list, now=NOW)

    open_ = findings.open_findings(conn, now=NOW)
    directions = {f["direction"] for f in open_}
    assert {"risk", "opportunity"} <= directions  # the both-directions law
    assert out["findings_minted"] == 2
    risk = next(f for f in open_ if f["direction"] == "risk")
    assert risk["metric"] == "return-rate"
    assert risk["evidence"]["evaluations"]  # every claim carries its provenance
    surge = next(f for f in open_ if f["direction"] == "opportunity")
    assert surge["metric"] == "monthly-sales"


def test_a_persisting_breach_refreshes_the_open_finding_never_floods(conn):
    for i, month in enumerate(["2026-03", "2026-04", "2026-05"]):
        seed_order(conn, f"o{i}", f"{month}-10T09:00:00Z", 100_000)
    seed_order(conn, "o9", "2026-06-10T09:00:00Z", 160_000)
    seed_return(conn, "r1", "o9", "2026-06-20T09:00:00Z", 25_600)
    watch_list = {"metrics": [RETURN_RATE]}

    first = engine.evaluate(conn, watch_list, now=NOW)
    second = engine.evaluate(conn, watch_list, now=NOW + timedelta(hours=6))
    assert first["findings_minted"] == 1
    assert second["findings_minted"] == 0 and second["findings_refreshed"] == 1
    open_ = findings.open_findings(conn)
    assert len(open_) == 1
    assert open_[0]["updated_at"] > open_[0]["noticed_at"]  # refreshed, age kept


# ---------- check 2: no evidence, no finding ----------

def test_a_finding_with_no_evidence_is_refused(conn):
    with pytest.raises(ValueError):
        findings.mint(conn, "something moved", "risk", {"evaluations": [], "facts": []})
    with pytest.raises(ValueError):
        findings.mint(conn, "something moved", "risk", {})
    assert conn.execute("SELECT count(*) c FROM findings").fetchone()["c"] == 0


# ---------- check 3: the seasonal baseline holds ----------

def test_a_july_dip_matching_the_gulf_curve_is_not_a_false_alarm(conn):
    curve = engine.load_watch_list(WATCH_LIST_PATH)["curves"]["gulf"]
    level = 100_000
    for month, factor in [("2026-02", 1.35), ("2026-03", 1.30), ("2026-04", 1.25),
                          ("2026-05", 0.75), ("2026-06", 0.65)]:
        seed_sales(conn, month, int(level * factor))
    seed_sales(conn, "2026-07", int(level * 0.60))  # the July trough, on the curve

    watch_list = {"curves": {"gulf": curve}, "metrics": [sales_metric(
        baseline={"method": "seasonal", "window": 5, "curve": "gulf"}, drift_pct=15)]}
    engine.evaluate(conn, watch_list, now=datetime(2026, 8, 1, tzinfo=timezone.utc))

    july = conn.execute(
        "SELECT * FROM evaluations WHERE metric='monthly-sales' AND period='2026-07'"
    ).fetchone()
    assert july["value"] == 60_000
    assert july["baseline"] == pytest.approx(60_000)  # deseasonalized level x 0.60
    assert abs(july["delta"]) < 0.01
    assert conn.execute("SELECT count(*) c FROM findings").fetchone()["c"] == 0


def test_until_the_window_fills_baseline_reads_forming_and_only_bands_fire(conn):
    seed_sales(conn, "2026-05", 50_000)
    seed_sales(conn, "2026-06", 200_000)  # would be +300% drift — but forming
    watch_list = {"metrics": [sales_metric(
        bands=[{"edge": 100_000, "side": "above", "direction": "opportunity"}])]}
    engine.evaluate(conn, watch_list, now=NOW)

    june = conn.execute(
        "SELECT * FROM evaluations WHERE metric='monthly-sales' AND period='2026-06'"
    ).fetchone()
    assert june["value"] == 200_000
    assert june["baseline"] is None and june["delta"] is None  # forming, not invented
    open_ = findings.open_findings(conn)
    assert [f["direction"] for f in open_] == ["opportunity"]  # the band, drift silent


# ---------- staleness: say stale, pretend nothing ----------

def test_stale_facts_evaluate_stale_instead_of_pretending_a_number(conn):
    old = (NOW - timedelta(days=10)).isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO orders (shopify_id, placed_at, gross_minor, net_minor, source, fetched_at)"
        " VALUES ('o1', '2026-07-01T09:00:00Z', 100000, 100000, 'shopify:test', ?)", (old,))
    watch_list = {"metrics": [sales_metric(
        name="daily-net",
        formula={"op": "sum", "table": "orders", "column": "net_minor",
                 "date": "placed_at", "period": "month", "freshness": ["orders"]},
        cadence="daily")]}
    out = engine.evaluate(conn, watch_list, now=NOW)

    assert out["stale"] == ["daily-net"]
    row = conn.execute("SELECT * FROM evaluations WHERE metric='daily-net'").fetchone()
    assert row["stale"] == 1 and row["value"] is None
    assert conn.execute("SELECT count(*) c FROM findings").fetchone()["c"] == 0


# ---------- check 4: a metric is a row, not code ----------

def test_adding_a_metric_row_evaluates_on_the_next_pass_zero_code_changes(conn):
    seed_order(conn, "o1", "2026-06-10T09:00:00Z", 70_000)
    watch_list = {"metrics": [sales_metric(
        formula={"op": "sum", "table": "orders", "column": "net_minor",
                 "date": "placed_at", "period": "month", "freshness": ["orders"]})]}
    engine.evaluate(conn, watch_list, now=NOW)
    assert not conn.execute(
        "SELECT 1 FROM evaluations WHERE metric='order-count'").fetchone()

    watch_list["metrics"].append({  # a new row in the dict — nothing else changes
        "name": "order-count",
        "formula": {"op": "count", "table": "orders", "column": "*",
                    "date": "placed_at", "period": "month", "freshness": ["orders"]},
        "cadence": "daily",
        "baseline": {"method": "rolling", "window": 3},
    })
    engine.evaluate(conn, watch_list, now=NOW)
    row = conn.execute("SELECT * FROM evaluations WHERE metric='order-count'").fetchone()
    assert row is not None and row["value"] == 1


# ---------- check 5: unactioned findings age visibly, never vanish ----------

def test_an_ignored_finding_ages_visibly_ends_aged_out_and_stays_queryable(conn):
    fid = findings.mint(
        conn, "return-rate at 0.16 is above the 0.12 edge", "risk",
        {"evaluations": [1], "facts": ["orders@2026-05 rows=4"]},
        metric="return-rate", now=NOW - timedelta(days=40))

    open_ = findings.open_findings(conn, now=NOW)
    assert open_ and open_[0]["age_days"] == pytest.approx(40, abs=0.1)  # age rendered

    out = engine.evaluate(conn, {"metrics": [], "age_out_days": {"risk": 30}}, now=NOW)
    assert out["aged_out"] == 1
    row = findings.get(conn, fid)
    assert row["disposition"] == "aged_out"
    assert findings.open_findings(conn) == []  # off the flag feed...
    aged = findings.query(conn, disposition="aged_out")
    assert [f["id"] for f in aged] == [fid]  # ...but never deleted, still queryable


def test_the_lifecycle_walks_noticed_routed_decided_done_and_refuses_shortcuts(conn):
    fid = findings.mint(conn, "vendor-margin[vendor=Acme] slumped", "risk",
                        {"evaluations": [7], "facts": []}, metric="vendor-margin", now=NOW)
    with pytest.raises(ValueError):
        findings.transition(conn, fid, "done")  # noticed cannot jump to done
    findings.route_to(conn, fid, "owner", now=NOW)
    with pytest.raises(ValueError):
        findings.decide(conn, fid, "")  # a decision carries its reason
    findings.decide(conn, fid, "acted: paused the vendor's POs", now=NOW)
    findings.complete(conn, fid, now=NOW)
    assert findings.get(conn, fid)["disposition"] == "done"
    with pytest.raises(ValueError):
        findings.transition(conn, fid, "routed")  # done is terminal


# ---------- the self-report ----------

def test_an_empty_watch_list_evaluates_nothing_and_says_so(conn):
    engine.evaluate(conn, {"metrics": []}, now=NOW)
    row = conn.execute("SELECT * FROM parts WHERE part='watching'").fetchone()
    assert row is not None
    assert "evaluating nothing" in row["last_run"]


# ---------- B3: the demostore watch-list ----------

def test_the_demostore_watch_list_loads_and_every_row_evaluates_honestly(conn):
    watch_list = engine.load_watch_list(WATCH_LIST_PATH)
    names = [m["name"] for m in watch_list["metrics"]]
    assert len(names) == len(set(names)) and len(names) >= 6
    assert {"monthly-sales", "return-rate", "ad-efficiency", "bnpl-fee-share",
            "vendor-margin", "vendor-return-rate"} <= set(names)
    gulf = watch_list["curves"]["gulf"]
    assert [gulf[str(m)] for m in range(1, 13)] == [
        1.40, 1.35, 1.30, 1.25, 0.75, 0.65, 0.60, 0.65, 0.75, 1.35, 1.40, 1.45]

    # against an empty spine every row still answers — stale or no-data, never invented
    out = engine.evaluate(conn, watch_list, now=NOW)
    assert out["metrics"] == len(names)
    assert out["findings_minted"] == 0
    assert set(out["stale"]) | set(out["no_data"]) == set(names)


# ---------- the real landed history ----------

@pytest.mark.skipif(not REAL_DB.exists(), reason="no landed store #1 db on this machine")
def test_monthly_sales_evaluates_the_real_books_history(tmp_path, monkeypatch):
    # never mutate the real DB: evaluate a tmp copy (WAL sidecars included).
    work = tmp_path / "commerceos-copy.db"
    shutil.copyfile(REAL_DB, work)
    for suffix in ("-wal", "-shm"):
        sidecar = REAL_DB.with_name(REAL_DB.name + suffix)
        if sidecar.exists():
            shutil.copyfile(sidecar, work.with_name(work.name + suffix))
    monkeypatch.setenv("COMMERCEOS_DB", str(work))

    conn = connect(work)
    try:
        newest = conn.execute("SELECT max(fetched_at) m FROM money_lines").fetchone()["m"]
        if not newest:
            pytest.skip("no money_lines landed in the local db")
        as_of = datetime.fromisoformat(newest.replace("Z", "+00:00")) + timedelta(hours=1)

        watch_list = engine.load_watch_list(WATCH_LIST_PATH)
        watch_list["metrics"] = [m for m in watch_list["metrics"]
                                 if m["name"] == "monthly-sales"]
        out = engine.evaluate(conn, watch_list, now=as_of)
        assert out["evaluations"] > 0 and not out["stale"]

        rows = {r["period"]: r for r in conn.execute(
            "SELECT * FROM evaluations WHERE metric='monthly-sales'")}
        for month in (f"2025-{m:02d}" for m in range(1, 13)):
            assert month in rows, f"no evaluation for {month}"
            assert rows[month]["stale"] == 0 and rows[month]["value"] > 0
            assert rows[month]["baseline"] is not None  # window long since filled
        # spot-check against your own landed books numbers: pin two months
        # you can verify by hand (fils, VAT-exclusive). the shape is the
        # check; the values are yours.
        #     assert rows["<year>-01"]["value"] == <your january total>
        #     assert rows["<year>-06"]["value"] == <your june total>
    finally:
        conn.close()
