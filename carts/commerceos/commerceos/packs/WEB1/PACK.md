git diff --quiet 53192cf..HEAD -- commerceos/web/auth.py commerceos/web/app.py commerceos/web/static/teletext.css spec/experience.md stores/demostore/rhythm.json tests/test_web_surface.py || echo "STALE — re-true before build (see RUNBOOK)"

# WEB1 — phone pairing: QR from the desktop, long-lived revocable token, over tailscale

## mission

the auth core already exists (paired_devices table, token mint, localhost-or-
bearer guard) but no surface uses it: there is no way to pair a phone, no way
for a phone browser to present the token, no list of paired devices, no
revoke. this build adds the QR pairing page (localhost-only), the claim leg
that lands the token in the phone's browser as a cookie, the paired-devices
block on /parts with revoke, and the refusal path — leaving identity exactly
where the open 7c ruling holds it.

as-of: commit 53192cf · suite 437 green (re-trued from 3c506f9/394; app.py churned +386 lines, auth.py byte-identical — see re-true note below)

## the backlog check (verbatim, backlog.md:104)

> pair by QR → approve from the phone → revoke from the parts view; unpaired device refused

## model

opus — one genuinely novel piece (a vendored dependency-free QR encoder whose
correctness can only be half-proven without the phone), an auth-surface change
(require_operator grows a second credential channel), and a hardware-gated
checkpoint that demands honest partial-done bookkeeping.

## boundaries

- **stores/dbs written**: scratch dbs only (COMMERCEOS_DB → tmp in every
  test; the checkpoint-3 live walk serves a SEEDED SCRATCH db through uvicorn
  — the phone pairs against that instance). data/<store>.db may hold a real catalog:
  this build never writes it. the REAL pairing of the owner's phone against
  demostore is the owner's own act after ship, not a build step.
- **table written**: `paired_devices` only — it rides the registry table-set
  and the web surface is its writer (auth.py:15, precedent: pair_device
  already writes it directly at :42-46). this is NOT a store write; the
  one-write-door law (writes.execute) governs store writes and is untouched.
- **gate lane**: none — pairing and revoking are the surface's own controls,
  not proposals. no approve verb is added to any agent-facing API.
- **writer-class**: no agent involved.
- **identity — hard boundary**: the approver identity strings ("localhost" /
  "paired-device", app.py:1201) are under the open [owner] 7c ruling. this
  build must NOT invent identity: no device label ever reaches a ledger `by`
  field. the label lives on /parts only.
- **reach is the owner's**: tailscale config is not a build item (ntfy
  precedent, backlog.md owner-gated list). the pairing form takes a reach
  address as input; it never configures the network.

## step plan (M-size: 3 checkpoints)

### step 1 — vendor the QR encoder, then write the failing tests

1a. vendor `qrcodegen.py` (nayuki's QR-Code-generator, MIT, single pure-python
    file, zero deps) into `commerceos/web/qrcodegen.py`, license header kept,
    marked vendored. verify by encoding a known string and checking matrix
    invariants (square, odd size ≥ 21, the three finder patterns). adding a
    pip dependency instead is an ESCALATION, not a fallback you may take
    silently. pyproject.toml today: fastapi, sse-starlette, uvicorn — nothing
    QR-capable, verified; no qrcode/segno/PIL importable in the env.
