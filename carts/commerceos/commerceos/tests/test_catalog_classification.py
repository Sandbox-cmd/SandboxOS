"""CW3's checks: classification / taxonomy cleanup — the SECOND catalog feature,
pure config over the one workflow engine (the engine's run_feature is UNCHANGED).

the queue finds exactly the products that are unresolved or in a fold bucket AND
resolvable to a locked category; a product_type that maps to nothing is left OUT
of the queue — silence over guesses. a classification counts only when the store
renders the commerceos.category metafield back == the target leaf, and a verified
count writes back to product_meta so progress moves without a re-sync.
"""

import pytest

from commerceos.catalog import audit as AI
from commerceos.catalog import classification as C
from commerceos.catalog import workflows as W
from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.spine.schema import ensure_schema


def seed_product(conn, pid, product_type, category_meta=None):
    """land one product the way the spine's sync shapes it; optionally seed a
    persisted commerceos.category metafield fact (product_meta)."""
    conn.execute(
        "INSERT INTO products (shopify_id, handle, title, status, vendor,"
        " product_type, tags, raw, source, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (pid, f"h-{pid}", f"P {pid}", "ACTIVE", "V", product_type, "[]", "{}",
         "test", "2026-07-12T00:00:00Z"))
    if category_meta is not None:
        conn.execute(
            "INSERT INTO product_meta (product_id, namespace, key, type, value,"
            " source, fetched_at) VALUES (?,?,?,?,?,?,?)",
            (pid, "commerceos", "category", "single_line_text_field",
             category_meta, "test", "2026-07-12T00:00:00Z"))
    conn.commit()


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "cls.db")
    ensure_schema(c)          # products + variants + product_meta (the spine)
    ledger.ensure_schema(c)   # the gate ledger + handles
    yield c
    c.close()


class FakeStore:
    """scripted metafield writes: metafieldsSet stores what it set and echoes it
    back in the SAME response (the classification readback is the mutation reply,
    writes.py::_mutate_product_field) — EXCEPT product ids in `reject`, which echo
    a mismatching value (a store that did not apply the write), so verify-render
    never counts them."""

    def __init__(self, reject=()):
        self.set = {}
        self.reject = set(reject)

    def graphql(self, query, variables=None):
        if "metafieldsSet" in query:
            m = variables["metafields"][0]
            owner = m["ownerId"]
            if owner in self.reject:
                # store did not render our value -> echo a different one
                return {"metafieldsSet": {"metafields": [
                    {"id": f"gid://mf/{owner}", "namespace": m["namespace"],
                     "key": m["key"], "value": "__NOT_APPLIED__"}], "userErrors": []}}
            self.set[(owner, m["namespace"], m["key"])] = m["value"]
            return {"metafieldsSet": {"metafields": [
                {"id": f"gid://mf/{owner}", "namespace": m["namespace"],
                 "key": m["key"], "value": m["value"]}], "userErrors": []}}
        raise AssertionError(f"unexpected query: {query[:60]}")


# --- the resolver -------------------------------------------------------

def test_resolve_leaf_picks_right_leaf_and_stays_silent_on_unresolvable():
    # a clear subcategory resolves to its locked category (non-fold)
    assert C.resolve_leaf("Flashlights") == ("Lighting", False)
    # a fold bucket's own category IS its target (still flagged fold)
    assert C.resolve_leaf("Lighting — Other") == ("Lighting", True)
    # an unresolved product_type given as a full taxonomy PATH normalizes to its
    # leaf and resolves — one tidy, not a guess
    assert C.resolve_leaf("Sporting Goods > Camping > Tents") == ("Tents & Shelters", False)
    # genuinely unresolvable -> None (the caller leaves it OUT of the queue)
    assert C.resolve_leaf("Zzz Nonsense Widget")[0] is None
    assert C.resolve_leaf("")[0] is None
    # a fold bucket whose category is not locked is also unresolvable
    assert C.resolve_leaf("Xyz — Other")[0] is None


# --- the queue ----------------------------------------------------------

