"""E2+E3's checks under the fresh-start ruling (landed 2026-07-11): two
explicit lanes. learnings — the old company's FTA/Zoho history (source
'fta:'/'zoho:'), read-only reference and the engine-correctness proof.
company — the fresh entity's own facts, honestly at zero today. a
learnings row never appears in company P&L and vice versa; the default
lane is company; the only combined view wears the "learnings overlay"
label; the learnings reconcile stays green on the real archive; the
company reconcile exits 2 with an honest message until the new entity's
first period."""

import json
import os
from pathlib import Path

import pytest

from commerceos.db import connect
from commerceos.economics import engine, reconcile, status
from commerceos.spine.schema import ensure_schema
from commerceos.spine.settlement import split, unwind
from commerceos.web import registry

REPO = Path(__file__).resolve().parents[1]
REAL_DB = REPO / "data" / "demostore.db"
REAL_CONFIG = REPO / "stores" / "demostore" / "economics.json"

FETCHED = "2026-07-11T00:00:00+00:00"
COMPANY_GAPS_TODAY = {"books_sales", "books_purchases", "gross_spread",
                      "settlement", "payouts", "fees", "ad_spend",
                      "po_purchases"}  # SP1: the supplier form's COGS input


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "test.db")
    ensure_schema(c)
    yield c
    c.close()


def _books(conn, date, account, amount_minor, source="fta:test-fixture"):
    """a books money_line; source decides the lane (fta:/zoho: = learnings)."""
    cur = conn.execute(
        "INSERT INTO money_lines (date, kind, account, amount_minor, currency,"
        " external_ref, import_batch, source, fetched_at)"
        " VALUES (?, 'books', ?, ?, 'AED', ?, 'testbatch', ?, ?)",
        (date, account, amount_minor, f"{source}-{account}-{date}-{amount_minor}",
         source, FETCHED))
    conn.commit()
    return cur.lastrowid


def _order(conn, oid, placed_at, lines, source="test:fixture"):
    """land a synthetic order the way the spine does: split at landing."""
    net = sum(line_net for _, line_net, _ in lines)
    conn.execute(
        "INSERT INTO orders (shopify_id, number, placed_at, currency, gross_minor,"
        " net_minor, source, fetched_at) VALUES (?, ?, ?, 'AED', ?, ?, ?, ?)",
        (oid, oid, placed_at, net, net, source, FETCHED))
    ids = []
    for vendor, line_net, bps in lines:
        take, payable = split(line_net, bps)
        cur = conn.execute(
            "INSERT INTO order_lines (order_id, vendor, qty, unit_price_minor, net_minor,"
            " take_rate_bps, take_minor, payable_minor, rate_source)"
            " VALUES (?, ?, 1, ?, ?, ?, ?, ?, 'default')",
            (oid, vendor, line_net, line_net, bps, take, payable))
        ids.append(cur.lastrowid)
    conn.commit()
    return ids


def _full_return(conn, rid, order_line_id, refunded_at):
    row = conn.execute("SELECT * FROM order_lines WHERE id = ?", (order_line_id,)).fetchone()
    take_rev, payable_rev = unwind(row["net_minor"], row["net_minor"], row["take_minor"])
    conn.execute(
        "INSERT INTO returns (shopify_id, order_id, refunded_at, amount_minor, source,"
        " fetched_at) VALUES (?, ?, ?, ?, 'test:fixture', ?)",
        (rid, row["order_id"], refunded_at, row["net_minor"], FETCHED))
    conn.execute(
        "INSERT INTO return_lines (return_id, order_line_id, qty, amount_minor,"
        " take_reversed_minor, payable_reversed_minor) VALUES (?, ?, 1, ?, ?, ?)",
        (rid, order_line_id, row["net_minor"], take_rev, payable_rev))
    conn.commit()


def _seed_2024_learnings_books(conn):
    """sales 1,000,000 fils · purchases 800,000 -> spread 200,000 = 20.0000%."""
    for date, amount in (("2024-01-15", 400_000), ("2024-05-02", 350_000), ("2024-11-20", 250_000)):
        _books(conn, date, "sales", amount)
    for date, amount in (("2024-02-01", 500_000), ("2024-09-09", 300_000)):
        _books(conn, date, "purchases", amount)


# ---------- engine: P&L math, provenance, gaps (learnings lane) ----------