1b. failing tests in a new tests/test_web_pairing.py (rig: test_web_surface.py
    :12-20 + the off-localhost trick `TestClient(app, client=("100.101.102.103",
    50000))` — supported, starlette 1.3.1; the default host "testclient" is
    treated as localhost by auth.py:52, which is exactly the trap):
    - `test_pair_page_is_localhost_only` — off-localhost GET /pair → 403 even
      WITH a valid paired token; plain refusal words.
    - `test_pair_mints_a_token_and_shows_the_qr_once` — localhost POST /pair
      (urlencoded label + reach) → page carries an `<svg`, the claim url with
      the token, and the label; the db row stores sha256(token) (auth._hash
      :32-35) and the raw token appears NOWHERE in the db.
    - `test_claim_sets_the_cookie_and_the_phone_gets_in` — off-localhost GET
      /pair/claim?t=<token> → 303 + Set-Cookie (HttpOnly, no Secure flag —
      tailscale is plain http); the same client with that cookie then GETs /
      and /approvals → 200.
    - `test_unpaired_device_refused` — off-localhost, no cookie, no bearer →
      401 with the existing plain words (auth.py:68); a WRONG cookie value →
      401 too.
    - `test_revoke_from_the_parts_view` — pair, claim, prove 200; POST
      /pair/revoke (token_hash) → row gone, /parts no longer lists the label,
      and the SAME cookie now gets 401. the refusal after revoke is half the
      backlog check — pin it hard.
    - `test_bearer_header_still_passes` — the existing API channel keeps
      working off-localhost (regression beside test_web_surface.py:52-63).
    - `test_device_labels_render_escaped_on_parts` — label `<b>my_phone</b>`
      renders escaped (user-typed ink; the escape-before-markup law).
    - `test_qr_matrix_invariants` — the vendored encoder's self-check.

CHECKPOINT 1 — tests failing for the right reasons; every file you plan to
touch is in context.md's seam map. stop and review.

### step 2 — build to suite-green (CODE-COMPLETE stops here)

2a. `require_operator` (auth.py:55-68) grows the cookie channel: localhost
    passes; else Bearer header OR a `commerceos_device` cookie whose sha256
    matches a paired_devices row. same hash path, same refusal words. a
    phone BROWSER cannot send Authorization headers on navigation — the
    cookie IS the phone story; SSE (/api/events) rides cookies automatically.
2b. `revoke_device(conn, token_hash)` in auth.py — DELETE by PK, commit;
    plus `list_devices(conn)` returning label + paired_at + token_hash.
