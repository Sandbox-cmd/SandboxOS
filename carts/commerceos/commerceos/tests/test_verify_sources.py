"""the spec-verification pilot: pilot-set selection admits only fit-critical
carriers; a fixture-built proposal PARKS as fit_critical (never autos);
conflict verdicts render as conflicts; the report writes. fixture-driven —
no live web anywhere in here."""

import json

import pytest

from commerceos.catalog import canonical
from commerceos.catalog.verify_sources import (build_proposal, check_against_claims,
                                               judge, pick_pilot_set, render_report,
                                               skeleton, submit_pilot, verdict_for,
                                               write_report)
from commerceos.db import connect
from commerceos.gate import ledger


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "pilot.db")
    canonical.ensure_schema(c)
    ledger.ensure_schema(c)
    c.executemany(
        "INSERT INTO canonical_products (shopify_id, handle, title, vendor, category, built_at)"
        " VALUES (?,?,?,?,?,'t')",
        [("gid://shopify/Product/1", "torch-x", "Torch X", "BrandA", "Lighting"),
         ("gid://shopify/Product/2", "knife-y", "Knife Y", "BrandB", "Knives & Tools"),
         ("gid://shopify/Product/3", "mug-z", "Mug Z", "BrandC", "Camp Kitchen"),
         ("gid://shopify/Product/4", "lamp-v", "Lamp V", "BrandA", "Lighting")])
    c.executemany(
        "INSERT INTO spec_claims (product, field, value, unit, source, verified, fit_critical)"
        " VALUES (?,?,?,?,?,?,?)",
        [  # Torch X: two unverified fit-critical claims -> in the pilot
         ("gid://shopify/Product/1", "ip_water_rating", "IP54", "IP code",
          "parsed:supplier-spec-blob", 0, 1),
         ("gid://shopify/Product/1", "battery_type", "Li-ion", None,
          "parsed:supplier-spec-blob", 0, 1),
         # Torch X: non-fit-critical claim -> never picked
         ("gid://shopify/Product/1", "lumens", "500", "lm",
          "parsed:supplier-spec-blob", 0, 0),
         # Knife Y: one unverified fit-critical claim -> in the pilot
         ("gid://shopify/Product/2", "blade_length", "10.16", "mm",
          "parsed:supplier-spec-blob", 0, 1),
         # Mug Z: carries only a non-fit-critical claim -> not a carrier
         ("gid://shopify/Product/3", "capacity_ml", "350", "ml",
          "parsed:supplier-spec-blob", 0, 0),
         # Lamp V: fit-critical but ALREADY verified -> nothing to verify
         ("gid://shopify/Product/4", "ip_water_rating", "IP68", "IP code",
          "https://example.com/spec", 1, 1)])
    c.commit()
    yield c
    c.close()


# ---- pilot-set selection --------------------------------------------------

def test_pilot_set_picks_only_unverified_fit_critical_carriers(conn):
    picked = pick_pilot_set(conn)
    handles = {p["handle"] for p in picked}
    assert handles == {"torch-x", "knife-y"}          # no mug-z, no lamp-v
    torch = next(p for p in picked if p["handle"] == "torch-x")
    assert {c["field"] for c in torch["claims"]} == {"ip_water_rating", "battery_type"}
    # the non-fit-critical lumens claim never rides along
    assert all(c["field"] != "lumens" for p in picked for c in p["claims"])


def test_pilot_set_honors_brand_filter_and_limit(conn):
    assert [p["vendor"] for p in pick_pilot_set(conn, brands=["BrandB"])] == ["BrandB"]
    # round-robin: limit 2 across two brands takes one from each
    two = pick_pilot_set(conn, brands=["BrandA", "BrandB"], limit=2)
    assert [p["vendor"] for p in two] == ["BrandA", "BrandB"]


# ---- verdicts, computed mechanically ---------------------------------------

def test_verdicts_agree_disagree_not_found():
    assert verdict_for("IP54", "IP code", "IP54")[0] == "agree"
    assert verdict_for("IP54", "IP code", "ip 54")[0] == "agree"     # normalization
    assert verdict_for("IPX4", "IP code", "IP54")[0] == "disagree"   # never collapse
    assert verdict_for("IP54", "IP code", None)[0] == "not_found"
    assert verdict_for("22.0", "L", "22", "L")[0] == "agree"
    assert verdict_for("7.62", "cm", "3.0", "in")[0] == "agree"      # cross-unit, same family
    assert verdict_for("9.0", "kg", "0.75", "kg")[0] == "disagree"
    assert verdict_for("Li-ion", None, "Li-ion")[0] == "agree"
    assert verdict_for("Li-ion", None, "alkaline")[0] == "disagree"


