git diff --quiet 888de9c..HEAD -- commerceos/web/app.py commerceos/gate/ledger.py commerceos/gate/gate.py commerceos/catalog/runs.py commerceos/stores.py tests/test_catalog_dashboard.py tests/test_workflow_runs_web.py tests/test_voice_register.py || echo "STALE — re-true before build (see RUNBOOK)"

# CS1 — the wall, the quiet home

## mission

the collaboration surface's first screen (spec/parts/collab-surface.md, the
fusion: quiet page × desk): a new page at `/wall` where the owner sits down.
the triage sentence names the size of the day, waiting work renders as
tickets (individual for your-eyes-first; ONE honest batch ticket per held
reversible run, riding the existing batch-approve machinery), one calm line
per store from the registry, doors. an empty day renders "Nothing needs
you." honestly. the wall opens BESIDE the current home — the spec's open
question rules the transition, so `/` is untouched. CS0's foundation
(triage brain, fusion render helpers, fusion.css, the three lints) is
composed here, never re-derived.

as-of: commit 0ea5b63 (CS0 landed) · suite 527 green (zero skips) · depends on CS0, met
landed (see step 0)

**COLLISION LAW: collides with the other CS pack and any app.py pack —
never two in flight.**

## the backlog check (verbatim, backlog.md CS1 row)

live render against real data: the sentence states the real wait count;
each ticket opens to its receipt; approving a ticket runs the existing gate
road end to end; producer cold read SHIP-CLEAR

## model

opus — composing three new modules into the app's routing seam, a move-only
refactor of the approvals card renderer, and a new register's first routed
page under two lint suites; more judgment than CW8w's one branch.

## boundaries

- **stores/dbs**: scratch dbs only (`COMMERCEOS_DB` → tmp path in every
  test) + FakeStore/FakeClient monkeypatched over `writes.ShopifyClient`
  (the tests/test_workflow_runs_web.py:125 pattern — that line uses
  FakeStore; FakeClient is test_catalog_delist.py:31-53). `data/<store>.db` is live
  data — NEVER written. the live-render leg reads it via a
  read-only backup copy (step 4), never the live file as `COMMERCEOS_DB`.
- **gate lane**: the wall adds NO approve verb. eyes-first tickets carry
  the exact per-item form the decisions page carries (POST
  /api/approvals/{id}, confirm required — app.py:1675-1679); a batch ticket
  doors to the existing run preview (/catalog/runs/{id}, app.py:3837) where
  the one glance-approve already lives. `api_resolve` (app.py:1486-1582) is
  NOT modified — its redirect lands on /approvals with the flash, and that
  IS the existing gate road the check names. wanting to change its redirect
  target is an automatic stop.
