`git diff --quiet 3c506f9..HEAD -- spec/frames/roster.md spec/parts/fleet.md commerceos/fleet/manifest.py commerceos/spine/writes.py commerceos/gate/policy.py commerceos/gate/gate.py commerceos/web/app.py commerceos/watching/findings.py commerceos/economics/reconcile.py commerceos/rhythm/runner.py commerceos/spine/seeds.py || echo "STALE — re-true before build (see RUNBOOK)"`

# scout — the design-before-pull agents

as-of: commit 3c506f9, suite 394 green.

mission of this scout: for each of the five backlog roster agents —
supplier clerk, bookkeeper, market-and-competitor watcher,
supplier-and-brand discoverer, supplier-and-vendor onboarder — say what
already exists, what its manifest would declare, and the design question
that blocks it. the supplier clerk is closest; its pull-ready row is
spelled out below.

## the binding laws (verified seams)

- **manifest = frontmatter alone**: spec/parts/fleet.md:22-30 (RULED
  2026-07-18) — the `.claude/agents/` file's frontmatter is the sole
  source of truth; the /fleet page renders from the files. parser:
  commerceos/fleet/manifest.py — REQUIRED keys :43, STATUSES
  ("built","building") :45, AUTONOMY ("acts","parks","proposes-only")
  :46, `read_manifest` :56 (refuses malformed files loudly), `roster`
  :122, `track_record` :131. **a design-stage agent has NO manifest file
  until its build starts** — the parser has no "planned" status.
- **the hand-counted footer**: commerceos/web/app.py:932 — "the backlog
  carries 8 more planned agents". it moves BY HAND every time one of
  these lands (the F1-fleet proof's standing note).
- **one writer per field-class**: fleet.md:34-38, enforced where the
  write happens. the write door's full method set today:
  commerceos/spine/writes.py :87-105 dispatch (mutate_product_field,
  mutate_variant_field, mutate_price, mutate_product_state, mutate_seo,
  mutate_spec_verification, record_supplier).
- **the autonomy ladder**: FW1 (built, backlog M-table) — widening one
  rung at a time through `gate.move_threshold`
  (commerceos/gate/gate.py:175), owner-only, on the ledger.
- **findings-only agents' one door**: commerceos/watching/findings.py
  `mint` :63 with `_clean_evidence` :50 — evidence must name evaluation
  or fact ids or the claim is refused.
- **scheduling**: commerceos/rhythm/runner.py — `BUILTIN_JOBS` :222,
  `registry_rows` :230; a per-agent job joins by adding a rhythm.json
  row, no code edit (fleet.md behavior 1). arming stays the owner's
  keystroke.
- **the missing check on record**: fleet.md's checks name
  tests/fleet/test_grant_lint.py (every manifest grants only gated
  tools) — it does not exist yet; tests/test_fleet_manifest.py carries
  no grant assertions. any new agent build should bring it.

## the five, each in turn

### 1. supplier clerk — CLOSEST (rides SP1, done)

**what exists**: the whole write path. /suppliers form
(commerceos/web/app.py :1689 GET, :1699 POST), submission through
gate.submit as consequential — `record_supplier` sits on the
CONSEQUENTIAL floor (commerceos/gate/policy.py:57) — executor
`_record_supplier` (commerceos/spine/writes.py:312; append-only
po_lines, COALESCE-kept terms), the approvals card renders the proposal
in plain AED+fils words (app.py:1281), 15 pins in
tests/test_supplier_form.py, producer SHIP-CLEAR (backlog SP1 row).

**its manifest would declare**: name supplier-clerk · writer_class
"supplier + purchase-order facts" · functions: record-supplier-facts:
parks (the consequential floor makes "acts" impossible by policy — the
manifest should say what the gate enforces).

**the design question that blocks**: the SOURCE. SP1 is the owner's
hand on a form; a clerk agent needs a document stream to read — accounting
invoices, supplier PDFs landed via the spine, or an inbox. roster.md:28
said "shape depends on sitting D (books import vs gated form)"; the
gated form won, so the clerk's remaining question is only: what does it
read?

**what its pull-ready row needs** (per pull rule 1): the source named
by the owner + a check of this shape: "a landed supplier document
becomes a parked record_supplier proposal with provenance (source +
fetched_at); approval lands it through the existing executor; a replayed
document stages nothing twice." everything downstream of the proposal
already exists and is pinned.

### 2. bookkeeper — monthly close, reports only

**what exists**: the whole close mechanism — economics/reconcile.py
(`selftest_roundtrip` :123, `write_report` :175, `main` :243), the
rhythm registry a monthly cadence row plugs into, and the monthly-close
skill row (roster.md:38-41). writer_class "none — reports only";
functions: monthly-close: proposes-only.

**the design question that blocks**: there are no real books to close —
S3 was re-scoped 2026-07-18 (backlog, owner-gated list): the old books
are learnings + the 6-fils mechanism proof; the gold period ratifies
from the NEW business's first real period. a second, smaller question:
where the staged summary lands (a report file + a staged note is the
reports-only answer; a gate proposal would contradict its writer-class).

### 3. market-and-competitor watcher — NEW writer-class: market facts

**what exists**: nothing of its substrate. the findings door refuses
evidence that names no evaluation/fact ids (findings.py:50-60) —
an external market observation HAS no fact id until a market-facts
table exists with its own single writer. flagged in fleet.md:57 as
"findings + market facts — new writer-class, flagged".

**the design questions that block** (design before pull, confirmed):
where market facts land (a new spine table? who owns the writer — this
agent alone, per one-writer law); what sources are permitted (the CW9
media ruling took a no-scraping posture — does it extend to competitor
pages?); how a market fact carries provenance (AGENTS.md: every fact
carries source + fetched_at — a URL + fetched_at shape needs designing).

### 4. supplier-and-brand discoverer — findings only

**what exists**: the full pattern to copy — .claude/agents/analyst.md is
the manifest prior art; the analyst's whole loop (watching/analyst.py,
tests/test_analyst.py) is findings-only done right.

