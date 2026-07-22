git diff --quiet 3c506f9..HEAD -- commerceos/catalog/classification.py commerceos/catalog/audit.py commerceos/catalog/canonical.py stores/demostore/taxonomy.json tests/test_catalog_classification.py || echo "STALE — re-true before build (see RUNBOOK)"

# CW3b — classification synonym/keyword fallback

## mission

teach the category resolver a small, data-driven synonym map so real-world
product types ("Torch") resolve to their locked category instead of being
silently unresolvable — and put those products INTO the classification queue
so the metafield gets persisted through the normal gated batch. genuine
nonsense stays out: a synonym is a curated mapping, never a fuzzy guess. the
map lives where the audit, the canonical builder, and the feature ALL resolve
through it, so no two surfaces can disagree about a product's category.

as-of: commit 3c506f9 · suite 394 green

## the backlog check (verbatim, backlog.md:158)

> a seeded "Torch" resolves to Flashlights + enters the queue; genuine nonsense stays un-queued

reading of the check: the synonym map carries `"torch" → "Flashlights"`; the
resolver then resolves Flashlights through the existing subcategory map to its
locked category (Lighting — the live taxonomy,
tests/test_catalog_classification.py:77), and the seeded product enters
`classification_queue` with that target. "resolves to Flashlights" is the
synonym hop; the persisted value stays what the feature always writes — the
locked category leaf.

## model

**sonnet** — no app.py, no new surface, a contained resolver change with a
sharp test battery. fully parallel-safe with CL1c (INDEX pull order 3).

## boundaries

- writes: **scratch dbs only.** `data/demostore.db` is read-only here (one
  read-only mining query in step 3). no store client, no live write, no
  rhythm arming.
- gate lane: unchanged — the feature stays reversible; this item never touches
  gate/ledger code.
