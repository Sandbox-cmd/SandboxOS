# part: economics from actuals
serves: O5 (spec/jtbd.md)
state: draft v1 — 2026-07-11; rulings of 2026-07-18 folded. OPEN items
marked.

## purpose

steer the money from what actually happened. every number this part shows
is computed from landed facts — orders, returns, fees, spend, costs, books —
and every scenario is a delta on an actual baseline.

the anti-pattern is on the record as a scar: two prior simulators computed
on invented defaults and never read the ledger — the simulator never met
the ledger. this part exists to
make that impossible. a number that cannot cite its source facts does not
render; a scenario that does not name its baseline period does not exist.

the model is RULED (2026-07-11, owner): commission marketplace. vendor
settlement is first-class — every order splits into take + vendor payable
at landing; the books carry a commission account from day one; returns
unwind both sides. the old books' reseller accounting (full sale booked as
revenue, no commission account) is fixed forward, not inherited. checkout
mechanics proposed: Shopify checkout as-is; commerceos computes and records
the settlement (S3 design detail).

fresh start is RULED 2026-07-18 [owner]: prior financial data is cut off
and treated as learnings from a past experience — no carry-over except
named specifics. consequence: the prior books remain (i) proof the
reconciliation engine works — a to-the-minor-unit result stands as a
mechanism proof — and (ii) learnings. they are NOT the standing gold
period. the reconciliation gold period and its tolerance are ratified from
the business's first real books, when they exist. this re-scopes the S3
items below.

## owns

- settlement records: per order, the split into take (per the take-rate
  table) and vendor payable — and the unwind when a return lands. both
  sides always move together.
- contribution results per order, category, and vendor.
- period P&L, assembled from facts and settlements.
- scenario definitions: a named baseline period (actuals) plus a set of
  deltas. no scenario stores free-standing invented numbers.
- reconciliation state: which periods reconcile to the books, and the
  unreconciled deltas per period.

does not own: the facts (the data spine owns those), metric evaluation
(watching), thresholds and approvals (the gate).

## exposes

- economics views for the web surface: P&L by period, contribution tables,
  settlement totals, scenario compare.
- metric inputs for watching: contribution-margin rows, BNPL fee share,
  return-cost rows — watching reads them as metric rows.
- reconciliation reports: period, books total vs computed total, delta per
  line, reconciled yes/no.

## consumes

facts from the data spine, nothing else:
- orders and returns (Shopify connector).
- payout/fee lines — gateway and platform fees as they actually charged.
- ad-spend lines (ads read connector).
- supplier and purchase-order costs, for lines that carry inventory.
- books imports (accounting exports / tax-authority-format CSV, file-drop
  V1) — the reconciliation target.
plus instance config: take-rate table, fee stack, tolerance, gold period.

## mechanism vs config

