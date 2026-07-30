"""CW8: the delist feature — the quality flags gated, and the approval ->
execute -> lifecycle return leg wired end to end.

the invariant under test: lifecycle state changes ONLY on a verified store
execution, never at staging, and catalog-lifecycle stays the SOLE writer of
the state field + history. so:

  - the queue finds exactly the flagged products (noise + decor), one item
    per product;
  - a delist proposal PARKS (consequential) and flips no state at staging;
  - after the owner approves, execute_and_record flips the store to DRAFT,
    verify-renders, and lifecycle then reads `delisted` with one history row
    carrying the record's ledger id;
  - an unverified execution (store readback disagrees) records NO lifecycle
    move (verify rendered, never files-exist);
  - relist (state="active") moves lifecycle delisted -> active.
"""

import json

import pytest

from commerceos.catalog import delist, lifecycle as L
from commerceos.catalog.workflows import DELIST, run_feature
from commerceos.db import connect
from commerceos.gate import gate, ledger
from commerceos.spine import writes
from commerceos.spine.schema import ensure_schema


class FakeClient:
    """scripted GraphQL: productUpdate(status) + a status readback.

    readback_status forces the read-back to disagree with the write, so a
    store that claims a change it did not render is caught honestly.
    """

    def __init__(self, status="ACTIVE", readback_status=None):
        self.status = status
        self._forced_readback = readback_status
        self.calls = []

    def graphql(self, query, variables=None):
        self.calls.append(query.split("(")[0].strip())
        if "productUpdate" in query:
            self.status = variables["input"]["status"]
            return {"productUpdate": {
                "product": {"id": variables["input"]["id"], "status": self.status},
                "userErrors": []}}
        if "query productStatus" in query:
            return {"product": {"id": "gid://x/1",
                                "status": self._forced_readback or self.status}}
        raise AssertionError(f"unexpected query: {query[:60]}")


def _add_product(c, pid, handle, title, vendor, ptype, tags=(), colls=(),
                 price=4995, sku="SKU1"):
    c.execute(
        "INSERT INTO products (shopify_id, handle, title, status, vendor, product_type,"
        " tags, collections, source, fetched_at) VALUES (?,?,?,?,?,?,?,?,'s','t')",
        (pid, handle, title, "ACTIVE", vendor, ptype,
         json.dumps(list(tags)), json.dumps(list(colls))))
    c.execute(
        "INSERT INTO variants (shopify_id, product_id, sku, price_minor, source, fetched_at)"
        " VALUES (?,?,?,?,'s','t')", (f"v-{pid}", pid, sku, price))


GID = "gid://shopify/Product/{}".format


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "delist.db")
    ensure_schema(c)          # facts + lifecycle tables
    ledger.ensure_schema(c)   # ledger + handles + events
    yield c
    c.close()


@pytest.fixture()
def seeded(conn):
    # one noise, one decor, one clean-normal — the queue must find exactly two.
    _add_product(conn, GID(1), "storm-shelter-tent", "Storm Shelter Tent", "Vango",
                 "Tents", ["Tents & Shelters"], ["Tents & Shelters"])            # normal
    _add_product(conn, GID(2), "gift-card", "Gift Card", "Snowboard Vendor",
                 "giftcard", [], [], sku=None)                                    # noise
    _add_product(conn, GID(3), "bar-grill-wall-sign", "Bar & Grill Wall Sign",
                 "La Hacienda", "Camp & Household — Other",
                 ["Decor", "Wall Signs"], ["Camp & Household"])                   # decor
    return conn


def _submit_delist(conn, product_id, state="delisted"):
    return gate.submit(conn, {
        "agent": "catalog-delist", "function": "catalog-enrichment",
        "method": "mutate_product_state",
        "args": {"product_id": product_id, "state": state},
        "declared_type": "consequential",
        "intent": f"{state} the product", "rationale": "quality flag ruled — pull it",
        "provenance": [{"source": "quality.py"}],
    })


# ---------- the queue ----------------------------------------------------

def test_delist_queue_finds_exactly_the_flagged_products(seeded):
    work = delist.delist_queue(seeded)
    # exactly the noise + decor products, one item each — not the clean tent.
    assert sorted(w["product_id"] for w in work) == [GID(2), GID(3)]
    assert sorted(w["handle"] for w in work) == ["bar-grill-wall-sign", "gift-card"]
    # each item carries the exact call the executor runs.
    for w in work:
        assert w["args"]["state"] == "delisted"
        assert w["args"]["product_id"] == w["product_id"]
        assert w["evidence"]  # its flag evidence rides along


# ---------- staging parks, flips nothing ---------------------------------

