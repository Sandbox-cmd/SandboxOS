"""CD1's checks: the /catalog operator dashboard — feature cards home, product
browser, per-product drill, and the flag-review queue.

the anti-blackbox contract, encoded: every card number is live (from
feature.progress / feature.queue) and links to its rows; the browser filters by
lifecycle state; the drill shows canonical claims + provenance + state +
history; the flag queue shows evidence; and [run batch] rides the SAME
/approvals resolve verb — this surface invents no second approve path.

all reads served through the TestClient over a seeded temp db (the pattern from
test_web_surface). the client host is 'testclient' -> localhost -> auth passes.
"""

import pytest
from fastapi.testclient import TestClient

from commerceos.catalog import canonical, lifecycle as L, workflows as W
from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.spine.schema import ensure_schema
from commerceos.web.app import app

VALID13 = "4006381333931"    # checksum-valid EAN-13
VALID12 = "036000291452"     # checksum-valid UPC-A


def seed_product(conn, pid, product_type="Flashlights", title=None, status="ACTIVE"):
    conn.execute(
        "INSERT INTO products (shopify_id, handle, title, status, vendor, product_type,"
        " tags, raw, source, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (pid, f"h-{pid}", title or f"P {pid}", status, "V", product_type, "[]", "{}",
         "test", "2026-07-12T00:00:00Z"))


def seed_variant(conn, pid, barcode):
    conn.execute(
        "INSERT INTO variants (shopify_id, product_id, sku, barcode, price_minor,"
        " inventory, source, fetched_at) VALUES (?,?,?,?,?,?,?,?)",
        (f"v-{pid}", pid, "SKU-1", barcode, 1000, 1, "test", "2026-07-12T00:00:00Z"))


def seed_media(conn, pid, media_count):
    conn.execute(
        "INSERT INTO product_media (product_id, media_count, first_image_url, source, fetched_at)"
        " VALUES (?,?,?,?,?)",
        (pid, media_count, "u" if media_count else None, "test", "2026-07-12T00:00:00Z"))


@pytest.fixture()
def env(tmp_path, monkeypatch):
    db = tmp_path / "catalog.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    conn = connect(db)
    ensure_schema(conn)          # facts: products, variants, product_meta, lifecycle
    ledger.ensure_schema(conn)   # the gate ledger + handles
    canonical.ensure_schema(conn)  # canonical_products + spec_claims
    yield conn, TestClient(app)
    conn.close()


# --- the home: a card per feature, live numbers, every number to its rows ---

def test_home_shows_a_card_per_feature_with_live_progress_and_queue_depth(env):
    conn, client = env
    seed_product(conn, "p1"); seed_variant(conn, "p1", "'" + VALID13)   # gtin fixable
    seed_product(conn, "p2"); seed_variant(conn, "p2", VALID12[1:])     # gtin fixable
    seed_product(conn, "p3"); seed_variant(conn, "p3", VALID13)         # already valid
    conn.commit()

    gtin_depth = len(W.GTIN.queue(conn))
    cls_depth = len(W.CLASSIFICATION.queue(conn))
    gprog = W.GTIN.progress(conn)

    page = client.get("/catalog")
    assert page.status_code == 200
    # a card for every feature in FEATURES
    for name in W.FEATURES:
        assert name in page.text
    # the live queue depth for each feature, linking to its rows
    assert f"/catalog/products?feature=gtin'>{gtin_depth}</a>" in page.text
    assert f"/catalog/products?feature=classification'>{cls_depth}</a>" in page.text
    # a real progress number is shown, not an invented figure
    assert f"{gprog['total']} total" in page.text
    # the flags card links to the review queue
    assert "/catalog/flags" in page.text


def test_a_cards_queue_depth_equals_the_features_queue_and_points_to_those_rows(env):
    conn, client = env
    seed_product(conn, "g1"); seed_variant(conn, "g1", "'" + VALID13)  # fixable -> queued
    seed_product(conn, "g2"); seed_variant(conn, "g2", VALID13)        # valid -> not queued
    conn.commit()

    depth = len(W.GTIN.queue(conn))
    assert depth == 1                                   # exactly the one fixable artifact
    page = client.get("/catalog")
    assert f"/catalog/products?feature=gtin'>{depth}</a>" in page.text

    # drilling the number lands on exactly those product rows and no others
    browsed = client.get("/catalog/products?feature=gtin")
    assert "/catalog/products/g1" in browsed.text
    assert "/catalog/products/g2" not in browsed.text


