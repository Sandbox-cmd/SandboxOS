# part: catalog-workflows
serves: O3 (delegate the routine) · C2 (choose with confidence, served first by
a clean, sourced, consistent catalog) · grounds O1 (a dashboard card per
feature) and O4 (every run on the record) · the catalog-operator jobs from
inventory.md: run a named feature, watch it close, rule the batches that need
judgment. (spec/jtbd.md, spec/inventory.md)
state: draft v1 — 2026-07-12. OPEN items marked.

## purpose

one engine that runs every catalog enrichment and curation feature. the owner
ruled it in-session (2026-07-12, RULED-pending-land): a catalog feature is not
its own program — it is the SAME machine every time. a queue of products that
share one gap → a gated batch the fleet runs → verify-rendered before it counts
→ progress on a dashboard card the operator watches. GTIN normalization,
taxonomy cleanup, merchandising, SEO close-out, spec-verification, delist — each
is a CONFIG ROW of this one engine, differing only in four dials: which field-
class it writes, where the corrected value comes from, which gate class it
carries, and what live check proves it landed.

the opportunity, not just the gap: today these workflows live buried inside the
loop as gap scores ranked by count × weight (catalog-loop.md, behavior 3). they
are real, recurring work — but they are nameless. an operator cannot pick "run
GTIN next", see its live percentage and how many barcodes are left, or hand a merchandiser one
feature to own. this part gives each feature a name, a queue depth, a run
control, and a progress card. the same mechanism that closes GTIN closes SEO and
every feature after it — so store #2 gets the whole feature system as config, not
a second build.

this part also builds the executors the feature system needs and does not yet
have: the product state-change write (delist / relist / archive, backlog C5w),
the spec-verification write that confirms the sources agree and returns the
receipt (C5w), and the smart-collection create the V1 merchandising feature
needs (create_collection, built 2026-07-19, backlog CW4). `spine/writes.py::execute()` executes
tags, title, metafield, variant barcode, and price today; it refuses state
changes and verify-flips (writes.py:95 — the `else: raise WriteRefused(f"no
executor for method {method}")` branch, and quality.py's own note that "no
executor for state changes exists yet"). this part is the sole author of these
executor BODIES, each added to that one door; the local record each write moves
is written by that table's OWNER, never by the executor (the one-writer-per-
table-set rule, AGENTS.md — RULED 2026-07-12).

## owns

- **the workflow-run object** — one row per batch run: id · feature · the
  product set (ids + the gap each carries) · batch size · staged proposals (the
  ledger ids) · gate class · status (drafting → staged → parked | executing →
  verified | failed) · verify-render result per product · progress delta. the
  run is the unit the dashboard card counts and the record remembers.
- **the per-feature config** — one row per feature (the schema below): the four
  dials plus the executor method it dispatches to and the queue predicate that
  defines its backlog. adding a feature is adding a config row, not code
  (proposed; the wave-2 rows exercise this claim).
