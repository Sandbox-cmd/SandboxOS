"""CW5 merchandising — the surface pins (TestClient over a seeded scratch db).

seen on /catalog (the merchandising front row: the coverage meter honest with
its as-of, the collections-to-create count), the front's own page, the armed
create preview (holds as ONE glance, never per-item), and decisions (the
SEPARATE nav proposal parked with its plain WHY). nothing lands without the
owner's approve — the redirects prove it.
"""

import json

import pytest
from fastapi.testclient import TestClient

from commerceos.catalog import merchandising as M
from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.spine.schema import ensure_schema
from commerceos.web.app import app


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    db = tmp_path / "merch-web.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    conn = connect(db)
    ensure_schema(conn)
    ledger.ensure_schema(conn)
    yield conn, TestClient(app)
    conn.close()


def seed(conn, pid, product_type="Flashlights", collections=None):
    conn.execute(
        "INSERT INTO products (shopify_id, handle, title, status, vendor,"
        " product_type, tags, collections, raw, source, fetched_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (pid, f"h-{pid}", f"P {pid}", "ACTIVE", "V", product_type, "[]",
         json.dumps(collections or []), "{}", "test", "2026-07-19T00:00:00Z"))


def test_overview_shows_the_merchandising_front_with_live_numbers(rig):
    conn, client = rig
    # a fake-synced fixture: 1 of 2 products already in a live shelf
    seed(conn, "p1", "Flashlights", collections=["Lighting"])
    seed(conn, "p2", "Tents", collections=[])
    conn.commit()

    page = client.get("/catalog")
    assert page.status_code == 200
    # the front is named plainly and numbered (p210)
    assert "collections" in page.text and "210" in page.text
    # the coverage figure is LIVE and honest about its lag
    assert "1 of 2 products in a collection, as of the last sync" in page.text
    # the actionable count is COLLECTIONS to create, opening to the front page
    to_create = M.merch_progress(conn)["to_create"]
    assert f"/catalog/workflows/merchandising'>{to_create}</a>" in page.text
    assert "collections to create" in page.text


def test_front_page_renders_coverage_and_the_collections_to_build(rig):
    conn, client = rig
    seed(conn, "p1", "Flashlights", collections=["Lighting"])
    seed(conn, "p2", "Tents")
    conn.commit()

    page = client.get("/catalog/workflows/merchandising")
    assert page.status_code == 200
    assert "as of the last sync" in page.text
    # the queued collections are REAL rows (each named), not a dead number
    assert "Tents &amp; Shelters" in page.text or "Tents & Shelters" in page.text
    # the one live collection is not re-listed as still-to-create
    assert "still to create" in page.text


def test_merch_surface_never_overclaims_freshness(rig):
    """the coverage figure is synced, not live — the header, marquee, and
    signoff must wear the lag its own detail line states, never "coverage now"
    or "live from the facts" (the producer's freshness overclaim)."""
    conn, client = rig
    seed(conn, "p1", "Flashlights", collections=["Lighting"])
    seed(conn, "p2", "Tents")
    conn.commit()
    text = client.get("/catalog/workflows/merchandising").text
    assert "as of the last sync" in text
    assert "coverage now" not in text
    assert "coverage is live from the facts" not in text


