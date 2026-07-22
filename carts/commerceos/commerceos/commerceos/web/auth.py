"""auth for the web surface: localhost trusted by binding; any other
origin carries a device-paired bearer token issued once on localhost.
tailscale is reach, not auth. money moves add a per-move confirm field
on top (the gate's resolve endpoint requires it)."""

from __future__ import annotations

import secrets
import sqlite3

from fastapi import HTTPException, Request

from commerceos.db import migrate

TABLE_SET = "registry"  # small; rides the registry table-set (web is its writer)

_PAIRING_MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS paired_devices (
        token_hash TEXT PRIMARY KEY,
        label      TEXT,
        paired_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    # additive: paired_at is MINT time (a code was shown). claimed_at is when
    # the phone actually scanned it — NULL until then. an abandoned code must
    # never render as a paired phone. existing rows tolerate NULL (they predate
    # the claim leg; they read "not scanned yet" until scanned or unpaired).
    "ALTER TABLE paired_devices ADD COLUMN claimed_at TEXT;",
]


def ensure_pairing_schema(conn: sqlite3.Connection):
    migrate(conn, "registry-pairing", _PAIRING_MIGRATIONS)


def _hash(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


def pair_device(conn: sqlite3.Connection, label: str) -> str:
    """issue a token — call only from a localhost request."""
    ensure_pairing_schema(conn)
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO paired_devices (token_hash, label) VALUES (?, ?)",
        (_hash(token), label),
    )
    conn.commit()
    return token


def revoke_device(conn: sqlite3.Connection, token_hash: str) -> int:
    """un-pair a device by its stored hash. revoke is a DELETE — the table has
    no status column. returns how many rows went (0 if the hash was unknown)."""
    ensure_pairing_schema(conn)
    cur = conn.execute("DELETE FROM paired_devices WHERE token_hash = ?", (token_hash,))
    conn.commit()
    return cur.rowcount


def list_devices(conn: sqlite3.Connection) -> list[dict]:
    """the paired phones, newest first — label, paired_at (when the code was
    shown), claimed_at (when the phone actually scanned it, or None), and the
    token_hash that revoke needs. the raw token was shown once, never stored."""
    ensure_pairing_schema(conn)
    return [
        {"label": r["label"], "paired_at": r["paired_at"],
         "claimed_at": r["claimed_at"], "token_hash": r["token_hash"]}
        for r in conn.execute(
            "SELECT label, paired_at, claimed_at, token_hash FROM paired_devices "
            "ORDER BY paired_at DESC"
        )
    ]


def claim_device(conn: sqlite3.Connection, token: str) -> bool:
    """the phone scanned its code: validate the minted token and stamp the
    first claim (COALESCE keeps the original scan time on a re-scan). returns
    False for an unknown token — nothing is stamped, the claim door refuses."""
    ensure_pairing_schema(conn)
    th = _hash(token)
    if not conn.execute(
        "SELECT 1 FROM paired_devices WHERE token_hash = ?", (th,)
    ).fetchone():
        return False
    conn.execute(
        "UPDATE paired_devices SET claimed_at = COALESCE(claimed_at, datetime('now')) "
        "WHERE token_hash = ?", (th,))
    conn.commit()
    return True


COOKIE_NAME = "commerceos_device"  # a phone browser cannot send a Bearer header
                                   # on navigation — the cookie IS the phone story


def _token_is_paired(conn: sqlite3.Connection, token: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM paired_devices WHERE token_hash = ?", (_hash(token),)
    ).fetchone())


def _label_for_token(conn: sqlite3.Connection, token: str) -> str | None:
    """the label on the row whose hash matches the presented credential, or
    None if the credential names no row (should not happen past require_operator,
    which already validated the same hash — this is a lookup, not a second gate)."""
    row = conn.execute(
        "SELECT label FROM paired_devices WHERE token_hash = ?", (_hash(token),)
    ).fetchone()
    return row["label"] if row else None


def identity_label(request: Request, conn: sqlite3.Connection) -> str:
    """the 7c threading: the honest built fact behind 'who did this'. localhost
    carries the fixed word 'the desk'; a paired device carries the LABEL its
    owner typed at pairing time (looked up from the same credential
    require_operator already trusted — the Bearer header or the device
    cookie), never the bare code word 'paired-device'. both identity sites
    (api_resolve, the grant-widen verb) call this one helper so the ledger
    never has two shapes for the same fact. the fallback string only fires if
    a credential passes require_operator's gate but names no row (should not
    happen; not a second gate, just an honest label when the impossible does)."""
    if is_localhost(request):
        return "the desk"
    ensure_pairing_schema(conn)
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        label = _label_for_token(conn, auth.removeprefix("Bearer "))
        if label is not None:
            return label
    cookie = (getattr(request, "cookies", None) or {}).get(COOKIE_NAME)
    if cookie:
        label = _label_for_token(conn, cookie)
        if label is not None:
            return label
    return "a paired device"


def is_localhost(request: Request) -> bool:
    client = request.client
    return client is not None and client.host in ("127.0.0.1", "::1", "testclient")


def require_operator(request: Request, conn: sqlite3.Connection) -> None:
    """localhost passes; anything else needs a paired token, presented EITHER
    as a Bearer header (the API channel) OR the commerceos_device cookie (the
    phone-browser channel — same hash path, same refusal words)."""
    if is_localhost(request):
        return
    ensure_pairing_schema(conn)
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        if _token_is_paired(conn, auth.removeprefix("Bearer ")):
            return
    # the cookie channel. getattr keeps the unit-test FakeRequest (no .cookies)
    # on its existing 401 path rather than raising AttributeError. NOT gated on
    # claimed_at: the cookie is only ever set BY a successful claim (which
    # stamps claimed_at), and the Bearer path above already accepts an
    # unclaimed token — possession of the raw token IS the credential. gating
    # only the cookie path would be incoherent, so authorization stays keyed on
    # possession; claimed_at is an HONESTY fact for the roster, not an auth gate.
    cookie = (getattr(request, "cookies", None) or {}).get(COOKIE_NAME)
    if cookie and _token_is_paired(conn, cookie):
        return
    raise HTTPException(status_code=401, detail="pair this device from localhost first")
