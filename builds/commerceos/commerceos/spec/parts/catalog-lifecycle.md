# part: catalog-lifecycle
serves: the catalog operator (inventory.md — owns the judgment: which flags to act on, what to delist / relist / archive); O2 (decide — delist and publish are judgment calls that gate); O4 (verify — every state move on the record). grounds C1–C2 (only a true, live product reaches the customer).
state: draft v1 — 2026-07-12. OPEN items marked.

## purpose

the product lifecycle — the small, ruled state model that is the spine of
the operator view. every product in the catalog sits in exactly one of five
states, and every move between them is a single, recorded step with a who, a
when, and a why. this is the surface the operator actually runs the catalog
from: what needs my judgment, what I pulled, what I can put back, what is
done for good.

the holistic point, said plainly: this is not only a guard against noise. a
delist is **reversible** — pulling a product is a cheap, undoable act, and
relist puts it back live. that means the operator can pull anything on
suspicion and lose nothing but a little shelf time; a cleared flag or a fixed
spec earns the product its place back. the flag queue is a recovery queue,
not a graveyard — relist recovers revenue that a delete-happy system would
have thrown away. caution costs nothing here; only **archive** is final.

this part **decides and records** state. it never writes the store itself.
the actual store change that a delist / relist / publish / archive requires
runs through the **catalog-workflows** executor (C5w) and the gate — that
seam is named below and it is load-bearing. RULED 2026-07-12 (the
one-writer-per-table-set rule, AGENTS.md): the catalog-workflows executor
performs the Shopify write and returns the verified RECEIPT; THIS part is the
sole writer of the product state field AND the transition-history row, and it
commits both only on that verified outcome. the executor never writes
lifecycle's tables, and lifecycle never calls the store — one writer per side,
settled, not an open seam.

## owns

- **the product state field** — one current state per product, one of five
  (RULED 2026-07-12): `draft`, `active`, `flagged`, `delisted`, `archived`.
  no product is ever in two states. this field is the local truth the
  operator surface reads; it is mapped onto (never replaced by) the inherited
  Shopify `status` (see consumes + the mapping OPEN).
- **the transition history** — an append-only row per move: product, from
  state, to state, transition name, who (operator id or `detector`), when
  (timestamp), why (the ruling text / the flag reason / the detector
  evidence), and the ledger id of the store write when one was required. no
  delete, no rewrite — a move is a fact, like any other on the spine.
- **the flag-review queue** — the set of `flagged` products waiting for the
  operator's ruling, each carried **with its evidence** (the detector's
  signal list from quality.py, or the operator's own note). the queue is the
  work-list; a flag leaves it only when the operator rules and a transition
  fires.

## exposes

- **current state + flag reason per product** to the catalog operator
  dashboard: the state badge, and for a `flagged` product the evidence behind
  the flag.
- **state-change requests** to the catalog-workflows executor (C5w): for any
  transition that changes what the customer sees (publish, delist, relist,
  archive-of-a-live-product), this part emits the request — target
  transition, product, the operator's why — and the executor stages the exact
  store mutation and submits it to the gate. this part never calls the store.
- **counts-by-state** to the dashboard and to audit: how many draft, active,
  flagged, delisted, archived — the shape of the catalog at a glance, and a
  number the audit can trend.
- **transition history per product** to the catalog operator dashboard — the
  append-only move log (from → to, who, when, why, ledger id) that backs the
  per-product drill's history timeline. this part owns the history DATA;
  catalog-dashboard owns the timeline VIEW that renders it.

## consumes

- **detector flags from quality.py** — the delist detector's noise + decor
  candidates, each with its evidence list. a candidate raises `active ->
  flagged` and lands in the review queue (see behavior 2). the detector
  proposes; it never sets a terminal state, never deletes (its module doctrine
  verbatim).
- **operator rulings from the dashboard** — the human call on a flagged
  product, or an operator-initiated pull / relist / archive. a ruling names
  exactly one transition.
