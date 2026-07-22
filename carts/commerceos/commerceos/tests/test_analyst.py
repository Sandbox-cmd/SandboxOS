"""F3 — the analyst's checks: each ruled hunt over seeded facts finds its
planted pattern and mints a finding whose evidence cites real rows; both
directions by construction (a planted slump mints risk, a planted surge
mints opportunity); thin data mints nothing and says why in the tally;
a candidate stripped of evidence is dropped — the mint law holds; a
repeated pattern refreshes its open finding instead of flooding; the
configured subset is honored; and the rhythm seam runs the job — with
the real demostore row shipped disabled (arming is the owner's)."""

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from commerceos.db import connect
from commerceos.rhythm import runner
from commerceos.spine.schema import ensure_schema as ensure_facts
from commerceos.watching import analyst, findings
from commerceos.watching.schema import ensure_schema

REPO = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO / "stores" / "demostore" / "rhythm.json"

NOW = datetime(2026, 7, 11, 12, 0, 0, tzinfo=timezone.utc)  # a Saturday
FRESH = NOW.isoformat(timespec="seconds")
THIS_MONDAY = "2026-07-06"   # the latest week orders land in
PRIOR_MONDAY = "2026-06-29"  # the week before


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "analyst.db")
    ensure_facts(c)
    ensure_schema(c)
    yield c
    c.close()