# --- the browser: filter by lifecycle state ---------------------------------

def test_browser_filters_by_lifecycle_state(env):
    conn, client = env
    for pid, status in [("a1", "ACTIVE"), ("a2", "ACTIVE"), ("d1", "DRAFT"), ("f1", "ACTIVE")]:
        seed_product(conn, pid, status=status)
    conn.commit()
    for pid, status in [("a1", "ACTIVE"), ("a2", "ACTIVE"), ("d1", "DRAFT"), ("f1", "ACTIVE")]:
        L.set_initial(conn, pid, status)
    L.raise_flag(conn, "f1", reason="looks off")        # active -> flagged

    flagged = client.get("/catalog/products?state=flagged")
    assert "/catalog/products/f1" in flagged.text
    for other in ("a1", "a2", "d1"):
        assert f"/catalog/products/{other}" not in flagged.text

    active = client.get("/catalog/products?state=active")
    assert "/catalog/products/a1" in active.text and "/catalog/products/a2" in active.text
    assert "/catalog/products/f1" not in active.text    # it moved to flagged

    draft = client.get("/catalog/products?state=draft")
    assert "/catalog/products/d1" in draft.text
    assert "/catalog/products/a1" not in draft.text


# --- view 2: the combined board (stage lanes + filter/sort/search) ----------

def test_board_shows_stage_lanes_with_counts_matching_counts_by_state(env):
    conn, client = env
    for pid, status in [("a1", "ACTIVE"), ("a2", "ACTIVE"), ("a3", "ACTIVE"),
                        ("d1", "DRAFT"), ("z1", "ARCHIVED")]:
        seed_product(conn, pid, status=status)
    conn.commit()
    for pid, status in [("a1", "ACTIVE"), ("a2", "ACTIVE"), ("a3", "ACTIVE"),
                        ("d1", "DRAFT"), ("z1", "ARCHIVED")]:
        L.set_initial(conn, pid, status)

    counts = L.counts_by_state(conn)          # {active:3, draft:1, archived:1, ...}
    page = client.get("/catalog/products")
    assert page.status_code == 200
    assert "class='board'" in page.text       # the combined board renders
    # every stage lane leads with its plain label + its live count, and that
    # count equals counts_by_state (the pipeline is the primary navigation).
    for stage, n in counts.items():
        from commerceos.web.app import state_label
        assert f"{state_label(stage)} · {n:,}" in page.text


def test_board_state_filter_narrows_every_lane_to_that_stage(env):
    conn, client = env
    for pid, status in [("a1", "ACTIVE"), ("d1", "DRAFT")]:
        seed_product(conn, pid, status=status)
    conn.commit()
    for pid, status in [("a1", "ACTIVE"), ("d1", "DRAFT")]:
        L.set_initial(conn, pid, status)

    draft = client.get("/catalog/products?state=draft")
    assert "/catalog/products/d1" in draft.text          # a card links to its drill
    assert "/catalog/products/a1" not in draft.text       # the active one is filtered out


def test_board_gap_filter_narrows_to_products_carrying_that_gap(env):
    conn, client = env
    seed_product(conn, "img", status="ACTIVE"); seed_media(conn, "img", 3)   # has a photo
    seed_product(conn, "noimg", status="ACTIVE")                              # no media row -> needs a photo
    conn.commit()
    L.set_initial(conn, "img", "ACTIVE"); L.set_initial(conn, "noimg", "ACTIVE")

    photo = client.get("/catalog/products?gap=photo")
    assert photo.status_code == 200
    assert "needs a photo" in photo.text
    assert "/catalog/products/noimg" in photo.text        # carries the gap
    assert "/catalog/products/img" not in photo.text       # has a photo -> excluded