def test_unit_slip_is_a_stated_conflict_not_a_silent_pass():
    # catalog says 10.16 mm; manufacturer says 10.16 cm — the bare number
    # matches, the claim as stored is still wrong: disagree, with the note.
    v, note = verdict_for("10.16", "mm", "10.16", "cm")
    assert v == "disagree"
    assert note and "unit" in note


def test_found_value_without_source_is_refused(conn):
    sk = skeleton(pick_pilot_set(conn, brands=["BrandB"]))
    sk["products"][0]["claims"][0]["found_value"] = "7.62"   # no source_url
    with pytest.raises(ValueError, match="no source"):
        judge(sk)


# ---- the gate: fit-critical parks, always ----------------------------------

def _judged(conn, brands=None):
    sk = skeleton(pick_pilot_set(conn, brands=brands))
    for p in sk["products"]:
        for c in p["claims"]:
            if c["field"] == "ip_water_rating":               # agree
                c.update(found_value="IP54", source_url="https://brand-a.example/torch-x",
                         quote="Protection class: IP54")
            elif c["field"] == "battery_type":                # conflict
                c.update(found_value="alkaline", source_url="https://brand-a.example/torch-x",
                         quote="Battery: 3x AAA alkaline")
            # blade_length left null -> not_found
    return judge(sk)


def test_proposal_built_from_fixture_verification_parks_as_fit_critical(conn):
    findings = _judged(conn, brands=["BrandA"])
    receipts = submit_pilot(conn, findings)
    assert receipts["submitted"] == 1 and receipts["parked"] == 1

    pending = ledger.pending_queue(conn)
    assert len(pending) == 1
    rec = pending[0]
    assert rec["status"] == "pending"
    assert rec["action_type"] == "fit_critical"               # parked, never auto
    assert rec["gate"]["decision"] == "pending" and rec["gate"]["required"] is True
    # the intent renders on home's record card — plain words, no insider terms
    assert rec["intent"] == "check 2 safety-bearing details for Torch X (1 agree, 1 conflict)"
    args = rec["proposal"]["args"]
    assert args["field"] == "spec_verification"
    assert args["product_id"] == "gid://shopify/Product/1"
    by_field = {c["field"]: c for c in args["value"]["claims"]}
    assert by_field["ip_water_rating"]["verdict"] == "agree"
    assert by_field["battery_type"]["verdict"] == "disagree"  # stated, not resolved
    assert by_field["battery_type"]["found_value"] == "alkaline"


def test_rerun_skips_identical_pending_and_all_not_found_products(conn):
    findings = _judged(conn)                                  # BrandB product all not_found
    first = submit_pilot(conn, findings)
    assert first["parked"] == 1 and first["skipped_nothing_found"] == 1
    again = submit_pilot(conn, findings)
    assert again["submitted"] == 0 and again["skipped_already_pending"] == 1
    assert len(ledger.pending_queue(conn)) == 1               # the queue never stacks


def test_conflict_verdicts_render_as_conflicts(conn):
    findings = _judged(conn, brands=["BrandA"])
    prop = build_proposal(findings["products"][0])
    assert "(1 agree, 1 conflict)" in prop["intent"]
    assert prop["declared_type"] == "fit_critical"
    report = render_report(findings)
    assert "## conflicts — stated, not resolved" in report
    assert "catalog says Li-ion, manufacturer says alkaline" in report


# ---- the report ------------------------------------------------------------

def test_report_writes_with_honest_totals(conn, tmp_path):
    findings = _judged(conn)
    receipts = submit_pilot(conn, findings)
    path = write_report(findings, receipts, out_dir=tmp_path)
    assert path.name == f"verify-pilot-{findings['date']}.md"
    text = path.read_text()
    assert f"**{findings['totals']['products']} products" in text
    assert "1 agree · 1 disagree · 1 not found" in text
    assert "| Torch X | BrandA | 2 | 1 | 1 | 0 | brand-a.example |" in text
    assert "not found — recorded, never guessed" in text      # blade_length row
    assert "parked pending the owner: 1" in text


# ---- findings-file honesty ---------------------------------------------------

def test_stale_findings_are_refused(conn):
    findings = _judged(conn, brands=["BrandA"])
    check_against_claims(conn, findings)                      # fresh: passes
    findings["products"][0]["claims"][0]["value"] = "IP99"    # drifted
    with pytest.raises(ValueError, match="drifted"):
        check_against_claims(conn, findings)
