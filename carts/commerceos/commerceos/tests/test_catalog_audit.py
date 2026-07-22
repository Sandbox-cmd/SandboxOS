"""D1's checks: the audit scores landed facts per configured dimension;
a signal the sync never landed is named not-scorable, never scored zero;
weights are config, not code; the report renders every dimension; and the
real re-baseline against the dev store's landed facts exists with sane bounds."""

import copy
import json
from pathlib import Path

import pytest

from commerceos.catalog import audit as A
from commerceos.catalog.status import report_status
from commerceos.db import connect
from commerceos.spine.schema import ensure_schema

REPO = Path(__file__).resolve().parents[1]
STORE_CONFIG = REPO / "stores" / "demostore" / "audit-config.json"

VALID_GTIN13 = "4006381333931"  # checksum-valid EAN-13

TAXONOMY = {
    "version": 0,
    "status": "test",
    "categories": {
        "_doc": "ignored meta key",
        "Lighting": {
            "subcategories": ["Flashlights", "Headlamps"],
            "spec_schema": [{"key": "max_lumens", "fc": False}, {"key": "beam_distance", "fc": False}],
        },
    },
}


def store_config(**weights) -> dict:
    """the shipped store config (proves it parses), optionally re-weighted."""
    cfg = json.loads(STORE_CONFIG.read_text())
    if weights:
        for d in cfg["dimensions"]:
            cfg["dimensions"][d]["weight"] = weights.get(d, 0.0)
    return cfg


def seed(conn, pid, ptype="Flashlights", tags=("Lighting",), barcode=None, sku="SKU-1", raw_extra=None):
    """land one product + variant the way the spine's sync shapes them."""
    raw = {
        "id": pid, "handle": f"h-{pid}", "title": f"P {pid}", "status": "ACTIVE",
        "vendor": "V", "productType": ptype, "tags": list(tags),
        "variants": {"pageInfo": {"hasNextPage": False},
                     "nodes": [{"id": f"v-{pid}", "sku": sku, "barcode": barcode,
                                "price": "10.00", "inventoryQuantity": 1}]},
    }
    if raw_extra:
        raw.update(raw_extra)
    conn.execute(
        "INSERT INTO products (shopify_id, handle, title, status, vendor, product_type,"
        " tags, raw, source, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (pid, f"h-{pid}", f"P {pid}", "ACTIVE", "V", ptype, json.dumps(list(tags)),
         json.dumps(raw), "test", "2026-07-11T00:00:00Z"))
    conn.execute(
        "INSERT INTO variants (shopify_id, product_id, sku, barcode, price_minor,"
        " inventory, source, fetched_at) VALUES (?,?,?,?,?,?,?,?)",
        (f"v-{pid}", pid, sku, barcode, 1000, 1, "test", "2026-07-11T00:00:00Z"))
    conn.commit()


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "t.db")
    ensure_schema(c)
    yield c
    c.close()


def test_gtin_checksum_knows_a_gtin_from_an_sku():
    assert A.gtin_valid(VALID_GTIN13)
    assert A.gtin_valid("96385074")            # GTIN-8
    assert not A.gtin_valid("4006381333932")   # checksum off by one
    assert not A.gtin_valid("LL501090")        # SKU-shaped
    assert not A.gtin_valid("'" + VALID_GTIN13)  # spreadsheet apostrophe, as stored


def test_a_gtin13_barcode_passes_identity(conn):
    seed(conn, "p1", barcode=VALID_GTIN13)
    state = A.audit(conn, TAXONOMY, store_config())
    ident = state["dimensions"]["identity_gtin"]
    assert ident["scorable"] and ident["passed"] == 1 and ident["rate"] == 100.0


def test_an_sku_shaped_barcode_fails_identity(conn):
    seed(conn, "p1", barcode="LL501090")
    seed(conn, "p2", barcode="'" + VALID_GTIN13)  # artifact-wrapped: fails as stored, counted as fixable
    state = A.audit(conn, TAXONOMY, store_config())
    ident = state["dimensions"]["identity_gtin"]
    assert ident["passed"] == 0
    ib = state["facts"]["identity_barcodes"]
    assert ib["sku_shaped"] == 1 and ib["apostrophe_wrapped_gtin"] == 1
    assert any("identity_gtin" in g["failing"] for g in state["worst_gaps"])


def test_image_present_and_absent_score(conn):
    # the media key present in raw = signal landed; one truthy, one null
    seed(conn, "p1", barcode=VALID_GTIN13, raw_extra={"featuredMedia": {"id": "m1"}})
    seed(conn, "p2", barcode=VALID_GTIN13, raw_extra={"featuredMedia": None})
    state = A.audit(conn, TAXONOMY, store_config())
    img = state["dimensions"]["images"]
    assert img["scorable"] and img["passed"] == 1 and img["rate"] == 50.0


