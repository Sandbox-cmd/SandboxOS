"""the 7c (RULED tonight): device-label threading. a web-made approval's
ledger row must carry the honest built fact behind "who did this" — the
desk's fixed word, or a paired device's own owner-typed label — never the
bare code words "localhost"/"paired-device" that predate this ruling. both
identity sites (api_resolve, the grant-widen verb on /fleet/autonomy) thread
commerceos.web.auth.identity_label; who_plain renders both plainly, and a
label (user-typed, so untrusted) is escaped at render, never in storage."""

import json

import pytest
from fastapi.testclient import TestClient

from commerceos.catalog import lifecycle as L
from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.spine import writes
from commerceos.spine.schema import ensure_schema
from commerceos.web.app import app, who_plain
from commerceos.web.auth import ensure_pairing_schema, pair_device

from tests.test_catalog_delist import FakeClient, _add_product, _submit_delist

OFF = ("100.101.102.103", 50000)  # a real off-localhost address (not "testclient")


# ---------- api_resolve (the per-item approve) ----------------------------

@pytest.fixture()
def rig(tmp_path, monkeypatch):
    db = tmp_path / "web.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    conn = connect(db)
    ensure_schema(conn)
    ledger.ensure_schema(conn)
    ensure_pairing_schema(conn)
    yield conn, db
    conn.close()


def _seed_active_product(conn, pid="gid://x/1"):
    _add_product(conn, pid, "storm-shelter-tent", "Storm Shelter Tent", "Vango", "Tents")
    conn.commit()
    L.set_initial(conn, pid, "ACTIVE")
    return pid


