# part: the gate + the record

serves: O2, O4 (spec/jtbd.md)
state: draft v1 — 2026-07-11; rulings of 2026-07-18 folded. OPEN items
marked.

## purpose

one wall, one memory. the gate decides what runs now and what waits; the
ledger remembers every action, its why, its outcome. nothing above
threshold moves without the owner (O2); any action auditable in under a
minute (O4). agents stage, the owner lands — the workshop's grammar.
home: the cartridge root — Python 3.14, FastAPI, SQLite (ruled).
multi-store shape is RULED 2026-07-18 [owner]: one database and one
append-only ledger per store — "the ledger" in this part always means
this store's own.

## owns

- the action taxonomy, severity-ordered:
  - reversible — runs at once, recorded. drafts, non-critical fields, seo.
  - consequential — parks for approval. money moves (price, spend, refund),
    publishing, delisting, inventory adjustments, supplier orders.
  - fit-critical — consequential subset for safety-bearing spec claims. a
    wrong temp rating is a safety claim, not content. always human-gated.
- classification: the agent declares a class; the gate computes its own
  from the policy table and takes the stricter — no self-downgrade. field-
  and state-aware; an unknown method classifies fit-critical, gated.
- per-function thresholds, stored as config: auto-approve classes, money
  thresholds. moved only by the owner; every move recorded (behavior 6).
- the append-only ledger (ratified as built — RULED 2026-07-18 [owner]:
  own ledger with DB triggers, one-use handles, and the events feed, same
  stage/approve grammar as the workshop), one record per action: id
  (minted at gate time; the idempotency key) · ts · agent · function ·
  action_type · intent ·
  rationale · impact (money, scope, risk) · provenance (cite or mark
  unverified) · proposal (the exact connector call, args, args hash) ·
  status (pending → approved → executing → executed | failed; or rejected
  | expired) · expires_at · gate (decision, by, ts) · outcome. no delete
  path; only the single-shot outcome fill and one-time gate resolve mutate.
- capability handles: approval mints a one-use handle keyed to the ledger
  id, bound to the exact call by the args hash, carrying the expiry. one
  law at the connector: no valid handle, no write — consumed on use.

## exposes

- gate check API (in-app, for connectors and agents): submit a proposal →
  allow (reversible) or parked pending. no approve verb on this API —
  v0's hard invariant re-keyed: headless cannot approve its own action.
- approval queue feed for the web surface (SSE): intent, why-now, impact,
  provenance, expiry countdown. phone push on consequential items —
  self-hosted ntfy, notify-only; approval never rides the push (RULED
  2026-07-18 [owner]).
- ledger query API: by function, agent, product, status, day, kind —
  "why did X happen" in under a minute, and the per-function track record.

## consumes

- proposals from agents (part 4) and the catalog loop (part 5): every
  world-write arrives as a proposal, never as a direct call.
- approvals and rejections from the owner on the web surface (part 7),
  phone included. plus the store's policy config: thresholds, field lists.

## mechanism vs config

