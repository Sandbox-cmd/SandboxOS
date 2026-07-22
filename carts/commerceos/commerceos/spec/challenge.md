# challenge — catalog feature system (workflows · lifecycle · dashboard)

state: challenge v1 — 2026-07-12

> **what this file is.** this is a HISTORICAL RECORD of what the 2026-07-12
> adversarial challenge found in the three catalog specs and how those specs were
> changed in response. it is NOT required reading to understand the current specs.
> every ruling this challenge raised has been RULED (2026-07-12) and folded
> directly into the specs themselves — catalog-workflows.md, catalog-lifecycle.md,
> and catalog-dashboard.md now stand on their own. read this file only to learn
> the history of the changes, never to learn the current contract.

## summary

Three new specs went through an adversarial read against five lenses (truth,
cold read, scars, seams, holistic). The core idea holds: one engine runs every
catalog feature as a config row, lifecycle is a five-state model, and the
dashboard is the hybrid console. The defects were not in the idea — they were in
the wiring. Two contradictions recurred across every lens: the feature card had
two contradictory homes (`/parts/catalog-workflows` and `/catalog`), and the
dashboard narrated every batch as parking in `/approvals` even though reversible
features (the GTIN flagship) run and land with no approval stop. Three data-
integrity seams were unnamed: state changes executed by the workflow batch never
returned to lifecycle to update the state field, the spec-verification executor
wrote a field that only catalog-loop is allowed to write, and the dashboard
filter named lifecycle states that do not exist (`live`, `parked`) while a scar-
guarding "recoverable revenue" figure carried no source and no check. The
recorded image-count scar was scoped to a wave-2 feature instead of guarding
every run. Fixes that are safe and internal to the three specs are applied;
ownership rulings and parent-spec fold-ups are listed for the owner and the
orchestrator.

## confirmed findings

| severity | file | problem | fix |
|---|---|---|---|
| blocker | workflows / dashboard (seams+cold) | feature card has two homes: workflows renders it on `/parts/catalog-workflows`, dashboard renders it on `/catalog`; contradicts the owner's hybrid-dashboard ruling | dashboard renders the card on `/catalog`; workflows EXPOSES `workflow_features` numbers only; both specs repointed |
| blocker | dashboard (cold read) | run-batch narrated as always parking in `/approvals`, but reversible features (GTIN flagship) run-and-land — first-built feature behaves opposite to the console spec | dashboard run-batch made gate-class-aware: reversible lands, consequential/fit-critical parks; checks 2/3 split |
| blocker | workflows (scars) | image-count scar scoped to the wave-2 image feature; every V1 run (GTIN first) touches products and can drop store media as v0 did | image-count-non-decreasing made a store-wide post-run assertion on EVERY run; added to check #1, de-scoped from check #4 |
| blocker | workflows (seams) | state changes run by the workflow delist batch never return to lifecycle; state field goes stale (store delisted, lifecycle says active, no history row) | workflows exposes the state-change return leg to lifecycle (sole writer of state + history); consumes inbound requests |
| major | workflows (truth) | the merchandising progress metric was a misread of the audit's own dimension; the rate it claimed does not exist | replaced with `smart-collection coverage 0 → collections live`, with the tag-proxy-vs-collection note as OPEN |
| major | dashboard (seams+cold) | filter states `live` / `parked` are not lifecycle states; `parked` collides with the gate term; "parked set" is really the delisted set | filter uses the five RULED states; parked→delisted everywhere on the dashboard |
| major | dashboard (scars) | "revenue recoverable by relisting" is an unsourced, unchecked projection guarding the empower-don't-minimize scar | reworded to a checkable list-price sum over the delisted set; added check 8; recovery-model basis flagged OPEN [owner] |
| major | workflows (seams) | `mutate_spec_verification` stamps catalog-loop's canonical `verified` field — a second writer of catalog's table (breaks one-writer-per-table-set) | executor reworded to verify + return the receipt; catalog-loop records the flip; seam surfaced in `## open` for the owner |
| minor | workflows (truth) | citation `writes.py:140` is the field-level refusal, not the method refusal for state changes | citation corrected to `writes.py:95` |
| minor | workflows (truth) | delist executor named `mutate_product_state` but quality.py still emits `mutate_product_field` with `args.state` | reconciliation note folded into the delist-ruling OPEN item |
| minor | workflows (cold read) | `field-class` used as load-bearing but never glossed; the field-class→agent map not pointed at | one-sentence gloss added; fleet.md pointer sharpened to its V1 roster |
| minor | workflows (seams) | `## owns` claims sole authorship of "two methods" but RULED V1 merchandising needs an unbuilt third (collection-create) | count qualified honestly; collection-create noted as an OPEN gap, not reassigned |
| minor | dashboard (truth) | drill claims panel promises a `standard` provenance attribute; spec_claims has no such column | `standard` marked proposed with its backing (the `std` key in product_meta `_provenance`), not silently dropped |
| minor | lifecycle (seams) | dashboard consumes transition history but lifecycle `## exposes` never lists it | history feed added to lifecycle `## exposes` with the data-owner/view-owner split stated |

