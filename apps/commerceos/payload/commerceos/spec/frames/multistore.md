# frame — the multi-store shape

state: frame draft — 2026-07-18, for sitting E. ruled already (2026-07-18):
the function gets built now; CommerceOS is the system, each store is a
project that uses it. what remains is the shape.

today: one store (demostore) is hardwired — ten places in the code resolve
config by a literal `stores/demostore/` path. env overrides exist for the
policy table and the database. the boundary is real in spirit (all
per-store facts live in `stores/demostore/` config files), not in mechanism.

## shape A — registry only, one shared database

A store registry + config resolution per store, but every store's facts land
in the same database with a store column.

- cheapest to start; one query surface across stores.
- but: every table changes (a store column everywhere), every writer and
  guard must re-prove itself, provenance mixes, and the append-only ledger
  interleaves two businesses. blast radius is maximal.

## shape B — registry + config resolution + one database per store  ← recommended

`stores/registry.json` names the stores. One resolver
(`resolve(store, filename)`) replaces the ten literals; `COMMERCEOS_STORE`
picks the store, existing env overrides still win. Each store gets its own
database (`data/<store>.db`) and its own ledger.

- the single-writer guards already work per connection — they hold unchanged.
- schemas stay as they are; no store column anywhere; tests keep their shape.
- the web surface gains one thing: a store context (pick once, shown on the
  masthead). the rhythm arms per store (one launchd label each).
- cost: cross-store questions need two reads — acceptable; the owner is one
  person and the parts view can show both.

## shape C — full tenancy (one process, stores as rows everywhere)

What a SaaS would do. It buys nothing here — the operator is one person on
one machine — and it pays the same schema-change cost as shape A plus
runtime complexity.

## what each shape means, side by side

| | A: shared DB | B: DB per store | C: tenancy |
|---|---|---|---|
| schema change | every table | none | every table |
| single-writer guards | re-prove all | hold as-is | re-prove all |
| ledger honesty | interleaved | one per business | interleaved |
| test blast radius | maximal | the ten literals only | maximal |
| cross-store view | free | two reads | free |

## the recommendation

Shape B. It is the smallest true mechanism: the ten literals become one
resolver, the guards and schemas stand, and the scaffold store proves the
whole path end-to-end (config set → DB → tick → render) without touching
demostore's data. If a real cross-store need ever bites, a read-only lens
over both databases is a later, cheap addition.
