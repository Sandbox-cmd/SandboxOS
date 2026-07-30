"""CW1's checks: the catalog workflow engine + the GTIN feature (the template).

the engine stages reversible proposals for the fixable-barcode queue, executes
them against a fake store, and counts a fix ONLY when the store reads back a
checksum-valid GTIN — a bad-checksum value or an unrendered write never counts.
the queue finds exactly the artifacts the audit flags, nothing more.
"""

import pytest

from commerceos.catalog import workflows as W
from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.spine.schema import ensure_schema

VALID13 = "4006381333931"   # checksum-valid EAN-13
VALID12 = "036000291452"    # checksum-valid UPC-A (textbook example)


def seed_variant(conn, pid, barcode):
    """land one product + variant the way the spine's sync shapes them."""
    conn.execute(
        "INSERT INTO products (shopify_id, handle, title, status, vendor, product_type,"
        " tags, raw, source, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (pid, f"h-{pid}", f"P {pid}", "ACTIVE", "V", "Flashlights", "[]", "{}",
         "test", "2026-07-12T00:00:00Z"))
    conn.execute(
        "INSERT INTO variants (shopify_id, product_id, sku, barcode, price_minor,"
        " inventory, source, fetched_at) VALUES (?,?,?,?,?,?,?,?)",
        (f"v-{pid}", pid, "SKU-1", barcode, 1000, 1, "test", "2026-07-12T00:00:00Z"))
    conn.commit()


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "wf.db")
    ensure_schema(c)          # products + variants (the spine)
    ledger.ensure_schema(c)   # the gate ledger + handles
    yield c
    c.close()


class FakeStore:
    """scripted barcode writes: stores what productVariantsBulkUpdate sets and
    echoes it on readback — EXCEPT variant ids in `reject`, which read back
    unchanged (a store that did not apply the write), so the fix never counts."""

    def __init__(self, reject=()):
        self.set = {}
        self.reject = set(reject)

    def graphql(self, query, variables=None):
        if "productVariantsBulkUpdate" in query:
            v = variables["variants"][0]
            if v["id"] not in self.reject:
                self.set[v["id"]] = v["barcode"]
            return {"productVariantsBulkUpdate": {
                "productVariants": [{"id": v["id"], "barcode": self.set.get(v["id"])}],
                "userErrors": []}}
        if "query variant" in query:
            vid = variables["id"]
            return {"node": {"id": vid, "barcode": self.set.get(vid)}}
        raise AssertionError(f"unexpected query: {query[:60]}")


# --- the normalization logic --------------------------------------------

def test_normalize_strips_apostrophe_and_restores_leading_zero():
    assert W.normalize_barcode("'" + VALID13) == VALID13
    assert W.normalize_barcode(VALID12[1:]) == VALID12   # 11-digit UPC missing its zero
    assert W.normalize_barcode(VALID13) is None          # already valid — nothing to fix
    assert W.normalize_barcode("LL501090") is None       # an SKU, not a GTIN
    assert W.normalize_barcode("") is None


def test_verify_rejects_a_bad_checksum_and_an_unrendered_write():
    item = {"new": VALID13}
    assert W._gtin_verify({"ok": True, "barcode": VALID13}, item) is True
    # the store rendered a different value -> not counted
    assert W._gtin_verify({"ok": True, "barcode": "4006381333999"}, item) is False
    # a "new" value that is not a valid GTIN never counts, even if echoed back
    bad = {"new": "4006381333932"}   # checksum off by one
    assert W._gtin_verify({"ok": True, "barcode": "4006381333932"}, bad) is False


# --- the queue ----------------------------------------------------------

def test_queue_finds_exactly_the_fixable_artifacts(conn):
    seed_variant(conn, "p1", "'" + VALID13)   # apostrophe artifact -> fixable
    seed_variant(conn, "p2", VALID12[1:])     # missing leading zero -> fixable
    seed_variant(conn, "p3", VALID13)         # already valid -> not queued
    seed_variant(conn, "p4", "LL501090")      # sku-shaped -> not queued
    seed_variant(conn, "p5", "")              # empty -> not queued
    q = W._gtin_queue(conn)
    assert {w["product_id"] for w in q} == {"p1", "p2"}
    assert {w["product_id"]: w["new"] for w in q} == {"p1": VALID13, "p2": VALID12}


