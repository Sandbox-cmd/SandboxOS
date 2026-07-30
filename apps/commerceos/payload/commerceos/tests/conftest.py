"""shared-copy skips: what a store must supply before a test can speak.

this file exists because commerceos ships without a store. mechanism is
here in full; the config and the facts that make a store real — its
taxonomy, its collection definitions, its database, its watch-list, its
API credentials — belong to whoever runs it.

a test that needs one of those does not fail here and it does not quietly
pass. it skips, naming the file you owe it. author that file and the test
wakes up on its own — nothing here needs editing.

delete this file once your store is real and every check should bite.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from commerceos import stores

ROOT = Path(__file__).resolve().parents[1]


def _store() -> str:
    try:
        return stores.active_store(ROOT)
    except Exception:
        return "demostore"


def _has_store_file(name: str) -> bool:
    return (ROOT / "stores" / _store() / name).exists()


def _has_db() -> bool:
    """a database with facts in it. the file alone proves nothing — a test run
    creates an empty one, and an empty store cannot answer these questions."""
    db = ROOT / "data" / f"{_store()}.db"
    if not db.exists():
        return False
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        return False
    try:
        return conn.execute("SELECT 1 FROM products LIMIT 1").fetchone() is not None
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def _has_credentials() -> bool:
    """a connector still wearing the placeholder domain reaches no store."""
    p = ROOT / "stores" / _store() / "connector.json"
    if not p.exists():
        return False
    try:
        domain = json.loads(p.read_text()).get("shop_domain", "")
    except ValueError:
        return False
    return bool(domain) and not domain.startswith("your-store")


def _has_watch_metrics() -> bool:
    p = ROOT / "stores" / _store() / "watch-list.json"
    if not p.exists():
        return False
    try:
        return bool(json.loads(p.read_text()).get("metrics"))
    except ValueError:
        return False


# requirement -> (is it met?, what you owe, where it goes)
NEEDS = {
    "taxonomy": (
        lambda: _has_store_file("taxonomy.json"),
        "a store taxonomy — author yours at stores/{store}/taxonomy.json"
        " (shape: spec/parts/catalog-loop.md)",
    ),
    "collections": (
        lambda: _has_store_file("collections.json"),
        "collection definitions — author yours at stores/{store}/collections.json"
        " (shape: spec/parts/catalog-loop.md)",
    ),
    "database": (
        _has_db,
        "a store database with landed facts — run the onboarding ceremony, then a"
        " sync, to fill data/{store}.db"
        " (spec/parts/multi-store.md)",
    ),
    "credentials": (
        _has_credentials,
        "live store credentials — fill stores/{store}/connector.json and put the"
        " secret in your Keychain (spec/parts/data-spine.md)",
    ),
    "watch-metrics": (
        _has_watch_metrics,
        "watch-list metrics — add rows to stores/{store}/watch-list.json"
        " (shape: spec/parts/watching.md)",
    ),
}

# (module stem, substring of the test name or None for the whole module) -> requirement
RULES = [
    ("test_catalog_classification", None, "taxonomy"),
    ("test_catalog_audit", "prior_body_delta", "taxonomy"),
    ("test_catalog_audit", "real_rebaseline", "database"),
    ("test_merchandising", None, "collections"),
    ("test_merchandising_web", None, "collections"),
    ("test_catalog_dashboard", "live_progress_and_queue_depth", "collections"),
    ("test_catalog_dashboard", "no_jargon_or_raw_codes", "collections"),
    ("test_catalog_dashboard", "live_coverage", "collections"),
    ("test_connector_shopify", "live_", "credentials"),
    ("test_economics", "real_", "database"),
    ("test_emitters", "real_", "database"),
    ("test_rhythm", "real_failed_job", "database"),
    ("test_store_isolation", "store_one_wears", "database"),
    ("test_watching", "real_books", "database"),
    ("test_watching", "gulf_curve", "watch-metrics"),
    ("test_watching", "watch_list_loads", "watch-metrics"),
    ("test_watching_surface", "drift_mode", "watch-metrics"),
]


def pytest_collection_modifyitems(items):
    met = {}
    for item in items:
        stem = Path(str(item.fspath)).stem
        for module, needle, req in RULES:
            if stem != module:
                continue
            if needle and needle not in item.name:
                continue
            if req not in met:
                met[req] = NEEDS[req][0]()
            if not met[req]:
                reason = NEEDS[req][1].format(store=_store())
                item.add_marker(pytest.mark.skip(reason=reason))
            break
