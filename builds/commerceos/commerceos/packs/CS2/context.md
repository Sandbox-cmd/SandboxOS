# CS2 — context (re-trued against the repo at 3405ad7 · suite 539 green,
zero skips · CS0+CS1 both landed)

## seam map (every file the build touches or reads, refs read fresh)

| file | what | refs |
|---|---|---|
| commerceos/web/app.py | `api_resolve` — the only approve verb; your-side forms post here; NOT modified | :1489-1585 (confirm wall :1520-1521 · flash+redirect to /approvals :1573-1584 · JSON answer :1585) |
| commerceos/web/app.py | the run preview + its approve/decline — the doors batch tickets and receipts open to; NOT modified | view :4327-4400 (status branches: staged :4343 · lapsed :4362 · rejected :4367 · done receipts :4372-4378) · approve :4403-4424 · decline :4427-4447 |
| commerceos/web/app.py | `catalog_run` — how a batch is armed from a surface (reversible holds, one waiting batch per front) | :4038-4068 |
| commerceos/web/app.py | the batch-fold arithmetic (members leave the singles list) | :1356-1360 (home) · :1593-1599 (decisions) · same shape again at `_view_from_conn` :2007-2020 (the wall's per-store fold — the board reads the active store's own version of this) |
| commerceos/web/app.py | `who_plain` — the approver in a person's words for landed receipts | :4095-4112 · `_who` :4115-4122 |
| commerceos/web/app.py | `_health` — the mirror the board's top line reads; how /catalog reads its date | :2670-2678 · :2777-2791 |
| commerceos/web/app.py | plain-word helpers · `_db`/`_guard` · `_ALLOWED_STATIC` · escape import | `feature_label` :64 · `action_type_label` :235 · `intent_plain` :1670 · `when_plain` :1683 · `_db` :619-624 · `_guard` :633-634 · `_ALLOWED_STATIC` :749-750 (fusion.css already listed — CS1 landed it) · escape import :13 |
| commerceos/web/app.py | **CS1-landed shared helpers, NEW material this pack composes with instead of rebuilding** — the wall's own render layer, all reusable as-is | `_fmt_local` :1707-1725 · `_age_plain` :1729-1748 · `_change_plain` :1752-1809 (the ONE change renderer, shared by /approvals and the wall) · `_wall_title` :1812-1836 · `_fusion_doc` :1848-1859 (wraps `fusion.page()`) · `_wall_eyes_ticket` :1862-1895 · `_wall_batch_ticket` :1896-1907 · `_wall_stopped_ticket` :1908-1934 (built from `_stopped_runs`) · `_foreign_line`/`_wall_foreign_ticket`/`_wall_foreign_batch` :1935-1967 (not needed by the board — single-store, no cross-store rendering) · `_stopped_runs` :1968-1983 · `_calm_line` :1986-1991 (not needed by the board) · `_folded_waits` :1994-2004 · `_view_from_conn` :2007-2041 · `_wall_store_views` :2043-2079 · `_wall_doors_from_views` :2100-2114 (the shape to extend for the doors-flip) · `wall` route :2117-2201 (reads `_wall_store_views`, `triage.triage`, the h2+.sub split — copy the composition pattern, not the route) |
| commerceos/catalog/runs.py | THE progress seam: statuses staged→executing→done\|rejected (docstring :12-14) · `approve` flips to executing then loops per item, items json written only at the END | schema :28-41 · `list_runs` :59-66 · `_shape` (live/lapsed render truth) :69-85 · `approve` :100-154 (executing flip :122-124 · per-item resolve+execute :125-141 · isolation :138-141 · item states :131,140,145 · final items/outcome write :149-150) · `reject` :157-181 · owner note :16 — UNCHANGED since 888de9c, file untouched by CS0/CS1 |
| commerceos/gate/ledger.py | why mid-run progress is readable: per-record commits | `resolve_gate` commit :242 · `fill_outcome` commit :284, outcome ts :275 · `pending_queue` :342-347 · `query` (status/day filters) :317-334 — UNCHANGED since 888de9c |
| commerceos/gate/gate.py | `resolve` — expiry wall + handle mint; the road every approve walks | :120-150 — UNCHANGED since 888de9c |
| commerceos/catalog/workflows.py | `run_feature` hold=True stages parked + groups the run; per-item isolation on the apply leg | :440-526 (hold law :449-453 · isolation :497-503 · run creation :522-525) — UNCHANGED since 888de9c |
| commerceos/stores.py | `active_store` (the one store this desk speaks for) · `load_registry` · ceremony stamps for the non-active card | :65-75 · :38-57 · :111-124 — UNCHANGED since 888de9c |
| commerceos/web/teletext.py | behavior 4 in masthead's docstring ("the store the surface speaks for, always — RULED"); the chrome the board must NOT wear | :88-103 — UNCHANGED since 888de9c |
| commerceos/web/triage.py, fusion.py, static/fusion.css | CS0's landed foundation — LANDED, real repo lines now (not a forward contract) | `triage.triage()` triage.py:55-98 (stopped clause: `_stopped_clause` :44-52, confirmed " {N} job{s} stopped." — no "overnight") · `fusion.aged` fusion.py:43-47 · `fusion.ticket` :55-83 · `fusion.group_label` :86-88 · `fusion.page` :92-108 · `static/fusion.css` (allow-listed at app.py:749-750) · lints: tests/test_sf1_lints.py |
| packs/CS1/PACK.md | CS1 landed FIRST and shipped every shared piece (`_fusion_doc`, `_change_plain`, `_stopped_runs`, `_wall_title`, `_fmt_local`/`_age_plain`, `_folded_waits`, `_wall_store_views`, the fusion.css allow-list entry) — all cited above with real app.py line numbers now; this pack composes with them, ships nothing shared itself | packs/CS1/PACK.md (ruled design) — landed shape confirmed at app.py, see the row above |
| tests/test_catalog_dashboard.py | the plain-language guard; "/board/demostore" joins the walked list | :337-414 (paths :404-409, now opening with "/wall" then "/board/demostore" to add · banned :400-402 · snake regex :403) — line numbers unchanged (CS1's "/wall" edit was same-line content, not a line-count change) |
| tests/test_board_web.py | NEW — the pins (below) | — |

## prior art (copy these shapes)

- **the web rig**: tests/test_workflow_runs_web.py:21-31 (COMMERCEOS_DB
  pin + TestClient) · `_arm` :34-39 (arming a held gtin batch from the
  surface) · ShopifyClient monkeypatch :122-125 · FakeStore import :18 ·
  the full glance-approve round trip :122-140 (including the who_plain
  assertion pattern).
- **staging a parked consequential wait**: tests/test_catalog_delist.py
  `_submit_delist` :93-101 · FakeClient :31-53 (scripted productUpdate +
  status readback; the forced-disagree mode for an unverified leg).
- **fold honesty**: tests/test_workflow_runs_web.py:65-82.
- **seeding at scale** (the producer's seed-scale scar): seed_variant
  loops for a 40-item queue — a 2-item batch hides the progress lie;
  the moves-pin uses a batch big enough that "n of 40" visibly climbs.

## binding laws

- the seven carried laws (spec/parts/collab-surface.md): the board
  implements 1 (one gesture, same gate), 2 (receipt in place), 3 (the
  health number wears its measured date via CS0's `aged` — the ONLY
  mirror number on the board), 4 (every count computed at render — the
  progress number is the sharpest case), 5 (one focus: the zones read
  top-to-bottom, depth on the ticket), 6 (stops are first-class red
  tickets with reasons), 7 (my side speaks as I).
- the plain-language guard walks /board/demostore once listed.
- the three SF1 lints (tests/test_sf1_lints.py, CS0's) bind every fusion
  string set; the land-guard's spirit binds the landed-today wording
  ("landed today — each on your approve").
- the gate: no new approve verb; confirm required; batch approve stays
  the reversible lane only (runs.py:116-118).
- writer-class: workflow_runs belongs to catalog-workflows (runs.py:16);
  the board and its tests never write it directly.
- append-only ledger · the escape law (1f7936e) · verify rendered, never
  files-exist.

## cold-start env

    cd the cartridge root
    uv run pytest -q                       # measure the count FIRST (539 at 3405ad7, zero skips — CS0+CS1 already landed)
    # CS0 and CS1 are BOTH landed as of this re-true (commit 3405ad7) — the
    # ls/grep discovery below is no longer a question, just a sanity check:
    ls commerceos/web/triage.py commerceos/web/fusion.py \
       commerceos/web/static/fusion.css tests/test_sf1_lints.py   # CS0 — present
    grep -n "fusion.css" commerceos/web/app.py                    # CS1's allow-list entry — app.py:749-750
    grep -n "/wall" commerceos/web/app.py                         # CS1's route — app.py:2117 (its store doors to flip: _wall_doors_from_views, app.py:2100-2114)
    # live surface (step 3): COMMERCEOS_DB=<scratch> uv run uvicorn commerceos.web.app:app --port 8848

required reading: AGENTS.md · .claude/agent-memory/producer/MEMORY.md ·
packs/RUNBOOK.md · spec/parts/collab-surface.md (fully) ·
packs/CS0/PACK.md + context.md · packs/CS1/PACK.md (the shared pieces +
collision law) · reports/collab-surface/fusion.html state 4 (the ruled
board comp: zones, receipt-in-place, landed today, the five doors).

## test plan (the pins, named)

new file tests/test_board_web.py; rig per prior art. active store in the
rig is "demostore" (the registry default resolves it; COMMERCEOS_DB
overrides its db to scratch — stores.py:28-31).

1. `test_unknown_store_answers_plainly` — GET /board/nope → 404, plain
   words ("no store called"), no traceback, no JSON dump.
2. `test_a_store_that_is_not_this_desks_renders_readonly` — GET
   /board/scaffold (real registry's second store) → the label, plain
   ceremony words, "this desk speaks for" line; NO approve form, NO
   zones markup.
3. `test_the_two_zones_render` — arm a gtin hold batch + park a delist:
   your side shows "your side — 2 waiting" (the batch as ONE + the
   single), my side reads "my hands are empty — nothing running."
4. `test_a_running_jobs_progress_moves` — THE moves pin, real machinery
   only: seed a 40-variant gtin queue; arm the hold batch; build a
   BarrierStore (wrapping FakeStore) that blocks on a threading.Event
   at the start of item 15's WRITE — count completed items, never raw
   graphql calls: each gtin item is TWO calls, the write
   (writes.py:228-231) + the readback (:234-235), so 14 items done =
   28 calls seen; monkeypatch writes.ShopifyClient; run
   `catalog_runs.approve(conn2, run_id, feat, by="localhost")` on a
   worker thread with its OWN `connect(db)`; wait until the barrier is
   reached (a second Event set by the client); GET /board/demostore →
   my side reads "14 of 40" and the page carries the refresh tag;
   release the barrier; join(timeout=10) — a timeout fails the test;
   GET again → the run is under landed-today, no refresh tag. progress
   came from ledger statuses (the per-record commits), which is exactly
   what this pin proves.
5. `test_a_wait_approved_from_the_board_flips_zones` — FakeClient over
   writes.ShopifyClient; POST the your-side single's form → 303 (the
   existing road); re-GET the board: your side no longer lists it,
   landed-today carries its green ticket with "you, at this desk" via
   who_plain and the verified receipt in place; the ledger record reads
   executed with verified_rendered.
6. `test_the_stopped_state_renders_from_a_real_stopped_receipt` — approve
   a held batch with a client that raises on one item (runs.py:138-141
   writes "errored — …" through the real loop) → the board shows the red
   ticket: the feature named, "1 of 2 did not land", the why (the state
   string, escaped), the untouched facts; doored to /catalog/runs/{id}.
7. `test_landed_today_excludes_run_members_from_singles` — after pin 5
   and a clean batch approve: one green batch ticket + one green single;
   no member record renders twice.
8. `test_record_born_ink_renders_escaped` — an intent carrying `<b>`
   appears only escaped on the board.
9. `test_the_doors_open_real_pages` — the five doors' hrefs are
   /catalog, /economics, /parts, /fleet, /record and each GETs 200
   (dead-door law).

plus the ONE edit to tests/test_catalog_dashboard.py:404-409
("/board/demostore" joins the walk). CS1 IS landed, and it already carries
its own doors pin, tests/test_wall_web.py:303-325
(`test_only_the_active_store_door_is_a_link` — confirms today's landed
shape: `<a href='/catalog'>Demo Store</a>` for the active store,
`<span>Scaffold</span>` plain text for the other, with the docstring's own
note "CS2 flips them when /board exists"). this pack's new
wall-door-flip pin (in tests/test_board_web.py or amending that CS1 test)
must assert the POST-flip shape: `<a href='/board/demostore'>Demo Store</a>`
and `<a href='/board/scaffold'>Scaffold</a>` — BOTH now real links,
neither plain text.

## open questions (honesty — escalation triggers, not guesses)

- **CS0/CS1 drift**: RESOLVED at this re-true — both landed at 3405ad7,
  every reference above now cites real app.py/triage.py/fusion.py lines
  (no more forward contracts). if the builder's own session diffs further
  past 3405ad7 before building, re-run this same re-true pass first — packs
  are frozen thinking; the landed diff always wins. (the earlier working
  note about a `Triage.batchable` field is now moot: the landed `Triage`
  dataclass carries `.stopped`, confirmed at triage.py:36-41.)
- **the health mirror is repo-global** (reports/health-latest.json — no
  store name in the file, app.py:2670-2678). the board shows it as the
  active store's because the audit runs against the active store's db,
  but nothing enforces that provenance. if the cold read flags it, the
  honest fix (a store name inside the mirror) is an audit-side backlog
  item, not this pack's surgery.
- **"checks" → /parts** is this pack's mapping (the comp's door is a
  placeholder `#`; /parts is where every part's self-report and health
  check renders). if it reads wrong on the cold read, the naming goes to
  the owner.
- **mid-run zone flicker**: between an item's gate.resolve commit and its
  fill_outcome commit, a record is briefly `approved`/`executing` — the
  ruled n_done counts only executed/failed/expired, so the number can
  trail by one item mid-write. honest (it counts finished items), but
  named here so the builder doesn't "fix" it into a lie.
- **the refresh cadence (3s)** is ruled to make "progress moves" true
  for a person watching without JS; if the owner wants SSE (the
  /api/events feed exists, app.py:703-719), that is a later round.
