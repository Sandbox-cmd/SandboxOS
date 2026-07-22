"""the first delegated work: checksum math, artifact repair, and the
proposer running its batch through the gate with receipts."""

import pytest

from commerceos.db import connect
from commerceos.fleet.proposer import (compute_gtin_proposals, gtin_checksum_ok,
                                       normalize_barcode, propose_and_run)
from commerceos.gate import ledger
from commerceos.spine.schema import ensure_schema


def test_gtin_checksum_truth():
    assert gtin_checksum_ok("036000291452")        # UPC-A canonical example
    assert gtin_checksum_ok("4006381333931")       # EAN-13 canonical example
    assert not gtin_checksum_ok("4006381333932")   # off-by-one check digit
    assert not gtin_checksum_ok("12345")           # wrong length
    assert not gtin_checksum_ok("ABC6381333931")   # non-digit


def test_normalize_repairs_exactly_the_two_artifacts():
    assert normalize_barcode("'4006381333931") == "4006381333931"   # apostrophe
    assert normalize_barcode("36000291452") == "036000291452"        # dropped zero
    assert normalize_barcode("4006381333931") == "4006381333931"     # already clean
    assert normalize_barcode("'832426") is None                      # SKU, not a GTIN
    assert normalize_barcode("") is None and normalize_barcode(None) is None


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "prop.db")
    ensure_schema(c)
    ledger.ensure_schema(c)
    c.execute("INSERT INTO products (shopify_id, title, source, fetched_at)"
              " VALUES ('1','P','s','t')")
    c.executemany(
        "INSERT INTO variants (shopify_id, product_id, barcode, source, fetched_at)"
        " VALUES (?, '1', ?, 's', 't')",
        [("v1", "'4006381333931"),   # repairable
         ("v2", "'832426"),          # SKU — untouchable
         ("v3", "036000291452")])    # already clean — no proposal
    c.commit()
    yield c
    c.close()


class FakeClient:
    def __init__(self):
        self.barcodes = {}

    def graphql(self, query, variables=None):
        if "productVariantsBulkUpdate" in query:
            v = variables["variants"][0]
            self.barcodes[v["id"]] = v["barcode"]
            return {"productVariantsBulkUpdate": {
                "productVariants": [{"id": v["id"], "barcode": v["barcode"]}],
                "userErrors": []}}
        if "query variant" in query:
            vid = variables["id"]
            return {"node": {"id": vid, "barcode": self.barcodes.get(vid)}}
        raise AssertionError(query[:60])


def test_proposer_computes_only_valid_repairs(conn):
    props = compute_gtin_proposals(conn)
    assert len(props) == 1
    assert props[0]["value"] == "4006381333931" and props[0]["was"] == "'4006381333931"


def test_the_first_delegated_run_lands_receipts_on_the_record(conn):
    res = propose_and_run(conn, "gtin_normalize", limit=10, client=FakeClient())
    assert res == {**res, "computed": 1, "executed": 1, "failed": 0, "parked": 0}
    recs = ledger.query(conn, function="catalog-enrichment")
    assert len(recs) == 1 and recs[0]["status"] == "executed"
    assert recs[0]["agent"] == "catalog-proposer"
    assert "normalize barcode" in recs[0]["intent"]


def test_bounded_limit_respected(conn):
    conn.executemany(
        "INSERT INTO variants (shopify_id, product_id, barcode, source, fetched_at)"
        " VALUES (?, '1', ?, 's', 't')",
        [(f"vx{i}", "'4006381333931") for i in range(5)])
    conn.commit()
    props = compute_gtin_proposals(conn, limit=3)
    assert len(props) == 3
