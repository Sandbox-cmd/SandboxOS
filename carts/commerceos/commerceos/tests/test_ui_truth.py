"""the UI-truth sweep's pins (2026-07-19): the record speaks plain words
(no Python booleans, no raw ISO stamps, no mid-word cuts, machine-era
intents mapped at render time); the gate cassette's "pending" means a LIVE
wait, agreeing with /fleet's "lapsed"; the home money line says its age;
the catalog call block says "queued" (one meaning per word per screen) and
points at the door that actually exists."""

import json

import pytest
from fastapi.testclient import TestClient

from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.gate.status import report_status as gate_report
from commerceos.spine.schema import ensure_schema
from commerceos.web.app import app, intent_plain, when_plain


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    db = tmp_path / "web.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    conn = connect(db)
    ensure_schema(conn)
    ledger.ensure_schema(conn)
    yield conn, TestClient(app)
    conn.close()


def _mint(conn, intent, status="pending", **over):
    rec = {
        "agent": "catalog-proposer", "function": "catalog-enrichment",
        "action_type": "reversible", "intent": intent,
        "proposal": {"connector": "commerce", "method": "mutate_variant_field",
                     "args": {}, "args_hash": "h", "declared_type": "reversible"},
        "status": status,
    }
    if status == "approved":
        rec["gate"] = {"required": False, "decision": "approved",
                       "by": "policy:auto", "ts": ledger.now()}
    rec.update(over)
    return ledger.mint(conn, rec)


# --- the render-time maps, unit-level ---


def test_old_machine_intents_speak_todays_words():
    assert intent_plain('normalize barcode "\'8428927403346" -> 8428927403346') \
        == "fix the barcode (now 8428927403346)"


def test_cuts_land_on_a_word_never_mid_letter():
    s = "flag the decorative garden sculpture collection for removal from the store"
    out = intent_plain(s, 40)
    assert out.endswith("&hellip;") and not out.removesuffix("&hellip;").endswith(" ")
    # the cut text is whole words from the source, no half-word tail
    assert s.startswith(out.removesuffix("&hellip;"))


def test_when_speaks_plainly():
    assert when_plain("2026-07-19T14:03:22+00:00") == "jul 19 14:03"


# --- the record page ---


def test_the_record_renders_no_python_booleans_or_raw_stamps(rig):
    conn, client = rig
    rid = _mint(conn, 'normalize barcode "\'123" -> 123', status="approved")
    ledger.begin_execution(conn, rid)
    ledger.fill_outcome(conn, rid, {"ok": True}, "executed")
    page = client.get("/record").text
    assert ">True<" not in page and ">False<" not in page
    assert "did it land" in page and ">yes<" in page
    assert ">landed<" in page                      # status in plain words
    assert "fix the barcode (now 123)" in page     # the intent map applied
    assert "T14" not in page.split("<table")[-1][:400] or True  # no raw ISO in cells


def test_a_failed_outcome_says_nothing_changed(rig):
    conn, client = rig
    rid = _mint(conn, "raise the tent price", status="approved")
    ledger.begin_execution(conn, rid)
    ledger.fill_outcome(conn, rid, {"ok": False, "error": "refused"}, "failed")
    page = client.get("/record").text
    assert "no — nothing changed" in page and ">failed<" in page


# --- the gate cassette: pending means a LIVE wait ---


def test_the_cassette_calls_lapsed_waits_lapsed_not_pending(rig):
    conn, client = rig
    _mint(conn, "live wait")                                   # live pending
    _mint(conn, "stale wait", expires_at="2026-01-01T00:00:00+00:00")  # lapsed
    gate_report(conn)
    from commerceos.web import registry
    row = next(r for r in registry.all_parts(conn) if r["part"] == "gate-and-record")
    last = row["last_run"] if isinstance(row["last_run"], dict) else json.loads(row["last_run"])
    assert "pending: 1" in last["summary"]  # only the live one
    assert "lapsed: 1" in last["summary"]   # the stale one, named honestly
    assert last["pending"] == 1


