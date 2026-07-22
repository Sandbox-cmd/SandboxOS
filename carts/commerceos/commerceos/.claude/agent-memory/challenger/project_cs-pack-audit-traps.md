---
name: cs-pack-audit-traps
description: Recurring correctness traps found auditing commerceos execution packs (CS0/CS1/CS2, 2026-07-22) — check these first on any future pack audit
metadata:
  type: project
---

Traps that produced real defects in the CS1/CS2 pack audit (base 888de9c):

- **call-vs-item conflation**: writes.execute is TWO client.graphql calls
  per item (write writes.py:228-231 + verify readback :234-235). Any
  barrier/counting harness gated on raw call count is off by 2x.
- **COMMERCEOS_DB override swallows per-store resolution**
  (stores.py:84-86): with the env pin set, EVERY store name resolves to
  the scratch db — a "db file missing" branch is unreachable in the
  standard rig; packs that pin that branch need a ruled rig mechanism.
- **land-guard allowlist law** (CS0 lint 1): allowlist entries must start
  with "you", so a machine-subject "landed …" string can never live in a
  FUSION_*_PLAIN set — placement (inline vs fusion set) decides pass/fail.
- **ledger status "executing" is neither pending nor approved nor done** —
  "no longer pending/approved" phrasing silently counts in-flight items.
- **_REPORTS is repo-global** (app.py:2187): tests inherit the real
  reports/health-latest.json unless monkeypatched — board/health renders
  are machine-dependent.

**Why:** each of these made a pack claim false or a pinned test unrunnable
as written, while every one of ~80 file:line citations was accurate — in
this repo the line numbers are reliable; the BEHAVIORAL claims are where
packs break.

**How to apply:** on any pack audit here, spend citation-checking time
proportionally — spot-check lines, but walk every claim about call
counts, env overrides, lint allowlists, and status state machines end to
end.