- mechanism (store #2 uses unchanged): classifier, stricter-of-two, gate
  decision, ledger + append-only enforcement, handles, queue, expiry.
- config (store #2 tunes): threshold values per function, auto-approve
  classes, handle lifetimes (RULED 2026-07-18 [owner]: 3600s default /
  1800s money moves — the current policy-table values; the owner may
  move them anytime, every move recorded), the fit-critical field list —
  this store starts from v0's set (temp_rating, load_limit, weight_limit,
  waterproof_rating, ip_rating, certifications, safety_rating,
  material_spec).
- method default classes ship with the connectors (a price change is
  consequential in any store); field overrides are the store's file.

## behavior

1. reversible pass-through: record minted approved, handle minted and
   consumed in one motion, connector writes, outcome filled. never silent.
2. consequential park-and-queue: record minted pending with an expiry,
   enters the queue, push sent. the proposing agent does not wait and
   cannot resolve its own gate — it files and moves on.
3. approve → mint → execute: the owner approves on the web surface;
   approval mints the one-use handle; the executor runs the exact stored
   proposal; the connector validates (approved, unexpired, unused, method
   and args-hash match), consumes it, writes the world, fills the outcome.
4. reject: status → rejected, reason stored, nothing executes. the
   disposition is on the record for the agent's next read.
5. expiry: pending past expires_at flips to expired — no longer approvable
   or executable. a stale approval lapses rather than fires on changed
   conditions; still wanted means re-proposed with current numbers.
6. threshold move: owner-only, and itself a recorded action on this same
   ledger — old value, new value, by whom, why. never silent.
7. the anti-bypass wall — a design requirement, not an afterthought. the
   gate holds only if the gated connectors are the only write path in an
   agent's hands. v0's red team proved the failure: its gate hook matched
   only its own tools — any other tool that could mutate the store
   (another Shopify MCP's mutate calls, raw HTTP from Bash) walked past
   gate, ledger, and handle. the fix lands at fleet-wiring (part 4): the
   restricted tool grant — gated connector tools plus reads, no raw Bash,
   no ungated admin tools. this part ships the check; the fleet enforces.

## renders

self-report into the web surface (part 7) — if it runs, it renders:
- queue: depth, oldest pending age, items expiring soon.
- decisions: counts by status, class, and function, over time.
- per-function threshold card — track record beside the control: approval
  rate, reversals, time since last reversal. the evidence for widening.
  recent threshold moves beneath, with who and why.

## checks

runnable tests in the repo; v0's red-team battery recreated, not trusted:
- a consequential write with no approval is refused and parked pending.
- an approved handle executes exactly once; a replay is refused.
- an expired approval does not execute; the record reads expired.
- a bypass attempt via a non-gated path is denied: the fleet-grant test
  fails on raw Bash or any ungated mutate-capable tool in an agent's hands.
- a self-downgrade attempt is gated at the stricter class and flagged;
  an unknown method classifies fit-critical and gates.
- a method or args mismatch against a valid handle is refused.
- a threshold move appears on the ledger as its own record.
- the ledger admits no delete or rewrite: only the outcome fill and the
  gate resolve mutate, each exactly once.

## v0 salvage

mine (built and red-team-tested in slice one):
- policy.py: one classifier shared by gate and connector so they never
  disagree; stricter-of-two; field/state overrides; unknown-method fails
  high; args hash binds to world-args only (metadata stripped).
- gate_core.py: reads free; deny-and-park, never approve-before-decision;
  expiry set at gate time; notify when no human is present.
- ledger.py: append-only by construction; id-at-gate-time as idempotency
  key; the jsonl audit mirror (cheap, git-diffable — keep).
- policy-table.json: the shape (functions: auto_approve + money_threshold;
  methods: default + field/state overrides; unknown_method_class) and the
  fit-critical field list as this store's starting config.
do not port: the dead kernel's wiring — PreToolUse/PostToolUse hooks,
sentry siblings, SBOS_RUN_ID "away" keying, statusline notify, the .mind/
ledger path (the gate is now an in-app API; where the approve verb lives
enforces headless-cannot-approve) · the Bash content-scan seatbelt (v0
called it blunt; the grant is the wall) · replay-tolerant handles (v1:
one-use, consumed transactionally, rows in SQLite, not loose JSON files).

## open

- own ledger vs riding the workshop's record — RULED 2026-07-18 [owner]:
  ratified as built. own append-only ledger (DB triggers, one-use
  handles, events feed), same stage/approve grammar as the workshop;
  revisit only if SandboxOS exposes its record as a library.
- expiry values — RULED 2026-07-18 [owner]: 3600s default, 1800s for
  money moves — the current policy-table values. the owner may move them
  anytime; every move is recorded (behavior 6).
- the phone approve path — RULED 2026-07-18 [owner]: QR pairing from the
  desktop surface, a long-lived revocable token, over tailscale. push is
  self-hosted ntfy, notify-only; approval lives solely on the
  authenticated web surface.
- OPEN by design (until ads/pricing money moves exist): money
  defense-in-depth below the app — per-agent caps at the payment rail,
  so an out-of-policy charge dies at the network even if the app layer
  were beaten. the proposal stands; decided when real money moves.
