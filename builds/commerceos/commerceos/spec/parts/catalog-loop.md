# part: the catalog loop
serves: O3; grounds C1, C2 (spec/jtbd.md)
state: draft v1 — 2026-07-11; open items trued up 2026-07-18.

## purpose

the standing loop that keeps the catalog true: ingest → audit → prioritize
→ act (gated) → verify rendered → decay/re-test. not an import script — a
loop that never declares itself finished. the catalog is where customer
trust is made: a typed spec with a source is something the store (and later
the concierge) can stand on; the same number buried in a text blob is
nothing. this loop ran in v0 and moved the dev store from 34.2 to 66.0 in
one night; this part rebuilds that shape clean on the new spine.

## owns — the canonical product record (spec claims with provenance), audit scores + health reports, the work queue (prioritized gaps), per-channel emitters

- one canonical record per product. every spec claim carries provenance:
  source, verified flag, verified-on date, unit, standard (proposed —
  today only the `std` key in the product_meta provenance companion, not
  yet a spec_claims column), fit-critical
  flag. a value parsed from a supplier blob stays verified:false until a
  real source resolves it. no source, no claim — silence over guesses (C2).
- audit scores + health reports: per-dimension pass rates, a weighted
  overall score, a dated report plus machine state so every run shows its
  delta against the last.
- the work queue: gaps ranked by count × impact weight, consumed by the
  catalog agent.
- per-channel emitters: Shopify fields, Google feed, JSON-LD — all emitted
  from the one record, so page, feed, and structured data cannot disagree.
  C2's consistency is built in, not checked after.

## exposes — health state to the web surface and watching; enrichment work orders to the fleet's catalog agent; emitted outputs to connectors

- health state to the web surface (part 7) and to watching (part 2): score,
  dimensions, deltas, open fronts. a health drop is a finding like any other.
- work orders to the catalog agent (part 4): the queue's top items, each
  with the gap, the products, and the evidence.
- emitted outputs to connectors (part 1): staged payloads only. this part
  never writes to the world itself.

## consumes — source files (exports, stock-movement, datasheets), live store state via the data spine, taxonomy (instance data), approved handles via the gate for writes

- source files: products_export CSVs (the load seed) · stock-movement CSVs
  (brand/MPN/spec backfill) · datasheets (OPEN: ingestion shape) ·
  sell-through data for priority order.
- live store state via the data spine — the audit reads what customers see,
  never what we intended to push.
- the store's taxonomy as instance data, carried as-is: locked categories,
  per-category spec schemas with fit-critical flags, the source-leaf map.
- approved handles via the gate (part 3) for every write: fit-critical spec
  fields and publish state are consequential and pause for the owner;
  reversible structure runs and is recorded.

## mechanism vs config — loop engine + emitters vs per-store audit dimensions/weights, taxonomy, source list, fit-critical field list