def test_arming_the_create_batch_holds_one_preview(rig):
    conn, client = rig
    seed(conn, "p1", "Flashlights")
    conn.commit()

    r = client.post("/catalog/run/merchandising", follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert loc.startswith("/catalog/runs/")
    page = client.get(loc).text
    assert "a batch waiting for your glance" in page
    assert "new collection" in page                      # the creates, in plain words
    assert "decline the lot" in page
    # the rule sentence renders WHOLE — the change line IS what's approved, so
    # it is never amputated mid-rule ("… water bottle, bike water,…")
    assert "water bottle, bike water, hydration or 6 more" in page
    assert "bike water,&hellip;" not in page and "bike water,…" not in page
    # nothing executed, nothing auto-approved — it HOLDS
    assert conn.execute("SELECT COUNT(*) FROM handles").fetchone()[0] == 0
    assert {r[0] for r in conn.execute("SELECT status FROM ledger")} == {"pending"}


def test_nav_flow_stages_one_consequential_proposal_into_decisions(rig):
    conn, client = rig
    # a live shelf exists, so there is something to place in the menu
    seed(conn, "p1", "Flashlights", collections=["Lighting"])
    conn.commit()

    # the nav control on the front page offers the placement
    front = client.get("/catalog/workflows/merchandising").text
    assert "put them in your store menu" in front
    assert "/catalog/merchandising/nav" in front

    r = client.post("/catalog/merchandising/nav", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/approvals"

    # exactly ONE parked proposal, nothing executed, no handle minted
    rows = conn.execute("SELECT status, json_extract(proposal,'$.method') AS m"
                        " FROM ledger").fetchall()
    assert len(rows) == 1 and rows[0]["status"] == "pending"
    assert rows[0]["m"] == "mutate_menu"
    assert conn.execute("SELECT COUNT(*) FROM handles").fetchone()[0] == 0

    # decisions renders the nav change in plain words with its WHY (no raw tree)
    decisions = client.get("/approvals").text
    assert "your store's main menu" in decisions
    assert "changes only after you approve" in decisions
    assert "resourceId" not in decisions and "menu_id" not in decisions
    # the method label is tense-honest on a still-pending card — a placement
    # ahead, never "placed" (past tense) before it landed
    assert "store menu placement" in decisions
    assert "store menu placed" not in decisions
    # the wait is in plain words, never a raw ISO stamp
    assert "waits until" in decisions
    assert "expires 20" not in decisions and "+00:00" not in decisions


def test_nav_control_steps_aside_when_a_change_is_already_waiting(rig):
    """one navigation change waits at a time — once staged, the control shows
    the open door instead of the button, and a re-press stages no duplicate
    (mirrors the reversible batch's one-waits-at-a-time step-aside)."""
    conn, client = rig
    seed(conn, "p1", "Flashlights", collections=["Lighting"])
    conn.commit()

    # first stage — one parked proposal
    client.post("/catalog/merchandising/nav", follow_redirects=False)
    n_after_one = conn.execute(
        "SELECT COUNT(*) FROM ledger WHERE json_extract(proposal,'$.method')"
        " = 'mutate_menu'").fetchone()[0]
    assert n_after_one == 1

    # the control steps aside — no button, points at the waiting one
    front = client.get("/catalog/workflows/merchandising").text
    assert "a navigation change is already waiting" in front
    assert "to your store menu &rarr;" not in front       # the arm button is gone

    # a re-press stages NO duplicate — still exactly one, redirected to decisions
    r2 = client.post("/catalog/merchandising/nav", follow_redirects=False)
    assert r2.status_code == 303 and r2.headers["location"].startswith("/approvals")
    n_after_two = conn.execute(
        "SELECT COUNT(*) FROM ledger WHERE json_extract(proposal,'$.method')"
        " = 'mutate_menu'").fetchone()[0]
    assert n_after_two == 1


def test_nav_button_is_singular_for_one_collection(rig):
    conn, client = rig
    seed(conn, "p1", "Flashlights", collections=["Lighting"])   # exactly one live
    conn.commit()
    front = client.get("/catalog/workflows/merchandising").text
    assert "add 1 collection to your store menu" in front       # not "collections"


def test_nav_control_waits_when_no_shelf_is_live_yet(rig):
    conn, client = rig
    seed(conn, "p1", "Flashlights")            # nothing synced live
    conn.commit()
    front = client.get("/catalog/workflows/merchandising").text
    assert "once your collections are live" in front
    # staging with nothing to place is a plain no-op, never a broken proposal
    r = client.post("/catalog/merchandising/nav", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/catalog/workflows/merchandising"
    assert conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == 0