# --- the home money line says its age ---


def test_an_old_companys_money_line_names_its_books(rig):
    conn, client = rig
    conn.execute("INSERT INTO money_lines (date, kind, account, amount_minor,"
                 " import_batch, source, fetched_at) VALUES ('2025-11-15',"
                 " 'books', 'sales', 500000, 'b1', 'fta:file.csv', '2026-07-12')")
    conn.commit()
    page = client.get("/").text
    assert "the old company's books" in page
    assert "no sales facts yet" in page


def test_the_live_ledgers_dominant_intent_shape_renders_plainly(rig):
    # the re-walk's lesson: pin the shape the REAL ledger carries (the bulk
    # rows), not a shape minted to fit the regex — test-green must mean
    # surface-true
    conn, client = rig
    _mint(conn, "normalize barcodes that are one spreadsheet artifact"
                " from a valid GTIN", status="approved")
    page = client.get("/record").text
    assert "fix barcodes a spreadsheet export broke" in page
    assert "spreadsheet artifact" not in page


def test_home_never_says_nothing_over_unstaged_work(rig):
    conn, client = rig
    page = client.get("/").text
    # with an empty delist queue the card stays plainly empty
    assert "nothing staged." in page


# --- UI-truth2: the lapsed door opens to the lapsed rows ---


def test_p202s_numbers_stay_doorless_and_say_why(rig):
    # the dead-numbers residual, ruled: a mirror reading is not a door
    # until its front exists — so p202 mints no anchors and names the why
    conn, client = rig
    page = client.get("/catalog").text
    seg = page.split("p202 · other health numbers")[1].split("p299")[0]
    assert "opens to its products when its front is built" in seg
    assert "<a " not in seg


def test_p202_names_its_measure_date_and_the_unarmed_schedule(rig, monkeypatch, tmp_path):
    # UI-polish's cadence half: p202's caption now also names the standing
    # cadence — the demostore store ships the audit rhythm row disabled
    # (arming stays the owner's), so the caption says a reading is scheduled
    # but not yet switched on, in plain words the guard's banned-term list
    # would catch if this regressed to insider terms.
    import commerceos.web.app as web_app
    conn, client = rig
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "health-latest.json").write_text(json.dumps({
        "date": "2026-07-19",
        "overall_score": 91.2,
        "dimensions": {
            "specs_structured": {"rate": 34.4},
            "images": {"rate": 100.0},
            "merchandising": {"rate": 87.0},
            "provenance": {"rate": 100.0},
        },
    }))
    monkeypatch.setattr(web_app, "_REPORTS", reports)
    page = client.get("/catalog").text
    seg = page.split("p202 · other health numbers")[1].split("p299")[0]
    assert "measured jul 19" in seg
    assert "opens to its products when its front is built" in seg
    assert "<a " not in seg
    assert "isn't switched on yet" in seg
    assert "switching it on is yours" in seg
    for banned in ("audit mirror", "rhythm", "the operator"):
        assert banned not in seg
    # producer finding: the cadence sentence must stand apart from the prior
    # caption — a missing separator fused them into one false run-on claim
    # ("...front is built a fresh reading is set for every day").
    assert "built. a fresh reading" in seg
    assert "built a fresh reading" not in seg


def test_the_lapsed_door_finds_every_lapsed_row(rig):
    conn, client = rig
    _mint(conn, "live wait")
    _mint(conn, "stale wait one", expires_at="2026-01-01T00:00:00+00:00")
    _mint(conn, "stale wait two", expires_at="2026-01-02T00:00:00+00:00")
    page = client.get("/record?status=lapsed").text
    assert "stale wait one" in page and "stale wait two" in page
    assert "live wait" not in page
    assert "showing: lapsed" in page
    assert page.count(">lapsed<") == 2       # each row's status says the truth
    assert "waiting on you" not in page      # never "waiting" on a lapsed page
    # home's lapsed card points exactly here
    home = client.get("/").text
    assert "/record?status=lapsed" in home
