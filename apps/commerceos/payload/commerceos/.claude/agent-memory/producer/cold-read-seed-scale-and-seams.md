---
name: cold-read-seed-scale-and-seams
description: Cold-read checks — judge caps/truncation at the REAL store's scale (tiny seeds hide default-path lies); check every string-concatenation seam in captions for a missing separator
metadata:
  type: feedback
---

Two finding classes from the UI-polish walk (2026-07-19, table density + p202 cadence):

1. **Seed-scale blindness:** a capture from a tiny seed store (3 products) cannot exercise any cap or truncation path — but a live catalog of thousands of products crosses those caps on the very FIRST real render. A caption like "N products, one row each" over a 100-row cap was invisible in the capture and would be the default experience live. Check: grep the rendering code for every `_CAP`/`[:n]` slice near the new surface and verify the adjacent caption/count uses the SHOWN length, not the matched length — or says "first X of N".
2. **Concatenation seams:** captions built by string concatenation (base + optional suffix line) must be checked at the JOIN — a suffix starting with a bare space fused two sentences into a false conditional ("when its front is built a fresh reading is set for every day"). Check: read the fused output in the capture, not the pieces in code; every optional fragment must open with its own separator (". ", " · ").

**Why:** both were MAJORs on an otherwise clean change; the seed capture was green everywhere the defect lived. Related: [[cold-read-tense-and-units]] (count-unit drift is the same family as #1), [[rewalk-grep-live-for-mapped-output]] (live data's dominant shape, not the test fixture's, is what renders).

**How to apply:** every commerceos cold read — ask what the LIVE store's row count is for each new list/table and code-walk the cap path if the capture can't reach it; grep new caption code for f-string/`+` joins with optional fragments and read the assembled sentence aloud.
