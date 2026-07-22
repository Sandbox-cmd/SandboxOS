# part: watching — metrics + findings

serves: O1, O6 (spec/jtbd.md)
state: draft v1 — 2026-07-11; rulings of 2026-07-18 folded. one OPEN
item remains, marked below.

## purpose

the operator's standing attention over the whole business. O1: when he
sits down, everything that moved and everything that needs him has already
been noticed. O6: what's next arrives as findings with evidence, so growth
is chosen, not stumbled into.

one engine, pointed both directions by construction. every finding carries
a direction — risk, opportunity, or insight — and the self-report shows
the mix, so a watch-list drifting all-defensive is visible at a glance.
this is the standing correction made structural: watching is holistic,
never a set of narrow watchers born from past failures. old lessons enter
as instance config rows; the engine itself knows no store's history.

watching notices and routes. it never acts: anything consequential a
finding suggests goes through the gate, by whoever it was routed to.

## owns — metric definitions (config rows: name, formula, dimensions, cadence, baseline method), evaluations, findings (evidence, direction: risk|opportunity|insight, suggested route, disposition, age)

- **metric definitions** — config rows in the store's watch-list. each
  row: name · formula over the canonical entities · dimensions
  (store/category/vendor/channel/cohort) · cadence · baseline method
  (rolling or seasonality-adjusted) · optional bands, each edge naming
  its own direction — a high edge is a risk on return rate and an
  opportunity on conversion.
- **evaluations** — one record per metric per dimension slice per run:
  value, baseline, delta, facts window, staleness. what the surfaces read.
- **findings** — first-class records: one plain sentence of what was
  noticed · direction (risk | opportunity | insight) · evidence — the
  evaluation ids and fact ids behind the claim; no provenance, no
  finding, the write is rejected · suggested route (a named agent or the
  owner) · disposition (lifecycle state) · age since noticed.

## exposes — the brief's flag feed, the findings stream, metric values for the economics/web surfaces

- the brief's flag feed: open findings, both directions, oldest-aging
  first; every line links to its evidence.
- the findings stream: all findings, filterable by direction, area,
  status (the findings surface in spec/experience.md).
- metric values: latest evaluations with baselines, read by the brief's
  money line and the economics and web surfaces. read-only to all.

## consumes — facts from the data spine; analyst-agent findings

- landed facts from the data spine (SQLite), read-only: orders with their
  take / vendor-payable settlement fields (the commission-marketplace
  ruling makes vendor economics watchable), products, returns, ad-spend
  lines, suppliers, payout/fee lines. watching writes no facts.
- findings from the analyst agent (the fleet part): it hunts open
  patterns on cadence — correlations, cohort shifts — and submits
  findings through the same door as the engine's own. same shape, same
  law: a claim naming no evaluation or fact ids is refused. RULED
  2026-07-18 [owner]: the analyst launches with both hunt trios day
  one — order patterns: category sales shifts week-over-week · vendor
  sales shifts week-over-week · basket pairings · AOV drift by
  category · return-rate drift by category — and catalog-health-vs-
  sales correlations. every hunt's findings mint only through this
  door, evaluation and fact ids attached. hunt cadence lives in the
  agent's fleet manifest (ruled below); watching receives findings,
  it does not schedule agents.

## mechanism vs config — the engine vs the store's watch-list; adding a metric is a row, not code

