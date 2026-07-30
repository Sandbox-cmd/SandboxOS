# commerceos — build spec (product + technical)

what to build, where it lives, and what each part solves. every part names
the job rows it serves (spec/jtbd.md). drafted 2026-07-11 from the ratified
lens; awaiting the owner's correction pass. OPEN decisions are marked and
stay his.

## what commerceos is (decided, landed 2026-06-28; reaffirmed 2026-07-11)

- SandboxOS is the operating system. commerceos is an app within it.
  stores are products it operates — the rebuilt outdoor store is product #1.
- brain local and sovereign; the store's body lives in the world
  (Shopify + Google), because that is where customers are.
- commerceos carries generic mechanism; each store carries config and data.
  the placement test: would store #2 need it unchanged (mechanism), tuned
  (config), or not at all (data)?

## parts

### 1. the data spine — canonical model + connectors
serves: every O and C row (the hands and the facts).

- canonical entities, V1, concrete: product (specs + provenance per claim),
  variant, order, return, customer-reference (PII stays in Shopify; local
  records hold ids only), ad-spend line, supplier, purchase order,
  payout/fee line.
- one local store of landed facts (SQLite). every fact carries source +
  fetched-at. connectors land facts; nothing else writes facts.
- connectors, V1: Shopify Admin (GraphQL, typed methods; single writer per
  field-class enforced at connector scope) · ads read (Google first) ·
  books import (accounting exports / tax-authority-format CSV; file-drop is
  acceptable V1).
- v0 salvage: typed-method connector shape, shopify_live patterns, webhook
  receiver (stays dormant until the owner arms it).

### 2. watching — metrics + findings
serves: O1, O6.

- metric definitions are config rows: name, formula over the canonical
  model, dimensions (store/category/vendor/channel/cohort), cadence,
  baseline method (rolling, seasonality-adjusted). one engine evaluates all
  rows. adding a metric is config, not code.
- findings are first-class records: evidence, direction (risk / opportunity
  / insight), suggested route (which agent or the owner), disposition.
  unactioned findings age visibly instead of evaporating.
- drift, RULED 2026-07-18 [owner]: statistical bands per metric, computed
  from that metric's own evaluation history, with a plain-percentage
  threshold as warm-up until the history suffices — plus an AI reasoning
  layer: the analyst agent's hunts over the same facts.
- aging, RATIFIED 2026-07-18 [owner]: 30 days risk / 14 opportunity /
  14 insight before an unactioned finding shows as aged.
- beyond declared metrics: an analyst agent on cadence runs open pattern
  hunts (correlations, cohort shifts) and writes findings — provenance
  required on every claim; no provenance, no finding. it launches with
  six hunts: category sales shifts · vendor sales shifts · basket
  pairings · AOV drift · return-rate drift · catalog-health-vs-sales
  correlations.
- instance side: which metrics, which bands, which curve — the store's file.

### 3. the gate + the record
serves: O2, O4.

- action taxonomy: reversible (runs, recorded) · consequential (pauses for
  approval) · fit-critical (consequential subset for safety-bearing spec
  claims — a wrong temp rating is a safety claim, not content).
- thresholds per function, stored as config, moved only by the owner;
  every threshold move is itself recorded.
- append-only ledger of every action: intent, rationale, impact,
  provenance, outcome. business-semantic and queryable, not engineer traces.
- approval handle: an approved action mints a one-use capability keyed to
  the ledger id; connectors reject writes without a valid one. (v0's
  red-teamed anti-bypass pattern — the wall, not decoration.)
- same grammar as the workshop: agents stage, the owner lands.
  RULED 2026-07-18 [owner] — own ledger, ratified as built: different
  volume and cadence, same grammar. (was OPEN; revisit only if SandboxOS
  exposes its record as a library.)

### 4. the fleet
serves: O3.

- roster contract: manifest (scope, writer-class, autonomy level per
  function) · propose-loop · provenance discipline. single writer per
  field-class, enforced where the write happens.