@pytest.fixture()
def fake_home(monkeypatch, tmp_path):
    """a tmp HOME so the rhythm's registry refresh never reads real plists."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


# ---------- seeding: facts the way the spine lands them ----------

def seed_product(conn, pid, ptype="", title=None, description_len=None,
                 seo_title=None, media=0):
    conn.execute(
        "INSERT INTO products (shopify_id, title, product_type, vendor,"
        " description_len, seo_title, source, fetched_at)"
        " VALUES (?, ?, ?, '', ?, ?, 'test:seed', ?)",
        (pid, title or pid, ptype, description_len, seo_title, FRESH))
    if media:
        conn.execute(
            "INSERT INTO product_media (product_id, media_count, source, fetched_at)"
            " VALUES (?, ?, 'test:seed', ?)", (pid, media, FRESH))
    conn.commit()


def seed_variant(conn, vid, pid):
    conn.execute(
        "INSERT INTO variants (shopify_id, product_id, source, fetched_at)"
        " VALUES (?, ?, 'test:seed', ?)", (vid, pid, FRESH))
    conn.commit()


def seed_order(conn, oid, placed, lines):
    """lines: [(variant_id, vendor, qty, net_minor)] -> order_line ids."""
    net = sum(l[3] for l in lines)
    conn.execute(
        "INSERT INTO orders (shopify_id, number, placed_at, gross_minor, net_minor,"
        " source, fetched_at) VALUES (?, ?, ?, ?, ?, 'test:seed', ?)",
        (oid, oid, placed, net, net, FRESH))
    ids = []
    for vid, vendor, qty, net_minor in lines:
        cur = conn.execute(
            "INSERT INTO order_lines (order_id, variant_id, vendor, qty,"
            " unit_price_minor, net_minor, take_rate_bps, take_minor, payable_minor,"
            " rate_source) VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, 'test:seed')",
            (oid, vid, vendor, qty, net_minor, net_minor, net_minor))
        ids.append(cur.lastrowid)
    conn.commit()
    return ids


def seed_week(conn, prefix, monday, n_orders, vid, vendor, net_each, qty=1):
    """n single-line orders spread across the week starting monday."""
    start = date.fromisoformat(monday)
    ids = []
    for i in range(n_orders):
        placed = (start + timedelta(days=i % 7)).isoformat()
        ids += seed_order(conn, f"{prefix}{i}", placed, [(vid, vendor, qty, net_each)])
    return ids


def seed_refund(conn, rid, line_id, refunded_at, amount):
    oid = conn.execute("SELECT order_id FROM order_lines WHERE id = ?",
                       (line_id,)).fetchone()["order_id"]
    conn.execute(
        "INSERT INTO returns (shopify_id, order_id, refunded_at, amount_minor,"
        " source, fetched_at) VALUES (?, ?, ?, ?, 'test:seed', ?)",
        (rid, oid, refunded_at, amount, FRESH))
    cur = conn.execute(
        "INSERT INTO return_lines (return_id, order_line_id, qty, amount_minor,"
        " take_reversed_minor, payable_reversed_minor) VALUES (?, ?, 1, ?, 0, ?)",
        (rid, line_id, amount, amount))
    conn.commit()
    return cur.lastrowid


def assert_refs_are_real_rows(conn, refs, table):
    """every evidence ref names an actual landed row — provenance, checked."""
    for ref in refs:
        t, _, rid = ref.partition(":")
        if t != table:
            continue
        assert conn.execute(f"SELECT 1 FROM {table} WHERE"  # noqa: S608 — test, fixed tables
                            f" {'id' if table != 'products' else 'shopify_id'} = ?",
                            (rid,)).fetchone(), f"{ref} names no landed row"


# ---------- hunts 1 + 2: sales shifts, both directions by construction ----------

def test_category_slump_mints_a_risk_citing_the_real_lines(conn):
    seed_product(conn, "P1", ptype="boots")
    seed_variant(conn, "V1", "P1")
    prior = seed_week(conn, "a", PRIOR_MONDAY, 5, "V1", "Acme", 10_000)
    this = seed_week(conn, "b", THIS_MONDAY, 5, "V1", "Acme", 2_000)  # -80%
    tally = analyst.run_hunts(conn, {"hunts": ["category_sales_shift"]}, now=NOW)
    assert tally == {"category_sales_shift": {
        "found": 1, "minted": 1, "refreshed": 0,
        "skipped_no_evidence": 0, "not_enough_data": 0}}
    rows = findings.query(conn, metric="analyst.category_sales_shift")
    assert len(rows) == 1
    f = rows[0]
    assert f["direction"] == "risk" and f["route"] == "owner"
    assert f["slice"] == "category=boots"
    assert "-80%" in f["sentence"] and THIS_MONDAY in f["sentence"]
    refs = f["evidence"]["facts"]
    assert set(refs) == {f"order_lines:{i}" for i in prior + this}
    assert_refs_are_real_rows(conn, refs, "order_lines")


def test_category_surge_mints_an_opportunity(conn):
    seed_product(conn, "P1", ptype="boots")
    seed_variant(conn, "V1", "P1")
    seed_week(conn, "a", PRIOR_MONDAY, 5, "V1", "Acme", 2_000)
    seed_week(conn, "b", THIS_MONDAY, 5, "V1", "Acme", 10_000)  # +400%
    analyst.run_hunts(conn, {"hunts": ["category_sales_shift"]}, now=NOW)
    (f,) = findings.query(conn, metric="analyst.category_sales_shift")
    assert f["direction"] == "opportunity"
    assert "+400%" in f["sentence"]


def test_vendor_shift_slices_by_the_line_vendor(conn):
    # vendor rides the order line itself — no variant needed
    seed_week(conn, "a", PRIOR_MONDAY, 6, None, "Summit Gear", 8_000)
    seed_week(conn, "b", THIS_MONDAY, 6, None, "Summit Gear", 4_000)  # -50%
    tally = analyst.run_hunts(conn, {"hunts": ["vendor_sales_shift"]}, now=NOW)
    assert tally["vendor_sales_shift"]["minted"] == 1
    (f,) = findings.query(conn, metric="analyst.vendor_sales_shift")
    assert f["direction"] == "risk" and f["slice"] == "vendor=Summit Gear"
    assert "Summit Gear" in f["sentence"]
    assert_refs_are_real_rows(conn, f["evidence"]["facts"], "order_lines")


# ---------- hunt 3: basket pairings ----------

def test_basket_pairings_finds_what_sells_together(conn):
    seed_product(conn, "PA", ptype="boots", title="Trail Boot")
    seed_product(conn, "PB", ptype="socks", title="Wool Sock")
    seed_variant(conn, "VA", "PA")
    seed_variant(conn, "VB", "PB")
    line_ids = []
    for i in range(3):  # the pair lands together in 3 orders
        line_ids += seed_order(conn, f"o{i}", f"2026-07-0{6 + i}",
                               [("VA", "Acme", 1, 5_000), ("VB", "Acme", 1, 1_000)])
    tally = analyst.run_hunts(conn, {"hunts": ["basket_pairings"]}, now=NOW)
    assert tally["basket_pairings"]["minted"] == 1
    (f,) = findings.query(conn, metric="analyst.basket_pairings")
    assert f["direction"] == "insight" and f["route"] == "catalog"
    assert f["slice"] == "pair=PA+PB"
    assert "Trail Boot" in f["sentence"] and "Wool Sock" in f["sentence"]
    assert "3 orders" in f["sentence"]
    assert set(f["evidence"]["facts"]) == {f"order_lines:{i}" for i in line_ids}


def test_a_pair_seen_too_rarely_makes_no_claim(conn):
    seed_product(conn, "PA", ptype="boots")
    seed_product(conn, "PB", ptype="socks")
    seed_variant(conn, "VA", "PA")
    seed_variant(conn, "VB", "PB")
    seed_order(conn, "o1", "2026-07-06", [("VA", "Acme", 1, 5_000), ("VB", "Acme", 1, 1_000)])
    tally = analyst.run_hunts(conn, {"hunts": ["basket_pairings"]}, now=NOW)
    assert tally["basket_pairings"] == {"found": 0, "minted": 0, "refreshed": 0,
                                       "skipped_no_evidence": 0, "not_enough_data": 0}
    assert findings.query(conn) == []


# ---------- hunt 4: AOV drift by category ----------

def test_aov_drop_mints_a_risk(conn):
    seed_product(conn, "P1", ptype="packs")
    seed_variant(conn, "V1", "P1")
    seed_week(conn, "a", PRIOR_MONDAY, 5, "V1", "Acme", 10_000)  # AOV 100 AED
    seed_week(conn, "b", THIS_MONDAY, 5, "V1", "Acme", 6_000)    # AOV 60 AED, -40%
    tally = analyst.run_hunts(conn, {"hunts": ["aov_drift"]}, now=NOW)
    assert tally["aov_drift"]["minted"] == 1
    (f,) = findings.query(conn, metric="analyst.aov_drift")
    assert f["direction"] == "risk" and f["slice"] == "category=packs"
    assert "-40%" in f["sentence"] and "average order value" in f["sentence"]
    assert_refs_are_real_rows(conn, f["evidence"]["facts"], "order_lines")


# ---------- hunt 5: return-rate drift by category ----------

def test_return_rate_jump_mints_a_risk_citing_the_refund_rows(conn):
    seed_product(conn, "P1", ptype="tents")
    seed_variant(conn, "V1", "P1")
    seed_week(conn, "a", PRIOR_MONDAY, 5, "V1", "Acme", 10_000)  # no refunds
    this = seed_week(conn, "b", THIS_MONDAY, 5, "V1", "Acme", 10_000)
    rl = seed_refund(conn, "r1", this[0], "2026-07-08", 6_000)  # 12% of the week
    tally = analyst.run_hunts(conn, {"hunts": ["return_rate_drift"]}, now=NOW)
    assert tally["return_rate_drift"]["minted"] == 1
    (f,) = findings.query(conn, metric="analyst.return_rate_drift")
    assert f["direction"] == "risk" and f["slice"] == "category=tents"
    assert "12%" in f["sentence"] and "0%" in f["sentence"]
    assert f"return_lines:{rl}" in f["evidence"]["facts"]
    assert_refs_are_real_rows(conn, f["evidence"]["facts"], "order_lines")
    assert_refs_are_real_rows(conn, f["evidence"]["facts"], "return_lines")


# ---------- hunt 6: catalog health vs sales ----------

def _seed_health_groups(conn, n_healthy=10, n_thin=10,
                        healthy_units=5, thin_units=1):
    for i in range(n_healthy):
        pid = f"H{i}"
        seed_product(conn, pid, ptype="gear", description_len=500,
                     seo_title="titled", media=2)
        seed_variant(conn, f"vh{i}", pid)
        seed_order(conn, f"oh{i}", "2026-07-06", [(f"vh{i}", "Acme", healthy_units, 5_000)])
    for i in range(n_thin):
        pid = f"T{i}"
        seed_product(conn, pid, ptype="gear")  # no media, no description, no seo
        seed_variant(conn, f"vt{i}", pid)
        seed_order(conn, f"ot{i}", "2026-07-06", [(f"vt{i}", "Acme", thin_units, 5_000)])


def test_health_vs_sales_correlation_mints_an_insight(conn):
    _seed_health_groups(conn)
    tally = analyst.run_hunts(conn, {"hunts": ["catalog_health_vs_sales"]}, now=NOW)
    assert tally["catalog_health_vs_sales"]["minted"] == 1
    (f,) = findings.query(conn, metric="analyst.catalog_health_vs_sales")
    assert f["direction"] == "insight" and f["route"] == "catalog"
    assert "healthier listings" in f["sentence"]
    assert "not a cause" in f["sentence"]  # a correlation, said plainly
    refs = f["evidence"]["facts"]
    assert len(refs) == 20  # every product in both groups is the evidence
    assert_refs_are_real_rows(conn, refs, "products")


def test_health_vs_sales_with_thin_groups_reports_not_enough_data(conn):
    _seed_health_groups(conn, n_healthy=3, n_thin=3)  # below min_group 10
    tally = analyst.run_hunts(conn, {"hunts": ["catalog_health_vs_sales"]}, now=NOW)
    assert tally["catalog_health_vs_sales"] == {
        "found": 0, "minted": 0, "refreshed": 0,
        "skipped_no_evidence": 0, "not_enough_data": 1}
    assert findings.query(conn) == []  # nothing minted — never a provenance-free guess


# ---------- honesty: thin data, empty stores, the mint law ----------

def test_a_big_shift_on_thin_data_mints_nothing_and_says_why(conn):
    seed_product(conn, "P1", ptype="boots")
    seed_variant(conn, "V1", "P1")
    seed_week(conn, "a", PRIOR_MONDAY, 2, "V1", "Acme", 10_000)  # only 2 orders
    seed_week(conn, "b", THIS_MONDAY, 2, "V1", "Acme", 1_000)    # -90%, but thin
    tally = analyst.run_hunts(conn, {"hunts": ["category_sales_shift"]}, now=NOW)
    assert tally["category_sales_shift"] == {
        "found": 0, "minted": 0, "refreshed": 0,
        "skipped_no_evidence": 0, "not_enough_data": 1}
    assert findings.query(conn) == []


def test_all_six_hunts_over_an_empty_store_mint_nothing(conn):
    tally = analyst.run_hunts(conn, {}, now=NOW)
    assert set(tally) == set(analyst.HUNTS)
    for t in tally.values():
        assert t["minted"] == 0 and t["found"] == 0
        assert t["not_enough_data"] == 1  # every hunt says why it stayed silent
    assert findings.query(conn) == []


def test_a_candidate_stripped_of_evidence_is_dropped_never_minted(conn, monkeypatch):
    def bare_claim(conn_, jcfg):
        return {"candidates": [{
            "metric": "analyst.bogus", "slice": "", "direction": "risk",
            "route": "owner", "sentence": "a claim naming no rows",
            "evidence": {"evaluations": [], "facts": []},
        }], "not_enough_data": 0}
    monkeypatch.setitem(analyst.HUNTS, "bogus", bare_claim)
    tally = analyst.run_hunts(conn, {"hunts": ["bogus"]}, now=NOW)
    assert tally["bogus"]["skipped_no_evidence"] == 1
    assert tally["bogus"]["minted"] == 0
    assert findings.query(conn) == []
    # and the door itself holds, independent of the pre-check
    with pytest.raises(ValueError, match="no provenance"):
        findings.mint(conn, "a claim naming no rows", "risk",
                      {"evaluations": [], "facts": []})


def test_run_hunts_honors_the_configured_subset_and_refuses_unknown_names(conn):
    seed_product(conn, "P1", ptype="boots")
    seed_variant(conn, "V1", "P1")
    seed_week(conn, "a", PRIOR_MONDAY, 5, "V1", "Acme", 10_000)
    seed_week(conn, "b", THIS_MONDAY, 5, "V1", "Acme", 2_000)  # category AND vendor shift
    tally = analyst.run_hunts(conn, {"hunts": ["vendor_sales_shift"]}, now=NOW)
    assert list(tally) == ["vendor_sales_shift"]
    assert findings.query(conn, metric="analyst.category_sales_shift") == []
    assert len(findings.query(conn, metric="analyst.vendor_sales_shift")) == 1
    with pytest.raises(ValueError, match="unknown hunt"):
        analyst.run_hunts(conn, {"hunts": ["nonsense"]})


def test_a_persisting_pattern_refreshes_its_open_finding_never_floods(conn):
    seed_product(conn, "P1", ptype="boots")
    seed_variant(conn, "V1", "P1")
    seed_week(conn, "a", PRIOR_MONDAY, 5, "V1", "Acme", 10_000)
    seed_week(conn, "b", THIS_MONDAY, 5, "V1", "Acme", 2_000)
    analyst.run_hunts(conn, {"hunts": ["category_sales_shift"]}, now=NOW)
    tally = analyst.run_hunts(conn, {"hunts": ["category_sales_shift"]},
                              now=NOW + timedelta(days=1))
    assert tally["category_sales_shift"]["minted"] == 0
    assert tally["category_sales_shift"]["refreshed"] == 1
    assert len(findings.query(conn, metric="analyst.category_sales_shift")) == 1


# ---------- the rhythm seam ----------

def test_the_demostore_row_ships_disabled_and_the_builtin_exists():
    assert "analyst" in runner.BUILTIN_JOBS
    cfg = json.loads(CONFIG_PATH.read_text())
    row = runner.job_configs(cfg)["analyst"]
    assert row["enabled"] is False  # nothing arms itself; arming is the owner's
    assert runner.parse_cadence(row["cadence"]) == 86400
    assert runner.resolve_job("analyst", row) is runner.BUILTIN_JOBS["analyst"]


def test_run_one_runs_the_analyst_job_and_records_the_outcome(conn, fake_home):
    seed_product(conn, "P1", ptype="boots")
    seed_variant(conn, "V1", "P1")
    seed_week(conn, "a", PRIOR_MONDAY, 5, "V1", "Acme", 10_000)
    seed_week(conn, "b", THIS_MONDAY, 5, "V1", "Acme", 2_000)
    cfg = {"jobs": {"analyst": {"cadence": "1d", "enabled": False,
                                "hunts": ["category_sales_shift"]}}}
    out = runner.run_one(conn, "analyst", cfg, now=NOW)  # the owner's keystroke
    assert out["ok"] is True
    assert "1 findings minted" in out["summary"]
    assert runner.state_rows(conn)["analyst"]["ok"] == 1
    assert len(findings.query(conn, metric="analyst.category_sales_shift")) == 1


def test_a_tick_with_an_enabled_test_row_runs_the_hunts(conn, fake_home):
    # a TEST config only — the real demostore row stays disabled
    seed_product(conn, "P1", ptype="boots")
    seed_variant(conn, "V1", "P1")
    seed_week(conn, "a", PRIOR_MONDAY, 5, "V1", "Acme", 2_000)
    seed_week(conn, "b", THIS_MONDAY, 5, "V1", "Acme", 10_000)  # a surge
    cfg = {"jobs": {"analyst": {"cadence": "1d", "enabled": True,
                                "hunts": ["category_sales_shift"]}}}
    out = runner.tick(conn, cfg, now=NOW)
    assert out["results"]["analyst"]["ran"] is True and out["failed"] == []
    (f,) = findings.query(conn, metric="analyst.category_sales_shift")
    assert f["direction"] == "opportunity"  # the surge side of the same code path
