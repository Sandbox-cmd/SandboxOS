"""CS1's checks: /wall — the collaboration surface's first screen (the fusion
of the quiet page and the desk; spec/parts/collab-surface.md). the sentence
names the size of the day, waiting work renders as tickets (eyes-first per
item, ONE honest batch ticket per held reversible run), one calm line per
store, doors. an empty day says "Nothing needs you." honestly. the wall
opens BESIDE home — `/` is untouched.

rig per prior art (tests/test_workflow_runs_web.py:21-31 — COMMERCEOS_DB
pinned at a scratch db + TestClient); FakeStore/seed_variant from
tests/test_catalog_workflows.py; FakeClient/_add_product/_submit_delist/GID
from tests/test_catalog_delist.py. a crafted registry under a monkeypatched
stores.REPO_ROOT makes the calm lines deterministic (the env-pinned
COMMERCEOS_DB otherwise resolves every store to the same scratch db —
stores.py:28-31,84-86).

STEP 1 of the pack: these are written to FAIL on the missing /wall route
(each asserts 200 first). the guard-walk edit rides in
tests/test_catalog_dashboard.py.
"""

import json

import pytest
from fastapi.testclient import TestClient

from commerceos import stores
from commerceos.catalog import lifecycle as L
from commerceos.db import connect
from commerceos.gate import gate, ledger
from commerceos.spine import writes
from commerceos.spine.schema import ensure_schema
from commerceos.web import triage as T
from commerceos.web.app import app

from tests.test_catalog_workflows import FakeStore, seed_variant, VALID12, VALID13
from tests.test_catalog_delist import FakeClient, _add_product, _submit_delist, GID


def _write_registry(root, rows):
    d = root / "stores"
    d.mkdir(parents=True, exist_ok=True)
    (d / "registry.json").write_text(json.dumps({"stores": rows}))


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    db = tmp_path / "web.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    # the policy table lives under the REAL repo root; the env override wins
    # over REPO_ROOT (stores.py:28-31) so gate.submit resolves it after we
    # redirect REPO_ROOT at the crafted registry below.
    monkeypatch.setenv("COMMERCEOS_POLICY_TABLE",
                       str(stores.REPO_ROOT / "stores" / "demostore" / "policy-table.json"))
    # a crafted single-store registry so the calm lines are deterministic;
    # pin 7 overwrites it with a second, db-less store.
    _write_registry(tmp_path, [{"name": "demostore", "label": "Demo Store", "default": True}])
    monkeypatch.setattr(stores, "REPO_ROOT", tmp_path)
    conn = connect(db)
    ensure_schema(conn)          # facts + lifecycle
    ledger.ensure_schema(conn)   # ledger + handles + events
    from commerceos.catalog import runs as R
    R.ensure_schema(conn)        # workflow_runs (the batch + stopped source)
    conn.commit()
    yield conn, TestClient(app)
    conn.close()


class _RaiseOnOne:
    """a store that raises mid-write for one variant — the real per-item
    isolation records THAT item as errored (runs.py:138-141), the rest
    proceed. mirrors FakeStore's readback shape (test_catalog_workflows:52-63)."""

    def __init__(self, boom_pid):
        self.set = {}
        self.boom = boom_pid  # the product id whose variant write raises

    def graphql(self, query, variables=None):
        if "productVariantsBulkUpdate" in query:
            v = variables["variants"][0]
            if self.boom in v["id"]:
                raise RuntimeError("the store refused this one")
            self.set[v["id"]] = v["barcode"]
            return {"productVariantsBulkUpdate": {
                "productVariants": [{"id": v["id"], "barcode": self.set.get(v["id"])}],
                "userErrors": []}}
        if "query variant" in query:
            vid = variables["id"]
            return {"node": {"id": vid, "barcode": self.set.get(vid)}}
        raise AssertionError(f"unexpected query: {query[:60]}")