def test_pnl_books_math_exact_and_period_bounded(conn):
    _books(conn, "2025-01-05", "sales", 100_000)
    _books(conn, "2025-06-30", "sales", 25_000)
    _books(conn, "2025-03-10", "purchases", 40_000)
    _books(conn, "2024-12-31", "sales", 999_999)  # outside the year
    _books(conn, "2026-01-01", "sales", 777)      # end is exclusive

    cells = engine.assemble(conn, "2025", lane="learnings")["cells"]
    assert cells["books_sales"]["value"] == 125_000
    assert cells["books_sales"]["sources"][0]["count"] == 2
    assert cells["books_purchases"]["value"] == 40_000
    assert cells["gross_spread"]["value"] == 85_000
    assert cells["gross_margin_bps"]["value"] == 6_800  # 85,000 / 125,000 exactly

    # month and quarter periods cut the same facts differently
    june = engine.assemble(conn, "2025-06", lane="learnings")
    assert june["cells"]["books_sales"]["value"] == 25_000
    assert "books_purchases" not in june["cells"]  # no June purchases -> gap
    q1 = engine.assemble(conn, "2025-Q1", lane="learnings")["cells"]
    assert q1["books_sales"]["value"] == 100_000
    assert q1["gross_margin_bps"]["value"] == 6_000

    with pytest.raises(ValueError):
        engine.parse_period("last-summer")


def test_every_cell_carries_provenance_down_to_fact_ids(conn):
    sale_ids = [_books(conn, "2025-01-05", "sales", 100_000),
                _books(conn, "2025-06-30", "sales", 25_000)]
    buy_id = _books(conn, "2025-03-10", "purchases", 40_000)

    pnl = engine.assemble(conn, "2025", lane="learnings")
    cells = pnl["cells"]
    assert cells["books_sales"]["sources"][0]["ids"] == sale_ids
    assert cells["books_purchases"]["sources"][0]["ids"] == [buy_id]
    for cell in cells.values():
        sources = cell.get("sources", [])
        derived = cell.get("derived_from", [])
        assert sources or derived, f"{cell['name']} cites nothing"
        for s in sources:
            assert s["table"] and s["query"] and s["count"] >= 1
        for d in derived:
            assert d in cells, f"{cell['name']} derives from a cell that does not render"
    assert engine.audit_provenance(pnl) == []  # zero orphan numbers


# ---------- the two lanes ----------


def test_company_lane_today_is_empty_but_real(conn):
    """the fresh-start ruling: zero orders, named gaps — empty but real,
    even with the old company's history landed in the same period."""
    _books(conn, "2026-02-01", "sales", 500_000)                 # fta: learnings
    _books(conn, "2026-02-02", "purchases", 100_000, source="zoho:export")

    pnl = engine.assemble(conn, "2026")  # default lane
    assert pnl["lane"] == "company"
    assert pnl["cells"] == {}                                    # nothing invented
    gaps = {g["name"]: g for g in pnl["gaps"]}
    assert set(gaps) == COMPANY_GAPS_TODAY                       # every input named
    assert "no orders landed yet" in gaps["settlement"]["reason"]
    assert "no company books facts" in gaps["books_sales"]["reason"]
    for g in pnl["gaps"]:
        assert g["name"] and g["reason"]

    # 'full' on the company lane has no books span to invent
    full = engine.assemble(conn, "full", lane="company")
    assert full["cells"] == {} and full["start"] is None
    assert "no company books facts landed" in full["gaps"][0]["reason"]


