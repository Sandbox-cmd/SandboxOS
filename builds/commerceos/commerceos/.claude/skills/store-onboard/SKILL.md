---
name: store-onboard
description: Walk a new store into commerceos — config set, registry row, fresh database, first tick, first render, each step stamped in the registry. Use when the owner says onboard a store, add a store, new store, or store #N. The ceremony is the product (spec/parts/multi-store.md behavior 2); launching store #2 is config, not a second build.
---

# store-onboard — the onboarding ceremony

five steps, no code changes. every step stamps the store's registry row
(`python -m commerceos.stores stamp <name> <step>`) so `stores list`
always tells the truth about how far a store has walked. run from the
cartridge root. `<name>` is lowercase, one word.

## 1 — config (`stamp <name> config`)

create `stores/<name>/` with the minimal set, then any store-specific
files the store's platform needs:

- `rhythm.json` — copy the shape of an existing store's, `"store": "<name>"`,
  every job `"enabled": false` (the law: nothing arms itself; jobs enable
  at the owner's arm keystroke).
- `policy-table.json` — the gate's method classes for this store. start
  from the shipped baseline (conservative: consequential parks) and the
  existing store's table as a shape reference.
- `watch-list.json` — may start `{"metrics": []}`; watching then
  evaluates nothing and says so honestly.
- `connector.json`, `taxonomy.json`, `audit-config.json`,
  `take-rates.json`, `economics.json` — as the store's platform and books
  demand; a file may start minimal but must be valid JSON. the resolver
  never guesses: a consumer that needs a missing file will fail loudly
  and name it.

## 2 — register (`stamp <name> register`)

    uv run python -m commerceos.stores register <name> "<Label>"

never the default — store #1 keeps that. the row appears in
`stores/registry.json`; this module and this ceremony are its only
writers.

## 3 — migrate (`stamp <name> migrate`)

a fresh `data/<name>.db` with every table-set's migrations run:

    COMMERCEOS_STORE=<name> uv run python -c "
    from commerceos.db import connect
    from commerceos.spine.schema import ensure_schema as spine
    from commerceos.gate.ledger import ensure_schema as gate
    from commerceos.catalog.canonical import ensure_schema as canonical
    from commerceos.watching.schema import ensure_schema as watching
    c = connect(); spine(c); gate(c); canonical(c); watching(c)"

## 4 — first tick (`stamp <name> first_tick`)

    COMMERCEOS_STORE=<name> uv run python -m commerceos.rhythm.runner tick

with every job disabled this runs nothing and says so — that IS the
passing shape: the rhythm reads this store's config, touches this
store's database, and leaves every other store alone.

## 5 — first render (`stamp <name> first_render`)

    COMMERCEOS_STORE=<name> uv run uvicorn commerceos.web.app:app --port 8890

open `/` — the masthead speaks this store's name, the counts are this
store's (zeros are honest zeros, never another store's numbers). stop
the server after the walk.

## after the ceremony — arming is the owner's, always

    COMMERCEOS_STORE=<name> uv run python -m commerceos.rhythm.arm

is a dry run that prints the per-store label and plist. `--yes` is the
owner's keystroke, never the operator's. arming any store disarms the
legacy single-store label first if one is found, and says so — record
that line. checks that must hold after arming: the new store's label is
`com.commerceos.<name>.rhythm`, and every other store's schedule is
untouched.
