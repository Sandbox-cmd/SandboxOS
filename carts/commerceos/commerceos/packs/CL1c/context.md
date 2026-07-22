# CL1c — context (verified against the repo at 3c506f9)

## seam map (every file the build touches, refs read fresh)

| file | what | refs |
|---|---|---|
| commerceos/spine/connector_shopify.py | `sync_products` — the public entry | :124-129 (delegates to `_run` :162-170, which marks sync_state ok/error and re-raises on failure) |
| commerceos/spine/connector_shopify.py | `_land_products` — the landing loop the hook goes in | def :209 · node loop :215 · product upsert :223-254 (status is in hand: `node.get("status")` :242) · media :257-272 · metafields :275-284 · variants :285-307 · **page commit :308 ("a page landed whole") — the hook lands after this line** · hasNextPage return :309-311 |
| commerceos/spine/connector_shopify.py | module docstring — what a sync lands (update it) | :1-24 |
| commerceos/catalog/lifecycle.py | `set_initial` — the idempotent placement door | :135-167 (short-circuit for placed products :143-144 · status map `_SHOPIFY_STATUS` :57 (ACTIVE/DRAFT/ARCHIVED) · unknown status raises `LifecycleError` :148-151 · history row who='sync', from_state NULL :161-165 · commits :166) |
| commerceos/catalog/lifecycle.py | `backfill_from_products` — the losing option, kept as-is (CL1b's seeder; `status or "ACTIVE"` fallback to mirror) | :267-275 |
| commerceos/catalog/lifecycle.py | the one-writer law | header :5-9 and the seam note :24-31 |
| commerceos/rhythm/runner.py | `_job_sync` — the only production caller of sync_products today (read, NOT edited — the hook makes it inherit the behavior) | :149-157 · BUILTIN_JOBS :222 |
| commerceos/spine/schema.py | migration 2 creates both lifecycle tables (so every `ensure_schema` db has them — the connector never needs a schema call of its own beyond what `_job_sync` already runs :151-152) | :170-186 |
| tests/test_connector_shopify.py | the pins land here | rig below |

import-cycle check (done, cite it, don't re-derive): lifecycle.py imports
`commerceos.gate.ledger` only (:38); gate/ledger.py imports `commerceos.db`
only (:33); neither imports spine — a spine → catalog.lifecycle import closes
no cycle. keep it function-level inside `_land_products` regardless.

## prior art (copy these shapes)

- **the sync rig**: tests/test_connector_shopify.py — `FakeClient` (pages
  keyed by cursor) :41-52, `products_client()` :58-64, the `conn` fixture
  (tmp-path db + `ensure_schema`) :70-75. fixture facts: page1 has 2 products
  status ACTIVE, page2 has 1 status DRAFT (verified by grep) — so a full
  fixture sync should place active=2, draft=1.
- **idempotence pin shape**: `test_two_syncs_of_the_same_fixture_land_the_same_row_count`
  :95-99 — the re-sync pin mirrors this.
- **set_initial's own pins** (what NOT to re-test, just rely on):
  tests/test_catalog_lifecycle.py :26-50 (mapping, idempotence, unknown-status
  refusal).

## binding laws (this item)

- one writer per table-set (AGENTS.md): lifecycle.py owns
  product_lifecycle + lifecycle_history; the connector calls `set_initial`,
  never SQL against those tables.
- every fact carries source + fetched_at — untouched here; the lifecycle row
  is placement, not a fact, and records its own reason
  ("synced from Shopify status …", lifecycle.py:155).
- a failed sync lands status=error and re-raises, never half-silent
  (connector header :10-12) — the LifecycleError path must keep this.
- spec-first: spec/parts/catalog-lifecycle.md already describes set_initial as
  the sync placement ("Place a newly-synced product…", lifecycle.py:136); the
  build FULFILLS the spec rather than contradicting it. if a wording drift is
  found in the spec, stage the spec edit first.

## cold-start pointers

- env + covenant: packs/RUNBOOK.md env block (`cd the cartridge root`,
  `uv run pytest -q` ~90s, call-time store resolution).
- required reading: AGENTS.md · .claude/agent-memory/producer/MEMORY.md · the
  plain-first guard test tests/test_catalog_dashboard.py:240 (no screen
  strings expected here, but the law rides every build).

## test plan (the pins, named — in tests/test_connector_shopify.py)

1. `test_products_sync_places_every_product_in_the_lifecycle` — fixture sync
   → all 3 products have a `product_lifecycle` row with the mapped state
   (2 active, 1 draft); each has exactly one history row, `by == 'sync'`,
   `from_state IS NULL`.
2. `test_a_resync_never_duplicates_placement` — sync twice with fresh
   `products_client()` each time (the fixture-client cursor is consumed) →
   history count per product still 1, states unchanged. this is the check's
   second clause, verbatim.
3. `test_a_resync_never_stomps_a_recorded_move` — sync, then move one product
   through the lifecycle's own door (`transition` to delisted, or
   `raise_flag`) → re-sync → the state and history are exactly as the move
   left them (`set_initial`'s short-circuit, the wall against the sync
   "correcting" an operator's ruling).
4. `test_an_unknown_status_fails_the_sync_loudly` — inline FakeClient page
   (do not edit the shared JSON fixtures) with one product carrying a bogus
   status → `sync_products` raises `LifecycleError`, and `sync_state` for
   `shopify:products` reads status='error' with the error recorded (the
   `_mark_error` leg, connector :184-193).

no capture script owed — not a [product] item. the step-3 sanity is one
/catalog HTML capture from a scratch db after a fixture sync (stage split
cells at app.py:1951 render the placed counts).

## open questions

none — the seams meet cleanly, the spec already names set_initial as the sync
placement, and demostore's live rows were backfilled by CL1b, so no data
migration or owner ruling rides this item.
