"""CS2 — the board (GET /board/{store}): one store's desk. two zones (MY
SIDE — running work read LIVE from ledger statuses; YOUR SIDE — waiting
tickets), receipt-in-place, landed-today, a first-class red stopped ticket,
five doors. composes CS0's foundation + CS1's landed wall helpers; the board
READS and writes nothing.

writer-class law: every workflow-run state in these pins comes from the REAL
machinery — catalog_runs.approve walking gate.resolve + writes.execute per
record, with fake store clients — NEVER a direct INSERT/UPDATE into
workflow_runs. the progress pin proves mid-run truth lives in the ledger's
per-record commits, not the run row's items json (written only at the end).
"""

import threading

import pytest
from fastapi.testclient import TestClient

from commerceos.catalog import runs as R
from commerceos.catalog import workflows as W
from commerceos.db import connect
from commerceos.gate import gate, ledger
from commerceos.spine import writes
from commerceos.spine.schema import ensure_schema
from commerceos.web.app import app

from tests.test_catalog_workflows import FakeStore, seed_variant, VALID13
from tests.test_catalog_delist import FakeClient as DelistClient


# ---------- the rig (per tests/test_workflow_runs_web.py:21-31) -------------

@pytest.fixture()
def rig(tmp_path, monkeypatch):
    """demostore is the registry default → the active store this desk speaks
    for; COMMERCEOS_DB overrides its db to a scratch path (stores.py:28-31).
    seeds nothing — each pin seeds the exact shape it needs so counts are
    exact ('n of 40' needs a queue big enough to see the number climb)."""
    db = tmp_path / "board.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    # the health mirror is monkeypatched to a fixture (RULED): never inherit the
    # repo's real mirror — a machine-dependent render is a flaky lie. the number
    # wears "as of" through fusion.aged like the live path.
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "health-latest.json").write_text(
        '{"overall_score": 78.5, "date": "2026-07-21"}')
    import commerceos.web.app as webapp
    monkeypatch.setattr(webapp, "_REPORTS", reports)
    conn = connect(db)
    ensure_schema(conn)
    ledger.ensure_schema(conn)
    R.ensure_schema(conn)
    yield conn, TestClient(app), db
    conn.close()


def _arm(client) -> str:
    """arm the fixable-barcode queue into ONE held reversible batch (the
    existing gated road) → its preview location /catalog/runs/{id}."""
    r = client.post("/catalog/run/gtin", follow_redirects=False)
    assert r.status_code == 303, r.text
    loc = r.headers["location"]
    assert loc.startswith("/catalog/runs/")
    return loc


def _seed_gtin(conn, pid):
    """one fixable-barcode variant (an apostrophe artifact → the queue finds
    it, the store fixes it)."""
    seed_variant(conn, pid, "'" + VALID13)


def _seed_product(conn, pid, title):
    conn.execute(
        "INSERT INTO products (shopify_id, handle, title, status, vendor,"
        " product_type, tags, raw, source, fetched_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (pid, f"h-{pid}", title, "ACTIVE", "V", "Flashlights", "[]", "{}",
         "test", "2026-07-12T00:00:00Z"))
    conn.commit()


def _submit_delist(conn, pid, intent="remove it from the store"):
    """a consequential delist wait, PARKED per item (the real gate road) — a
    your-side single carrying the decisions form."""
    return gate.submit(conn, {
        "agent": "catalog-delist", "function": "catalog-enrichment",
        "method": "mutate_product_state",
        "args": {"product_id": pid, "state": "delisted"},
        "declared_type": "consequential",
        "intent": intent, "rationale": "quality flag ruled — pull it",
        "provenance": [{"source": "quality.py"}],
    })["record_id"]


# ---------- 1. an unknown store answers plainly -----------------------------

def test_unknown_store_answers_plainly(rig):
    conn, client, _db = rig
    r = client.get("/board/nope")
    assert r.status_code == 404
    text = r.text.lower()
    assert "no store called" in text        # plain words, never a raw dump
    assert "traceback" not in text
    assert '"detail"' not in text            # not a raw JSON answer on a screen


# ---------- 2. a store that is not this desk's renders read-only ------------

def test_a_store_that_is_not_this_desks_renders_readonly(rig):
    conn, client, _db = rig
    r = client.get("/board/scaffold")        # the registry's second store
    assert r.status_code == 200
    text = r.text
    assert "Scaffold" in text                # the label
    # its onboarding read in plain ceremony words (the RULED stamp map) — the
    # real registry row carries all five stamps
    assert "settings written" in text and "first screen rendered" in text
    # the behavior-4 line: this desk speaks for the active store only
    assert "this desk speaks for" in text
    # NO zones, NO forms — the surface speaks for one store
    assert "your side" not in text.lower()
    assert "action='/api/approvals/" not in text


