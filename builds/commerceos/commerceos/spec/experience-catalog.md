# the catalog interface — IA / experience spec

state: draft v1 — 2026-07-12. awaiting the owner's ratification. supersedes
the undesigned /catalog log; the visual register is teletext (RULED 2026-07-12),
the nav model is job-based (RULED 2026-07-12).

this spec is the interface CONTRACT: what each view communicates, to whom, for
which job, and the exact data, hierarchy, controls, filters, and navigation it
carries. the teletext look is applied AFTER the structure — it is not the
structure. every view names the job row it serves; a view that cannot is cut.

## who it serves

the **catalog operator** (Owner now, a merchandiser later) — the person who
keeps the catalog true and rules its judgment calls. the jobs (from
spec/jtbd.md, catalog-scoped):

- **O1** know the state — the catalog's health and what needs me, in minutes.
- **O2** decide — rule the judgment calls (delist, verify, relist) with context.
- **O3** delegate the routine — run enrichment without hand-touching every SKU.
- **O4** verify — every catalog act on the record, "why did X happen" answerable.

the customer (C2 choose-with-confidence) is served INDIRECTLY: this interface
is where the operator makes the specs true, the images real, the categories
right — so the storefront never lies. the customer never sees this surface.

## where it lives — the job-based nav (RULED 2026-07-12)

the operator interface is organized by intent, not by table name:

    home · decisions · operations · record · money · growth

**catalog lives under _operations_** (O3 — the routine, done to standard). the
catalog area carries its own sub-nav (the five views below). the top nav is the
one masthead; the sub-nav is the catalog channel's own index.

## the working loop (RULED 2026-07-12) — how the operator and the system move through a front

there is not one loop; there are two granularities, but **every front has an
approval step — nothing auto-lands** (RULED; supersedes the earlier
"reversible batches land with no /approvals stop"). the operator always gets a
glance before a change touches the store.

the loop, for every front:

    arm  ->  the system STAGES the batch as a PREVIEW  ->  operator APPROVES
         ->  execute  ->  verify-render  ->  the fact writes back, the meter moves

- **what the system receives (its input):** the queue (products carrying the
  gap) · the rule/source (checksum, taxonomy map, copy rules, manufacturer
  page) · the batch size.
- **what the system hands back (the preview):** per product — the exact
  **old -> new** change, its **source/evidence**, and (after execute) the
  **verify-rendered ✓/✗** receipt; plus the counts.
- **what the operator sees + does — by gate class:**
  - **reversible fronts (gtin, classification, seo): approve the batch after a
    glance.** the preview is a compact list of old->new changes + a sample; one
    approval lands the whole batch; then the run log streams and the meter
    climbs, each fix a receipt. halt is always available.
  - **consequential / fit-critical fronts (delist, spec-verification): rule per
    item, with evidence.** each proposal shows the product · the change · the
    WHY · the consequence; grouped so a queued batch is ruled fast; approve
    executes + verify-renders + records the lifecycle move.
- **what moves:** a verified change updates the product's coverage and, where a
  state changes, its lifecycle stage — so the effect shows as products moving
  across the board (below).

build implication (goes to the backlog, not silently here): run_feature needs a
**stage-preview-then-approve** mode (stage the batch, hold, execute on approval)
even for reversible fronts; the gate/web needs a **batch-approval** surface (a
glance-and-approve card for a reversible batch, distinct from per-item rulings).

## the five views

each view: the ONE question it answers · the hierarchy (what leads) · the data
it pulls · the controls/filters/nav · the teletext components.

### 1 · overview — "is my catalog healthy, and what's the one thing that needs me?"

- **hierarchy:** (a) the catalog health score + its trend, big, at the top;
  (b) the single call that needs a ruling, in the one earned amber accent
  (e.g. "N products are queued to remove from the store — not staged
  yet", pointing at the remove row, then decisions once staged — the
  ruled words; "flagged" is reserved for the review queue, one word one
  meaning per screen); (c) the enrichment fronts as index
  rows, ordered by leverage; (d) the state mix as a one-line bar.
