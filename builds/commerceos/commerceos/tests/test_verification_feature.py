"""V2 — the verification feature on the one engine: the queue is file-driven
from the latest judged findings (no findings, no proposals); every staged
proposal PARKS (fit_critical never autos); the owner's approve runs the
return leg through the web resolve path (local flip + render check, no store
client); the progress numbers move on the flip; and the /catalog card
renders it in plain words."""

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from commerceos.catalog import canonical
from commerceos.catalog import workflows as W
from commerceos.catalog.verify_sources import METHOD, build_proposal, judge
from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.spine import writes
from commerceos.web.app import app

P1 = "gid://shopify/Product/1"   # two found claims (one agree, one conflict) -> queued
P2 = "gid://shopify/Product/2"   # all not_found -> drops (nothing to put before the owner)
P3 = "gid://shopify/Product/3"   # found, but already verified -> drops (done)
P4 = "gid://shopify/Product/4"   # claim value drifted under the findings -> drops (stale)
SRC = "https://maker.example/spec"


def _seed(conn):
    conn.executemany(
        "INSERT INTO canonical_products (shopify_id, handle, title, vendor, category, built_at)"
        " VALUES (?,?,?,?,?,'t')",
        [(P1, "torch-x", "Torch X", "BrandA", "Lighting"),
         (P2, "lamp-y", "Lamp Y", "BrandA", "Lighting"),
         (P3, "knife-z", "Knife Z", "BrandB", "Tools"),
         (P4, "rope-w", "Rope W", "BrandB", "Climbing")])
    conn.executemany(
        "INSERT INTO spec_claims (product, field, value, unit, source, verified,"
        " verified_on, fit_critical) VALUES (?,?,?,?,?,?,?,?)",
        [(P1, "ip_water_rating", "IP54", "IP code", "parsed:supplier-spec-blob", 0, None, 1),
         (P1, "battery_type", "Li-ion", None, "parsed:supplier-spec-blob", 0, None, 1),
         (P2, "burn_time", "40", "h", "parsed:supplier-spec-blob", 0, None, 1),
         (P3, "blade_length", "90", "mm", SRC, 1, "2026-07-01", 1),
         (P4, "length", "10", "m", "parsed:supplier-spec-blob", 0, None, 1)])
    conn.commit()


def _fclaim(field, value, unit, found=None, found_unit=None, src=None, quote=None):
    return {"field": field, "value": value, "unit": unit, "found_value": found,
            "found_unit": found_unit, "source_url": src, "quote": quote, "note": None}


def _write_findings(fdir):
    """the newest findings file plus an older empty one — the queue must glob
    the newest. raw legwork shape (no verdicts); the queue judges it."""
    (fdir / "verify-pilot-2026-07-01-findings.json").write_text(
        json.dumps({"date": "2026-07-01", "products": []}))
    findings = {"date": "2026-07-18", "products": [
        {"product_id": P1, "handle": "torch-x", "title": "Torch X",
         "vendor": "BrandA", "category": "Lighting", "claims": [
             _fclaim("ip_water_rating", "IP54", "IP code",
                     found="IP54", found_unit="IP code", src=SRC, quote="IP54 rated"),
             _fclaim("battery_type", "Li-ion", None,
                     found="NiMH", src=SRC, quote="NiMH pack")]},
        {"product_id": P2, "handle": "lamp-y", "title": "Lamp Y",
         "vendor": "BrandA", "category": "Lighting", "claims": [
             _fclaim("burn_time", "40", "h")]},                       # not_found
        {"product_id": P3, "handle": "knife-z", "title": "Knife Z",
         "vendor": "BrandB", "category": "Tools", "claims": [
             _fclaim("blade_length", "90", "mm",
                     found="90", found_unit="mm", src=SRC, quote="90 mm blade")]},
        {"product_id": P4, "handle": "rope-w", "title": "Rope W",
         "vendor": "BrandB", "category": "Climbing", "claims": [
             _fclaim("length", "12", "m",                             # drifted vs the claim set
                     found="12", found_unit="m", src=SRC, quote="12 m rope")]},
    ]}
    path = fdir / "verify-pilot-2026-07-18-findings.json"
    path.write_text(json.dumps(findings))
    return path