engine (store #2 uses it unchanged):
- settlement math: order -> take + payable; return -> unwind both sides.
  payment fees are borne by the take side — vendor payable stays price
  minus take (RULED 2026-07-18 [owner]; per-vendor config remains
  possible later).
- contribution and period P&L assembly, with fact-id provenance per cell.
- scenario deltas over a baseline period; side-by-side compare.
- the reconciliation comparator: computed period vs books import, line by
  line, within a stated tolerance.

instance config (this store's file; store #2 writes its own):
- take rates: your own. shape RULED 2026-07-18 [owner]: vendor default +
  category override; SKU-level exceptions allowed but flagged as
  exceptions on the economics surface.
- fee stack: your platform rate + your gateway rates, each with its
  per-transaction fee. BNPL is typically the expensive tail.
- sanity bands for scenario inputs: an AOV range and a conversion floor
  from your own history. bands warn; they never substitute for facts.
- reconciliation tolerance and the gold period (both OPEN below).

## behavior

1. order lands (fact) -> settlement split computed and recorded: take per
   the take-rate table + vendor payable, as a commission entry dated and
   keyed to the order's fact id. the rate applied is stored on the line;
   landed orders keep the rate they landed with when the table later
   changes — recomputation is an economics-lens question, never a facts
   rewrite (RULED 2026-07-18 [owner]).
2. return lands -> the linked settlement unwinds both sides: take reversed,
   payable reduced. never revenue-only — that was the reseller books' bug.
3. fee, payout, spend, and cost lines land -> matched to orders and periods
   where matchable; unmatched lines go to a visible unreconciled bucket and
   age there. nothing silently drops.
4. period close -> P&L assembled from facts + settlements, compared to the
   books import for that period, delta per line. the period is marked
   reconciled only when every line is within tolerance.
5. scenario: pick a baseline period (actuals) -> apply named deltas (take
   rate, fee mix, ad spend, return rate, volume) -> recompute -> compare
   against the baseline side by side. the scenario stores the baseline
   reference and the deltas, nothing else.
6. every displayed number links to its source facts: any cell drills down
   to the fact rows that produced it. missing inputs render as a named gap,
   never as a default.

## renders

self-report on the web surface (the part-7 condition):
- reconciliation status: last known-good period, periods pending, and the
  unreconciled deltas per period with their age.
- settlement totals: take earned, vendor payables outstanding, unwinds.
- P&L by period, every cell drillable to facts.
- config in force (take-rate table, fee stack, tolerance), last run, next run.

## checks

the S3 gate — runnable, exit code is the verdict:
- `commerceos econ reconcile --period <gold> --tolerance <t>` — computed
  P&L for the gold period matches the real books line by line within the
  stated tolerance (0.5% per line stays the proposal on the table).
  RULED 2026-07-18 [owner]: the gold period and tolerance are ratified
  from the business's first real books, when they exist; prior-period
  books stand as mechanism proof + learnings, not the standing gold
  period (the fresh-start ruling above). historical books may be
  reseller-shaped (full sale as revenue, no commission account), in which
  case a run against them reconciles only at the lines those books carry:
  GMV, refunds, purchases, fees, spend. keep your proof anchors in a
  reconciliation report beside the period they came from. (a lesson from
  this build: a trio of headline numbers rode the spec for weeks before a
  challenge found nothing on the record computed them — an anchor with no
  computation behind it is a claim in costume.)
- `commerceos econ selftest roundtrip` — a synthetic order + full return
  nets to exactly zero on both sides: take, vendor payable, and the
  commission account all return to their prior balance.
- `commerceos econ audit provenance --period <gold>` — every rendered P&L
  cell resolves to at least one fact id; zero orphan numbers.

## v0 salvage

- the prior simulator's unit-economics module: the formula kit
  (LTV, CAC, LTV:CAC, payback, break-even, contribution margin, runway) as
  reference math only — port the formulas, test them first (a known
  LTV:CAC bug at defaults is on the record), and feed them facts.
- the prior simulator: the scenario-over-baseline interaction ideas (sliders,
  side-by-side compare, seasonality shaping) as interface reference.
- NONE of their default numbers — every one was invented; none crosses
  over.

## open

- take-rate table shape — RULED 2026-07-18 [owner]: vendor default +
  category override; SKU-level exceptions allowed but flagged as
  exceptions on the economics surface.
- mixed lines: stocked/consignment heroes carry COGS, not a payable — how
  the settlement record marks them; decided against sell-through data
  at S3 (per the store spec).
- who bears payment fees inside the split — RULED 2026-07-18 [owner]:
  the take side. vendor payout stays price minus take; per-vendor config
  remains possible later.
- VAT treatment in commission accounting: under the marketplace model the
  store's own taxable base changes (commission vs full sale) while a
  tax-authority filing may speak full-sale. write the brief (principal vs
  disclosed-agent) and park the decision with your accountant.
- the reconciliation gold period — RULED 2026-07-18 [owner]: ratified
  from the business's first real books, when they exist; prior periods
  stand as mechanism proof + learnings, not the standing gold period
  (the fresh-start ruling in ## purpose).
- tolerance value — RULED 2026-07-18 [owner]: ratified with the gold
  period from the business's first real books; 0.5% per line stays
  the proposal on the table.
