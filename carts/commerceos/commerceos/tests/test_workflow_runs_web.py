"""WF-approve's web checks: arm a reversible batch from the surface → it
holds as ONE preview (never a hundred per-item cards) → one glance-approve
executes + verify-renders + the receipts read back on the same page. seen
on /catalog (the batches block) and decisions (the one batch card). the
decline leg lands its why. nothing lands without the approve.
"""

import pytest
from fastapi.testclient import TestClient

from commerceos.catalog import runs as R
from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.spine import writes
from commerceos.spine.schema import ensure_schema
from commerceos.web.app import app

from tests.test_catalog_workflows import FakeStore, seed_variant, VALID12, VALID13


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    db = tmp_path / "web.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    conn = connect(db)
    ensure_schema(conn)
    ledger.ensure_schema(conn)
    seed_variant(conn, "p1", "'" + VALID13)
    seed_variant(conn, "p2", VALID12[1:])
    yield conn, TestClient(app)
    conn.close()


def _arm(client) -> str:
    r = client.post("/catalog/run/gtin", follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert loc.startswith("/catalog/runs/")
    return loc


def test_arming_a_reversible_batch_holds_one_preview(rig):
    conn, client = rig
    loc = _arm(client)
    page = client.get(loc).text
    assert "a batch waiting for your glance" in page
    assert "approve the lot — 2 changes" in page
    assert "decline the lot" in page
    # the changes read in plain words — the product by name, was → becomes,
    # the changed characters marked for the glance — never the machine shape
    assert "P p1" in page and f"becomes {VALID13}" in page
    assert "was <b>&#x27;</b>" in page          # the dropped apostrophe, visible
    assert "becomes <b>0</b>" in page           # the restored zero, visible
    assert "normalize" not in page and "-&gt;" not in page
    # where the changes come from is on the surface
    assert "where these come from" in page
    # the halt boundary is stated, not implied
    assert "runs to its end" in page and "declining is your door until then" in page
    # nothing executed, nothing auto-approved
    assert conn.execute("SELECT COUNT(*) FROM handles").fetchone()[0] == 0
    rows = conn.execute("SELECT status FROM ledger").fetchall()
    assert {r[0] for r in rows} == {"pending"}


def test_decisions_shows_the_batch_once_not_its_member_rows(rig):
    conn, client = rig
    _arm(client)
    page = client.get("/approvals").text
    assert "a batch of 2" in page and "glance and approve" in page
    # the member rows never render as per-item cards
    assert "fix the barcode" not in page
    assert page.count("<form method='post' action='/api/approvals/") == 0


def test_home_folds_the_batch_into_one_wait_line(rig):
    conn, client = rig
    loc = _arm(client)
    page = client.get("/").text
    # the heading counts what the list shows — one batch, named as one
    assert "waits on you (a batch of 2)" in page
    assert "one glance approves the lot" in page
    assert page.count(loc) == 1                # one line, one door


def test_home_speaks_honest_tense_over_unlanded_work(rig):
    conn, client = rig
    _arm(client)
    page = client.get("/").text
    # a staged wait never reads as finished work, a machine status word
    # never reaches the screen, and no raw ISO stamp renders
    assert "a barcode fix" in page and "barcode fixed" not in page
    assert "· waiting on you" in page and "· pending" not in page


def test_rearming_opens_the_waiting_batch_never_a_duplicate(rig):
    conn, client = rig
    loc = _arm(client)
    n_before = conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    r = client.post("/catalog/run/gtin", follow_redirects=False)
    assert r.headers["location"] == loc              # the same waiting batch
    n_after = conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    assert n_after == n_before                       # nothing staged twice


def test_the_workflow_page_names_its_waiting_batch(rig):
    conn, client = rig
    loc = _arm(client)
    page = client.get("/catalog/workflows/gtin").text
    assert "already waiting for your glance" in page and loc in page
    assert "start a batch" not in page               # the arm steps aside
    assert "Start one above" not in page             # no stranded pointer either


def test_the_overview_carries_the_batches_block(rig):
    conn, client = rig
    loc = _arm(client)
    page = client.get("/catalog").text
    assert "batches waiting for your glance" in page
    assert loc in page


def test_one_glance_approve_lands_verifies_and_reads_back(rig, monkeypatch):
    conn, client = rig
    store = FakeStore()
    monkeypatch.setattr(writes, "ShopifyClient", lambda: store)
    loc = _arm(client)
    r = client.post(f"{loc}/approve", follow_redirects=False)
    assert r.status_code == 303
    page = client.get(loc).text
    assert "the batch landed" in page
    assert "showed up live? yes" in page
    # the screen answers "who approved" in a person's words, never the
    # machine's name for the desk
    assert "approved by" in page and "you, at this desk" in page
    assert "localhost" not in page
    # every record honestly reads a person's approval, executed
    for row in conn.execute("SELECT id FROM ledger"):
        rec = ledger.get(conn, row[0])
        assert rec["gate"]["by"] == "localhost" and rec["status"] == "executed"
    # the facts carry the verified value
    got = conn.execute("SELECT barcode FROM variants WHERE product_id='p1'").fetchone()[0]
    assert got == VALID13
    # and the wait is gone from decisions
    assert "a batch of" not in client.get("/approvals").text


def test_decline_lands_the_why_and_nothing_runs(rig):
    conn, client = rig
    loc = _arm(client)
    r = client.post(f"{loc}/decline", data={"why": "wrong batch today"},
                    follow_redirects=False)
    assert r.status_code == 303
    page = client.get(loc).text
    assert "declined" in page and "wrong batch today" in page
    for row in conn.execute("SELECT id FROM ledger"):
        assert ledger.get(conn, row[0])["status"] == "rejected"
    # the store untouched
    got = conn.execute("SELECT barcode FROM variants WHERE product_id='p1'").fetchone()[0]
    assert got == "'" + VALID13


def test_a_decline_without_its_why_is_refused(rig):
    conn, client = rig
    loc = _arm(client)
    r = client.post(f"{loc}/decline", data={"why": "  "}, follow_redirects=False)
    assert r.status_code == 303 and "why" in r.headers["location"]
    run_id = loc.rsplit("/", 1)[1]
    assert R.get(conn, run_id)["status"] == "staged"


def test_a_missing_batch_answers_plainly(rig):
    conn, client = rig
    r = client.get("/catalog/runs/not-a-run")
    assert r.status_code == 404
    assert "no such batch" in r.text