- mechanism (commerceos, unchanged for store #2): the evaluator, both
  baseline methods, band logic pointed both ways, drift detection that
  fires on surges as readily as slumps — statistical bands per metric
  from its own evaluation history, plain-percentage warm-up until the
  history suffices (RULED 2026-07-18, behavior 4) — the finding record
  and its lifecycle, aging, provenance validation, routing.
- config (the store's file): the watch-list rows. a store's first rows
  come from its own earned lessons, carried as learnings and not as
  anchors, and they move on actuals. the shapes worth starting from:
  a return-rate band · ad efficiency (a ROAS target and a CPA ceiling) ·
  a seasonality curve for your market · BNPL fee share · vendor
  performance both directions (returns, margin from take, lead time) ·
  AOV and conversion floors. the values are yours — the engine ships
  with none.
- the engine ships with zero built-in metrics. an empty watch-list
  evaluates nothing and says so on its self-report — it never invents.
- adding a metric is a row. editing a row is a recorded action, not a
  gated one: bands move attention, not money. OPEN below.

## behavior — numbered flows: evaluate cadence, baseline computation (rolling + seasonality-adjusted), band breach -> finding, positive anomaly -> finding, finding lifecycle (noticed -> routed -> decided -> done/aged-out), aging of unactioned findings

1. **evaluate on cadence** — per row, compute the formula over spine
   facts for each dimension slice; write an evaluation. if the facts
   behind it are stale (source fetched-at older than the row's cadence),
   the evaluation says stale instead of pretending a number.
2. **baseline** — rolling: over the row's window of prior evaluations.
   seasonality-adjusted: rolling × the store's curve factor for the
   period, so a seasonal trough is not a false alarm. until the window fills
   from actuals, baseline reads "forming" and only configured band edges
   fire — no invented defaults, ever.
3. **band breach → finding** — value crosses a configured edge; a finding
   is minted with that edge's direction and the evaluation as evidence.
4. **positive anomaly → finding** — value beats baseline past the row's
   drift threshold with no band involved: an opportunity or insight
   finding. the same drift math that catches a slump catches a surge —
   both directions in one mechanism, not two code paths. RULED
   2026-07-18 [owner]: the drift threshold is a statistical band per
   metric, computed from that metric's own evaluation history; until
   the history suffices, a plain-percentage threshold carries the
   warm-up, and each row states which mode it is in on its surface.
   on top of the bands sits the reasoning layer — the analyst agent's
   hunts (consumes). the owner's words: "2 + smart and AI driven
   analysis and reasoning".
5. **lifecycle** — noticed → routed (owner-routed findings surface on the
   brief; agent-routed ones land in that agent's queue — whatever the
   route then wants to do that is consequential goes through the gate) →
   decided (disposition recorded: acted or dismissed, with reason) →
   done or aged-out.
6. **aging** — an open finding's age shows everywhere it appears. past
   the configured limit it is marked aged-out on the record — never
   deleted; an ignored opportunity stays visible as ignored. RATIFIED
   2026-07-18 [owner]: the limits are 30 days risk · 14 opportunity ·
   14 insight — the values in the store's watch-list.json move from
   provisional to ruled.
7. **no duplicates** — a breach persisting across runs refreshes the open
   finding's evidence and age; a new finding is minted only after the
   prior one is decided or aged-out.

## renders — self-report: active metrics, last evaluation, findings by direction/status, aging items

on the parts view: what I am · the active watch-list rows (editable where
safe, edits recorded), each stating its drift mode — statistical bands
or warm-up percentage · last and next evaluation per cadence · findings
counted by direction × status — the direction mix is the health of the
watching itself · aging items, oldest first · stale-fact warnings.

## checks — runnable (e.g. seed known facts, assert a breach finding AND an opportunity finding both fire; an unactioned finding ages visibly)

against a throwaway data-spine store seeded with known facts:

1. seed returns above the configured band and conversion above baseline;
   run one pass; assert a risk finding AND an opportunity finding both
   exist — the both-directions law, executable.
2. submit a finding with no evidence ids; assert it is rejected.
3. seed a revenue dip matching your curve's trough factor; assert no
   risk finding fires — the seasonality-adjusted baseline holds.
4. add a metric row to the watch-list file, no code change; assert the
   next pass evaluates it.
5. leave a finding unactioned past the age limit; assert its age is
   rendered along the way and its disposition ends aged-out, queryable.

## v0 salvage — none (new part); note what the old simulator got wrong (hardcoded invented defaults, never read actuals) as the anti-pattern

nothing to salvage — this part is new in the re-spec. the anti-pattern it
is built against: the old simulator hardcoded invented
defaults — a fictional store's numbers baked into code — and never read
actuals, so everything it "watched" was theater. the inverse, as law
here: every number a finding cites traces to a landed fact; baselines
form from actuals or say "forming"; the engine carries no store's
numbers in code.

## open — OPEN questions

- RULED 2026-07-18 [owner] — drift threshold method: statistical bands
  per metric, computed from that metric's own evaluation history, with
  a plain-percentage warm-up until the history suffices; each row
  states which mode it is in on its surface. on top sits the reasoning
  layer — the analyst agent's hunts. the owner's words: "2 + smart and
  AI driven analysis and reasoning".
- RATIFIED 2026-07-18 [owner] — aging limits per direction: 30 days
  risk · 14 opportunity · 14 insight. the values in the store's
  watch-list.json move from provisional to ruled.
- OPEN: is a watch-list edit ever consequential enough to gate — say, an
  edit that silences a band? proposed: recorded only in V1; revisit on
  the first silenced-band regret.
- RULED 2026-07-18 [owner] — the analyst's hunt cadence lives in its
  fleet manifest (the `.claude/agents/` frontmatter alone, per the
  fleet ruling); watching receives findings, it does not schedule
  agents.
