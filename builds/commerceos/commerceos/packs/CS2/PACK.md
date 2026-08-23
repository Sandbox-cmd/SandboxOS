git diff --quiet 3405ad7..HEAD -- commerceos/web/app.py commerceos/gate/ledger.py commerceos/gate/gate.py commerceos/catalog/runs.py commerceos/catalog/workflows.py commerceos/stores.py tests/test_catalog_dashboard.py tests/test_workflow_runs_web.py tests/test_voice_register.py || echo "STALE — re-true before build (see RUNBOOK)"

# CS2 — the board, one store opened

## mission

the collaboration surface's second screen (spec/parts/collab-surface.md):
`GET /board/{store}` — the desk proper for one store. two zones: MY SIDE
(running work, live progress from workflow-run rows) and YOUR SIDE (waiting
tickets), receipt-in-place on any ticket, "landed today" below with
receipts, doors to catalog/money/checks/agents/record. a stopped job
renders red with what stopped, why, and what was untouched — from a real
stopped receipt, never a minted one. composes CS0's foundation (triage
tickets, fusion.css, the lints); reuses the wall's shell and shared
helpers — CS1 landed first and shipped every shared piece this pack
needs (see step 0's landed-helper map).

as-of: commit 3405ad7 · suite 539 green (zero skips) · CS0+CS1 both
landed (re-trued past the CS1 churn of app.py — see step 0)

**COLLISION LAW: collides with the other CS pack and any app.py pack —
never two in flight.**

## the backlog check (verbatim, backlog.md CS2 row)

live render: a running job's progress moves; a wait approved from the board
lands through the gate and flips zones verify-rendered; the stopped state
renders from a real stopped receipt; producer cold read SHIP-CLEAR

## model

opus — the live-progress seam is subtle (progress must be read from ledger
row states mid-run, not from the run row's items — see the ruled design),
the moves-check needs a thread-frozen real run, and the page composes five
data sources under two lint suites.

## boundaries

- **stores/dbs**: scratch dbs only (`COMMERCEOS_DB` → tmp path) +
  FakeStore monkeypatched over `writes.ShopifyClient`
  (tests/test_workflow_runs_web.py:125). `data/demostore.db` NEVER written;
  the live-render leg uses a read-only `sqlite3 .backup` copy (CS1's
  step-3 recipe).
- **gate lane**: the board adds NO approve verb. your-side singles carry
  the decisions form (POST /api/approvals/{id}, confirm required,
  app.py:1645-1649 — decisions now renders this card through
  `_change_plain`, CS1's shared renderer, so the board's own
  receipt-in-place should read the SAME helper, never a re-derived one);
  batch tickets door to /catalog/runs/{id} where the glance-approve lives
  (app.py:4403-4424). `api_resolve` and the run approve/decline endpoints
  are NOT modified.
- **writer-class**: the board READS ledger rows, workflow-run rows, the
  registry, and the health mirror; it writes nothing. workflow_runs stays
  catalog-workflows' table (runs.py:16) — the board (and its tests) never
  INSERT/UPDATE it directly; test states come from the real machinery only.
- **files**: commerceos/web/app.py (the route + zone renderers + the wall
  door flip) · tests/test_board_web.py (new) · tests/test_catalog_dashboard.py
  (ONE edit: "/board/demostore" joins the guard walk at :404-409). CS1
  already shipped every shared helper this pack needs, all living in
  app.py (see step 0) — there is no separate shared-helpers file to
  create; nothing else.
- **NO commits, NO record commands; stage never land.**

## ruled design (the builder renders, never re-derives)

- **route**: `GET /board/{store}`, guarded. three answers:
  - unknown store → 404, a plain fusion page: "no store called {name}
    here." + a door to /wall, HARDCODED (RULED: the CS pull order is
    strictly serial, CS1 lands before CS2 — the else-branch is dead by
    law). never a raw JSON dump on a person's screen.
  - known but NOT the active store (stores.active_store, stores.py:65-75)
    → an honest read-only card: the label, its onboarding state in plain
    words — the stamp map is RULED so no builder invents it:
    config → "settings written" · register → "on the roster" ·
    migrate → "database ready" · first_tick → "first heartbeat ran" ·
    first_render → "first screen rendered"; a missing stamp renders
    "not yet" beside its plain phrase — (registry row's ceremony stamps,
    stores.py:124), and the line
    "this desk speaks for {active label} — open {label} from its own desk
    to act." NO zones, NO forms — the surface speaks for one store
    (behavior 4, teletext.py:90-92); pretending to act across stores would
    aim the gate at the wrong ledger.
  - the active store → the full board below.
- **top line** (the comp's tiny bar): left "{label} · running" when any
  run is executing, "{label} · quiet" otherwise; right: the health mirror
  IF present — "health {overall_score:g} as of {measured date}" via CS0's
  `aged()` (the mirror-as-of lint's one formatter; source
  `_health()`/app.py:2670-2678, its `date` field as app.py:2777-2791 reads
  it) — else "no health check yet"; then "· {k} changes today" (executed
  records whose outcome ts is today — a real count at render, law 4).
  the mirror rides here (unlike the wall) because the board IS one store's
  desk and the mirror is the active store's audit; its store-ambiguity
  stays an open question named in context.md.
- **MY SIDE**: workflow runs with status `executing` (catalog_runs.
  list_runs, runs.py:59-66), each a blue ticket: "{feature_label} —
  {n_done} of {batch}". **the progress law**: an executing run's `items`
  json is written ONLY when the run finishes (runs.py:149-150) — mid-run
  truth lives in the LEDGER, because gate.resolve and writes.execute
  commit per record (ledger.py:242, :284). so `n_done` = count of the
  run's item record_ids whose ledger status is one of
  `executed`/`failed`/`expired` — NEVER `executing` (an in-flight item is
  not done; the trailing-by-one honesty is named in context.md) —
  computed at render, never cached. meta line: "each verified before it counts". empty my-side:
  "my hands are empty — nothing running." (first person, law 7). when any
  run is executing the page carries `<meta http-equiv='refresh'
  content='3'>` — no JS on this surface; a person watching sees the
  number move. no executing runs → no refresh tag.
- **YOUR SIDE**: heading "your side — {n} waiting" where n counts what
  the LIST shows (batches as one — the home-heading honesty law,
  app.py:1372-1383). content exactly the wall's ticket rendering — reuse
  the landed helpers directly, never re-derive them: `_wall_eyes_ticket`
  (app.py:1862-1895) / `_wall_batch_ticket` (app.py:1896-1907) build the
  eyes-first `<details>` receipt-in-place card and the one-batch-ticket
  shape already; `_change_plain` (app.py:1752-1809) is the one change
  renderer both
  /approvals and the wall already share — the board's receipt-in-place is
  a third caller of the SAME function, not a new one. empty: "nothing
  waits on you."
- **LANDED TODAY** (below the zones, group label exactly "landed today —
  each on your approve"): done runs whose `approved_ts` is today → one
  green ticket each ("a batch of {batch} {feature_label} fixes", meta
  "you approved · {counted} showed up live", door → /catalog/runs/{id})
  + executed single records whose outcome ts is today and which are not
  members of any run (outcome ts: ledger.py:275) → green ticket, receipt
  in `<details>` (who approved via `who_plain`, app.py:4095-4112; what
  landed via the shared change renderer, `_change_plain` app.py:1752-1809).
  empty: omit the group entirely — silence is the product.
- **STOPPED**: red tickets from the LANDED `_stopped_runs` (app.py:1968-1983
  — CS1 shipped it exactly as this pack assumed: latest done run per
  feature, stopped iff `errored > 0` or `failed > 0`) — call it, don't
  reimplement it. each ticket names: what stopped ("{n} of {batch} did
  not land"), why (the items' own state strings — "errored — …"
  runs.py:140, "executed, not verified — not counted" :145 — escaped,
  plain), and what was untouched ("{lapsed} lapsed, skipped — never run
  late" :131). door → the run receipt. CS1's own `_wall_stopped_ticket`
  (app.py:1908-1934) is the shape to copy (it already builds the red
  ticket from a `_stopped_runs` row via `fusion.ticket`) — the board can
  call it directly if a plain `fusion.ticket` red card is what the comp
  wants, or wrap it if the board's stopped card needs its own layout.
  renders as its own group above landed-today (law 6: stops are
  first-class, never hidden).
- **doors** (the comp's five, mapped to real pages): catalog → /catalog ·
  money → /economics · checks → /parts (the system self-report, where
  every part's health check renders — the closest true door; if the
  producer's cold read finds it dishonest, escalate rather than invent a
  page) · agents → /fleet · the record → /record.
- **the wall's store doors flip**: landed CS1's actual shape is narrower
  than earlier assumed — `_wall_doors_from_views` (app.py:2100-2114) links
  ONLY the active store's name, to /catalog (a dead door was ruled worse
  than none — coordinator ruling M4); every OTHER store's name renders as
  PLAIN TEXT, no link at all. the function's own docstring already names
  this pack: "CS2 flips them when /board/{store} exists." so CS2's job
  here is two-fold, not a simple repoint: (a) the active store's door
  moves from /catalog to /board/{name}, and (b) every other store's
  now-dead plain-text name becomes a REAL door to /board/{name} for the
  first time — turning M4's "no link" default into a true one now that
  the destination exists.
- **strings**: same laws as CS1 — triage prose capitalizes, chrome
  lowercase, no banned terms, no snake_case in visible text, record-born
  ink escaped, no new unrostered `*_LABELS`/`*_PLAIN` dict.

## step plan (M-size: 3 checkpoints)

**step 0 — preflight (no code, but already re-verified for this build —
both CS0 and CS1 are landed as of commit 3405ad7, suite 539).** CS0 and
CS1 landed; skip the `ls`/discovery — go straight to reading and reusing
the shapes below (all in commerceos/web/app.py unless noted; `_ALLOWED_STATIC`
already carries the fusion.css entry at app.py:749-750):

  - `_fusion_doc` (app.py:1848-1859) — wraps CS0's `fusion.page()`; the
    board's doc shell.
  - `_change_plain` (app.py:1752-1809) — the ONE change renderer shared by
    /approvals and the wall; the board's receipt-in-place is a third
    caller, not a new renderer.
  - `_stopped_runs` (app.py:1968-1983) — landed EXACTLY per this pack's own
    assumption (errored>0 or failed>0 on the latest done run per feature);
    call it, don't rebuild it. `_wall_stopped_ticket` (app.py:1908-1934) is
    the ticket shape built from it.
  - `_wall_store_views`/`_view_from_conn` (app.py:2043-2079 / 2007-2041) and
    `_folded_waits` (app.py:1994-2004) — the per-store gather + the
    triage-input fold; the board only needs the ACTIVE view's slice of what
    these already compute (it does not need to call `_wall_store_views` for
    every store the way /wall does — the board speaks for one store, so
    reading the active store's own `pending`/`staged`/`in_batch` directly,
    same shape as `_view_from_conn` builds, is enough; import the shape,
    don't import cross-store fan-out you don't need).
  - `_fmt_local` (app.py:1707-1725) / `_age_plain` (app.py:1729-1748) — the
    absolute-time and age renderers; use these for any timestamp the board
    shows, never a raw ISO stamp.
  - `_wall_title` (app.py:1812-1836) — the product-named title (never the
    method) for a wait; reuse for the board's your-side tickets.
  - `fusion.ticket` (commerceos/web/fusion.py:55-83) / `fusion.group_label`
    (:86-88) / `fusion.page` (:92-108) / `fusion.aged` (:43-47) — CS0's
    card/heading/shell/date-suffix primitives; `_wall_doors_from_views`
    (app.py:2100-2114) is the shape to extend for the doors-flip, not a new
    door-renderer.

verify each landed signature against this pack's own step-2/3 assumptions
before building — they were checked at re-true time (this pass) and matched
in every case; escalate only if a builder's re-read finds a real drift.

**step 1 — failing tests.** new file tests/test_board_web.py — rig from
tests/test_workflow_runs_web.py:21-31; FakeStore/seed_variant via the :18
import; the pins named in context.md, including the thread-frozen
progress test (its exact shape is ruled there — an Event-gated fake
client inside the REAL catalog_runs.approve, never a minted row). stage
the guard edit ("/board/demostore" at tests/test_catalog_dashboard.py:404-409).
run; watch them fail. **CHECKPOINT 1**: failing output + seam-map
compliance.

**step 2 — build to green.** the route and renderers per the ruled
design. **CHECKPOINT 2**: `uv run pytest -q` ≥ 539 + new pins (the count
measured at this re-true, CS0+CS1 already landed — compare against
whatever count you measure fresh at your own step 0), zero
skips; diff reviewed against the laws checklist; any file outside the
seam map is an automatic stop. run the thread test 20x
(`uv run pytest tests/test_board_web.py -q --count` equivalent loop) —
flaky is a defect, not a shrug; if it cannot be made deterministic with
the Event barrier, escalate.

**step 3 — live render + producer captures.** seeded scratch db via
uvicorn :8848: (a) arm a gtin batch, approve it with the slow fake client
harness from the test (or watch a real seeded batch of 40 execute) and
capture the board mid-run twice — the progress number MOVED between
captures; (b) approve a wait from the board → follow the road → re-render:
zones flipped, the wait now under landed-today (verify-rendered); (c) the
stopped state captured from the real errored-item run the tests built.
plus the real-data read-only backup walk (CS1's recipe) for the resting
board. **CHECKPOINT 3**: captures + producer cold read → SHIP-CLEAR;
findings block until repaired or overruled by the owner's recorded k.

## escalation triggers

the RUNBOOK's six, plus:

- landed CS0/CS1 contracts (both landed, commit 3405ad7) differ from the
  assumptions and citations in this pack — they were re-verified line by
  line at this re-true and matched in every case; a builder's own re-read
  finding real drift from what's cited here is the trigger, not a
  landed/not-landed question anymore.
- the progress test cannot be made deterministic through the real
  machinery — STOP; never write workflow_runs rows directly (writer-class
  + the minted-fixture scar, the house's twice-paid lesson).
- any impulse to modify api_resolve, the run approve/decline endpoints,
  or catalog_runs.approve's loop (e.g. "just write items mid-run") — the
  seam is read-side only; a mid-run item-write is a catalog-workflows
  design change = new backlog item.
- the "checks" door: if /parts reads dishonest as "checks" on the cold
  read, escalate the naming to the owner — do not invent a new page.
- cross-store acting: any design pull toward approving another store's
  waits from this desk — behavior 4 stop.
- a board string trips the plain-language guard or an SF1 lint — fix the
  string, never the lint.

## "done"

the RUNBOOK's five lines, plus: the backlog check ran verbatim — progress
seen moving (two live captures + the thread pin), an approve from the
board landed through the gate and flipped zones verify-rendered, the
stopped state rendered from a real stopped receipt (the errored-item run);
suite green at the step-0 count + new pins, zero skips; the guard walks
/board/demostore; producer cold read SHIP-CLEAR; captures kept with the
make note.

## risks (item-specific)

- **the progress lie (the sharpest one)**: reading an executing run's
  `items[].state` mid-run shows the STAGED states — the run row is only
  rewritten at the end (runs.py:149-150). progress read there would sit
  frozen at 0 until the batch finishes, then jump — a lying meter. the
  ledger's per-record commits (ledger.py:242, :284) are the only mid-run
  truth. this is why the pack rules `n_done` from ledger statuses.
- **sqlite across threads**: the moves-test approves on a worker thread
  with its own connection while TestClient GETs on the main thread — each
  request opens a fresh conn (`_db`, app.py:619-624) so there is no
  shared-connection hazard, but keep the worker's conn its own
  (`connect(db)` inside the thread) and join with a timeout; a hung
  barrier must fail the test, not the suite.
- **"landed today" wording**: the SF1 land-guard allows "land/landed"
  only with the owner as subject. the group label is ruled "landed today
  — each on your approve" so it stays true under a broadened lint; ticket
  meta says "you approved · …". never a bare machine-subject "landed".
  **placement (RULED — the audit named the trap)**: this label lives
  INLINE in app.py, never in a `FUSION_*_PLAIN` set — the land-guard's
  allowlist entries must start with "you", so a fusion.py placement
  would hit an unfixable lint. inlining in app.py is the design, not a
  dodge: the lint's roster covers fusion.py by construction.
- **the health mirror in tests (RULED)**: board tests monkeypatch the
  reports dir (app.py's `_REPORTS`, :2667) to a tmp dir carrying a
  fixture health-latest.json — never inherit the repo's real mirror
  (machine-dependent renders are flaky lies). the fixture's number wears
  "as of" through `fusion.aged` like the live path.
- **zone honesty**: a run flips staged→executing→done within one approve
  request — a board rendered right after shows it under landed-today,
  never a phantom "running" (compute zones from the row's CURRENT status,
  no caching, no session state).
- **double-counting**: your-side singles must exclude batch members
  (`in_batch`, the app.py:1356-1360 fold — same shape `_view_from_conn`
  builds at app.py:2007-2020) and landed-today singles must exclude run
  members — the run ticket already carries them.
- **record-born ink**: item states, intents, reasons — html_escape at
  every interpolation (1f7936e).
- **meta-refresh scope**: the refresh tag ONLY when a run is executing —
  a resting board that reloads every 3s is noise on the quiet page and
  would churn the live walk's captures.