@pytest.fixture()
def env(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    conn = connect(db)
    canonical.ensure_schema(conn)
    ledger.ensure_schema(conn)
    _seed(conn)
    fdir = tmp_path / "reports"
    fdir.mkdir()
    _write_findings(fdir)
    monkeypatch.setattr(W, "FINDINGS_DIR", fdir)
    yield conn, TestClient(app)
    conn.close()


@pytest.fixture(autouse=True)
def no_store_client(monkeypatch):
    """the CW7 law carried into V2: this whole path constructs no store
    client — a construction is the test failing, not an inconvenience."""
    class Boom:
        def __init__(self, *a, **k):
            raise AssertionError("ShopifyClient constructed on a local branch")
    monkeypatch.setattr(writes, "ShopifyClient", Boom)


# --- the queue: file-driven, one item per qualifying product -----------------

def test_queue_yields_one_item_per_qualifying_product(env):
    conn, _ = env
    q = W.VERIFICATION.queue(conn)
    assert [w["product_id"] for w in q] == [P1]     # P2/P3/P4 all drop

    # the args are EXACTLY the pilot's own proposal shape, reused verbatim
    newest = sorted(W.FINDINGS_DIR.glob(W.FINDINGS_GLOB))[-1]
    findings = judge(json.loads(newest.read_text()))
    p1 = next(p for p in findings["products"] if p["product_id"] == P1)
    assert q[0]["args"] == build_proposal(p1)["args"]
    assert q[0]["args"]["field"] == "spec_verification"
    assert "torch-x" in q[0]["display"]


def test_no_findings_file_means_an_empty_queue(env, tmp_path, monkeypatch):
    conn, _ = env
    empty = tmp_path / "no-reports"
    empty.mkdir()
    monkeypatch.setattr(W, "FINDINGS_DIR", empty)
    assert W.VERIFICATION.queue(conn) == []          # no legwork, no proposals


# --- run_feature: stages, and every proposal PARKS ---------------------------

def test_run_feature_stages_and_every_proposal_parks(env):
    conn, _ = env
    rep = W.run_feature(conn, W.VERIFICATION, apply=False)
    assert rep["staged"] == 1 and rep["parked"] == 1
    assert rep["executed"] == 0 and rep["counted"] == 0

    rec = ledger.query(conn, function="catalog-enrichment")[0]
    assert rec["proposal"]["method"] == METHOD
    assert rec["action_type"] == "fit_critical"
    assert rec["status"] == "pending"                # parked, never auto-approved

    # a re-run must not stack the owner's queue: the parked proposal is
    # pending coverage, so the queue is empty until it resolves.
    rep2 = W.run_feature(conn, W.VERIFICATION, apply=False)
    assert rep2["queue_depth"] == 0 and rep2["staged"] == 0


# --- the approve return leg through the web resolve path ---------------------

def test_approve_runs_the_return_leg_and_flips_the_claim(env):
    conn, client = env
    rep = W.run_feature(conn, W.VERIFICATION, apply=False)
    rid = rep["log"][0]["record_id"]

    resp = client.post(f"/api/approvals/{rid}",
                       json={"decision": "approved", "confirm": "true"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["outcome"]["verified_rendered"] is True
    assert body["outcome"]["flipped"] == 1
    assert body["outcome"]["conflicts_stated"] == 1
    assert body["record"]["status"] == "executed"

    verified, verified_on, source = conn.execute(
        "SELECT verified, verified_on, source FROM spec_claims"
        " WHERE product=? AND field='ip_water_rating'", (P1,)).fetchone()
    assert verified == 1 and source == SRC
    assert verified_on                               # dated, not just marked

    # the conflict was stated for the ruling, never resolved
    assert conn.execute(
        "SELECT verified FROM spec_claims WHERE product=? AND field='battery_type'",
        (P1,)).fetchone()[0] == 0

    # verify() reads the return leg's receipt shape
    assert W.VERIFICATION.verify(body["outcome"], rep["log"][0]) is True
    assert W.VERIFICATION.verify({"verified_rendered": False}, {}) is False


# --- progress: the card numbers move on the flip -----------------------------

def test_progress_counts_move_after_the_flip(env):
    conn, client = env
    before = W.VERIFICATION.progress(conn)
    # 5 fit-critical claims; P3 seeded verified; P1's two found claims could
    # flip (P4's finding drifted, so it cannot); nothing pending yet. the
    # units are counted apart: claims (details) vs products.
    assert before["total"] == 5 and before["verified"] == 1
    assert before["unverified"] == 4
    assert before["with_findings"] == 2
    assert before["products"] == 4                   # P1..P4 carry fit-critical claims
    assert before["products_with_findings"] == 1     # only P1's evidence can flip
    assert before["pending"] == 0
    assert before["lapsed"] == 0

    rep = W.run_feature(conn, W.VERIFICATION, apply=False)
    assert W.VERIFICATION.progress(conn)["pending"] == 1

    rid = rep["log"][0]["record_id"]
    resp = client.post(f"/api/approvals/{rid}",
                       json={"decision": "approved", "confirm": "true"})
    assert resp.status_code == 200

    after = W.VERIFICATION.progress(conn)
    assert after["verified"] == 2 and after["unverified"] == 3
    assert after["with_findings"] == 1               # the stated conflict still waits
    assert after["pending"] == 0
    assert after["rate"] > before["rate"]


# --- the card: /catalog renders the feature in plain words -------------------

def test_catalog_card_renders_the_verification_front(env):
    conn, client = env
    page = client.get("/catalog")
    assert page.status_code == 200
    assert "spec check" in page.text                 # the plain label
    assert "/catalog/products?feature=verification" in page.text

    idx = client.get("/catalog/workflows")
    assert idx.status_code == 200
    assert "/catalog/workflows/verification" in idx.text

    front = client.get("/catalog/workflows/verification")
    assert front.status_code == 200
    assert "spec check" in front.text
    assert "start a batch" in front.text             # the gated run control


# --- the coldread repairs (2026-07-18): lapsed honesty, evidence, units ------

OLD_TS = "2026-07-11T12:00:00+00:00"                 # a week past any expiry


def _mint_lapsed_pilot_row(conn):
    """one pending row in the OLD pilot shape — method mutate_product_field on
    the spec-verification field — staged a week ago, long past expiry."""
    return ledger.mint(conn, {
        "agent": "spec-verifier", "function": "catalog-enrichment",
        "action_type": "fit_critical", "ts": OLD_TS,
        "intent": "check 2 safety-bearing details for Torch X (1 agree, 1 conflict)",
        "proposal": {"connector": "commerce", "method": "mutate_product_field",
                     "args": {"product_id": P1, "field": "spec_verification",
                              "value": {"claims": []}},
                     "args_hash": "old-pilot", "declared_type": "fit_critical"},
        "status": "pending", "expires_at": "2026-07-11T13:00:00+00:00",
    })


def test_expired_pending_is_lapsed_not_a_live_wait(env):
    conn, client = env
    # stage this feature's own proposal a week in the past -> expiry long gone
    past = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
    W.run_feature(conn, W.VERIFICATION, apply=False, now_ts=past)
    _mint_lapsed_pilot_row(conn)                     # plus the old-method shape

    # the ledger splits the facts: no live waits, two lapsed
    assert ledger.pending_queue(conn) == []
    assert len(ledger.lapsed_queue(conn)) == 2

    # the card counts them as lapsed — INCLUDING the old-method pilot row —
    # and pending stays live-only, agreeing with home
    prog = W.VERIFICATION.progress(conn)
    assert prog["pending"] == 0
    assert prog["lapsed"] == 2

    # home renders no actionable wait; the lapsed line names the re-run path
    home = client.get("/")
    assert home.status_code == 200
    assert "waits on you (" not in home.text          # no live-wait count card
    assert "nothing staged." in home.text
    assert "2 requests waited past the approval window and expired" in home.text
    # the lapsed card never links a lapsed item into decisions
    assert "waited past" in home.text and "re-proposed with current numbers" in home.text

    # the run page says it plainly, with the re-run path
    front = client.get("/catalog/workflows/verification")
    assert "2 lapsed — run a fresh batch to re-propose with current numbers" in front.text


def test_home_waits_and_the_card_agree_on_live_pending_only(env):
    conn, client = env
    _mint_lapsed_pilot_row(conn)                      # noise: lapsed, not live
    rep = W.run_feature(conn, W.VERIFICATION, apply=False)   # one LIVE wait
    assert rep["parked"] == 1

    live = ledger.pending_queue(conn)
    assert len(live) == 1                             # the lapsed row is excluded
    prog = W.VERIFICATION.progress(conn)
    assert prog["pending"] == 1 and prog["lapsed"] == 1

    home = client.get("/")
    assert f"waits on you ({len(live)})" in home.text  # same fact, same count
    front = client.get("/catalog/workflows/verification")
    assert "1 waiting for your call" in front.text
    assert "1 lapsed — run a fresh batch to re-propose with current numbers" in front.text

    # the decisions surface offers only the live wait; the lapsed one is a note
    dec = client.get("/approvals")
    assert "1 earlier request waited past the approval window" in dec.text


def test_run_page_renders_the_evidence_list_and_the_card_links_to_it(env):
    conn, client = env
    front = client.get("/catalog/workflows/verification")
    assert front.status_code == 200
    # per queued product: the plain field label, the found value, the QUOTE,
    # and the source link — from the findings file the queue reads
    assert "Torch X" in front.text
    assert "water resistance" in front.text           # plain label, never ip_water_rating
    assert "IP54 rated" in front.text                 # the quote, verbatim
    assert "NiMH pack" in front.text                  # the conflict's quote too
    assert f"href='{SRC}'" in front.text              # the source link
    assert "matches what we claim" in front.text
    assert "conflicts with what we claim" in front.text
    # the drifted (P4) and not-found (P2) products never show as evidence
    assert "Rope W" not in front.text and "Lamp Y" not in front.text

    # the card's evidence figure opens to this list — never a dead end
    card = client.get("/catalog")
    assert "/catalog/workflows/verification#evidence" in card.text
    assert "1 product with evidence in hand" in card.text


def test_no_evidence_yet_says_so_plainly(env, tmp_path, monkeypatch):
    conn, client = env
    empty = tmp_path / "no-reports"
    empty.mkdir()
    monkeypatch.setattr(W, "FINDINGS_DIR", empty)
    front = client.get("/catalog/workflows/verification")
    assert front.status_code == 200
    assert "no evidence gathered yet" in front.text


def test_progress_line_names_its_units(env):
    conn, client = env
    front = client.get("/catalog/workflows/verification")
    # claims are details, products are products — the line says which is which
    assert "5 details across 4 products" in front.text
    assert "4 still to check" in front.text
    card = client.get("/catalog")
    assert "5 details across 4 products" in card.text


def test_run_control_states_its_batch_size_and_links_decisions(env):
    conn, client = env
    front = client.get("/catalog/workflows/verification")
    # queue holds 1 product; the batch default caps at 100 -> the honest size is 1
    assert "start a batch of 1" in front.text
    # "stages into decisions" is a real link to the approvals surface
    assert "<a href='/approvals'>decisions</a>" in front.text
