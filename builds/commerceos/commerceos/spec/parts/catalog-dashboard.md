# part: catalog-dashboard
serves: the catalog-operator jobs from inventory.md (the operator who owns
judgment — which flags to act on, which workflow to run next, what to
delist/relist, when a batch is good enough to approve); O1 know-the-state
(catalog health and what waits on me, in one view); O4 verify (every number
opens to its rows, every claim to its provenance, every act to its record —
if it runs, it renders).
state: draft v1 — 2026-07-12. OPEN items marked. the hybrid shape and the
not-a-Shopify-clone boundary are RULED-pending-land (owner ruled 2026-07-12).

## purpose

the console the operator runs the catalog from. today catalog self-reports
one health card into the generic `/parts` view and drops write cards into
`/approvals` — there is no place to browse the catalog, see any one
product's state and health, resolve a flag, or arm a workflow batch. this
part is that place: a home screen of one card per catalog feature (images,
gtin, classification, merchandising, seo, spec-verification, delist), and
behind it a product browser and a per-product drill where the operator edits
one product without a direct write.

it earns its screen by being the anti-blackbox surface. it shows what a
Shopify admin does NOT: a gap-scored health number per product, a run
control that arms a gated enrichment batch, the provenance behind every
claim, and the verify-rendered proof that a change actually landed on the
live surface. it is holistic on purpose — it surfaces openings (an
under-served category, and a plain list-price SUM over the delisted set,
labeled as such — recoverable by relisting, but shown as a sum, never a revenue
projection), not only gaps.

this part OWNS the operator surface and its routes. it does NOT own product
state (that is catalog-lifecycle) or the workflow engine (that is
catalog-workflows). it renders their data and sends operator intents — run a
batch, rule a flag, edit a product — to them through the one gate. it invents
no second approve verb: arming a batch and approving its staged writes go
through the SAME gate/approvals resolve path the whole surface already uses.

## owns — the /catalog routes + the operator views; NOT state, NOT the engine

- **the routes** — a new route family under the web surface:
  - `/catalog` — the home: the feature cards + the flags card.
  - `/catalog/products` — the product browser (filter/sort).
  - `/catalog/products/{id}` — the per-product drill + edit.
  - `/catalog/flags` — the flag-review queue (may render as a panel off the
    home flags card; same data either way).
  (OPEN [design]: whether `/catalog` is its own top-level route or a section
  under `/parts` — see ## open.)
- **the operator views** — the feature-card layout, the browser table with
  its filters, the per-product drill layout, the flag-review panel. these are
  render code and view state only.
- what it does NOT own: product lifecycle state, transitions, and history
  (catalog-lifecycle) · the workflow queues, run engine, and batch execution
  (catalog-workflows) · the canonical claims and provenance (catalog-loop) ·
  the gate, the ledger, and the approvals resolve verb (gate-and-record via
  web-surface). this part reads all of them and writes none of them directly.

## exposes — operator intents: run-batch, rule-flag, edit-product — all through the gate

these are operator gestures the surface captures and forwards. none is a
write; each becomes a gate proposal that the operator lands through the
existing `/approvals` resolve path.

- **run-batch(feature, scope)** — the operator presses [run batch] on a
  feature card. the surface asks catalog-workflows to stage a run over the
  scoped products; what happens next follows the feature's gate class (RULED per
  feature in catalog-workflows) and the bulk size cap (RULED 2026-07-12): a
  REVERSIBLE feature (GTIN, classification, SEO, merchandising) whose batch is AT
  OR UNDER the config size cap `bulk_confirm_cap` runs through the gated connector
  and lands, and the card moves with the verify-rendered result — no `/approvals`
  stop. a reversible batch OVER that cap asks the owner ONCE at `/approvals`
  (one confirm for the whole batch, not one per write) before it lands. a
  CONSEQUENTIAL or FIT-CRITICAL feature (delist, spec-verification) ALWAYS parks
  its staged writes in the SAME `/approvals` queue and waits for the owner,
  regardless of size. no new approve verb any of these ways.
