# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The check of a release's seal in plain Python: minisign's key and signature files parsed, the key id matched, Ed25519 (RFC 8032's
reference arithmetic, written here, no third-party code) verified over the BLAKE2b-512 of the manifest, then the global signature over
the signature and the trusted comment. The suite holds it against `minisign -V -H` on every fixture.

    verify(manifest_path, sig_path, pub_path) -> {"ok", "reason", "key_id", "trusted_comment"}"""
import base64, hashlib, sys

P, L = 2 ** 255 - 19, 2 ** 252 + 27742317777372353535851937790883648493
D, SQRT_M1 = -121665 * pow(121666, P - 2, P) % P, pow(2, (P - 1) // 4, P)


def _add(a, b):
    """Point addition in extended coordinates (RFC 8032 section 5.1.4)."""
    A, B = (a[1] - a[0]) * (b[1] - b[0]) % P, (a[1] + a[0]) * (b[1] + b[0]) % P
    C, E2 = 2 * a[3] * b[3] * D % P, 2 * a[2] * b[2] % P
    E, F, G, H = B - A, E2 - C, E2 + C, B + A
    return (E * F % P, G * H % P, F * G % P, E * H % P)


def _mul(s, p):
    q = (0, 1, 1, 0)
    while s:
        q, p, s = (_add(q, p) if s & 1 else q), _add(p, p), s >> 1
    return q


def _point(y, sign):
    """A point from its y and the sign of x (RFC 8032 section 5.1.3), or None when no point has them."""
    x2 = (y * y - 1) * pow(D * y * y + 1, P - 2, P) % P if y < P else None
    if not x2:
        return None if x2 is None or sign else (0, y, 1, 0)
    x = pow(x2, (P + 3) // 8, P)
    x = x if (x * x - x2) % P == 0 else x * SQRT_M1 % P
    if (x * x - x2) % P:
        return None
    x = P - x if x & 1 != sign else x
    return (x, y, 1, x * y % P)


def _decode(b):
    y = int.from_bytes(b, "little")
    return _point(y & ((1 << 255) - 1), y >> 255)


BASE = _point(4 * pow(5, P - 2, P) % P, 0)


def ed25519(pub, msg, sig):
    """RFC 8032 section 5.1.7: [S]B == R + [k]A, with S below L and both points decoded."""
    if len(pub) != 32 or len(sig) != 64:
        return False
    a, r, s = _decode(pub), _decode(sig[:32]), int.from_bytes(sig[32:], "little")
    if a is None or r is None or s >= L:
        return False
    k = int.from_bytes(hashlib.sha512(sig[:32] + pub + msg).digest(), "little") % L
    left, right = _mul(s, BASE), _add(r, _mul(k, a))
    return (left[0] * right[2] - right[0] * left[2]) % P == 0 and (left[1] * right[2] - right[1] * left[2]) % P == 0


def key_id(raw):
    """The key id as minisign prints it: its eight bytes read little-endian, in upper-case hex."""
    return raw[::-1].hex().upper()


def public(pub_path):
    """(key id bytes, the 32-byte key, the base64 line) from a minisign public key file."""
    line = [x for x in open(pub_path, encoding="utf-8").read().splitlines() if x and not x.startswith("untrusted comment:")][0].strip()
    raw = base64.b64decode(line, validate=True)
    if len(raw) != 42 or raw[:2] != b"Ed":
        raise ValueError("not a minisign Ed25519 public key")
    return raw[2:10], raw[10:], line


def verify(manifest_path, sig_path, pub_path):
    """Checks a minisign seal over a manifest against a public key; returns the trusted comment when every part holds."""
    try:
        with open(manifest_path, "rb") as m, open(sig_path, "rb") as s:
            return verify_bytes(m.read(), s.read(), pub_path)
    except OSError as e:
        return {"ok": False, "reason": f"the manifest or its seal could not be read: {e}", "key_id": None, "trusted_comment": None}


def verify_bytes(manifest, sig, pub_path):
    """The same check over the manifest's bytes and the signature file's bytes (as read from inside a wheel)."""
    out = {"ok": False, "reason": None, "key_id": None, "trusted_comment": None}
    try:
        kid, pk, _ = public(pub_path)
        out["key_id"], lines = key_id(kid), sig.decode("utf-8").splitlines()
        if len(lines) < 4 or not lines[0].startswith("untrusted comment:") or not lines[2].startswith("trusted comment: "):
            return dict(out, reason="the signature file is not in minisign's four-line form")
        raw, glob_sig = base64.b64decode(lines[1].strip(), validate=True), base64.b64decode(lines[3].strip(), validate=True)
    except (OSError, ValueError, IndexError, UnicodeDecodeError) as e:
        return dict(out, reason=f"the key or the signature could not be read: {e}")
    comment = lines[2][len("trusted comment: "):]
    if len(raw) != 74 or raw[:2] != b"ED":
        return dict(out, reason="the signature is not minisign's hashed Ed25519 form (BLAKE2b-512); the legacy unhashed form is refused")
    if raw[2:10] != kid:
        return dict(out, reason=f"signed by another key ({key_id(raw[2:10])}), not the key this tool holds ({key_id(kid)})")
    if not ed25519(pk, hashlib.blake2b(manifest, digest_size=64).digest(), raw[10:]):
        return dict(out, reason="the seal does not match the manifest: a byte of it changed since it was sealed")
    if not ed25519(pk, raw[10:] + comment.encode("utf-8"), glob_sig):
        return dict(out, reason="the trusted comment was changed since it was sealed")
    return dict(out, ok=True, trusted_comment=comment)


def main(argv):
    """seal MANIFEST MANIFEST.minisig KEY.pub: prints the trusted comment, or the reason the seal fails."""
    r = verify(*argv) if len(argv) == 3 else None
    print("usage: seal MANIFEST MANIFEST.minisig KEY.pub" if r is None else f"seal matched key {r['key_id']}; trusted comment: "
          f"{r['trusted_comment']}" if r["ok"] else f"refused: {r['reason']}")
    return 2 if r is None else 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