## what changed

Applied, internal to the three new specs only:

catalog-workflows.md
- `writes.py:140` → `writes.py:95` (state-change refusal cite).
- merchandising progress metric: dropped the fabricated rate,
  replaced with `smart-collection coverage 0 → collections live` plus the
  tag-proxy-vs-collection-membership note as an OPEN.
- image scar: added a store-wide, every-run post-run image-count assertion to
  behavior 1 and to check #1 (the GTIN template); de-scoped check #4 from "wave-2
  image feature" to every run.
- feature card home: `## renders` reworded so this part EXPOSES the per-feature
  numbers and the dashboard renders the card on `/catalog`; check 5 and the
  registry-seam OPEN item repointed to `/catalog`.
- state-change return leg: added an `## exposes` bullet (verified outcome to
  catalog-lifecycle, the sole writer of state + history), an inbound `## consumes`
  bullet (state-change requests from lifecycle), and a sentence in behavior 2.
- `mutate_spec_verification`: `## owns` and behavior 3 reworded so the executor
  verifies and returns the receipt; catalog-loop records the provenance flip; the
  one-writer seam surfaced in `## open`.
- `## owns` "two methods" count qualified; collection-create noted as an OPEN gap.
- field-class glossed in one sentence; fleet.md pointer sharpened to its V1 roster.
- delist emitter/executor method-name reconciliation folded into the delist OPEN.

catalog-lifecycle.md
- added `transition history per product` to `## exposes` with the data-owner
  (lifecycle) vs view-owner (dashboard) split stated.

catalog-dashboard.md
- run-batch made gate-class-aware in `## exposes`, behavior 3, behavior 4, and
  checks 2/3; added OPEN [owner] on whether bulk arming is itself consequential.
- lifecycle filter states use the RULED five (draft/active/flagged/delisted/
  archived); every `parked` → `delisted`; `live` → `active`.
- holistic strip reworded to a checkable list-price sum over the delisted set;
  added check 8 (strip drills to its rows); recovery-model basis flagged OPEN.
- `standard` provenance attribute marked proposed with its backing.
- mechanism "render from the parts registry" corrected to `workflow_features`
  (workflows-owned) + audit health.

## owner rulings — RESOLVED 2026-07-12 (encoded in the specs)

every seam and open question this challenge surfaced was ruled by the owner on
2026-07-12 and folded into the specs. each is RESOLVED; the pointer says which
spec now carries it:

1. **one-writer seam (state + spec-verification).** RESOLVED — the spine executor
   performs the Shopify write and returns the receipt; the TABLE'S OWNER records
   the local change (catalog-loop writes the verified:false→true flip;
   catalog-lifecycle writes the state field + history row). now carried by
   catalog-workflows.md (`## owns`, `## exposes` return leg, behavior 2 + 3) and
   catalog-lifecycle.md (`## purpose` seam, RULED). the executor-ownership,
   one-writer, and return-leg OPEN items were removed from catalog-workflows.md.
2. **collection-create.** RESOLVED — it is a V1 executor (backlog CW4), a new
   gated method on the one door; V1 merchandising (CW5) depends on it. now carried
   by catalog-workflows.md `## owns` and the merchandising config row; dropped from
   `## open` (only the wave-2 media-attach executor stays open).
3. **merchandising metric.** RESOLVED — the /catalog merchandising card headlines
   a NEW collection-coverage measure (products in ≥1 smart collection, 0 → near
   full), NOT the audit's tag-presence "merchandising" dimension (a separate
   dimension). now carried by catalog-workflows.md (merchandising row progress
   metric) and catalog-dashboard.md (`## consumes` audit-health, behavior 1).
4. **bulk gate class.** RESOLVED — reversible batches at/under a config size cap
   `bulk_confirm_cap` land with no stop; over the cap asks once; consequential and
   fit-critical always park. now carried by catalog-dashboard.md (`## exposes`,
   behavior 3, config, check 2); the bulk-arming OPEN is now RULED there.