- **rule-flag(flag_id, ruling)** — the operator rules a flag in the review
  panel (e.g. delist / keep / relist). the surface forwards the ruling to
  catalog-lifecycle, which fires exactly one lifecycle transition — recorded,
  and where the transition writes to the world, gated like any write.
- **edit-product(id, field_changes)** — the operator edits one product in the
  drill. the edit does not write; it stages the exact field changes as a gate
  proposal that appears in `/approvals`, lands on approval, then verify-renders
  (edit → stage → gate → live → verified). a direct-write editor is forbidden.

every intent leaves the surface as a proposal and returns as a rendered
outcome over SSE — the same round-trip web-surface already runs for approvals.

## consumes — queue depth + progress from workflows; state + flags + history from lifecycle; claims + provenance from loop; the gate/approvals resolve path; audit health

- **catalog-workflows** — per-feature queue depth (how many products carry
  this gap), progress (rate/coverage now vs the run's start), and run state
  (armed, running, staged, done). the feature cards render from these live
  numbers.
- **catalog-lifecycle** — per-product lifecycle state, the open flags with
  their evidence, and the transition history. the browser filters on state,
  the drill shows state + history, the flag panel shows flags + evidence.
- **catalog-loop** — the canonical record: per-product claims, each with its
  provenance (source, verified flag, verified-on, unit, fit-critical — and
  `standard`, proposed: not yet a spec_claims column, it lives only as the `std`
  key in the product_meta `_provenance` companion and needs promotion before the
  drill can render it) and the last verify-rendered result. the drill shows
  claims +
  provenance; the audit's per-dimension pass rates back the card rate numbers.
- **the gate + record** (via web-surface / gate-and-record) — the pending
  queue feed, the resolve API (the only approve verb), and the ledger for
  drill-downs. arming a batch and approving an edit both ride this path.
- **audit health** (catalog-loop's audit) — the store-wide and per-product
  health scores and dimension pass rates; a card's headline rate is the audit's
  number for that dimension, and it must match. ONE exception, RULED 2026-07-12:
  the merchandising card headlines a NEW collection-coverage measure — the share
  of products that belong to at least one smart collection, moving 0 → (near)
  full (sourced from catalog-workflows, the merchandising feature's progress
  metric). it does NOT headline the audit's existing "merchandising" dimension,
  which is a tag-presence proxy and stays a separate dimension. every
  card's headline is a real, checkable number — collection-coverage is measured
  the same way (members / total), so "the card headline must match a real audit
  number" holds for it too.

## mechanism vs config — the hybrid layout + render-from-registry = mechanism; which feature cards show = config

- **mechanism (store #2 uses unchanged):** the hybrid layout itself (home
  cards over a product browser over a per-product drill) · rendering each
  feature card from `workflow_features` (catalog-workflows owns the per-feature
  numbers) + audit health, and browser row and drill from the live reads above
  (the one-row-per-part `parts` registry stays only for the catalog part's
  generic self-report), no bespoke code per feature · the three intents wired to
  the gate · the flag-review flow · the verify-rendered display.
- **config (this store's file):** which feature cards show and their order
  (images, gtin, classification, merchandising, seo, spec-verification,
  delist — a store with different dimensions shows different cards) · the
  browser's default filters and sort · per-feature copy/labels · thresholds
  for a card's "healthy / at-risk" band (a label, never the gate's threshold,
  which moves only through the recorded path) · `bulk_confirm_cap` — the batch
  size above which a REVERSIBLE run asks the owner once at `/approvals` before it
  lands (RULED 2026-07-12; a named config number, not engine code).
- adding a feature is a config row plus that feature existing in
  catalog-workflows — never a new view. a card with no backing queue renders
  as "no data yet," never as a blank.

## behavior — numbered flows

1. **the home renders from live queue depth.** `/catalog` draws one card per
   configured feature. each card shows: the current rate/coverage (the audit's
   number for that dimension — except the merchandising card, which headlines
   collection-coverage: the share of products in at least one smart collection,
   RULED 2026-07-12), the queue depth (products with this gap, from
   catalog-workflows), progress (movement since the last run), and a
   [run batch] control. every number on the card links to the rows behind it.
   the flags card shows "N waiting your ruling → [review]" where N is the open
   flag count from catalog-lifecycle.
2. **holistic, not only gaps.** cards and the home surface also carry openings,
   not just deficits: an under-served category the browser can jump to, and the
   list-price sum over catalog-lifecycle's `delisted` set (recoverable by
   relisting) — each figure linked to the products it sums, never a detached
   number. that figure is a plain sum of list price over the delisted set,
   labeled as such (e.g. "list-price of the delisted set: AED X"), NOT a
   sell-through or revenue projection. RULED 2026-07-12 (law-driven default): no
   invented recovery number and no modeled sell-through until real sell-through
   data exists to model on — the strip shows the sum the delisted set actually
   carries, nothing more.
3. **[run batch] arms a gate-class-aware, size-capped run.** pressing it asks
   catalog-workflows to stage a run over the card's scope (all gapped products, or
   a browser-defined subset). a REVERSIBLE feature's run at or under the config
   size cap `bulk_confirm_cap` executes through the gated connector and lands
   immediately — the card moves and shows the verify-rendered result, with no
   `/approvals` stop (matching the RULED reversible gate class: no queue). a
   reversible batch OVER the cap parks ONCE in `/approvals` for a single
   whole-batch confirm, then lands on approval (RULED 2026-07-12: a big
   reversible batch asks once; a small one just runs). a CONSEQUENTIAL /
   FIT-CRITICAL feature's run ALWAYS parks its staged writes in the SAME
   `/approvals` queue — same card shape, same resolve verb — and the operator
   approves there. nothing on THIS surface approves anything.