- mechanism (store #2 uses unchanged): the loop engine, the emitters, the
  spec-extraction pattern library, the provenance model, scoring + delta
  tracking, the queue.
- config (store #2 tunes): audit dimensions and weights — classification,
  specs, provenance, identity/GTIN, merchandising, seo, images · the source
  list · the fit-critical field list · decay window · quality-flag terms.
- data (this store's file): taxonomy v1.2, market priors, the source CSVs.
- the v0 engine knew nothing about outdoor gear and the seam held — editing
  the taxonomy changed behavior with no code change. keep that seam.

## behavior — numbered flows

1. **ingest a source**: extract → normalize → classify (source-anchored
   map first, keyword rules only as fallback) → structure specs (patterns
   scoped to the category's schema) → quality flags (decor leakage flagged
   for the owner, never auto-deleted) → validate (critical blocks, warn
   reports) → stage. everything on our side; no world writes.
2. **audit pass → scored health report**: enumerate the live rendered
   surface via the spine, score every product per dimension against the
   taxonomy, aggregate. emits the dated report + machine state with deltas.
   read-only; fails closed if the live read fails.
3. **prioritize (gap × impact)**: rank the backlog by failing count ×
   dimension weight. V1 weights are config; the business axis (conversion,
   citation, concierge misses) joins when traffic exists — designed now,
   not faked now.
4. **act (gated writes via catalog agent)**: the agent takes queue items,
   stages exact changes, and submits them. consequential items pause at the
   gate; an approved handle is one-use and the connector rejects writes
   without one. every act lands on the record with intent and rationale.
5. **verify rendered (pull the live surface, compare)**: after any act,
   read the store as a customer's browser would — the page shows the spec,
   the feed carries it, the JSON-LD renders, collections settled, images
   resolve. diff against intended; the delta is the receipt. a push without
   this step is not done — law, not a step to skip under time pressure
   (the files-exist scar recurred across four bodies).
6. **decay/re-test on cadence**: a verified spec older than the decay
   window (config; v0 used 365 days) re-enters the queue; drift and new
   arrivals re-enter via the next audit. the score is an output, never a
   target.

## renders — self-report: health score by dimension with deltas, open fronts with counts, last verify-rendered results, work queue depth

on the parts view (spec/experience.md): overall score and per-dimension
pass rates with deltas since the last audit · open fronts with live counts
(the open fronts as the live audit reads them today)
· the last verify-rendered sample with pass/fail per product · queue depth
and the top items · last run, next run.

## checks — runnable

- audit the dev store: a scored report is produced, and a hand spot-check
  of 20 products matches the report's per-dimension calls.
- an enrichment write round-trips: staged → approved at the gate → live →
  verified rendered — every step on the record, one ledger id end to end.
- emit page, feed, and JSON-LD for a 50-product sample: spec values are
  identical across all three surfaces.
- the image scar test: a push that touches products never lowers the
  store's image count; verify-rendered fails the run if it does.
- provenance invariant: zero specs verified-without-source, store-wide.

## v0 salvage

- keep the shapes, rebuilt clean: the loop's six phases · the 13-stage
  ingest design (extract → normalize → classify → structure-specs →
  enrich-gaps → govern-tags → build-collections → seo → validate → stage →
  upload → verify-live → reconcile) · audit dimensions with weighted
  scoring and a health-latest delta file · count × weight backlog ·
  provenance companion per spec field · definitions-first metafields ·
  the keystone lesson: persist the customer category as a field and rule
  smart collections on it (a couple of dozen collection creates lift
  collection-membership coverage — the share of products in a collection,
  NOT the audit's tag-presence dimension — instead of a per-product write
  for every product in the catalog) · SEO
  with the brand token isolated
  (rebrand-safe — the name is parked) · conservative quality flags (a home
  brand alone never flags; it only corroborates a decor path or keyword) ·
  staged output the owner can eyeball before any push.
- do NOT port: hardcoded ~/Downloads and repo-relative paths · sys.path
  import hacks · gate_core / shopify_live kernel hooks (the gate is part 3
  now, the connector part 1) · .mind spec references.
- the scar to test against: an old push dropped media — images landed at a
  fraction of a percent and only the live audit caught it; the same night,
  the tracking file's own count was stale by thousands. one lesson twice:
  the rendered surface is the only truth. the image scar test above exists
  because of this.

## open — OPEN questions

- OPEN: datasheet PDF ingestion shape — per-vendor PDFs into typed claims:
  manual extraction into a form, or parsed with human confirmation?
  fit-critical claims need a citable source either way.
- RULED 2026-07-18 [owner]: image sourcing — hybrid: supplier/brand feeds
  where rights allow, commissioned shoots for hero products, no scraping.
  the biggest open front now has its route.
- OPEN: GTIN sourcing route — supplier data vs GS1 lookup; cost unknown.
- RULED 2026-07-12 [owner]: delist — demo-noise and decor-leakage products
  delisted; an earlier flag count had gone stale. the loop flagged, the
  owner ruled, the delist ran — flag-never-delete held.
- OPEN: audit cadence — cheap enough to run daily on the dev store; pick
  when S2 lands. like everything, scheduled runs start owner-armed.
- OPEN: where the canonical record lives day one — proposed: the spine's
  SQLite from the start, emitters read it (v0 staged JSONL files instead).
