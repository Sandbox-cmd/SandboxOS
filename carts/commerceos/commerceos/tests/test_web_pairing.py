"""WEB1 — phone pairing: QR from the desktop, a long-lived revocable token, a
cookie channel a phone browser can actually present, revoke from /parts, and
the refusal path. every off-localhost test passes an explicit client address
because the default TestClient host "testclient" is treated as localhost by
auth.is_localhost — the identity trap. code-complete pins (checkpoint 2); the
real phone walk is the owner's (checkpoint 3)."""

import re

import pytest
from fastapi.testclient import TestClient

from commerceos.db import connect
from commerceos.web import registry
from commerceos.web.app import app
from commerceos.web.auth import _hash, ensure_pairing_schema, pair_device

OFF = ("100.101.102.103", 50000)  # a real off-localhost address (not "testclient")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """a scratch db with the registry seeded — demostore is never touched."""
    path = tmp_path / "web1.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(path))
    conn = connect(path)
    registry.ensure_schema(conn)
    registry.report(conn, "throwaway", "a test part that proves the registry", state="idle")
    ensure_pairing_schema(conn)
    conn.close()
    return path


@pytest.fixture()
def local(db):
    """a localhost client (host defaults to 'testclient' → localhost-trusted)."""
    return TestClient(app)


@pytest.fixture()
def phone(db):
    """an off-localhost client — a phone reaching over tailscale."""
    return TestClient(app, client=OFF)


def _mint(db_path, label="a phone") -> str:
    """mint a token directly (stands in for a localhost pairing)."""
    conn = connect(db_path)
    token = pair_device(conn, label)
    conn.close()
    return token


def _row_count(db_path) -> int:
    conn = connect(db_path)
    ensure_pairing_schema(conn)
    n = conn.execute("SELECT count(*) FROM paired_devices").fetchone()[0]
    conn.close()
    return n


def _hash_of_label(db_path, label) -> str:
    conn = connect(db_path)
    ensure_pairing_schema(conn)
    r = conn.execute("SELECT token_hash FROM paired_devices WHERE label = ?", (label,)).fetchone()
    conn.close()
    return r[0]


def _all_db_text(db_path) -> str:
    """every stored value in paired_devices, joined — for 'raw token absent'."""
    conn = connect(db_path)
    ensure_pairing_schema(conn)
    rows = conn.execute("SELECT token_hash, label, paired_at FROM paired_devices").fetchall()
    conn.close()
    return " ".join(str(v) for r in rows for v in r)


# 1 — the pairing page mints, so it is localhost-only, harder than require_operator
def test_pair_page_is_localhost_only(db, phone):
    token = _mint(db)  # a genuinely paired device...
    # ...still cannot reach the mint surface from off-localhost, even with its token
    r = phone.get("/pair", headers={"authorization": f"Bearer {token}"})
    assert r.status_code == 403
    p = phone.post("/pair", headers={"authorization": f"Bearer {token}"},
                   data={"label": "x", "reach": "y"})
    assert p.status_code == 403
    # plain refusal words, no insider term (MAJOR 2: "localhost" never on screen)
    assert "this computer" in r.text.lower()
    assert "localhost" not in r.text.lower()
    assert "traceback" not in r.text.lower() and "exception" not in r.text.lower()


# 2 — a localhost POST mints, shows the QR once, stores only the hash
def test_pair_mints_a_token_and_shows_the_qr_once(db, local):
    r = local.post("/pair", data={"label": "kitchen phone", "reach": "http://host:8848"})
    assert r.status_code == 200
    assert "<svg" in r.text                       # the QR rendered inline
    assert "kitchen phone" in r.text              # the label echoed
    m = re.search(r"/pair/claim\?t=([A-Za-z0-9_\-]+)", r.text)
    assert m, "the claim url with the token must appear on the page"
    token = m.group(1)
    # the db stores the hash, never the raw token
    assert _hash(token) in _all_db_text(db)
    assert token not in _all_db_text(db)


# 3 — claim lands the cookie and the phone gets in
def test_claim_sets_the_cookie_and_the_phone_gets_in(db, phone):
    token = _mint(db)
    r = phone.get(f"/pair/claim?t={token}", follow_redirects=False)
    assert r.status_code == 303
    setc = r.headers.get("set-cookie", "")
    assert "commerceos_device=" in setc
    assert "httponly" in setc.lower()
    assert "secure" not in setc.lower()           # tailscale is plain http
    assert "samesite=lax" in setc.lower()
    # the same client now carries the cookie — guarded pages open
    assert phone.get("/").status_code == 200
    assert phone.get("/approvals").status_code == 200


# 4 — an unpaired device is refused; a wrong cookie is refused (the 4th leg)
def test_unpaired_device_refused(db, phone):
    r = phone.get("/")
    assert r.status_code == 401
    assert "pair this device from localhost first" in r.text
    phone.cookies.set("commerceos_device", "not-a-real-token")
    w = phone.get("/")
    assert w.status_code == 401


