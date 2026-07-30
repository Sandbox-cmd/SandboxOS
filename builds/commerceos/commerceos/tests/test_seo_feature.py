"""F4b: the listing-text FEATURE — the content agent's drafts (F4a) as a
front over the one workflow engine.

the pins for this item's binding laws, as re-trued by the repair round:
  - the queue is the refusal wall (the engine has no refusal hook): a draft
    the catalog cannot back never reaches the gate, and the held-back list
    names each product with a plain reason;
  - the queue is reversible-only: a consequential (spec-quoting) draft never
    rides a held batch — it stays on F4a's per-item park;
  - drafting is PER FIELD (B1a): a real human description is kept, only an
    empty or platform-echo field is drafted;
  - a near-echo of the raw name + vendor is too thin — the widened wall (M5)
    refuses it honestly;
  - a held batch stages and nothing executes; one glance-approve executes,
    verify-renders per drafted field, writes the facts back, and the queue
    DROPS; a dishonest read-back writes nothing back.

fixture — one product per behavior: p2/p4 plain reversible (both fields),
p7 title-only (its real description kept), p1 consequential (quotes a verified
claim), p5 refused-hype, p6 refused-thin, p3 strong (stays out).
"""

import pytest

from commerceos.catalog import canonical, runs, workflows
from commerceos.db import connect
from commerceos.fleet import content
from commerceos.fleet.content import (FUNCTION, DraftRefused,
                                      check_draft_against_catalog,
                                      propose_and_run)
from commerceos.gate import ledger
from commerceos.spine.schema import ensure_schema


class FakeSeoClient:
    """scripted productSeo mutation + per-product read-back. forced_readback
    makes the live surface disagree with the write so a dishonest store is
    caught by verify, never trusted."""

    def __init__(self, forced_readback=None):
        self.seo = {}
        self._forced = forced_readback

    def graphql(self, query, variables=None):
        if "mutation productSeo" in query:
            pid = variables["input"]["id"]
            self.seo.setdefault(pid, {"title": None, "description": None})
            self.seo[pid].update(variables["input"]["seo"])
            return {"productUpdate": {
                "product": {"id": pid, "seo": dict(self.seo[pid])},
                "userErrors": []}}
        if "query productSeo" in query:
            pid = variables["id"]
            back = self._forced if self._forced is not None else self.seo.get(pid, {})
            return {"product": {"id": pid, "seo": dict(back)}}
        raise AssertionError(f"unexpected query: {query[:60]}")


# the LIVE truth: products, canonical_products, and spec_claims all key on the
# FULL gid (verified read-only against data/demostore.db). the fixture seeds the
# live shape so a card that mis-keys the id fails here, not only in production.
P1 = "gid://shopify/Product/1001"   # Torch X — verified claim -> consequential
P2 = "gid://shopify/Product/1002"   # Rope Y — echo title, no desc -> both fields
P3 = "gid://shopify/Product/1003"   # Tent Z — written, strong, stays out
P4 = "gid://shopify/Product/1004"   # Head Lamp — missing -> both fields
P5 = "gid://shopify/Product/1005"   # Ultimate Lantern — hype -> refused
P6 = "gid://shopify/Product/1006"   # Gizmo — no category/claims -> too thin
P7 = "gid://shopify/Product/1007"   # Camp Stove — echo title, REAL desc -> title only


