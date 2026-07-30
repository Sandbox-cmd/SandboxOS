# UI-polish · context — the frozen seam map

every ref below read fresh at commit 942d7715c9627ab57b048e787a163482980559d4
(re-trued 2026-07-19, superseding the 3c506f9 read — see the "re-true
corrections" note at the foot). the repo is truth; if line 1 of PACK.md says
STALE, re-read these seams before trusting a single line number.

## seam map (verified)

### the board (density half)

- `commerceos/web/app.py`
  - `catalog_products` :2258-2523 — the combined board. the whole half lives
    inside this one function.
  - `_LANE_CAP = 25` :2172 — per-lane card cap; the table view needs its own
    cap (100, /record precedent) — do not reuse _LANE_CAP for it.
  - the filter-set dict `current` :2287-2288 and `compose()` :2290-2297 —
    EVERY link and form must carry the new density key through these two
    sites or the toggle silently drops on the first filter click.
  - hidden form fields :2419-2423 — the GET search form re-composes the
    chips; density joins this tuple or "apply" resets the view.
  - tabs :2366-2377 — built via compose(), so they inherit density for free
    once it is in `current`.
  - lanes render :2463-2487 — the cards path; the table path branches before
    this loop. `prods` :2333-2355 is already filtered; sort :2357-2363
    already applied (health default).
  - `when_plain` :1412 — plain time words for the "last change" column.
    `state_label` (imported into app.py; used at :2436, :2470) — plain state
    words for the state column.
- `commerceos/web/teletext.py`
  - `chip` :142-151 — the toggle pair. `pcard` :154-160 — the card the
    default view keeps. `board_lane` :163-172 / `board` :175-178 — untouched
    by the table path, just skipped.
  - `block` :61 — wrap the table in a P-block (`p2xx` bar) like every other
    surface.
- `commerceos/web/static/teletext.css`
  - board/lane/pcard styles :357-396; the drift-rows table precedent styled
    at :470 (used from app.py:693-699). add one table class here if the
    drift-rows look is too small for a full board table.
- `spec/experience-catalog.md`
  - :113-118 — the deferred intent, verbatim: "a compact card in the board; a
    full row when switched to table density. columns (table density): product
    (title + handle) · vendor · category · lifecycle state · the gaps it
    carries · last change."
  - :137-140 — components law: "a teletext data table (P-block with a
    bell-blue header bar, monospace columns, cyan openable ids)".
  - provenance of the deferral: the 2026-07-12 board-build journal note —
    "the table-density toggle from the spec is deferred".

### the cadence half

- `stores/demostore/rhythm.json` — the audit row ALREADY EXISTS: cadence
  "24h", `enabled: false`, no "calls" key. this build does not add the row;
  it pins it and reads it at render.
- `commerceos/rhythm/runner.py`
  - `load_config` :70-71 + `job_configs` :74-77 — the guarded config read
    p202's caption uses (call-time; env-resolved store per stores.py law).
  - `resolve_job` :242-248 — the F2 defaulting rule: a row naming no
    callable resolves to the built-in of its name.
  - `_job_audit` :177-188 — the builtin the row resolves to; writes the
    mirror via `catalog_audit.write_reports(state, catalog_audit.DEFAULT_OUT)`
    :186. it does NOT stamp `state["db"]` (the CLI does at audit.py:520) —
    the optional 2-line provenance fix from the step plan.
  - registry order :230-239 — expire_sweep first, file order otherwise.
  - the arming law in prose :13-17 ("nothing arms itself").
- `commerceos/catalog/audit.py`
  - `main` :506-527 — the CLI that produced every mirror to date.
  - `write_reports` :481-496 — health-<date>.md + health-latest.json; the
    previous latest feeds run-over-run deltas.
  - `connect_readonly` :499-503 — `mode=ro`, the mechanical no-writes
    guarantee.
  - `default_db` :43-44 — resolves the active store call-time (data/demostore.db
    today); `DEFAULT_OUT` :40 — the SHARED reports/ dir (the multi-store trap
    named in PACK.md risks).