# 5 — revoke from the parts view; the refused-after-revoke leg pinned hard
def test_revoke_from_the_parts_view(db, local, phone):
    token = _mint(db, label="the phone to revoke")
    phone.get(f"/pair/claim?t={token}", follow_redirects=False)
    assert phone.get("/").status_code == 200                 # in
    assert "the phone to revoke" in local.get("/parts").text  # listed
    th = _hash(token)
    rev = local.post("/pair/revoke", data={"token_hash": th}, follow_redirects=False)
    assert rev.status_code in (303, 200)
    assert _row_count(db) == 0                                # row gone
    assert "the phone to revoke" not in local.get("/parts").text
    assert phone.get("/").status_code == 401                  # the same cookie now refused


# 6 — the existing bearer channel keeps working (regression)
def test_bearer_header_still_passes(db, phone):
    token = _mint(db)
    r = phone.get("/", headers={"authorization": f"Bearer {token}"})
    assert r.status_code == 200


# 7 — user-typed labels render escaped on /parts
def test_device_labels_render_escaped_on_parts(db, local):
    conn = connect(db)
    pair_device(conn, "<b>my_phone</b>")
    conn.close()
    page = local.get("/parts").text
    assert "&lt;b&gt;my_phone&lt;/b&gt;" in page
    assert "<b>my_phone</b>" not in page


# 8 — the vendored encoder's self-check
def test_qr_matrix_invariants():
    from commerceos.web.qrcodegen import QrCode

    qr = QrCode.encode_text("http://100.101.102.103:8848/pair/claim?t=abc_-DEF",
                            QrCode.Ecc.MEDIUM)
    size = qr.get_size()
    assert size >= 21 and size % 2 == 1               # square, odd, ≥ 21
    # the three finder patterns: dark core corners
    assert qr.get_module(0, 0) and qr.get_module(size - 1, 0) and qr.get_module(0, size - 1)
    # out-of-range is safe (light)
    assert qr.get_module(-1, -1) is False


# 9 — a bad claim token says so plainly, no stack, no code identifier
def test_claim_with_a_bad_token_says_so_plainly(db, phone):
    r = phone.get("/pair/claim?t=this-is-not-a-real-token", follow_redirects=False)
    assert r.status_code == 401
    body = r.text.lower()
    assert "traceback" not in body and "sqlite" not in body
    snake = re.compile(r"[a-z]{2,}_[a-z_]{2,}")
    # strip tags, then no code identifier on the visible refusal
    visible = re.sub(r"<[^>]+>", " ", r.text)
    assert not snake.findall(visible.lower()), snake.findall(visible.lower())


# MAJOR 1 (producer) — an abandoned code must never pose as a paired phone
def test_mint_without_claim_never_poses_as_paired(db, local, phone):
    # a code shown on localhost but never scanned
    conn = connect(db)
    pair_device(conn, "abandoned code")
    conn.close()
    page = local.get("/parts").text
    assert "abandoned code" in page
    assert "not scanned yet" in page
    # the abandoned row carries NO "paired <when>" stamp
    assert not re.search(r"abandoned code</span><span class='stat'>paired ", page)

    # a real claim on another device flips THAT row to "paired <when>"
    token = _mint(db, label="scanned phone")
    phone.get(f"/pair/claim?t={token}", follow_redirects=False)
    page2 = local.get("/parts").text
    assert re.search(r"scanned phone</span><span class='stat'>paired ", page2)
    assert "not scanned yet" in page2                 # the abandoned one stays honest

    # both rows carry a WORKING unpair door — including the unclaimed one
    th = _hash_of_label(db, "abandoned code")
    rev = local.post("/pair/revoke", data={"token_hash": th}, follow_redirects=False)
    assert rev.status_code in (303, 200)
    assert "abandoned code" not in local.get("/parts").text
    assert "scanned phone" in local.get("/parts").text  # the claimed one survives


# MAJOR 2 (producer) — "localhost" never reaches the pairing surfaces
def test_localhost_never_reaches_the_pairing_surfaces(db, local, phone):
    assert "localhost" not in local.get("/pair").text.lower()          # the form (200)
    r = phone.get("/pair")                                             # off-localhost refusal
    assert r.status_code == 403 and "localhost" not in r.text.lower()
    p = phone.post("/pair", data={"label": "x", "reach": "y"})          # off-localhost POST refusal
    assert p.status_code == 403 and "localhost" not in p.text.lower()
    m = local.post("/pair", data={"label": "phone", "reach": "http://desktop:8848"})
    assert "localhost" not in m.text.lower()                           # the minted code page


# plain-first guard: /pair (a page WEB1 owns whole) carries no code identifier
# on screen — the pack's "cheap honesty". NB /parts is NOT walked whole here:
# its pre-existing registry self-reports already surface metric keys outside
# WEB1's seam; the p501 block's own escaping is pinned by test 7 instead.
def test_pair_passes_the_plain_first_guard(db, local):
    snake = re.compile(r"[a-z]{2,}_[a-z_]{2,}")
    html = local.get("/pair").text
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    visible = re.sub(r"<[^>]+>", " ", html).lower()
    leaked = snake.findall(visible)
    assert not leaked, f"/pair: code identifier reached the screen: {leaked[:5]}"
