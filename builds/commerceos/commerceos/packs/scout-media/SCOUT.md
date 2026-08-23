`git diff --quiet 3c506f9..HEAD -- commerceos/spine/writes.py commerceos/spine/schema.py commerceos/spine/connector_shopify.py commerceos/gate/policy.py commerceos/catalog/workflows.py commerceos/watching/analyst.py commerceos/web/app.py spec/parts/catalog-workflows.md spec/parts/catalog-loop.md || echo "STALE — re-true before build (see RUNBOOK)"`

# scout — media-attach executor + the images agent (wave 2)

this is a SCOUT pack: the seam is verified and the missing piece is named. no
owner ruling is open here — CW9 (the sourcing strategy) was RULED 2026-07-18.
the gate is build order: the media-attach executor is the missing piece; the
images agent row unblocks the day it exists. as-of: commit 3c506f9, suite 394
green. rides packs/RUNBOOK.md.

the backlog rows, verbatim:

wave 2 / later (backlog.md:209-212):
> - **media-attach + the images agent** (the ruled hybrid pipeline: supplier
>   feeds where rights allow, commissioned shoots for heroes, no scraping).
>   the media-attach executor is the missing piece; deps CW1. CW9 RULED
>   2026-07-18.

roster rows (backlog.md:118):
> images agent (CW9 ruled hybrid — needs the media-attach executor)

## the rights law (rides every future pack in this line)

RULED 2026-07-18 [owner], spec/parts/catalog-loop.md:146-148:

> image sourcing — hybrid: supplier/brand feeds where rights allow,
> commissioned shoots for hero products, no scraping.

that is a boundary, not a preference: the images agent may draft attaches
ONLY from supplier/brand feeds whose rights allow it, plus commissioned shoot
assets. no scraping — a proposal whose source is a scraped URL is refused at
construction (the F4a content-agent pattern: refusal law at construction,
reasons on the receipt — backlog.md:86).

## seam map (verified 2026-07-19 against the repo at 3c506f9)

**product_media is READ-ONLY today.** the full trace:

- the table: spine/schema.py:152-158 — `product_media (product_id PK,
  media_count, first_image_url, source NOT NULL, fetched_at NOT NULL)`.
  one row per product, a COUNT + first URL, not a media list.
- the only writer: the connector's sync — connector_shopify.py:256-272
  upserts count + first image from `mediaCount`/`featuredMedia`
  (queried at connector_shopify.py:59-60). store → local only.
