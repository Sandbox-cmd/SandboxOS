"""P-W's checks: the product half of the watching work.

hunt findings render on /findings as first-class findings — the plain hunt
label (never the raw analyst.<hunt> metric key), direction, lifecycle state,
age, and an honest evidence count, through the SAME columns an engine
finding gets. and the parts view renders each watch row's drift mode from
the watching's own self-report — "banded" or "warming up (n of N)" per
metric row, in plain words, not just the summary count.

all reads served through the TestClient over a seeded temp db (the pattern
from test_web_surface / test_catalog_dashboard).
"""

import re
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from commerceos.db import connect
from commerceos.spine.schema import ensure_schema as ensure_facts
from commerceos.watching import findings
from commerceos.watching.analyst import HUNTS
from commerceos.watching.schema import ensure_schema as ensure_watching
from commerceos.web.app import HUNT_LABELS, app


@pytest.fixture()
def env(tmp_path, monkeypatch):
    db = tmp_path / "watching-surface.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    conn = connect(db)
    ensure_facts(conn)
    ensure_watching(conn)
    yield conn, TestClient(app)
    conn.close()


def _visible_text(html: str) -> str:
    """the text a person actually reads — tags stripped, as in the guard."""
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", html)


# --- hunt findings are first-class on /findings ------------------------------

def test_a_hunt_finding_renders_first_class_with_a_plain_label(env):
    conn, client = env
    findings.mint(
        conn,
        "category Flashlights net sales for the week of 2026-07-06 are 900 AED,"
        " -45% vs 1,600 AED the week before (6 vs 7 orders)",
        "risk",
        {"evaluations": [], "facts": ["order_lines:1", "order_lines:2", "order_lines:3"]},
        route="owner", metric="analyst.category_sales_shift",
        slice_="category=Flashlights")

    page = client.get("/findings")
    assert page.status_code == 200
    text = _visible_text(page.text)
    # the hunt is named in plain words; the raw metric key never appears at all
    assert "category sales shift" in text
    assert "analyst.category_sales_shift" not in page.text
    # the slice in plain words, not the key=value code shape
    assert "category Flashlights" in text
    assert "category=Flashlights" not in text
    # direction, lifecycle state, aging, and route render as for any finding
    assert "risk" in text and "noticed" in text and "owner" in text
    # age in plain words — never a decimal with a unit letter
    assert "under a day" in text and "0.0d" not in text
    # the evidence counted honestly — the three cited fact rows, never their ids
    assert "3 landed facts" in text
    assert "order_lines:1" not in text


def test_an_engine_finding_rides_the_same_columns(env):
    conn, client = env
    findings.mint(
        conn,
        "monthly-sales at 45,000 for 2026-06 is outside its usual range",
        "opportunity",
        {"evaluations": [7, 8], "facts": ["money_lines@2026-06 rows=12"]},
        route="owner", metric="monthly-sales", slice_="")

    text = _visible_text(client.get("/findings").text)
    # the watch row's name in plain words, its evidence counted the same way —
    # and a sentence stored with the raw metric key translates at render
    assert "monthly sales at 45,000" in text
    assert "monthly-sales" not in text
    assert "2 readings" in text and "1 landed fact" in text