- `commerceos/web/app.py` (mirror read side)
  - `_REPORTS` :1886 · `_health` :1889-1897 — the mirror read; missing file
    → {} → "no health check yet".
  - `catalog_home` :1976-2166 — `mirror_asof` :1990-1995 (the mirror wears
    its OWN date, not today); the p202 block (dims read :2120, keys built
    :2129-2132 — RE-TRUED: now FOUR keys, specs_structured / images /
    merchandising / provenance — "seo" was dropped from this block in a113f47
    because listing text (p209) got its own live front; the mirror JSON itself
    still may carry a "seo" dimension, p202 simply no longer renders it, by
    design); caption :2133-2135 — the edit site, text unchanged.
  - the masthead's `as_of=mirror_asof` param was ALSO removed in a113f47 (the
    date now folds into the `sub` line text itself); this pack does not touch
    the masthead, so it is unaffected — noted for completeness only.
- current mirror state (why this half exists): reports/health-latest.json —
  `date: 2026-07-12`, `overall_score: 78.5`, `db: .../data/commerceos.db` —
  a path M3 renamed away on 2026-07-19. the mirror is a week stale and its
  provenance points at a file that no longer exists.

## prior art (copy these shapes)

- **board tests**: tests/test_catalog_dashboard.py — the `env` rig :49-58
  (COMMERCEOS_DB → tmp, TestClient, seeded via seed_product/seed_variant
  :27-46), board pins :132-193. copy test_board_state_filter_narrows... :153
  for the composure pin.
- **plain-first guard**: tests/test_catalog_dashboard.py
  test_no_jargon_or_raw_codes_reach_the_screen :240-313 — the walk list
  :305-309 is where the density URL joins (RE-TRUED: a113f47 inserted
  "/catalog/workflows/seo" into this same list, shifting it by one line);
  banned terms :301-303; snake regex :304.
- **p202 pin**: tests/test_ui_truth.py
  test_p202s_numbers_stay_doorless_and_say_why :143-150 — the pin your
  caption must keep green; its `rig` :20-28 is the fixture to reuse.
  NOTE: `_health()` reads the module-global `_REPORTS` (the repo's REAL
  reports dir) even under a scratch db — a deterministic caption pin needs
  `monkeypatch.setattr(commerceos.web.app, "_REPORTS", tmp_reports_dir)`.
- **rhythm config pins**: tests/test_rhythm.py
  test_config_is_parseable_and_arming_is_a_boolean_choice :99-115 (asserts
  the six job names on the shipped config — extend here), the defaulting-rule
  coverage around :202-260.
- **a data table on a surface**: the drift-rows table, app.py:693-699 +
  teletext.css:470.
- **the honesty cap line**: /record's "showing the newest 100 of N acts"
  (UI-truth, backlog.md:93) — the table view's cap line copies this voice.

## binding laws specific to this item

- arming any store's rhythm is the owner's keystroke — the build may pin the
  disabled row and read it; it may never flip `enabled` (backlog.md:37,
  runner.py:13-17).
- the ruled dead-numbers law: a mirror reading is not a door until its front
  is built — p202 mints no anchors and says why (UI-truth2, backlog.md:98;
  pinned at test_ui_truth.py:143).
- server-rendered pages, no SPA, no new JS (spec/experience.md:92).
- plain words on every screen; escape any record-born ink before markup
  (titles/vendors here come from the facts — render them the way pcard
  already does, no new raw f-string interpolation of user ink).
- spec-first: this pack reads "table density" as ONE flat table (the spec
  names a lifecycle-state column, redundant inside lanes). if the builder
  concludes stacked full-width lanes instead, that reading contradicts
  nothing — but changing the spec's column list would; stage the spec edit
  first (escalation trigger 1).

## cold-start pointers

- RUNBOOK.md env block (cd, `uv run pytest -q` ~90s, uvicorn on 8848,
  call-time store resolution — never re-introduce an import-time path read).
- required reading: AGENTS.md · .claude/agent-memory/producer/MEMORY.md ·
  the plain-first guard test (tests/test_catalog_dashboard.py:240).
- the store resolver: commerceos/stores.py — COMMERCEOS_DB env wins first;
  that is why the scratch-db rigs work.

## test plan (the pins, named)

1. `test_board_default_stays_cards` — no density param → pcard markup, no
   data table.
2. `test_board_table_view_shows_the_specs_columns` — ?density=table → one
   table, both seeded products, vendor + plain state + plain last-change
   words; title cell links to /catalog/products/<pid>.
3. `test_table_view_composes_with_filters_and_survives_the_form` —
   ?density=table&state=draft narrows; hidden field carries density; chips'
   hrefs keep it.