def test_board_incoming_feature_query_maps_to_the_matching_gap(env):
    conn, client = env
    seed_product(conn, "p1", status="ACTIVE"); conn.commit()
    L.set_initial(conn, "p1", "ACTIVE")
    # the overview links carry ?feature=delist; the board maps it onto the
    # flagged-to-remove gap filter (plain-labeled), never showing the raw key.
    page = client.get("/catalog/products?feature=delist")
    assert page.status_code == 200
    assert "flagged to remove" in page.text
    # the mapping lit the flagged filter — the "needs review" saved view is active
    assert "class='tab here'" in page.text


# --- view 2b: the table density (UI-polish) ----------------------------------

def test_board_default_stays_cards(env):
    conn, client = env
    seed_product(conn, "p1", status="ACTIVE")
    conn.commit()
    L.set_initial(conn, "p1", "ACTIVE")
    page = client.get("/catalog/products")
    assert page.status_code == 200
    assert "class='pcard'" in page.text
    assert "<table" not in page.text


def test_board_table_view_shows_the_specs_columns(env):
    from commerceos.web.app import state_label
    conn, client = env
    seed_product(conn, "p1", title="Torch X", status="ACTIVE")
    seed_product(conn, "p2", title="Lamp Y", status="DRAFT")
    conn.commit()
    L.set_initial(conn, "p1", "ACTIVE")
    L.set_initial(conn, "p2", "DRAFT")

    page = client.get("/catalog/products?density=table")
    assert page.status_code == 200
    assert "<table" in page.text
    assert "class='pcard'" not in page.text  # the table view replaces the lanes
    # both seeded rows, each opening to its drill
    assert "/catalog/products/p1" in page.text
    assert "/catalog/products/p2" in page.text
    assert "Torch X" in page.text and "Lamp Y" in page.text
    assert "V" in page.text  # the seeded vendor, on the row
    # plain lifecycle-state words, not the raw stage key
    assert state_label("active") in page.text
    assert state_label("draft") in page.text


def test_table_view_composes_with_filters_and_survives_the_form(env):
    conn, client = env
    seed_product(conn, "p1", status="ACTIVE")
    seed_product(conn, "d1", status="DRAFT")
    conn.commit()
    L.set_initial(conn, "p1", "ACTIVE")
    L.set_initial(conn, "d1", "DRAFT")

    page = client.get("/catalog/products?density=table&state=draft")
    assert page.status_code == 200
    assert "<table" in page.text
    assert "/catalog/products/d1" in page.text
    assert "/catalog/products/p1" not in page.text        # narrowed by the filter
    # the hidden form field carries density so "apply" never resets the view
    assert "name='density' value='table'" in page.text
    # the cards-view chip keeps the active filter in its href
    assert "state=draft" in page.text


def test_the_word_density_never_reaches_the_screen(env):
    conn, client = env
    seed_product(conn, "p1", status="ACTIVE")
    conn.commit()
    L.set_initial(conn, "p1", "ACTIVE")
    for path in ("/catalog/products", "/catalog/products?density=table"):
        text = _visible_text(client.get(path).text).lower()
        assert "density" not in text        # a spec term — never on screen


def test_table_view_words_its_own_filter_caption(env):
    # producer finding: "constrains every lane at once" is false in the table
    # view — there are no lanes to constrain. each view names its own truth.
    conn, client = env
    seed_product(conn, "p1", status="ACTIVE")
    conn.commit()
    L.set_initial(conn, "p1", "ACTIVE")

    cards = client.get("/catalog/products").text
    table = client.get("/catalog/products?density=table").text
    assert "constrains every lane at once" in cards
    assert "constrains every lane at once" not in table
    assert "narrows the table" in table


def test_table_view_cap_line_is_honest_at_scale(env):
    # producer finding: "N products, one row each" lied once N exceeded the
    # 100-row cap — only 100 rows actually render. pin the honest window line
    # and the true row count over a scratch db seeded past the cap.
    conn, client = env
    for i in range(120):
        pid = f"p{i:03d}"
        seed_product(conn, pid, status="ACTIVE")
        L.set_initial(conn, pid, "ACTIVE")
    conn.commit()

    page = client.get("/catalog/products?density=table").text
    assert "showing the first 100 of 120 products — filter to narrow." in page
    assert "one row each" not in page          # never claimed once capped
    assert page.count("<tr>") == 101           # 1 header + exactly 100 rows