**the design question that blocks**: the same evidence problem as the
watcher — a discovery from the open web names no evaluation or fact
ids, so today the one door refuses it. either watching's intake grows an
external-source evidence shape (a spec change to the watching part,
staged first per spec-first law) or discoveries land as facts before
they mint. this is the SAME design sitting as the watcher's — one
ruling can serve both.

### 5. supplier-and-vendor onboarder — gated config proposals

**what exists**: the least. take rates are deliberately NULL until real
contracts — spine/seeds.py:1-8: "take rates stay NULL — they arrive with
real contracts (F6), never from history."

**the design question that blocks**: what an approved config proposal
EXECUTES against. no writes.py method covers supplier/vendor config —
but the pattern exists: `gate.move_threshold`
(commerceos/gate/gate.py:175) already writes a config-shaped change
through the gate — it edits stores/<name>/policy-table.json values
(money_threshold, auto_approve) as a recorded, owner-only,
mint-and-consume ledger action. the onboarder's question is a
generalization, not an invention: widen the move_threshold pattern to
supplier/vendor config keys (take rates, terms), or widen
record_supplier to carry them. also calendar-gated: F6 (supplier
reconnects) is name-gated on F1, so the onboarder's real work starts
post-name.

## the ruling cards — two, each one keypress

### card 1 — the entry order

**the question:** approve the order the five enter design and build.

the recommended order: **supplier clerk first** (only its source is
missing; every wall downstream is built and pinned) → **bookkeeper**
when the new business's first real books exist (its mechanism is done
today) → **watcher + discoverer together** behind ONE market-facts /
external-evidence design sitting (they share the blocking question) →
**onboarder last** (name-gated F6; its door is a widening of the
move_threshold pattern, see above).

**what this k unlocks:** the order stops floating — the market-facts
design sitting gets scheduled as the watcher/discoverer's next step
instead of hanging on "someday", and the roster rows read in this
order. it makes no agent pullable by itself.

### card 2 — the clerk's source

**the question:** what does the supplier clerk read?

the options: (a) accounting documents · (b) supplier documents landed via
the spine · (c) it stays the owner's hand-form until an import stream
exists — no agent yet. the scout recommends (c) as the honest default
until a real document stream is named.

**what each k unlocks:** (a) or (b) — the clerk's backlog row gains
its check (the named source slots into the check shape above) and the
clerk becomes pullable the same day; everything downstream of the
proposal already exists and is pinned. (c) — no clerk yet: the
/suppliers form stays the only entry door, the clerk row stays
design-parked, and this card re-opens the day a real document stream
exists. nothing becomes pullable under (c).

## what the full pack needs (per agent)

- clerk: the source ruling + a reader for it, the manifest file, pins
  copying tests/test_supplier_form.py's replay/provenance shapes, the
  footer count moved, test_grant_lint.py brought to life.
- bookkeeper: real books (calendar, not code), the staged-summary
  landing shape, a rhythm row (config, no code edit), manifest.
- watcher + discoverer: the market-facts/evidence design ruled and
  spec'd into spec/parts/watching.md FIRST (spec-first law), then the
  table + writer + manifests.
- onboarder: F1 → F6 first; then the move_threshold-pattern widening
  (or the record_supplier widening) spec'd as its own delta before any
  pack.
