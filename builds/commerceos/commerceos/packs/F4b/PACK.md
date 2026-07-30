git diff --quiet 3ab25d1..HEAD -- commerceos/catalog/workflows.py commerceos/fleet/content.py commerceos/spine/writes.py commerceos/spine/connector_shopify.py commerceos/catalog/runs.py commerceos/web/app.py tests/test_workflow_runs_web.py tests/test_content_agent.py || echo "STALE — re-true before build (see RUNBOOK)"

# F4b — the listing-text feature

## mission

give the listing-text work (CW6) a front on /catalog: the content agent's
drafts (F4a) become a Feature row over the one workflow engine, so a batch of
plain drafts holds as one preview and lands on one glance-approve (WF-approve),
executes through the S1 executor (`mutate_seo`), verify-renders, and moves a
card the owner watches. drafts that quote a verified spec value keep parking
per item — F4a's ruled split is honored by splitting the queue, never by
softening the gate.

as-of: commit 3ab25d1 · suite 398 green

## the backlog check (verbatim, backlog.md:109)

> a batch renders title + meta live; the card's queue drops; HARD producer cold-read (customer-facing words)

## model

**opus** — heaviest app.py churn of the wave (INDEX pull order 2: runs ALONE
among app.py packs), a HARD cold-read on customer-facing words, and one
real design seam (per-item declared_type vs the batch lane) that must be
resolved without widening the gate.

## boundaries

- writes: **scratch dbs + FakeStore/FakeClient only.** `data/demostore.db` +
  `data/<store>.ledger.jsonl` may hold real facts — read-only if touched at
  all. no live store write; the dev store is not needed for this check.
- gate lane: the new front declares **reversible** and rides the WF-approve
  hold path (`run_feature(hold=True)` → `catalog/runs.py`). the consequential
  (spec-quoting) drafts stay on F4a's per-item park (`content.propose_and_run`)
  — nothing in this build may batch-approve a consequential draft.
- writer-class: the content agent (`.claude/agents/content.md`) — listing
  text/meta only. the one new spine writer is `writeback_product_seo`
  (products.seo_title/seo_description), the spine's own lane per the comment
  at commerceos/spine/writes.py:156-161.

## step plan (M — 3 checkpoints)

**step 0 — freshness.** run line 1. read context.md fully + its required reading.

**step 1 — write the failing tests** (checkpoint 1: tests failing + seam
confirmed). new file `tests/test_seo_feature.py` (+ web pins, either there or
`tests/test_seo_feature_web.py`), rigs copied from
tests/test_content_agent.py:43-70 (the seeded catalog: weak listings + one
verified + one unverified claim) and tests/test_workflow_runs_web.py:21-39
(COMMERCEOS_DB scratch + TestClient + `_arm`). the pins are named in
context.md's test plan. run them; every one must fail for the right reason.

**step 2 — build to green** (checkpoint 2: suite green, ≥ 398 + the new pins,
zero skips; diff reviewed against the laws checklist; any file outside the
seam map = stop):

1. `commerceos/spine/connector_shopify.py` — add `writeback_product_seo(conn,
   product_id, title, description)` updating products.seo_title/
   seo_description with a `writeback:verified@<ts>` source. copy the shape of
   `writeback_variant_barcode` (:422-438).
2. `commerceos/fleet/content.py` — the feature half:
   - `seo_queue(conn)`: `compute_listing_drafts` (:151) → run
     `check_draft_against_catalog` (:106) on EVERY draft, drop refusals
     (counted — the engine has no refusal hook, so the queue is the wall)
     → keep ONLY `declared_type == "reversible"` drafts → shape each for the
     engine: `args={"product_id","title","description"}` (the S1 executor's
     args, writes.py:176-190), `product_id` (the stored shopify_id, for
     `_titles_for` app.py:3048), plain `display`, and the preview fields
     (see context.md — `_run_receipts` needs old/new per field).
   - `seo_progress(conn)`: written vs missing-or-weak counts from the same
     weak-listing SQL (:166-174), `to draft` = queue len, plus live
     `pending`/`lapsed` mutate_seo waits copied from `_verification_progress`'s
     ledger read (workflows.py:289-302) so the parked consequential drafts are
     named on the card, honestly, with the lapsed ones lapsed.
   - `seo_verify(outcome, item)`: `outcome["ok"]` and the read-back seo dict
     equals the drafted title + description (the `_mutate_seo` receipt shape,
     writes.py:188-190).
   - `seo_writeback(conn, item, outcome)`: route the verified values into
     products via the new spine writer — this is what makes the queue drop.
3. `commerceos/catalog/workflows.py` — the config row: `SEO = Feature(
   name="seo", method="mutate_seo", declared_type="reversible",
   agent="content", ...)`, batch_default 50 (the spec's proposed size,
   catalog-workflows.md:160), plain-words intent; register in `FEATURES`
   (:367). give `Feature` an optional `function: str = FUNCTION` field and
   thread it into the `gate.submit` payload (:411) so this front's ledger rows
   carry `content-geo` (the content agent's registered policy function,
   stores/demostore/policy-table.json:23) instead of catalog-enrichment.
   default unchanged for every existing feature — zero behavior change there.