# ---------- 3. the two zones render -----------------------------------------

def test_the_two_zones_render(rig):
    conn, client, _db = rig
    _seed_gtin(conn, "g1")
    _seed_gtin(conn, "g2")
    _seed_product(conn, "d1", "Storm Lantern")
    _arm(client)                             # a held batch of 2 (folds to ONE)
    _submit_delist(conn, "d1")               # one your-side single
    text = client.get("/board/demostore").text
    # your-side counts what the LIST shows — the batch as one + the single
    assert "your side — 2 waiting" in text
    # nothing is running yet — my side speaks as I
    assert "my hands are empty — nothing running." in text
    # the top line: the desk names its store + resting state, and the health
    # mirror wears its measured date through aged() (law 3)
    assert "Demo Store · quiet" in text
    assert "health 78.5 as of jul 21" in text
    # the number wears a quiet door to its breakdown (owner-ruled 2026-07-22)
    assert "<a href='/catalog'>health 78.5 as of jul 21</a>" in text
    assert "0 changes today" in text


# ---------- 4. a running job's progress moves (THE pin, real machinery) -----

class BarrierStore:
    """wraps FakeStore; blocks on a threading.Event at the START of item 15's
    WRITE. each gtin item is TWO graphql calls — the write
    (productVariantsBulkUpdate, writes.py:228-231) then the readback
    (writes.py:234-235) — so blocking before the 15th write means 14 items
    are fully executed in the ledger (14 per-record commits), which is exactly
    what the board's n_done must read. NEVER a minted workflow_runs row."""

    def __init__(self, inner, at, reached, release):
        self.inner = inner
        self.at = at
        self.reached = reached
        self.release = release
        self.writes = 0

    def graphql(self, query, variables=None):
        if "productVariantsBulkUpdate" in query:
            self.writes += 1
            if self.writes == self.at:
                self.reached.set()
                self.release.wait(timeout=15)
        return self.inner.graphql(query, variables)


def test_a_running_jobs_progress_moves(rig, monkeypatch):
    conn, client, db = rig
    for i in range(40):                      # a queue big enough to see it climb
        _seed_gtin(conn, f"p{i:02d}")
    loc = _arm(client)
    run_id = loc.rsplit("/", 1)[1]

    reached, release = threading.Event(), threading.Event()
    barrier = BarrierStore(FakeStore(), at=15, reached=reached, release=release)
    monkeypatch.setattr(writes, "ShopifyClient", lambda: barrier)

    err: dict = {}

    def worker():
        try:
            c2 = connect(db)                 # the worker's OWN connection
            R.approve(c2, run_id, W.GTIN, by="localhost")
            c2.close()
        except Exception as e:               # a failure must not wedge main
            err["e"] = e
            release.set()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    try:
        assert reached.wait(timeout=15), "the barrier was never reached"
        mid = client.get("/board/demostore").text
    finally:
        release.set()
        t.join(timeout=15)
    assert not t.is_alive(), "the worker thread hung"
    assert not err, f"the worker raised: {err.get('e')!r}"
    after = client.get("/board/demostore").text

    # mid-run truth came from LEDGER statuses (14 executed), never the run
    # row's items json (rewritten only at the end)
    assert "14 of 40" in mid
    # B1: an EXECUTING batch is my-side's running work — its members never
    # render as your-side waits, and never carry an approve form
    assert "your side — 0 waiting" in mid
    assert "/api/approvals/" not in mid
    # B1's twin: an executing run's already-committed members are NOT loose
    # landed-today singles — with no other landed work, no landed group at all
    assert "landed today" not in mid
    assert "showed up live" not in mid          # no phantom batch ticket either
    # M3 branch 1: a run executes and NO form is on the page → auto-refresh,
    # no person-controlled refresh link needed
    assert "http-equiv='refresh'" in mid     # a person watching sees it move
    assert "refresh ↻" not in mid
    # once done: under landed-today, no refresh churn on a quiet page
    assert "http-equiv='refresh'" not in after
    assert "landed today" in after


