"""the quality gate's delist flags (D5): the conservative law holds —
one decor signal alone never flags, noise shapes do, and the batch
proposal parks consequential on the owner's queue, never auto."""

import json

import pytest

from commerceos.catalog.quality import (compute_delist_candidates, decor_flags,
                                        decor_signals, noise_flags, propose_delists)
from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.spine.schema import ensure_schema


# ---------- the decor law, unit-level ------------------------------------

def test_decor_keyword_alone_never_flags():
    # a patio keyword on a legit vendor with clean type/tags: one signal, held
    assert decor_flags("Patio Lantern XL", "Vango", "Lanterns", ["Lighting"], []) == []


def test_keyword_plus_corroborating_path_flags():
    # keyword + decor-leaf product_type (the current-facts descendant of
    # v0's source_path): two signals, flagged with both named
    flags = decor_flags("Decorative Metal Wall Art", "Acme Living", "Novelty Signs", [], [])
    assert "decor_keyword" in flags and "decor_type" in flags


def test_decor_tag_plus_home_brand_flags():
    # the real landed shape: supplier Decor tag + La Hacienda
    flags = decor_flags("Hanging Goldfinch", "La Hacienda", "Camp & Household — Other",
                        ["Decor", "Garden Decor", "Home & Garden"], ["Camp & Household"])
    assert "decor_tag" in flags and "home_brand" in flags


def test_home_brand_alone_never_flags():
    # v0's law verbatim: a home brand also makes legit outdoor gear
    assert decor_signals("Delos Firepit", "La Hacienda", "Fire Pits",
                         ["Fire Pits", "Camp Kitchen"], []) == []
    assert decor_flags("Delos Firepit", "La Hacienda", "Fire Pits",
                       ["Fire Pits", "Camp Kitchen"], []) == []


def test_decor_tag_alone_never_flags():
    # supplier feeds hang "Decor" on work floodlights; tag alone is held
    assert decor_flags("AF2R Work Floodlight", "Ledlenser", "Work Lights",
                       ["Decor", "Lighting"], []) == []


# ---------- noise shapes, unit-level --------------------------------------

def test_noise_shapes_flag():
    assert "demo_handle" in noise_flags("the-complete-snowboard", "The Complete Snowboard",
                                        "Snowboard Vendor")
    assert "demo_vendor" in noise_flags("selling-plans-ski-wax", "Selling Plans Ski Wax",
                                        "CommerceOS Dev")
    assert "placeholder_title" in noise_flags("some-product", "TEST do not use", "Acme")
    assert "zero_price" in noise_flags("freebie", "Freebie", "Acme", prices=[0, None])


def test_noise_stays_word_bounded_and_conservative():
    # Bontrager's XXX line and "Contest ..." are real products
    assert noise_flags("xxx-road-cycling-shoes", "XXX Road Cycling Shoes", "Bontrager") == []
    assert noise_flags("contest-winner-tee", "Contest Winner Tee", "Acme") == []
    # one zero-price variant among priced ones is a freebie row, not junk
    assert noise_flags("bundle", "Bundle", "Acme", prices=[0, 4995]) == []
    # no_sku is corroborating-only: alone it never flags
    assert noise_flags("real-product", "Real Product", "Acme", has_sku=False) == []
    assert "no_sku" in noise_flags("gift-card", "Gift Card", "Snowboard Vendor", has_sku=False)


# ---------- fixture-driven: compute -> gate -------------------------------

def _add_product(c, pid, handle, title, vendor, ptype, tags=(), colls=(), price=4995, sku="SKU1"):
    c.execute(
        "INSERT INTO products (shopify_id, handle, title, status, vendor, product_type,"
        " tags, collections, source, fetched_at) VALUES (?,?,?,?,?,?,?,?,'s','t')",
        (pid, handle, title, "ACTIVE", vendor, ptype,
         json.dumps(list(tags)), json.dumps(list(colls))))
    c.execute(
        "INSERT INTO variants (shopify_id, product_id, sku, price_minor, source, fetched_at)"
        " VALUES (?,?,?,?,'s','t')", (f"v-{pid}", pid, sku, price))


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "quality.db")
    ensure_schema(c)
    ledger.ensure_schema(c)
    yield c
    c.close()


