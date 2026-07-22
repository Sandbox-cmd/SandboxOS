# WEB1 · context — the frozen seam map

every ref read fresh at commit 3c506f9. WEB1 runs last in the pull order and
app.py will have churned — line 1 of PACK.md gates every number below.

## RE-TRUE @ HEAD 53192cf (suite 437) — 2026-07-19

line 1 printed STALE. auth.py is BYTE-IDENTICAL (every ref below still exact).
spec/experience.md, rhythm.json, test_web_surface.py: UNCHANGED. app.py grew
3155 → 3541 (+386, from 3ab25d1 delist · a113f47 seo · 53192cf table+p202).
teletext.css changed (cosmetic; no WEB1 seam depends on a css line). corrected
app.py line refs (old → HEAD):

- `_db`         :545-550  → :578-583
- `_guard`      :559-560  → :592-593   (call sites 28 → 29)
- SSE /api/events :575-591 → :608-624
- `_asof`       :594-596  → :627-629
- `_page`       :599-617  → :632-650
- static `_ALLOWED_STATIC` :620-632 → :653-665 (still allow-list only; inline SVG)
- `parts_view`  :635-700  → :669-733 · p500 block built at :728-729 · p501
  insertion point is between :729 and the /fleet cross-link :730-731 · `_page`
  call :732
- `api_resolve` :1167-1234 → :1201+ · the hand-parsed form body no longer uses
  the manual split — it is now `parse_qs((await request.body()).decode())` at
  :1213-1218 (copy THIS shape; python-multipart still not a dep)
- the 7c identity seam :1201 → :1234 (DO NOT TOUCH); a SECOND 7c site appeared
  at :1034-1036 (grant-widen verb) and a render-map at :3216/:3228 — all three
  untouched
- `when_plain`  :1345 → :1412

no claim in the pack is contradicted by HEAD; the build proceeds on these numbers.


## seam map (verified)

### commerceos/web/auth.py (68 lines — read it whole)

- module doc :1-4 — the ruled auth model in one breath: "localhost trusted by
  binding; any other origin carries a device-paired bearer token issued once
  on localhost. tailscale is reach, not auth."
- `TABLE_SET = "registry"` :15 — paired_devices rides the registry table-set;
  the web surface is its writer. this is why direct writes here are legal.
- `paired_devices` migration :17-25 — token_hash TEXT PRIMARY KEY · label ·
  paired_at (defaults now). no status column: revoke = DELETE.
- `ensure_pairing_schema` :28-29 — idempotent, called lazily.
- `_hash` :32-35 — sha256 hex; the raw token is never stored.
- `pair_device(conn, label) -> str` :38-47 — mints secrets.token_urlsafe(32),
  stores the hash, returns the raw token ONCE. docstring: "call only from a
  localhost request" — today that is convention, not enforcement; the /pair
  endpoints make it mechanical.
- `is_localhost` :50-52 — hosts "127.0.0.1", "::1", **"testclient"** (the
  identity trap).
- `require_operator` :55-68 — localhost passes; else Bearer-token hash match;
  else 401 "pair this device from localhost first". THE EDIT SITE for the
  cookie channel.

### commerceos/web/app.py (3,155 lines)

- `_guard` :559-560 — wraps require_operator; grep counts 28 call sites, so
  the cookie channel lights up every surface at once, including:
- `api_resolve` :1167-1234 — the system's only approve verb; the identity
  seam at :1201: `by=(form.get("by") or ("localhost" if <localhost host> else
  "paired-device"))` — the 7c's exact line. DO NOT TOUCH. it also shows the
  hand-parse of urlencoded bodies :1177-1187 (python-multipart is not a
  dependency) — copy this for POST /pair and POST /pair/revoke.
- `parts_view` :635-700 — the p500 block builds cards :644-694, block at
  :695-696, then the fleet cross-link :697-698 and `_page("system", ...)`
  :699. the p501 paired-phones block lands between :696 and :697.
- `_page` :599-617 — the frame every new page wears; `_db` :545-550;
  `when_plain` :1345 (plain times for "paired when").
- `_asof` :594-596 — lowercase chrome date, if the block wants one.
- page numbers in use (avoid collisions): p200-p299 catalog · p500 parts ·
  p601 suppliers · p700/p701 findings. p501 is free.
- SSE `/api/events` :575-591 — guarded like everything else; EventSource
  sends cookies automatically, so the phone gets live updates for free once
  the cookie channel exists.
