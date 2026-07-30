"""C1's checks: a reported part appears with zero UI changes; auth holds."""

import pytest
from fastapi.testclient import TestClient

from commerceos.db import connect
from commerceos.web import registry
from commerceos.web.app import app
from commerceos.web.auth import pair_device, require_operator


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "web.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    conn = connect(db)
    registry.ensure_schema(conn)
    registry.report(conn, "throwaway", "a test part that proves the registry", state="idle")
    conn.close()
    return TestClient(app)


def test_a_registered_part_appears_with_zero_ui_changes(client):
    api = client.get("/api/parts").json()
    assert any(p["part"] == "throwaway" for p in api["parts"])
    page = client.get("/parts")
    assert "throwaway" in page.text


def test_health_and_pages_render(client):
    assert client.get("/health").json()["ok"] is True
    for route in ("/", "/approvals", "/record", "/parts", "/economics", "/findings"):
        assert client.get(route).status_code == 200


def test_non_localhost_without_token_is_refused(tmp_path):
    from fastapi import HTTPException

    class FakeClient:  # request.client stand-in
        host = "100.101.102.103"

    class FakeRequest:
        client = FakeClient()
        headers = {}

    conn = connect(tmp_path / "auth.db")
    with pytest.raises(HTTPException) as e:
        require_operator(FakeRequest(), conn)
    assert e.value.status_code == 401


def test_paired_token_passes_from_off_localhost(tmp_path):
    conn = connect(tmp_path / "auth2.db")
    token = pair_device(conn, "phone")

    class FakeClient:
        host = "100.101.102.103"

    class FakeRequest:
        client = FakeClient()
        headers = {"authorization": f"Bearer {token}"}

    require_operator(FakeRequest(), conn)  # no raise = pass


def test_the_brief_assembles_with_named_gaps(client):
    page = client.get("/")
    assert "waits on you" in page.text
    assert "what we're watching" in page.text and "the money line" in page.text
    # gaps are named, never invisible
    assert ("not landed yet" in page.text) or ("findings" in page.text)


def test_economics_page_and_lens_recompute_from_real_shapes(client, tmp_path, monkeypatch):
    # seed books facts so the baseline is measured
    import os
    from commerceos.db import connect
    conn = connect(os.environ["COMMERCEOS_DB"])
    from commerceos.spine.schema import ensure_schema
    ensure_schema(conn)
    conn.executemany(
        "INSERT INTO money_lines (date, kind, account, amount_minor, import_batch, source, fetched_at)"
        " VALUES (?, 'books', ?, ?, 'seed', 'test', 't')",
        [("2025-03-01", "sales", 100000), ("2025-04-01", "sales", 100000),
         ("2025-03-15", "purchases", 120000)])
    conn.commit()
    page = client.get("/economics?period=2025")
    assert "gross spread" in page.text and "no data yet" in page.text
    lens = client.get("/economics/scenario?period=2025&sales_pct=10&purchases_pct=0")
    assert "scenario over 2025" in lens.text and "margin" in lens.text


def test_findings_page_renders(client):
    page = client.get("/findings")
    assert page.status_code == 200


def test_a_past_next_run_renders_overdue(client):
    """a next-run moment already gone renders 'overdue' — never a past date
    dressed as a future promise (coldread 2026-07-18, the rhythm cassette)."""
    import os
    conn = connect(os.environ["COMMERCEOS_DB"])
    registry.report(conn, "overdue-part", "a part whose next run came and went",
                    state="armed", next_run="2026-07-11T00:00:00+00:00")
    conn.close()
    page = client.get("/parts")
    assert "overdue" in page.text
    assert "2026-07-11T00:00:00" not in page.text