def test_an_aged_out_finding_reads_plainly(env):
    conn, client = env
    findings.mint(
        conn, "vendor Acme net sales surged and nobody acted", "opportunity",
        {"evaluations": [], "facts": ["order_lines:9"]},
        metric="analyst.vendor_sales_shift", slice_="vendor=Acme",
        now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert findings.age_out(conn) == 1

    text = _visible_text(client.get("/findings").text)
    assert "aged out" in text
    assert "aged_out" not in text


def test_every_ruled_hunt_carries_a_plain_label(env):
    # a new hunt must land with its plain words — the map and the registry
    # move together, and no label smuggles an identifier onto the screen.
    assert set(HUNT_LABELS) == set(HUNTS)
    for label in HUNT_LABELS.values():
        assert "_" not in label and "." not in label


# --- the parts view states each watch row's drift mode -----------------------

def _seed_evaluation(conn, metric, slice_, period, value, drift_mode):
    conn.execute(
        "INSERT INTO evaluations (metric, slice, period, value, baseline, delta,"
        " facts_window, stale, ts, drift_mode) VALUES (?, ?, ?, ?, NULL, NULL,"
        " '{}', 0, '2026-07-18T00:00:00+00:00', ?)",
        (metric, slice_, period, value, drift_mode))


def test_parts_view_renders_each_watch_rows_drift_mode_in_plain_words(env):
    conn, client = env
    _seed_evaluation(conn, "return-rate", "vendor=Acme", "2026-06", 0.08, "banded")
    _seed_evaluation(conn, "monthly-sales", "", "2026-06", 45000,
                     "warming up (3 of 6)")
    conn.commit()

    page = client.get("/parts")
    assert page.status_code == 200
    text = _visible_text(page.text)
    # each metric row states how its change is judged — not just the summary
    # count, and never in trade words ("banded" / "warming up (n of N)")
    assert "each watched number" in text
    assert "how change is judged" in text
    assert "return rate · vendor Acme" in text
    assert "judged against its own history's band" in text
    # the warm-up names the row's own drift percentage (monthly-sales
    # carries drift_pct 30 in the store's watch-list), never a hardcoded one
    assert "monthly sales" in text
    assert "still learning its normal — 3 of 6 readings; "         "a plain 30% line carries it meanwhile" in text
    # the raw row label (metric[slice], key=value) never reaches the screen
    assert "return-rate[vendor=Acme]" not in page.text
    # the summary count still rides along
    assert "1 banded, 1 warming up" in text


def test_parts_view_absence_speaks_when_no_evaluation_carries_a_mode(env):
    """blocker 1 (coldread 2026-07-18): evaluations that predate the
    drift_mode column render an honest absence line, never a silent gap."""
    conn, client = env
    _seed_evaluation(conn, "monthly-sales", "", "2026-06", 45000, None)
    conn.commit()

    text = _visible_text(client.get("/parts").text)
    assert "drift modes not yet known — no evaluation since modes were added" in text
    assert "each watched number" not in text  # no half-empty table pretends


# --- the evidence opens onward: the finding detail view ----------------------

def test_evidence_links_to_a_detail_view_with_plain_rows(env):
    conn, client = env
    _seed_evaluation(conn, "monthly-sales", "", "2026-06", 45000, "banded")
    conn.commit()
    eid = conn.execute("SELECT id FROM evaluations").fetchone()["id"]
    fid = findings.mint(
        conn, "monthly-sales at 45,000 for 2026-06 is outside its usual range",
        "opportunity",
        {"evaluations": [eid], "facts": ["money_lines@2026-06 rows=12"]},
        route="owner", metric="monthly-sales", slice_="")

    page = client.get("/findings")
    assert f"/findings?finding={fid}" in page.text  # the count opens onward

    detail = client.get(f"/findings?finding={fid}")
    assert detail.status_code == 200
    text = _visible_text(detail.text)
    assert "one finding, opened" in text
    # the cited reading, laid out in plain words with its number
    assert "monthly sales" in text and "2026-06" in text and "45,000" in text
    # the fact reference translated — no snake_case identifier on screen
    assert "money lines · 2026-06 · 12 rows read" in text
    assert "money_lines" not in text
    # an open finding offers the recorded decide action
    assert "record the decision" in text


def test_deciding_a_finding_is_recorded_with_its_reason(env):
    conn, client = env
    fid = findings.mint(
        conn, "vendor Acme returns crept past the 12% bar", "risk",
        {"evaluations": [], "facts": ["order_lines:5"]},
        metric="analyst.return_rate_drift", slice_="vendor=Acme")

    resp = client.post(f"/findings/{fid}/decide",
                       data={"reason": "raised the vendor with a return-window change"},
                       follow_redirects=False)
    assert resp.status_code == 303
    row = findings.get(conn, fid)
    assert row["disposition"] == "decided"
    assert row["decided_reason"] == "raised the vendor with a return-window change"
    text = _visible_text(client.get(f"/findings?finding={fid}").text)
    assert "decided" in text and "return-window change" in text
    # a decision without a reason is refused
    bare = client.post(f"/findings/{fid}/decide", follow_redirects=False)
    assert bare.status_code == 400


# --- stale inputs are said on the page ---------------------------------------

def test_findings_page_names_the_watch_rows_on_stale_facts(env):
    conn, client = env
    conn.execute(
        "INSERT INTO evaluations (metric, slice, period, value, baseline, delta,"
        " facts_window, stale, ts) VALUES ('return-rate', '', '2026-07', NULL,"
        " NULL, NULL, '{}', 1, '2026-07-18T00:00:00+00:00')")
    _seed_evaluation(conn, "monthly-sales", "", "2026-06", 45000, "banded")
    conn.commit()

    text = _visible_text(client.get("/findings").text)
    assert "1 of 2 watched numbers rest on stale facts" in text
    assert "return rate" in text
    assert "return-rate" not in text  # the plain name, never the slug


# --- newly minted engine sentences are plain ---------------------------------

def test_the_engine_mints_plain_labels_into_sentences():
    from commerceos.watching.engine import _plain_label
    assert _plain_label("monthly-sales", "") == "monthly sales"
    assert _plain_label("vendor-return-rate", "vendor=Acme") ==         "vendor return rate · vendor Acme"