- static serving :620-632 — ALLOW-LISTED files only (tokens.css,
  teletext.css). an SVG QR must be INLINE in the page, not a static file,
  unless you extend the allow-list (don't — inline is simpler and per-token).

### the reach prefill (owner's config, read-only)

- stores/demostore/rhythm.json → `ntfy.link_base` ("http://localhost:8000"
  today; its _doc says "set it to the tailscale hostname when the phone
  needs reach"). read via `commerceos.rhythm.runner.load_config()`
  (runner.py:70-71, call-time store resolution) inside try/except — a
  missing config must never break /pair. this is the ntfy precedent: the
  build reads the owner's reach config, never writes it.

### the spec (the contract)

- spec/experience.md:94-95 — "phone pairing: a QR code on the desktop surface
  mints a long-lived, revocable token; reach is over tailscale." (RULED
  2026-07-18 [owner], the "how it is served" section :90-99.)
- spec/experience.md:103-104 — "works in the phone's browser" — why the
  cookie channel is required, not optional: browsers do not send Bearer
  headers on navigation.
- AGENTS.md conventions — "no approve verb on any agent-facing API"; "phone
  reach via tailscale" (settled decision).

### QR (verified absent)

- pyproject.toml deps: fastapi, sse-starlette, uvicorn (+dev: httpx, pytest).
  no qrcode/segno/qrcodegen/PIL importable (checked in the env). vendoring
  target: `commerceos/web/qrcodegen.py` — nayuki's single-file MIT encoder;
  render `qr.get_module(x, y)` into one inline `<svg>` path string. version
  auto-fits; a ~60-char claim url fits comfortably in a low version at ECC M.

## prior art (copy these shapes)

- **rig + refusal tests**: tests/test_web_surface.py — the client fixture
  :12-20 (COMMERCEOS_DB → tmp, registry seeded, TestClient); the FakeRequest
  unit shape :36-63 for require_operator-level pins. for ENDPOINT-level
  off-localhost tests use `TestClient(app, client=("100.101.102.103", 50000))`
  — verified supported (starlette 1.3.1 TestClient signature has
  `client: tuple[str, int] = ("testclient", 50000)`).
- **hand-parsed form POST + browser-vs-JSON answers**: api_resolve
  app.py:1177-1193 (the SP1 lesson: a browser click never lands on raw
  JSON — /pair/revoke should 303 back to /parts).
- **a block of rows on /parts**: the cassette cards :686-693 and the
  drift-rows table :664-666 — either shape fits the paired-phones list.
- **escaping user ink**: the record-born-ink law (commit 1f7936e) — every
  label goes through html escaping before markup.
- **honest live-walk script**: scripts/a6_prove.py — the shape of a scripted
  proof with receipts printed ("the approver is labeled session:a6-proof —
  the record never claims the owner pressed"). the checkpoint-3 walk borrows
  its spirit: never simulate the phone's tap in the record.

## binding laws specific to this item

- pairing MINTS on localhost only — enforce mechanically (403), do not trust
  the docstring convention (auth.py:39).
- the claim endpoint is the single unguarded door and validates a minted
  token before doing anything; everything else stays behind _guard.
- identity is the 7c's: "localhost" / "paired-device" (app.py:1201) render
  as-is until the owner rules; labels never reach the ledger.
- the gate stays untouched: no approve verb added anywhere, no new write
  path; phone approves ride the existing /api/approvals/{id} resolve verb.
- verify rendered, never files-exist — a pairing "works" when the phone's
  browser rendered a guarded page, on camera at checkpoint 3.
- reach config (tailscale hostname, ntfy link_base) is the owner's; the
  build reads it, never sets it.

## cold-start pointers

- RUNBOOK.md env block (cd, `uv run pytest -q` ~90s, uvicorn 8848, call-time
  store resolution via commerceos/stores.py — COMMERCEOS_DB wins first).
- required reading: AGENTS.md · .claude/agent-memory/producer/MEMORY.md
  (the cold-read walk-to-terminal + JSON-dead-end lessons apply DIRECTLY to
  the revoke button and claim redirect) · the plain-first guard test
  (tests/test_catalog_dashboard.py:240).

## test plan (the pins, named — tests/test_web_pairing.py)

1. `test_pair_page_is_localhost_only` — off-localhost GET/POST /pair → 403,
   even carrying a valid Bearer token.
2. `test_pair_mints_a_token_and_shows_the_qr_once` — localhost POST /pair →
   `<svg` + claim url + label on the page; db holds sha256 only, raw token
   absent from every row.
3. `test_claim_sets_the_cookie_and_the_phone_gets_in` — off-localhost claim
   → 303 + Set-Cookie(HttpOnly, no Secure); cookie'd client gets 200 on /
   and /approvals.
4. `test_unpaired_device_refused` — no credential → 401; wrong cookie → 401;
   the check's fourth leg.
5. `test_revoke_from_the_parts_view` — the full loop: pair → claim → 200 →
   POST /pair/revoke → row gone, label off /parts, same cookie → 401.
6. `test_bearer_header_still_passes` — regression beside
   test_web_surface.py:52.
7. `test_device_labels_render_escaped_on_parts` — hostile label, escaped
   output.
8. `test_qr_matrix_invariants` — vendored encoder self-check (square, odd
   size ≥ 21, finder corners).
9. `test_claim_with_a_bad_token_says_so_plainly` — 401 body carries plain
   words, no stack, no code identifiers.

capture script shape ([product] cold read): seeded scratch db + TestClient →
write HTML captures of /pair (form), the post-mint QR page, /parts with one
paired row, and the 401 refusal body. the producer walks these cold at
checkpoint 2; checkpoint 3 adds phone-camera photos as the live fixtures.

## open questions

- **the 7c (approver identity)** — OPEN [owner], riding since FW1/WF-approve
  (backlog.md:37-39, INDEX riding rulings). this pack builds around it: the
  phone approves as "paired-device". when the owner rules, wiring the device
  LABEL into `by` is a separate small item (C4 was folded into CW8w for
  exactly this, backlog.md:254).
- **one-time claim codes vs token-in-QR** — v1 ships token-in-QR with the
  exposure named (PACK.md risks). if the owner wants the stricter shape, it
  is a new item, not a mid-build swerve.
- **cookie lifetime** — "long-lived" (spec) is not a number. pack picks 365
  days Max-Age; the owner can shorten it with a ruling; revoke is the real
  control either way.