# --- the drill: claims + provenance + state + history -----------------------

def test_drill_shows_claims_provenance_lifecycle_state_and_history(env):
    conn, client = env
    seed_product(conn, "p1", title="Torch X")
    conn.commit()
    conn.execute(
        "INSERT INTO canonical_products (shopify_id, handle, title, vendor, category, built_at)"
        " VALUES ('p1','torch-x','Torch X','BrandA','Lighting','t')")
    conn.execute(
        "INSERT INTO spec_claims (product, field, value, unit, source, verified, fit_critical)"
        " VALUES ('p1','ip_water_rating','IP54','IP code','parsed:supplier-spec-blob',0,1)")
    conn.commit()
    # active -> flagged -> delisted, so history carries who/when/why
    L.set_initial(conn, "p1", "ACTIVE")
    L.raise_flag(conn, "p1", reason="decor_keyword")
    L.delist(conn, "p1", reason="pulled on suspicion")

    page = client.get("/catalog/products/p1")
    assert page.status_code == 200
    assert "Torch X" in page.text
    # the canonical claim + its provenance + the fit-critical marker, in PLAIN
    # words — the raw field code never shows; its friendly label does.
    assert "ip_water_rating" not in page.text
    assert "water resistance" in page.text and "IP54" in page.text
    # the raw source code never shows; the plain sentence does
    assert "parsed:supplier-spec-blob" not in page.text
    assert "supplier's spec sheet" in page.text
    # the safety-critical marker in plain words, not the jargon
    assert "must be right" in page.text
    # an unverified claim renders honestly as an "only claimed" chip, never verified
    assert "only claimed" in page.text
    # current lifecycle stage in plain words + the history moves (plain why lines)
    assert "removed from store" in page.text               # delisted, in plain words
    assert "decor_keyword" not in page.text                # the raw signal code never shows
    assert "home decor" in page.text                       # mapped to plain evidence
    assert "pulled on suspicion" in page.text              # a human note, kept verbatim


def _visible_text(html: str) -> str:
    """the text a person actually reads — tags, styles, scripts stripped, so the
    guard checks words on screen, not href/class attributes."""
    import re
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", html)