5. **recoverable-revenue strip.** RESOLVED (law-driven default) — the delisted-set
   strip shows a plain list-price SUM labeled as such, never a revenue projection;
   no invented numbers until real sell-through data exists. now carried by
   catalog-dashboard.md (purpose, behavior 2, renders strip, check 8); the
   recovery-model OPEN is now RULED there.
6. **delist list + method-name reconciliation.** RESOLVED — the owner ruled all 29
   (17 noise + 12 decor) delisted; held near-misses stay; the executor + the
   quality.py method-name fix land with backlog CW8. now carried by
   catalog-workflows.md (delist config row RULED, behavior 2 BUILD TASK); the
   delist-ruling OPEN was removed.

## residual risks

- RESOLVED (ruling 1) — the one-writer-per-table-set division and the state-change
  return leg are now RULED and encoded in catalog-workflows.md and
  catalog-lifecycle.md; no longer an open seam.
- PARTLY RESOLVED (ruling 2) — collection-create is now RULED V1 (backlog CW4).
  the wave-2 media-attach executor is still genuinely OPEN (image sourcing rides
  on the wave-2 source-strategy ruling) — tracked in catalog-workflows.md `## open`.
- RESOLVED (ruling 4) — bulk arming is a size cap, not a blanket consequential
  class; encoded in catalog-dashboard.md.
- RESOLVED (ruling 6) — the quality.py method-name fix (`mutate_product_field` →
  `mutate_product_state`) is now a named BUILD TASK in catalog-workflows.md
  behavior 2, landing with backlog CW8, not an open question.
- STILL OPEN (orchestrator fold-ups, not owner rulings) — two parent-spec
  fold-ups (web-surface.md satellite tables, catalog-loop.md `standard` column)
  are deferred to the orchestrator; until folded, the multi-card render contract
  and the `standard` attribute remain cross-spec-inconsistent. these are not part
  of the 2026-07-12 owner rulings.

---

# challenge round 2 — the system-level run (2026-07-18)

one challenger, three lenses (truth against the live code · cold read ·
the scars), over only what the 2026-07-18 run changed. verdict: shape B
right, guards and counts honest, twelve holes. all twelve repaired the
same day:

- [blocker] the jsonl audit mirror would have interleaved every store's
  ledger into one data/ledger.jsonl — the exact mixing shape B exists to
  prevent. FIX: per-store mirrors (data/<store>.ledger.jsonl); M3's
  check now covers the mirrors, not just the databases.
- [blocker] "ten literals are the full migration checklist" was false —
  seven data/commerceos.db database-path sites were off the list, db.py
  reads its env at import time, and demostore's live database needs a
  rename (data/commerceos.db → data/<store>.db, WAL/SHM/mirror
  included) nobody had specced. FIX: owns checklist extended, resolver
  stated call-time, the rename is a named M3 step.
- [major] one global launchd label meant arming store #2 would silently
  overwrite store #1's schedule. FIX: per-store labels with the legacy
  label disarmed first, recorded; M4 asserts demostore's schedule
  untouched.
- [major] the fabricated-number scar recurred: a trio of proof numbers
  rode the checks line while nothing on the record computed them. FIX:
  cut from the checks line with the reason; the anchors that actually
  verify carry the mechanism proof alone.
- [major] the onboarding ceremony named no actor and its state no home.
  FIX: the operator runs it as the store-onboard skill; step stamps in
  registry.json, the multi-store part their sole writer.
- [major] F2's "still ticks unchanged" contradicted the registry row
  shape (demostore's rows carry no callable key), and the propose job
  re-reads the default config path, ignoring the tick's own config.
  FIX: the defaulting rule written into fleet.md behavior 1; F2's check
  covers both.
- [minor ×6, all applied] V1's test asserts the verified date (the
  schema alone does not) · grep-guard scoped to *.py with quality.py's
  stray comment on the checklist · W1 defines N per period grain and
  tests a month-grain metric (a fresh-start store may honestly sit in
  warm-up a long time) · VAT brief de-jargoned for an outside
  accountant · M3's files-exist check replaced with the behavioral
  isolation check · the cold-read gate names its judge (findings block
  the ship until resolved or the owner overrules, recorded).

residual, stated honestly: (i) "M2 runs alone" is load-bearing and only
discipline enforces it — nothing mechanical freezes the other lanes;
(ii) with the scaffold created by the ceremony (not checked in), M4's
test is the onboarding claim's only standing witness — if that check
ever weakens, O6's "config, not a second build" has no other proof.
