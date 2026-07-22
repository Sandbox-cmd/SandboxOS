"""W1 — drift bands (RULED 2026-07-18): the drift threshold is a statistical
band per metric, computed from that metric's OWN evaluation history — mean ±
band_k standard deviations — with a plain-percentage warm-up until the history
reaches N for the row's period grain (day 14 · week 8 · month 6, overridable
via the watch-list's "drift_warmup_n"). every evaluation records which mode
governed it, the self-report shows the mode per row, and a band breach mints
through the same findings door with the evaluation ids as evidence."""

from datetime import date, datetime, timedelta, timezone

import pytest

from commerceos.db import connect
from commerceos.spine.schema import ensure_schema as ensure_facts
from commerceos.watching import engine, findings
from commerceos.watching.schema import ensure_schema

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


def seed_sales(conn, month, amount_minor):
    conn.execute(
        "INSERT INTO money_lines (date, kind, account, amount_minor, external_ref,"
        " import_batch, source, fetched_at)"
        " VALUES (?, 'books', 'sales', ?, ?, 'seed', 'test:seed', ?)",
        (f"{month}-15", amount_minor, f"seed/{month}", FRESH),
    )


def month_metric(**over):
    row = {
        "name": "monthly-sales",
        "formula": {"op": "sum", "table": "money_lines", "column": "amount_minor",
                    "where": "kind='books' AND account='sales'", "date": "date",
                    "period": "month", "freshness": ["money_lines"]},
        "cadence": "monthly",
    }
    row.update(over)
    return row


def day_metric(**over):
    row = {
        "name": "daily-sales",
        "formula": {"op": "sum", "table": "orders", "column": "net_minor",
                    "date": "placed_at", "period": "day", "freshness": ["orders"]},
        "cadence": "daily",
    }
    row.update(over)
    return row


def seed_stable_days(conn, first: date, count: int, outlier_minor=None):
    """count consecutive days alternating 99k/101k (mean 100k, sd 1000),
    then one more day at outlier_minor if given. Returns the last day."""
    day = first
    for i in range(count):
        seed_order(conn, f"o{i}", f"{day.isoformat()}T09:00:00Z", 99_000 if i % 2 else 101_000)
        day += timedelta(days=1)
    if outlier_minor is not None:
        seed_order(conn, "o-outlier", f"{day.isoformat()}T09:00:00Z", outlier_minor)
    return day


def drift_mode_of(conn, metric, period):
    return conn.execute(
        "SELECT drift_mode FROM evaluations WHERE metric = ? AND period = ?",
        (metric, period)).fetchone()["drift_mode"]


# ---------- (a) thin history: warm-up mode, and the evaluation says so ----------

def test_thin_history_evaluates_in_warm_up_mode_and_says_so(conn):
    for month in ("2026-03", "2026-04", "2026-05"):
        seed_sales(conn, month, 100_000)
    seed_sales(conn, "2026-06", 200_000)  # +100% vs the rolling baseline
    watch_list = {"metrics": [month_metric(
        baseline={"method": "rolling", "window": 3}, drift_pct=20)]}
    engine.evaluate(conn, watch_list, now=NOW)

    # 3 prior evaluations < the month-grain N of 6: warming up, honestly
    assert drift_mode_of(conn, "monthly-sales", "2026-06") == "warming up (3 of 6)"
    open_ = findings.open_findings(conn, now=NOW)
    assert [f["direction"] for f in open_] == ["opportunity"]
    assert "drift line" in open_[0]["sentence"]  # the plain-percentage path fired
    assert open_[0]["evidence"]["evaluations"]


def test_without_a_drift_pct_the_warm_up_watches_nothing_but_still_says_so(conn):
    seed_sales(conn, "2026-05", 100_000)
    seed_sales(conn, "2026-06", 500_000)  # a surge, but no warm-up line configured
    engine.evaluate(conn, {"metrics": [month_metric()]}, now=NOW)
    assert drift_mode_of(conn, "monthly-sales", "2026-06") == "warming up (1 of 6)"
    assert conn.execute("SELECT count(*) c FROM findings").fetchone()["c"] == 0


# ---------- (b) seeded history: the band computes and flags honestly ----------

