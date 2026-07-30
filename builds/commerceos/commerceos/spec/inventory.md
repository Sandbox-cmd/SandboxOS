# inventory — catalog management as a feature system

mode: interactive (owner at the terminal, 2026-07-12)

scope of this run: reframe catalog work from a pile of one-off fixes into a
feature system — recurring workflows (image sourcing, GTIN normalization,
spec/attribute enrichment, SEO) plus a product lifecycle the operator runs
from a dashboard (flag → review → delist → edit → relist → archive). this
folds existing backlog items D2, D3, D4, C5w, and the delist ruling into one
coherent set of features, each reusing the one catalog-loop mechanism.

this is a re-frame of an existing, partly-built system, not a green field.
the format is sized down: movement 3 (frame) is skipped out loud — the
direction is ruled (commission marketplace, 2026-07-11; catalog-as-feature-
system, 2026-07-12).

## what already exists and works (verified live, not claimed)

built and passing their own checks against a real catalog:

- **the audit** (`commerceos/catalog/audit.py`) — read-only health scorer,
  7 dimensions, weights in config (`stores/<store>/audit-config.json`).
  scores all 7: an overall out of 100 plus a per-dimension breakdown
  (provenance, merchandising, classification, seo, specs, identity/gtin,
  images).
- **the canonical record** (`canonical.py`) — one record per product, one
  claim per (product, field), provenance on every claim.
- **the emitters** (`emitters.py`) — page / Google feed / JSON-LD, all from
  the one record, consistency re-checked on the rendered output. machine
  surfaces carry verified claims only.
- **the delist detector** (`quality.py`) — flags noise + decor-leakage
  products, submits one gate proposal per class, parks, never deletes.
- **the spec-verification pilot** (`verify_sources.py`) — checks parsed
  claims against manufacturer pages only, computes agree/disagree/not-found,
  parks a fit-critical proposal per product.

## the correction the scouts landed

- **A8 (widen the sync) is effectively done.** the sync landed metafields,
  media, seo, collections; the audit scores all 7 dimensions. the backlog's
  "next pulls: A8 -> D2 -> D3 -> D4" line is stale. confirm and mark A8 done.
- the older backlog's numbers were the v0 re-baseline, scored on fewer
  dimensions. the current landed facts supersede them — and the delist
  counts were recomputed under a conservative two-signal law.

## what the catalog actually contains (the real work)

the shape of the work, which recurs on any store that grew by import:

- **images.** a catalog can carry near-zero real media while a handful of
  platform demo fixtures make the number look non-zero. the true gap is
  read from the live audit, never from a tracking file.
- **gtin.** most invalid barcodes are one normalization away — apostrophe-
  wrapped values and dropped UPC leading zeros dominate. a gated cleanup,
  not a sourcing project.
- **specs.** claims present but unverified: source
  `parsed:supplier-spec-blob`, verified:false, waiting for a real source.
- **delist.** noise and decor-leakage products, parked as proposals,
  awaiting the ruling and an executor.

## the gaps this run closes (both confirmed absent in the specs)

1. **no product lifecycle.** there is no state model for flag → review →
   delist → edit → relist → archive. only ad-hoc gated publish/delist
   actions, an inherited Shopify `status` field, and a "flag, never delete"
   quality convention. no transitions, no relisting path, no archive.
2. **no operator dashboard for catalog.** catalog self-reports a health card
   into the generic `/parts` view and drops write cards into `/approvals`.
   there is no console to browse products, see per-product state + health,
   resolve flags, or launch a workflow batch. `experience.md` explicitly
   disclaims being "a Shopify admin duplicate" — so the operator surface has
   to earn its place, not clone Shopify.
3. **the recurring workflows are internal, not features.** images / gtin /
   specs / seo live inside the loop as enrichment gaps ranked by count ×
   weight. they are not named, operator-facing features with their own
   queue, run control, and progress. the mechanism is right (a loop that
   never finishes); the surfacing is missing.

## what is right and stays (the mechanism to build on, not replace)

- the catalog loop is already specced as "a loop that never declares itself
  finished" — ingest → audit → prioritize → act (gated) → verify rendered →
  decay/re-test. recurring is already the design.
- one canonical record; per-channel emitters; provenance on every claim;
  verify-rendered is law; single writer per field-class; the gate wall
  (no catalog write without an approved one-use handle).
- **salvage posture:** reuse the loop engine, emitters, provenance model,
  audit, scoring, the queue. what this run adds is a lifecycle state model,
  named workflow features over the one loop, and the operator dashboard —
  configuration and surfacing of the existing mechanism, not new anatomy.

## the executors this run must serve

- **the catalog operator** (Owner, later a merchandiser) — under-served
  today. owns judgment: which flags to act on, which workflow to run next,
  what to delist/relist/archive, when a batch is good enough to approve.
- **the agent fleet** (already the executor of O3, delegate-the-routine) —
  the hands that run the workflows the operator arms.
- (downstream) the **store customer**, served indirectly: true specs, real
  images, consistent surfaces are what the workflows produce for them.

## the seam that governs execution

the only write door is `spine/writes.py::execute()`. it executes
tags/title/metafields, variant barcode, and price. it does NOT yet execute:
a product state change (delist/publish) or a spec-verification flip
(verified:false → true). those are C5w — the executor this feature system
needs before any lifecycle action or verify-flip is real. no catalog write
before the gate (A6, done); no lifecycle action before its executor.