- files: commerceos/catalog/classification.py, commerceos/catalog/audit.py,
  stores/demostore/taxonomy.json (staged data), tests/. canonical.py is a
  read-side seam (verify, don't edit). anything else = stop.

## the design note (read before writing code)

`_normalize_ptype`'s docstring (classification.py:58-67) says "no synonyms, no
fuzzy match" — that was CW3's scope line, and CW3b is the RULED widening: the
backlog row exists with a check, and the SPEC already names the shape —
spec/parts/catalog-workflows.md:158: *"source-anchored leaf map first, keyword
rules only as fallback"*. so this is spec-conformant, not a spec change; what
must change is the code's own docstring and the resolver. order is law: the
exact leaf-map resolution always wins; a synonym fires ONLY when exact
resolution (and the one normalization retry) found nothing.

**where the fallback lives — VERIFIED**: audit.py `resolve_category` (:119-129)
is the shared choke point. its callers: audit's per-product scoring
(audit.py:239), canonical's category fallback (canonical.py:252),
classification's `resolve_leaf` (:80, :85) and `_is_resolved` (:111). audit
does NOT call `resolve_leaf` — so a synonym map placed only in `resolve_leaf`
would leave the audit counting "Torch" unclassified forever (the health mirror
and the feature disagreeing). the map therefore applies INSIDE
`resolve_category`, with one escape hatch: `_is_resolved` must not count a
synonym-only resolution as "cleanly resolved", or the product never enters the
queue and the check fails. see the step plan.

**where the map lives as data — recommendation, not hand-waving**: inside
taxonomy.json under `classification.synonyms` (lowercased synonym → canonical
leaf name). why there and not a new file: `_index_taxonomy` (audit.py:95-116)
is the single indexing door all three consumers already share, and audit's CLI
(`--taxonomy`, audit.py:509) + `load_taxonomy` (classification.py:35-41) +
canonical all load exactly one taxonomy dict — a sibling synonyms.json would
need every one of those load paths threaded. the taxonomy file already carries
a `classification` section (ordered_rules, fallback, leaf_category_map). the
catch: the file is **LOCKED v1.2 (owner)** — see open questions in context.md;
the build proceeds on test fixtures either way.

## step plan (M — 3 checkpoints)

**step 0 — freshness.** run line 1. read context.md fully + its required reading.

**step 1 — write the failing tests** (checkpoint 1: failing + seam confirmed).
extend tests/test_catalog_classification.py (its fixtures and FakeStore are
the rig). the pins are named in context.md's test plan — the backlog-check pin
verbatim first: seeded "Torch" enters the queue with a locked target; "Zzz
Nonsense Widget" stays out.

**step 2 — build to green** (checkpoint 2: suite green ≥ 394 + new pins, zero
skips; laws checklist; outside-seam touch = stop):

1. `audit.py _index_taxonomy` (:95-116): index
   `taxonomy["classification"]["synonyms"]` (missing → `{}`) into the tax dict
   as `synonyms` {lower(synonym) → canonical leaf}. validate loudly: a synonym
   whose target leaf resolves to no locked category is a config error —
   `ValueError` naming the synonym and the target (the audit already fails
   closed on bad config, :194-199). a synonym that collides with a REAL leaf
   name is also refused — a synonym may never shadow an exact resolution.
2. `audit.py resolve_category` (:119-129): add keyword
   `use_synonyms: bool = True`. after the exact `subcat_to_cat` lookup misses
   (and only then, and never for fold buckets), look up
   `tax["synonyms"][p.lower()]` and resolve THAT leaf through `subcat_to_cat`
   → `(category, False)`. default True means audit (:239) and canonical (:252)
   pick the fallback up with zero call-site edits.
3. `classification.py _is_resolved` (:104-112): call
   `resolve_category(ptype, tax, use_synonyms=False)` — a synonym-resolvable
   product is QUEUEABLE, not resolved, until its metafield is persisted
   (mirrors the existing fold-bucket precedent: audit counts folds classified
   while the feature queues them, :107 docstring).
4. `classification.py resolve_leaf` (:70-88): no structural change — it calls
   resolve_category twice (raw, then normalized) and inherits the fallback;
   verify the normalized retry also hits synonyms ("Sporting Goods > Camping >
   Torch" → leaf "Torch" → synonym → Flashlights → Lighting). update ITS
   docstring and `_normalize_ptype`'s (:58-67) to name the ruled fallback and
   the order law.
5. re-run the suite. the live-taxonomy resolver tests (:75-87) must stay green
   untouched — the fallback fires only where resolution failed before.

**step 3 — data + live verify** (checkpoint 3). mine the real gap read-only:
`SELECT DISTINCT product_type FROM products` against data/demostore.db,
resolve each through `resolve_leaf`, list the unresolvables (the spec's count
was 17, catalog-workflows.md:158). draft a starter synonym map ONLY for the
ones with an honest, obvious leaf (torch-class certainty; anything debatable
is left out — silence over guesses). STAGE the taxonomy.json edit
(`classification.synonyms` + version bump note) — see the open question; do
not land it yourself. the rendered proof: with a seeded scratch db +
TestClient, the /catalog categories row (p205) counts the synonym-resolved
product in its queue and the batch preview renders it in plain words — the
queue/progress plumbing is already generic, no app.py change.

## escalation triggers

the RUNBOOK's six, plus:

- **the locked-taxonomy edit turns out to need more than a staged note** — if
  anything in the record says taxonomy.json edits are owner-keystroke-only,
  park the demostore data half as its own note and ship the mechanism on test
  fixtures (the check passes without live data).
- **audit health counts move in the suite** — if any audit/health pin breaks
  because synonyms changed a live-shape count, stop and check whether the pin
  was pinned to the live shape on purpose (the UI-truth lesson); re-pin only
  with the reason written.
- **the synonym map wants to become fuzzy matching** — any similarity scoring,
  stemming, or embedding idea is a NEW backlog item, never this one (pull
  rule 3; the refuse-to-guess invariant is a ruled design line).

## "done"

the RUNBOOK's five lines, with these specifics: (a) the verbatim check above,
proven at both levels — the resolver pin AND the queue pin, plus the rendered
categories row on a seeded scratch db; (c) no HARD cold-read is demanded by
the row (mechanism item; the words that reach a screen are the existing
generic surfaces) — but any NEW surface string still passes the plain-first
guard; (e) the proof line for the sync names the mined unresolved count and
how many the starter map resolves.

## risks (item-specific, found in the code)

- **the `_TAX` module cache** (classification.py:44-55): the store taxonomy is
  loaded once per process and cached globally. tests must pass their own tax
  fixture (the existing tests' pattern) or the cache poisons cross-test; and
  a staged taxonomy.json edit won't show in a running web process until
  restart — say so in the note, don't chase a phantom bug.
- **`_is_resolved` is the trap**: put synonyms in resolve_category without the
  `use_synonyms=False` escape and "Torch" counts as cleanly resolved →
  never queued → the check's second clause fails while the resolver pin
  passes. the queue pin exists precisely to catch this.
- **fold buckets must not hit synonyms**: resolve_category returns early for
  "… — Other" (:126-128) — keep the synonym lookup on the non-fold branch
  only, or "Xyz — Other" could resolve through a synonym and break :87.
- **canonical.py:252 is a silent consumer**: persisted metafield first, then
  resolve_category — with synonyms defaulting on, canonical's fallback
  category shifts for synonym-typed products. that is the intended agreement,
  but if a canonical test pins the old None, read it before re-pinning.
- **taxonomy.json is git-tracked live instance data** and LOCKED v1.2: commit
  by path, stage the edit, name it in the note for the owner's k. never
  `git add -A` (the WAL/git trap also applies to the read-only demostore.db
  connection — use `connect_readonly` audit.py:499, checkpoint no WAL).
- **plain words**: if any refusal/validation message can reach a screen via
  the /parts row or a 500, keep identifiers out of the sentence a person
  reads; the ValueError text is operator-log territory, but write it plainly
  anyway.
