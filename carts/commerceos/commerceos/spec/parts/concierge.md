# part: the concierge

serves: C1, C2 as amplifier (spec/jtbd.md) — phase 2 (S5), earned by catalog
truth.
state: draft v1 — 2026-07-11. OPEN items marked. NOT in V1 builds; spec'd now
so the seam is designed, not discovered.

## purpose

the one part that talks to the public. a customer asks a spec question or
describes a mission ("3-day desert camp in December"); the concierge answers
from sourced catalog truth or says plainly that it cannot. its job is to be
the most trustworthy voice in a spec-dense category, not the most persuasive:
a wrong temp rating is a safety claim, so refuse-to-guess is a duty of care,
not a style choice. it amplifies C1 (the full kit, nothing missing) and C2
(specs you can trust) only after the catalog loop has made the specs true —
catalog truth first, conversation second. it never runs its own checkout.

## owns

- the grounding corpus build: a published, read-only bundle — spec claims
  with provenance per claim, supplier datasheets keyed by SKU, store policies
  (returns, delivery). built from what the catalog loop landed, published as
  a snapshot. the corpus is the only product knowledge the concierge has.
- conversation handling on its own substrate: the service that takes customer
  turns, retrieves, answers, streams. separate production inference — never
  the personal subscription pool, no shared process ancestor, no shared key.
- the kit composition logic: mission in, itemized kit out, each line
  justified, fit-critical claims cited per line.

## exposes

- the storefront chat surface: a Shopify theme app extension (product pages
  plus a kit-builder page) talking to the concierge service through a Shopify
  app proxy, so requests stay first-party. inference happens server-side; the
  browser sees streamed text and kit data, never a key.
- structured signals back to the brain, as records not prose: spec gaps found
  (product, field, how often asked) · questions declined or unanswered · kit
  patterns (missions described, kits accepted) · hand-off requests. the brain
  treats these as untrusted input from public conversations and routes them
  as findings (part 2).

## consumes

- the published corpus from the catalog loop — never live DB access. no path
  to the brain's SQLite, its ledger, or Shopify admin.
- Shopify storefront APIs for live price and availability — commerce facts
  stay live from the rail; spec truth comes only from the corpus.
- Shopify cart APIs for hand-off: the kit becomes lines in the normal cart;
  checkout stays Shopify's.
- the gate (part 3) for consequential requests: order changes, returns,
  refunds, anything touching PII. the concierge holds no order-write scope
  and no PII-read scope. PII stays in Shopify.

## mechanism vs config

- engine (store #2 unchanged): grounded answering with per-claim
  cite-or-decline · claim classification (fit-critical vs general) · kit
  composition · corpus snapshot reader · signal emitter · gated hand-off
  protocol · the two call shapes (see v0 salvage).
- instance (this store's file): the corpus content itself · which spec
  classes count fit-critical here (shared with the gate's taxonomy) · tone
  rules · language mix (EN + AR, native script, text-first) · kit templates
  per activity and season · where the surface sits on the theme.

## behavior

1. spec question → classify each claim the answer would make → retrieve from
   the published corpus. a fit-critical claim (temp rating, load, waterproof
   class, certification) is stated only with its citation attached; no source
   in the corpus → decline that claim in plain words and answer the rest.
   per claim, not per conversation — one reply can carry a cited spec and a
   declined one. conflicting sources are stated as a conflict, never silently
   resolved. off-domain questions get an honest "outside what I can verify."
2. mission described → kit assembled from templates plus corpus: every item
   carries why it is in and what conditions it holds for, cited per line →
   hand-off into the normal Shopify cart. never its own checkout, never a
   payment surface.
3. consequential ask (order status, return, refund, address change) → the
   concierge says plainly it is handing this to the team, collects the least
   identifiers needed, and emits a gated request. the gate approves per
   policy, the brain executes, the answer returns to the thread.
4. disclosure: the first message says it is AI, and says why that honesty
   matters — it only states specs it can verify.
5. corpus refresh: the catalog loop publishes a new snapshot each landed
   catalog batch; the concierge always answers from the latest published
   snapshot and records its age. staleness is the operator's flag to chase,
   not the customer's problem.
6. the seam: outward crosses one thing — the published read-only corpus.
   inward crosses one thing — structured signals (gaps, declines, kit
   patterns, gated requests). never crosses, either direction: brain DB
   access, any key or credential, subscription-pool traffic, raw PII, the
   ledger.

## renders

self-reports into the operator's web surface (part 7), like every part:
questions answered vs declined, with declined claims named — declines become
the catalog loop's work queue · spec gaps by product and field · kit
conversions (kits composed → carts created) · hand-off queue depth and age ·
corpus snapshot age. decline-rate is an output to read, not a number to
optimize; the target is zero fabricated fit-critical claims.

## checks

- a fit-critical test set: a question whose spec is absent from the corpus
  yields a decline of that claim, not an answer. a mixed question (one
  sourced spec, one missing) yields a cited answer and a decline in the same
  reply. (this is S5's earning check in build.md.)
- the same test set in Arabic yields the same cite-or-decline outcomes.
- a kit hand-off lands in a real cart on the dev store — verify rendered:
  open the cart, count the lines.
- no code path from the concierge substrate reads the brain's DB or keys:
  its tree and its runtime env carry no brain DB path, no subscription
  credential, no gate-capability secret — a grep proves the absence.
- the concierge's stored records carry session references only — a schema
  check shows no PII field.

## v0 salvage

from inherited/specs/concierge.md — mined, not ported blind:

- surface architecture: theme app extension + app proxy + server-side
  inference + streaming. carried as-is.
- corpus design: provenance-bearing spec claims plus a SKU-keyed datasheet
  index, keyword retrieval first — no vector store until a recall failure
  earns one. carried, with one change: the concierge reads the published
  snapshot, not live metafields.
- bilingual approach: EN + AR in native script for customers, text-first, no
  voice in V1. carried.
- the API caveat, on the record: citations and structured outputs were
  mutually exclusive in the API (400 if combined). the kit-builder therefore
  needs two call shapes — cited prose for spec claims, a structured pass for
  the kit skeleton with citations re-attached per line. verify against the
  current API when built; the constraint may have moved.
- model tiering, simplified for V1: one model, single tier, prompt caching on
  the corpus prefix from day one. the fast-path/escalation router waits for a
  real cost number, not a guess.

## open

- OPEN [owner]: inference provider + GCC data residency — where customer
  conversations may be processed; legal read pending. the production
  inference account is a new metered billing surface, armed only by the owner.
- OPEN: WhatsApp as a later channel — GCC-native, demand unvalidated;
  nothing in V1 may assume it.
- OPEN: AR dialect handling — standard Arabic first; dialect tuning only on
  evidence from real conversations.
- OPEN: a read-only, no-PII order-status path — the full gate may be too
  slow for "where's my order"; decide when hand-off latency is measured.