def test_lane_separation_learnings_never_meets_company(conn):
    """the ruling, encoded: a learnings row never appears in company P&L
    and a company row never appears in learnings P&L."""
    fta_id = _books(conn, "2025-03-01", "sales", 100_000)                     # learnings
    zoho_id = _books(conn, "2025-04-01", "sales", 50_000, source="zoho:export")
    co_id = _books(conn, "2025-05-01", "sales", 7_000, source="company:books-import")
    _order(conn, "ord-co-1", "2025-06-10T12:00:00Z", [("vendor-a", 61_500, 3_250)])

    company = engine.assemble(conn, "2025", lane="company")
    learnings = engine.assemble(conn, "2025", lane="learnings")

    # company P&L: only the company books row, plus the settlement facts
    assert company["cells"]["books_sales"]["value"] == 7_000
    assert company["cells"]["books_sales"]["sources"][0]["ids"] == [co_id]
    assert company["cells"]["take_earned"]["value"] == split(61_500, 3_250)[0]

    # learnings P&L: only the fta:/zoho: rows — and no settlement at all
    assert learnings["cells"]["books_sales"]["value"] == 150_000
    assert learnings["cells"]["books_sales"]["sources"][0]["ids"] == [fta_id, zoho_id]
    assert "take_earned" not in learnings["cells"]
    assert "payable_outstanding" not in learnings["cells"]
    assert all(g["name"] not in ("settlement", "payouts", "fees", "ad_spend")
               for g in learnings["gaps"])

    # the id sets never intersect
    co_ids = set(company["cells"]["books_sales"]["sources"][0]["ids"])
    learn_ids = set(learnings["cells"]["books_sales"]["sources"][0]["ids"])
    assert co_ids.isdisjoint(learn_ids)


def test_default_lane_is_company(conn):
    _books(conn, "2025-03-01", "sales", 100_000)                              # learnings
    _books(conn, "2025-05-01", "sales", 7_000, source="company:books-import")
    _order(conn, "ord-1", "2025-06-10T12:00:00Z", [("vendor-a", 61_500, 3_250)])

    default = engine.assemble(conn, "2025")
    assert default["lane"] == "company"
    assert default == engine.assemble(conn, "2025", lane="company")
    assert default["cells"]["books_sales"]["value"] == 7_000  # never the fta 100,000


def test_combined_view_only_exists_as_labeled_overlay(conn):
    _books(conn, "2025-03-01", "sales", 100_000)
    _books(conn, "2025-05-01", "sales", 7_000, source="company:books-import")

    # merging is not a lane — anything but the two lanes refuses
    for bad in ("both", "combined", "company+learnings", "all"):
        with pytest.raises(ValueError, match="overlay"):
            engine.assemble(conn, "2025", lane=bad)

    ov = engine.overlay(conn, "2025")
    assert ov["label"] == "learnings overlay"                 # the required label
    assert ov["company"]["lane"] == "company"
    assert ov["learnings"]["lane"] == "learnings"
    # side by side, never summed
    assert ov["company"]["cells"]["books_sales"]["value"] == 7_000
    assert ov["learnings"]["cells"]["books_sales"]["value"] == 100_000


# ---------- settlement (company lane) ----------


def test_settlement_aggregates_and_full_return_nets_to_zero(conn):
    [line_id] = _order(conn, "ord-1", "2026-01-10T12:00:00Z", [("vendor-a", 61_500, 3_250)])

    before = engine.assemble(conn, "2026-01")["cells"]
    assert before["take_earned"]["value"] == 19_988       # split(61500, 3250)
    assert before["payable_outstanding"]["value"] == 41_512
    assert before["take_earned"]["sources"][0]["ids"] == [line_id]

    # an order placed outside the period is not this period's settlement
    feb = engine.assemble(conn, "2026-02")
    assert "take_earned" not in feb["cells"]
    assert any(g["name"] == "settlement" for g in feb["gaps"])

    _full_return(conn, "ret-1", line_id, "2026-01-20T09:00:00Z")
    pnl = engine.assemble(conn, "2026-01")
    after = pnl["cells"]
    assert after["take_earned"]["value"] == 0             # measured zero, cited facts
    assert after["payable_outstanding"]["value"] == 0
    assert after["unwinds"]["value"] == 61_500
    assert len(after["take_earned"]["sources"]) == 2      # order lines + return lines
    assert engine.audit_provenance(pnl) == []

    # the settlement never leaks into the learnings lane
    learn = engine.assemble(conn, "2026-01", lane="learnings")
    assert "take_earned" not in learn["cells"] and "unwinds" not in learn["cells"]


def test_reconcile_selftest_roundtrip_nets_to_zero():
    result = reconcile.selftest_roundtrip()
    assert result["ok"] is True
    assert result["take_net"] == 0
    assert result["payable_net"] == 0


# ---------- reconcile: the E3 gate, per lane ----------


def _write_config(tmp_path, anchors, tolerance_bps=50, books_source=None):
    cfg = tmp_path / "economics.json"
    cfg.write_text(json.dumps({
        "learnings": {"anchors": anchors},
        "company": {"books_source": books_source, "first_period": None},
        "tolerance_bps": tolerance_bps}))
    return cfg


