`git diff --quiet 3c506f9..HEAD -- commerceos/spine/writes.py commerceos/gate/policy.py commerceos/catalog/workflows.py commerceos/web/app.py commerceos/spine/connector_shopify.py commerceos/spine/schema.py stores/demostore/policy-table.json spec/parts/catalog-workflows.md || echo "STALE — re-true before build (see RUNBOOK)"`

# scout — collections: CW4 (collection-create executor, S) + CW5 (merchandising feature, M)

this is a SCOUT pack: the seam map is verified, the two owner rulings are framed
as one-k cards, and the tail names what the full packs need once ruled. it is
not buildable on its own — the full PACK.md + context.md come after the rulings.
as-of: commit 3c506f9, suite 394 green. rides packs/RUNBOOK.md.

the backlog rows, verbatim (backlog.md:155-156):

> | CW4 | collection-create executor — a new gated method (unblocks merchandising) | O3, C2 | S | CW2 pattern; [owner] placement | an approved collection-create makes the smart collection, renders live, membership confirms; replay refused. seen on the live storefront |
> | CW5 | merchandising / smart-collections feature (~20 creates) | C2, O3 | M | CW1, CW4; [owner] card metric | ~20 collections created, a sample product's membership renders live; the coverage figure advances. seen on /catalog + storefront |

## seam map (verified 2026-07-19 against the repo at 3c506f9)

**there is NO collection write machinery anywhere.** verified by grep: every
`collection` hit in `commerceos/` is read-only or stdlib `import collections`.

the write door — commerceos/spine/writes.py:
- the dispatch is writes.py:87-108. exactly SEVEN methods today:
  `mutate_spec_verification` (:87), `record_supplier` (:91),
  `mutate_product_field` (:97), `mutate_variant_field` (:99),
  `mutate_price` (:101), `mutate_product_state` (:103), `mutate_seo` (:105).
  an unlisted method hits `raise WriteRefused(f"no executor for method {method}")`
  at writes.py:108. CW4 adds branch #8 here — there is no other door.
- the handle wall is writes.py:74-84: consume-before-network, replay refused
  at the wall. every new branch inherits it for free by being inside `execute`.
- prior art for the new method body: `_mutate_seo` (writes.py:176-190) and
  `_mutate_product_state` (writes.py:290-304) — mutation, userErrors check,
  read-back query, `verified_rendered` computed from the read-back, all inside
  the one function. copy that shape.

the classifier — commerceos/gate/policy.py:
- `_BUILTIN_METHOD_CLASS` is policy.py:52-58 — today only
  `mutate_product_state` and `record_supplier` (both CONSEQUENTIAL).
- an UNKNOWN method fails safe-high: policy.py:117-119 sends it to
  `table.get("unknown_method_class", FIT_CRITICAL)` with flag `unknown-method`,
  and fit_critical NEVER auto-approves (policy.py:150-151). demostore's table
  sets `unknown_method_class: fit_critical` explicitly
  (stores/demostore/policy-table.json). **so a collection-create submitted
  before registration parks EVERYTHING as fit-critical — the registration is a
  build step, not an afterthought.** register in BOTH places: a row in
  stores/demostore/policy-table.json `methods` (13 methods today, none for
  collections) AND the `_BUILTIN_METHOD_CLASS` floor (per the floor's own
  comment, policy.py:45-51: a shipped executor never silently falls to
  fit_critical for lack of a config row).
- spec/parts/catalog-workflows.md:159 rules the merchandising feature's gate
  class REVERSIBLE (~20 creates). under WF-approve (commit dd20d15) reversible
  no longer means auto-lands — it means the batch HOLDS for one glance-approve.

what exists read-only (the facts side CW5's coverage figure reads):
- the connector pulls `collections(first: 10) { ... nodes { title } }` per
  product — connector_shopify.py:61 in `_PRODUCTS_QUERY` — and lands the
  titles as a JSON array into `products.collections`
  (connector_shopify.py:219 whole-entity check, :234 upsert clause, :248 the
  json.dumps). the column is spine/schema.py:150 (migration 1, A8).
  this refreshes ONLY on a full product sync.

the engine CW5 rides — commerceos/catalog/workflows.py:
- `Feature` dataclass :40-55 (name, method, declared_type, agent, queue,
  verify, progress, writeback, intent, batch_default).
- `FEATURES` registry :367. `run_feature` :374-460; `hold=True` :400-414
  parks every proposal and groups the batch into one workflow run
  (catalog/runs.py — landed with WF-approve, dd20d15).
- config-row prior art: CLASSIFICATION (:158-169) wires queue/verify/progress/
  writeback out of classification.py — CW5's shape exactly (its own module,
  one Feature row here).

the web surface a new front must join — commerceos/web/app.py:
- `FEATURE_LABELS` :40-49 (already carries "seo"/"images" placeholders; no
  merchandising key), `FEATURE_TO_GAP` :240-241, `FRONT_BLURB` :251-258,
  `GATE_CLASS_PLAIN` :268-272, `SOURCE_PLAIN` :280-285 — each map needs the
  new feature's plain-words entry or the guard test
  (tests/test_catalog_dashboard.py:240,
  `test_no_jargon_or_raw_codes_reach_the_screen`) meets a raw code.
- front page numbers: `front_no` app.py:1960-1961 = gtin 204, classification
  205, delist 206, verification 208. **207 is taken** (flagged products,
  app.py:1969-1972). the merchandising front needs a fresh number — and page
  numbering is itself half of the UI-polish [owner] item (backlog.md:160), so
  the full pack should propose one (2xx next free: 209) and flag it to that ruling.