2c. the surfaces in app.py:
    - GET /pair (localhost-only, 403 otherwise): a small form — label
      ("your phone"), reach address prefilled from the store's rhythm.json
      ntfy.link_base when set (guarded read; the ntfy precedent — reach is
      the owner's config), else the request's host. plain words about what
      pairing does.
    - POST /pair (localhost-only): parse the urlencoded body BY HAND like
      api_resolve does (app.py:1177-1187) — python-multipart is NOT a
      dependency and FastAPI's Form() needs it; mint via pair_device
      (auth.py:38-47), render the QR as inline SVG (dark modules on a light
      block with a quiet zone — cameras need the contrast; do not let the
      teletext dark ground touch the code), the claim url in plain text
      under it, and "shown once" honesty.
    - GET /pair/claim (UNGUARDED — the one door an unpaired phone may open):
      validate ?t= against the table; ok → Set-Cookie (HttpOnly, SameSite=Lax,
      long Max-Age — "long-lived, revocable" per spec/experience.md:94-95) +
      303 to /; bad token → 401 plain words.
    - /parts (parts_view, app.py:635-700): a new block after p500 —
      "p501 · phones paired to this room" (final words the builder's, plain,
      guard-safe): label · paired when (when_plain) · an "unpair" POST button
      per row; empty state says no phone is paired yet and points at /pair.
      POST /pair/revoke is _guard-ed (a paired phone may revoke itself).
2d. wire nothing into identity: the 7c seam stays byte-identical. AT HEAD it
    is app.py:1234 (was :1201) — and a SECOND 7c site surfaced at app.py:1034-
    1036 (the grant-widen verb) plus the render-map at :3216/:3228; leave all
    three untouched.

CHECKPOINT 2 — full suite green at ≥ 394 + the new pins, zero skips. take the
producer captures NOW (scratch-db TestClient walk: /pair form, the QR page,
/parts with a paired row, the 401 body) — WEB1 is [product]; the cold read
runs on these. review the diff against the laws checklist. **this is
code-complete — the pack's honest stopping point without the phone.**

### step 3 — HARDWARE STOP: the owner's phone in hand

the backlog check CANNOT pass without the phone (escalation trigger 4 by
design — named here so it is a checkpoint, not a surprise):
- serve a seeded scratch db: `COMMERCEOS_DB=/tmp/web1-live.db uv run uvicorn
  commerceos.web.app:app --host 0.0.0.0 --port 8848` (0.0.0.0 so tailscale
  reaches it; the auth guard is what protects non-localhost, and proving
  that IS this walk).
- on the desktop: /pair → QR on screen. on the phone (over tailscale): scan
  → claim → the surface renders. stage an approvable item in the scratch db;
  approve it FROM THE PHONE (the check's second leg; the ledger `by` reads
  "paired-device" — today's word, per the riding 7c). revoke from /parts on
  the desktop; the phone's next tap gets the plain 401. unpaired second
  device (or the phone post-revoke) refused — the check's last leg.
- producer re-walk on fresh captures if the cold read found anything.

if the session is headless or the phone is not present: STOP at checkpoint 2,
stage the note "WEB1 code-complete, checkpoint 3 waits on the phone in hand"
with the commit sha — that is the designed outcome, not a failure. WEB1 was
already skipped once by the owner's word for exactly this (backlog.md:29-30).

## escalation triggers

RUNBOOK's six, plus:

- the QR encoder cannot be vendored (no network to fetch, or the vendored
  file's self-test fails) → escalate with the honest alternatives: add
  `segno` as a dependency (trigger: dependency), or ship the claim-url-as-
  text fallback and propose a spec edit — never silently ship a QR you
  cannot structurally verify.
- anything that wants a device label, or any new string, in a ledger `by`
  field → the 7c rides; stop.
- any surface needing python-multipart or any new dependency → stop.
- the cookie channel breaking an existing surface's auth test → the suite
  count law (trigger 3), plus auth is load-bearing on 28 _guard sites
  (app.py:559 wraps require_operator) — a regression here is a stop, not a
  fix-forward.
- checkpoint 3 without the phone → trigger 4/6; stage and end, as written.

## "done"

RUNBOOK's five lines, plus: (a) the check's four legs each proven ON THE
PHONE at checkpoint 3 (pair by QR · approve from the phone · revoke from
/parts · unpaired refused) — code-complete at checkpoint 2 is staged as
partial-done, never claimed as the check passing; (b) HARD producer cold read
(WEB1 is [product]) over the checkpoint-2 captures, findings block until
repaired; (c) the 7c ruling untouched and named in the make note; (d) commit
by path: auth.py, app.py, qrcodegen.py (vendored, license named in the
commit), teletext.css if touched, tests — never `git add -A`.

## risks inline

- **the testclient identity trap**: "testclient" IS localhost (auth.py:52).
  every refusal test must pass `client=("100.101.102.103", 50000)` to
  TestClient or it tests nothing. verified: starlette 1.3.1 supports the
  kwarg.
- **token in the claim url**: the QR carries the token in a GET query — it
  lands in the phone's history and uvicorn's access log. device-local
  exposure, accepted for v1 and named here; a one-time claim code is the
  upgrade if the owner wants it (new state, out of scope). the 303 redirect
  at claim drops it from the visible url.
- **no Secure cookie flag**: tailscale reach is plain http — a Secure cookie
  would never ride. HttpOnly + SameSite=Lax, yes; Secure, no.
- **QR contrast on the teletext ground**: the dark theme will eat a naive
  QR. white block, quiet zone ≥ 4 modules, dark modules — or the phone
  camera fails at checkpoint 3 with the owner watching.
- **plain-language guard**: /pair and the p501 block are person-facing.
  labels are user ink — escape them (the record-born-ink law, commit
  1f7936e); a label like "my_phone" would trip the snake regex if the guard
  ever walks these pages — escape does not save you there, word choice on
  CHROME does; the guard walk list does not include /parts or /pair today,
  extend it if you add one (cheap honesty).
- **app.py churn**: four packs collide on app.py; INDEX pull order runs WEB1
  LAST, "when the phone is in hand; re-true first". expect _guard and
  api_resolve line refs to have moved — trust the map only after line 1
  passes.
- **append-only ledger**: untouched here — approving from the phone rides
  the existing resolve verb; write no new ledger paths.
