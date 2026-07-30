"""FW1's checks (RULED 2026-07-18): widen one function from the fleet card
→ the policy table moves, the act lands on the record, the card shows the
new grant; narrowing works the same way. a widening is never silent (why
required), takes the explicit confirm, moves ONE rung, and fit-critical is
never grantable — the ladder simply has no such rung. findings-only agents
have nothing to widen and the surface says so."""

import json

import pytest
from fastapi.testclient import TestClient

from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.web.app import app

BASE_TABLE = {
    "version": 1,
    "severity_order": ["reversible", "consequential", "fit_critical"],
    "unknown_method_class": "fit_critical",
    "expiry_seconds": {"default": 3600, "money": 1800},
    "functions": {
        "catalog-enrichment": {"auto_approve": ["reversible"]},
        "content-geo": {"auto_approve": []},
    },
}


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    db = tmp_path / "web.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    table = tmp_path / "policy-table.json"
    table.write_text(json.dumps(BASE_TABLE, indent=2))
    monkeypatch.setenv("COMMERCEOS_POLICY_TABLE", str(table))
    conn = connect(db)
    ledger.ensure_schema(conn)
    conn.close()
    return TestClient(app), table, db


def grants(table_path):
    return {f: cfg.get("auto_approve")
            for f, cfg in json.loads(table_path.read_text())["functions"].items()}


def test_widen_moves_the_table_lands_the_record_and_the_card_shows_it(rig):
    client, table, db = rig
    r = client.post("/fleet/autonomy", data={
        "agent": "catalog-proposer", "direction": "widen",
        "why": "40 barcode repairs, zero reversals", "confirm": "true"})
    assert r.status_code in (200, 303) and r.request.url.path in ("/fleet", "/fleet/autonomy")
    assert grants(table)["catalog-enrichment"] == ["reversible", "consequential"]
    conn = connect(db)
    rec = conn.execute(
        "SELECT * FROM ledger WHERE function = 'policy' ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    assert rec is not None and rec["status"] == "executed"
    prop = json.loads(rec["proposal"])
    assert prop["method"] == "policy.move_threshold"
    assert prop["args"]["old"] == ["reversible"]
    assert prop["args"]["new"] == ["reversible", "consequential"]
    assert "zero reversals" in rec["rationale"]
    conn.close()
    page = client.get("/fleet").text
    assert "undone AND consequential acts run free" in page


def test_narrow_takes_the_same_road_back(rig):
    client, table, _ = rig
    client.post("/fleet/autonomy", data={
        "agent": "catalog-proposer", "direction": "widen",
        "why": "earned", "confirm": "true"})
    r = client.post("/fleet/autonomy", data={
        "agent": "catalog-proposer", "direction": "narrow",
        "why": "two bad flips this week"})
    assert r.status_code in (200, 303)
    assert grants(table)["catalog-enrichment"] == ["reversible"]


def test_widening_is_never_silent(rig):
    client, table, _ = rig
    r = client.post("/fleet/autonomy", data={
        "agent": "catalog-proposer", "direction": "widen", "confirm": "true"})
    assert r.status_code == 400 and "why" in r.json()["error"]
    assert grants(table)["catalog-enrichment"] == ["reversible"]


def test_widening_takes_the_second_gesture(rig):
    client, table, _ = rig
    r = client.post("/fleet/autonomy", data={
        "agent": "catalog-proposer", "direction": "widen", "why": "earned"})
    assert r.status_code == 400 and "confirm" in r.json()["error"]
    assert grants(table)["catalog-enrichment"] == ["reversible"]


def test_the_ladder_tops_out_below_fit_critical(rig):
    client, table, _ = rig
    client.post("/fleet/autonomy", data={
        "agent": "catalog-proposer", "direction": "widen",
        "why": "earned", "confirm": "true"})
    r = client.post("/fleet/autonomy", data={
        "agent": "catalog-proposer", "direction": "widen",
        "why": "more", "confirm": "true"})
    assert r.status_code == 409 and "safety-critical work never runs free" in r.json()["error"]
    assert grants(table)["catalog-enrichment"] == ["reversible", "consequential"]


def test_narrowing_below_the_floor_refused(rig):
    client, table, _ = rig
    r = client.post("/fleet/autonomy", data={
        "agent": "content", "direction": "narrow", "why": "tighter"})
    assert r.status_code == 409 and "narrowest" in r.json()["error"]
    assert grants(table)["content-geo"] == []


def test_findings_only_agent_has_nothing_to_widen(rig):
    client, table, _ = rig
    r = client.post("/fleet/autonomy", data={
        "agent": "analyst", "direction": "widen", "why": "x", "confirm": "true"})
    assert r.status_code == 400 and "findings" in r.json()["error"]
    before = grants(table)
    assert before == grants(table)


def test_a_hand_tuned_grant_off_the_ladder_is_refused_honestly(rig):
    client, table, _ = rig
    t = json.loads(table.read_text())
    t["functions"]["catalog-enrichment"]["auto_approve"] = ["consequential"]
    table.write_text(json.dumps(t))
    r = client.post("/fleet/autonomy", data={
        "agent": "catalog-proposer", "direction": "widen",
        "why": "x", "confirm": "true"})
    assert r.status_code == 409 and "by hand" in r.json()["error"]
    page = client.get("/fleet").text
    assert "hand-tuned grant" in page


def test_the_card_renders_grant_and_controls(rig):
    client, _, _ = rig
    page = client.get("/fleet").text
    assert "acts that can be undone run free" in page
    assert "widen one rung" in page and "narrow one rung" in page
    assert "nothing to widen" in page  # the analyst's honest line
    assert "recorded rule change" in page


def test_a_shared_grant_moves_only_from_the_owning_card(rig):
    # the endpoint agrees with the surface: spec-verifier shares
    # catalog-enrichment but the control lives on catalog-proposer's card
    client, table, _ = rig
    r = client.post("/fleet/autonomy", data={
        "agent": "spec-verifier", "direction": "widen",
        "why": "x", "confirm": "true"})
    assert r.status_code == 409 and "catalog-proposer's card" in r.json()["error"]
    assert grants(table)["catalog-enrichment"] == ["reversible"]
