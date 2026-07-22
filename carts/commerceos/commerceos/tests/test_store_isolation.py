"""M3's checks (spec/parts/multi-store.md ## checks): two stores booted
side by side — separate data/<store>.db files AND separate
data/<store>.ledger.jsonl mirrors, single-writer guards holding in both,
a write in one never visible in the other — in the database or in the
mirror. plus the rename's receipts: store #1's files now conform to the
per-store naming law."""

import json
import sqlite3
from pathlib import Path

import pytest

from commerceos import stores
from commerceos.catalog.canonical import connect_guarded
from commerceos.db import connect
from commerceos.gate import ledger
from commerceos.spine.schema import ensure_schema

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("COMMERCEOS_STORE", "COMMERCEOS_DB", "COMMERCEOS_POLICY_TABLE"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def two_stores(tmp_path):
    """a tmp workshop with two registered stores, each booted: schema up,
    one product fact landed, one ledger record minted-and-mirrored."""
    (tmp_path / "stores").mkdir()
    (tmp_path / "stores" / "registry.json").write_text(
        json.dumps({"stores": [{"name": "alpha", "default": True}, {"name": "beta"}]})
    )
    conns = {}
    for name, handle in (("alpha", "tent-alpha"), ("beta", "lamp-beta")):
        conn = connect(stores.resolve(name, stores.DB, tmp_path))
        ensure_schema(conn)
        ledger.ensure_schema(conn)
        conn.execute(
            "INSERT INTO products (shopify_id, handle, title, source, fetched_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (f"gid://{name}/1", handle, handle, f"{name} boot", "2026-07-19T00:00:00Z"),
        )
        conn.commit()
        ledger.mint(
            conn,
            {
                "agent": "isolation-test",
                "function": "catalog",
                "action_type": "consequential",
                "intent": f"{name}'s own proposal",
                "rationale": "M3 isolation battery",
                "impact": {},
                "provenance": {"cite": f"facts:products@{name}"},
                "proposal": {
                    "connector": "commerce",
                    "method": "mutate_seo",
                    "args": {"product_id": f"gid://{name}/1"},
                    "args_hash": f"h-{name}",
                },
            },
        )
        conns[name] = conn
    yield tmp_path, conns
    for c in conns.values():
        c.close()


def test_each_store_gets_its_own_files(two_stores):
    root, _ = two_stores
    assert (root / "data" / "alpha.db").exists()
    assert (root / "data" / "beta.db").exists()
    assert (root / "data" / "alpha.ledger.jsonl").exists()
    assert (root / "data" / "beta.ledger.jsonl").exists()


def test_a_fact_in_one_store_is_never_visible_in_the_other(two_stores):
    _, conns = two_stores
    alpha = {r["handle"] for r in conns["alpha"].execute("SELECT handle FROM products")}
    beta = {r["handle"] for r in conns["beta"].execute("SELECT handle FROM products")}
    assert alpha == {"tent-alpha"}
    assert beta == {"lamp-beta"}


def test_a_ledger_record_in_one_store_is_never_visible_in_the_other(two_stores):
    _, conns = two_stores
    for name, other in (("alpha", "beta"), ("beta", "alpha")):
        intents = [r["intent"] for r in conns[name].execute("SELECT intent FROM ledger")]
        assert intents == [f"{name}'s own proposal"]
        assert not any(other in i for i in intents)


def test_the_mirrors_never_interleave(two_stores):
    root, _ = two_stores
    for name, other in (("alpha", "beta"), ("beta", "alpha")):
        text = (root / "data" / f"{name}.ledger.jsonl").read_text()
        assert f"{name}'s own proposal" in text
        assert other not in text


def test_single_writer_guards_hold_in_both_stores(two_stores):
    root, _ = two_stores
    for name in ("alpha", "beta"):
        guarded = connect_guarded(stores.resolve(name, stores.DB, root))
        with pytest.raises(sqlite3.DatabaseError):
            guarded.execute(
                "INSERT INTO products (shopify_id, handle, title) VALUES ('x', 'x', 'x')"
            )
        guarded.close()


# -- the rename's receipts: store #1 conforms to the naming law --


def test_store_one_wears_the_per_store_names():
    assert (REPO_ROOT / "data" / "demostore.db").exists()
    assert (REPO_ROOT / "data" / "demostore.ledger.jsonl").exists()
    assert not (REPO_ROOT / "data" / "commerceos.db").exists()
    assert not (REPO_ROOT / "data" / "ledger.jsonl").exists()


def test_the_live_mirror_is_where_the_resolver_and_ledger_agree_it_is():
    db = stores.resolve("demostore", stores.DB)
    conn = connect(db)
    try:
        assert ledger.mirror_path(conn) == REPO_ROOT / "data" / "demostore.ledger.jsonl"
    finally:
        conn.close()