- **the inherited Shopify `status`** (from the data spine's product entity) —
  read on sync to place a newly-synced product in `draft` or `active` (see
  behavior 1). proposed mapping below; the exact mapping is an OPEN.
- **the executed-and-verified outcome, back from the workflow executor** —
  which held the gate's approved one-use handle, ran `spine/writes.py::
  execute()`, and verified the rendered store surface. this part commits the
  new state and writes the history row **only** when that outcome returns
  good — so the state field never claims a change the store did not actually
  make.

## mechanism vs config

- **mechanism** (store #2 takes it unchanged): the five states, the legal
  transitions between them, the one-current-state invariant, the append-only
  history, and the rule that a customer-visible transition commits only on a
  verified store outcome. the shape of the lifecycle is not store-specific.
- **config** (this store tunes): the flag **reasons** and the detector
  **thresholds** — quality.py's noise/decor signal lists, the corroboration
  law, the fit-critical field set that may auto-raise a flag. what counts as
  worth flagging is a per-store call; that a flag is a state is not.
- **data** (this store's file): the operator/vendor ids that appear in `who`.

## behavior

the state machine, RULED 2026-07-12 (pending land). each arrow is one real
move, recorded:

    draft --publish--> active
    active <--raise flag / clear flag--> flagged
    active|flagged --delist--> delisted
    delisted --relist--> active
    delisted --archive--> archived
    flagged  --archive--> archived
    archived : terminal — no outgoing arrows

`relist` is a **transition, not a state** — the owner explicitly rejected a
separate "relisted" state (a relisted product is just `active` again).
likewise "under-review" is **not** a state — a flagged product the operator
is working is still `flagged`.

1. **enter on sync (draft / active).** when the spine syncs a product, this
   part reads the inherited Shopify `status` and places it: a product live
   and published on Shopify enters `active`; a not-yet-published / draft
   product enters `draft`. the placement is recorded as the product's first
   history row (who: `sync`). no store write — the state is read from what the
   store already shows.
2. **raise a flag (-> flagged), rendered with evidence.** a flag is raised
   two ways: (a) the detector (quality.py) hands a candidate with its signal
   list; (b) the operator flags a product by hand with a note. either fires
   `active -> flagged` and puts the product in the flag-review queue **with
   its evidence** — the detector's signals (e.g. `decor_keyword, decor_type`)
   or the operator's words. raising a flag is operator/detector judgment and
   commits locally with a history row; whether it also pulls the product from
   customer surfaces is an OPEN (below). proposed: by default it does not —
   the product stays live until an explicit delist.
3. **rule a flag -> one transition fires.** the operator opens a flagged
   product in the queue, reads the evidence, and rules. the ruling maps to
   exactly one transition: **clear** (`flagged -> active`, the flag was
   wrong / the product is fine — commits locally, history row, product leaves
   the queue), **delist** (`flagged -> delisted`, pull it — store write, see
   below), or **archive** (`flagged -> archived`, gone for good — see
   archive). one ruling, one transition; never two.
4. **delist and relist (the reversible pair).** `delist` (`active|flagged ->
   delisted`) and `relist` (`delisted -> active`) both change what the
   customer sees, so both go through the seam: this part emits a state-change
   request to the catalog-workflows executor, which stages the exact Shopify
   mutation, submits it to the gate (delist/publish are **consequential** —
   they park for the owner per the gate's policy table), and on an approved
   one-use handle runs the store write and verifies it rendered. the state
   flips to `delisted` / `active` and the history row is written **only** when
   that verified outcome returns. a delisted product carries no lost data —
   relist is one ruling away. relist is the revenue-recovery path.
5. **archive (terminal).** `archive` (`delisted -> archived` or `flagged ->
   archived`) is final — `archived` has no outgoing arrow. archiving a
   product still live on the store also pulls it (a store write through the
   seam, gated); archiving an already-`delisted` product may be a purely
   local terminal mark (proposed) or map to Shopify `ARCHIVED` (mapping
   OPEN). because it is irreversible, archive is **always** an explicit
   operator ruling — never automated (proposed; retention OPEN).
6. **history records every move.** every transition — sync placement, flag
   raise/clear, delist, relist, archive — appends one row: from, to, who,
   when, why, and the ledger id when a store write backed it. the history is
   append-only; a product's whole life is its ordered rows.
7. **edit is an action, in any state.** editing a product (title, spec,
   metafield, image) is an **action available in every state** — draft,
   active, flagged, delisted, even a product mid-review — and it is **never a
   state**. an edit stages, gates (per its field class — fit-critical spec
   edits are human-gated), and verify-renders through the normal catalog-loop
   / gate path; it does not move the product between lifecycle states. you
   can fix a flagged product's spec and then clear its flag; the fix and the
   clear are two separate recorded things.

## renders

on the catalog operator dashboard (the console this run introduces — see
inventory.md gap 2), every result of this part is a real operator surface,
never a silent log:

- **the flag-review queue** — the list of `flagged` products awaiting a
  ruling, each row showing the product and **its evidence** (the detector's
  signals or the operator's note) and the ruling controls (clear / delist /
  archive). this is the operator's main work-list.
- **counts by state** — draft / active / flagged / delisted / archived, live
  counts, each a click into that set. the catalog's shape at a glance.
- **the per-product state + history timeline** — on a product's card: the
  current state badge, and the ordered history (from → to, who, when, why,
  and a link to the ledger record for any move that touched the store). a
  delist / relist links straight to its gate record and its verify-rendered
  receipt — so "why is this delisted" is answered on the spot.

cross-surface: consequential transitions (delist / publish / archive-of-live)
appear on **approvals** (O2) while they wait for the owner, and every
committed transition is on **the record** (O4) via its ledger id.

## checks

runnable, meaningful; each names the surface where its result is seen:

- **sync placement.** sync a known-published product and a known-draft
  product; the first lands `active`, the second `draft` — seen as the state
  badge on each product's card on the catalog console.
- **a detector flag reaches the queue with evidence.** run quality.py against
  the dev store; a flagged candidate appears in the **flag-review queue**
  carrying its exact signal list (e.g. `decor_keyword, decor_type`) — seen in
  the queue, evidence visible per row.
- **one ruling, one transition, one history row.** rule a flagged product
  (clear); exactly one transition fires and exactly one history row is
  appended with who / when / why — seen on the product's **history timeline**
  and cross-checked on the record.
- **delist then relist round-trips.** delist an `active` product (through the
  seam + gate), verify it left the customer surface, then relist it; the
  product returns to `active` with two history rows and two ledger ids — seen
  on the history timeline and on the record's verify-rendered receipts.
- **archived is terminal.** attempt any transition out of an `archived`
  product; it is refused, no history row is written — seen on the console as
  no available transition / a refused action, and confirmed by an unchanged
  history.
- **one state, always.** scan the state field store-wide: every product has
  exactly one current state, never zero, never two — seen as the counts-by-
  state totals summing to the product count on the console.
- **every store-backed move carries a ledger id.** SQL over the history:
  every delist / relist / publish / archive-of-live row names a ledger record
  whose outcome is `executed` — seen by opening any such row on the record.

## v0 salvage

- **mine:** quality.py's flag logic — the noise/decor signal detection, the
  conservative two-signal law (one signal alone never flags; a home brand
  only corroborates), and the evidence-per-flag shape — feeds this part's
  flag-raise (behavior 2) directly. the **"flag, never delete"** convention
  is the whole spine of the model: the detector raises `flagged`, the human
  rules, delete does not exist — the terminal move is `archive`, and it is
  the operator's, never the detector's.
- **do NOT port:** any auto-delete path. no code in this part removes a
  product; the strongest automated act a detector may take is raising a flag.
  removal from the store is `delist` (reversible) or `archive` (operator-only,
  gated).

## open

- **OPEN [owner]: does `draft` auto-publish when health passes a bar, or is
  publish always operator-gated?** proposed: always operator-gated in V1 —
  publish is a consequential store write and parks at the gate like any
  other; auto-publish-on-health is a later autonomy widening, earned on
  evidence (reversal rate), never the V1 default.
- **OPEN [owner]: retention before archive.** how long may a product sit in
  `delisted` before archive is offered or forced? proposed: no auto-archive
  in V1 — archive is irreversible, so it is always an explicit operator
  ruling; a delisted product may sit indefinitely (relist stays open). a
  retention nudge on the dashboard is a later nicety, not an automated purge.
- **OPEN [owner/design]: does `flagged` block a product from customer
  surfaces?** proposed: no by default — a flag is operator judgment and the
  product stays live until an explicit delist, so a false flag never costs a
  sale. exception to weigh: a **fit-critical / safety** flag (a wrong temp or
  load rating — the gate's fit-critical class) may auto-suppress the product
  from customer surfaces pending the ruling. this ties to the gate's
  fit-critical field set.
- **OPEN [design]: the exact Shopify `status` mapping.** proposed: `draft` ↔
  Shopify `DRAFT`; `active` ↔ `ACTIVE` + published; `delisted` ↔ unpublished
  / `DRAFT` (reversible — the mapping must preserve reversibility, losing no
  product data); `archived` ↔ Shopify `ARCHIVED`. `flagged` has **no** native
  Shopify status — it is a local overlay that rides on top of the product's
  live status (unless the fit-critical suppression above applies). confirm the
  delisted mapping with the executor (C5w) so relist is guaranteed lossless.