def _barrier_running(rig, monkeypatch, *, n_gtin, at, extra_single=False):
    """arm a gtin batch and hold it mid-execute on a worker thread (real
    machinery, barrier at item `at`); optionally park one delist single first.
    returns (client, mid_html, wall_html, delist_rid|None) captured WHILE the
    run executes, then releases and joins. shared by the mid-run pins."""
    conn, client, db = rig
    delist_rid = None
    if extra_single:
        _seed_product(conn, "d1", "Storm Lantern")
        delist_rid = _submit_delist(conn, "d1")
    for i in range(n_gtin):
        _seed_gtin(conn, f"p{i:02d}")
    run_id = _arm(client).rsplit("/", 1)[1]
    reached, release = threading.Event(), threading.Event()
    barrier = BarrierStore(FakeStore(), at=at, reached=reached, release=release)
    monkeypatch.setattr(writes, "ShopifyClient", lambda: barrier)
    err: dict = {}

    def worker():
        try:
            c2 = connect(db)
            R.approve(c2, run_id, W.GTIN, by="localhost")
            c2.close()
        except Exception as e:
            err["e"] = e
            release.set()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    try:
        assert reached.wait(timeout=15), "the barrier was never reached"
        mid = client.get("/board/demostore").text
        wall = client.get("/wall").text
    finally:
        release.set()
        t.join(timeout=15)
    assert not t.is_alive() and not err, f"worker: {err.get('e')!r}"
    return client, mid, wall, delist_rid


def test_a_confirm_form_holds_off_the_auto_refresh(rig, monkeypatch):
    # a run executes AND a your-side single carries a confirm form → M3: NO
    # auto-refresh (it would wipe the checkbox); a person-controlled refresh
    # link rides my-side instead.
    _client, mid, _wall, delist_rid = _barrier_running(
        rig, monkeypatch, n_gtin=4, at=2, extra_single=True)
    assert "barcodes — 1 of 4" in mid           # the batch runs on my side
    assert "your side — 1 waiting" in mid        # only the delist — NOT members
    assert f"/api/approvals/{delist_rid}" in mid  # its confirm form is present
    assert "http-equiv='refresh'" not in mid     # the refresh yields to the form
    assert "refresh ↻" in mid                    # a real, person-walked door
    # the 1 committed member is my-side progress, never a loose landed single
    assert "landed today" not in mid


def test_a_mid_run_wall_never_shows_batch_members_as_waits(rig, monkeypatch):
    # B1 on the WALL (the shared _view_from_conn fix): while the batch executes,
    # none of its members render as waiting tickets or carry a form.
    _client, _mid, wall, _rid = _barrier_running(
        rig, monkeypatch, n_gtin=6, at=3)
    assert 'class="ticket waiting"' not in wall   # no member is a wait
    assert "/api/approvals/" not in wall          # no member form on the wall


# ---------- 5. a wait approved from the board flips zones --------------------

def test_a_wait_approved_from_the_board_flips_zones(rig, monkeypatch):
    conn, client, _db = rig
    monkeypatch.setattr(writes, "ShopifyClient", lambda: DelistClient())
    _seed_product(conn, "d1", "Storm Lantern")
    rid = _submit_delist(conn, "d1")
    # the your-side single carries the decisions form → POST the existing road
    r = client.post(f"/api/approvals/{rid}",
                    data={"confirm": "true", "decision": "approved"},
                    follow_redirects=False)
    assert r.status_code == 303
    text = client.get("/board/demostore").text
    # zones flipped: gone from your side, now under landed-today with the
    # approver in a person's words (who_plain) and the receipt in place
    assert "you, at this desk" in text
    assert f"/api/approvals/{rid}" not in text   # no longer an open wait
    # the record honestly reads executed, verified rendered
    rec = ledger.get(conn, rid)
    assert rec["status"] == "executed"
    assert rec["outcome"].get("verified_rendered") is True


# ---------- 6. the stopped state renders from a real stopped receipt ---------

class OneRaises(FakeStore):
    """a store that raises on ONE variant's write — the real approve loop
    catches it and records 'errored — …' on that item (runs.py:138-141),
    leaving a genuinely stopped done run. never a minted state."""

    def __init__(self, boom_variant):
        super().__init__()
        self.boom = boom_variant

    def graphql(self, query, variables=None):
        if (variables and variables.get("variants")
                and variables["variants"][0]["id"] == self.boom):
            raise RuntimeError("THROTTLED")
        return super().graphql(query, variables)


def test_the_stopped_state_renders_from_a_real_stopped_receipt(rig):
    conn, client, _db = rig
    _seed_gtin(conn, "s1")
    _seed_gtin(conn, "s2")
    loc = _arm(client)
    run_id = loc.rsplit("/", 1)[1]
    # approve through the REAL machinery with a client that errors on v-s2
    R.approve(conn, run_id, W.GTIN, by="localhost", client=OneRaises("v-s2"))
    text = client.get("/board/demostore").text
    # a first-class red stopped ticket: what stopped, the why in plain words,
    # the door to the full run receipt
    assert "1 of 2" in text                  # one item did not finish
    # m5: the raw error constant NEVER reaches the screen — a plain sentence
    # speaks, the raw string stays behind the run door
    assert "the store told us to slow down" in text
    assert "THROTTLED" not in text
    # m6: the finished member DOES count in today's changes — said on the
    # ticket so the top line reconciles on-page
    assert "the 1 that finished count in today" in text   # ('today&#x27;s changes', escaped)
    assert f"/catalog/runs/{run_id}" in text
    assert "<script>" not in text            # record-born ink never raw
    # a stop is first-class RED only — never ALSO green under landed-today, and
    # its one executed member never leaks out as a loose landed single
    assert "landed today" not in text


