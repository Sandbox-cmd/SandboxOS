# commerceos

the operator brain for commerce — an app within SandboxOS. it runs stores
(the reborn outdoor store is product #1) through a gated agent fleet:
facts land, watching notices, the gate decides, the ledger remembers,
the web surface shows everything. nothing stays a blackbox.

## run · test · build

    uv run pytest -q            # the floor — every part's checks
    uv run uvicorn commerceos.web.app:app --reload   # the web surface (C1+)

## the specs are the contract

jobs, build, experience, and one spec per part live HERE, in the
cartridge: `spec/` (jtbd.md, build.md, experience.md, parts/*.md). a
change that contradicts a spec updates the spec first. the backlog with
pull rules: `backlog.md` at this root. the channel
(~/Sandbox/channels/commerceos) keeps the record: CHANNEL.md, CANON.md,
inherited/.

## conventions that differ from defaults

- one SQLite database, one writer per table-set: facts (spine) · canonical
  product record (catalog) · ledger + events (gate) · registry (each part
  its row via the web helper).
- every fact carries source + fetched_at. no fact, no number.
- no approve verb on any agent-facing API. writes need a one-use handle.
- PII stays in Shopify; local rows carry references only.
- credentials live in the macOS Keychain, referenced by service name.

## settled decisions

decisions live on the workshop record (channel: commerceos — `sandbox
recall QUERY --channel commerceos`). the three that bite most:

- commission marketplace: every order splits take + vendor payable at
  landing; returns unwind both sides.
- re-spec clean: the tombstoned v0 is read-only reference — mine patterns,
  never port blind.
- FastAPI + small frontend; SQLite; local-first; phone reach via tailscale.

## gotchas

- the dev store (your-store.myshopify.com) is the proving
  fixture; its catalog was pushed 2026-07-01 at health 66/100, images ~0.5%.
- verify rendered, never files-exist: a push is done when the live surface
  shows it.