def test_delist_feature_parks_and_changes_no_state_at_staging(seeded):
    # place both flagged products as sync would (ACTIVE -> active).
    for pid in (GID(2), GID(3)):
        L.set_initial(seeded, pid, "ACTIVE")

    rep = run_feature(seeded, DELIST)     # apply=False by default: stage only

    assert rep["batch"] == 2
    assert rep["parked"] == 2
    assert rep["executed"] == 0 and rep["counted"] == 0
    # every proposal parked consequential, awaiting the owner.
    queue = ledger.pending_queue(seeded)
    assert len(queue) == 2
    for rec in queue:
        assert rec["status"] == "pending"
        assert rec["action_type"] == "consequential"
        assert rec["proposal"]["method"] == "mutate_product_state"
        assert rec["proposal"]["args"]["state"] == "delisted"
    # NOTHING executed: no handle minted, so nothing is executable yet.
    assert seeded.execute("SELECT COUNT(*) FROM handles").fetchone()[0] == 0
    # lifecycle is untouched at staging — still active, only the sync row.
    for pid in (GID(2), GID(3)):
        assert L.state_of(seeded, pid) == "active"
        assert len(L.history(seeded, pid)) == 1


# ---------- approval -> execute -> lifecycle (the seam) ------------------

def test_approved_delist_executes_verifies_and_records_the_transition(conn):
    pid = "gid://x/1"
    L.set_initial(conn, pid, "ACTIVE")
    assert L.state_of(conn, pid) == "active"          # before approval

    res = _submit_delist(conn, pid)
    assert res["decision"] == "parked"
    rid = res["record_id"]

    # still nothing recorded while it sits parked.
    assert L.state_of(conn, pid) == "active"
    assert len(L.history(conn, pid)) == 1

    # the owner's only approve path mints the one-use handle.
    gate.resolve(conn, rid, "approved", by="owner", reason="pull it")

    out = delist.execute_and_record(conn, rid, client=FakeClient(status="ACTIVE"))

    # the store flipped to DRAFT and the read-back confirms it.
    assert out["outcome"]["verified_rendered"] is True
    assert out["outcome"]["status"] == "DRAFT"
    assert out["recorded"] is True

    # lifecycle now reads delisted, with exactly one history row carrying the
    # record's ledger id (the seam that ties state to the verified store write).
    assert L.state_of(conn, pid) == "delisted"
    rows = L.history(conn, pid)
    assert len(rows) == 2                             # sync + delist
    tail = rows[-1]
    assert tail["from_state"] == "active" and tail["to_state"] == "delisted"
    assert tail["ledger_id"] == rid
    carrying = [r for r in rows if r["ledger_id"] == rid]
    assert len(carrying) == 1

    # the executor's receipt landed on the ledger record.
    assert ledger.get(conn, rid)["status"] == "executed"


def test_unverified_execution_records_no_lifecycle_move(conn):
    pid = "gid://x/1"
    L.set_initial(conn, pid, "ACTIVE")
    res = _submit_delist(conn, pid)
    gate.resolve(conn, res["record_id"], "approved", by="owner", reason="pull it")

    # the write claims DRAFT but the live surface still reads ACTIVE — a store
    # that did not render the change. verify rendered, never files-exist.
    fake = FakeClient(status="ACTIVE", readback_status="ACTIVE")
    out = delist.execute_and_record(conn, res["record_id"], client=fake)

    assert out["outcome"]["verified_rendered"] is False
    assert out["recorded"] is False and out["transition"] is None
    # lifecycle is UNCHANGED — still active, only the sync row, no ledger id.
    assert L.state_of(conn, pid) == "active"
    assert len(L.history(conn, pid)) == 1


def test_relist_path_moves_delisted_back_to_active(conn):
    pid = "gid://x/1"
    L.set_initial(conn, pid, "ACTIVE")

    # leg 1: delist through the seam (active -> delisted, store ACTIVE -> DRAFT).
    r1 = _submit_delist(conn, pid, state="delisted")
    gate.resolve(conn, r1["record_id"], "approved", by="owner", reason="pull it")
    delist.execute_and_record(conn, r1["record_id"], client=FakeClient(status="ACTIVE"))
    assert L.state_of(conn, pid) == "delisted"

    # leg 2: relist is just state="active" — the executor is state-agnostic and
    # the seam records delisted -> active on the verified read-back.
    r2 = _submit_delist(conn, pid, state="active")
    gate.resolve(conn, r2["record_id"], "approved", by="owner", reason="fixed, back live")
    out = delist.execute_and_record(conn, r2["record_id"], client=FakeClient(status="DRAFT"))

    assert out["outcome"]["status"] == "ACTIVE"
    assert out["recorded"] is True
    assert L.state_of(conn, pid) == "active"
    rows = L.history(conn, pid)
    # sync + delist + relist; the relist row carries leg 2's ledger id.
    assert [r["to_state"] for r in rows] == ["active", "delisted", "active"]
    assert rows[-1]["ledger_id"] == r2["record_id"]