def test_learnings_reconcile_passes_within_tolerance_and_writes_report(tmp_path):
    conn = connect(tmp_path / "facts.db")
    ensure_schema(conn)
    _seed_2024_learnings_books(conn)
    # a company-lane row that would blow the tolerance if the lanes ever merged
    _books(conn, "2024-06-01", "sales", 999_999, source="company:books-import")
    conn.close()
    cfg = _write_config(tmp_path, {"fy2024_sales_minor": 1_000_300,  # 3 bps off: within 50
                                   "full_period_spread_pct": 20.0})
    rc = reconcile.main(["--period", "2024", "--db", str(tmp_path / "facts.db"),
                         "--config", str(cfg), "--report-dir", str(tmp_path / "reports")])
    assert rc == 0

    data = json.loads((tmp_path / "reports" / "econ-reconcile-learnings-2024.json").read_text())
    assert data["ok"] is True
    assert data["lane"] == "learnings"
    assert data["meaning"] == "learnings lane: engine proof against the old company's books"
    sales = next(ln for ln in data["lines"] if ln["kind"] == "minor")
    assert (sales["computed_minor"], sales["anchor_minor"], sales["delta_minor"]) == \
        (1_000_000, 1_000_300, -300)                     # the company row stayed out
    spread = next(ln for ln in data["lines"] if ln["kind"] == "pct")
    assert spread["computed_pct"] == 20.0 and spread["delta_bps"] == 0.0
    assert data["selftest"]["ok"] is True

    md = (tmp_path / "reports" / "econ-reconcile-learnings-2024.md").read_text()
    assert "learnings lane: engine proof against the old company's books" in md
    assert "RECONCILED" in md and "NOT RECONCILED" not in md
    assert "10,000.00" in md and "10,003.00" in md  # computed vs anchor, in AED


def test_learnings_reconcile_fails_with_exit_1_beyond_tolerance(tmp_path):
    conn = connect(tmp_path / "facts.db")
    ensure_schema(conn)
    _seed_2024_learnings_books(conn)
    conn.close()
    cfg = _write_config(tmp_path, {"fy2024_sales_minor": 1_100_000,  # ~909 bps off
                                   "full_period_spread_pct": 20.0})
    rc = reconcile.main(["--period", "2024", "--db", str(tmp_path / "facts.db"),
                         "--config", str(cfg), "--report-dir", str(tmp_path / "reports")])
    assert rc == 1

    data = json.loads((tmp_path / "reports" / "econ-reconcile-learnings-2024.json").read_text())
    assert data["ok"] is False
    sales = next(ln for ln in data["lines"] if ln["kind"] == "minor")
    assert sales["ok"] is False and sales["delta_bps"] > 50
    assert "NOT RECONCILED" in (tmp_path / "reports" / "econ-reconcile-learnings-2024.md").read_text()


def test_reconcile_errors_exit_2_on_missing_anchor_or_db(tmp_path):
    conn = connect(tmp_path / "facts.db")
    ensure_schema(conn)
    _seed_2024_learnings_books(conn)
    conn.close()
    cfg = _write_config(tmp_path, {"full_period_spread_pct": 20.0})  # no sales anchor
    assert reconcile.main(["--period", "2024", "--db", str(tmp_path / "facts.db"),
                           "--config", str(cfg), "--report-dir", str(tmp_path / "r")]) == 2
    assert reconcile.main(["--period", "2024", "--db", str(tmp_path / "nowhere.db"),
                           "--config", str(cfg), "--report-dir", str(tmp_path / "r")]) == 2


def test_company_reconcile_is_an_honest_exit_2_stub(tmp_path, capsys):
    """no company books yet — the check refuses to pretend, even over a
    perfectly good facts db full of learnings history."""
    conn = connect(tmp_path / "facts.db")
    ensure_schema(conn)
    _seed_2024_learnings_books(conn)
    conn.close()
    cfg = _write_config(tmp_path, {"fy2024_sales_minor": 1_000_000,
                                   "full_period_spread_pct": 20.0})
    rc = reconcile.main(["--lane", "company", "--db", str(tmp_path / "facts.db"),
                         "--config", str(cfg), "--report-dir", str(tmp_path / "reports")])
    assert rc == 2
    err = capsys.readouterr().err
    assert ("no company books yet — first reconciliation lands with the"
            " new entity's first period") in err
    assert not (tmp_path / "reports").exists()  # a stub writes no report