- the arm path: `POST /catalog/run/<feature>` app.py:2900-2930 — a reversible
  front takes `hold=True` (:2923) and redirects to the run preview
  (/catalog/runs/<id>, app.py:3034). the preview renders was→becomes via
  `_mark_diff` (app.py:2957) over item display strings — a collection-create
  has no "was"; the preview shape for creates needs a look in the full pack.

## ruling card 1 — CW4 [owner]: where do collections land on the storefront?

**the question:** when the ~20 smart collections exist, where does a shopper
meet them? the executor can make collections all day; placement decides
whether they are navigation, landing pages, or shelf logic.

**the options:**
- (a) **main navigation menus** — collections become the store's nav tree.
  biggest visible change; touches the theme's menu (an online-store write the
  door has no method for yet — menus are a separate Shopify resource).
- (b) **collection pages only, linked from content** — each collection gets
  its live URL (/collections/<handle>); nav untouched. smallest surface,
  verifiable today by fetching the collection page.
- (c) **defer placement** — create them unlinked now (they still power search,
  filtering, and the coverage metric), place them after F1-the-name rules the
  storefront's shape.

**what each unlocks:** (a) needs a second executor method (menu write) — CW4
grows; (b) and (c) need only collection-create — CW4 stays S-size. all three
unlock CW5 identically (membership is placement-independent).

**recommendation:** (b) now, (a) revisited when the store rails (F2-F6) open —
they are name-gated anyway (backlog.md:222). the check "seen on the live
storefront" is satisfiable under (b): the collection URL renders with its
members.

## ruling card 2 — CW5 [owner]: the card's headline metric

**the question:** what number does the merchandising card on /catalog headline?

**the options:**
- (a) **collection-coverage** — share of products belonging to at least one
  smart collection. already RULED toward this 2026-07-12
  (spec/parts/catalog-workflows.md:159: "collection-coverage 0 → (near) full
  ... this is a NEW measure the card headlines"); backlog.md:196-197 says
  "ruled toward coverage; confirm at build". this card is that confirmation.
- (b) **the tag-presence proxy** — the audit's existing "merchandising"
  dimension (the untagged count at audit.py:454-456). starts
  near-full, so the card would open saying the work is done before it starts.

**what each unlocks:** (a) makes the card honest at 0 and moving as
collections land; the spec keeps (b) as its own separate audit dimension either
way (spec:159). (b) headline would contradict the spec and needs a spec edit first.

**recommendation:** (a), confirming the standing ruling. note for the full
pack: coverage read from `products.collections` lags until the next sync —
the honest read-back is the live store's membership query, with a writeback
into `products.collections` on verified creates (the `_gtin_writeback` /
`classification_writeback` pattern, workflows.py:111-116,
classification.py:167-172).

## what the full packs need (once ruled)

- **CW4 pack (S, sonnet):**
  - the method name settled: spec/parts/catalog-workflows.md:74 names it
    `collection-create`; every existing method is snake_case `mutate_*` /
    `record_*`. pick `mutate_collection_create` and true the spec's name in
    the same diff (spec-first law), or keep the spec's literal — one line
    either way, decided in the pack, not mid-build.
  - the Shopify seam: `collectionCreate` mutation with a `ruleSet` (smart
    collection = rules, not manual members), read-back via `collection(id)`
    { id, handle, ruleSet, productsCount } — exact GraphQL to be drafted in
    the pack and validated against the dev store
    (your-store.myshopify.com, the proving fixture per AGENTS.md).
  - the registration step written as its own checkpoint: policy-table row +
    `_BUILTIN_METHOD_CLASS` entry + a pin that an unregistered submit parks
    fit-critical (the fail-safe proven, then removed by registration).
  - replay-refusal + provenance pins (mandatory for any executor,
    RUNBOOK env block) — copy tests/test_seo_executor.py's shape (FakeClient
    :14, replay test :84).
  - trap to carry: smart-collection membership is computed asynchronously by
    Shopify after a rules create — the verify may need the membership check
    split from the create receipt (create verified ≠ membership settled).
    spec:158 already words classification's check as "its smart collections
    settle".
- **CW5 pack (M, opus):**
  - a merchandising.py module (queue: the ~20 ruled collection definitions +
    the customer-category field writes via the EXISTING `mutate_product_field`
    metafield door; verify; progress = the ruled coverage; writeback) + one
    Feature row — the CLASSIFICATION shape.
  - where the ~20 collection definitions come from: the taxonomy
    (stores/demostore/taxonomy.json) is the natural source; the pack freezes
    the actual list.
  - the WF-approve interplay pinned: reversible → hold → one run → the
    preview must read sensibly for creates (no "was"); prior art
    tests/test_workflow_runs.py + tests/test_workflow_runs_web.py (rig :21-31).
  - the five plain-words maps in app.py fed, the front's page number placed,
    and a HARD producer cold-read — CW5 is [product]: capture script =
    TestClient + seeded scratch db + HTML captures of /catalog, the front
    page, the run preview.
  - boundaries: scratch dbs + FakeStore (tests/test_catalog_workflows.py:43)
    for the suite; the dev store for the live proof. data/demostore.db is the
    real catalog — never written.

## open questions

- both ruling cards above — CW4 placement and CW5 metric confirmation. nothing
  else found that needs the owner: gate class (reversible), batch (~20), and
  the coverage definition are already ruled in spec/parts/catalog-workflows.md:158-159.