- RULED 2026-07-18 [owner]: the manifest's source of truth is
  `.claude/agents/` frontmatter alone. the web roster reads those files;
  there is no duplicate config row to drift.
- scheduler, RULED 2026-07-18 [owner]: jobs are config rows in the
  store's rhythm.json — a job registry replaces the hardcoded tuple.
  arming stays the owner's keystroke.
- build cap this run, RULED 2026-07-18 [owner]: analyst + content/seo
  agents — the two NEW builds. the catalog agent already exists and runs
  (the proposer ran the first delegated batch live 2026-07-11, on the
  record). the ads agent is dropped this run (no token, no connector).
  pricing stays deferred until analyst evidence — price is a writer-class
  held by nobody; price moves arrive as analyst findings or owner drafts
  and execute only under an owner-approved handle. no forecaster —
  unearned until real data demands it.
- roster backlog, RULED 2026-07-18 [owner] — build later, each arriving
  with a job row and a writer-class:
  - merchandiser — collections and placement · writer-class:
    merchandising.
  - images agent — image sourcing and quality · writer-class: images.
  - localization (Arabic) — Arabic-language content · writer-class:
    translations.
  - supplier clerk — supplier and purchase-order records · writer-class:
    supplier facts.
  - bookkeeper — the monthly close · writer-class: book entries
    (proposals only).
  - market-and-competitor watcher — market findings · writer-class: none
    (findings only).
  - supplier-and-brand discoverer — sourcing leads · writer-class: none
    (findings only).
  - supplier-and-vendor onboarder — onboarding records · writer-class:
    vendor records.
- runs on SandboxOS's own agent mechanism. the fleet is the app using the
  OS's powers, not a second runtime.

### 5. the catalog loop
serves: O3, C1, C2.

- the standing loop: ingest → audit → prioritize → act (gated) → verify
  rendered → decay/re-test.
- audit dimensions are config: classification, specs, provenance, identity
  (GTIN), merchandising, seo, images.
- verify-rendered is law: a push is not done until the live surface shows
  it. (the files-exist scar is on the record across four bodies.)
- v0 salvage: pipeline stage design, audit scoring shape, seed scripts as
  reference. taxonomy v1.2 is instance data, carried as-is.

### 6. economics from actuals
serves: O5.

- engine: contribution per order/category/vendor and period P&L computed
  from landed facts (orders, fees, COGS, spend, returns), reconciling to
  the books for a known period before it is trusted.
- simulation is a lens over the same numbers: scenarios are deltas on
  actual baselines. the prior simulator's interaction ideas survive; its invented
  defaults do not.
- RULED 2026-07-11 [owner]: **commission marketplace.** the marketplace
  positioning stands; the old books' contradiction (reseller accounting
  under marketplace marketing) is fixed forward, not inherited.
  consequences, encoded once:
  - vendor settlement is a first-class economics object: take rate
    (per vendor/category), vendor payout,
    vendor payable — every order splits into take + payable at landing.
  - the books carry a commission account from day one; returns unwind
    both sides of the settlement, not just revenue.
  - checkout mechanics (Shopify checkout + commerceos settlement ledger
    vs a multivendor app) is an S3 design decision — proposed: Shopify
    checkout as-is, settlement computed and recorded by commerceos.
- RULED 2026-07-18 [owner]: **fresh start.** prior financial data is cut
  off and treated as learnings from a past experience. the prior books
  remain proof the reconciliation engine works, and a source of learnings;
  the gold period is ratified from the business's first real books.
- take rates, RULED 2026-07-18 [owner]: a table — vendor default +
  category override; SKU exceptions allowed but flagged. landed orders
  keep the rate they landed with. payment fees are borne by the take
  side.
- E5 VAT, RULED 2026-07-18 [owner]: a decision brief goes to the owner
  and their accountant; the decision itself stays parked [owner].

### 7. the web surface
serves: O4 — and is the condition every part ships under.