def _arm(client) -> str:
    r = client.post("/catalog/run/gtin", follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert loc.startswith("/catalog/runs/")
    return loc


# ---------- pin 1: the empty day ----------------------------------------

def test_the_empty_day_says_nothing_needs_you(rig):
    conn, client = rig
    r = client.get("/wall")
    assert r.status_code == 200
    page = r.text
    # triage's own honest empty output, exactly once
    assert page.count("Nothing needs you.") == 1
    # the one calm line + the doors still render
    assert "Demo Store" in page
    assert "/record" in page
    # an empty day carries no ticket markup at all
    assert "ticket waiting" not in page
    assert "ticket stopped" not in page


# ---------- pin 2: the sentence states the real wait count --------------

def test_the_sentence_states_the_real_wait_count(rig):
    conn, client = rig
    # two consequential waits (delist shape), parked per item
    _add_product(conn, GID(1), "h1", "T1", "V", "Tents")
    _add_product(conn, GID(2), "h2", "T2", "V", "Tents")
    _submit_delist(conn, GID(1))
    _submit_delist(conn, GID(2))
    # a held reversible batch of two (gtin)
    seed_variant(conn, "p1", "'" + VALID13)
    seed_variant(conn, "p2", VALID12[1:])
    conn.commit()
    _arm(client)
    r = client.get("/wall")
    assert r.status_code == 200
    # the sentence counts DECISIONS not members (M-B): two delist singles + the
    # held batch folded to ONE = three. the first sentence is the h2 focus, the
    # triage-split rides the .sub line under it (comp h2+sub).
    assert "<h2>Three things need you.</h2>" in r.text
    assert "<div class='sub'>Two deserve your eyes. One is routine.</div>" in r.text
    # the calm line agrees with the sentence (same folded gather)
    assert "Demo Store — <b>3</b> waiting on you" in r.text


# ---------- pin 3: eyes-first opens to its receipt in place -------------

def test_eyes_first_tickets_open_to_their_receipt_in_place(rig):
    conn, client = rig
    _add_product(conn, GID(1), "storm", "Storm Tent", "V", "Tents")
    L.set_initial(conn, GID(1), "ACTIVE")
    rid = _submit_delist(conn, GID(1))["record_id"]
    conn.commit()
    r = client.get("/wall")
    assert r.status_code == 200
    page = r.text
    # an amber (waiting) ticket, its title naming the product (M3)
    assert "ticket waiting" in page
    assert "remove Storm Tent from the store" in page
    # the change words are the SAME the decisions card carries — both surfaces
    # read the one shared _change_plain
    assert "removes Storm Tent from your store" in page
    assert "removes Storm Tent from your store" in client.get("/approvals").text
    # the receipt opens in place, no JS: a <details> holding the per-item
    # confirm+approve form posting to the one approve verb
    assert "<details" in page
    assert f"/api/approvals/{rid}" in page
    assert "confirm" in page
    assert "approve" in page


# ---------- pin 4: routine folds into ONE batch ticket ------------------

def test_routine_folds_into_one_batch_ticket(rig):
    conn, client = rig
    seed_variant(conn, "p1", "'" + VALID13)
    seed_variant(conn, "p2", VALID12[1:])
    conn.commit()
    loc = _arm(client)
    r = client.get("/wall")
    assert r.status_code == 200
    page = r.text
    # the held batch is ONE ticket, doored to its run preview
    assert "a batch of 2" in page
    assert page.count(loc) == 1
    # its member records never render as individual wall tickets
    assert "fix the barcode" not in page


# ---------- pin 5: approving from the wall walks the gate road ----------

def test_approving_from_the_wall_runs_the_gate_road_end_to_end(rig, monkeypatch):
    conn, client = rig
    _add_product(conn, GID(1), "storm", "Storm Tent", "V", "Tents")
    L.set_initial(conn, GID(1), "ACTIVE")
    rid = _submit_delist(conn, GID(1))["record_id"]
    conn.commit()
    # the delist executes through the one write door — a scripted store
    monkeypatch.setattr(writes, "ShopifyClient", lambda: FakeClient(status="ACTIVE"))
    page = client.get("/wall")
    assert page.status_code == 200
    assert rid in page.text  # the wall carries the record's approve form
    # approve through the form's target — the existing gate road, unmodified
    r = client.post(f"/api/approvals/{rid}",
                    data={"decision": "approved", "confirm": "true"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert ledger.get(conn, rid)["status"] == "executed"
    # re-GET the wall: the ticket is gone, the day is empty again
    after = client.get("/wall").text
    assert rid not in after
    assert "Nothing needs you." in after


# ---------- pin 6: a stopped job renders red with its why ---------------

def test_a_stopped_job_renders_red_with_its_why(rig, monkeypatch):
    conn, client = rig
    seed_variant(conn, "p1", "'" + VALID13)
    seed_variant(conn, "p2", VALID12[1:])
    conn.commit()
    loc = _arm(client)
    # one item's store write raises — the real isolation writes "errored — …"
    monkeypatch.setattr(writes, "ShopifyClient", lambda: _RaiseOnOne("p2"))
    ap = client.post(f"{loc}/approve", follow_redirects=False)
    assert ap.status_code == 303
    r = client.get("/wall")
    assert r.status_code == 200
    page = r.text
    # a red stopped ticket, naming the stop, doored to the run receipt
    assert "ticket stopped" in page
    assert "stopped" in page
    assert loc in page


# ---------- pin 7: one calm line per store ------------------------------

def test_calm_lines_one_per_store(rig, tmp_path, monkeypatch):
    conn, client = rig
    # a two-store registry: demostore (active/default) + scaffold (no db file).
    _write_registry(tmp_path, [
        {"name": "demostore", "label": "Demo Store", "default": True},
        {"name": "scaffold", "label": "Scaffold"},
    ])
    # the env-pinned COMMERCEOS_DB otherwise resolves EVERY store to the
    # scratch db (stores.py:28-31,84-86); wrap resolve so the second store's
    # db points at a path no file backs (context.md — the pin-7 rig).
    real_resolve = stores.resolve
    missing = tmp_path / "data" / "scaffold-missing.db"

    def fake_resolve(store, filename, root=None):
        if store == "scaffold" and filename == stores.DB:
            return missing
        return real_resolve(store, filename, root)

    monkeypatch.setattr(stores, "resolve", fake_resolve)
    # a live wait so the active store's line carries a real count
    _add_product(conn, GID(1), "h1", "T1", "V", "Tents")
    _submit_delist(conn, GID(1))
    conn.commit()
    r = client.get("/wall")
    assert r.status_code == 200
    page = r.text
    # the active store's line, with its live count
    assert "Demo Store" in page and "waiting on you" in page
    # the db-less store reads plainly, never a traceback
    assert "Scaffold" in page and "nothing set up yet" in page
    # law 3 by absence: no mirror/health number rides the wall
    assert "health" not in page.lower()


# ---------- pin 8: record-born ink renders escaped ----------------------

def test_record_born_ink_renders_escaped(rig):
    conn, client = rig
    # a product whose NAME carries markup — it rides the M3 title and the
    # receipt change, and must render escaped in both, never live (the
    # 1f7936e regression shape; CS0's fixture pins the same law)
    _add_product(conn, GID(1), "h1", "<b>inject</b> Tent", "V", "Tents")
    _submit_delist(conn, GID(1))
    conn.commit()
    r = client.get("/wall")
    assert r.status_code == 200
    page = r.text
    assert "&lt;b&gt;inject&lt;/b&gt;" in page
    assert "<b>inject</b>" not in page


# ---------- M3: the eyes-first title carries the product ----------------

def test_the_eyes_first_title_carries_the_product(rig):
    conn, client = rig
    _add_product(conn, GID(1), "storm", "Storm Shelter Tent", "V", "Tents")
    _submit_delist(conn, GID(1))
    conn.commit()
    r = client.get("/wall")
    assert r.status_code == 200
    page = r.text
    # the product rides the title, a verb names the act
    assert "remove Storm Shelter Tent from the store" in page
    # the method identifier never reaches the screen
    assert "mutate_product_state" not in page


# ---------- M4 flipped by CS2: every store door links to its board ------

def test_both_store_doors_link_to_their_board(rig, tmp_path, monkeypatch):
    conn, client = rig
    _write_registry(tmp_path, [
        {"name": "demostore", "label": "Demo Store", "default": True},
        {"name": "scaffold", "label": "Scaffold"},
    ])
    missing = tmp_path / "data" / "scaffold-missing.db"
    real_resolve = stores.resolve

    def fake_resolve(store, filename, root=None):
        if store == "scaffold" and filename == stores.DB:
            return missing
        return real_resolve(store, filename, root)

    monkeypatch.setattr(stores, "resolve", fake_resolve)
    r = client.get("/wall")
    assert r.status_code == 200
    doors = r.text[r.text.index("class='doors'"):]
    # CS2 flipped M4: /board/{store} exists now, so every store's name is a
    # REAL door to its own board — the active store's door moved off /catalog,
    # and the once-dead plain-text name became a true link.
    assert "<a href='/board/demostore'>Demo Store</a>" in doors
    assert "<a href='/board/scaffold'>Scaffold</a>" in doors
    assert "<span>Scaffold</span>" not in doors
    assert "<a href='/catalog'>Demo Store</a>" not in doors


# ---------- B1: the sentence triages the WHOLE business -----------------

def test_a_non_active_store_wait_raises_the_sentence_and_renders_formless(
        rig, tmp_path, monkeypatch):
    conn, client = rig
    from commerceos.catalog import runs as R
    # demostore (active) gets one wait on a real product
    _add_product(conn, GID(1), "g1", "Demo Store Tent", "V", "Tents")
    _submit_delist(conn, GID(1))
    conn.commit()
    # scaffold gets its OWN db (not the pinned scratch) with one wait
    scaffold_db = tmp_path / "data" / "scaffold.db"
    scaffold_db.parent.mkdir(parents=True, exist_ok=True)
    sconn = connect(scaffold_db)
    ensure_schema(sconn)
    ledger.ensure_schema(sconn)
    R.ensure_schema(sconn)
    _add_product(sconn, GID(2), "s1", "Scaffold Ladder", "V", "Ladders")
    _submit_delist(sconn, GID(2))
    sconn.commit()
    sconn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    sconn.execute("PRAGMA journal_mode=DELETE")   # a clean file for the ro read
    sconn.close()
    # two-store registry; scaffold resolves to its OWN db
    _write_registry(tmp_path, [
        {"name": "demostore", "label": "Demo Store", "default": True},
        {"name": "scaffold", "label": "Scaffold"},
    ])
    real_resolve = stores.resolve

    def fake_resolve(store, filename, root=None):
        if store == "scaffold" and filename == stores.DB:
            return scaffold_db
        return real_resolve(store, filename, root)

    monkeypatch.setattr(stores, "resolve", fake_resolve)
    r = client.get("/wall")
    assert r.status_code == 200
    page = r.text
    # the WHOLE business: two waits across two stores → the sentence counts both
    assert "Two things need you." in page
    # demostore's wait is actionable; scaffold's renders FORMLESS, stating the
    # fact (M-C: names the store, instructs nothing; labels verbatim)
    assert "remove Demo Store Tent from the store" in page
    assert "remove Scaffold Ladder from the store" in page
    assert "waits at Scaffold — this desk speaks for Demo Store" in page
    # the calm lines agree with the sentence — each store shows its one wait
    assert "Demo Store — <b>1</b> waiting on you" in page
    assert "Scaffold — <b>1</b> waiting on you" in page
    # scaffold's wait carries NO approve form — only demostore's does
    assert page.count("action='/api/approvals/") == 1


# ---------- M-B: the sentence counts decisions, not batch members -------

def test_a_held_batch_counts_as_one_wait_in_the_sentence(rig):
    conn, client = rig
    # one consequential single + a held reversible batch of three members
    _add_product(conn, GID(1), "g1", "Storm Tent", "V", "Tents")
    _submit_delist(conn, GID(1))
    seed_variant(conn, "p1", "'" + VALID13)
    seed_variant(conn, "p2", VALID12[1:])
    seed_variant(conn, "p3", "'" + VALID13)
    conn.commit()
    _arm(client)   # holds all three fixable barcodes as ONE batch
    r = client.get("/wall")
    assert r.status_code == 200
    page = r.text
    # the batch is ONE thing needing you (one glance lands it), not three:
    # single (1) + batch (1) = two
    assert "<h2>Two things need you.</h2>" in page
    # and the calm line folds identically
    assert "Demo Store — <b>2</b> waiting on you" in page
    # the batch still renders as one ticket naming its three changes
    assert "a batch of 3" in page