def seed_catalog(conn):
    conn.executemany(
        "INSERT INTO products (shopify_id, title, vendor, seo_title,"
        " seo_description, source, fetched_at) VALUES (?,?,?,?,?,?,'t')",
        [(P1, "Torch X", "Acme", None, None, "s"),
         (P2, "Rope Y", "Bindworks", "Rope Y", None, "s"),
         (P3, "Tent Z", "Peak", "Tent Z 4-Season Shelter | Peak",
          "A 4-season tent built for winter lines.", "s"),
         (P4, "Head Lamp", "Nord", None, None, "s"),
         (P5, "Ultimate Lantern", "Glow", None, None, "s"),
         (P6, "Gizmo", "Widgetco", None, None, "s"),
         (P7, "Camp Stove", "BrassCo", "Camp Stove",
          "Hand-built brass stove, field-tested across three seasons.", "s")])
    conn.executemany(
        "INSERT INTO canonical_products (shopify_id, handle, title, vendor,"
        " category, built_at) VALUES (?,?,?,?,?,'t')",
        [(P1, "torch-x", "Torch X", "Acme", "torches"),
         (P2, "rope-y", "Rope Y", "Bindworks", "ropes"),
         (P4, "head-lamp", "Head Lamp", "Nord", "headlamps"),
         (P7, "camp-stove", "Camp Stove", "BrassCo", "stoves")])
    conn.executemany(
        "INSERT INTO spec_claims (product, field, value, unit, source,"
        " verified, verified_on, fit_critical) VALUES (?,?,?,?,?,?,?,?)",
        [(P1, "beam_output", "900", "lm", "datasheet:acme", 1, "2026-07-01", 0),
         (P1, "temp_rating", "-20", "C", "parsed:supplier-spec-blob", 0, None, 1)])
    conn.commit()


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "seo-feature.db")
    ensure_schema(c)
    ledger.ensure_schema(c)
    canonical.ensure_schema(c)
    seed_catalog(c)
    yield c
    c.close()


def test_queue_holds_only_reversible_drafts_and_refusals_are_named(conn):
    """the queue is the wall: only reversible drafts that pass the refusal law
    ride it; the spec-quoting draft parks per item; the hype and the too-thin
    drafts are held back and named."""
    q = content.seo_queue(conn)
    ids = {it["product_id"] for it in q}
    assert ids == {P2, P4, P7}                     # the plain reversible drafts only
    assert not ({P1, P5, P6} & ids)                # consequential + both refusals excluded
    for it in q:
        assert set(it["args"]) >= {"product_id", "title", "description"}
        # the STORED id (top-level) is the FULL gid the products table keys on,
        # and it equals the executor's arg id in the live shape.
        assert it["product_id"] == it["args"]["product_id"]
        assert it["product_id"].startswith("gid://shopify/Product/")
        assert it["product_id"] in (P2, P4, P7)
        assert "was" in it
    # p7's real description is kept — only its echoed title is drafted (B1a)
    p7 = next(it for it in q if it["product_id"] == P7)
    assert p7["title"] and p7["description"] is None
    # the held-back list names each product and why (M2)
    held = content.seo_held_back(conn)
    assert {h["product"] for h in held} == {P5, P6}
    reasons = {h["product"]: h["reason"] for h in held}
    assert "thin" in reasons[P6]                     # the near-echo, too thin
    assert "sales word" in reasons[P5]               # the hype word
    prog = content.seo_progress(conn)
    assert prog["to_draft"] == 3 and prog["held_back"] == 2 and prog["written"] == 1


def test_pre_park_state_names_the_unproposed_consequential_draft(conn):
    """the breathing gap: before the writer proposes, the consequential draft
    is inside the missing-or-weak door but no per-item wait names it. to_stage
    names exactly those, so every weak product is accounted; once staged, the
    live wait covers it and to_stage clears (the parked-state accounting is
    unchanged)."""
    prog = content.seo_progress(conn)                 # ledger empty — nothing proposed yet
    assert prog["to_stage"] == 1 and prog["waiting"] == 0
    # ready to draft + waiting + to_stage + held back = the whole weak set
    assert (prog["to_draft"] + prog["waiting"] + prog["to_stage"]
            + prog["held_back"]) == prog["weak"] == 6
    # once the writer stages it per item, the wait covers it and to_stage clears
    propose_and_run(conn, "listing_draft", limit=10, client=FakeSeoClient())
    after = content.seo_progress(conn)
    assert after["waiting"] == 1 and after["to_stage"] == 0
    assert (after["to_draft"] + after["waiting"] + after["to_stage"]
            + after["held_back"]) == after["weak"]


