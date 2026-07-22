"""C2's checks: the canonical record builds from landed facts with honest
provenance (a `<field>_provenance` companion verifies only when it says
verified:true AND names a source; no companion, no verification); the three
emitters read only the canonical record and carry identical values; an
unverified claim renders "not yet verified" on the page and never reaches
the machine surfaces; fit-critical marks render; the write guard denies
this part every table but its own; and the real 50-product consistency
check passed against the landed dev-store facts."""

import json
import sqlite3
from pathlib import Path

import pytest

from commerceos.catalog import emitters as E
from commerceos.catalog.audit import connect_readonly
from commerceos.catalog.canonical import build_canonical, connect_guarded, ensure_schema
from commerceos.db import connect
from commerceos.spine.schema import ensure_schema as ensure_facts

REPO = Path(__file__).resolve().parents[1]
TS = "2026-07-11T00:00:00Z"
GTIN13 = "4006381333931"  # checksum-valid EAN-13

# a toy taxonomy — the engine knows nothing about outdoor gear; units and
# fit-critical flags come from this instance data.
TAXONOMY = {
    "version": 0,
    "status": "test",
    "categories": {
        "_doc": "ignored meta key",
        "Lighting": {
            "subcategories": ["Flashlights"],
            "spec_schema": [
                {"key": "max_lumens", "type": "number_integer", "unit": "lm", "fc": False},
                {"key": "ip_water_rating", "type": "single_line_text", "unit": "IP code", "fc": True},
                {"key": "weight", "type": "number_integer", "unit": "g", "fc": False},
            ],
        },
    },
}
CONFIG = {"spec_namespaces": ["commerceos"], "spec_blob_keys": ["tech_spec", "features", "category"]}


def prov(source=None, verified=False, verified_on=None, **extra) -> str:
    """a provenance companion the way the landed meta actually carries it:
    a `<field>_provenance` json metafield {source, verified, verified_on, ...}."""
    return json.dumps({"source": source, "verified": verified, "verified_on": verified_on, **extra})


