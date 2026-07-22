# part: multi-store

serves: O6 (spec/jtbd.md) — "launching store #2 is config, not a second
build"
state: draft v1 — 2026-07-18. OPEN items marked.

## purpose

make the store a project that uses commerceos, not the thing commerceos
is. the owner's framing (RULED 2026-07-18 [owner]): "commerceOS is the
system and we ship it as a cartridge, the store becomes the project that
uses it and ill have more projects later." today the boundary is real in
spirit only — ten places in the code resolve config through a literal
`stores/demostore/` path (spec/frames/multistore.md). this part is shape
B made mechanism (RULED 2026-07-18 [owner]): one registry names the
stores, one resolver replaces the ten literals, and each store keeps its
own database and its own append-only ledger. schemas and single-writer
guards stand unchanged.

## owns — the store registry and the resolver

- **stores/registry.json** — the file that names the stores: name,
  label, default flag. this part is its sole writer; everything else
  reads store facts only through the resolver. a row may carry a `db`
  filename for a database that predates per-store naming (M1
  discovery, 2026-07-19): demostore's row says `"db": "commerceos.db"`
  until M3 renames the live file to `data/demostore.db` and drops the
  field — without the bridge, M2 would resolve demostore to a database
  that does not exist yet and boot store #1 empty.
- **commerceos/stores.py** — the resolver module, `resolve(store,
  filename)`. it replaces the ten `stores/demostore/` path literals in
  gate/policy.py · watching/engine.py · spine/connector_shopify.py ·
  spine/shopify_client.py · catalog/classification.py ·
  catalog/canonical.py · catalog/audit.py · economics/reconcile.py ·
  rhythm/runner.py · rhythm/arm.py — AND the seven `data/commerceos.db`
  database-path sites (challenge 2026-07-18): db.py · catalog/canonical.py
  · catalog/audit.py · catalog/workflows.py · catalog/verify_sources.py ·
  catalog/quality.py · economics/reconcile.py (its import-time
  DEFAULT_PATH included). the resolver is CALL-TIME — db.py's import-time
  env read is part of what M2 replaces, or `COMMERCEOS_STORE` silently
  loses to a frozen module constant.
- **the onboarding ceremony** (behavior 2) — the one path a new store
  enters by. the operator runs it, as the store-onboard skill
  (spec/frames/roster.md); its step stamps live in registry.json with
  this part as their sole writer — no unowned table.

## exposes — resolved paths to every part; the store list and active store

- `resolve(store, filename)` — the only way mechanism code turns a
  store name into a config path (`stores/<store>/<filename>`) or that
  store's database (`data/<store>.db`).
- the active store name — read by the web surface for its masthead
  store context, and by the rhythm when it arms per store.
- the registry list — read by the web surface's parts view and by the
  onboarding ceremony.

## consumes — env vars, the registry file, each store's config directory

- `COMMERCEOS_STORE` — picks the store for a process.
- the existing env overrides — `COMMERCEOS_POLICY_TABLE`,
  `COMMERCEOS_DB` — which still win over anything the resolver returns.
- `stores/<name>/` — that store's config set (policy-table.json ·
  connector.json · taxonomy.json · audit-config.json · take-rates.json
  · watch-list.json · economics.json · rhythm.json).

## mechanism vs config — resolver + registry are mechanism; stores/<name>/ is the store

- mechanism (every store uses unchanged): stores.py, the registry
  file's shape, the resolve order, the onboarding ceremony.
- config + data (that store's own): everything under `stores/<name>/`,
  and that store's `data/<name>.db` — one database, one append-only
  ledger, per store. no store column anywhere; the single-writer guards
  hold as they are, per connection.

## behavior — numbered flows

1. **resolve order** — an explicit env override (`COMMERCEOS_DB`,
   `COMMERCEOS_POLICY_TABLE`) wins first; else `COMMERCEOS_STORE` names
   the store; else the registry's default store. the resolver never
   guesses: an unknown store name fails loudly, before any read.
2. **store onboarding (the ceremony)** — create `stores/<name>/` with
   the minimal config set → register the name in registry.json →
   migrate a fresh `data/<name>.db` → first tick → first web render.
   five steps, no code changes — that is O6's claim, and the checks
   prove it on a scaffold store.
3. **per-store isolation** — every fact, ledger entry, and registry row
   a store produces lands in that store's own database. two businesses
   never share a ledger; provenance never mixes. the jsonl audit mirror
   is per store too — `data/<store>.ledger.jsonl` — or the mirrors
   interleave what the databases keep apart (challenge 2026-07-18).
4. **the web store context** — the operator picks a store once; the
   masthead shows it everywhere; switching is explicit, never inferred
   from a route or a cookie's guess (RULED 2026-07-18 [owner]).
5. **the rhythm arms per store** — one launchd label per store, each
   armed process pinned to its store by `COMMERCEOS_STORE`. migrating to
   per-store labels DISARMS the legacy `com.commerceos.rhythm` label
   first, as a recorded act — an orphaned plist must not keep ticking
   the default config against whatever the default then resolves to.

## renders — store on the masthead; per-store parts view; onboarding state

- the active store's name on the masthead of every surface.
- the parts view shows which store each part's row speaks for.
- onboarding state per store: which ceremony steps have run, which
  config files exist, whether the first tick and first render landed.

## checks — runnable

- grep-guard: `grep -rn --include="*.py" demostore commerceos/` finds
  nothing — the name of store #1 has no business in mechanism code,
  comments included (and stale .pyc binaries stay out of the verdict).
- scaffold onboarding end-to-end: run the ceremony for
  `stores/scaffold/` (minimal config set) — config → DB → tick → web
  render, with zero demostore leakage into the scaffold's database or
  its rendered pages.
- two stores booted side by side: separate `data/<store>.db` files AND
  separate `data/<store>.ledger.jsonl` mirrors, single-writer guards
  holding in both, a write in one never visible in the other — in the
  database or in the mirror.
- demostore's schedule untouched: after the scaffold store arms, the
  demostore rhythm's jobs still run on their own label and their own
  config.

## v0 salvage — the env-override seam, honored

the env overrides already in db.py (`COMMERCEOS_DB`) and gate/policy.py
(`COMMERCEOS_POLICY_TABLE`, read through `table_path()`) are the seam
to honor, not replace — the resolver sits behind them and an explicit
override still wins, so existing tests and scripts keep working. the
migration checklist is the ten config-path literals PLUS the seven
database-path sites (both listed under owns; challenge 2026-07-18);
the `Path(__file__).resolve().parents[2] / "stores" / ...` pattern
becomes one call into stores.py. one migration step nobody may skip:
demostore's live `data/commerceos.db` moves to `data/demostore.db` —
WAL, SHM, and the jsonl mirror included — before any two-store boot,
or store #1's facts sit stranded in a file no resolver names.

## open — OPEN questions

- OPEN [design]: cross-store read lens — proposed: a later read-only
  view over both databases, built only when a real need bites (the
  frame's "two reads" cost is acceptable until then).
- RESOLVED by the run (2026-07-19): both, each in its lane — the live
  ceremony onboarded stores/scaffold/ into the repo (its five stamps in
  registry.json are the receipt; its database stays untracked like every
  *.db), and the tests re-run the ceremony's shape in tmp roots
  (tests/test_store_onboard.py) so the mechanism can't rot behind the
  checked-in copy.