def test_a_near_echo_of_the_raw_name_is_refused_as_too_thin(conn):
    """M5: a draft that says nothing past the raw name + vendor is template
    smell — the wall refuses it, it never reaches a glance."""
    with pytest.raises(DraftRefused, match="thin"):
        check_draft_against_catalog(conn, {
            "product": P6, "title": "Gizmo | Widgetco",
            "description": "Gizmo from Widgetco.", "claims": [], "thin": True})


def test_run_hold_stages_the_batch_and_nothing_executes(conn):
    before = len(content.seo_queue(conn))
    rep = workflows.run_feature(conn, workflows.SEO, hold=True)
    assert rep["batch"] == before and rep["parked"] == before
    assert rep["executed"] == 0 and rep["counted"] == 0
    assert rep.get("run_id")
    run = runs.get(conn, rep["run_id"])
    assert run["batch"] == before
    statuses = {r[0] for r in conn.execute("SELECT status FROM ledger").fetchall()}
    assert statuses == {"pending"}
    assert conn.execute("SELECT COUNT(*) FROM handles").fetchone()[0] == 0


def test_glance_approve_executes_verifies_and_the_queue_drops(conn):
    before = len(content.seo_queue(conn))
    rep = workflows.run_feature(conn, workflows.SEO, hold=True)
    fake = FakeSeoClient()
    res = runs.approve(conn, rep["run_id"], workflows.SEO, by="me", client=fake)
    assert res["approved"] == before and res["counted"] == before
    for pid in (P2, P4, P7):
        row = conn.execute(
            "SELECT seo_title, seo_description, source FROM products"
            " WHERE shopify_id = ?", (pid,)).fetchone()
        assert row["seo_title"]                              # a title landed for each
        assert row["source"].startswith("writeback:")         # via the writeback lane
    # p7's kept human description survives the title-only writeback (B1a)
    p7desc = conn.execute("SELECT seo_description FROM products WHERE shopify_id = ?",
                          (P7,)).fetchone()[0]
    assert "Hand-built brass stove" in p7desc
    assert len(content.seo_queue(conn)) < before             # the card's queue drops


def test_verify_checks_only_drafted_fields_and_refuses_a_dishonest_readback(conn):
    both = {"title": "Rope Y | Bindworks",
            "description": "Rope Y from Bindworks. Find it in ropes."}
    ok = {"ok": True, "seo": {"title": both["title"], "description": both["description"]}}
    assert content.seo_verify(ok, both) is True
    lie = {"ok": True, "seo": {"title": "something else", "description": both["description"]}}
    assert content.seo_verify(lie, both) is False
    # a title-only draft: the untouched description field is not required to match
    title_only = {"title": "Camp Stove | BrassCo", "description": None}
    out = {"ok": True, "seo": {"title": title_only["title"], "description": "the real one, kept"}}
    assert content.seo_verify(out, title_only) is True
    # through a batch: a lying store writes nothing back
    rep = workflows.run_feature(conn, workflows.SEO, hold=True)
    liar = FakeSeoClient(forced_readback={"title": "not what you asked", "description": None})
    runs.approve(conn, rep["run_id"], workflows.SEO, by="me", client=liar)
    for pid in (P2, P4, P7):
        src = conn.execute("SELECT source FROM products WHERE shopify_id = ?",
                           (pid,)).fetchone()["source"] or ""
        assert not src.startswith("writeback:")


def test_spec_quoting_drafts_park_per_item_never_in_a_batch(conn):
    assert P1 not in {it["product_id"] for it in content.seo_queue(conn)}
    res = propose_and_run(conn, "listing_draft", limit=10, client=FakeSeoClient())
    assert res["parked"] >= 1
    parked = [r for r in ledger.query(conn, function=FUNCTION)
              if r["status"] == "pending"]
    assert any("900 lm" in (r["proposal"]["args"].get("description") or "")
               for r in parked)                              # product 1's beam claim, parked
    with pytest.raises(DraftRefused):                        # the honest-refusal path still fires
        check_draft_against_catalog(conn, {
            "product": P5, "title": "Ultimate Lantern | Glow",
            "description": "The ultimate lantern.", "claims": []})