- every part self-reports into one local web app: what I am, my state, my
  config, last run, next run, track record. a part that does not render
  does not ship.
- stack, RULED 2026-07-11 [owner]: light framework — FastAPI + a small
  frontend build for the web surface (developer experience over stdlib
  purity). still local-first: SQLite, SSE, localhost/LAN;
  phone-reachable approvals (tailscale for reach, ntfy for push).
- surfaces defined in spec/experience.md.

### 8. the concierge
serves: C1, C2 — as amplifier. phase 2 by design.

- deferred until the catalog can back it: specs sourced and consistent
  first. refuse-to-guess on fit-critical claims — cite or decline, per
  claim, disclosed as AI up front.
- runs on separate production inference when it comes; customer-serving
  traffic never rides the personal subscription pool.

## multi-store — the cartridge and its stores

RULED 2026-07-18 [owner] — multi-store is built now, overruling the
earlier wait-until-earned posture. commerceos ships as a cartridge; each
store is a project using it. the shape (shape B):

- `stores/registry.json` names the stores. one resolver
  (`commerceos/stores.py`, `resolve(store, file)`) replaces the ten
  hardcoded stores/demostore path literals. `COMMERCEOS_STORE` picks the
  store for a run.
- one database and one append-only ledger per store (`data/<store>.db`).
  schemas and the single-writer guards are unchanged.
- the web surface gains a store context: one store picked, shown on the
  masthead (spec/experience.md); switching is explicit.
- the rhythm arms per store — one launchd label each; arming stays the
  owner's keystroke.
- the placement test above stops being a thought experiment: the
  registry, the resolver, and the per-store db/ledger enforce it in code.
- proof: a scaffold store (`stores/scaffold/`) onboarded end-to-end.

## where it lives

- RULED 2026-07-11 [owner], AMENDED same day by his word ("i dont want it
  living somewhere else"): the body lives INSIDE the workshop —
  `the cartridge root`, the first cartridge. specs and the
  backlog live in the cartridge beside the code; the channel keeps the
  record's files (CHANNEL.md, CANON.md, inherited/). loaded from the
  foundation-v2 cart. Python 3.14;
  FastAPI + a small frontend build for the web surface (see part 7);
  SQLite for facts and the ledger.
- the tombstoned body (the tombstoned prior body) stays
  read-only reference — mined, never ported blind.

## v0 posture

RULED 2026-07-11 [owner] — re-spec clean, rebuild on the current workshop
against this spec. the kernel v0 rode (loom, .mind, sentry) no longer
exists here; porting blind imports its assumptions. mine the tombstone
for: taxonomy v1.2 · policy-table shape · gate/ledger logic · pipeline
stages · audit dimensions.

## slices — each proves a job live, each carries a check

| slice | proves | contents | check |
|---|---|---|---|
| S1 control loop | O1, O2, O4 | facts landing (orders + catalog from the dev store) · gate · ledger · web brief + approvals | one end-to-end gated write against the dev store, visible in the web surface, on the record |
| S2 catalog loop | O3, C2 groundwork | audit + remediation on the dev store — images, GTIN and specs are the open fronts | health-report delta + verify-rendered samples |
| S3 economics | O5 | books + orders in, take/payout settlement + per-order economics out | reconciles against the business's first real period; the prior period stays the mechanism proof [rulings landed: commission marketplace · fresh start 2026-07-18] |
| S4 store rails | C3 | theme, payments, delivery, domain | name-gated [OWNER] |
| S5 concierge | C1, C2 amplified | after S2 earns it | cite-or-decline holds on a fit-critical test set |

sequence: S1 → S2 → S3 through the trough · S4 on the name · S5 earned.
your market's peak season is the clock.

## standing constraints (carried from landed canon)

- no secrets in specs or canon; credentials live in Keychain.
- PII stays in Shopify; local records carry references, not identities.
- nothing arms itself: scheduled/autonomous runs start owner-armed.
- customer-serving inference never rides the personal subscription.
