# part: the data spine — canonical model + connectors

serves: every O and C row (spec/jtbd.md) — facts for O1/O4/O5/O6, hands for O2/O3, catalog truth for C1–C2.
state: draft v1 — 2026-07-11; rulings of 2026-07-18 folded. OPEN items
marked.

## purpose

one local store of landed facts, and the only wires that touch the world.
multi-store shape is RULED 2026-07-18 [owner]: one database and one
append-only ledger per store — "one local store" here always means this
store's own. connectors pull what happened (catalog, orders, spend,
books) into a canonical model every other part reads; every write to
Shopify goes out through typed methods that demand an approved capability
handle from the gate. nothing else in commerceos talks to a platform, and
nothing else writes a fact.

## owns

the facts store: one SQLite database per store (the multi-store ruling
above); this store's lives in `the cartridge root`. the
spine is the sole writer of the facts tables below; every fact carries
source + fetched_at. one writer per table-set is the law across the whole
database: facts (the spine) · the canonical product record (the catalog
loop) · the ledger and event log (the gate + record part) · the part
registry (each part its own row, through the web surface's helper). file
layout inside the one database is an S1 detail. V1 entities:

- **product** — shopify id, handle, title, status, vendor, product type,
  tags; spec claims each as (field, value, source, verified) — per claim.
- **variant** — shopify id, product ref, sku, gtin/barcode, price, inventory
  quantity.
- **order** — shopify id, number, placed_at, customer_ref, lines (variant
  ref, qty, unit price, discount), totals (gross, discount, shipping, tax,
  net), financial + fulfillment status — and settlement per line: take_rate
  applied, take_amount, vendor_payable. every order splits into take +
  payable at landing (the commission-marketplace ruling).
- **return** — shopify id, order ref, lines, refund amount, take_reversed,
  payable_reversed — a return unwinds both sides of the settlement.
- **customer-reference** — shopify customer id only. PII stays in Shopify —
  no name, email, phone, or address column exists in this schema.
- **ad-spend line** — platform, campaign id + name, date, spend, currency,
  clicks, impressions.
- **supplier** — name (matched to Shopify's vendor field), default take rate,
  payment terms.
- **purchase order** — supplier ref, lines (variant ref, qty, unit cost),
  status, dates. V1 source RULED 2026-07-18 (below).
- **payout/fee line** — date, kind (payout, gateway fee, platform bill, books
  line), amount, currency, external ref, import batch.

## exposes

- **facts, read-only**: watching, economics, and the web surface open the
  same SQLite file read-only and query the tables above — the spine being
  sole writer is the contract that makes this safe.
- **typed connector methods** (the hands the fleet is handed): reads are free
  — read_products, read_orders, read_inventory — and every return carries a
  source ref (`shopify:product/<id>@<ts>`) a downstream claim can cite.
  writes are gated — mutate_product_field, mutate_price, mutate_inventory,
  catalog upsert (create/migration only; an upsert may not change a live
  price). a mutate without a valid capability handle fails closed — no write.
- **sync state**: last run, cursors, per-connector health — read by the web
  surface (see renders).

## consumes

- **Shopify Admin GraphQL** (dev store now; the real store at S4): products,
  variants, inventory, orders, refunds, customer ids. custom-app token;
  credentials live in the macOS Keychain, referenced by name, never in files.
- **ads read, Google first**: campaign spend and performance, read-only in V1.
- **books file-drop**: accounting exports / tax-authority-format CSV dropped
  into a watched inbox directory. file-drop is acceptable V1; no accounting
  API wiring yet.
- **supplier/PO facts** (RULED 2026-07-18 [owner]): a gated web form on
  the web surface — submit files a gated proposal, never a direct write —
  plus, where a prior body exists, a one-time carry-over import of supplier
  info from it — a ruled specific carry-over under the fresh-start law.

## mechanism vs config

- **mechanism** (store #2 takes it unchanged): the canonical schema · the sync
  engine (cursors, paging, pacing to the platform's returned rate budget) ·
  the file importer · the typed-method pattern with handle enforcement · the
  settlement split routine.
- **instance config** (this store's file): store id · shop domain · Keychain
  service names (references, never secrets) · field-class writer map — which
  agent writes which field class (single writer, enforced at connector scope)
  and which fields are fit-critical here · sync cadences · take-rate table
  per vendor/category · books CSV column map.

## behavior

1. **initial sync** — full pull of catalog and order history from Shopify,
   paged, paced to the returned rate budget. idempotent on shopify id: a
   re-run updates, never duplicates. every row lands with source + fetched_at.
2. **incremental sync** — on cadence per connector, cursored on updated_at.
   V1 polls. the webhook receiver is salvaged but stays dormant; polling
   carries. arming is owner-only, decided on a real freshness need
   (RULED 2026-07-18 [owner]).
3. **landing an order** — each line splits into take_amount + vendor_payable
   from the take-rate table; the rate applied is stored on the line, and
   a landed order keeps the rate it landed with when the table later
   changes (RULED 2026-07-18 [owner]). landing a return writes the unwind
   on both sides.
4. **file-drop import** — a dropped file is parsed by the instance column
   map; rows land as payout/fee lines carrying the file hash as import batch.
   re-importing the same file lands zero new rows.
5. **write path** — a mutate arrives with the handle the gate minted on
   approval (build.md part 3). the connector checks it is approved, unexpired,
   and names this method; executes idempotently keyed to the ledger id; writes
   the outcome back to that record. no handle: rejected before any network call.
6. **failure** — reads retry with backoff. a mutate retries at most twice on
   the same idempotency key, then stops and surfaces. a failed gated write
   lands as outcome: failed on its ledger record — visible, never silent.
   repeated failures pause that connector and show on the web surface.

## renders

on the parts view (spec/experience.md): what I am · my config rows · last run,
next run · per-connector health (cursor, rate headroom, paused, last error) ·
fact counts per entity with last-landed · import history · failed writes with
their ledger links. any fact opens to its source + fetched_at.

## checks

run in `the cartridge root` (command names proposed):

- initial sync against the dev store, then SQL: local product count equals
  Shopify's own productsCount; zero rows anywhere with NULL source/fetched_at.
- a mutate_price call with no handle, and one with an expired handle, are both
  rejected; a read-back shows the price unchanged on Shopify.
- the same books file imported twice: the second run lands 0 rows.
- SQL: zero order lines where take_amount + vendor_payable differs from line
  net revenue; a fully refunded test order nets take and payable both to zero.
- schema scan: no PII column (name/email/phone/address) exists; a repo grep
  finds no credential material — Keychain references only.

## v0 salvage

mined from `the tombstoned prior body (read-only reference)`
(read-only reference; re-spec clean is the ruling):

- **worth carrying, as patterns rewritten**: the read_*/apply_* split — the
  connector never gates, it executes only already-approved, handle-bound
  mutations · the fail-closed GraphQL wrapper (an errored mutation is never
  reported applied) · in-process Keychain resolution, token cached in memory
  only, never on disk · productSet upsert idempotent by handle · metafield
  definitions-first (undefined values stay hidden in the admin) · the
  fit-critical field set, as instance data · the source-ref shape. ledger.py's
  append-only construction and single-shot outcome are the gate part's salvage.
- **not to port — dead-kernel assumptions**: `.mind/` paths, SBOS_RUN_ID
  keying, mindguard/loom/sentry hooks (that kernel no longer exists) · shop
  domain and client id hardcoded in code (instance config now) · stdlib-only
  urllib (superseded by the FastAPI ruling) · the catch-all "any other field
  maps to descriptionHtml" write · the spend-cap card rail — V1 ads is
  read-only; no agent spend to cap yet.

## open

- V1 source for supplier and purchase-order facts — RULED 2026-07-18
  [owner]: a gated web form on the web surface (submit files a gated
  proposal, never a direct write), plus a one-time carry-over import of
  supplier info from a prior body where one exists — a ruled specific
  carry-over under the fresh-start law.
- take-rate table changes — RULED 2026-07-18 [owner]: landed orders keep
  the rate they landed with; recomputation is an economics-lens question,
  never a facts rewrite.
- OPEN [owner]: the ads developer token — which access level, applied for
  when. approval carries calendar lead time; it is not a flip-on.
- the webhook receiver — RULED 2026-07-18 [owner]: stays dormant; polling
  carries S1–S3. arming remains owner-only, decided on a real freshness
  need; its reachability trade (tunnel vs poll) is decided then.
