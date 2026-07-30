"""M1's checks — the store registry and the resolver (spec/parts/multi-store.md
## behavior 1): the default resolves demostore; COMMERCEOS_STORE switches the
store; an unknown store fails loudly before any read; the existing env
overrides (COMMERCEOS_DB, COMMERCEOS_POLICY_TABLE) still win over anything
the resolver returns; the registry refuses malformed shapes."""

import json

import pytest

from commerceos import stores

REPO_ROOT = stores.REPO_ROOT


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("COMMERCEOS_STORE", "COMMERCEOS_DB", "COMMERCEOS_POLICY_TABLE"):
        monkeypatch.delenv(var, raising=False)


def write_registry(root, rows):
    (root / "stores").mkdir(parents=True, exist_ok=True)
    (root / "stores" / "registry.json").write_text(json.dumps({"stores": rows}))


# -- the real registry: demostore is the default and its paths are live --


def test_default_store_is_demostore():
    assert stores.active_store() == "demostore"


def test_config_resolves_to_demostore_and_exists():
    path = stores.resolve("demostore", "policy-table.json")
    assert path == REPO_ROOT / "stores" / "demostore" / "policy-table.json"
    assert path.exists()


def test_demostore_db_resolves_to_its_own_live_file():
    # M3 renamed the legacy data/commerceos.db — every store's database
    # is data/<name>.db now, store #1 included.
    path = stores.resolve("demostore", stores.DB)
    assert path == REPO_ROOT / "data" / "demostore.db"
    assert path.exists()


# -- switching and refusing --


def test_env_switches_store(tmp_path, monkeypatch):
    write_registry(
        tmp_path,
        [{"name": "demostore", "default": True}, {"name": "scaffold"}],
    )
    monkeypatch.setenv("COMMERCEOS_STORE", "scaffold")
    assert stores.active_store(tmp_path) == "scaffold"
    assert stores.resolve("scaffold", "rhythm.json", tmp_path) == (
        tmp_path / "stores" / "scaffold" / "rhythm.json"
    )


def test_unknown_env_store_fails_loudly(monkeypatch):
    monkeypatch.setenv("COMMERCEOS_STORE", "nope")
    with pytest.raises(ValueError, match="nope"):
        stores.active_store()


def test_unknown_store_refused_before_any_read():
    with pytest.raises(ValueError, match="unknown store"):
        stores.resolve("nope", "policy-table.json")


# -- the env-override seam, honored --


def test_db_override_wins(monkeypatch):
    monkeypatch.setenv("COMMERCEOS_DB", "/somewhere/else.db")
    assert str(stores.resolve("demostore", stores.DB)) == "/somewhere/else.db"


def test_policy_table_override_wins_for_that_file_only(monkeypatch):
    monkeypatch.setenv("COMMERCEOS_POLICY_TABLE", "/somewhere/table.json")
    assert str(stores.resolve("demostore", "policy-table.json")) == "/somewhere/table.json"
    assert stores.resolve("demostore", "rhythm.json") == (
        REPO_ROOT / "stores" / "demostore" / "rhythm.json"
    )


def test_override_beats_even_an_unknown_store(monkeypatch):
    # behavior 1: an explicit override wins FIRST, before the registry is read
    monkeypatch.setenv("COMMERCEOS_DB", "/somewhere/else.db")
    assert str(stores.resolve("never-registered", stores.DB)) == "/somewhere/else.db"


# -- a store without a legacy db name gets data/<name>.db --


def test_plain_store_db_is_named_after_it(tmp_path):
    write_registry(tmp_path, [{"name": "scaffold", "default": True}])
    assert stores.resolve("scaffold", stores.DB, tmp_path) == tmp_path / "data" / "scaffold.db"


# -- malformed registries refuse loudly --


def test_missing_registry_refused(tmp_path):
    with pytest.raises(FileNotFoundError):
        stores.load_registry(tmp_path)


def test_no_default_refused(tmp_path):
    write_registry(tmp_path, [{"name": "a"}, {"name": "b"}])
    with pytest.raises(ValueError, match="0 stores as default"):
        stores.load_registry(tmp_path)


def test_two_defaults_refused(tmp_path):
    write_registry(tmp_path, [{"name": "a", "default": True}, {"name": "b", "default": True}])
    with pytest.raises(ValueError, match="2 stores as default"):
        stores.load_registry(tmp_path)


def test_duplicate_name_refused(tmp_path):
    write_registry(tmp_path, [{"name": "a", "default": True}, {"name": "a"}])
    with pytest.raises(ValueError, match="twice"):
        stores.load_registry(tmp_path)
