git diff --quiet 942d7715c9627ab57b048e787a163482980559d4..HEAD -- commerceos/web/app.py commerceos/web/teletext.py commerceos/web/static/teletext.css commerceos/rhythm/runner.py commerceos/catalog/audit.py stores/demostore/rhythm.json spec/experience-catalog.md tests/test_catalog_dashboard.py tests/test_ui_truth.py tests/test_rhythm.py || echo "STALE — re-true before build (see RUNBOOK)"

# UI-polish — the buildable half: the board's table view + a fresh health reading with a standing cadence

## mission

give the products board its deferred second density — the spec's "full row when
switched to table density" — and make p202's health numbers current again: the
mirror they render was measured 2026-07-12 against a database path that stopped
existing when M3 renamed it. the cadence mechanism (a disabled rhythm row that
audits daily once armed) already exists; this build refreshes the mirror, pins
the cadence row as law, and makes the surface say plainly what keeps it fresh.
the two [owner] sub-items are EXCLUDED — they ride below as a ruling card.

as-of: commit 942d7715c9627ab57b048e787a163482980559d4 · suite 416 green

re-trued 2026-07-19 after 3ab25d1 (delist branch) and a113f47 (F4b: listing-text
feature) both moved app.py under this pack's feet. corrections applied below;
see the "re-true corrections" note at the foot of context.md for the full list.
the two behavioral facts worth flagging up front: (1) p202 now renders FOUR
dimension rows, not five — "seo" dropped off the mirror block because listing
text got its own live front (p209) in a113f47; the caption text this pack edits
is unchanged, only its line number and its row count moved. (2) the masthead on
/catalog no longer takes an `as_of=mirror_asof` param (a113f47 folded the date
into the sub-line text itself, "catalog health · measured &lt;date&gt;"); this
pack never touches the masthead, so it is unaffected — noted only because the
RUNBOOK flagged this exact area for reconciliation.

## the backlog check (verbatim, backlog.md:160)

> each resolved on its surface; the owner rules the [owner] items

## model

sonnet — both halves are seam-following work over verified prior art (the board
renderer, the rhythm registry, the audit CLI); no novel design, no new laws.

## boundaries

- **stores/dbs written**: scratch dbs only for every test (COMMERCEOS_DB → tmp,
  the test_catalog_dashboard.py rig). the ONE live touch permitted: running the
  read-only audit CLI (`uv run python -m commerceos.catalog.audit`) against
  data/demostore.db — it opens the db with `mode=ro` (audit.py:499-503, the
  guarantee is mechanical) and writes only reports/health-<date>.md +
  reports/health-latest.json, which are repo report files, committed by path.
- **never**: arm any rhythm row, write demostore.db, touch the live store.
  arming is the owner's keystroke — hard law (runner.py:13-17, backlog.md:37).
- **gate lane**: none — nothing here stages a proposal.
- **writer-class**: no agent involved; the web surface's own rendering only.

## step plan (S-size: 2 checkpoints)

### step 1 — write the failing tests

