# the pack rack — one row per pack

_as of: 2026-07-22 · base commit 888de9c · suite 508. a pack is usable only when
its freshness check (line 1 of its PACK.md) passes — pull rule 1 extends to packs.
backlog-sync sweeps this table and flips fresh/stale. a pack older than two landed
builds re-trues regardless of seam diff._

## the collaboration-surface run (SF1 converged 2026-07-22 → CS0/CS1/CS2)

| pack | item | size | model | status | collides on |
|---|---|---|---|---|---|
| packs/CS0 | fusion register foundation (triage + fusion.py + fusion.css + the three lints) | M | sonnet | EXECUTED 2026-07-22 — dry-run 5/5, three gates, one pack defect (singular agreement) ruled at review (commit 0ea5b63, suite 527); contract AMENDED in CS1 round two (stopped clause drops "overnight") | — consumed |
| packs/CS1 | the wall (quiet home: sentence triage + tickets + calm lines) | M | opus | EXECUTED 2026-07-22 — dry-run clean, THREE producer rounds (round 1: scope lie + clocks + twin tickets + dead doors; round 2: four new lies beside the repairs — decisions-not-members fold, formless line, no self-anchors, the overnight amendment), round 3 SHIP-CLEAR; suite 539 zero skips. riding minor: together-clause scope when a routine batch waits at another desk | — consumed |
| packs/CS2 | the board (two zones + receipt-in-place + stopped honesty) | M | opus | EXECUTED 2026-07-22 — re-trued past CS1's churn, dry-run clean, TWO producer rounds on sonnet-5 whole-surface reads (round one: 2 blockers incl. the raw-JSON receipts; round two: the landed-leak, B1's twin, caught only by the whole-surface law); final read SHIP-CLEAR; suite 554 zero skips. the walk caught a real bug the pins missed (stopped-run double-representation) and one incident (the real db briefly opened read-write by a stale server — rows verified intact, on the record) | — consumed |

CS pull order: CS0 → CS1 → CS2, strictly serial (CS1/CS2 share the app.py
seam AND whichever lands first owns the _ALLOWED_STATIC fusion.css entry +
the page shell — the second re-trues on the first's diff, expected).

## full packs (pull-ready — every one passed the graded cold-read gate 2026-07-19:
## a Sonnet read only the pack + repo and named its first edits, check commands,
## the trap, and the probe answer correctly against a hidden key)

| pack | item | size | model | status | collides on |
|---|---|---|---|---|---|
| packs/CW8w | delist web return-leg | S | sonnet | EXECUTED 2026-07-19 — the pilot, ship-clean (commit 3ab25d1, suite 398) | — consumed |
| packs/F4b | listing-text feature | M | opus | EXECUTED 2026-07-19 — ship-clear through the loop (commit a113f47, suite 416; producer round one BLOCKED, repaired; two pack defects fed back) | — consumed |
| packs/CL1c | sync → lifecycle auto-register | S | sonnet | EXECUTED 2026-07-19 — parallel run (4edb26e, suite 435) | — consumed |
| packs/CW3b | classification synonym fallback | M | sonnet | EXECUTED 2026-07-19 — parallel run (7c80d84; map honestly empty, proposal in reports/) | — consumed |
| packs/UI-polish | board density toggle + audit cadence (buildable half) | S | sonnet | EXECUTED 2026-07-19 — parallel run, self-re-trued, ship-clear (53192cf, suite 437) | — consumed |
| packs/WEB1 | phone pairing (QR + code + revoke) | M | opus | CODE-COMPLETE 2026-07-19, ship-clear surfaces (a76d1b8, suite 449; two producer rounds) — checkpoint 3 = the OWNER'S PHONE WALK, instructions in the make note | — awaiting the phone |

## scout packs (gated / wave-2 — seam map + ruling card + what a full pack
## needs; all six challenged adversarially 2026-07-19: one blocker + two majors
## + four minors found and repaired, every citation re-verified at HEAD)

| pack | covers | gate |
|---|---|---|
| packs/scout-collections | CW4 collection-create executor + CW5 merchandising | [owner] placement + card metric rulings |
| packs/scout-media | media-attach executor + the images agent (CW9 hybrid) | the executor is the missing piece |
| packs/scout-localization | Arabic localization + descriptions/copy | source + human-confirm ruling |
| packs/scout-concierge | G1 grounding corpus + G2 surface | waits on verified claims at scale |
| packs/scout-roster | supplier clerk · bookkeeper · market watcher · discoverer · onboarder | design-before-pull per roster.md |
| packs/scout-wave2 | cross-store lens · D6 customer carry-over · store rails F2–F6 | rails are name-gated (F1) |

## pull order (P0 ruling — collision-aware)

1. ~~CW8w~~ — DONE 2026-07-19, the pilot: a sonnet builder shipped it from the
   pack alone (two checkpoint gates, three honest inferences named, zero files
   outside the seam). the pack system is proven.
2. **F4b** — the wave-1 exit item; heaviest app.py churn, so it runs ALONE among
   app.py packs. re-true first (bounded: the only seam diff is the new delist
   branch in api_resolve).
3. **CL1c ∥ CW3b** — no app.py collision; safe to run in parallel with each other
   or with an app.py pack.
4. **UI-polish** — after F4b lands (both touch the board surface).
5. **WEB1** — when the phone is in hand; re-true first (app.py will have moved).

collision law: **never two app.py packs in flight at once** (app.py is 3,100+ lines
and four of six packs touch it). CL1c and CW3b are the only fully parallel-safe
pair. WIP cap 3 holds across the program.

## the riding rulings (fold into ruling cards)

mid-run halt boundary · approver identity (the 7c) · CW4 placement · CW5 card
metric · UI-polish P-page numbers + money-view labels ([owner] halves).
