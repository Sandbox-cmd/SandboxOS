"""SP1's checks: the supplier gated form — a submitted supplier PARKS (a
hand-typed money fact never runs free), approval through the system's one
approve verb lands the facts with operator: provenance via the local
executor (no store client), the economics COGS side (po_purchases) reads
and cites them, a replay is refused at the wall. SP2's render half: the
carried-over suppliers say where they came from."""

import json

import pytest
from fastapi.testclient import TestClient

from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.spine.schema import ensure_schema
from commerceos.web.app import app

BASE_TABLE = {
    "version": 1,
    "severity_order": ["reversible", "consequential", "fit_critical"],
    "unknown_method_class": "fit_critical",
    "expiry_seconds": {"default": 3600, "money": 1800},
    "functions": {"supplier-facts": {"auto_approve": []}},
}


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    db = tmp_path / "web.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    table = tmp_path / "policy-table.json"
    table.write_text(json.dumps(BASE_TABLE))
    monkeypatch.setenv("COMMERCEOS_POLICY_TABLE", str(table))
    conn = connect(db)
    ensure_schema(conn)
    ledger.ensure_schema(conn)
    conn.close()
    return TestClient(app), db


SUBMIT = {"name": "Alpine Traders", "payment_terms": "net 30",
          "po_id": "PO-1001", "po_date": "2026-07-01",
          "qty": "40", "unit_cost": "2500",
          "why": "invoice INV-88 from the July order"}


def test_a_submitted_supplier_parks_never_writes(rig):
    client, db = rig
    r = client.post("/suppliers/submit", data=SUBMIT)
    assert r.status_code in (200, 303)
    conn = connect(db)
    rec = conn.execute("SELECT * FROM ledger ORDER BY ts DESC LIMIT 1").fetchone()
    assert rec["status"] == "pending" and rec["action_type"] == "consequential"
    assert json.loads(rec["proposal"])["method"] == "record_supplier"
    # parked means NOT written — the facts tables stay empty
    assert conn.execute("SELECT COUNT(*) AS n FROM suppliers").fetchone()["n"] == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM purchase_orders").fetchone()["n"] == 0
    conn.close()
    page = client.get("/suppliers").text
    assert "waiting on your call in decisions" in page


def _approve_latest(client, db):
    conn = connect(db)
    rid = conn.execute("SELECT id FROM ledger WHERE status='pending'"
                       " ORDER BY ts DESC, rowid DESC LIMIT 1").fetchone()["id"]
    conn.close()
    return rid, client.post(f"/api/approvals/{rid}",
                            json={"decision": "approved", "confirm": "true"})


def test_approval_lands_the_facts_with_provenance(rig):
    client, db = rig
    client.post("/suppliers/submit", data=SUBMIT)
    rid, r = _approve_latest(client, db)
    assert r.status_code == 200
    out = r.json()["outcome"]
    assert out["ok"] is True and out["supplier"]["name"] == "Alpine Traders"
    conn = connect(db)
    s = conn.execute("SELECT * FROM suppliers WHERE name='Alpine Traders'").fetchone()
    assert s["source"] == "operator:web-form" and s["payment_terms"] == "net 30"
    po = conn.execute("SELECT * FROM purchase_orders WHERE id='PO-1001'").fetchone()
    assert po["supplier"] == "Alpine Traders" and po["source"] == "operator:web-form"
    line = conn.execute("SELECT * FROM po_lines WHERE po_id='PO-1001'").fetchone()
    assert line["qty"] == 40 and line["unit_cost_minor"] == 2500
    conn.close()
    page = client.get("/suppliers").text
    assert "Alpine Traders" in page and "entered by hand, approved" in page


def test_the_economics_cogs_side_reads_and_cites_it(rig):
    client, db = rig
    client.post("/suppliers/submit", data=SUBMIT)
    _approve_latest(client, db)
    from commerceos.economics import engine
    conn = connect(db)
    pnl = engine.assemble(conn, "2026-07")
    conn.close()
    cell = pnl["cells"].get("po_purchases")
    assert cell is not None, f"po_purchases missing — gaps: {pnl['gaps']}"
    assert cell["value"] == 40 * 2500
    assert cell["sources"][0]["table"] == "po_lines" and cell["sources"][0]["count"] == 1


def test_a_replay_is_refused_at_the_wall(rig):
    client, db = rig
    client.post("/suppliers/submit", data=SUBMIT)
    rid, first = _approve_latest(client, db)
    assert first.status_code == 200
    again = client.post(f"/api/approvals/{rid}",
                        json={"decision": "approved", "confirm": "true"})
    assert again.status_code == 409
    conn = connect(db)
    assert conn.execute("SELECT COUNT(*) AS n FROM po_lines").fetchone()["n"] == 1
    conn.close()


def test_never_silent_and_never_nameless(rig):
    client, db = rig
    r = client.post("/suppliers/submit", data={**SUBMIT, "why": ""})
    assert r.status_code == 400 and "never silent" in r.text
    r = client.post("/suppliers/submit", data={**SUBMIT, "name": ""})
    assert r.status_code == 400
    conn = connect(db)
    assert conn.execute("SELECT COUNT(*) AS n FROM ledger").fetchone()["n"] == 0
    conn.close()