def test_queue_finds_exactly_unresolved_and_fold_not_the_classified(conn):
    seed_product(conn, "p1", "Lighting — Other")                 # fold -> queued (Lighting)
    seed_product(conn, "p2", "Sporting Goods > Camping > Tents") # unresolved path -> queued (Tents & Shelters)
    seed_product(conn, "p3", "Flashlights")                      # resolved non-fold -> NOT queued
    seed_product(conn, "p4", "Zzz Nonsense Widget")             # unresolvable -> NOT queued (silence)
    seed_product(conn, "p5", "")                                 # empty -> unresolvable -> NOT queued
    seed_product(conn, "p6", "Zzz Widget", category_meta="Lighting")  # persisted -> resolved -> NOT queued
    q = C.classification_queue(conn)
    assert {w["product_id"] for w in q} == {"p1", "p2"}
    assert {w["product_id"]: w["leaf"] for w in q} == {"p1": "Lighting", "p2": "Tents & Shelters"}
    # the item shape the engine consumes
    p1 = next(w for w in q if w["product_id"] == "p1")
    assert p1["args"] == {"field": "commerceos.category", "product_id": "p1", "value": "Lighting"}


# --- the engine: execute + verify-render (run_feature UNCHANGED) ---------

def test_run_counts_only_verified_and_writes_back(conn):
    seed_product(conn, "p1", "Lighting — Other")                 # store renders -> counts
    seed_product(conn, "p2", "Sporting Goods > Camping > Tents") # store REJECTS -> not counted
    store = FakeStore(reject={"p2"})
    rep = W.run_feature(conn, W.CLASSIFICATION, client=store, apply=True)
    assert rep["executed"] == 2
    assert rep["counted"] == 1 and rep["failed"] == 1
    counted = [e for e in rep["log"] if e["state"] == "counted"]
    assert len(counted) == 1 and counted[0]["rendered"]["metafield"]["value"] == "Lighting"
    # reversible metafield writes auto-approve at the gate — nothing parks
    assert rep["parked"] == 0
    # the verified value is now a fact in product_meta (no separate sync step)
    row = conn.execute(
        "SELECT value FROM product_meta WHERE product_id='p1'"
        " AND namespace='commerceos' AND key='category'").fetchone()
    assert row[0] == "Lighting"
    # the rejected one left the facts untouched
    assert conn.execute(
        "SELECT COUNT(*) FROM product_meta WHERE product_id='p2'").fetchone()[0] == 0


def test_progress_moves_after_a_verified_classification(conn):
    seed_product(conn, "p1", "Lighting — Other")   # a fold bucket — not yet resolved
    seed_product(conn, "p3", "Flashlights")        # already resolved
    before = C.classification_progress(conn)
    assert before["resolved"] == 1 and before["total"] == 2 and before["queue_remaining"] == 1
    W.run_feature(conn, W.CLASSIFICATION, client=FakeStore(), apply=True)
    after = C.classification_progress(conn)
    assert after["resolved"] == 2 and after["queue_remaining"] == 0
    assert after["rate"] > before["rate"]


def test_a_store_rejection_is_not_counted_and_leaves_facts_untouched(conn):
    seed_product(conn, "p2", "Sporting Goods > Camping > Tents")
    rep = W.run_feature(conn, W.CLASSIFICATION, client=FakeStore(reject={"p2"}), apply=True)
    assert rep["counted"] == 0 and rep["failed"] == 1
    # readback mismatch -> verify fails -> no write-back -> product_meta stays empty
    assert conn.execute(
        "SELECT COUNT(*) FROM product_meta WHERE product_id='p2'").fetchone()[0] == 0
    # and the queue still holds it (resumable) — nothing was silently marked done
    assert {w["product_id"] for w in C.classification_queue(conn)} == {"p2"}


def test_dry_run_stages_reversible_proposals_without_touching_the_store(conn):
    seed_product(conn, "p1", "Lighting — Other")
    rep = W.run_feature(conn, W.CLASSIFICATION, client=None, apply=False)
    assert rep["queue_depth"] == 1 and rep["staged"] == 1
    assert rep["executed"] == 0 and rep["parked"] == 0
    assert all(e["decision"] == "allow" for e in rep["log"])


# --- the synonym/keyword fallback (CW3b) ---------------------------------
#
# a curated synonym map ("torch" -> "Flashlights") lets a real-world
# product_type resolve to its locked category instead of staying silently
# unresolvable. order is law: the exact leaf-map resolution always wins; a
# synonym only fires when exact resolution AND the one normalization retry
# both find nothing. the map is DATA (classification.synonyms in
# taxonomy.json), indexed through the one door every consumer (audit,
# canonical, the feature) already shares — audit.resolve_category — so no
# two surfaces can ever disagree about a product's category.


def _tax_with_synonym(extra_synonyms=None):
    """a small tax dict, never the global cache — built through the real
    indexing door (_index_taxonomy) so validation runs exactly as it will in
    production."""
    synonyms = {"torch": "Flashlights"}
    if extra_synonyms:
        synonyms.update(extra_synonyms)
    return AI._index_taxonomy({
        "categories": {"Lighting": {"subcategories": ["Flashlights"]}},
        "classification": {"synonyms": synonyms},
    })


