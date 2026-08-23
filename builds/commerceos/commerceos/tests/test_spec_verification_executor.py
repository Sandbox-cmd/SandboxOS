"""CW7 — the local provenance flip (V1): an approved verification executes
with NO store client constructed; agreeing claims flip verified with source
AND date through catalog-loop's own writer; conflicts are stated, never
flipped; the render check gates verified_rendered; a replay is refused at
the handle wall; and the flip survives a full canonical rebuild only while
the landed value still matches — drift honestly drops the mark."""

import json

import pytest

from commerceos.catalog import canonical
from commerceos.catalog.verify_sources import build_proposal, execute_and_record
from commerceos.db import connect
from commerceos.gate import gate, ledger
from commerceos.spine import writes
from commerceos.spine.schema import ensure_schema as ensure_facts

PID = "gid://shopify/Product/1"
TS = "2026-07-11T00:00:00Z"

# the same toy taxonomy test_emitters.py uses — instance data drives units
# and fit-critical flags; the engine knows nothing about outdoor gear.
TAXONOMY = {
    "version": 0, "status": "test",
    "categories": {"Lighting": {"subcategories": ["Flashlights"], "spec_schema": [
        {"key": "ip_water_rating", "type": "single_line_text", "unit": "IP code", "fc": True},
    ]}},
}
CONFIG = {"spec_namespaces": ["commerceos"], "spec_blob_keys": ["category"]}


def prov(source=None, verified=False, verified_on=None, **extra) -> str:
    return json.dumps({"source": source, "verified": verified,
                       "verified_on": verified_on, **extra})


def seed_product(conn, pid, meta=()):
    conn.execute(
        "INSERT INTO products (shopify_id, handle, title, status, vendor, product_type,"
        " tags, raw, source, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (pid, f"h-{pid}", f"P {pid}", "ACTIVE", "V", "Flashlights", "[]", "{}", "test", TS))
    for key, value in meta:
        conn.execute(
            "INSERT INTO product_meta (product_id, namespace, key, type, value, source, fetched_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (pid, "commerceos", key, None, value, f"shopify:product/{pid}@{TS}", TS))
    conn.commit()


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "t.db")
    canonical.ensure_schema(c)
    ledger.ensure_schema(c)
    c.execute(
        "INSERT INTO canonical_products (shopify_id, handle, title, vendor, category, built_at)"
        " VALUES (?,?,?,?,?,'t')", (PID, "torch-x", "Torch X", "BrandA", "Lighting"))
    c.executemany(
        "INSERT INTO spec_claims (product, field, value, unit, source, verified, fit_critical)"
        " VALUES (?,?,?,?,?,?,?)",
        [(PID, "ip_water_rating", "IP54", "IP code", "parsed:supplier-spec-blob", 0, 1),
         (PID, "battery_type", "Li-ion", None, "parsed:supplier-spec-blob", 0, 1)])
    c.commit()
    yield c
    c.close()


@pytest.fixture(autouse=True)
def no_store_client(monkeypatch):
    """the CW7 law: this branch constructs no client — a construction is
    the test failing, not an inconvenience."""
    class Boom:
        def __init__(self, *a, **k):
            raise AssertionError("ShopifyClient constructed on a local branch")
    monkeypatch.setattr(writes, "ShopifyClient", Boom)


def _approved_record(conn, claims):
    prop = build_proposal({
        "product_id": PID, "handle": "torch-x", "title": "Torch X",
        "vendor": "BrandA", "claims": claims})
    res = gate.submit(conn, prop)
    assert res["decision"] == "parked"          # fit_critical never autos
    gate.resolve(conn, res["record_id"], "approved", by="owner", reason="checked")
    return res["record_id"]


AGREE = {"field": "ip_water_rating", "value": "IP54", "unit": "IP code",
         "found_value": "IP54", "source_url": "https://maker.example/spec",
         "quote": "IP54 rated", "verdict": "agree"}
DISAGREE = {"field": "battery_type", "value": "Li-ion", "unit": None,
            "found_value": "NiMH", "source_url": "https://maker.example/spec",
            "quote": "NiMH pack", "verdict": "disagree"}


def _claim(conn, field):
    return conn.execute(
        "SELECT verified, verified_on, source FROM spec_claims"
        " WHERE product=? AND field=?", (PID, field)).fetchone()


def test_approved_verification_flips_locally_with_source_and_date(conn):
    rid = _approved_record(conn, [AGREE, DISAGREE])
    out = execute_and_record(conn, rid)
    assert out["ok"] and out["verified_rendered"]
    assert out["flipped"] == 1 and out["conflicts_stated"] == 1

    verified, verified_on, source = _claim(conn, "ip_water_rating")
    assert verified == 1
    assert source == "https://maker.example/spec"
    assert verified_on            # the date is asserted, not assumed (schema alone allows NULL)

    # the conflict was stated for the ruling, never resolved
    assert _claim(conn, "battery_type")[0] == 0


def test_replay_refused_at_the_handle_wall(conn):
    rid = _approved_record(conn, [AGREE])
    execute_and_record(conn, rid)
    with pytest.raises(writes.WriteRefused):
        writes.execute(conn, rid, client=None)


def test_agree_without_source_refuses_and_fails_the_record(conn):
    bare = dict(AGREE, source_url=None)
    rid = _approved_record(conn, [bare])
    with pytest.raises(writes.WriteRefused):
        execute_and_record(conn, rid)
    assert ledger.get(conn, rid)["status"] == "failed"
    assert _claim(conn, "ip_water_rating")[0] == 0    # nothing flipped


def test_flip_survives_rebuild_until_the_value_drifts(tmp_path):
    c = connect(tmp_path / "facts.db")
    ensure_facts(c)
    canonical.ensure_schema(c)
    seed_product(c, "p1", meta=(
        ("category", "Lighting"),
        ("ip_water_rating", "IPX8"),
        ("ip_water_rating_provenance", prov("parsed:supplier-spec-blob", False,
                                            unit="IP code", fc=True)),
    ))
    canonical.build_canonical(c, TAXONOMY, CONFIG)
    assert c.execute("SELECT verified FROM spec_claims WHERE product='p1'"
                     " AND field='ip_water_rating'").fetchone()[0] == 0

    canonical.record_verification(c, "p1", "ip_water_rating", "IPX8",
                                  "https://maker.example/spec")
    c.commit()

    # the full rebuild wipes and re-derives from facts — the recorded
    # verification re-applies because the landed value still matches
    canonical.build_canonical(c, TAXONOMY, CONFIG)
    row = c.execute("SELECT verified, source FROM spec_claims WHERE product='p1'"
                    " AND field='ip_water_rating'").fetchone()
    assert tuple(row) == (1, "https://maker.example/spec")

    # the landed value drifts -> the verification no longer applies
    c.execute("UPDATE product_meta SET value='IPX7' WHERE key='ip_water_rating'")
    c.commit()
    canonical.build_canonical(c, TAXONOMY, CONFIG)
    assert c.execute("SELECT verified FROM spec_claims WHERE product='p1'"
                     " AND field='ip_water_rating'").fetchone()[0] == 0
    c.close()
