# commerceos — operator experience spec

the surfaces where the operator's jobs happen, derived from spec/jtbd.md
(O rows). the customer's experience lives on the store's own channel — this
file is the brain's face, not the store's.

## the grammar (one rule everywhere)

agents stage, the owner lands. every surface is a view over the same
record; approving is one action that looks the same everywhere it appears.

## the register — how it looks, how it is organized

RULED 2026-07-12 [owner], on the record; this file catches up:

- visual register: teletext/broadcast — dense, typographic, built to be
  read at a glance. not a dashboard of cards.
- navigation is by job, not by part: home · decisions · operations ·
  record · money · growth (the findings stream). "system" (the parts
  view) rides the right corner of the nav on every page — the O4
  self-report stays reachable without crowding the jobs (as built).
- plain-language guard: a test fails the build if any code identifier or
  insider term reaches the screen. the operator reads plain words only.
- the catalog's interface contract lives in spec/experience-catalog.md.

## surfaces

### the brief — O1, minutes to the picture
- one screen on arrival: what happened since last visit · what waits on me
  · what the watching flagged (both directions) · the money line for the
  period against baseline.
- every line links to its record. nothing appears on the brief without a
  source behind it.
- outcome held: full picture in under five minutes, cold.

### approvals — O2, seconds to a decision
- the queue. each item: intent · why now · impact (money, scope,
  reversibility) · the exact proposed change · evidence links.
- one action to approve or reject; comment optional. stale money-moves
  expire rather than execute late.
- phone-reachable: push on consequential items, decide from anywhere.

### the record — O4, "why did X happen" in under a minute
- browse and search the ledger by part, product, day, kind. each entry
  reads: intent → rationale → what changed → outcome → who approved.
- findings show their lifecycle: noticed → routed → decided → done or
  aged-out. an ignored opportunity is visible as ignored.

### the parts view — O4, no blackbox
- every part self-reports: what I am · my config (rows, editable where
  safe) · last run and next run · track record (proposals made, approved,
  reversed) · autonomy level per function.
- autonomy widens on the fleet roster, not here (built 2026-07-19, FW1):
  each owning agent card carries the control beside the track record
  that earned it — why + explicit confirm, one rung at a time, every
  move recorded. the parts view self-reports; the fleet card moves.

### economics — O5, arithmetic not vibes
- actuals first: contribution per order/category/vendor, period P&L, the
  fee stack — reconciled numbers, each linking to its sources.
- the lens on top: scenario controls over the actual baseline (what the
  old simulator wanted to be), never detached defaults.

### findings — O1 and O6, both directions
- the stream of what the watching noticed: risks, opportunities, insights.
  filter by direction, area, status. unactioned items age visibly
  (30 days risk / 14 opportunity / 14 insight — ratified 2026-07-18).
- the analyst's hunt findings look like any other finding: evidence
  links, direction, aging. hunts add rows to the same stream, not a
  separate surface.

### the fleet roster — O4, who works here
- one roster page (/fleet, off the system corner), a card per agent read
  straight from its manifest file (the `.claude/agents/` frontmatter —
  there is no second config row to drift): what I am · scope · autonomy
  per function · track record computed from the ledger at render
  (proposals made, approved, reversed). the widening control lives on
  the owning card (see the parts view note).

### the verification card — O4, is it really live
- a small card wherever a push is in flight: what was pushed · what the
  live surface shows · verified or still waiting. done means verified
  rendered, never sent. (the files-exist scar is on the record.)

### the supplier form — money facts in, still gated
- a small form for supplier and purchase-order facts. submitting stages
  a gated proposal, never a direct write; the approved entry reads in the
  record like any other action.

## how it is served (RULED 2026-07-18 [owner])

- server-rendered pages with small interactive islands — no SPA.
- live updates arrive over SSE.
- phone pairing: a QR code on the desktop surface mints a long-lived,
  revocable token; reach is over tailscale.
- push, when it turns on, is self-hosted ntfy and notify-only: the
  notification tells, the surface decides. unchanged law.
- store context, once multi-store lands: one store picked, always visible
  on the masthead. switching stores is explicit, never implicit.

## principles

- boring and fast: local-first, loads instantly, works in the phone's
  browser.
- everything explains itself: every number opens to its formula and its
  sources; every action opens to its record.
- no dead ends: any item links onward to the thing it is about.
- the surface never acts alone: viewing is free; acting goes through the
  gate.
- the cold-read gate, RULED 2026-07-18 [owner]: no user-facing surface
  ships without the producer's cold read against this spec, findings
  staged as a note. findings BLOCK the ship until each is resolved or
  the owner overrules it — his keystroke, recorded. a debug surface
  never satisfies a product slice.
- one visual system across all surfaces. (the design-system channel may
  carry the tokens later; not V1-blocking.)

## what this is not

- not a BI tool — it answers the operator's six jobs, nothing else.
- not a Shopify admin duplicate — Shopify keeps its own house; this is the
  brain's view of decisions, health, and money.
