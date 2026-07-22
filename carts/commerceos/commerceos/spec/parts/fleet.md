# part: the fleet

serves: O3 (spec/jtbd.md)
state: draft v1 — 2026-07-11; rulings of 2026-07-18 folded. all
former OPEN items are ruled below.

## purpose
O3: routine work — spec enrichment, SEO, feed hygiene, campaign upkeep —
done to standard without the operator, his hours going only where
judgment lives. the fleet is the agents doing that work, each inside a
contract making it individually trustable: one scope, one writer-class,
an autonomy level per function that widens only on evidence. it runs on
the current workshop's own agent mechanism — Claude Code subagents
raised from `.claude/agents/` in the commerceos repo; commerceos is an
app using the OS's powers, not a second runtime. fleet agents ride the
personal subscription pool; customer-serving inference is a separate
substrate (the concierge part's concern).

## owns
the roster contract — four parts, every agent implements all four:

1. **manifest** — the agent definition in `.claude/agents/`: name, scope,
   writer-class (the one field-class it may write), autonomy level per
   function, triggers, and the tool grant. RULED 2026-07-18 [owner]:
   the file's frontmatter ALONE is the manifest — each agent is a file,
   and that frontmatter is the source of truth for scope, writer-class,
   and autonomy per function; the web roster surface renders from the
   files; no duplicate config row anywhere. the grant is the wall: hands
   hold only the gated connector tools — no raw shell, no direct API.
2. **propose-loop** — read facts, draft acts, classify against the
   gate's taxonomy: reversible acts run and land on the record,
   consequential ones park (behavior 2).
3. **provenance discipline** — every claimed fact names its source or
   is marked unverified; an unverified claim cannot publish and cannot
   become a finding. no source, no claim — decline, never guess.
4. **coordination** — agents signal through events on the shared log,
   never through each other's fields. single writer per field-class,
   enforced where the write happens (connector scope), not convention.

the roster. RULED 2026-07-18 [owner]: the build cap this run is two
agents — analyst + content/seo. ads is DROPPED this run (no A7 token,
no connector; A7 sits on the owner's calendar), pricing is deferred
until analyst evidence. the remaining rows enter the backlog, each
pulled later when its dependency lands:

| agent | scope | writer-class | status · autonomy |
|---|---|---|---|
| analyst | open pattern hunts on cadence, for watching | findings only — no store writes | build this run — findings only, provenance on every claim |
| content/seo | copy, meta, structured data, feed legibility | pages, meta, structured data, feed | build this run — reversible content acts; customer-facing claims park; spec values pulled from catalog, never re-derived |
| catalog | enrichment against the audit: specs, images, GTIN, classification | product fields + publish state | BUILT — the proposer ran the first delegated batch live 2026-07-11 (on the record); reversible fields act; fit-critical specs and publish always park |
| ads | campaign upkeep, budget pacing | external ad campaigns | DROPPED this run (2026-07-18) — no A7 token, no connector; parks with A7 on the owner's calendar |
| merchandiser | collection membership (O3/C1) | collection membership | [backlog, pulled when the CW4/CW5 executors land] |
| images | product media (O3/C2) | product media | [backlog, unblocked — CW9 ruled hybrid] |
| localization/arabic | translations (C2) | translations | [backlog, pulled on the source + human-confirm ruling] |
| supplier clerk | supplier + PO facts (O5) | supplier + PO facts, via the ruled gated form | [backlog, pulled on dependency] |
| bookkeeper | reports at monthly close (O5) | reports only | [backlog, pulled on dependency] |
| market-and-competitor watcher | market watch (O6/O1) | findings + market facts — new writer-class, flagged | [backlog, pulled on dependency] |
| supplier-and-brand discoverer | discovery (O6) | supplier-candidate findings | [backlog, pulled on dependency] |
| supplier-and-vendor onboarder | onboarding (O5/O3) | gated take-rate + supplier config proposals | [backlog, pulled on dependency] |

pricing has no agent in V1 — RULED 2026-07-18 [owner]: deferred until
analyst evidence argues for one. price is a writer-class held by nobody:
pricing moves arrive as analyst findings or the owner's drafts, and a
price write executes only under an owner-approved handle — propose-only
through the gate. no forecaster — unearned until real data demands it.

## exposes
- proposals into the gate: every consequential or fit-critical act, as
  a full record — intent, rationale, impact, provenance.
- events onto the shared log: product.enriched, content.published, and
  the like — pointers, not state copies; Shopify stays operational truth.
- findings (analyst) into watching: evidence-carrying, routed by config.
- a self-report per agent into the web surface (renders).

## consumes
- facts (read) from the data spine — landed, with source + fetched-at.
  an agent never holds a raw API; source material (datasheets included)
  arrives landed via the spine or the catalog loop's ingest.
- approved handles via the gate — an approved proposal returns a one-use
  handle keyed to the ledger id; connectors reject writes without one.
- catalog-loop work orders — the loop owns ordering, the fleet the doing.
- events from the shared log — the coordination surface (behavior 4).

## mechanism vs config
- **mechanism** (store #2 gets it unchanged): the four-part contract, the
  propose-loop, the provenance rule, single-writer enforcement at the
  connector, event grammar, raise/park/re-raise wiring, self-report shape.
- **config** (each store's file): roster tuning — which agents are on,
  each function's starting autonomy level, scope bounds (categories,
  collections, ad accounts), armed triggers. thresholds live with the
  gate + record part; enrichment sources and tone rules with the catalog
  loop and the store instance.
- **data**: none owned here. proposals, events, outcomes land on the
  record and the log, kept by the gate + record part.

## behavior
1. **raising an agent.** session: the operator (or commerceos on his
   instruction) raises it from `.claude/agents/` with one work order.
   triggered: a schedule the owner armed raises it — nothing arms itself,
   disarming removes it. it wakes with manifest, grant, one work order.
   RULED 2026-07-18 [owner]: the scheduler is the rhythm's job list
   turned into a job registry, read from the store's rhythm.json config
   rows — name, what it calls, cadence, enabled. the hardcoded job
   tuple in the rhythm code is the seam this replaces; a per-agent job
   joins by adding a row, no code edit. a row that names no callable
   defaults to the built-in job of that name — that defaulting rule is
   why the current demostore config (which carries no such key) keeps
   ticking unchanged (challenge 2026-07-18). the widening also threads
   the tick's own config into every job — today the propose job re-reads
   the default config path, ignoring the config the tick was given.
   arming stays the owner's keystroke via launchd; per-store arming —
   one launchd label per store — arrives once multi-store lands, and
   the legacy label is disarmed first (multi-store part, behavior 5).
2. **the propose-loop.** read facts from the spine → draft acts →
   classify against the gate's taxonomy, checked against the manifest's
   table — no self-downgrade; a mismatch reads as the higher class →
   reversible acts execute through the gated connector and land on the
   record; consequential and fit-critical acts park in the approval
   queue, and a parked branch never blocks the rest of the run.
3. **provenance.** every claim names its source (a spine fact's source +
   fetched-at, a datasheet). no source → unverified → cannot publish,
   cannot become a finding. fit-critical: cite a datasheet or decline.
4. **coordination.** finished work others care about becomes an event
   on the shared log; interested agents consume it on their next raise.
   no agent writes another's field-class — the connector refuses and
   records the refusal.
5. **execute on approval.** an approved proposal re-raises its agent with
   the one-use handle; it executes through the connector, verifies
   rendered where the catalog loop demands it, writes outcome to record.
6. **autonomy widening.** a function's level moves only when the owner
   moves its threshold at the gate, evidence in view (reversal near zero
   is the O3 bar). every move is recorded. never the agent's act.

## renders
one card per agent on the web surface: name · scope · writer-class ·
autonomy level per function · proposals made / approved / reversed ·
last run and its outcome · next armed run, if any. the fleet page is
the roster read whole. an agent that does not render does not run.

## checks
- `pytest tests/fleet/test_writer_wall.py` — the content agent attempts
  a product-spec write; passes only if the connector refuses and the
  refusal is on the record.
- `pytest tests/fleet/test_park.py` — a consequential act (a publish)
  parks into the approval queue; a dev-store read-back proves no write.
- `pytest tests/fleet/test_provenance.py` — a finding with no source
  refs is rejected at watching's intake; a spec claim with no datasheet
  is declined.
- `pytest tests/fleet/test_grant_lint.py` — every fleet manifest in
  `.claude/agents/` grants only gated connector tools: no shell, no raw
  network, no ungated write.

## v0 salvage
carries (from inherited/specs/agent-roster.md, runtime-fleet.md): the
four-part contract shape · single writer per field-class, enforced at
connector scope, not convention · park, don't block — no human present
means a pending proposal is filed and that branch stops; an agent never
resolves its own gate · no self-downgrade of classification · the
forecaster reality-gate (out, slot reserved) · the hand-off shape: one
go-live touches several agents through events, never cross-writes.

dies with the kernel: the loom-layer PreToolUse gate wiring — the wall is
now the restricted tool grant plus the connector's writer-class check and
approval handle (gate + record part) · all `.mind` paths — manifests live
in the repo, the record where the gate + record part puts it · away.sh /
SBOS_RUN_ID / launchd plists / /arm plumbing — the surviving law:
owner-armed, never self-armed · the six-agent roster — concierge-ops,
merchandising, pricing deferred; V1 is four · the L0–L4 ladder words die;
the idea — autonomy per function, widened on evidence — stays plainly.

## open
- RULED 2026-07-18 [owner] — event log substrate: ratified as built —
  the ledger's events table is the log. (was: table vs jsonl.)
- RULED 2026-07-18 [owner] — scheduler shape: a job registry read from
  the store's rhythm.json config rows (behavior 1); the hardcoded job
  tuple is the seam replaced. arming stays launchd, owner-keyed;
  per-store labels once multi-store lands.
- RULED 2026-07-18 [owner] — pricing timing: deferred until analyst
  evidence; propose-only through the gate stands meanwhile.
- RULED 2026-07-18 [owner] — ads widening: moot this run — the ads
  agent is dropped (no A7 token, no connector); the question parks
  with A7 on the owner's calendar.
- RULED 2026-07-18 [owner] — manifest source of truth: the
  `.claude/agents/` frontmatter alone; the web roster surface renders
  from the files; no duplicate config row.
