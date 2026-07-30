# CS1 — context (verified against the repo at 888de9c)

## seam map (every file the build touches or reads, refs read fresh)

| file | what | refs |
|---|---|---|
| commerceos/web/app.py | `_page` — the teletext frame the wall must NOT wear; its docstring carries the casing law ("lowercase chrome throughout; UPPERCASE only for the one slap") | :725-743 |
| commerceos/web/app.py | `_ALLOWED_STATIC` + `/static/{name}` — the vetted allow-list fusion.css must join | :746-758 |
| commerceos/web/app.py | home (`/`) — the surface the wall opens beside; the batch-fold arithmetic to copy (staged runs, `in_batch`, singles) | :1337-1454 (fold :1350-1357 · heading honesty :1369-1380 · lapsed card :1397-1404) |
| commerceos/web/app.py | `api_resolve` — the system's only approve verb; NOT modified; the wall's forms post here | :1486-1582 (confirm wall :1517-1518 · gate.resolve :1520 · flash+redirect :1570-1581) |
| commerceos/web/app.py | `approvals_view` — the per-item card whose change-rendering moves into `_change_plain` (move-only) | :1585-1681 (method renderings :1630-1669 · the form shape :1675-1679) · `_seo_approval_card` :3692 |
| commerceos/web/app.py | plain-word helpers the tickets reuse | `feature_label` :62 · `method_label` def :195 · `action_type_label` :233 · `intent_plain` :1700-1710 · `when_plain` :1713-1719 · `RECORD_STATUS_PLAIN` :1687-1691 · `html_escape` import :13 |
| commerceos/web/app.py | `_db` / `_guard` — the per-request conn + operator guard every page uses | :617-622 · :631-632 |
| commerceos/web/app.py | the run preview page batch tickets door to | :3837-3910 |
| commerceos/web/app.py | `_health` — the repo-global mirror the wall must NOT put on per-store lines | :2190-2198 |
| commerceos/web/teletext.py | `masthead` — teletext chrome the wall must not use; behavior 4 in its docstring ("the store the surface speaks for, always") | :88-103 |
| commerceos/gate/ledger.py | `pending_queue` (live waits, oldest first) · `lapsed_queue` (never live) · `fill_outcome` stamps outcome ts (the "changes today" clock) | :342-347 · :350-355 · :263-286 (ts :275) |
| commerceos/gate/gate.py | `resolve` — the only approve path the wall's forms reach through api_resolve | :120-150 |
| commerceos/catalog/runs.py | run rows: statuses staged→executing→done\|rejected; `live`/`lapsed` render truth; per-item error isolation writes the stopped states | schema :28-41 · `list_runs` :59-66 · `_shape` :69-85 · `approve` :100-154 (isolation :138-141 · states :131,140,145) |
| commerceos/stores.py | the registry + resolver for the calm lines | `load_registry` :38-57 · `active_store` :65-75 · `resolve` :78-96 · env overrides :28-31 · `REPO_ROOT` :23 |
| commerceos/web/triage.py, fusion.py, static/fusion.css | CS0's landed foundation — composed, never re-derived; contracts in packs/CS0/PACK.md ("the ruled contracts"), NOT repo lines at 888de9c (they do not exist at this commit — verify at step 0) | CS0's contract |
| tests/test_catalog_dashboard.py | the plain-language guard: `_visible_text` + banned terms + snake regex + the walked-path list "/wall" must join | :329-334 · :337-414 (banned :400-402 · regex :403 · paths :404-409) · `env` fixture :49-57 |
| tests/test_wall_web.py | NEW — the pins (below) | — |

not touched but read: commerceos/catalog/workflows.py `run_feature`
(hold stages parked + groups a run :449-453, :522-525; reversible
without hold goes straight to executing :493 — why loose reversible
pendings are rare).

## prior art (copy these shapes)

- **the web rig**: tests/test_workflow_runs_web.py:21-31 (COMMERCEOS_DB
  pin + connect + ensure_schema + ledger.ensure_schema + TestClient);
  ShopifyClient monkeypatch :122-125; FakeStore/seed_variant import :18.
- **arming a held batch from the surface**:
  tests/test_workflow_runs_web.py:34-39 `_arm` (POST /catalog/run/gtin →
  303 → /catalog/runs/…).
- **staging a parked consequential wait**: tests/test_catalog_delist.py
  `_submit_delist` :93-101 (the exact gate.submit shape); FakeClient
  :31-53 for the approve leg.
- **fold-honesty pins to echo**: tests/test_workflow_runs_web.py:65-82
  (the batch shows once; the heading counts what the list shows).
- **guard-walk membership**: tests/test_catalog_dashboard.py:404-409 —
  add "/wall" to this exact list; the test itself stages real gated work
  first (:363-398), so the wall renders with live rows on it during the
  walk.

## binding laws

- the seven carried laws — spec/parts/collab-surface.md "the laws
  carried". the wall implements 1 (one gesture per ticket / one honest
  batch, same gate), 2 (receipt in place), 4 (counts computed at render),
  5 (one focus — the sentence), 6 (stops are first-class red tickets), 7
  (first person plain). law 3 (mirror-as-of) binds by ABSENCE here: no
  mirror number rides the wall (the health mirror is store-ambiguous).
- the plain-language guard walks /wall (tests/test_catalog_dashboard.py:337)
  — no insider term, no snake_case identifier in visible text.