# --- the engine: stage (dry run, no store) ------------------------------

def test_run_stages_reversible_proposals_without_touching_the_store(conn):
    seed_variant(conn, "p1", "'" + VALID13)
    seed_variant(conn, "p2", VALID12[1:])
    rep = W.run_feature(conn, W.GTIN, client=None, apply=False)
    assert rep["queue_depth"] == 2
    assert rep["staged"] == 2 and rep["parked"] == 0 and rep["executed"] == 0
    # reversible features auto-approve at the gate — nothing parks
    assert all(e["decision"] == "allow" for e in rep["log"])


# --- the engine: execute + verify-render --------------------------------

def test_run_executes_and_counts_only_verified_fixes(conn):
    seed_variant(conn, "p1", "'" + VALID13)   # the store will render it -> counts
    seed_variant(conn, "p2", VALID12[1:])     # the store will REJECT it -> not counted
    store = FakeStore(reject={"v-p2"})
    rep = W.run_feature(conn, W.GTIN, client=store, apply=True)
    assert rep["executed"] == 2
    assert rep["counted"] == 1 and rep["failed"] == 1
    counted = [e for e in rep["log"] if e["state"] == "counted"]
    assert len(counted) == 1 and counted[0]["rendered"]["barcode"] == VALID13


def test_progress_reads_the_valid_gtin_rate_live(conn):
    seed_variant(conn, "p1", VALID13)         # already valid
    seed_variant(conn, "p2", "'" + VALID13)   # fixable, still an artifact
    prog = W.GTIN.progress(conn)
    assert prog["valid"] == 1 and prog["fixable_remaining"] == 1 and prog["total"] == 2


# --- CW1b: facts write-through, so progress + feed read truth -----------

def test_a_verified_write_is_written_back_to_facts_and_progress_moves(conn):
    seed_variant(conn, "p1", "'" + VALID13)   # a fixable artifact
    before = W.GTIN.progress(conn)
    assert before["valid"] == 0 and before["fixable_remaining"] == 1
    W.run_feature(conn, W.GTIN, client=FakeStore(), apply=True)
    # the store-verified value is now in the local facts — no separate sync step
    row = conn.execute("SELECT barcode FROM variants WHERE product_id='p1'").fetchone()
    assert row[0] == VALID13
    after = W.GTIN.progress(conn)
    assert after["valid"] == 1 and after["fixable_remaining"] == 0


def test_an_unverified_write_leaves_the_facts_untouched(conn):
    seed_variant(conn, "p2", VALID12[1:])     # the store will reject this one
    W.run_feature(conn, W.GTIN, client=FakeStore(reject={"v-p2"}), apply=True)
    row = conn.execute("SELECT barcode FROM variants WHERE product_id='p2'").fetchone()
    assert row[0] == VALID12[1:]              # unchanged — no verified write, no write-back


def test_one_failing_item_is_isolated_and_the_batch_continues(conn):
    seed_variant(conn, "p1", "'" + VALID13)   # succeeds
    seed_variant(conn, "p2", VALID12[1:])     # its store call raises (a throttle)

    class Flaky(FakeStore):
        def graphql(self, query, variables=None):
            if variables and variables.get("variants") \
               and variables["variants"][0]["id"] == "v-p2":
                raise RuntimeError("THROTTLED")
            return super().graphql(query, variables)

    rep = W.run_feature(conn, W.GTIN, client=Flaky(), apply=True)
    assert rep["errored"] == 1 and rep["counted"] == 1        # the batch did not crash
    # the good one wrote back; the errored one left the facts untouched (resumable)
    assert conn.execute("SELECT barcode FROM variants WHERE product_id='p1'").fetchone()[0] == VALID13
    assert conn.execute("SELECT barcode FROM variants WHERE product_id='p2'").fetchone()[0] == VALID12[1:]