# ---------- status: the registry row states both lanes ----------


def test_status_states_both_lanes_plainly(conn, tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    learnings_sidecar = reports / "econ-reconcile-learnings-2025.json"
    learnings_sidecar.write_text(json.dumps(
        {"period": "2025", "lane": "learnings", "ok": True,
         "lines": [{"kind": "minor", "delta_minor": 6, "delta_bps": 0.0007, "ok": True}]}))
    # a newer company sidecar (the future) must never shadow the learnings proof
    company_sidecar = reports / "econ-reconcile-company-2027.json"
    company_sidecar.write_text(json.dumps({"period": "2027", "lane": "company",
                                           "ok": False, "lines": []}))
    os.utime(learnings_sidecar, (1, 1))  # force the learnings file older

    status.report_status(conn, reports_dir=reports, period="2025")
    [row] = [p for p in registry.all_parts(conn) if p["part"] == "economics"]
    assert row["state"] == "idle"
    summary = row["last_run"]["summary"]
    assert "learnings lane: engine proof against the old company's books" in summary
    assert "proven" in summary and "+6 fils" in summary
    assert "company lane: at zero" in summary
    assert "awaiting the new entity" in summary
    assert "settlement" in row["last_run"]["gaps"]
    assert "ad_spend" in row["last_run"]["gaps"]

    # a failed learnings proof flips the state, never hides
    learnings_sidecar.write_text(json.dumps(
        {"period": "2025", "lane": "learnings", "ok": False, "lines": []}))
    status.report_status(conn, reports_dir=reports, period="2025")
    [row] = [p for p in registry.all_parts(conn) if p["part"] == "economics"]
    assert row["state"] == "failed"
    assert "FAILED" in row["last_run"]["summary"]


# ---------- your own archive: learnings proven, company at zero ----------
#
# these two only run against a real store database, so they ship as a
# template. they are the checks that prove the economics engine against
# YOUR books — write them once your first period lands.
#
# fill in your period, your anchor (the total your accountant agrees with),
# and your expected gross spread, then delete the comments.
#
# @pytest.mark.skipif(not REAL_DB.is_file(), reason="no live db on this machine")
# def test_real_learnings_lane_reconciles_within_tolerance(tmp_path):
#     """the landed anchors, learnings-lane: your period's sales total and
#     its gross spread as a share of sales, both within tolerance."""
#     rc = reconcile.main(["--period", PERIOD, "--tolerance-bps", "50",
#                          "--db", str(REAL_DB), "--config", str(REAL_CONFIG),
#                          "--report-dir", str(tmp_path)])
#     assert rc == 0
#
#     data = json.loads(
#         (tmp_path / f"econ-reconcile-learnings-{PERIOD}.json").read_text())
#     assert data["lane"] == "learnings"
#     sales = next(ln for ln in data["lines"] if ln["kind"] == "minor")
#     assert sales["computed_minor"] == ANCHOR_SALES_MINOR
#     assert sales["delta_bps"] < 1
#     spread = next(ln for ln in data["lines"] if ln["kind"] == "pct")
#     assert spread["computed_pct"] == pytest.approx(ANCHOR_SPREAD_PCT, abs=0.001)
#     assert spread["delta_bps"] <= 50
#     assert data["selftest"]["ok"] is True
#
#
# @pytest.mark.skipif(not REAL_DB.is_file(), reason="no live db on this machine")
# def test_real_db_company_lane_is_at_zero():
#     """the fresh start on a real archive: everything landed so far belongs
#     to the prior body — the company lane renders empty, every gap named."""
#     conn = reconcile.connect_ro(REAL_DB)
#     try:
#         company = engine.assemble(conn, PERIOD)          # default lane = company
#         learnings = engine.assemble(conn, PERIOD, lane="learnings")
#     finally:
#         conn.close()
#     assert company["lane"] == "company"
#     assert company["cells"] == {}                        # not one old number leaks
#     assert {g["name"] for g in company["gaps"]} == COMPANY_GAPS_TODAY
#     assert learnings["cells"]["books_sales"]["value"] == ANCHOR_SALES_MINOR