@pytest.fixture()
def seeded(conn):
    gid = "gid://shopify/Product/{}".format
    _add_product(conn, gid(1), "storm-shelter-tent", "Storm Shelter Tent", "Vango",
                 "Tents", ["Tents & Shelters"], ["Tents & Shelters"])          # clean
    _add_product(conn, gid(2), "patio-lantern-xl", "Patio Lantern XL", "Vango",
                 "Lanterns", ["Lighting"], ["Lighting"])                        # keyword only: held
    _add_product(conn, gid(3), "bar-grill-wall-sign", "Bar & Grill Wall Sign", "La Hacienda",
                 "Camp & Household — Other", ["Decor", "Wall Signs"], ["Camp & Household"])  # decor
    _add_product(conn, gid(4), "male-buddha-head", "Male Buddha Head", "La Hacienda",
                 "Camp & Household — Other", ["Decor", "Garden Decor"], ["Camp & Household"])  # decor
    _add_product(conn, gid(5), "delos-firepit", "Delos Firepit", "La Hacienda",
                 "Fire Pits", ["Fire Pits", "Camp Kitchen"], ["Camp & Household"])  # brand only: clean
    _add_product(conn, gid(6), "the-complete-snowboard", "The Complete Snowboard",
                 "Snowboard Vendor", "snowboard", ["Snowboard"], [], sku=None)  # noise
    _add_product(conn, gid(7), "gift-card", "Gift Card", "Snowboard Vendor",
                 "giftcard", [], [], sku=None)                                  # noise
    return conn


def test_compute_separates_the_classes(seeded):
    c = compute_delist_candidates(seeded)
    assert c["total"] == 7
    assert sorted(x["handle"] for x in c["noise"]) == ["gift-card", "the-complete-snowboard"]
    assert sorted(x["handle"] for x in c["decor"]) == ["bar-grill-wall-sign", "male-buddha-head"]
    assert [x["handle"] for x in c["held"]] == ["patio-lantern-xl"]
    # brand-only stays visible for the ruling but is never a candidate
    assert [x["handle"] for x in c["brand_only"]] == ["delos-firepit"]
    # every candidate carries its evidence, and decor evidence is >= 2 signals
    assert all(x["evidence"] for x in c["noise"] + c["decor"])
    assert all(len(x["evidence"]) >= 2 for x in c["decor"])


def test_per_product_proposals_park_as_consequential(seeded):
    c = compute_delist_candidates(seeded)
    parked = propose_delists(seeded, c, report_path="reports/test.md")
    n = len(c["noise"]) + len(c["decor"])
    assert n >= 1                                        # the fixture flags something
    # CW8: ONE proposal per PRODUCT (not per class) — noise products first, then decor
    assert len(parked) == n
    assert [p["flag_class"] for p in parked] == \
        ["noise"] * len(c["noise"]) + ["decor"] * len(c["decor"])
    assert all(p["decision"] == "parked" and p["action_type"] == "consequential"
               for p in parked)
    queue = ledger.pending_queue(seeded)
    assert len(queue) == n
    for rec in queue:
        assert rec["status"] == "pending"
        assert rec["action_type"] == "consequential"
        assert rec["gate"]["required"] is True and rec["gate"]["decision"] == "pending"
        # the exact call the executor runs: mutate_product_state, one product each
        assert rec["proposal"]["method"] == "mutate_product_state"
        assert rec["proposal"]["args"]["state"] == "delisted"
        assert rec["proposal"]["args"]["product_id"]
    # no handle minted: nothing is executable until the owner rules
    assert seeded.execute("SELECT COUNT(*) FROM handles").fetchone()[0] == 0


def test_zero_candidates_zero_proposals(conn):
    _add_product(conn, "gid://shopify/Product/9", "storm-shelter-tent",
                 "Storm Shelter Tent", "Vango", "Tents", ["Tents & Shelters"], [])
    c = compute_delist_candidates(conn)
    assert c["noise"] == [] and c["decor"] == []
    assert propose_delists(conn, c) == []
    assert ledger.pending_queue(conn) == []
    assert conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == 0