def test_no_jargon_or_raw_codes_reach_the_screen(env):
    """the plain-first guard (the lint the voice pass asked for): no code
    identifier and no insider term reaches a person's screen. a check, not taste
    — if this fails, a word broke the plain-first law on a real rendered surface.

    the scar (coldread 2026-07-18): mutate_variant_field reached home's "what
    happened" because this guard never looked at "/". so the guard now stages
    REAL gated work — a reversible batch, a consequential ruling, a fit-critical
    verification proposal, and one lapsed old-method pilot row — and walks home
    and the record too, with live rows on them. it also walks /findings with a
    live analyst hunt finding and an aged-out one on it, so a hunt's raw metric
    key (analyst.category_sales_shift) or a raw disposition (aged_out) can
    never reach the screen."""
    import re
    from datetime import datetime, timezone
    conn, client = env
    seed_product(conn, "p1", title="Torch X")
    seed_variant(conn, "p1", "'4006381333931")
    conn.execute("INSERT INTO canonical_products (shopify_id, handle, title, vendor,"
                 " category, built_at) VALUES ('p1','torch-x','Torch X','BrandA','Lighting','t')")
    conn.execute("INSERT INTO spec_claims (product, field, value, unit, source, verified,"
                 " fit_critical) VALUES ('p1','ip_water_rating','IP54','IP code',"
                 "'parsed:supplier-spec-blob',0,1)")
    conn.commit()
    L.set_initial(conn, "p1", "ACTIVE")

    from commerceos.gate import gate as G
    r = client.post("/catalog/run/gtin", follow_redirects=False)              # a held batch
    run_path = r.headers["location"]                                          # its preview page
    mr = client.post("/catalog/run/merchandising", follow_redirects=False)    # a merch create batch
    merch_run_path = mr.headers["location"]                                   # its preview page
    client.post("/catalog/rule/p1", data={"ruling": "remove"},
                follow_redirects=False)                                       # a live wait
    G.submit(conn, {                                                          # the fit-critical wait
        "agent": "spec-verifier", "function": "catalog-enrichment",
        "method": "mutate_spec_verification",
        "args": {"product_id": "p1", "field": "spec_verification", "value": {"claims": []}},
        "declared_type": "fit_critical", "intent": W.VERIFICATION.intent,
        "rationale": "torch-x  1 agree / 1 conflict of 2 claims",
        "provenance": [{"source": "https://maker.example/spec"}],
    })
    ledger.mint(conn, {                                                       # a lapsed pilot row
        "agent": "spec-verifier", "function": "catalog-enrichment",
        "action_type": "fit_critical", "intent": W.VERIFICATION.intent,
        "proposal": {"connector": "commerce", "method": "mutate_product_field",
                     "args": {"product_id": "p1", "field": "spec_verification"},
                     "args_hash": "old", "declared_type": "fit_critical"},
        "status": "pending", "expires_at": "2026-07-11T13:00:00+00:00",
    })

    from commerceos.watching import findings as WF
    WF.mint(conn,                                                             # a live hunt finding
            "category Flashlights net sales for the week of 2026-07-06 are 900 AED,"
            " -45% vs 1,600 AED the week before (6 vs 7 orders)",
            "risk", {"evaluations": [], "facts": ["order_lines:1", "order_lines:2"]},
            metric="analyst.category_sales_shift", slice_="category=Flashlights")
    WF.mint(conn,                                                             # an aged-out one
            "vendor Acme net sales surged and nobody acted",
            "opportunity", {"evaluations": [], "facts": ["order_lines:3"]},
            metric="analyst.vendor_sales_shift", slice_="vendor=Acme",
            now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    WF.age_out(conn)

    banned = ["enrichment", "lifecycle", "normaliz", "fit-critical", "audit mirror",
              "parsed:", "shopify:", "writeback:", "supplier-spec-blob",
              "the operator", "fasttext", "the operations index"]
    snake = re.compile(r"[a-z]{2,}_[a-z_]{2,}")   # a code identifier on screen
    for path in ["/", "/wall", "/board/demostore", "/record", "/catalog", "/catalog/products", "/catalog/workflows",
                 "/catalog/workflows/gtin", "/catalog/workflows/verification",
                 "/catalog/workflows/seo", "/catalog/workflows/merchandising",
                 "/catalog/products?density=table",
                 "/catalog/flags", "/catalog/products/p1", "/fleet", "/findings",
                 run_path, merch_run_path]:
        text = _visible_text(client.get(path).text).lower()
        for term in banned:
            assert term not in text, f"{path}: insider term '{term}' reached the screen"
        leaked = snake.findall(text)
        assert not leaked, f"{path}: a code identifier leaked to the screen: {leaked[:5]}"


# --- the flag-review queue: evidence + the one gate -------------------------

def test_flags_queue_shows_a_flag_with_its_evidence(env):
    conn, client = env
    seed_product(conn, "p1", title="Wall Sign Lantern")
    conn.commit()
    L.set_initial(conn, "p1", "ACTIVE")
    L.raise_flag(conn, "p1", reason="decor_keyword, decor_type")

    page = client.get("/catalog/flags")
    assert page.status_code == 200
    assert "/catalog/products/p1" in page.text
    # the evidence is laid out in PLAIN words — the raw signal codes never show
    assert "decor_keyword" not in page.text and "decor_type" not in page.text
    assert "home decor" in page.text                       # the plain reason
    assert "matched 2 signals" in page.text                # the signal count, plainly
    # the ruling routes through the existing approvals flow, not a new verb
    assert "/approvals" in page.text
    # keep / remove / archive are offered as gated rulings
    assert "remove from store" in page.text and "archive" in page.text


def test_flags_empty_state_says_so_plainly(env):
    conn, client = env
    page = client.get("/catalog/flags")
    assert page.status_code == 200
    assert "nothing flagged right now" in page.text


def test_a_flag_ruling_stages_a_proposal_and_routes_to_decisions(env):
    conn, client = env
    seed_product(conn, "p1")
    conn.commit()
    L.set_initial(conn, "p1", "ACTIVE")
    L.raise_flag(conn, "p1", reason="decor_keyword, decor_type")

    # ruling "remove from store" stages ONE gated proposal and redirects to
    # decisions — it does not approve or write here.
    resp = client.post("/catalog/rule/p1", data={"ruling": "remove"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/approvals"

    staged = ledger.query(conn, function="catalog-enrichment")
    assert staged, "a ruling should stage at least one proposal"
    assert staged[0]["proposal"]["method"] == "mutate_product_state"
    assert staged[0]["proposal"]["args"] == {"product_id": "p1", "state": "delisted"}
    assert staged[0]["status"] == "pending"                # consequential parks; never approved here

    # an unknown ruling is refused
    bad = client.post("/catalog/rule/p1", data={"ruling": "nonsense"}, follow_redirects=False)
    assert bad.status_code == 400


# --- view 3: the workflow view (front index + a per-front run-and-watch page) -

def test_workflows_index_and_a_front_page_show_live_coverage(env):
    conn, client = env
    seed_product(conn, "g1"); seed_variant(conn, "g1", "'" + VALID13)   # fixable barcode
    seed_product(conn, "g2"); seed_variant(conn, "g2", VALID13)         # already valid
    conn.commit()

    from commerceos.web.app import feature_label
    idx = client.get("/catalog/workflows")
    assert idx.status_code == 200
    # one working page per front, named in PLAIN words, each opening to its page
    for name in W.FEATURES:
        assert feature_label(name) in idx.text
        assert f"/catalog/workflows/{name}" in idx.text

    depth = len(W.GTIN.queue(conn))
    page = client.get("/catalog/workflows/gtin")
    assert page.status_code == 200
    assert "coverage now" in page.text
    # the queue opens to the products board filtered to this gap
    assert "/catalog/products?feature=gtin" in page.text
    # the gated run control rides the existing run path, labelled plainly
    assert "start a batch" in page.text
    assert "action='/catalog/run/gtin'" in page.text
    # an unknown front is refused plainly
    assert client.get("/catalog/workflows/not-a-front").status_code == 404


# --- [run batch] rides the ONE approve verb; no second approve path ---------

def test_run_batch_stages_and_reuses_the_one_approvals_resolve_verb(env):
    conn, client = env
    seed_product(conn, "p1"); seed_variant(conn, "p1", "'" + VALID13)
    conn.commit()

    # the per-item resolve verb is the web-surface's POST endpoint
    resolve_posts = [r.path for r in app.routes
                     if "POST" in getattr(r, "methods", set()) and "approvals" in r.path]
    assert resolve_posts == ["/api/approvals/{record_id}"]

    # the catalog surface's POSTs: the STAGING verbs (rule, run, and the CW5
    # merchandising nav placement — each parks a proposal into decisions, never
    # approves) plus the RULED batch verbs (WF-approve — every front has an
    # approval step). none is a second gate: the merch nav walks gate.submit and
    # the batch approve walks gate.resolve per record, same wall, and the one
    # per-item resolve verb above stays the only place a person approves.
    catalog_posts = sorted(r.path for r in app.routes
                           if "POST" in getattr(r, "methods", set()) and r.path.startswith("/catalog"))
    assert catalog_posts == ["/catalog/merchandising/nav",
                             "/catalog/rule/{product_id:path}",
                             "/catalog/run/{feature}",
                             "/catalog/runs/{run_id}/approve",
                             "/catalog/runs/{run_id}/decline"]

    # [run batch] on a reversible front HOLDS: it stages parked proposals and
    # lands on the batch preview — nothing auto-approves, nothing executes
    resp = client.post("/catalog/run/gtin", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/catalog/runs/")

    # it really staged through gate.submit — held pending, no approve verb ran
    staged = ledger.query(conn, function="catalog-enrichment")
    assert staged, "run batch should stage at least one proposal"
    assert staged[0]["proposal"]["method"] == "mutate_variant_field"
    assert staged[0]["status"] == "pending"


def test_run_batch_on_an_unknown_feature_is_refused(env):
    conn, client = env
    resp = client.post("/catalog/run/not-a-feature", follow_redirects=False)
    assert resp.status_code == 404
