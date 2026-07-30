"""F4a: the content agent's drafting half — listings drafted from catalog
facts only. the weak rule finds unwritten listings; verified claims are the
only spec values that reach customer-facing text; a draft the catalog
cannot back is refused with its reason; reversible drafts auto-execute
with a verify-rendered receipt while spec-quoting drafts park; provenance
rides every proposal; the search-listing limits hold."""

import pytest

from commerceos.catalog import canonical
from commerceos.db import connect
from commerceos.fleet.content import (AGENT, DESCRIPTION_LIMIT, FUNCTION,
                                      TITLE_LIMIT, WORK_KINDS, DraftRefused,
                                      check_draft_against_catalog,
                                      compute_listing_drafts, propose_and_run)
from commerceos.gate import ledger
from commerceos.spine.schema import ensure_schema

LONG_TITLE = ("Expedition Down Sleeping Bag With Extra Long Zip"
              " And Oversized Storage Sack")  # 76 chars — past the 60 limit


class FakeClient:
    """scripted GraphQL for mutate_seo: productUpdate(seo) + readback."""

    def __init__(self):
        self.seo = {}

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
            return {"product": {"id": pid, "seo": dict(self.seo.get(pid, {}))}}
        raise AssertionError(f"unexpected query: {query[:60]}")


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "content.db")
    ensure_schema(c)
    ledger.ensure_schema(c)
    canonical.ensure_schema(c)
    c.executemany(
        "INSERT INTO products (shopify_id, title, vendor, seo_title,"
        " seo_description, source, fetched_at) VALUES (?,?,?,?,?,?,'t')",
        [("1", "Torch X", "Acme", None, None, "s"),                # missing listing
         ("2", "Rope Y", "Bindworks", "Rope Y",                    # raw title echoed
          "Strong rope for climbing anchors.", "s"),
         ("3", "Tent Z", "Peak", "Tent Z 4-Season Shelter | Peak",  # written — strong
          "A 4-season tent from Peak.", "s"),
         ("4", LONG_TITLE, "Nord", None, None, "s")])              # long + missing
    c.executemany(
        "INSERT INTO canonical_products (shopify_id, handle, title, vendor,"
        " category, built_at) VALUES (?,?,?,?,?,'t')",
        [("1", "torch-x", "Torch X", "Acme", "torches"),
         ("2", "rope-y", "Rope Y", "Bindworks", "ropes")])
    c.executemany(
        "INSERT INTO spec_claims (product, field, value, unit, source,"
        " verified, verified_on, fit_critical) VALUES (?,?,?,?,?,?,?,?)",
        [("1", "beam_output", "900", "lm", "datasheet:acme", 1, "2026-07-01", 0),
         ("1", "temp_rating", "-20", "C", "parsed:supplier-spec-blob", 0, None, 1)])
    c.commit()
    yield c
    c.close()


def test_weak_listing_rule_and_reasons(conn):
    drafts = compute_listing_drafts(conn, limit=10)
    reasons = {d["product"]: d["weak_reason"] for d in drafts}
    assert set(reasons) == {"1", "2", "4"}          # the written listing (3) stands
    assert reasons["1"] == "no-seo-title"
    assert reasons["2"] == "seo-title-is-raw-title"  # a default is not a listing
    assert reasons["4"] == "no-seo-title"


def test_drafts_quote_only_verified_facts(conn):
    drafts = compute_listing_drafts(conn, limit=10)
    d1 = next(d for d in drafts if d["product"] == "1")
    assert "Beam output: 900 lm." in d1["description"]   # verified — quoted
    # the sentence break survives: a whole (untruncated) description keeps its
    # period, so the category sentence never runs into the claim
    assert ". Beam output: 900 lm." in d1["description"]
    assert "torches" in d1["description"] and "torchesBeam" not in d1["description"].replace(" ", "")
    for d in drafts:                                     # unverified — never appears
        text = " ".join(p for p in (d["title"], d["description"]) if p)
        assert "-20" not in text
    assert d1["claims"] and all(c["field"] == "beam_output" for c in d1["claims"])


