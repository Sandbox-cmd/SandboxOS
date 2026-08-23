---
name: cold-read-tense-and-units
description: Cold-read checks — verb tense must match row status; a header count and its list must share a unit; the arm surface must see its own staged work
metadata:
  type: feedback
---

Three finding classes that all appeared in the WF-approve cold read (2026-07-19):

1. **Tense vs status:** a kind label rendered in past tense ("barcode fixed") over a row whose status is pending is a dishonest claim — check every event/line label against its status field. "Done means verified rendered live."
2. **Count-unit drift:** a header count and the rows under it must share a unit. "waits on you (2)" over a 1-item list = counting proposals while listing batches. Cross-page count checks must also confirm the UNIT, not just the number.
3. **Arm-surface blindness:** the page that stages work must acknowledge work it already staged. Check: capture the arm/control page WHILE the staged thing exists — if it still offers to start and says "nothing yet", and re-arming is a silent no-op redirect, that's a dead click. Corollary (CW5, 2026-07-19): a page with TWO arm controls (e.g. batch + nav-placement) must be walked per control — the guard added to the primary does not cover the second, and an unguarded second control both re-offers blindly AND parks duplicates (gate.submit has no pending-dup check; dedupe lives at the route/render layer). Also: a headline must not overclaim the freshness its own fine print disclaims ("coverage now" over "as of the last sync").
4. **Issue-time rows wearing redemption-time verbs** (WEB1, 2026-07-19): a credential/pairing roster rendered "paired <time>" for rows INSERTed at mint time, before any phone ever claimed — no claimed marker existed in the schema at all. Check the writer's INSERT site, not just the template: if a lifecycle has issue→redeem steps but the table has one timestamp, the roster's verb is lying about one of them. On security rosters (what holds access) this class is automatic MAJOR. Validated repair shape (accepted on the re-walk): add the redemption timestamp as an HONESTY fact keyed by the render ("code shown … — not scanned yet" vs "paired …"), while auth stays keyed on possession — do not demand the auth gate consume the new column when possession already implies it; the roster tells the truth, the gate keeps one rule.
5. **Repairs strand their pointers:** a fix that removes or replaces a control must sweep every sentence that points at it. On the re-walk, the arm button correctly stepped aside for the waiting batch — but a neighboring panel still said "Start one above". After any control-level repair, grep the fresh capture for imperative sentences ("start/press/open ... above/below/here") and re-resolve each one's target.

**Why:** WF-approve walk — loop was structurally true (arm→preview→one approve→verify receipts) yet shipped BLOCKED on exactly these sentence-level honesty gaps plus a raw sqlite error the plain-language guard missed because it was exception text interpolated at render time.

**How to apply:** every commerceos cold read: grep captures for past-tense verbs adjacent to "pending/staged/held"; recount every "(N)" header against its visible rows; take at least one capture of each control page while its own output is in flight. Related: [[cold-read-walk-to-terminal]], [[rewalk-grep-live-for-mapped-output]].