4. **the card moves on the verified outcome.** for a reversible run the writes
   land straight away; for a consequential / fit-critical run the operator
   approves at `/approvals` first. either way catalog-workflows executes with
   one-use handles, catalog-loop verify-renders the live surface, and the outcome
   flows back over SSE. the feature card's rate and progress update; the
   verify-rendered result (per product pass/fail) is shown, not asserted.
5. **the product browser filters by state / health / gap.** `/catalog/products`
   lists products with filter and sort on lifecycle state (the RULED five:
   draft, active, flagged, delisted, archived), health score, and per-feature
   gap (e.g. "no
   image", "unverified specs"). the result set is the scope a [run batch] can
   target. counts on the filter chips link to the audit rows behind them.
6. **the per-product drill shows claims + provenance + state + history.**
   `/catalog/products/{id}` shows the canonical claims each with its provenance
   (openable to the source), the current lifecycle state and its full history,
   and the last verify-rendered result. it is the single-product answer to
   "what do we claim, on what evidence, and did it render."
7. **edit stages, gates, verifies — never direct-writes.** in the drill the
   operator edits one product's fields. saving stages the exact changes as a
   gate proposal into `/approvals`; on approval the change goes live and
   verify-renders; the drill shows the round-trip (staged → approved → live →
   verified) with the ledger id. an edit that skips the gate is impossible by
   construction — the surface has no write door.
8. **the flag-review flow.** the flags card and `/catalog/flags` show each open
   flag with its evidence (the signals that raised it, from catalog-lifecycle).
   the operator's ruling calls rule-flag, which fires exactly one lifecycle
   transition; where that transition writes to the world it is gated, and the
   panel updates over SSE when it lands. one flag, one ruling, one transition.

## renders — the whole point IS the render

- **`/catalog` (the home).** a grid of feature cards. each card: feature name ·
  headline rate/coverage (links to the audit rows) · queue depth as a count
  (links to the browser filtered to those products) · a progress indicator
  (delta since last run, links to that run's ledger entries) · [run batch]. one
  flags card: "N waiting your ruling → [review]" (links to the flag panel).
  plus the holistic strip: top under-served category and the list-price sum of
  the delisted set (labeled as a sum, e.g. "list-price of the delisted set: AED
  X" — not a projection), each linked to its products. every number is a link;
  nothing is a bare figure.
- **`/catalog/products` (the browser).** a table of products with filter chips
  (state, health band, per-feature gap) and sort. each row: product, lifecycle
  state, health score, the gaps it carries. row → the drill. the active filter
  is the scope [run batch] on a card can inherit.
- **`/catalog/products/{id}` (the drill).** three panels. claims + provenance:
  each claim with source, verified flag and date, unit, fit-critical marker (and
  `standard` — proposed, not yet backed by a spec_claims column) — provenance
  openable to the source. state + history: current
  lifecycle state and the transition log (what changed, when, who approved).
  verify: the last verify-rendered result (page / feed / JSON-LD pass or fail).
  an [edit] that stages field changes into the gate, showing the staged →
  approved → live → verified round-trip and its ledger id.
- **`/catalog/flags` (the review panel).** each open flag with its evidence
  laid out (the signals, the products, the proposed transition), and the ruling
  control. a ruling fires one transition; the panel flips over SSE when it
  lands. an ignored flag ages visibly — it does not vanish.
- across all four: every number links to the rows behind it, every claim's
  provenance is openable, and every verify-rendered result is shown as the
  live-surface receipt — never a files-exist claim.

## checks — runnable, meaningful (result seen on the named surface)

1. **card depth matches the audit.** a feature card's queue depth equals the
   audit's count of products failing that dimension; drilling the card's count
   lands on exactly those product rows. seen on: `/catalog` (the card) and
   `/catalog/products` (the filtered set).
2. **a consequential [run batch] parks; a small reversible one lands; a big
   reversible one asks once.** pressing [run batch] on a CONSEQUENTIAL /
   fit-critical card (delist, spec-verification) arms a run whose staged writes
   appear in the existing `/approvals` queue — no new approve endpoint. pressing
   it on a REVERSIBLE card (the GTIN template, built first) with a batch AT OR
   UNDER `bulk_confirm_cap` executes through the gated connector and lands with NO
   new pending card, the card moving with the verify-rendered result. pressing it
   on a REVERSIBLE card with a batch OVER `bulk_confirm_cap` produces exactly ONE
   pending confirm in `/approvals` for the whole batch (not one per write), and
   the batch lands only on that approval (RULED 2026-07-12). seen on: `/approvals`
   (consequential cards carry the batch's ledger ids; an over-cap reversible batch
   shows one whole-batch confirm) and `/catalog` (an under-cap reversible GTIN
   card advances, verify-render shown, nothing pending).
3. **an approved consequential batch verify-renders and the card moves.**
   approving a consequential / fit-critical batch at `/approvals` runs the
   executor, verify-renders the live surface, and the card's rate/progress
   advances by the verified count. seen on: `/catalog` (card progress) and the
   drill's verify panel for a sampled product.
4. **the browser filter returns the right set.** filtering by state=flagged +
   gap=no-image returns exactly the products the audit and catalog-lifecycle
   agree carry both; the chip count equals the row count. seen on:
   `/catalog/products`.
5. **a per-product edit round-trips.** editing one product's field in the drill
   stages a proposal into `/approvals`; approving it lands the change live and
   verify-renders; the drill shows staged → approved → live → verified with one
   ledger id. seen on: `/catalog/products/{id}` and `/approvals`.
6. **the flag-review queue shows evidence and a ruling fires one transition.**
   each flag in the panel shows its evidence; ruling one flag fires exactly one
   lifecycle transition (recorded), and no direct write escapes the gate. seen
   on: `/catalog/flags` (the flag flips) and `/record` (the one transition).
7. **no second approve verb exists.** a code/route audit shows this part calls
   only the web-surface resolve path; it exposes no approve endpoint of its
   own. seen on: the route list and `/approvals` (the sole approve verb).
8. **the holistic strip drills to its rows.** each strip figure (top under-served
   category, the list-price value of the delisted set) opens to exactly the
   products it sums — figure count == row count of the linked set, no bare
   number. seen on: `/catalog` (the strip) and `/catalog/products` (the linked
   set).

## v0 salvage

- **mine:** the web-surface app skeleton (FastAPI + small frontend, SQLite
  reads, SSE, device-paired auth) — the routes here are new pages in that same
  app · the parts registry as the render contract (a card/row costs a config
  entry, not a bespoke view) · the approvals/resolve verb as the ONLY approve
  path (run-batch and edit-product both ride it) · SSE for live card, browser,
  and flag updates · device-paired auth + per-money-move confirm, unchanged ·
  the park-don't-block round-trip with the executor as the single chokepoint.
- **do NOT port:** a second approve verb of any kind — arming a batch and
  approving an edit are the existing resolve verb, full stop · a direct-write
  product editor — every edit stages, gates, and verify-renders · any
  files-exist "done" — the verify-rendered result is shown or the surface does
  not claim done.

## open

- OPEN [design]: is `/catalog` its own top-level route, or a section under
  `/parts/{name}` for the catalog part? proposed: its own `/catalog` family —
  it is a workspace the operator lives in, heavier than a single part card, and
  the parts view stays the generic self-report. resolve at S1 build.
- OPEN [owner]: how much editing is too much before this clones Shopify? the
  boundary this draft holds: edit only what carries provenance and verifies
  (specs, identity, classification, merchandising, seo, images, lifecycle
  state) — NOT order management, theme, checkout, or inventory ops, which stay
  in Shopify. proposed rule: if a field has no provenance and no verify-render,
  it does not belong in this drill. owner to confirm the line.
- OPEN [design]: the [run batch] scope control — does the operator arm a full
  feature run, or must a batch always be scoped to a browser filter (safer,
  smaller, more approvals)? proposed: default to the full gapped set, but let a
  browser filter narrow it before arming; the gate still gates each staged
  write. resolve at S1.
- OPEN [design]: the phone/mobile layout for the operator. the feature cards
  and the flag panel are phone-friendly (aligned with web-surface's phone path
  and ntfy deep links); the product browser table and the multi-panel drill are
  not, and need a stacked/collapsed layout. proposed: cards + flags full on
  phone, browser and drill read-first with edit deferred to desktop. resolve
  when the phone path is exercised.
- OPEN [design]: does the holistic strip (under-served category, the list-price
  sum of the delisted set) live on `/catalog` or on the brief (`/`)? proposed: a
  compact copy on `/catalog` scoped to the catalog, the business-wide version on
  the brief. resolve with the watching/findings seam. (this is a placement
  question only — the strip's content is RULED: a plain list-price sum, no
  projection.)
- RULED 2026-07-12 — **bulk arming is size-capped, not blanket-consequential.**
  a reversible batch AT OR UNDER the config cap `bulk_confirm_cap` lands with no
  `/approvals` stop; a reversible batch OVER the cap asks the owner once (one
  whole-batch confirm); consequential and fit-critical features always park
  regardless of size. encoded in `## exposes` (run-batch), behavior 3, check 2,
  and the `bulk_confirm_cap` config row above. (this replaces the earlier open
  question of whether every operator-armed batch should be classed consequential:
  the answer is a size cap, not a blanket class.)
- RULED 2026-07-12 — **the holistic strip shows a plain list-price sum, never a
  projection.** the "recoverable by relisting" figure is a plain sum of list
  price over the `delisted` set — a real, checkable number (check 8), labeled as
  a sum. no recovery / sell-through probability is modeled on top and no revenue
  projection is invented until real sell-through data exists to model on (the
  law-driven default: no invented numbers). encoded in the purpose, behavior 2,
  the renders strip, and check 8.