def test_config_weights_change_the_overall_config_not_code(conn):
    seed(conn, "p1", barcode=VALID_GTIN13)     # passes everything scorable
    seed(conn, "p2", barcode="SKU-ONLY")       # fails identity only
    heavy = A.audit(conn, TAXONOMY, store_config(identity_gtin=0.9, classification=0.1))
    light = A.audit(conn, TAXONOMY, store_config(identity_gtin=0.1, classification=0.9))
    assert heavy["overall_score"] == 55.0      # 0.1*100 + 0.9*50
    assert light["overall_score"] == 95.0      # 0.9*100 + 0.1*50
    assert heavy["overall_score"] != light["overall_score"]


def test_a_signal_the_sync_never_landed_is_named_not_scored_zero(conn):
    seed(conn, "p1", barcode=VALID_GTIN13)     # sync-shaped raw: no metafields/seo/media keys
    state = A.audit(conn, TAXONOMY, store_config())
    for d in ("specs_structured", "provenance", "seo", "images"):
        dim = state["dimensions"][d]
        assert dim["scorable"] is False and dim["rate"] is None
        assert "not landed by the current sync" in dim["reason"]
    # and the overall excludes them instead of dragging them in as zeros:
    assert state["overall_score"] == 100.0
    assert state["scored_dimensions"] == 3


def test_a_wider_sync_makes_specs_provenance_and_seo_scorable(conn):
    good_prov = json.dumps({"source": "datasheet", "verified": True, "verified_on": "2026-07-01"})
    seed(conn, "p1", barcode=VALID_GTIN13, raw_extra={
        "seo": {"title": "T", "description": "D"},
        "metafields": {"nodes": [
            {"key": "max_lumens", "type": "number_integer", "value": "900"},
            {"key": "max_lumens_provenance", "type": "json", "value": good_prov},
        ]}})
    seed(conn, "p2", barcode=VALID_GTIN13, raw_extra={
        "seo": {"title": "T", "description": None},
        "metafields": {"nodes": [
            {"key": "weight_g", "type": "number_integer", "value": "80"},
            {"key": "weight_g_provenance", "type": "json",
             "value": json.dumps({"verified": True})},  # verified without a source: breach
        ]}})
    state = A.audit(conn, TAXONOMY, store_config())
    specs = state["dimensions"]["specs_structured"]
    assert specs["scorable"] and specs["passed"] == 2 and specs["rate"] == 100.0
    assert state["dimensions"]["provenance"]["passed"] == 1
    assert state["dimensions"]["seo"]["passed"] == 1
    assert state["facts"]["verified_without_source"] == 1


def test_report_renders_all_dimensions_and_the_prior_body_delta(conn, tmp_path):
    seed(conn, "p1", barcode=VALID_GTIN13)
    seed(conn, "p2", ptype="", tags=(), barcode=None, sku="")  # fails everything scorable
    state = A.audit(conn, TAXONOMY, store_config())
    md_path, json_path = A.write_reports(state, tmp_path / "reports")
    md = md_path.read_text()
    for d in ("classification", "specs_structured", "provenance", "identity_gtin",
              "merchandising", "seo", "images"):
        assert d in md
    assert "not landed by the current sync" in md
    assert "delta vs the prior body" in md and "66.0" in md
    assert "worst gaps" in md and "h-p2" in md
    reloaded = json.loads(json_path.read_text())
    assert 0 <= reloaded["overall_score"] <= 100
    assert reloaded["prior_body"]["overall_prior"] == 66.0


def test_status_reports_its_row_via_the_registry(conn, tmp_path):
    report_status(conn, reports_dir=tmp_path)  # no report yet -> starting
    row = conn.execute("SELECT * FROM parts WHERE part='catalog-loop'").fetchone()
    assert row["state"] == "starting"
    seed(conn, "p1", barcode=VALID_GTIN13)
    state = A.audit(conn, TAXONOMY, store_config())
    A.write_reports(state, tmp_path)
    report_status(conn, reports_dir=tmp_path)
    row = conn.execute("SELECT * FROM parts WHERE part='catalog-loop'").fetchone()
    assert row["state"] == "idle"
    last = json.loads(row["last_run"])
    assert "health" in last["summary"] and last["ok"] is True
    assert "not scorable yet" in last["summary"]


REAL_DB = REPO / "data" / "demostore.db"


@pytest.mark.skipif(not REAL_DB.exists(), reason="dev-store facts not landed on this machine")
def test_the_real_rebaseline_ran_and_is_sane():
    latest = REPO / "reports" / "health-latest.json"
    assert latest.exists(), "run: uv run python -m commerceos.catalog.audit"
    s = json.loads(latest.read_text())
    assert s["total"] > 0
    assert 0 <= s["overall_score"] <= 100
    for d, v in s["dimensions"].items():
        if v["scorable"]:
            assert 0 <= v["rate"] <= 100, d
        else:
            assert "not landed by the current sync" in v["reason"], d
    assert (REPO / "reports" / f"health-{s['date']}.md").exists()
