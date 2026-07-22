# CW8w — context (verified against the repo at 3c506f9)

## seam map (every file the build touches, refs read fresh)

| file | what | refs |
|---|---|---|
| commerceos/web/app.py | `api_resolve` — the system's only approve verb (POST /api/approvals/{record_id}) | def :1168 · guard + body parse :1176-1187 · `answer_error` dual-shape helper :1189-1193 · decision/confirm walls :1195-1199 · `gate.resolve` + the "localhost" by-stamp :1201-1202 · the approved block :1206-1219 (local imports :1207-1208 · verify_sources branch :1213-1215 · **the bare `writes.execute` fallback :1217 — the hole** · except wrapper :1218-1219) · flash logic :1222-1233 (`outcome.get("ok")` :1227) · JSON answer :1234 |
| commerceos/web/app.py | `approvals_view` — the decisions page the parked card and flash render on | :1237-1313 (flash card :1265-1270 · per-item card + approve form :1301-1311) |
| commerceos/web/app.py | the product drill — where "the product's state" is seen | route :2723 · `state_of` read :2753 · stage row via `state_label` :2759 · history timeline :2793-2800 |
| commerceos/web/app.py | STATE_LABELS ("delisted" → "removed from store") | :209-216, `state_label` :218 |
| commerceos/web/app.py | `catalog_rule` — the flag-review surface staging the SAME method (keep/remove/archive → mutate_product_state, consequential) | :2870-2899 (`_RULE_STATE` :2867) — CW8w's branch completes this path's loop too |
| commerceos/web/app.py | `catalog_run` — proof the consequential lane parks per item (hold is reversible-only) | :2902-2933 (reversible hold :2916-2929 · consequential park :2932) |
| commerceos/catalog/delist.py | the seam this pack wires in: `execute_and_record` | def :95 · METHOD `"mutate_product_state"` :41 · verified-rendered gate :133-135 · **return shape (no top-level `ok`) :134-142** · state-agnostic law :106-109 |
| commerceos/catalog/lifecycle.py | the sole writer the seam calls | `transition` :170 (raises on unplaced product :190-193) · `set_initial` :135 · one-writer header law :24-31 |
| commerceos/spine/writes.py | the one write door + the state executor | `execute` :61 (dispatch to `_mutate_product_state` :104) · `_mutate_product_state` :290, returns `{"ok", "verified_rendered", "status"}` :304 |
| tests/test_delist_web.py | NEW — the pins (below) | — |

not touched but read: commerceos/catalog/verify_sources.py `execute_and_record`
:317 (returns top-level `ok` :333-338 — why the existing branch's flash works).

## prior art (copy these shapes)

- **the web rig**: tests/test_workflow_runs_web.py:21-31 — `COMMERCEOS_DB`
  monkeypatch.setenv to a tmp path, `connect` + `ensure_schema` +
  `ledger.ensure_schema`, `TestClient(app)`. the ShopifyClient monkeypatch:
  :122-125 (`monkeypatch.setattr(writes, "ShopifyClient", lambda: store)`).
- **the seam's own tests**: tests/test_catalog_delist.py —
  `FakeClient` :31-53 (scripted productUpdate + `query productStatus`
  readback; `readback_status=` forces a store that lies), `_submit_delist`
  :93-101 (the exact gate.submit shape for a parked delist), the
  approve→execute→record test :148-183, the unverified-records-nothing test
  :186-201, the relist leg :204-226.
- **dual browser/JSON answer assertions**: tests/test_supplier_form.py
  exercises the same endpoint's form leg (SP1) if a redirect-shape reference
  is needed.

## binding laws (this item)

- one write door: the branch calls `delist.execute_and_record`, which itself
  runs `writes.execute` — never a second door (delist.py:128).
- lifecycle state moves ONLY on `verified_rendered` — the seam already
  enforces it (delist.py:133-135); the web layer must not re-implement or
  bypass that gate.
- catalog-lifecycle is the sole writer of both lifecycle tables
  (lifecycle.py:24-31, AGENTS.md "one writer per table-set").
- the gate: no approve verb anywhere agent-facing; the person's confirm field
  stays required (app.py:1198-1199).
- plain words on every surface string; verify rendered, never files-exist.

## cold-start pointers

- env + covenant: packs/RUNBOOK.md env block (`uv run pytest -q`, ~90s;
  uvicorn on 8848; call-time store resolution — never an import-time path).
- required reading: AGENTS.md · .claude/agent-memory/producer/MEMORY.md ·
  the plain-first guard test tests/test_catalog_dashboard.py:240
  (`test_no_jargon_or_raw_codes_reach_the_screen`).

## test plan (the pins, named)

new file `tests/test_delist_web.py`, rig copied per prior art:

1. `test_web_approve_of_a_parked_delist_flips_store_and_records_the_move` —
   seed product + `set_initial(ACTIVE)`, park via `_submit_delist`, POST the
   browser form (`decision=approved&confirm=true`) → 303 to
   `/approvals?flash=landed...`; FakeClient status now DRAFT; `state_of` reads
   `delisted`; exactly one new history row carrying the record id as
   `ledger_id`, `by` from the record's agent; ledger record `executed`.
2. `test_json_approve_answers_with_a_truthful_outcome` — same park, JSON body
   → answer keeps `{"record", "outcome"}`; `outcome["ok"]` and
   `outcome["verified_rendered"]` true; `recorded` true rides in the outcome.
3. `test_unverified_store_readback_records_no_move_and_says_so` —
   `FakeClient(status="ACTIVE", readback_status="ACTIVE")`; state stays
   `active`, history stays 1 row, and the form flash reads refused in plain
   words (never "landed").
4. `test_the_drill_page_shows_the_move` — after pin 1, GET
   `/catalog/products/{pid}` shows "removed from store" and the history
   timeline row (the check's "seen" leg, pinned against the rendered surface —
   the house's twice-paid lesson says pin the live shape, not a minted one).

optional (worth one pin if time allows): the flag-review "keep" ruling
(`/catalog/rule/{pid}` with ruling=keep on a flagged product) approved via the
web now records flagged → active through the same branch.

capture script shape (for the step-3 walk): TestClient or live uvicorn against
the seeded scratch db; write the three HTML captures (decisions-before,
decisions-after-flash, product-drill) to a scratch dir named in the make note.

## open questions

- the [owner] 7c ruling — what "by" should carry on web-made moves — is open
  and RIDING; this pack ships with the existing convention ("localhost"
  stamped, rendered as "you, at this desk"). backlog.md's cut section folds C4
  (approver identity) into CW8w only as far as the stamp that already exists
  at app.py:1201; no new identity work belongs here.
