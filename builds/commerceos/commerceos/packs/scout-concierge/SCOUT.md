`git diff --quiet 3c506f9..HEAD -- spec/parts/concierge.md spec/build.md commerceos/catalog/verify_sources.py commerceos/catalog/canonical.py commerceos/catalog/workflows.py commerceos/web/app.py || echo "STALE — re-true before build (see RUNBOOK)"`

# scout — the concierge (G1 grounding corpus + G2 surface)

as-of: commit 3c506f9, suite 394 green.

mission of this scout: name what "verified claims at scale" — the park
condition on the concierge — concretely means, with a measurable
threshold the owner can k. the concierge is the one part that talks to
the public; its whole trust story is cite-or-decline over claims the
verification feature has actually flipped. today that count is zero.

## why it is parked

- backlog.md (wave 2): "concierge (G1 grounding corpus · G2 the surface)
  — parked until spec-verification (now building as V1/V2) scales real
  verified claims."
- spec/build.md:233 — S5 concierge: "after S2 earns it · cite-or-decline
  holds on a fit-critical test set"; :235-236 — "S5 earned. the Oct–Dec
  peak is the clock."

## seam map (verified 2026-07-19 against the repo)

- **the part spec exists**: spec/parts/concierge.md (draft v1, spec'd so
  the seam is designed, not discovered). the laws that bind any build:
  the published read-only corpus is the concierge's ONLY product
  knowledge (:20-27); conversation runs on a separate substrate — never
  the personal subscription pool, no shared key (:25-27); per-claim
  cite-or-decline, conflicts stated never resolved (:66-74); the seam
  crosses exactly one thing each way (:89-93); checks at :104-117
  including the no-brain-DB grep and the Arabic mirror of the test set;
  the api caveat at :130-135 (citations vs structured output — two call
  shapes, re-verify against the current api).
- **the claims source**: commerceos/catalog/verify_sources.py —
  `pick_pilot_set` :81, `judge` :212, `build_proposal` :245,
  `submit_pilot` :286, `execute_and_record` :317 (the approval return
  leg), `check_against_claims` :463.
- **the flip writer**: commerceos/catalog/canonical.py
  `record_verification` :143-165 — writes claim_verifications and flips
  the matching spec_claims row to verified=1 with source + verified_on;
  `revert_verification` :168 is the exact compensation.
- **the feature**: commerceos/catalog/workflows.py `VERIFICATION`
  :351-365 — fit-critical, always parks; `_verification_queue` :222
  reads the latest pilot findings file (reports/verify-pilot-*-findings.json,
  glob at :206); `verification_evidence` :326 renders quote + maker
  link. web return leg: commerceos/web/app.py:1210 (an approved
  spec-verification executes through verify_sources.execute_and_record).
- **the live baseline (the honest number)**: data/demostore.db carries
  a live catalog's spec_claims, a subset flagged fit_critical=1 — and every
  row reads verified=0; the claim_verifications table does not exist in
  the live database yet. one pilot findings file exists
  (reports/verify-pilot-2026-07-11-findings.json, 20 products). the
  verification MECHANISM is built and producer-passed (V2, suite pins in
  tests/test_verification_feature.py + tests/test_spec_verification_executor.py);
  no flip has landed live. "at scale" is currently zero of them.

## the ruling card — one k

**the question:** what count of verified claims unparks G1? pick the
unpark condition so "parked" stops meaning "forever".

- (a) **coverage threshold** — N% of the fit-critical claims
  verified, store-wide. clean number, but store-wide coverage is the
  slowest possible bar and the concierge doesn't need all of it to be
  safe.
- (b) **absolute count** — e.g. 200 verified claims wherever they fall.
  easy to hit, but scattered claims ground scattered answers; the
  surface would decline almost everything a real customer asks.
- (c) **category-complete + a running pipeline** — every fit-critical
  claim verified in ONE launch category, AND the verification feature
  running as an armed batch loop (not a hand pilot) so the corpus keeps
  growing after launch. the concierge launches scoped to that category
  and declines honestly outside it — which cite-or-decline already makes
  safe by construction (concierge.md behavior 1).

**recommendation:** (c), with the floor keyed to the live distribution
(read 2026-07-19, data/demostore.db opened read-only). fit-critical
claims per category: Packs & Bags 191 · Lighting 135 · Climb Hardware
134 · Knives & Tools 133 — then a cliff: Camp Furniture 29, Coolers &
Storage 28, Apparel 27, everything else 22 or fewer. a flat ~100 floor
silently narrows the launch-category pick to those top four, so say it
out loud: the floor is category-complete WITH a stated minimum — the
launch category carries at least 100 fit-critical claims (today that
means one of the four above) and EVERY fit-critical claim in it is
verified. measurable both ways: `SELECT COUNT(*) FROM spec_claims
WHERE fit_critical=1 AND verified=1` within the category equals that
category's fit-critical count (and so lands ≥ 130 for any of the
four), and the verification feature's progress card shows a nonzero
weekly flip rate. the real risk is not thin coverage (declines are
safe) — it is a corpus that stops growing the day the surface ships.

**what the k unlocks:** G1 (the corpus builder + publisher) becomes a
draftable full pack immediately; G2 (the storefront surface) queues
behind it and behind the second owner gate below.

## what the full pack needs

1. **G1**: the snapshot format + publisher — verified spec_claims rows
   (with source + verified_on), SKU-keyed datasheet index, store
   policies; published as a read-only bundle, snapshot age recorded
   (concierge.md :20-27, behavior 5). prior art for read-only opens:
   commerceos/economics/reconcile.py `connect_ro` :63.
2. **the second owner gate, named**: inference provider + GCC data
   residency is OPEN [owner] (concierge.md :141-144) — a new metered
   billing surface only the owner arms. G2 cannot be packed until that
   ruling lands; G1 can.
3. the fit-critical test set (concierge.md checks :104-110), mirrored in
   Arabic, as the earning check — this is S5's check in build.md:233.
4. the two-call-shapes caveat (:130-135) re-verified against the current
   api before G2's design freezes.
5. the isolation greps as tests: no brain-DB path, no subscription
   credential, no PII field in concierge storage (:113-117).

## open questions

- the launch category itself is the owner's pick at unpark time (his
  read on Oct–Dec demand); the scout deliberately does not propose one.
