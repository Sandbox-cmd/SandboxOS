git diff --quiet 3c506f9..HEAD -- commerceos/spine/connector_shopify.py commerceos/catalog/lifecycle.py commerceos/rhythm/runner.py tests/test_connector_shopify.py tests/test_catalog_lifecycle.py || echo "STALE — re-true before build (see RUNBOOK)"

# CL1c — new products from a sync auto-register into the lifecycle

## mission

a product the sync lands today gets facts rows but NO lifecycle row — nobody
calls `set_initial` for it, so it sits stateless until someone runs a manual
backfill (`backfill_from_products` is called by nobody). the fix: the product
sync places every landed product through the lifecycle's own idempotent door,
so a new product carries its state the moment it exists and a re-sync never
duplicates or stomps a recorded move.

as-of: commit 3c506f9 · suite 394 green

## the backlog check (verbatim, backlog.md:159)

a sync that adds a product lands it in product_lifecycle with the right
state, no manual step; a re-sync doesn't duplicate

## model

sonnet — a small hook at one landing site plus pins; both halves
(`_land_products`, `set_initial`) already exist and are separately tested.

## boundaries

- **stores/dbs**: scratch dbs only (tmp-path `connect` + `ensure_schema`) and
  fixture-driven fake clients (tests/test_connector_shopify.py's FakeClient).
  NEVER run a live sync against `data/<store>.db` to prove this — a live store
  may already be fully backfilled by CL1b (every product placed); this item is
  about NEW products on any store.
- **gate lane**: none — `set_initial` is a read-of-the-store's-own-status
  placement, NOT a store write (lifecycle.py:139-141); no proposal, no gate,
  no fronts. WF-approve's hold machinery (dd20d15) is untouched by this item.
- **writer-class**: lifecycle.py stays the SOLE writer of `product_lifecycle`
  + `lifecycle_history` (lifecycle.py header :5-9 and :24-31, schema.py
  :170-180, AGENTS.md one-writer-per-table-set). the connector never touches
  those tables directly — it calls the owner's own door.

## the hook — decided, with the why

**per-page inside `_land_products` (connector_shopify.py:209), calling
`lifecycle.set_initial` for each landed product after the page's commit** —
not a post-sync backfill call at the rhythm caller. the reasons:

1. the check says "no manual step" for *a sync* — the rhythm job
   (runner.py:149-157) is only ONE caller of `sync_products`; a hand-run or a
   future CLI sync would silently skip placement if the hook lived in
   `_job_sync`. that is exactly the registered-but-not-runnable class of trap
   S1 closed once already.
2. `backfill_from_products` (lifecycle.py:267-275) loops the WHOLE products
   table every call (a `state_of` SELECT per product per tick); the
   page hook touches only the page's ~50 products.
3. the one-writer law holds either way — the writer is `set_initial` itself;
   the only real question was import layering, and it is clean: lifecycle.py
   imports only `gate.ledger` (:38), which imports only `commerceos.db` — no
   path back into spine, so no cycle. keep the import function-level inside
   `_land_products` anyway (the app.py pattern) so the spine stays importable
   without the catalog package.

mechanics: collect `(pid, node.get("status"))` in the node loop; after the
page's `conn.commit()` (:308 — "a page landed whole"), loop
`set_initial(conn, pid, status or "ACTIVE")`, mirroring backfill's fallback
(:273) so the two doors always agree. `set_initial` short-circuits placed
products before any write and commits per NEW product only (:142-167) — a
re-sync is a no-op pass of SELECTs.

## step plan (S-size: 2 checkpoints)

**step 1 — write the failing tests** in tests/test_connector_shopify.py (the
file that owns sync behavior; the pins are named in context.md). run them —
they fail because no lifecycle row exists after `sync_products`.

**step 2 — the hook** per the mechanics above, ~8 lines in
`_land_products` + a sentence in the module docstring naming the placement
(the connector's docstring :1-24 lists what a sync lands — keep it honest).

**checkpoint 1 — suite green**: `uv run pytest -q` ≥ 394 + new pins, zero
skips. review against the laws checklist; any file outside the seam map stops
the build.

**step 3 — scratch render sanity** (no [product] surface is owed here, but
the lifecycle counts feed real screens): on a scratch db, run
`sync_products` with the fixture client, boot the web app with
`COMMERCEOS_DB` pointed at it, and read /catalog — the stage split renders
the placed counts (2 active · 1 draft from the fixtures; counts read at
app.py:1939 and :2199). one capture for the note.

**checkpoint 2 — the check line proven** (fresh sync places, re-sync
duplicates nothing) + the render sanity reviewed.

## escalation triggers

the RUNBOOK's six, plus:

- the hook seems to want a schema change or a new table — stop; the tables
  exist (schema migration 2) and the shape is ruled.
- a reviewer wants the rhythm-caller shape instead of the connector hook —
  that is a design disagreement on a ruled seam; escalate, do not build both.
- ANY urge to prove against the live store or `data/demostore.db` — the
  fixtures + a scratch db are the whole proof; a live sync is the owner's
  rhythm, not this build's.

## "done"

the RUNBOOK's five lines, plus: the backlog check verbatim as pins (fresh
sync → placed with right state + who='sync' history row; re-sync → same row
counts, recorded moves untouched); suite ≥ 394 + new, zero skips. no producer
cold-read owed (infra-shaped; no new person-facing surface) — the scratch
/catalog render is the sanity receipt, not a walk.

## risks (item-specific)

- **don't stomp recorded moves**: a delisted product's store status is DRAFT;
  a naive upsert-style placement would "correct" it back to draft on re-sync.
  `set_initial`'s short-circuit (:143-144) is the wall — PIN it explicitly
  (re-sync of a moved product changes nothing).
- **loud refusal is the house law**: an unknown Shopify status raises
  `LifecycleError` (:148-151), which fails the sync through `_run` →
  `_mark_error` + re-raise (connector_shopify.py:162-169) — "visible, never
  half-silent" is the connector's own header law (:10-12). do not swallow it;
  pin it with an inline fake page carrying a bogus status.
- **commit granularity**: `set_initial` commits per new product; calling it
  BEFORE the page commit would break "a page landed whole" (:308). call after.
- **the store-agnostic grep guard**: tests/test_store_agnostic.py scans every
  *.py including comments — no store-name literal in the new code or its
  comments.
- **git/WAL trap**: no live database file is touched at all in this build;
  commit code + tests by path, never `git add -A`.
- **plain-language guard**: this item adds no screen strings; if any sneak in
  (a status summary word), they walk the guard test like everything else.
- fixture discipline: do NOT edit the shared JSON fixtures
  (tests/fixtures/shopify_products_page*.json — other counts pin against
  them); the bogus-status case uses an inline page dict.