def test_with_enough_history_the_band_computes_and_an_outlier_flags(conn):
    # 14 days at ~100k (the day-grain N), then a 200k day: outside mean ± 2 sd
    seed_stable_days(conn, date(2026, 6, 21), 14, outlier_minor=200_000)
    out = engine.evaluate(conn, {"metrics": [day_metric()]}, now=NOW)

    assert drift_mode_of(conn, "daily-sales", "2026-07-05") == "banded"
    assert out["findings_minted"] == 1
    open_ = findings.open_findings(conn, now=NOW)
    assert [f["direction"] for f in open_] == ["opportunity"]
    assert "outside its usual range" in open_[0]["sentence"]

    # evidence cites the evaluation ids: the breaching one plus its history
    all_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM evaluations WHERE metric='daily-sales' ORDER BY period")]
    assert set(open_[0]["evidence"]["evaluations"]) == set(all_ids)
    assert len(all_ids) == 15

    # behavior 7 holds on the band path too: a persisting breach refreshes
    again = engine.evaluate(conn, {"metrics": [day_metric()]}, now=NOW + timedelta(hours=6))
    assert again["findings_minted"] == 0 and again["findings_refreshed"] == 1
    assert len(findings.open_findings(conn)) == 1


def test_a_slump_below_the_band_is_a_risk_same_math_both_directions(conn):
    seed_stable_days(conn, date(2026, 6, 21), 14, outlier_minor=50_000)
    engine.evaluate(conn, {"metrics": [day_metric()]}, now=NOW)
    open_ = findings.open_findings(conn, now=NOW)
    assert [f["direction"] for f in open_] == ["risk"]


def test_band_k_is_per_row_a_wider_band_holds_its_tongue(conn):
    # same facts, two rows: the default k=2 band flags a 110k day, k=50 does not
    seed_stable_days(conn, date(2026, 6, 21), 14, outlier_minor=110_000)
    watch_list = {"metrics": [day_metric(),
                              day_metric(name="daily-sales-wide", band_k=50)]}
    engine.evaluate(conn, watch_list, now=NOW)
    open_ = findings.open_findings(conn, now=NOW)
    assert [f["metric"] for f in open_] == ["daily-sales"]
    assert drift_mode_of(conn, "daily-sales-wide", "2026-07-05") == "banded"


# ---------- (c) the month-grain challenge: 5 months warm, 6 flips banded ----------

def test_a_month_grain_metric_stays_warm_at_five_months_and_flips_at_six(conn):
    for month in ("2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"):
        seed_sales(conn, month, 100_000)
    engine.evaluate(conn, {"metrics": [month_metric()]}, now=NOW)
    # 5 prior months for June: still warming up, and it says so
    assert drift_mode_of(conn, "monthly-sales", "2026-06") == "warming up (5 of 6)"

    seed_sales(conn, "2026-07", 100_000)
    engine.evaluate(conn, {"metrics": [month_metric()]}, now=datetime(2026, 8, 1, tzinfo=timezone.utc))
    # 6 prior months for July: the band takes over
    assert drift_mode_of(conn, "monthly-sales", "2026-07") == "banded"
    assert conn.execute("SELECT count(*) c FROM findings").fetchone()["c"] == 0  # stable


def test_n_per_grain_is_config_a_watch_list_override_flips_sooner(conn):
    for month in ("2026-03", "2026-04", "2026-05"):
        seed_sales(conn, month, 100_000)
    seed_sales(conn, "2026-06", 200_000)
    watch_list = {"drift_warmup_n": {"month": 3}, "metrics": [month_metric()]}
    engine.evaluate(conn, watch_list, now=NOW)
    assert drift_mode_of(conn, "monthly-sales", "2026-06") == "banded"
    open_ = findings.open_findings(conn, now=NOW)
    assert [f["direction"] for f in open_] == ["opportunity"]


# ---------- (d) stable values inside the band mint nothing ----------

def test_stable_values_inside_the_band_mint_nothing(conn):
    seed_stable_days(conn, date(2026, 6, 21), 14, outlier_minor=101_000)  # inside
    engine.evaluate(conn, {"metrics": [day_metric()]}, now=NOW)
    assert drift_mode_of(conn, "daily-sales", "2026-07-05") == "banded"
    assert conn.execute("SELECT count(*) c FROM findings").fetchone()["c"] == 0


# ---------- the mode reaches the surface: the self-report carries it ----------

def test_the_self_report_states_each_rows_drift_mode_in_plain_words(conn):
    for month in ("2026-04", "2026-05", "2026-06"):
        seed_sales(conn, month, 100_000)
    engine.evaluate(conn, {"metrics": [month_metric()]}, now=NOW)
    row = conn.execute("SELECT last_run FROM parts WHERE part='watching'").fetchone()
    assert "drift_modes" in row["last_run"]
    assert "warming up (2 of 6)" in row["last_run"]
    assert "0 banded, 1 warming up" in row["last_run"]