- the consumers: the analyst (watching/analyst.py:299 counts it as an input
  freshness signal, :314 LEFT JOINs it for the images-gap hunt) and the web
  surface (web/app.py:2101-2105, the products board's media join).
- **no mutate_*media method exists.** the write door (spine/writes.py:87-108)
  dispatches exactly seven methods — none touch media; an eighth branch is
  where media-attach lands. grep for `media` in writes.py: zero hits.
- the classifier: an unknown method fails safe-high to fit_critical
  (policy.py:117-119; demostore's table pins `unknown_method_class:
  fit_critical`). registration = a stores/demostore/policy-table.json methods
  row + a `_BUILTIN_METHOD_CLASS` floor entry (policy.py:52-58). the spec
  classes the image feature "reversible media-attach"
  (spec/parts/catalog-workflows.md:168) — under WF-approve (dd20d15) that
  means the batch HOLDS for one glance-approve, never auto-lands.

the spec's standing contract for this exact build
(spec/parts/catalog-workflows.md:337-345, the OPEN block):

> the media-attach write these wave-2 features need does not exist in
> writes.py and is not in V1 scope — build it with image sourcing (wave 2),
> a new gated method on the one door, same pattern as the V1 methods.

## the seam a media-attach method needs (sketch, not a design)

- **the mutation side:** Shopify attaches media to a product via
  `productCreateMedia(productId, media: [CreateMediaInput!])` (an
  `originalSource` URL + alt text), with `fileCreate`/staged uploads as the
  route for local shoot files. exact GraphQL is drafted in the full pack and
  validated against the dev store (your-store.myshopify.com) —
  do not trust this sketch's field names over the live schema.
- **the read-back shape:** media processing on Shopify is ASYNC — a created
  media node passes through a processing status before it is READY, so the
  read-back receipt differs from every existing executor (tags/seo/status
  echo back instantly). the receipt likely verifies "the store accepted the
  media and reports it against the product" and the feature's verify-render
  check ("the image resolves live in a browser", spec:168) runs as the
  render leg — the same two-legged split the delist feature uses (executor
  receipt at writes.py:290-304; the local commit on that receipt at
  catalog/delist.py:95-140).
- **the writeback:** on a verified attach, `product_media.media_count` /
  `first_image_url` route back through the spine (the fact-owner's API,
  never a direct engine write — the `_gtin_writeback` pattern,
  catalog/workflows.py:111-116). the one-row count shape may want widening
  to a media list; that is a schema migration decision for the full pack.
- **provenance:** every attach proposal carries its rights basis in the
  ledger record's provenance (which supplier feed, or which shoot) — the
  no-scraping law made checkable on the record, not a comment.

## discovery on record — the spec's image scar guard is not in the engine

spec/parts/catalog-workflows.md behavior 1 (:198-201) and checks 1 and 4
(:280-281, :293-297) mandate a STORE-WIDE invariant: after any feature run's
writes, the engine reads the live store image count and FAILS the whole run
if it dropped (the recorded v0 scar: a push dropped store media to a
fraction of a percent). verified by grep: `catalog/workflows.py` and `catalog/runs.py`
contain no image/media/scar check — `run_feature` (:374-456) and the
WF-approve execute leg never read an image count. every feature so far
touches non-media fields, so nothing has tripped it; a media-writing
executor is exactly the build the guard was specced for. the full pack must
either build the guard with the executor or stage the spec edit first
(escalation trigger 1) — building media writes without it contradicts the
spec as written.

## ruling card — none open

CW9 is ruled (hybrid, 2026-07-18); gate class is specced (reversible
media-attach, spec:168); the writer-class is named (images agent → product
media, spec/frames/roster.md:26). the only gate is build order:

**what unlocks the images agent row:** the roster row (backlog.md:118) reads
"needs the media-attach executor". the day an approved media-attach executes
through writes.py with replay refused and a verified receipt, the images
agent becomes pullable as a design-then-build item per roster.md — its
drafting half (source feeds → refusal-law construction → gated proposals) is
the F4a content-agent shape (fleet/content.py, tests/test_content_agent.py),
its writer-class is product media and nobody else's.

## what the full pack needs

- **a source in hand before the pack is cut:** the ruled route needs at least
  one supplier/brand feed with usable rights (or shoot assets) actually
  available — an executor with no lawful source has nothing to attach. this
  is an owner ACTION (obtain feeds/rights), not a ruling; name it in the
  pack's as-of.
- the method name + registration step (policy-table row, builtin floor,
  the unregistered-submit-parks pin) — same checklist as scout-collections.
- the async read-back settled: how long to wait / what counts as
  verified_rendered for a processing media node; the image-resolves-live
  check as the render leg.
- the image scar guard built or the spec trued (the discovery above) — with
  a pin that a run whose writes drop the live image count fails.
- true up spec/parts/catalog-workflows.md:168 and :337-341 to RULED (CW9,
  2026-07-18) — :168 still calls the strategy "OPEN [owner]" and the :337
  OPEN block still says image sourcing "rides on the owner's call"; both
  predate the ruling (catalog-loop.md:146-148). spec-first motion: stage
  the spec edit with (or before) the pack.
- the schema question answered: keep the one-row count shape or migrate to a
  media list (migration 1's comment calls product_media the "queryable home";
  products.raw already carries the full payload).
- executor pins per RUNBOOK: replay-refusal, provenance, dishonest-readback
  fails honestly — copy tests/test_seo_executor.py; FakeClient grows media
  responses (a FakeStore that "processes" media exercises the async shape).
- the images agent itself is a SECOND pack (design before pull, per
  roster.md) — drafting half + rhythm row disabled + manifest in
  .claude/agents/ — never folded into the executor's make (pull rule 3).
- boundaries: scratch dbs + fakes in the suite, dev store for live proof;
  data/demostore.db never written; no scraping in any test fixture's
  provenance strings (the fixture teaches the law too).

## open questions

- none needing a k today. the two decisions above (async verify shape,
  media-list schema) are build-time engineering calls for the full pack;
  the source-in-hand item is owner legwork, not a ruling.
