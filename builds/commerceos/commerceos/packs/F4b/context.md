# F4b context — the frozen research (verified at 3ab25d1)

## seam map (every ref read fresh from the repo)

**commerceos/catalog/workflows.py**
- `Feature` dataclass :39-55 — name, method, declared_type, agent,
  queue/verify/progress callables, intent, batch_default, optional writeback.
  queue items carry `args` + `display` (:47); F4b adds `function` (default
  the module's `FUNCTION = "catalog-enrichment"`, :36).
- `run_feature` :374-460 — the engine. `hold=True` (:376, :400-401): every
  proposal parks via `gate.submit(..., hold=hold)` (:410-414), held items
  collect the WHOLE queue-item dict + record_id (:423-426), one run row minted
  at :456-459 (`runs.create`). the gate payload :410-414 is where the new
  `feature.function` threads.
- `FEATURES` registry :367-368 — add `SEO.name: SEO`.
- `report_status` :482-498 — picks the new feature up automatically (/parts row).
- the template to copy: `GTIN` :134-145 (config row shape), `_gtin_queue`
  :79-99 (item shape incl. `old`/`new`/`product_id` for the preview),
  `_gtin_writeback` :111-116, `_gtin_progress` :119-131.
- the pending/lapsed ledger-read pattern for progress: `_verification_progress`
  :289-302 (json_extract on method, `ledger.expired` per row).

**commerceos/fleet/content.py** (F4a — the drafting half, all built)
- `draft_title` :70-77 · `draft_description` :80-101 (returns used claims).
- `check_draft_against_catalog` :106-146 — THE refusal law: length limits
  (:119-122), hype words (:123-125), cited claim missing/unverified/drifted
  (:126-138), unverified value stated verbatim in text (:139-146). raises
  `DraftRefused`.
- `compute_listing_drafts` :151-213 — the weak rule SQL :166-174
  (seo_title/seo_description NULL/blank or title echoed), draft dict shape
  :199-210: `product`, `product_id` (gid-normalized :201-202), `title`,
  `description`, `was` {seo_title, seo_description} :204, `weak_reason`,
  `claims`, **`declared_type`** :208 ("consequential" if claims used else
  "reversible" — F4a's ruled split), `provenance` :193-198.
- `propose_and_run` :219-264 — today's OWN loop outside FEATURES: refuse →
  gate.submit(method="mutate_seo", function="content-geo") → parked or
  auto-execute. F4b leaves this as the consequential lane's door; the new
  queue/progress/verify/writeback callables live beside it in this module.

**commerceos/spine/writes.py**
- `execute` :61-116 — the one write door; `mutate_seo` dispatch :105-106;
  `client = client or ShopifyClient()` :96 (why tests monkeypatch
  `writes.ShopifyClient`).
- `_mutate_seo` :176-190 — verify-render INSIDE it: refuses empty (:183-184),
  mutates, reads back, `{"ok", "verified_rendered", "seo": back}` :190.
- the writeback-lane division comment :156-161 — products.seo_* facts belong
  to the spine's writeback lane, recorded by the caller on the receipt.

**commerceos/spine/connector_shopify.py**
- `writeback_variant_barcode` :422-438 — the shape to copy for the NEW
  `writeback_product_seo` (source `writeback:verified@<ts>`). also
  `writeback_product_metafield` :441-463. there is no seo writeback today —
  F4b adds the third.

**commerceos/catalog/runs.py** (WF-approve, dd20d15 — read, do not edit)
- `approve` :100-154 — refuses non-reversible features :116-118 ("batch
  approve is the reversible lane — this front rules per item"); walks
  gate.resolve → writes.execute → `feature.verify(out, it)` :143 →
  `feature.writeback(conn, it, out)` :147-148. NOTE: verify/writeback receive
  the STORED run item — whatever keys `seo_queue` puts on an item are exactly
  what verify/writeback get back after the glance.
- `_shape` :69-85 — lapsed is a render truth, computed from the ledger.

**commerceos/web/app.py** (3,100+ lines — the collision file; this pack runs alone)
- `FEATURE_LABELS` :40-49 — **"seo": "listing text" already exists.**
- `PROGRESS_LABELS` :58-76 + `progress_detail` :88-116 — every new progress
  key needs a plain label or the raw key renders (guard-fatal).
- `METHOD_LABELS` :123-131 + `METHOD_LABELS_AHEAD` :143-151 — mutate_seo
  already mapped both tenses ("listing text written" / "new listing text").
- verb map :1899-1901 (per-gate-class verbs; add "seo") · `front_no`
  :1988-1989 (add "seo": "209"; rows sort by number :2002).
- `_front_row` :1873-1907 — renders automatically once registered; its queue
  link is `/catalog/products?feature=seo` :1895 → mapped at :2202 via
  `FEATURE_TO_GAP` :240-241 — **unmapped keys silently show the unfiltered
  board.** gaps: `GAP_LABELS`/`GAP_ORDER` :227-234, `_board_gap_sets`
  :2115-2128 (workflow-queue-backed gaps are set-comprehensions over
  `FEATURES[fkey].queue`).
- `FRONT_BLURB` :251-258 · `SOURCE_PLAIN` :280-285 · `GATE_CLASS_PLAIN`
  :268-272 (per class, already covers reversible).
- `_WF_NO` :2440 (add "seo": "235") · workflows index :2443-2477 · the front's
  run-and-watch page :2480+ (arm control + waiting-batch step-aside :2523-2557
  — all generic, no edit needed).
- the arm handler `catalog_run` :2930-2960 — reversible → hold + one-waiting-
  batch dedupe; generic, no edit needed.
- `who_plain` :2963-2972 · `_who` :2975-2982 (testclient → "localhost" →
  "you, at this desk").
- `_mark_diff` :2985-3004 · `_run_receipts` :3007-3045 — the old/new branch
  keys off `it.get("new") is not None and "old" in it` (:3029) and renders ONE
  was→becomes line; the fallback is `intent_plain(display)` (:3040). F4b adds
  a listing branch (two lines: title, description) keyed on its own item keys.
- `_titles_for` :3048-3059 — looks items' `product_id` up in
  products.shopify_id; keep the STORED id on items (compute_listing_drafts's
  gid normalization :201-202 only matters for the executor args).
- run view :3062-3131 · approve :3134-3155 · decline :3158-3178 — generic.

**policy + manifest**
- stores/demostore/policy-table.json — `content-geo` function :23 (reversible
  auto-approves) · `mutate_seo` method :77 (default reversible).
- .claude/agents/content.md — writer_class "pages, meta, structured data, and
  the feed"; listing-text acts, customer-facing-claims parks.

## prior art (copy these shapes)

- **feature-as-config**: `CLASSIFICATION` (workflows.py:158-169) — a feature
  whose callables live in their own module; F4b mirrors it with content.py.
- **web rig + hold-loop pins**: tests/test_workflow_runs_web.py — the whole
  file is the shape (rig :21-31, `_arm` :34-39, glance-approve with
  `monkeypatch.setattr(writes, "ShopifyClient", lambda: store)` :122-144).
- **seeded catalog with claims**: tests/test_content_agent.py :43-70 (products
  1/2/4 weak, product 1 has one verified + one unverified claim — exactly the
  reversible/consequential split fixture) and its `FakeClient` :23-40
  (productSeo mutation + readback, per-product).
- **executor-level pins**: tests/test_seo_executor.py (S1) — the seo
  FakeClient with `forced_readback` for the dishonest-readback case.

## binding laws for this item

- F4a's ruled split (backlog F4a row, RULED): plain drafts ride the auto/batch
  lane; a draft quoting a verified spec value declares consequential and PARKS
  PER ITEM — a customer-facing claim waits for a human, even a true one.
- WF-approve's ruling (dd20d15): every front has an approval step; reversible
  batches HOLD for one glance-approve; nothing auto-lands; batch approve is
  the reversible lane only (runs.py:116-118).
- spec/parts/catalog-workflows.md:160 (SEO close-out row): reversible content,
  batch ~50, check "title + meta render on the page AND the feed reads
  legible". its executor column predates S1 — stage the true-up (see PACK
  escalations).
- one write door · one writer per table-set: the engine never writes
  products.* — the spine's writeback function does.
- the two riding [owner] rulings (INDEX): mid-run halt boundary + approver
  identity (7c) — build inside today's recorded shapes, don't pre-empt them.

## cold-start pointers

- environment: RUNBOOK.md's env block (cd, `uv run pytest -q`, uvicorn
  :8848, COMMERCEOS_DB call-time resolution — never import-time).
- required reading: AGENTS.md · .claude/agent-memory/producer/MEMORY.md (the
  three scars: walk one click past the last surface — /api/* JSON dead-ends;
  grep the fresh capture for the mapped OUTPUT string; tense must match
  status, capture control pages mid-flight) · the plain-first guard test
  tests/test_catalog_dashboard.py:240-313.

## test plan

new `tests/test_seo_feature.py` (rig: content_agent's seeded catalog + gtin's
scratch-db conventions), plus web pins (workflow_runs_web's rig):

1. `test_queue_holds_only_reversible_drafts_and_refusals_are_counted` — seed a
   weak listing whose draft is fine, one whose draft quotes the verified claim
   (consequential — NOT in the queue), and one the refusal law kills (e.g. a
   product whose unverified claim value appears in its title, or a hype-word
   title); queue = the plain draft only; the refused count is reported.
2. `test_run_hold_stages_the_batch_and_nothing_executes` — run_feature(SEO,
   hold=True): all parked, one run row, ledger all pending, zero handles
   (the test_workflow_runs_web.py:59-62 assertions).
3. `test_glance_approve_executes_verifies_and_the_queue_drops` — FakeClient
   monkeypatched; approve the run; counted == batch; products.seo_title/
   seo_description now carry the drafts with a `writeback:` source; the queue
   re-read is smaller (THE backlog check's second clause, pinned at the
   mechanism level).
4. `test_verify_refuses_a_dishonest_readback` — forced_readback mismatch →
   not counted, no writeback (copy test_seo_executor's forced-readback shape).
5. `test_spec_quoting_drafts_park_per_item_never_in_a_batch` —
   propose_and_run parks the consequential draft; it appears in /approvals as
   its own card; the seo run preview never contains it.
6. web pins: the /catalog row (p209, plain words, queue link lands on the
   listing gap-filtered board); the preview renders BOTH fields plain
   (title was → becomes, description was → becomes, escaped); post-approve
   receipts read "showed up live? yes"; "localhost" never renders; add the
   new pages to the plain-first guard's walk list
   (test_catalog_dashboard.py:305-308).

**producer capture script** (the item is [product] — HARD cold read): copy the
walk shape the WF-approve round used — a script that boots `TestClient(app)`
against a SEEDED scratch db (COMMERCEOS_DB env), drives the real flow (arm →
preview → approve → receipts), and writes each page's HTML to
`reports/coldread-f4b/` (or /tmp) as numbered captures: home, /catalog,
/catalog/workflows, /catalog/workflows/seo, the run preview (mid-flight — the
arm-blindness scar), the post-approve run page, /approvals with the parked
consequential draft, /record. capture BEFORE and AFTER states of the pages the
check names. the producer walks captures, not the code.

## open questions

- **the p-numbers**: "209" (overview) and "235" (workflows index) are
  next-in-sequence, but the UI-polish backlog row holds a parked [owner]
  ruling on P-page numbers. recommendation: take 209/235 now (the pattern the
  four existing fronts set), and note it in the make note so the ruling can
  renumber once, cheaply. not a blocker.
- **the shopping feed**: the spec's check line says "AND the feed reads
  legible" — no feed surface exists in the cartridge today. the backlog row's
  check (the binding one) doesn't require it. recommendation: build to the
  backlog check; the feed leg stays with CW6's fold note for the sync.
