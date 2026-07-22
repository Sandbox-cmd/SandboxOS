git diff --quiet 3c506f9..HEAD -- commerceos/web/app.py commerceos/catalog/delist.py commerceos/catalog/lifecycle.py commerceos/spine/writes.py tests/test_catalog_delist.py tests/test_workflow_runs_web.py || echo "STALE — re-true before build (see RUNBOOK)"

# CW8w — wire the delist return-leg into the web approve path

## mission

when the owner approves a parked delist on the decisions page, the store flip
happens but the product's lifecycle move is never recorded — the web approve
path routes every non-verification method to the bare write door and skips
`delist.execute_and_record`, the seam built exactly for this (today NO code
path calls it). one `elif` branch in the resolve endpoint closes the hole, so
an approved state change lands on the store AND on the product's history in
the same act.

as-of: commit 3c506f9 · suite 394 green

## the backlog check (verbatim, backlog.md:154)

approve a parked delist via the web → store status flips to DRAFT
(verify-rendered) + lifecycle reads delisted with a history row. seen on
decisions → the product's state

## model

sonnet — one branch in one endpoint plus pins; every seam already exists and
is tested in isolation (delist.py has its own suite, the web rig is proven).

## boundaries

- **stores/dbs**: scratch dbs only (`COMMERCEOS_DB` → tmp path) + a fake
  client monkeypatched over `writes.ShopifyClient`. `data/demostore.db` is the
  real catalog — never written, never opened for the live verify (seed a
  scratch db instead).
- **gate lane**: consequential, per-item. delist proposals park on /approvals
  and are ruled one by one — WF-approve's hold/batch machinery does NOT carry
  this method today (app.py:2916-2933: only `declared_type == "reversible"`
  fronts hold; the consequential branch at :2932 parks per item, as before).
  no new approve verb anywhere; POST /api/approvals/{id} stays the only door.
- **writer-class**: catalog-lifecycle (lifecycle.py) stays the SOLE writer of
  `product_lifecycle` + `lifecycle_history` (lifecycle.py:24-31, schema.py:170-180).
  the web layer only calls the feature's door (`delist.execute_and_record`).

## step plan (S-size: 2 checkpoints)

**step 1 — write the failing tests** (new file `tests/test_delist_web.py`).
copy the rig from tests/test_workflow_runs_web.py:21-31 (COMMERCEOS_DB env pin
+ TestClient) and the FakeClient from tests/test_catalog_delist.py:31-53
(scripted productUpdate + status readback, with a forced-disagree mode).
monkeypatch `writes.ShopifyClient` the way test_workflow_runs_web.py:125 does.
the pins are named in context.md ("test plan"). run them; watch them fail on
the missing branch (state stays `active`, history stays 1 row).

**step 2 — the branch.** in `api_resolve` (commerceos/web/app.py:1168), inside
the approved block: import `delist` beside the existing local imports
(:1207-1208), and between the verify_sources branch (:1214-1215) and the bare
`writes.execute` fallback (:1217) add:

    elif record and record["proposal"]["method"] == delist.METHOD:
        res = delist.execute_and_record(conn, record_id)
        outcome = {**res["outcome"], "recorded": res["recorded"],
                   "transition": res["transition"], "state": res["state"]}