- **the executor writes it is sole author of** — three gated methods on the one
  write door, `spine/writes.py::execute()`. it authors the executor BODIES (the
  mutation, the read-back, the verify-render check each returns); it does NOT own
  the door, the one-use handle wall, or the Shopify client — those stay with the
  gate+record part and the spine (RULED 2026-07-12: this ownership split is
  settled, not an open seam). the one-writer-per-table-set rule (AGENTS.md)
  governs every method here — the executor performs the Shopify write and returns
  the RECEIPT; the OWNER of each local table records the local change. this part
  never writes catalog-loop's or catalog-lifecycle's tables (RULED 2026-07-12):
  - `mutate_product_state` — delist / relist / archive. reads the store back and
    verifies the live state matches, then returns the verified outcome;
    catalog-lifecycle (sole writer of the product state field + the history row)
    records the state change on that outcome. C5w for the method; the delist
    feature's executor lands with backlog CW8.
  - `mutate_spec_verification` — on approval of a `verify_sources.py` proposal
    (C5w), it verifies page = feed = JSON-LD agree on the owner-ruled sourced
    value and returns the verify-render receipt; catalog-loop (the sole writer of
    the canonical record) records the provenance flip (verified:false → true,
    verified-on, cite) on that returned outcome. this executor does NOT re-derive
    the value and does NOT write catalog-loop's table itself.
  - `create_collection` (built 2026-07-19; the spec's earlier `collection-create` name trued to the shipped identifier) — creates a smart collection with its membership rule,
    reads it back, and returns the receipt (RULED 2026-07-12, backlog CW4). it is
    the write the V1 merchandising feature (backlog CW5) needs and did not have;
    built as a new gated method on the same door, with the same handle-first /
    read-back-is-the-receipt discipline as the two C5w methods.

## exposes

- **queue depth + progress per feature** to the web surface: for each feature,
  how many products still carry the gap, how many this run closed, in-flight,
  verify-render pass rate, last run, next batch. renders as a card per feature
  (see `## renders`).
- **run and verify events to the record**: `workflow.run.staged`,
  `workflow.run.executed`, `workflow.verify.rendered` (pass/fail per product) —
  pointers onto the shared log, so a run's whole life is auditable in under a
  minute (O4). every executor write already lands `write.executed`
  (writes.py:101); this part adds the run-level events above it.
- **the executed-and-verified state-change outcome to catalog-lifecycle (the
  return leg)**: when a run executes a delist / relist / archive — whether from
  the delist feature's own batch or from a state-change request lifecycle ruled
  — its per-product verified outcome returns to catalog-lifecycle, which is the
  SOLE writer of the product state field and the transition-history row. the run
  object records the execution mechanics; it is never the system of record for
  lifecycle state. (RULED 2026-07-12: this return leg is settled — without it a
  batch delist would leave the store pulled but lifecycle still reading `active`,
  with no history row.)

## consumes

- **the audit's gap scores and the work queue** from the catalog loop
  (catalog-loop.md owns both): the loop scores the 7 dimensions and ranks gaps;
  this part reads that ranking to fill each feature's queue. it does not
  re-audit — the loop is the single source of what is broken.
- **state-change requests from catalog-lifecycle**: the delist / relist /
  archive transitions lifecycle rules — lifecycle's state model owns WHEN a
  change is legal, this part owns HOW it executes. the delist feature's queue is
  these requests reconciled with quality.py's flags, not an independent read
  behind lifecycle's back, so a state change has one path and one recorder (the
  return leg is in `## exposes`).
- **approved one-use handles from the gate**: every write in a run executes only
  under a handle keyed to its ledger id and bound by args-hash
  (gate-and-record.md). no handle, no write — the wall this part's executors
  obey, never bypass.
- **source material per feature**: deterministic (the stored artifact itself, for
  GTIN) · instance data (the taxonomy leaf map, for classification) · a record
  field + rule (the customer-category field, for merchandising) · fetched pages
  (manufacturer spec pages, for spec-verification) · owner rulings (the quality
  flags, for delist). the source strategy is a config dial, not engine code.