- the three SF1 lints (tests/test_sf1_lints.py, CS0's) — land-guard ·
  fiction-collision · mirror-as-of; they walk fusion.py's string sets and
  triage's sentences. wall strings placed in fusion.py sets inherit them.
- the gate: no approve verb anywhere new; confirm stays required
  (app.py:1517-1518). agents stage, a person lands.
- append-only ledger: the wall reads; render-time maps translate old ink.
- the escape law: every record-born string through html_escape before
  markup (regression precedent commit 1f7936e).
- verify rendered, never files-exist: done means the live surface read it
  back; the check's "live render against real data" is that law applied.

## cold-start env

    cd the cartridge root
    uv run pytest -q                       # expect 508+ passed, zero skips, ~90s
    # step 0 preflight — CS0 landed?
    ls commerceos/web/triage.py commerceos/web/fusion.py \
       commerceos/web/static/fusion.css tests/test_sf1_lints.py
    # live surface (step 3): COMMERCEOS_DB=<scratch> uv run uvicorn commerceos.web.app:app --port 8848
    # store/db resolution is CALL-TIME (stores.py) — never an import-time path

required reading: AGENTS.md · .claude/agent-memory/producer/MEMORY.md ·
packs/RUNBOOK.md · spec/parts/collab-surface.md (fully) ·
packs/CS0/PACK.md + context.md (the contracts composed here) ·
reports/collab-surface/fusion.html (the ruled comp — states 1-3 are the
wall's three days: calm, heavy, empty).

## test plan (the pins, named)

new file tests/test_wall_web.py; rig per prior art; a crafted two-store
registry via `monkeypatch.setattr(stores, "REPO_ROOT", tmp_root)` where
the calm-line pins need it (demostore default + a second store with no db
file → the "nothing set up yet" line).

**the pin-7 rig (RULED — the audit caught the contradiction)**: with
COMMERCEOS_DB pinned, stores.resolve returns the scratch path for EVERY
store (stores.py:28-31, :84-86), so the db-less branch can never trigger
through the real resolver. the test monkeypatches `stores.resolve` with
a wrapper: the active store's name falls through to the real resolver
(the env-pinned scratch db); the second store's name returns a path
under tmp_root that no file backs. do NOT delenv COMMERCEOS_DB (that
breaks the whole rig) and do NOT weaken the pin.

1. `test_the_empty_day_says_nothing_needs_you` — fresh scratch db → the
   page carries "Nothing needs you." exactly once, the calm lines, the
   doors; zero ticket elements.
2. `test_the_sentence_states_the_real_wait_count` — stage 2 consequential
   waits (delist shape) + arm a gtin hold batch of 2 → the rendered
   heading equals `triage(pending_queue(conn)).sentence` computed in the
   test, and states 4.
3. `test_eyes_first_tickets_open_to_their_receipt_in_place` — a parked
   delist renders an amber ticket whose `<details>` carries the same
   change words the decisions card shows (pin a distinctive phrase, not
   the whole card), plus the confirm+approve form posting to
   /api/approvals/{id}.
4. `test_routine_folds_into_one_batch_ticket` — the held batch renders
   ONE ticket ("a batch of 2"), doored to its /catalog/runs/{id}; the
   member records never render as individual wall tickets (echo
   test_workflow_runs_web.py:65-72).
5. `test_approving_from_the_wall_runs_the_gate_road_end_to_end` —
   FakeClient over writes.ShopifyClient; POST the wall ticket's form
   (decision=approved&confirm=true) → 303; the record reads executed with
   a verified outcome; re-GET /wall → the sentence decremented, the
   ticket gone.
6. `test_a_stopped_job_renders_red_with_its_why` — approve a held batch
   through catalog_runs.approve with a client that raises on one item
   (the real isolation writes "errored — …", runs.py:138-141) → the wall
   shows a stopped ticket naming the feature, the why, and "lapsed,
   skipped"/untouched facts; doored to the run receipt.
7. `test_calm_lines_one_per_store` — crafted registry: active store's
   line carries the live counts; the db-less store reads "nothing set up
   yet"; no health number anywhere on the wall.
8. `test_record_born_ink_renders_escaped` — a wait whose intent carries
   `<b>` appears only escaped (the 1f7936e regression shape).

plus the ONE edit to tests/test_catalog_dashboard.py:404-409 ("/wall"
joins the walk) — run that test file alone first to see the wall pass the
guard with live rows staged.

## open questions (honesty — these are escalation triggers, not guesses)

- **CS0 drift**: this pack assumes CS0's PACK.md contracts land verbatim
  (`Triage.sentence/.eyes_first/.routine/.stopped`; `fusion.page`
  referencing the stylesheet by path; edge enum). the earlier working
  note naming a `.batchable` field does NOT match CS0's ruled contract on
  disk — the disk contract wins; re-verify against LANDED code at step 0.
- **whether `fusion.page()` emits a full html document** — CS0's contract
  is ambiguous ("the <link> is CS1's business"); step 0 reads the landed
  code and either uses it or ships `_fusion_doc`.
- **the health mirror is repo-global** (reports/health-latest.json,
  app.py:2187-2198) with no store name — unusable on a multi-store
  surface without lying. the wall omits it; if the board (CS2) or a later
  round wants per-store health, that is a new backlog item.
- **the approve return-trip**: api_resolve redirects to /approvals, so a
  wall approve lands on decisions with the flash — the existing road,
  which the check names. a "return to where you pressed" affordance is a
  possible follow-up ruling, not built here.
- **store doors point at /catalog until CS2 lands** `/board/<name>` —
  CS2's pack flips them; a door must open a real page today.