def test_a_synonym_resolves_through_its_target_leaf():
    tax = _tax_with_synonym()
    assert C.resolve_leaf("Torch", tax) == ("Lighting", False)
    assert C.resolve_leaf("TORCH", tax) == ("Lighting", False)
    assert C.resolve_leaf("torch", tax) == ("Lighting", False)


def test_a_seeded_torch_enters_the_queue_and_nonsense_stays_out(conn):
    tax = _tax_with_synonym()
    seed_product(conn, "p1", "Torch")               # synonym hop -> Lighting, queued
    seed_product(conn, "p2", "Zzz Nonsense Widget")  # genuine nonsense -> stays un-queued
    q = C.classification_queue(conn, tax)
    ids = {w["product_id"] for w in q}
    assert "p1" in ids
    assert "p2" not in ids
    p1 = next(w for w in q if w["product_id"] == "p1")
    assert p1["leaf"] == "Lighting"
    assert p1["args"] == {"field": "commerceos.category", "product_id": "p1", "value": "Lighting"}


def test_exact_resolution_always_beats_a_synonym():
    tax = _tax_with_synonym()
    tax_no_syn = AI._index_taxonomy({"categories": {"Lighting": {"subcategories": ["Flashlights"]}}})
    # a real leaf resolves identically whether or not a synonym map is present
    assert C.resolve_leaf("Flashlights", tax) == C.resolve_leaf("Flashlights", tax_no_syn) == ("Lighting", False)
    # a synonym shadowing a real leaf name is refused loudly at index time
    with pytest.raises(ValueError):
        AI._index_taxonomy({
            "categories": {"Lighting": {"subcategories": ["Flashlights"]}},
            "classification": {"synonyms": {"flashlights": "Lighting"}},
        })


def test_a_synonym_with_an_unknown_target_refuses_loudly():
    with pytest.raises(ValueError, match="torch"):
        AI._index_taxonomy({
            "categories": {"Lighting": {"subcategories": ["Flashlights"]}},
            "classification": {"synonyms": {"torch": "Nonexistent Leaf"}},
        })


def test_synonym_resolved_stays_queued_until_persisted(conn):
    tax = _tax_with_synonym()
    seed_product(conn, "p1", "Torch")                                 # no persisted fact -> queued
    seed_product(conn, "p2", "Torch", category_meta="Lighting")       # persisted -> resolved, not queued
    ids = {w["product_id"] for w in C.classification_queue(conn, tax)}
    assert "p1" in ids
    assert "p2" not in ids


def test_audit_and_feature_agree_on_a_synonym_type():
    tax = _tax_with_synonym()
    assert AI.resolve_category("Torch", tax) == ("Lighting", False)
    assert AI.resolve_category("Torch", tax) == C.resolve_leaf("Torch", tax)


def test_the_normalized_retry_also_hits_synonyms():
    tax = _tax_with_synonym()
    assert C.resolve_leaf("Something > Torch", tax) == ("Lighting", False)


def test_fold_buckets_never_resolve_via_synonyms():
    # even a fold bucket whose folded name IS a synonym key must never resolve
    # through it — the fold branch returns before any synonym lookup
    tax = _tax_with_synonym(extra_synonyms={"xyz": "Flashlights"})
    assert C.resolve_leaf("Xyz — Other", tax)[0] is None
    # the live-file pin (:87 in this file) stays green untouched
    assert C.resolve_leaf("Xyz — Other")[0] is None


def test_synonym_run_round_trip_persists_through_the_gated_batch(conn, monkeypatch):
    # the engine (run_feature) never passes tax explicitly — it calls
    # feature.queue(conn) — so the module-global cache is the seam here;
    # monkeypatch reverts it automatically, no cross-test poisoning.
    tax = _tax_with_synonym()
    monkeypatch.setattr(C, "_TAX", tax)
    seed_product(conn, "p1", "Torch")
    rep = W.run_feature(conn, W.CLASSIFICATION, client=FakeStore(), apply=True)
    assert rep["executed"] == 1 and rep["counted"] == 1
    row = conn.execute(
        "SELECT value FROM product_meta WHERE product_id='p1'"
        " AND namespace='commerceos' AND key='category'").fetchone()
    assert row[0] == "Lighting"
    assert C.classification_queue(conn) == []