4. `commerceos/web/app.py` — the surface entries (all verified seams in
   context.md): `front_no` "209" (:1988), the per-class verb map (:1899),
   `FRONT_BLURB` (:251), `SOURCE_PLAIN` (:280), `PROGRESS_LABELS` for the new
   progress keys (:58), `_WF_NO` "235" (:2440), the products-board gap
   (`GAP_LABELS`/`GAP_ORDER` :227-234, `FEATURE_TO_GAP` :240,
   `_board_gap_sets` :2115 — without this, `?feature=seo` silently shows ALL
   products, app.py:2202, a lying link the cold read will kill), and a
   `_run_receipts` branch (:3007) that renders a listing item as TWO plain
   lines (title: was → becomes; description: was → becomes) — additive,
   guarded by the item's own keys, so the gtin preview pins (:52-54 of
   test_workflow_runs_web.py) stay untouched.

**step 3 — live verify + producer captures** (checkpoint 3). boot the web
surface against a seeded scratch db, walk the whole loop, and write HTML
captures for the cold read (script shape in context.md). the check, rendered:
arm the listing-text front → the preview reads both fields in plain words →
one glance-approve → the receipts read "showed up live? yes" with the FakeStore
readback → the front's queue count on /catalog dropped → the parked
consequential draft sits in decisions per item. then the **HARD producer cold
read** (the item is [product] and customer-facing): findings block until
repaired or overruled by the owner's recorded k.

## escalation triggers

the RUNBOOK's six, plus:

- **the per-item declared_type seam wants engine surgery**: if honoring the
  split turns into editing `catalog_runs.approve`'s reversible-only wall
  (runs.py:116-118) or making `run_feature` route mixed gate classes in one
  held run — stop. the queue split (reversible-only queue; consequential rides
  F4a's `propose_and_run`) is the ruled shape; anything wider is a spec
  question first.
- **the spec's executor column**: catalog-workflows.md:160 still names
  `mutate_product_field (title) + meta write` for SEO — S1 (built, backlog row
  S1) superseded it with `mutate_seo`. stage the one-line spec true-up BEFORE
  the code lands (trigger 1), don't silently diverge.
- **gtin/classification preview or board pins break**: `_run_receipts` and the
  gap-set changes touch shared render paths — if any existing workflow-runs or
  dashboard pin fails, stop and re-shape additively.
- **the cold read blocks on duplicate drafts**: F4a's recorded risk (backlog
  F4a row) — identical vendor titles can draft identical listings. dedup is
  OUT of scope; if it blocks ship, it becomes a new backlog item (pull rule 3).

## "done"

the RUNBOOK's five lines, with these specifics: (a)'s check is the verbatim
row above, proven on the rendered run page + /catalog, not on dicts; (c) is
**HARD** here — producer cold read over fresh captures of every walked surface
(home, /catalog, the front page, the preview, the post-approve receipts,
decisions with the parked consequential draft) to SHIP-CLEAR; (e)'s proof
line should also note **the CW6 backlog fold** — CW6's row (backlog.md:164)
says superseded by F4a/F4b, so the sync marks CW6 closed-by-F4b.

## risks (item-specific, found in the code)

- **the engine has no refusal hook** — `run_feature` (:374) submits every
  queue item straight to the gate. if the queue doesn't run
  `check_draft_against_catalog` itself, an unverified-claim draft rides to a
  glance-approve. the refusal law lives in the queue callable, with a count,
  or the feature is dishonest by construction.
- **a mixed batch breaks the ruled gate boundary** — with `hold=True` EVERY
  proposal parks and rides `held_items` into one run (workflows.py:419-426),
  and `runs.approve` then approves the LOT. a consequential draft inside that
  lot would be glance-approved. the wall at runs.py:116-118 checks only
  `feature.declared_type`, not the items. hence: reversible-only queue.
- **the queue only drops through writeback** — `compute_listing_drafts` reads
  products.seo_title/seo_description (:166-174); without
  `writeback_product_seo` the store changes but the card lies until the next
  full sync. "the card's queue drops" is the check — the writeback IS the check.
- **testclient identity**: `_who` (app.py:2975-2982) maps "testclient" to
  "localhost"; `who_plain` (:2963) renders "you, at this desk". pins must
  assert the plain words and that "localhost" never renders (the
  test_workflow_runs_web.py:132-135 pattern). the approver-identity [owner]
  ruling (the 7c) rides — do not invent an identity.
- **plain-language guard**: tests/test_catalog_dashboard.py:240-313 walks
  rendered pages and bans snake_case + insider terms. new surface strings
  (progress labels, blurbs, verbs, receipts) are written to pass it — e.g.
  never "seo" on screen (the label is "listing text", FEATURE_LABELS :45),
  never `weak_reason` codes. add the new front's pages to the guard's walk.
- **tense/voice**: a held draft is "new listing text ... waiting on you",
  never "listing text written" — `METHOD_LABELS_AHEAD` already carries
  mutate_seo (:147); don't bypass `act_label`.
- **escape record-born ink**: drafted titles/descriptions come from catalog
  data and render on the preview — through `html_escape` as `_run_receipts`
  already does (:3034-3038), never raw.
- **append-only ledger**: progress/receipt honesty is computed at render
  (the runs.py `_shape` lapsed pattern) — never UPDATE ledger rows.
- **git discipline**: commit by path; `reports/run-seo-latest.json` or db/WAL
  churn from live-verify boots never rides the build commit.