def seed_product(conn, pid, title=None, vendor="V", ptype="Flashlights", meta=()):
    """land one product + its commerceos metafields the way the spine does."""
    conn.execute(
        "INSERT INTO products (shopify_id, handle, title, status, vendor, product_type,"
        " tags, raw, source, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (pid, f"h-{pid}", title or f"P {pid}", "ACTIVE", vendor, ptype, "[]", "{}", "test", TS))
    for key, value in meta:
        conn.execute(
            "INSERT INTO product_meta (product_id, namespace, key, type, value, source, fetched_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (pid, "commerceos", key, None, value, f"shopify:product/{pid}@{TS}", TS))
    conn.commit()


P1_META = (
    ("category", "Lighting"),                       # identity, not a spec claim
    ("tech_spec", "a descriptive blob"),            # blob key, not a spec claim
    ("features", "another blob"),                   # blob key, not a spec claim
    ("max_lumens", "900"),                          # verified: companion says true + source
    ("max_lumens_provenance", prov("datasheet:acme-x900.pdf", True, "2026-07-01", unit="lm")),
    ("ip_water_rating", "IPX8"),                    # unverified: companion says verified false
    ("ip_water_rating_provenance", prov("parsed:supplier-spec-blob", False, unit="IP code", fc=True)),
    ("weight", "93"),                               # unverified: no companion at all
    ("gtin", GTIN13),                               # verified gtin -> feed gtin + jsonld gtin13
    ("gtin_provenance", prov("gs1:lookup", True, "2026-07-02")),
    ("output_provenance", prov("parsed:supplier-spec-blob")),  # orphan companion, no bare value
    ("temp_rating", ""),                            # landed empty -> a gap, never a claim
)


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "t.db")
    ensure_facts(c)
    yield c
    c.close()


def claims_by_field(conn, pid):
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row
    return {r["field"]: dict(r) for r in cur.execute(
        "SELECT * FROM spec_claims WHERE product = ?", (pid,))}


# ------------------------------------------------------- the canonical build

def test_build_from_seeded_facts_with_and_without_companions(conn):
    seed_product(conn, "p1", meta=P1_META)
    counts = build_canonical(conn, TAXONOMY, CONFIG)
    assert counts == {"products": 1, "claims": 4, "verified": 2, "unverified": 2,
                      "built_at": counts["built_at"]}
    c = claims_by_field(conn, "p1")
    assert set(c) == {"max_lumens", "ip_water_rating", "weight", "gtin"}

    # a companion that says verified:true and names a source -> verified
    assert c["max_lumens"]["verified"] == 1
    assert c["max_lumens"]["source"] == "datasheet:acme-x900.pdf"
    assert c["max_lumens"]["verified_on"] == "2026-07-01"
    assert c["max_lumens"]["unit"] == "lm"

    # a companion that exists but says verified:false -> NOT verified;
    # its source still carries (parsed value awaiting a real source)
    assert c["ip_water_rating"]["verified"] == 0
    assert c["ip_water_rating"]["source"] == "parsed:supplier-spec-blob"
    assert c["ip_water_rating"]["verified_on"] is None

    # no companion at all -> verified=0, source falls back to the landed ref,
    # unit filled from the taxonomy schema
    assert c["weight"]["verified"] == 0
    assert c["weight"]["source"] == f"shopify:product/p1@{TS}"
    assert c["weight"]["unit"] == "g"

    # blobs, the identity category field, orphan companions, and empty landed
    # values never become claims — no invented values
    for absent in ("category", "tech_spec", "features", "output", "temp_rating"):
        assert absent not in c


def test_verified_without_source_lands_unverified(conn):
    # the refuse-to-guess invariant: a companion claiming verified:true with
    # no source cannot land a verified claim
    seed_product(conn, "p1", meta=(
        ("max_lumens", "500"),
        ("max_lumens_provenance", json.dumps({"verified": True})),
    ))
    build_canonical(conn, TAXONOMY, CONFIG)
    c = claims_by_field(conn, "p1")["max_lumens"]
    assert c["verified"] == 0
    assert c["source"] == f"shopify:product/p1@{TS}"  # the landed ref, the only provenance left


def test_identity_category_prefers_the_persisted_field_then_the_taxonomy_map(conn):
    seed_product(conn, "p1", meta=(("category", "Lighting"),))     # persisted customer category
    seed_product(conn, "p2", ptype="Flashlights")                  # reverse-mapped from product_type
    seed_product(conn, "p3", ptype="")                             # unresolvable
    build_canonical(conn, TAXONOMY, CONFIG)
    cats = dict(conn.execute("SELECT shopify_id, category FROM canonical_products"))
    assert cats == {"p1": "Lighting", "p2": "Lighting", "p3": None}


def test_rebuild_is_a_refresh_not_an_append(conn):
    seed_product(conn, "p1", meta=P1_META)
    build_canonical(conn, TAXONOMY, CONFIG)
    counts = build_canonical(conn, TAXONOMY, CONFIG)
    assert counts["products"] == 1 and counts["claims"] == 4


# ------------------------------------------------------------- the emitters

def test_a_claim_carries_the_same_value_on_all_three_surfaces(conn):
    seed_product(conn, "p1", title="Acme X900", vendor="Acme", meta=P1_META)
    build_canonical(conn, TAXONOMY, CONFIG)
    page = E.parse_page(E.emit_page(conn, "p1"))
    feed = E.emit_feed(conn, "p1")
    ld = E.emit_jsonld(conn, "p1")

    # the verified claim, value-identical on every surface
    assert page.rows["max_lumens"]["value"] == "900"
    assert page.rows["max_lumens"]["text"] == "900 lm"
    detail = {d["attribute_name"]: d for d in feed["product_detail"]}
    assert detail["max lumens"]["attribute_value"] == "900 lm"
    assert detail["max lumens"]["section_name"] == "Lighting"
    props = {p["name"]: p for p in ld["additionalProperty"]}
    assert props["max lumens"]["value"] == "900"
    assert props["max lumens"]["unitText"] == "lm"

    # identity travels identically too
    assert feed["id"] == ld["productID"] == "p1"
    assert feed["title"] == ld["name"] == "Acme X900"
    assert feed["brand"] == ld["brand"]["name"] == "Acme"
    assert feed["gtin"] == ld["gtin13"] == GTIN13


def test_unverified_claims_never_reach_the_machine_surfaces(conn):
    # MACHINE SURFACES CARRY VERIFIED TRUTH ONLY: an unverified claim renders
    # "not yet verified" on the page (the gap is shown, the value is not) and
    # is EXCLUDED from the feed's gtin/product_detail and from the JSON-LD's
    # gtin13/additionalProperty.
    seed_product(conn, "p1", meta=P1_META)
    seed_product(conn, "p2", meta=(
        ("gtin", "96385074"),
        ("gtin_provenance", prov("parsed:supplier-spec-blob", False)),
    ))
    build_canonical(conn, TAXONOMY, CONFIG)

    fragment = E.emit_page(conn, "p1")
    page = E.parse_page(fragment)
    for field, value in (("ip_water_rating", "IPX8"), ("weight", "93")):
        assert page.rows[field]["text"] == "not yet verified"
        assert page.rows[field]["value"] is None              # no data-value attribute either
        assert f'data-value="{value}"' not in fragment        # the value rides no attribute
        assert f">{value}<" not in fragment                   # ...and no element text
    assert "IPX8" not in fragment                             # the bare value appears nowhere at all

    feed, ld = E.emit_feed(conn, "p1"), E.emit_jsonld(conn, "p1")
    machine_names = {d["attribute_name"] for d in feed["product_detail"]} \
        | {p["name"] for p in ld["additionalProperty"]}
    assert machine_names == {"max lumens", "gtin"}    # the verified subset, exactly

    # an unverified gtin claim never becomes feed gtin or jsonld gtin13
    feed2, ld2 = E.emit_feed(conn, "p2"), E.emit_jsonld(conn, "p2")
    assert "gtin" not in feed2 and "gtin13" not in ld2
    assert feed2["product_detail"] == [] and ld2["additionalProperty"] == []


def test_fit_critical_marking_present_on_the_page(conn):
    seed_product(conn, "p1", meta=P1_META)
    build_canonical(conn, TAXONOMY, CONFIG)
    page = E.parse_page(E.emit_page(conn, "p1"))
    assert "ip_water_rating" in page.fc_fields        # taxonomy says fc for Lighting
    assert "max_lumens" not in page.fc_fields
    assert claims_by_field(conn, "p1")["ip_water_rating"]["fit_critical"] == 1


def test_emitters_read_only_the_canonical_record(conn):
    # the whole point: a raw-fact edit changes nothing until the canonical
    # record is rebuilt — the renderers never look at the facts tables.
    seed_product(conn, "p1", meta=P1_META)
    build_canonical(conn, TAXONOMY, CONFIG)
    conn.execute("UPDATE product_meta SET value = '999' WHERE key = 'max_lumens'")
    conn.execute("UPDATE products SET title = 'Renamed'")
    conn.commit()
    assert E.parse_page(E.emit_page(conn, "p1")).rows["max_lumens"]["value"] == "900"
    assert E.emit_feed(conn, "p1")["title"] == "P p1"
    build_canonical(conn, TAXONOMY, CONFIG)
    assert E.parse_page(E.emit_page(conn, "p1")).rows["max_lumens"]["value"] == "999"


def test_unknown_product_raises_instead_of_inventing(conn):
    build_canonical(conn, TAXONOMY, CONFIG)
    with pytest.raises(LookupError):
        E.emit_page(conn, "ghost")


# -------------------------------------------------- the check + the guard

def test_run_check_passes_on_the_fixture_and_writes_the_report(conn, tmp_path):
    seed_product(conn, "p1", title="Acme X900", vendor="Acme", meta=P1_META)
    seed_product(conn, "p2", meta=(("weight", "20"),))
    build_canonical(conn, TAXONOMY, CONFIG)
    result = E.run_check(conn, sample=50)
    assert result["pass"] is True
    assert result["totals"]["products"] == 2          # only products with claims are emittable
    assert result["totals"]["claims"] == 5
    assert result["totals"]["verified"] == 2 and result["totals"]["unverified"] == 3
    path = E.write_report(result, tmp_path, build={"products": 2, "claims": 5,
                                                   "verified": 2, "unverified": 3})
    md = path.read_text()
    assert "PASS" in md and "h-p1" in md and "machine surfaces carry verified truth only" in md


def test_run_check_fails_closed_on_an_empty_canonical(conn):
    ensure_schema(conn)
    assert E.run_check(conn, sample=50)["pass"] is False


def test_the_write_guard_denies_every_table_but_the_canonical_set(conn, tmp_path):
    seed_product(conn, "p1", meta=P1_META)
    g = connect_guarded(tmp_path / "t.db")
    try:
        with pytest.raises(sqlite3.DatabaseError):
            g.execute("UPDATE products SET title = 'x'")
        with pytest.raises(sqlite3.DatabaseError):
            g.execute("INSERT INTO product_meta (product_id, namespace, key, type, value,"
                      " source, fetched_at) VALUES ('p1','commerceos','k',NULL,'v','s','t')")
        with pytest.raises(sqlite3.DatabaseError):
            g.execute("DELETE FROM variants")
        # ...while its own table-set builds fine on the same connection
        counts = build_canonical(g, TAXONOMY, CONFIG)
        assert counts["products"] == 1 and counts["claims"] == 4
    finally:
        g.close()


# ------------------------------------------------------------- the real db

REAL_DB = REPO / "data" / "demostore.db"


@pytest.mark.skipif(not REAL_DB.exists(), reason="dev-store facts not landed on this machine")
def test_the_real_50_sample_check_passes():
    conn = connect_readonly(REAL_DB)
    try:
        built = conn.execute(
            "SELECT name FROM sqlite_master WHERE name = 'canonical_products'").fetchone()
        assert built, "run: uv run python -m commerceos.catalog.emitters check --sample 50"
        result = E.run_check(conn, sample=50)
    finally:
        conn.close()
    assert result["pass"] is True
    assert result["totals"]["products"] == 50
    assert result["totals"]["claims"] > 0
    assert list(REPO.glob("reports/emit-consistency-*.md")), \
        "run: uv run python -m commerceos.catalog.emitters check --sample 50"
