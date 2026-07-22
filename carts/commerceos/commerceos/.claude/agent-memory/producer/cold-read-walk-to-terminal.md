---
name: cold-read-walk-to-terminal
description: Cold-read technique — walk every flow to its terminal PAGE, including form POST responses; forms posting to /api/* JSON endpoints are a recurring dead-end class here
metadata:
  type: feedback
---

Walk every operator flow one click PAST the last rendered surface — the terminal page of a form POST is part of the flow.

**Why:** on the SP1 suppliers cold read (2026-07-19), round 1 caught the raw-JSON error path and the raw-JSON approvals card, but stopped at the card — and missed that the approve button itself (a plain HTML form posting to `/api/approvals/{id}`) lands the browser on the endpoint's raw JSON return, on the happy path, every time. The web app is server-rendered with NO JS islands (static/ holds only CSS), so any `<form>` whose action is an `/api/...` route that returns a dict is a guaranteed raw-JSON landing.

**How to apply:** in every commerceos cold read, for each `<form>` on the surface, resolve its action's return type in web/app.py — a JSONResponse or bare dict reached by a browser form is a dead-end finding regardless of how clean the page renders. Also check executor-time refusals (spine/writes.py returns `ok: False` AFTER approval) and ask where that refusal renders for the operator.