- **data:** audit health-latest (overall + per dimension); for each feature in
  FEATURES — progress() + queue depth; lifecycle counts_by_state; review_queue
  count; catalog-scoped pending approvals.
- **controls/nav:** each feature row → its workflow view; each number → the
  products browser filtered to those rows; the amber call → flag review or
  approvals; run-batch arms a run (reversible lands, consequential parks).
- **components:** the marquee (health + product count); teletext index rows
  with block-mosaic meters (one per front); a P-block for the state mix; the
  one slap only on a true finished win; fasttext jump to the other views.

### 2 · products — "find and inspect the products I care about, and see where they all are"  [THE MISSING PIECE]

the operator has no way to browse, filter, or navigate the catalog today.
this view is a **combined board** (RULED 2026-07-12): the **stage pipeline and
the filterable table, fused into one surface** — you see products laid across
their lifecycle stages AND you filter/sort/search the same set. lean (not a
Shopify-admin clone — it shows what carries provenance and verify-renders,
nothing Shopify already owns).

- **the board:** stage columns — `draft · active · flagged · delisted ·
  archived` — each a lane with its live count and the products in it. this is
  the primary navigation: see where everything is, move across stages. a
  filter/sort/search bar sits above and constrains what shows in every lane at
  once (e.g. show only vendor=Osprey across all stages, or only products
  missing an image). so the pipeline and the table are one thing: columns for
  where a product IS, filters for which products you mean.
- **row / card content (per product in a lane):** title + handle · vendor ·
  category · the gaps it carries (chips: no-gtin / unclassified /
  unverified-specs / no-image) · last change. a compact card in the board; a
  full row when switched to table density.
- **columns (table density):** product (title + handle) · vendor · category ·
  lifecycle state · the gaps it carries · last change.
- **filters:** state (draft/active/flagged/delisted/archived) · gap (each
  enrichment front) · vendor · category · verified/unverified. filters compose
  (state=flagged AND gap=no-image). the active filter set is a shareable URL,
  never PII in the query.
- **tabs (the common use-cases as saved views, as built):** needs review ·
  worst health · recently changed. a tab is a named filter set; selecting it
  sets the filters. the other saved views live as gap chips and state
  filters (missing images = the photo gap chip; unverified fit-critical
  specs = the details gap chip; delisted = the state filter, set from the
  lanes and composed links), composing with everything else instead of
  holding tab slots.
- **sort:** by health (worst first, default) · by last change · by vendor.
- **search:** title / SKU / handle.
- **select → act:** select rows (or "all matching the filter") → run a workflow
  on that selection, gated (the selection is the batch scope). reversible lands;
  consequential/fit-critical parks in decisions.
- **nav:** a row → the product drill; every count on the overview links here
  pre-filtered.
- **components:** a teletext data table (P-block with a bell-blue header bar,
  monospace columns, cyan openable ids); a filter bar as teletext filter chips;
  tabs as page-numbers (P210 needs-review, P211 worst-health, P212
  recently-changed — as built).

### 3 · workflow view — "run and watch one enrichment front"

- **hierarchy:** the front's coverage now + its target; the queue (products
  carrying this gap); the run control; the last run's log + verify-render
  receipts; the front's config (source strategy, gate class).
- **data:** feature.progress + queue; the run report (staged/executed/counted/
  failed/errored per run); the config row.
- **controls:** run batch (with a size, honoring the RULED bulk size-cap);
  the queue → the products browser filtered to this gap.
- **components:** a P-block with the block-mosaic meter; a run-log ledger block
  (code-written lines, each verify-render a receipt).

### 4 · flag review — "rule the judgment calls"

- **hierarchy:** the flagged queue, each product with ITS EVIDENCE (why the
  quality gate flagged it — the signal list); the ruling actions.
- **data:** lifecycle.review_queue (flagged products + reason/evidence).
- **controls:** per product — keep (clear the flag) / delist / archive, each
  gated (a consequential proposal into decisions); bulk-rule a selection.