4. `test_the_word_density_never_reaches_the_screen` — explicit pin (the
   guard's regexes would miss it).
5. guard walk extended with "/catalog/products?density=table" (edit the list
   at test_catalog_dashboard.py:305-309).
6. `test_demostore_ships_the_audit_row_disabled_and_resolvable` (test_rhythm.py)
   — the shipped config's audit row: enabled false, cadence parses, resolves
   to the audit builtin via the defaulting rule with no "calls" key.
7. `test_p202_names_its_measure_date_and_the_unarmed_schedule`
   (test_ui_truth.py, _REPORTS monkeypatched) — the caption: measured date +
   plain unarmed-schedule sentence + keeps "opens to its products when its
   front is built" + zero anchors (do not weaken the existing :143 pin;
   add beside it).

capture shape (producer cold read): a throwaway script — seeded scratch db +
TestClient, write /catalog, /catalog/products, /catalog/products?density=table
HTML to a captures dir; PLUS the live-fixture captures from the real
127.0.0.1:8848 run (the twice-paid lesson: minted-fixture green while the live
surface lies — pin and capture the LIVE shape too).

## open questions

none blocking the buildable half. the two [owner] halves (P-page numbers ·
money-view labels) are framed as the ruling card in PACK.md and are excluded
here by design. one discovery rides out as a NEW backlog item, not a question:
the shared reports/ dir across stores (audit.py:40, app.py:1886) will
interleave mirrors when a second store's audit ever runs.

## re-true corrections (2026-07-19, commits 3ab25d1 + a113f47)

every app.py line ref above was re-verified fresh at HEAD
(942d7715c9627ab57b048e787a163482980559d4) and corrected from the 3c506f9
read. full list of what moved:

- `catalog_products` 2156-2409 → 2258-2523
- `_LANE_CAP` 2084 → 2172
- `current` dict 2186-2187 → 2287-2288
- `compose()` 2189-2196 → 2290-2297
- hidden form fields 2318-2322 → 2419-2423
- tabs 2265-2276 → 2366-2377
- lanes render 2362-2386 → 2463-2487
- `prods` build 2232-2254 → 2333-2355
- sort block 2256-2262 → 2357-2363
- `when_plain` 1345 → 1412
- `state_label` call sites 2335/2369 → 2436/2470
- `_REPORTS` 1819 → 1886
- `_health` 1822-1830 → 1889-1897
- `catalog_home` 1903-2078 → 1976-2166
- `mirror_asof` 1918-1923 → 1990-1995
- p202 block / caption 2033-2047 → dims read 2120, keys 2129-2132, caption
  2133-2135
- drift-rows table precedent 664-666 → 693-699
- R2 ruling card's /economics lane line 1569/1593-1598 → 1660-1665
- tests/test_catalog_dashboard.py guard walk list 305-308 → 305-309 (one line
  inserted ahead of it by a113f47)

two behavioral (not just line-number) changes, both from a113f47, neither
contradicting this pack's plan:

1. **p202 lost a row.** the health block now renders FOUR dimensions
   (specs_structured, images, merchandising, provenance), not five — "seo"
   was removed because listing text got its own live front (p209) and the
   comment at the call site says so explicitly ("listing text has a LIVE
   front now (p209) ... only fronts not yet built stay in this block"). the
   caption text this pack's step 2b appends to is byte-identical to the old
   read; only its line number and the row count above it moved. this is a
   landed, intentional surface change from a prior commit, not a mirror-data
   contradiction — escalation trigger 2 is about a NEW loss/rename among the
   remaining four keys, not this one.
2. **the masthead dropped `as_of=mirror_asof`.** catalog_home's masthead call
   no longer takes that param; the measured date now lives only in the `sub`
   line text ("catalog health · measured &lt;date&gt;"). this pack never
   touches the masthead — noted only because it sits in the same function
   this pack does edit.

nothing else in the seam (rhythm.json, runner.py, audit.py,
spec/experience-catalog.md, tests/test_rhythm.py, tests/test_ui_truth.py,
teletext.py, teletext.css) changed between 3c506f9 and HEAD — `git diff
--stat` over that range touches only commerceos/web/app.py and one line of
tests/test_catalog_dashboard.py. every citation into those other files in
this pack was already correct and needed no change.
