`git diff --quiet 3c506f9..HEAD -- commerceos/stores.py spec/parts/multi-store.md spec/frames/multistore.md spec/frames/brand.md spec/build.md commerceos/spine/seeds.py stores/registry.json || echo "STALE — re-true before build (see RUNBOOK)"`

# scout — wave-2 thin cluster: cross-store lens · D6 customer carry-over · store rails F2–F6

as-of: commit 3c506f9, suite 394 green.

mission of this scout: hold the seam pointers and gate conditions for
three deliberately-waiting items in one thin map, and put the F1 card on
the table plainly — F1 is the master gate to the Oct–Dec peak, and
everything in the third section waits behind it.

## 1. cross-store read lens

**the deliberate wait**: spec/parts/multi-store.md:140-142 — OPEN
[design]: "a later read-only view over both databases, built only when
a real need bites (the frame's 'two reads' cost is acceptable until
then)." spec/frames/multistore.md:52-58 says the same from the shape-B
ruling: "if a real cross-store need ever bites, a read-only lens over
both databases is a later, cheap addition."

**seam pointers (verified)**: commerceos/stores.py — `load_registry`
:38, `active_store` :65, `resolve` :78, `register_store` :101; the
registry today holds demostore + scaffold (stores/registry.json, M4's
five ceremony stamps). the masthead names the store every surface
speaks for (commerceos/web/teletext.py `masthead` :88 — behavior 4, one
site). prior art for read-only opens:
commerceos/economics/reconcile.py `connect_ro` :63. store isolation is
pinned both directions by tests/test_store_isolation.py — a lens must
never weaken those pins (read-only connections only, no cross-write
path).

**gate condition**: a SECOND real store exists (post-F1 rails) AND the
owner asks a cross-store question more than once. until then the cost
of "two reads" is nothing — the operator is one person.

**what a full pack needs**: the real need named (which question, which
surface), read-only opens of each data/<name>.db, and a decision on
where it renders (a store-picker view vs a lens page) — an experience
question for experience.md before code.

## 2. D6 — customer carry-over

**the ruling that stands**: ruled in, fresh-start — customers carry;
PII stays in Shopify (AGENTS.md conventions; backlog wave-2 row). the
code says it at the seam: commerceos/spine/seeds.py:1-8 — "customers
carry only when the real store exists (PII goes to Shopify, never
here)."

**seam pointers (verified)**: spine/seeds.py `seed_suppliers_from_fta`
:18 is the carry-over prior art SHAPE (land the rows with source +
fetched_at, provenance rendered in plain words on the surface — SP2's
proof). the customer move itself is Shopify-side (an import into the
NEW store via Shopify's own tools/api); local rows carry references
only — no PII column ever lands in a commerceos database, and the
concierge part repeats the same wall (spec/parts/concierge.md :52-53).

**gate condition**: the real store exists — which means F1 → the rails
below. there is nothing to build before that day.

**what a full pack needs**: the export/import act (Shopify-side, the
owner's hands on the real accounts), a reference-only local shape if
any local row is wanted at all (it may need none), and a schema-check
pin proving no PII field — same law as concierge.md's checks.

## 3. store rails F2–F6 — all name-gated on F1

**the rows**: backlog wave-2 — F2 registrar/handles · F3 entity · F4
theme · F5 payments+BNPL · F6 supplier reconnects. spec/build.md:232
carries them as slice S4: "theme, payments, delivery, domain —
name-gated [OWNER]". spec/frames/brand.md:55-56: "the decision is F1;
store rails F2–F6 open behind it."

**the honest shape of these items**: F2–F5 are calendar work in the
owner's hands (registrar, legal entity, theme setup, payment/BNPL
onboarding), not code. the one code-adjacent item is F6: supplier
reconnects bring the real contracts, and take rates land only then
(spine/seeds.py:1-8 — "take rates stay NULL — they arrive with real
contracts (F6), never from history"); F6 also unblocks the
supplier-and-vendor onboarder agent (see packs/scout-roster).

## the F1 ruling card — one k

**the question:** F1 — the name — is the master gate to the Oct–Dec
peak (build.md:235-236: "S4 on the name · S5 earned. the Oct–Dec peak
is the clock."). it is PARKED AGAIN since 2026-07-18: B3 closed without
a pick — five boards built, the whole slate rejected, "the name simply
isn't found yet" (backlog, B3 row + the owner-gated list). the material
stands ready: reports/brand/research-2026-07.md, directions.md,
moodboards/. what does the owner want to do with the clock?

- (a) **run brand round two now** — fresh directions from the standing
  research; the B3 lesson rides: his ear rules every dialect question
  in-session, never an external gate.
- (b) **set the latest-responsible decision date** — back the date off
  from October: F2–F5 are lead-time items (registrar, entity, theme,
  payments/BNPL onboarding are weeks, not days), so the name must land
  well before the peak the rails are for. round two runs whenever he
  likes, but the date is on the calendar either way.
- (c) **keep it parked with no date** — honest about today, but the
  peak arrives whether or not the name does, and the rails silently
  miss it.

**recommendation:** (b), with (a) inside it — and here is the
arithmetic, so the k lands a date, not an intention. target: rails
ready by 1 Oct 2026 (build.md:235-236 — the Oct–Dec peak is the
clock). the lead-time assumptions, each an ESTIMATE TO CONFIRM, not a
fact:

- F2 registrar/handles: days — runs parallel, never the critical path.
- F3 legal entity: 2–6 weeks (license + bank account; payments KYB
  needs the entity, so F3 → F5 runs sequential).
- F4 theme: 2–4 weeks — parallel with F5 once the store shell exists.
- F5 payments + BNPL onboarding: 4–8 weeks (gateway KYB + BNPL
  merchant review) — the long pole.

critical path: name → F3 → F5 = 6–14 weeks. backed off 1 Oct, the name
must land between 25 Jun (worst case — already behind us) and 20 Aug
(best case). **the proposed date: the name lands by 1 Aug 2026** —
that leaves ~9 weeks of runway, which only holds if the lead times
confirm at the low-middle of the estimates. so the first calendar row
the k creates is confirming the real numbers (registrar, license
office, gateway, BNPL); if the confirmed path runs longer than 9
weeks, the date moves earlier the day that is known. the name itself
still resolves at a moodboard, as ruled, whenever round two finds one
he actually likes — the k here rules the date, not the name.

**what the k unlocks:** a landed date (1 Aug 2026, or the k's
amendment of it) makes F2–F6 schedulable backwards from the peak,
gives round two a deadline, and turns three "wave 2 / later"
paragraphs into calendar rows. without it, nothing in this scout can
become a full pack.

## open questions

- the lens's "real need" and D6's import shape are unanswerable until a
  second store and a real store exist, respectively — deliberately left
  open; the gate conditions above say exactly when to ask again.