def test_refusal_fires_on_a_draft_the_catalog_cannot_back(conn):
    unverified_id = conn.execute(
        "SELECT id FROM spec_claims WHERE field = 'temp_rating'").fetchone()["id"]
    base = {"product": "1", "product_id": "gid://shopify/Product/1",
            "title": "Torch X | Acme", "claims": []}
    with pytest.raises(DraftRefused, match="unverified"):     # states a raw value
        check_draft_against_catalog(conn, {
            **base, "description": "Torch X rated to -20 C."})
    with pytest.raises(DraftRefused, match="unverified"):     # cites an unverified claim
        check_draft_against_catalog(conn, {
            **base, "description": "Torch X from Acme.",
            "claims": [{"id": unverified_id, "field": "temp_rating", "value": "-20"}]})
    with pytest.raises(DraftRefused, match="drifted"):        # re-derived value
        verified_id = conn.execute(
            "SELECT id FROM spec_claims WHERE field = 'beam_output'").fetchone()["id"]
        check_draft_against_catalog(conn, {
            **base, "description": "Torch X. Beam output: 950 lm.",
            "claims": [{"id": verified_id, "field": "beam_output", "value": "950"}]})
    with pytest.raises(DraftRefused, match="hype"):           # invented superlative
        check_draft_against_catalog(conn, {
            **base, "description": "The best torch money can buy."})
    check_draft_against_catalog(conn, {                       # an honest draft passes
        **base, "description": "Torch X from Acme. Category: torches."})


def test_reversible_drafts_auto_execute_and_spec_quoting_drafts_park(conn):
    res = propose_and_run(conn, "listing_draft", limit=10, client=FakeClient())
    # product 1 quotes a verified claim -> parks; product 2 is a plain title
    # fix (its real description is kept) -> auto-executes; product 4 says
    # nothing past its raw name + vendor -> the widened wall refuses it (M5).
    assert res == {**res, "computed": 3, "executed": 1, "parked": 1,
                   "refused": 1, "failed": 0}
    recs = ledger.query(conn, function=FUNCTION)
    assert len(recs) == 2 and all(r["agent"] == AGENT for r in recs)
    parked = [r for r in recs if r["status"] == "pending"]
    executed = [r for r in recs if r["status"] == "executed"]
    assert len(parked) == 1 and len(executed) == 1
    # the spec-quoting draft (product 1, quotes the beam claim) is the parked one
    assert parked[0]["action_type"] == "consequential"
    assert "900 lm" in parked[0]["proposal"]["args"]["description"]
    for r in executed:                       # plain facts ride reversible, verified
        assert r["action_type"] == "reversible"
        assert r["outcome"]["ok"] and r["outcome"]["verified_rendered"]


def test_provenance_rides_every_proposal(conn):
    propose_and_run(conn, "listing_draft", limit=10, client=FakeClient())
    recs = ledger.query(conn, function=FUNCTION)
    assert recs and all(r["provenance"] for r in recs)
    for r in recs:                            # every draft cites the product fact
        assert any(p.get("fact") == "products" for p in r["provenance"])
    parked = next(r for r in recs if r["status"] == "pending")
    cited = [p for p in parked["provenance"] if p.get("fact") == "spec_claims"]
    assert cited and cited[0]["field"] == "beam_output"


def test_length_limits_hold(conn):
    drafts = compute_listing_drafts(conn, limit=10)
    for d in drafts:
        if d["title"] is not None:                       # a kept field is None
            assert len(d["title"]) <= TITLE_LIMIT
        if d["description"] is not None:
            assert len(d["description"]) <= DESCRIPTION_LIMIT
    d4 = next(d for d in drafts if d["product"] == "4")
    assert LONG_TITLE.startswith(d4["title"])            # words verbatim, never invented
    assert LONG_TITLE[len(d4["title"])] == " "           # the cut lands on a word boundary
    assert d4["title"].split()[-1].lower() not in {      # never ends on a dangling connective
        "and", "with", "for", "the", "or", "to", "of"}


def test_work_kinds_dispatch(conn):
    assert WORK_KINDS["listing_draft"] is compute_listing_drafts
    drafts = WORK_KINDS["listing_draft"](conn, limit=1)
    assert len(drafts) == 1