- **components:** a review-queue block, one row per flag with its evidence
  chips; the ruling as a gated action (never approves here — routes to decisions).

### 5 · product drill — "understand and fix one product"

- **hierarchy:** the product identity; its canonical claims each with provenance
  (source · verified chip · date); its lifecycle state + full history (who/when/
  why); the per-front gaps; the store preview (page = feed = JSON-LD).
- **data:** canonical_products + spec_claims (+ provenance); lifecycle
  state_of + history; per-feature queue membership; the emitter outputs.
- **controls:** edit a field — stages a gated proposal (never a direct write);
  run a single-product enrichment; the ruling actions (delist/relist/archive).
- **components:** teletext blocks — a claims block (each claim wears its ink
  chip: checked/claimed), a provenance block, a history timeline block, a
  store-preview block.

## navigation + linking (the law: every number opens to its rows)

- the catalog sub-nav: overview · products · workflows · flags (the drill is
  reached from a row, not the nav).
- every count anywhere is a link — to the products browser pre-filtered, or to
  a drill. no dead numbers. one lawful exception (the UI-truth ruling): a
  mirror reading with no front to open to yet stays doorless and wears a
  caption naming its door-to-come (p202's dimension rates; the masthead
  health score reads as the audit's figure, not a filter).
- always a path back to the rows behind a figure.

## the components, by register (teletext)

the ratified teletext layer (web/teletext.py + static/teletext.css) supplies:
the masthead marquee, the nav teletext-bar, the P-block (bell-blue bar + body),
the index row, the block-mosaic meter, the ledger/run-log line, the ink chip,
the filter chip, the one slap. supercolor is reserved for /parts (ownable),
never here. one earned accent per view (amber for the one call); cyan for links.

## data contracts (what each view queries — one reader per table-set holds)

- health + per-dimension: reports/health-latest.json (catalog-loop owns).
- feature progress + queue: each FEATURE's progress()/queue() (catalog-workflows).
- product rows + gaps: products + variants + product_meta + canonical_products
  + spec_claims, joined with product_lifecycle for state — a read-only browser
  query (the interface READS; it never writes a fact).
- lifecycle state + history + flags: catalog-lifecycle (sole writer; the view reads).
- approvals: the gate ledger pending queue, catalog-scoped.
- acting: every operator action leaves as a gate proposal — the interface holds
  no approve verb of its own (the one approve verb lives in decisions/approvals).

## checks (runnable; each names the surface where its result is seen)

- overview: the health number + each feature card's queue depth equal the audit/
  feature values; each fronted number links to exactly its rows, and a
  doorless mirror reading wears its why (the exception above). seen on the
  overview.
- products: a filter (state=flagged AND gap=no-image) returns exactly the
  products matching both, from the facts; a tab sets its named filter; a row
  opens the drill. seen on the browser.
- products select → run: selecting N products and arming a reversible front
  stages N proposals scoped to the selection. seen on the run log + decisions.
- workflow view: the run log shows staged/executed/counted with verify-render
  receipts; the meter matches the audit. seen on the workflow view.
- flag review: each flagged product renders with its signal evidence; a ruling
  fires a gated proposal (nothing executes here). seen on flag review + decisions.
- drill: the claims + provenance + lifecycle history render for a real product;
  an edit stages a gated proposal, not a direct write. seen on the drill.

## open [owner] / [design]

- RULED 2026-07-12 [owner]: the top-nav labels — home/decisions/operations/
  record/money/growth as proposed, built. still open inside it: whether
  "operations" holds only catalog or grows future operation types
  (campaigns, suppliers) — today /suppliers hangs off money instead.
- OPEN [owner]: the products browser default tab (proposed: needs-review).
- OPEN [design]: how much per-product editing before it clones Shopify admin —
  the drill edits only provenance-bearing, verify-rendering fields; the boundary
  is drawn but the exact field list is a build detail.
- OPEN [design]: phone layout — the browser table collapses to a stacked card
  list under a width; the overview + decisions are phone-first (O2 is decided
  from the phone).
- OPEN [design]: saved custom filters (beyond the fixed tabs) — later.
