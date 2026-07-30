# commerceos — the shared copy

the operator brain for commerce. it runs a store through a gated agent
fleet: facts land, watching notices, the gate decides, the ledger
remembers, the web surface shows everything. nothing stays a blackbox.

this is the whole build — mechanism, specs, execution packs, and the
test suite. what it does not carry is anyone's store: no catalog, no
credentials, no database, no numbers. those are yours to bring.

## start

    uv sync
    uv run pytest -q

you should see **503 passed, 51 skipped**. the skips are the point — each
one names a file you have not written yet, and wakes up on its own once
you do. read them:

    uv run pytest -q -rs

then bring the surface up:

    uv run uvicorn commerceos.web.app:app --reload

open http://127.0.0.1:8000. with no store it renders honestly — "nothing
staged", "this part isn't set up yet", "no money data yet". an empty
system that says it is empty is working correctly.

## what you owe it

a store lives in `stores/<name>/`. `stores/demostore/` is a placeholder
with the gate config, the rhythm (every job disabled), and an empty
watch-list. rename it, or register your own in `stores/registry.json`.

four files decide how much of the system can speak:

| file | what it unlocks |
| --- | --- |
| `connector.json` | the live store. fill the domain and client id; the secret goes in your Keychain, never in the file |
| `taxonomy.json` | classification, the catalog audit, product resolution |
| `collections.json` | merchandising and the smart-collection flow |
| `watch-list.json` | the watching engine — what counts as drift |

shapes for each are in `spec/parts/`. the engine knows nothing about any
vertical; your taxonomy is where the domain lives.

## the shape of it

- `commerceos/` — mechanism. store-agnostic by law, and there is a test
  that greps for a leaked store name to keep it that way.
- `spec/` — the contract. jobs, build, experience, and one spec per part.
  a change that contradicts a spec updates the spec first.
- `packs/` — execution packs. each one is a frozen research brief that
  lets a model build a slice cold, without re-deriving the context.
  `packs/RUNBOOK.md` explains the loop.
- `backlog.md` — the work, with pull rules. every row carries a job and a
  runnable check.
- `tests/` — 554 checks. `tests/conftest.py` holds the skip rules and is
  the only file written for this shared copy; delete it once your store
  is real and every check should bite.

## the conventions that differ from defaults

- one SQLite database, one writer per table-set.
- every fact carries source + fetched_at. no fact, no number.
- no approve verb on any agent-facing API. writes need a one-use handle.
- PII stays in the platform; local rows carry references only.
- credentials live in the macOS Keychain, referenced by service name.

## running it in your own workshop

this arrived as a cart. `sandbox load commerceos` drops it into the
project you are working on; start a channel for it and the record follows
the same loop it came from — you build, notes stage, your keystroke lands.

the specs are the contract. read `spec/build.md` first.