- **the fleet's hands**: the catalog agent and the content/SEO agent
  (fleet.md's V1 roster) are the executors that run the batches this part arms;
  single writer per field-class is enforced at the connector, honored here by
  routing each feature to the agent that owns its field-class.

## mechanism vs config

THE central section. the one engine is the mechanism; each feature is a config
row. store #2 gets the engine unchanged and writes its own feature rows.

a field-class is the set of Shopify fields one fleet agent is the sole writer
of; fleet.md's V1 roster IS the field-class → agent map — the catalog agent
owns product fields + publish state, the content/SEO agent owns pages, meta,
structured data, and the feed. "routes to the owning agent" below means: look
up the target field-class in that roster.

**the config schema** (one row per feature):

    feature            unique name — "gtin-normalization", ...
    target_field_class the writer-class it may write (routes to the owning
                       agent; the connector enforces single-writer)
    source_strategy    where the corrected value comes from
    gate_class         reversible | consequential | fit-critical (the gate
                       computes its own and takes the stricter — no downgrade)
    batch_size         products staged per run (humane queue; proposed sizes)
    verify_render_check the live-surface assertion that makes a product count
    progress_metric    the audit dimension / count this feature moves
    executor_method    the writes.py method a run dispatches to
    queue_predicate    the gap that defines this feature's backlog

**the V1 feature rows** (all RULED 2026-07-12, gate classes RULED; batch sizes
proposed):

| feature | target field-class | source strategy | gate class | batch | verify-render check | progress metric | executor method |
|---|---|---|---|---|---|---|---|
| gtin-normalization (the template — build first) | `variant.barcode` | deterministic: unwrap the apostrophe artifact, restore the dropped UPC leading zero — no external fetch | reversible | a batch at a time | GS1 checksum valid on the live barcode AND the Google feed accepts it | identity/GTIN up, with the queue depth live | `mutate_variant_field` (exists) |
| classification / taxonomy cleanup | product taxonomy field (`commerceos.category`) | source-anchored leaf map first, keyword rules only as fallback (the loop's classify) | reversible | a batch at a time | resolves to a locked taxonomy leaf AND its smart collections settle | classification up, with unresolved + fold-bucket counts live | `mutate_product_field` (metafield) |
| merchandising / smart collections | customer-category field + collection membership | persist the customer category as a field, rule smart collections on it (the v0 keystone: a couple of dozen collection creates, not a write per product) | reversible | a collection create per definition | collection membership renders live for a sample product | collection-coverage 0 → (near) full — the share of products that belong to at least one smart collection (RULED 2026-07-12). this is a NEW measure the card headlines; it is NOT the audit's existing "merchandising" dimension (a tag-presence proxy), which stays its own separate dimension | `mutate_product_field` + `create_collection` (built 2026-07-19) + `mutate_menu` (main-nav placement, RULED both-now by the owner 2026-07-19; CONSEQUENTIAL — a menu write replaces the whole tree, parks per item) |
| SEO close-out | pages / meta / title / feed (content-agent writer-class) | generated from the record's fields, brand token isolated (parked name, rebrand-safe) | reversible content | a batch at a time | title + meta render on the page AND the feed reads legible | seo up, with the title/meta gap count live | `mutate_seo` (S1, built 2026-07-18 — supersedes the earlier `mutate_product_field` (title) + meta write sketch) |
| spec-verification (fit-critical) | `spec_verification` provenance flip | manufacturer public spec pages ONLY, one fetch per product (the D4 mechanism, verify_sources.py) | fit-critical (always parks) | a small pilot batch | page = feed = JSON-LD agree AND the verified flip lands with its cite | specs verified 0 → N | `mutate_spec_verification` (build, C5w) |
| delist / lifecycle | product state | quality.py's noise + decor flags, plus the owner's ruling per flag class | consequential (parks) | per flag class | the product's live state on the store matches (a delisted product is off the storefront), verify-rendered | all 29 flagged delisted — 17 noise + 12 decor (RULED 2026-07-12); the held near-misses stay | `mutate_product_state` (build, backlog CW8) |

**the wave-2 feature rows** (shape specced, marked [wave 2] — proposed):

| feature | target field-class | source strategy | gate class | verify-render check | progress metric |
|---|---|---|---|---|---|
| image sourcing [wave 2] | product media | hybrid: supplier feeds / manufacturer pages / commissioned shoots (the biggest open front — the strategy is OPEN [owner], catalog-loop.md) | reversible media-attach | the image resolves live in a browser (the image scar test — a run never lowers the store's image count) | images up, with the count of products carrying none live |
| Arabic translation / localization [wave 2] | locale translations (translation metafields) | generated + human confirm; fit-critical specs stay gated | reversible content | the localized surface renders in Arabic as real as English (C2) | AR coverage per surface |
| descriptions / copy generation [wave 2] | product description / body | generated from the record's typed claims, never invented specs | reversible content | the description renders and states no unsourced spec | description coverage |
| duplicate / fold consolidation [wave 2] | product state + merge/redirect | dedup detection over the record | consequential (a merge removes a product) | the surviving canonical product renders AND redirects from the folded handles resolve | fold-bucket → down |

- **mechanism** (store #2 unchanged): the run object, the batch orchestrator,
  the stage → gate → execute → verify-render → progress loop, the three new
  executor methods (state-change, spec-verification, collection-create), the
  dashboard-card renderer, the run log.
- **config** (store #2's file): the feature rows above — the four dials per
  feature, batch sizes, cadence.
- **data** (this store): the taxonomy leaf map, the fit-critical field list,
  the quality-flag terms — all already owned by the loop and the gate; this
  part reads, never re-keeps them.

## behavior

1. **one workflow run, queue → progress.** the operator (or an armed schedule)
   picks a feature. the engine reads that feature's queue_predicate against the
   loop's gap scores, takes the top `batch_size` products, and the owning fleet
   agent stages exact changes as gate proposals — one per product, or batched per
   class where humane (delist parks one proposal per flag class, quality.py's
   shape). reversible features (GTIN, classification, SEO, merchandising) execute
   through the gated connector and land on the record; consequential and
   fit-critical features (delist, spec-verification) park in the approval queue
   and the run pauses for the owner. after each write the engine reads the live
   surface and runs the feature's verify_render_check; a product counts as done
   only when that check passes (the files-exist scar — verify-rendered is the
   loop's law, catalog-loop.md behavior 5). the run's progress delta is the
   count that passed. nothing counts on a stage; only on a verified render.
   AND, after the run's writes, the engine reads the live store image count and
   FAILS the whole run if it dropped — a store-wide invariant on EVERY feature
   run, not one feature's check (the recorded media scar: a v0 push dropped
   store media to a fraction of a percent, caught only by the live audit).
2. **the executor performs a state change.** `mutate_product_state` runs an
   approved delist/relist/archive proposal: it validates and consumes the
   one-use handle BEFORE any network call (the wall, writes.py:69), mutates the
   product's state via the Shopify client, reads the state back, and returns
   `verified_rendered` true only if the live state matches the intent (a
   delisted product no longer on the storefront). failure fills the outcome
   `failed` and raises — never a silent half-write. the verified outcome then
   returns to catalog-lifecycle, which commits the new state and appends the
   history row — the run object records execution; lifecycle is the record of
   state (the return leg, `## exposes`; RULED 2026-07-12).
   BUILD TASK (RULED 2026-07-12, lands with backlog CW8): quality.py today emits
   `method="mutate_product_field"` with `args.state="delist"` (quality.py:50) and
   no `field` arg. when this `mutate_product_state` executor lands, quality.py
   MUST be updated to emit `method="mutate_product_state"` with the arg shape this
   executor reads, then re-run to re-park the delist proposals — otherwise an
   approved delist routes to `_mutate_product_field`, KeyErrors on `args['field']`,
   and check 2 fails. this is a build task, not an open question.
3. **the executor performs a verify-flip.** `mutate_spec_verification` runs an
   approved spec-verification proposal (verify_sources.py's shape): for each
   claim the owner approved with verdict `agree`, it confirms the manufacturer
   source, then re-reads page, feed, and JSON-LD and returns `verified_rendered`
   true only if all three agree on the value. catalog-loop — the sole writer of
   the canonical record — records the provenance flip (verified:true, verified-on
   today, the manufacturer source_url as cite) on that verified outcome; this
   executor never writes catalog-loop's table itself (RULED 2026-07-12: the
   one-writer division is settled). conflicts (`disagree`) are never flipped —
   they were stated for
   the ruling, not resolved. no source on an approved claim is a construction
   failure and refuses (no source, no claim).
4. **a run resumes after approval.** a parked run's proposals sit pending; the
   owner approves on `/approvals`; approval mints the one-use handle
   (gate-and-record.md behavior 3); the engine re-raises the run's agent with
   the handle, executes the exact stored proposal, verify-renders, and fills the
   run's progress. an approved-but-not-yet-executed run is `parked`; on execution
   it moves `executing → verified`. the agent never resolves its own gate.
5. **expiry / lapse interaction.** a parked proposal past its expiry flips to
   `expired` (gate-and-record.md behavior 5) — no longer approvable or
   executable. the run marks those products lapsed and leaves them in the
   feature's queue; re-running the feature re-proposes them with current numbers
   (verify_sources.py already skips anything still pending, so a re-run never
   stacks the queue). a stale approval never fires on changed conditions — a
   barcode or spec that drifted under a lapsed proposal re-enters as fresh work.

## renders

the no-blackbox contract (O4): if a feature runs, it renders. this part is the
SOURCE of the per-feature numbers but does not host the operator feature-card:
catalog-dashboard renders that card on `/catalog` (the owner's hybrid-dashboard
ruling), and this part supplies the numbers behind it. this part renders its own
generic self-report row under `/parts/catalog-workflows` (the web surface's
registry-driven view, web-surface.md) plus the run detail it owns:

- **the feature numbers behind each card** — name · queue depth (products still
  carrying the gap) · closed / in-flight / lapsed · verify-render pass rate · the
  audit dimension it moves, with its delta since last run · last run and next
  batch · the run-control arm target. catalog-dashboard renders these as the
  operator's "which feature next, and how far is it" card on `/catalog`; this
  part is their single source, not a second card (the card-home direction is
  settled: dashboard renders the card on `/catalog`, this part exposes the
  numbers — see the per-feature registry seam in `## open`).
- **the run log** — per run: the product set, the staged proposals (ledger ids,
  linking to `/record`), the gate decisions, and the per-product verify-render
  result (pass / fail, with the live value read back). a failed run reads why.
- **the verify-render result** — the receipt that a product counted: the live
  value pulled from the store, side by side with the intended value. never
  "logs to a file nobody opens" — the result is on the card and drills to the
  ledger id behind it.

## checks

runnable, each naming the surface where its result is seen:

1. **the GTIN template, end to end** — arm a GTIN batch of N artifact barcodes;
   the run stages N `mutate_variant_field` proposals (reversible); execution
   writes each; the engine reads the live barcode back, the GS1 checksum
   validates, and the Google feed accepts it. seen on: the gtin card's queue
   depth drops by the count that passed, and each product's verify-render result
   shows the live barcode. a barcode whose checksum fails does NOT count. AND the
   store's live image count does not drop across the run — the run fails if it
   does (the store-wide image scar guard, applied to this first-built feature).
2. **the state executor** — an approved delist proposal executes: the handle is
   consumed once, the product's live state flips, and the read-back confirms it
   is off the storefront. seen on: the delist card's closed count and the run
   log's verify-render result; the ledger holds one `write.executed`. a replay
   of the same handle is refused (writes.py wall).
3. **the verify-flip** — an approved spec-verification proposal lands
   verified:true with its cite on every agreeing claim, flips nothing on a
   conflict, and page = feed = JSON-LD agree on the verified value. seen on: the
   spec-verification card's verified count and the run log; the provenance
   invariant (zero specs verified-without-source) still holds store-wide.
4. **verify-rendered gates the count** — force a write to succeed but the live
   read to disagree; the product is NOT counted done, the run marks it failed,
   and the card's pass rate reflects it. the scar test applies to EVERY run
   regardless of feature: a run that touches products never lowers the store's
   image count, and the engine fails the run if it does (the wave-2 image
   feature keeps its own additional image-resolves-live check on top).
5. **feature as config** — add a wave-2 feature as one config row (no engine
   code); its card appears on `/catalog` (catalog-dashboard renders it from this
   part's numbers) and its queue fills from the loop's gap scores. removing the
   row removes the card.

## v0 salvage

mine:
- **the loop engine** (catalog-loop.md) — this part is the loop's "act (gated)"
  phase named and surfaced per feature; it reuses the loop's queue, gap scores,
  emitters, provenance model, and the verify-rendered law rather than rebuilding
  them.
- **the proposal shape** — `quality.py`'s one-proposal-per-flag-class delist
  parking and `verify_sources.py`'s one-proposal-per-product fit-critical
  parking are the two batch shapes this engine generalizes; their gate wiring
  (declared class, stricter-of-two, park-not-approve, re-run skips pending) is
  the run's staging contract.
- **the write-door dispatch** — `writes.py::execute()`'s method dispatch
  (writes.py:88) is the seam the three new executor methods slot into: same
  handle-first wall, same read-back-is-the-receipt discipline.

do NOT port: any ungated write path. every executor write goes through the
handle wall or it does not run; the delist and verify-flip methods refuse
without an approved, unexpired, unused, args-hash-matched handle — exactly as
the existing methods do.

## open

- OPEN [design] — **the per-feature registry seam (workflows data vs dashboard
  view vs web-surface).** the web surface's registry is one row per PART
  (web-surface.md); this part is one part but has MANY features. resolved
  direction (aligns with the owner's hybrid-dashboard ruling): this part OWNS a
  `workflow_features` table (one row per feature — queue depth, progress,
  verify-render rate) and EXPOSES it; catalog-dashboard renders the feature cards
  from it on `/catalog`; the one-row-per-part `parts` registry stays for this
  part's generic self-report only. FOLD-UP for the web-surface owner: add a line
  to web-surface.md acknowledging part-owned satellite tables (like
  `workflow_features`) that a workspace route renders, so the multi-card contract
  is a named pattern, not a bespoke view.
- OPEN [owner] — **wave-2 source strategies + the media-attach executor.** image
  sourcing (supplier feeds vs scraping rights vs commissioned shoots) is the
  biggest open front and rides on the owner's call (catalog-loop.md); Arabic
  localization and copy generation need a source and a human-confirm step ruled
  before they run. the media-attach write these wave-2 features need does not
  exist in writes.py and is not in V1 scope — build it with image sourcing
  (wave 2), a new gated method on the one door, same pattern as the V1 methods.
  (collection-create, the OTHER previously-missing executor, is now RULED V1
  — backlog CW4, see `## owns`.)
- OPEN [design] — **batch sizing and cadence.** the batch sizes above are
  proposed, not measured; pick real sizes from the first GTIN run's cost and the
  owner's approval appetite. cadence (how often an armed feature runs a batch)
  starts owner-armed — nothing self-schedules (fleet.md, gate-and-record.md);
  the scheduled-run shape is OPEN until the fleet's scheduler lands.