def test_a_desk_approval_stamps_the_desk(rig, monkeypatch):
    conn, db = rig
    pid = _seed_active_product(conn)
    monkeypatch.setattr(writes, "ShopifyClient", lambda: FakeClient(status="ACTIVE"))
    res = _submit_delist(conn, pid)
    client = TestClient(app)  # host defaults to "testclient" -> localhost-trusted
    r = client.post(f"/api/approvals/{res['record_id']}",
                    data={"decision": "approved", "confirm": "true"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert ledger.get(conn, res["record_id"])["gate"]["by"] == "the desk"


def test_the_approvals_form_no_longer_lies_that_every_click_is_the_desk(rig):
    # the per-item approve card must not hardcode a 'by' — a paired phone
    # rendering that same card and clicking approve would otherwise always
    # stamp 'localhost', which is exactly the dishonest fact this ruling
    # closes. (regression: a hidden <input name='by' value='localhost'> once
    # rode every card, browser or not.)
    conn, db = rig
    pid = _seed_active_product(conn)
    _submit_delist(conn, pid)
    client = TestClient(app)
    page = client.get("/approvals").text
    assert "name='by'" not in page


def test_a_paired_device_approval_stamps_its_own_label(rig, monkeypatch):
    conn, db = rig
    pid = _seed_active_product(conn)
    monkeypatch.setattr(writes, "ShopifyClient", lambda: FakeClient(status="ACTIVE"))
    res = _submit_delist(conn, pid)
    token = pair_device(conn, "kitchen phone")
    conn.commit()
    phone = TestClient(app, client=OFF)
    claimed = phone.get(f"/pair/claim?t={token}", follow_redirects=False)
    assert claimed.status_code == 303
    r = phone.post(f"/api/approvals/{res['record_id']}",
                   data={"decision": "approved", "confirm": "true"},
                   follow_redirects=False)
    assert r.status_code == 303
    assert ledger.get(conn, res["record_id"])["gate"]["by"] == "kitchen phone"


def test_the_stored_label_is_raw_never_pre_escaped(rig, monkeypatch):
    conn, db = rig
    pid = _seed_active_product(conn)
    monkeypatch.setattr(writes, "ShopifyClient", lambda: FakeClient(status="ACTIVE"))
    res = _submit_delist(conn, pid)
    token = pair_device(conn, "<b>my_phone</b>")
    conn.commit()
    phone = TestClient(app, client=OFF)
    phone.get(f"/pair/claim?t={token}", follow_redirects=False)
    phone.post(f"/api/approvals/{res['record_id']}",
              data={"decision": "approved", "confirm": "true"}, follow_redirects=False)
    # the ledger's own ink is exactly the owner-typed label — escaping is a
    # render-time job, never a storage-time one (the append-only law).
    assert ledger.get(conn, res["record_id"])["gate"]["by"] == "<b>my_phone</b>"


def test_a_bearer_paired_device_stamps_its_label_too(rig, monkeypatch):
    conn, db = rig
    pid = _seed_active_product(conn)
    monkeypatch.setattr(writes, "ShopifyClient", lambda: FakeClient(status="ACTIVE"))
    res = _submit_delist(conn, pid)
    token = pair_device(conn, "the api tablet")
    conn.commit()
    phone = TestClient(app, client=OFF)
    r = phone.post(f"/api/approvals/{res['record_id']}",
                   headers={"authorization": f"Bearer {token}"},
                   json={"decision": "approved", "confirm": True})
    assert r.status_code == 200
    assert ledger.get(conn, res["record_id"])["gate"]["by"] == "the api tablet"


# ---------- the grant-widen verb (/fleet/autonomy) -------------------------

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
def widen_rig(tmp_path, monkeypatch):
    db = tmp_path / "web.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    table = tmp_path / "policy-table.json"
    table.write_text(json.dumps(BASE_TABLE, indent=2))
    monkeypatch.setenv("COMMERCEOS_POLICY_TABLE", str(table))
    conn = connect(db)
    ledger.ensure_schema(conn)
    ensure_pairing_schema(conn)
    yield conn
    conn.close()


def _last_policy_gate(conn) -> dict:
    rec = conn.execute(
        "SELECT gate FROM ledger WHERE function = 'policy' ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    return json.loads(rec["gate"])


def test_a_desk_widen_stamps_the_desk(widen_rig):
    conn = widen_rig
    client = TestClient(app)
    r = client.post("/fleet/autonomy", data={
        "agent": "catalog-proposer", "direction": "widen",
        "why": "40 barcode repairs, zero reversals", "confirm": "true"})
    assert r.status_code in (200, 303)
    assert _last_policy_gate(conn)["by"] == "the desk"


def test_a_paired_device_widen_stamps_its_own_label(widen_rig):
    conn = widen_rig
    token = pair_device(conn, "warehouse tablet")
    conn.commit()
    phone = TestClient(app, client=OFF)
    phone.get(f"/pair/claim?t={token}", follow_redirects=False)
    r = phone.post("/fleet/autonomy", data={
        "agent": "catalog-proposer", "direction": "widen",
        "why": "40 barcode repairs, zero reversals", "confirm": "true"})
    assert r.status_code in (200, 303)
    assert _last_policy_gate(conn)["by"] == "warehouse tablet"


# ---------- who_plain: the plain reading, both identity sites, escaped ----

def test_who_plain_renders_the_desk():
    assert who_plain("the desk") == "you, at this desk"


def test_who_plain_still_honors_the_ledgers_own_pre_ruling_ink():
    # append-only law: rows minted before this ruling carry the old words;
    # the render-time map keeps translating them, forever.
    assert who_plain("localhost") == "you, at this desk"
    assert who_plain("paired-device") == "you, from your paired device"


def test_who_plain_renders_a_device_label_plainly():
    assert who_plain("kitchen phone") == "your kitchen phone"


def test_who_plain_output_is_escaped_at_render_not_in_storage():
    from html import escape as html_escape
    hostile = "<b>evil</b>"
    plain = who_plain(hostile)
    assert plain == "your <b>evil</b>"          # the function itself: honest, unescaped
    rendered = html_escape(plain)               # every caller's actual render step
    assert "<b>" not in rendered
    assert "&lt;b&gt;evil&lt;/b&gt;" in rendered