1a. board table view, in tests/test_catalog_dashboard.py (reuse the `env` rig,
    :49-58):
    - default board unchanged: `/catalog/products` renders pcard markup
      (`class='pcard'`), no data table.
    - `/catalog/products?density=table` renders ONE full-width teletext data
      table of the filtered set with the spec's columns
      (spec/experience-catalog.md:117-118): product (title + handle) · vendor ·
      category · lifecycle state (plain via state_label) · the gaps it carries
      · last change (plain via when_plain, app.py:1412). seed 2 products in
      different states; assert both rows + their vendors + plain state words.
    - composure: the table view survives a filter — e.g.
      `?density=table&state=draft` shows only the draft row and the toggle
      chip for the card view carries the state in its href (compose() law,
      app.py:2290-2297).
    - the toggle's screen words are plain: "cards" / "table" — the word
      "density" must NOT reach the screen (it is a spec term; the guard's
      snake/insider rules at :301-313 won't catch it, so pin it explicitly).
    - extend the plain-first guard walk (test_catalog_dashboard.py:305-309)
      with "/catalog/products?density=table".
1b. cadence pins:
    - in tests/test_rhythm.py (read :99-115 first — extend, don't duplicate):
      the SHIPPED stores/demostore/rhythm.json carries an "audit" row with
      `enabled: false` and a cadence that parses (24h today), and
      `resolve_job("audit", row)` resolves to the audit builtin via the
      defaulting rule (runner.py:242-248) — the row names no "calls" key.
    - in tests/test_ui_truth.py (the `rig`, :20-28): monkeypatch
      `commerceos.web.app._REPORTS` to a tmp dir carrying a minted
      health-latest.json (date + dimensions), and pin p202's caption: it names
      the measured date, keeps the exact phrase "opens to its products when
      its front is built", mints NO anchors (the ruled dead-numbers pin,
      test_ui_truth.py:143-150 — your new caption must keep that test green),
      and — when the store's audit rhythm row exists but is not armed — says
      so in plain words (e.g. "a fresh reading is set for every day, but the
      schedule isn't switched on yet — switching it on is yours"; final words
      are the builder's, they must pass the guard: no "audit mirror", no
      "rhythm", no snake_case).

CHECKPOINT 1 — tests written and failing; every touched file is in the seam
map (context.md). stop and review.

### step 2 — build, then prove live

2a. the table view in `catalog_products` (app.py:2258-2523):
    - read `density = q.get("density") if q.get("density") == "table" else None`,
      add it to `current` (:2287-2288) so compose() and the hidden form fields
      (:2419-2423) carry it everywhere; default (cards) stays out of urls.
    - a "view" chip pair in the filter bar (tt.chip, teletext.py:142-151):
      "cards" (active when density is None) · "table" (href=compose(density="table")).
    - when density == "table": skip the lanes (:2463-2487) and render one
      P-block data table of `prods` (already filtered + sorted), columns per
      spec; cap at 100 rows with the /record precedent's honesty line
      ("showing the first 100 of N products" — /record says "showing the
      newest 100 of N acts"); title cell links to the drill like pcard does.
      style: follow the drift-rows table prior art (app.py:693-699,
      teletext.css:470) + the spec's "bell-blue header bar, monospace columns"
      (experience-catalog.md:137-138); add a small css class to teletext.css
      if needed. no javascript — server-rendered law.
    - the state column repeats the spec's column list verbatim
      (experience-catalog.md:117-118) — with one flat table the state column
      is what replaces the lanes; that is why this pack reads "full row" as
      one table, not stacked lanes (the spec names a lifecycle-state COLUMN,
      which a lane layout would make redundant).
2b. the cadence surface + the fresh mirror:
    - p202's caption (app.py:2133-2135): append the standing-check sentence,
      built from a guarded read of the active store's rhythm config
      (runner.load_config + job_configs, runner.py:70-77 — call-time, never
      import-time; wrap in try/except so a missing config never takes the
      overview down). keep the caption anchor-free.
    - optional 2-line honesty fix while you are in the seam: `_job_audit`
      (runner.py:177-188) writes the mirror without the `db` provenance key
      that the CLI stamps (audit.py:520) — set `state["db"]` from
      `str(catalog_audit.default_db())` before write_reports so a rhythm-run
      mirror carries the same provenance. covered by suite green; no new pin
      required.
    - refresh the mirror: `uv run python -m commerceos.catalog.audit`
      (read-only; audit.py:506-527). confirm the new health-latest.json's
      `date` is today and `db` ends in data/demostore.db.

CHECKPOINT 2 — full suite green at ≥ 416, zero skips (orchestrated: the
builder runs only its own touched test files at each checkpoint per the
parallel-build split; the orchestrator runs and confirms the full count).
then the live proof: boot `uv run uvicorn commerceos.web.app:app --port 8848`
and verify-render at 127.0.0.1:8848 — /catalog shows "measured jul <dd>"
(today) on p202 with all FOUR dimension rows carrying numbers (not "—") —
re-trued: specs_structured / images / merchandising / provenance, "seo" no
longer lives in this block (it has its own live front, p209) — and
/catalog/products?density=table renders the table with real rows. take HTML
captures of both (plus the default cards board) for the producer's cold read —
these are operator surfaces. stop and review against the laws checklist.

## escalation triggers

RUNBOOK's six, plus:

- the audit CLI cannot open data/demostore.db read-only (WAL sidecar/lock) —
  checkpoint WAL per RUNBOOK boundaries first; still failing → stop.
- the fresh mirror loses or renames a dimension key p202 renders
  (specs_structured / images / merchandising / provenance, app.py:2129-2132 —
  re-trued: this is FOUR keys now, not five; "seo" dropped off this block in
  a113f47 because listing text got its own live front, p209 — that is a prior,
  already-landed surface change, not a new contradiction) → a genuinely NEW
  loss or rename among these four is what to escalate; never render "—"
  silently over a rename.
- the table view wants javascript or a new dependency → stop
  (server-rendered law, spec/experience.md:92).
- any temptation to resolve a ruling-card item below "while you're in there"
  → trigger 6, the owner's ruling.
- test_p202s_numbers_stay_doorless_and_say_why (test_ui_truth.py:143) goes
  red → your caption broke the ruled dead-numbers law; fix the caption, never
  the pin.

## "done"

RUNBOOK's five lines, plus this item's specifics: the check is per-surface —
(1) the board's table view verify-rendered live with the spec's columns and
plain words; (2) p202 verify-rendered with a today-fresh mirror AND the
standing-cadence sentence; (3) the cadence row pinned disabled (arming stays
the owner's); (4) producer cold read over the three captures (board cards,
board table, overview) to SHIP-CLEAR; (5) the ruling card below staged for the
owner, not resolved. commit code + tests + the two report files by path —
never `git add -A`.

## the ruling card — the two [owner] halves (EXCLUDED from this build)

**R1 · the P-page numbers.** since the 2026-07-12 voice pass the teletext
p-numbers (p200, p206, p500…) render as accent beside plain labels; the open
question on the record: "owner may want them dropped" (journal note,
2026-07-12). options: (a) KEEP — they are now load-bearing: UI-truth ordered
them on the page, tests cite them (p202/p206 pins), and the teletext habit
tunes by page number; (b) DROP — a sweep across ~20 block titles + the pins
that quote them. recommendation: keep (a); dropping is churn with no jobs
gain, and the accent is chrome, not jargon — the plain label leads everywhere.
one k either way.

**R2 · the money view's two-books labels.** /economics renders its lanes by
their code names: "showing: company · see learnings" (app.py:1660-1665).
the question is only the words — the mechanism is built and the explanatory
muted lines are already honest. options: (a) "your store's books" /
"the old company's books — reference only"; (b) any words the owner prefers —
it is his store and his old company. recommendation: (a) shape, owner picks
exact words; URL params stay company/learnings (no link churn). one k + the
two strings.

## risks inline

- **collision law**: this pack touches app.py — per packs/INDEX.md pull order
  it runs AFTER F4b lands, and never beside another app.py pack. re-run line 1
  after F4b; catalog_products line numbers WILL have drifted.
- **the p202 pin trap**: the caption edit sits inside the exact segment
  test_ui_truth.py:148 slices ("p202 · other health numbers" → "p299"). no
  anchors, keep the quoted phrase.
- **plain-language guard**: the guard walks /catalog/products
  (test_catalog_dashboard.py:305-309). banned on screen: "density", "audit
  mirror", "rhythm", any snake_case. say "table", "cards", "reading",
  "schedule".
- **testclient identity**: TestClient's host is "testclient" → localhost
  (auth.py:52); irrelevant here but explains why no auth headers appear in
  the rig.
- **git-tracked data**: reports/health-latest.json + the new health-<date>.md
  are the only data files this make may commit — by path, named in the
  commit. demostore.db must show zero diff (it is opened mode=ro; verify with
  `git status` before commit).
- **multi-store mirror trap (discovery, NOT this build)**: audit's
  DEFAULT_OUT (audit.py:40) and the web's _REPORTS (app.py:1886) are one
  shared reports/ dir for ALL stores — a scaffold audit tick would overwrite
  demostore's mirror. per pull rule 3 this is a new backlog item; name it in
  the make note, do not fix it here.
- **tense/voice**: p202's new sentence speaks to the owner ("switching it on
  is yours"), never about "the operator" (banned term, guard :303).
