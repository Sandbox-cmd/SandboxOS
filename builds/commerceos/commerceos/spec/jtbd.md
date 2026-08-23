# the jobs — commerceos and its first store

foundation of the re-spec. ratified by the owner 2026-07-11. every part in
build.md and every surface in experience.md must name a row here; anything
that cannot name its job is cut.

## who hires

- **the operator** (Owner) — runs a commerce business essentially alone.
- **the customer** — a UAE adventurer equipping for an activity.

agents, pipelines, and dashboards are hired things, never job owners.
suppliers and AI shopping-agents appear inside job steps, not as main jobs.

## the operator's main job

> When I run my commerce business, I want to know it, steer it, and grow it
> in a few focused hours a week, so it compounds without consuming me — and
> without me ever wondering what it did in my absence.

| # | job step | when… I want… so I can… | desired outcomes (measurable) |
|---|---|---|---|
| O1 | know the state | when I sit down, I want everything that happened and everything that needs me in one view, so I can act on what matters in minutes | time-to-full-picture < 5 min · zero late surprises · flags carry both directions: problems and openings |
| O2 | decide | when a call needs judgment (price, spend, publish, refund, delist), I want context, options, and consequences together, so I decide in seconds and it executes exactly | time-to-decision in seconds · every decision carries its why · nothing above threshold moves without me · decidable from my phone |
| O3 | delegate the routine | when work is repeatable (spec enrichment, SEO, feed hygiene, campaign upkeep, sorting), I want it done to standard without me, so my hours go only where judgment lives | share of routine work unattended · reversal rate near zero · autonomy per function widens only on evidence |
| O4 | verify anything | when the system has acted for me, I want every action on a record with rationale and outcome, so I can audit any decision and adjust trust with evidence | 100% of actions on the record · "why did X happen" answered in < 1 min · no part of the system exists off the web view — if it runs, it renders |
| O5 | steer the money | when I plan or review, I want economics computed from what actually happened (orders, costs, spend, returns, fees), so calls rest on arithmetic — and when I weigh a move, I want to simulate it against that real baseline | P&L per order/category/vendor always current · simulation reads actuals, never invented defaults · one resolved answer to marketplace-vs-reseller, encoded once |
| O6 | grow deliberately | when the business runs steady, I want what's next surfaced with evidence (category gaps, AR-language demand, channel shifts, a second store), so growth is chosen, not stumbled into | opportunities arrive as findings with evidence · launching store #2 is config, not a second build |

the holistic reading: O1 + O6 are one watching job over the whole business,
both directions — never single-metric patches born from the last failure.
the no-blackbox requirement is O4's outcome, not a feature request.
the prior simulator's failure was an O5 failure: it never read the ledger.

## the customer's main job

> When I'm preparing for an adventure, I want to be correctly and confidently
> equipped for its real conditions, so nothing fails me out there.

| # | job step | when… I want… so I can… | desired outcomes |
|---|---|---|---|
| C1 | know what I need | when I plan a trip (3-day desert camp in December), I want the full kit for those conditions, so nothing's missing out there | complete kit from a described mission · gaps in existing gear identified |
| C2 | choose with confidence | when gear is fit-critical (temp rating, load, waterproofing, certification), I want specs I can trust, in my language, so I don't buy wrong | specs present, sourced, consistent on every surface · Arabic as real as English · no invented answers — silence over guesses |
| C3 | get it in time | when I order, I want predictable delivery and payment my way (card, BNPL), so I'm equipped before the trip date | delivery promise kept · payment options native to the market |
| C4 | recover when it goes wrong | when size or fit misses, I want an easy return and a straight answer, so a miss doesn't cost the relationship | returns without friction · support that knows my order |
| C5 | belong (emotional/social) | when I buy, I want to feel like an insider among adventurers, not a mark in a funnel, so I come back and vouch | repeat rate · community signal — the brand direction serves this |

note: C2 is served first by the catalog itself — clean, sourced, consistent
specs on every surface. the concierge is a second, stronger hire for the same
job, not the first. catalog truth before conversational surface.

## the map: job → hired solution → layer

| job | hired solution | commerceos (generic mechanism) | store instance (config/data) | rented rail |
|---|---|---|---|---|
| O1, O6 | watching the whole business, both directions | signal ingestion into one data model · metrics as config rows · findings routed with evidence | which metrics, bands, seasonality curve, the store's starting watch-list | shopify/google/ads data out |
| O2 | the decision gate + approval queue | gate engine, thresholds-as-config, approval flow, phone reach | threshold values per function · what counts as fit-critical here | — |
| O3 | the agent fleet + catalog pipeline | roster contract (single writer per field-class) · pipeline engine · audit scoring | taxonomy · enrichment sources · tone rules | shopify admin api |
| O4 | the record + the web view over everything | append-only ledger · every part self-reports into one web surface | — | — |
| O5 | economics from actuals + simulation as a lens | economics engine over orders/costs/spend · scenario layer on top | this store's cost structure, fee stack, the model ruling | zoho/shopify as sources |
| C1, C2 | catalog truth first; concierge second | spec/provenance model · refuse-to-guess policy · kit composition | datasheets, AR content, activity kits | storefront (shopify theme) |
| C3, C4 | checkout, delivery, returns | return/refund actions flow through the gate (they are O2 money-moves) | delivery promise, BNPL mix | shopify checkout · tabby/tamara · carriers |
| C5 | brand + community | — | the whole brand layer (name parked) | instagram/tiktok |

one system, read twice: the operator's jobs define the brain; the customer's
jobs define what the store must never get wrong.

## what V1 must serve

- **O1 + O2 + O4 are the control loop** — first, and as one piece: seeing
  without deciding is a report; deciding without a record is the old blackbox.
- **O3 ships for catalog first** — the proven loop; images, GTIN, specs are
  the open work the store needs anyway.
- **O5 baseline ships early** — actuals in, per-order economics out. blocked
  on the business-model ruling.
- **C1–C2 via catalog** in V1; the concierge amplifies later, when catalog
  truth can back it.
- **C3–C5 ride rented rails + brand work** — gated on the name, the owner's
  keystroke, not buildable around.

## the lens (reusable — ratified 2026-07-11)

1. name the executors — people, not software.
2. main jobs, then job steps: when/want/so-that + measurable outcomes.
3. map each job to the hired solution and its layer: generic mechanism /
   instance config+data / rented rail.
4. derive parts from jobs — a part that can't name its job is cut.
5. holistic from the start: watching, deciding, recording are one loop over
   the whole business, pointed both directions (risk and opportunity).