# ---------- B2: change receipts are plain, never raw JSON on a fusion surface

def test_a_barcode_change_renders_in_plain_words(rig):
    conn, _client, _db = rig
    from commerceos.web.app import _change_plain
    _seed_gtin(conn, "g1")                    # seed_variant titles it "P g1"
    r = {"proposal": {"method": "mutate_variant_field",
                      "args": {"product_id": "g1", "field": "barcode",
                               "value": VALID13}}}
    html = _change_plain(conn, r, fusion_safe=True)
    assert f"sets P g1's barcode to {VALID13}" in html
    assert "<pre" not in html                 # never the raw args dump


def test_an_unmapped_change_is_fusion_safe_never_raw_json(rig):
    conn, _client, _db = rig
    from commerceos.web.app import _change_plain
    r = {"proposal": {"method": "some_unmapped_method", "args": {"foo": "bar"}}}
    # decisions keeps its deliberate raw <pre> (the default, unchanged)
    assert "<pre" in _change_plain(conn, r, fusion_safe=False)
    # a fusion surface NEVER shows raw JSON — a plain line + a door to the record
    safe = _change_plain(conn, r, fusion_safe=True)
    assert "<pre" not in safe and "{" not in safe
    assert "a technical change" in safe and "/record" in safe


# ---------- 7. landed-today excludes run members from singles ---------------

def test_landed_today_excludes_run_members_from_singles(rig, monkeypatch):
    conn, client, _db = rig
    monkeypatch.setattr(writes, "ShopifyClient", lambda: FakeStore())
    _seed_gtin(conn, "g1")
    _seed_gtin(conn, "g2")
    loc = _arm(client)
    run_id = loc.rsplit("/", 1)[1]
    # a clean glance-approve of the whole batch (the reversible lane)
    R.approve(conn, run_id, W.GTIN, by="localhost", client=FakeStore())
    # plus one landed single of a different kind
    monkeypatch.setattr(writes, "ShopifyClient", lambda: DelistClient())
    _seed_product(conn, "d1", "Storm Lantern")
    rid = _submit_delist(conn, "d1")
    client.post(f"/api/approvals/{rid}",
                data={"confirm": "true", "decision": "approved"},
                follow_redirects=False)
    text = client.get("/board/demostore").text
    # the batch renders as ONE green ticket, doored to its run — never its
    # member records a second time as loose landed singles
    assert "landed today" in text
    assert text.count(f"/catalog/runs/{run_id}") == 1
    assert "a batch of 2" in text and "barcodes" in text


# ---------- 8. record-born ink renders escaped ------------------------------

def test_record_born_ink_renders_escaped(rig):
    conn, client, _db = rig
    _seed_product(conn, "d1", "Storm <b>Lantern</b>")   # markup in the name
    _submit_delist(conn, "d1", intent="pull the <b>bad</b> one")
    text = client.get("/board/demostore").text
    assert "<b>Lantern</b>" not in text         # never the raw markup
    assert "&lt;b&gt;Lantern&lt;/b&gt;" in text  # escaped exactly (1f7936e)


# ---------- 9. the five doors open real pages -------------------------------

def test_the_doors_open_real_pages(rig):
    conn, client, _db = rig
    text = client.get("/board/demostore").text
    for href in ("/catalog", "/economics", "/parts", "/fleet", "/record"):
        assert f"href='{href}'" in text, f"missing door {href}"
        assert client.get(href).status_code == 200   # no dead door


# ---------- the wall's store doors flip to the board ------------------------

def test_the_wall_store_doors_flip_to_the_board(rig):
    conn, client, _db = rig
    doors = client.get("/wall").text
    doors = doors[doors.index("class='doors'"):]
    # BOTH stores now open to their own board — the active store's door moves
    # off /catalog, and the once-dead plain-text name becomes a real link
    assert "<a href='/board/demostore'>Demo Store</a>" in doors
    assert "<a href='/board/scaffold'>Scaffold</a>" in doors
    assert "<span>Scaffold</span>" not in doors   # no longer plain text