def test_an_error_rerenders_the_page_and_keeps_the_typing(rig):
    # a mistake never lands the operator on a raw JSON page, and never eats
    # what they typed (the producer's cold read, finding 1)
    client, db = rig
    r = client.post("/suppliers/submit", data={**SUBMIT, "qty": "forty"})
    assert r.status_code == 400
    assert "whole numbers" in r.text and "<form" in r.text
    assert "Alpine Traders" in r.text and "invoice INV-88" in r.text  # typing kept
    r = client.post("/suppliers/submit", data={**SUBMIT, "po_date": "19-07-2026"})
    assert r.status_code == 400 and "YYYY-MM-DD" in r.text


def test_a_repeat_po_id_appends_never_replaces(rig):
    # approved money facts are never deleted by a later entry (finding 2)
    client, db = rig
    client.post("/suppliers/submit", data=SUBMIT)
    _approve_latest(client, db)
    client.post("/suppliers/submit", data={**SUBMIT, "qty": "10", "unit_cost": "900",
                                           "why": "second line of INV-88"})
    _approve_latest(client, db)
    conn = connect(db)
    rows = list(conn.execute("SELECT qty, unit_cost_minor FROM po_lines"
                             " WHERE po_id='PO-1001' ORDER BY id"))
    assert [(r["qty"], r["unit_cost_minor"]) for r in rows] == [(40, 2500), (10, 900)]
    conn.close()


def test_a_po_never_moves_to_another_supplier(rig):
    client, db = rig
    client.post("/suppliers/submit", data=SUBMIT)
    _approve_latest(client, db)
    client.post("/suppliers/submit", data={**SUBMIT, "name": "Someone Else",
                                           "why": "typo test"})
    rid, r = _approve_latest(client, db)
    assert r.status_code == 200
    assert r.json()["outcome"]["ok"] is False
    assert "one po, one supplier" in r.json()["outcome"]["error"]


def test_update_never_nulls_what_an_earlier_approval_landed(rig):
    client, db = rig
    client.post("/suppliers/submit", data=SUBMIT)
    _approve_latest(client, db)
    client.post("/suppliers/submit", data={"name": "Alpine Traders", "payment_terms": "",
                                           "why": "just confirming the supplier"})
    rid, r = _approve_latest(client, db)
    assert r.status_code == 200 and r.json()["outcome"]["ok"] is True
    conn = connect(db)
    s = conn.execute("SELECT payment_terms FROM suppliers WHERE name='Alpine Traders'").fetchone()
    assert s["payment_terms"] == "net 30"  # not nulled by the empty resubmit
    conn.close()


def test_submit_lands_back_with_the_parked_entry_named(rig):
    client, db = rig
    r = client.post("/suppliers/submit", data=SUBMIT, follow_redirects=True)
    assert r.status_code == 200
    assert "parked" in r.text and "Alpine Traders" in r.text
    assert "decide it in decisions" in r.text


def test_the_approval_card_speaks_plain_words_not_json(rig):
    client, db = rig
    client.post("/suppliers/submit", data=SUBMIT)
    page = client.get("/approvals").text
    assert "supplier: Alpine Traders, terms net 30" in page
    assert "po PO-1001 dated 2026-07-01: 40 at 25.00 AED (2500 fils) each" in page
    assert "unit_cost_minor" not in page  # the raw shape never renders here
    assert "the store is never touched" in page


def test_carried_over_suppliers_say_where_they_came_from(rig):
    client, db = rig
    conn = connect(db)
    conn.execute(
        "INSERT INTO suppliers (name, payment_terms, source, fetched_at)"
        " VALUES ('Old Faithful LLC', NULL, 'fta:FTAVATAuditFile_Demo Store.csv',"
        " '2026-07-12T00:00:00')")
    conn.commit()
    conn.close()
    page = client.get("/suppliers").text
    assert "Old Faithful LLC" in page
    assert "carried over from the old company" in page
    assert "1 suppliers" in page or "1 supplier" in page


def test_the_approve_click_lands_on_plain_words_never_json(rig):
    # finding 12: a browser-form approve redirects back to decisions with
    # the outcome in plain words — the decisive click never ends on a dump
    client, db = rig
    client.post("/suppliers/submit", data=SUBMIT)
    conn = connect(db)
    rid = conn.execute("SELECT id FROM ledger WHERE status='pending'").fetchone()["id"]
    conn.close()
    r = client.post(f"/api/approvals/{rid}",
                    data={"decision": "approved", "confirm": "true"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "<html" in r.text.lower()  # a page, not a JSON blob
    assert "landed: new supplier Alpine Traders" in r.text
    assert "unit_cost_minor" not in r.text


def test_a_refused_execution_surfaces_plainly_on_the_form_path(rig):
    client, db = rig
    client.post("/suppliers/submit", data=SUBMIT)
    _approve_latest(client, db)
    client.post("/suppliers/submit", data={**SUBMIT, "name": "Someone Else",
                                           "why": "typo test"})
    conn = connect(db)
    rid = conn.execute("SELECT id FROM ledger WHERE status='pending'").fetchone()["id"]
    conn.close()
    r = client.post(f"/api/approvals/{rid}",
                    data={"decision": "approved", "confirm": "true"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "nothing was written" in r.text and "one po, one supplier" in r.text


def test_json_callers_still_get_json(rig):
    client, db = rig
    client.post("/suppliers/submit", data=SUBMIT)
    rid, r = _approve_latest(client, db)  # the helper speaks JSON
    assert r.status_code == 200 and r.json()["outcome"]["ok"] is True
