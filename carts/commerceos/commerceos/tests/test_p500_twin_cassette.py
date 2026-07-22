"""p500 twin cassettes: /parts once rendered this part's cassette title as
the bare registry key "watching", while the record's own voice everywhere
else (comments, the /findings block, the agent manifests) calls it "the
watching" — a self-contradiction between two places a person reads the same
part's name. the house form is "the watching"; every other cassette's raw
key is untouched (no other part carries this clash)."""

import pytest
from fastapi.testclient import TestClient

from commerceos.db import connect
from commerceos.watching import schema as wschema, status as wstatus
from commerceos.web import registry
from commerceos.web.app import app, part_title


@pytest.fixture()
def db(tmp_path, monkeypatch):
    path = tmp_path / "twin-cassette.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(path))
    conn = connect(path)
    registry.ensure_schema(conn)
    wschema.ensure_schema(conn)
    wstatus.report_status(conn)  # the watching's own self-report, no live data
    conn.close()
    return path


def test_the_watching_cassette_reads_the_house_form(db):
    client = TestClient(app)
    page = client.get("/parts").text
    assert "<h3>the watching <span class='state'>" in page
    assert "<h3>watching <span class='state'>" not in page


def test_other_cassette_titles_are_untouched():
    assert part_title("catalog-lifecycle") == "catalog-lifecycle"
    assert part_title("gate-and-record") == "gate-and-record"
    assert part_title("web-surface") == "web-surface"


def test_the_registry_key_itself_is_unchanged(db):
    # a render-time label, not a rename — lookups still key on "watching".
    conn = connect(db)
    parts = registry.all_parts(conn)
    conn.close()
    assert any(p["part"] == "watching" for p in parts)
    assert not any(p["part"] == "the watching" for p in parts)