the normalized shape is RULED here so no builder has to guess: the inner
store receipt (`res["outcome"]`, which carries top-level `ok` +
`verified_rendered` from writes.execute) IS the outcome, with the lifecycle
facts riding alongside. and the lifecycle leg gets its OWN try inside this
branch: wrap only the `execute_and_record` call; on `LifecycleError`, if the
store write already verified, answer honestly ("the change landed on the
store; recording its history failed — <why>") — never let the outer except
at :1218-1219 turn a verified store write into "nothing was written". the
outer except stays as-is for every other branch.

`delist.METHOD` is `"mutate_product_state"` (delist.py:41), so the branch also
carries relist, archive, and the flag-review "keep/remove/archive" rulings
staged by `catalog_rule` (app.py:2870-2899) — the seam is state-agnostic by
design (delist.py:106-109). normalize the answer so the flash line at :1227
(`outcome.get("ok")`) and the JSON answer at :1234 stay truthful: surface
`ok` + `verified_rendered` from the inner receipt at top level, let
`recorded` / `transition` ride alongside.

**checkpoint 1 — suite green**: `uv run pytest -q` ≥ 394 + the new pins, zero
skips; review the diff against the RUNBOOK laws checklist; any file outside
the seam map is an automatic stop.

**step 3 — live verify-render.** seed a scratch db (products + variants +
`lifecycle.set_initial` + a parked delist via `gate.submit` — the helper shape
at tests/test_catalog_delist.py:93-101), boot
`COMMERCEOS_DB=<scratch> uv run uvicorn commerceos.web.app:app --port 8848`,
walk: /approvals shows the parked card → approve (confirm checked) → the flash
reads landed in plain words → /catalog/products/{pid} shows stage
"removed from store" and the history timeline's new who/when/why row. take
HTML captures of decisions (before/after) and the drill page — the check says
"seen on", so the seen half gets receipts. note: the live-store leg of the
fake-free walk cannot run (no store write outside FakeClient is allowed by the
boundary); the rendered-surface halves are what this checkpoint proves.

**checkpoint 2 — rendered proof + captures** reviewed against the check line.

## escalation triggers

the RUNBOOK's six, plus:

- the honest answer shape seems to want a change to `writes.execute` or
  `verify_sources.execute_and_record` return shapes — stop; both have other
  consumers (runs.py:137, tests). normalize inside the branch only.
- a real product missing its lifecycle row makes `transition` raise
  (lifecycle.py:190-193) and the fix wants a backfill — that is CL1c's item;
  never a side-quest here (pull rule 3).
- any impulse to add an approve affordance on another surface — the gate law.

## "done"

the RUNBOOK's five lines, plus this item's specifics: the backlog check ran
verbatim through TestClient AND was seen on the live scratch surface
(decisions flash + the drill page's stage row + history row); suite ≥ 394 +
new pins, zero skips; captures kept with the make note. the row does not mark
a HARD producer cold-read (that wording is F4b's) — the captures stand as the
"seen on" receipt.

## risks (item-specific)

- **the shape trap (the sharpest one)**: `delist.execute_and_record` returns
  `{"outcome", "recorded", "transition", "product_id", "state"}` with NO
  top-level `"ok"` (delist.py:134-142) — but the flash decision at app.py:1227
  reads `outcome.get("ok")` and the JSON caller at :1234 gets `outcome` raw.
  unnormalized, every successful web delist flashes "refused: the write did
  not land — nothing was written": a lie on the decisive click. the existing
  branches work because writes.execute and verify_sources both return
  top-level `ok` (writes.py:304, verify_sources.py:333-338).
- **the post-write lie**: the except wrapper at app.py:1218-1219 answers
  "refused ... nothing was written" for ANY exception — but a
  `LifecycleError` raised AFTER `writes.execute` verified the store flip
  (e.g. an illegal transition, or a product never placed) means the store DID
  change. catch lifecycle failures inside the branch and answer honestly
  (the store changed; the history row did not land), never "nothing changed".
- **plain-language guard**: any new flash words walk the guard
  (tests/test_catalog_dashboard.py:240, `test_no_jargon_or_raw_codes_reach_the_screen`).
  no "lifecycle", no "delist", no method name on screen — the house words are
  in STATE_LABELS (app.py:209-216: delisted → "removed from store").
- **testclient identity**: `by` is stamped "localhost" for
  127.0.0.1/::1/testclient (app.py:1201); `who_plain` (app.py:2936-2944)
  renders it "you, at this desk" — never put "localhost" itself on a screen.
  the [owner] 7c ruling on what "by" should carry is riding, not blocking.
- **append-only ledger**: nothing here updates ledger rows outside gate/writes'
  own doors; `ledger.fill_outcome` inside writes.execute is the only outcome
  writer (writes.py:110-115).
- **dual answer**: the endpoint answers a browser form with a 303 redirect and
  a JSON caller with JSON (the SP1 pattern, app.py:1172-1193) — keep BOTH legs
  working; the JSON shape stays `{"record", "outcome"}`.