- **writer-class**: the wall READS ledger.pending_queue / catalog_runs
  rows / the stores registry; it writes nothing. cross-store counts open
  other stores' dbs read-only (`sqlite3.connect(f"file:{path}?mode=ro",
  uri=True)`) — mode=ro enforces the never-written law mechanically.
- **files**: commerceos/web/app.py (the route + shell + the move-only card
  refactor + `_ALLOWED_STATIC`) · tests/test_wall_web.py (new) ·
  tests/test_catalog_dashboard.py (ONE edit: "/wall" joins the guard-walk
  list at :404-409). nothing else.
- **NO commits, NO record commands; stage never land** — the orchestrator
  owns close-out.

## ruled design (the builder renders, never re-derives)

- **route**: `GET /wall`, guarded (`_guard(request, conn)` — the convention
  every page follows, app.py:631-632). `/` is untouched.
- **the shell**: the wall does NOT use `_page`/teletext (`tt.masthead`
  app.py:732 carries the broadcast fiction the fusion register supersedes
  FOR THIS SURFACE — spec "the register"). a small `_fusion_doc(title,
  inner)` in app.py emits `<!doctype html>` + viewport meta + `<link
  rel='stylesheet' href='/static/fusion.css'>` + the inner html — UNLESS
  CS0's landed `fusion.page()` already returns a full document (verify at
  step 0; if it does, use it and skip `_fusion_doc`). top tiny bar: left
  "commerceos", right the day+time lowercase ("thursday 10:30" shape).
- **static**: add `"fusion.css": "text/css"` to `_ALLOWED_STATIC`
  (app.py:747) if the other CS pack hasn't already — CS0 never touches
  app.py, so the first CS pack in wires it.
- **the sentence**: `triage(ledger.pending_queue(conn),
  stopped=_stopped_runs(conn))` — CS0's contract (packs/CS0/PACK.md "the
  ruled contracts"): `triage(waits, stopped=()) -> Triage` with `.sentence
  .eyes_first .routine .stopped`. render `.sentence` VERBATIM as the page's
  one heading. never recount, never rephrase — the sentence and the tickets
  come from the same rows, so they cannot disagree.
- **`_stopped_runs(conn)`** (new helper, ~10 lines): for each feature, the
  LATEST done workflow run (catalog_runs.list_runs, runs.py:59-66); it is
  stopped iff its outcome shows `errored > 0` or `failed > 0` (the per-item
  isolation writes those states — runs.py:138-145). a stopped job stays on
  the wall until a newer clean run of the same feature lands — self-
  clearing, computed at render (law 4), no invented time window.
- **tickets**: rendered through CS0's `fusion.ticket()` (edge enum
  waiting/running/stopped/done — CS0's contract). eyes-first rows (each of
  `.eyes_first`) render individually, amber edge: title
  `intent_plain(r["intent"], 70)` (app.py:1700), meta
  `action_type_label(...)` + "waits until " + `when_plain(r["expires_at"])`
  (app.py:233, 1713). the receipt opens IN PLACE via `<details>` (no JS on
  this surface), body = `_change_plain(conn, r)` — the move-only extraction
  of the decisions page's per-method change rendering (app.py:1630-1669 +
  `_seo_approval_card`'s body, app.py:3692) so the wall and /approvals read
  the SAME receipt. inside the details, the per-item approve/reject form,
  verbatim shape app.py:1675-1679.
- **the batch ticket**: `.routine` rows that are members of a staged run
  (membership exactly as home computes it — app.py:1353-1357) fold into ONE
  ticket per staged run: title "a batch of {live:,} {feature_label} fixes",
  meta "one glance approves the lot", door → `/catalog/runs/{id}`. a
  reversible pending row in NO staged run (rare — reversible submits
  without hold execute immediately, workflows.py:493) renders as an
  individual amber ticket with the same form.
- **stopped tickets**: each `_stopped_runs` row renders red: title
  "{feature_label} stopped", meta names what stopped and why from the
  items' own state strings ("errored — …", "executed, not verified — not
  counted", runs.py:140,145), plus what was untouched ("{lapsed} lapsed,
  skipped — never run late"). every record-born string through
  `html_escape` (the 1f7936e law). door → `/catalog/runs/{id}` (the full
  receipt).
- **empty day**: zero waits and zero stopped → the sentence IS "Nothing
  needs you." (triage's own output) + the calm lines + doors. no empty
  ticket markup, no placeholder card.
- **one calm line per store**: for each registry row
  (stores.load_registry, stores.py:38-57): the active store
  (stores.active_store, :65-75) reads counts from `conn`; any other store
  resolves its db (stores.resolve, :78-96) and opens read-only. line shape:
  "{label} — {n} waiting on you · {m} running · {k} changes today" (counts:
  live pending_queue length with batches folded as home folds them; runs
  status executing; executed records whose outcome ts is today —
  ledger.fill_outcome stamps it, ledger.py:275). db file missing → "{label}
  — nothing set up yet". any read error → "{label} — couldn't read its
  numbers right now" (plain, never a traceback — the app.py:2222-2228
  instinct). mirror numbers (health) do NOT ride the wall — the health
  mirror (reports/health-latest.json, app.py:2190-2198) is repo-global and
  store-ambiguous; putting it on a multi-store line would lie (open
  question, context.md).
- **doors**: one door per store label → `/catalog` (the store's operations
  home TODAY — `/board/<name>` does not exist until CS2 lands and flips
  these; a door must open a real page, the voicer's law) + "the record" →
  `/record`.
- **"changes today" clock (RULED — the audit named the trap)**: today =
  the UTC day, computed by prefix-matching the OUTCOME ts (the ISO string
  ledger.fill_outcome stamps, ledger.py:275) against today's UTC date.
  NEVER ledger.query's `day=` filter — it filters submission ts, the
  wrong clock for "changes made today". the surface just says "today";
  localizing is a later ruling, not yours.
- **`_fusion_doc` title (RULED)**: `<title>commerceos</title>` on the
  wall. the board's title is CS2's business.
- **the wall writes nothing (RULED)**: the handler NEVER calls
  `_refresh_reports` or any writer — home's shape refreshes report rows;
  copying that pattern here violates this surface's writer-class line. a
  GET of /wall leaves every file and table byte-identical.
- **comp divergence, ruled in the pack's favor**: the comp's heavy-day
  state shows "health 76.1" ON the wall; this pack forbids any mirror
  number there and pin 7 enforces it. when you hit that pin, the pack
  wins — do not treat it as a comp bug or an excuse to weaken the pin.
- **strings**: the triage sentence is prose and capitalizes as English
  (CS0's ruling); ALL other wall chrome is lowercase. no word from the
  guard's banned list, no snake_case identifier in visible text
  (tests/test_catalog_dashboard.py:400-403). any new module-level dict in
  app.py named `*_LABELS`/`*_PLAIN` MUST join the roster in
  tests/test_voice_register.py:29-51 (the convention guard at :61-68 fails
  otherwise) — prefer inline strings or a non-convention name for
  wall-only chrome.

## step plan (M-size: 3 checkpoints)

**step 0 — preflight (no code).** confirm CS0 landed: `ls
commerceos/web/triage.py commerceos/web/fusion.py
commerceos/web/static/fusion.css tests/test_sf1_lints.py` — any missing is
an automatic stop (dep not met). read CS0's landed triage/fusion signatures
against this pack's assumptions (Triage fields; whether `fusion.page()`
emits a full document; the ticket edge enum). a mismatch = re-true this
pack's ruled design against the LANDED contract before writing a line.
check whether `_ALLOWED_STATIC` already carries fusion.css (the other CS
pack may have landed first).

**step 1 — failing tests.** new file tests/test_wall_web.py — rig copied
from tests/test_workflow_runs_web.py:21-31 (COMMERCEOS_DB env pin +
TestClient), FakeStore/seed_variant imported from
tests/test_catalog_workflows.py as :18 does, and
`monkeypatch.setattr(stores, "REPO_ROOT", tmp_root)` with a crafted
two-store registry for the calm-line pins. the pins are named in context.md
("test plan"). also stage the guard edit: "/wall" joins the walked list
(tests/test_catalog_dashboard.py:404-409). run; watch them fail on the
missing route. **CHECKPOINT 1**: failing-test output + every touched file
inside the seam map.

**step 2 — build to green.** `_fusion_doc` (or CS0's page), the
`_ALLOWED_STATIC` entry, `_change_plain` extracted move-only (the
/approvals body at app.py:1630-1669 calls the helper afterward — its
existing pins in tests/test_delist_web.py, test_supplier_form.py,
test_seo_feature_web.py must stay green untouched), `_stopped_runs`, the
`/wall` route per the ruled design. **CHECKPOINT 2**: `uv run pytest -q` ≥
508 + the new pins, zero skips; diff reviewed against the RUNBOOK laws
checklist; any file outside the seam map is an automatic stop.

**step 3 — live render against real data + producer captures.** back up
the real db read-only to scratch: python —
`src = sqlite3.connect("file:data/demostore.db?mode=ro", uri=True);
dst = sqlite3.connect(scratch); src.backup(dst)` (no write, no WAL churn on
the source). boot `COMMERCEOS_DB=<scratch> uv run uvicorn
commerceos.web.app:app --port 8848`. walk: /wall — the sentence's count
equals the db's true live wait count (compute it independently via
pending_queue in a shell); open a ticket's receipt; approve one (through
FakeClient? NO — no store client may exist against real-data scratch:
approve a record whose method needs no store, or seed one; if none exists,
run the approve leg on the seeded test-db walk instead and say so in the
note). capture the wall empty-day state on a fresh scratch db too. captures
past the fold (the producer's seed-scale scar: a 3-product fixture hides
at-scale lies — capture the real-data wall, not a toy). **CHECKPOINT 3**:
captures + the producer cold read → SHIP-CLEAR; findings block until
repaired or overruled by the owner's recorded k.

## escalation triggers

the RUNBOOK's six, plus:

- CS0 not landed, or its landed contracts differ from this pack's
  assumptions (triage signature/fields, fusion.page shape, edge enum).
- any impulse to touch `/` (the home route) — the spec's open question
  rules the wall opens BESIDE it; replacing home is an owner ruling.
- any impulse to modify `api_resolve` (its redirect, its shape) — the one
  approve door is not this pack's to reshape.
- the move-only `_change_plain` extraction breaks any existing approvals
  pin — stop and re-cut the seam; never adjust the old pins to fit.
- a wall string trips the plain-language guard or an SF1 lint — fix the
  string, never the lint; if the lint itself seems wrong, escalate with
  the string as evidence.
- the health mirror's store-ambiguity wants fixing — that is a new backlog
  item, never a side-quest (pull rule 3).

## "done"

the RUNBOOK's five lines, plus: the backlog check ran verbatim — sentence
count proven against the real wait count on the live scratch surface,
receipt-in-place seen, one approve walked the existing gate road end to end
(TestClient pin + live where the boundary allows); suite ≥ 508 + new pins,
zero skips; the guard walks /wall; producer cold read SHIP-CLEAR (the row
demands it); captures kept with the make note.

## risks (item-specific)

- **the sentence lying**: the ONLY way the sentence and the tickets agree
  forever is one source — both from the same `pending_queue` snapshot in
  the same request. never call pending_queue twice in the handler (a row
  could lapse between calls).
- **double-counting batches**: home's own lesson (app.py:1350-1357) — a
  held batch's members are IN pending_queue. the sentence counts them
  individually by design ("Eight are routine and can go together"), but
  the ticket list must fold them or the wall shows a hundred cards. the
  fold set is `in_batch` exactly as home builds it.
- **record-born ink**: intents, rationales, item states are stored text —
  every one through html_escape before markup (regression precedent
  1f7936e; CS0's fixture pins the same law).
- **the guard's snake regex** (tests/test_catalog_dashboard.py:403):
  visible text only, so hrefs are safe — but a raw feature key or method
  name in a ticket body fails the suite. labels via feature_label /
  method_label / action_type_label only.
- **cross-store reads under COMMERCEOS_DB**: the env override wins for
  EVERY store name (stores.py:28-31, 84-86) — in tests all registry rows
  resolve to the scratch db and the calm lines show identical counts.
  that's the resolver's law, not a bug; the crafted-registry rig makes the
  pins deterministic.
- **voice-register roster**: a new `*_LABELS`/`*_PLAIN` dict in app.py
  fails tests/test_voice_register.py:61-68 unless rostered — and rostered
  values must start lowercase. the triage sentence never lives in such a
  dict (it is CS0's, and it is prose).
