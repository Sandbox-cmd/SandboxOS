"""the phone-facing refusal: the shared require_operator 401 (the named
candidate row — self-unpair then tap a guarded page) currently answers a
browser with a bare JSON line. content-negotiate on Accept: a request that
prefers text/html gets a small honest page naming the fix ("this phone
isn't paired — pair it from the computer at /pair"); everyone else gets the
exact JSON FastAPI always returned, byte-identical — the 29 guarded surfaces
and every existing API caller see no change."""

import pytest
from fastapi.testclient import TestClient

from commerceos.db import connect
from commerceos.web import registry
from commerceos.web.app import app
from commerceos.web.auth import ensure_pairing_schema

OFF = ("100.101.102.103", 50000)  # off-localhost, not the "testclient" trap


@pytest.fixture()
def db(tmp_path, monkeypatch):
    path = tmp_path / "phone-refusal.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(path))
    conn = connect(path)
    registry.ensure_schema(conn)
    ensure_pairing_schema(conn)
    conn.close()
    return path


@pytest.fixture()
def phone(db):
    return TestClient(app, client=OFF)


def test_a_browser_gets_the_honest_html_page(db, phone):
    r = phone.get("/", headers={"accept": "text/html,application/xhtml+xml,"
                                          "application/xml;q=0.9,*/*;q=0.8"})
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("text/html")
    assert "this phone isn't paired" in r.text
    assert "pair it from the computer" in r.text
    assert "/pair" in r.text
    # the plain-first guard: no code identifier, no stack, on the visible page
    assert "traceback" not in r.text.lower()
    assert "pair this device from localhost first" not in r.text  # the old JSON words


def test_an_api_caller_gets_byte_identical_json(db, phone):
    # no Accept override — the httpx default ("*/*") is exactly what every
    # existing API caller (and every existing test) already sends.
    r = phone.get("/")
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("application/json")
    assert r.json() == {"detail": "pair this device from localhost first"}


def test_an_explicit_json_accept_also_gets_json(db, phone):
    r = phone.get("/", headers={"accept": "application/json"})
    assert r.status_code == 401
    assert r.json() == {"detail": "pair this device from localhost first"}


def test_the_self_unpair_then_guarded_tap_repro_reads_honestly(db, phone):
    """the named candidate row's own repro: pair, unpair yourself, then tap a
    guarded page as a browser — the phone gets prose, not a JSON dump."""
    from commerceos.web.auth import pair_device, _hash

    conn = connect(db)
    token = pair_device(conn, "the phone under test")
    conn.close()
    phone.get(f"/pair/claim?t={token}", follow_redirects=False)
    assert phone.get("/approvals").status_code == 200          # paired, in
    local = TestClient(app)                                     # localhost revokes
    local.post("/pair/revoke", data={"token_hash": _hash(token)},
               follow_redirects=False)
    r = phone.get("/approvals", headers={"accept": "text/html"})
    assert r.status_code == 401
    assert "this phone isn't paired" in r.text
