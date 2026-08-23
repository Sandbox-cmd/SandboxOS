# CS0 — context (the seam map, verified at 888de9c)

## required reading, in order

1. spec/parts/collab-surface.md — the ruled direction this foundation
   serves; the seven carried laws; the lint suite's origin.
2. reports/collab-surface/fusion.html — the ruled comp; fusion.css
   transcribes its values (the <style> block is the design).
3. packs/RUNBOOK.md — the execution contract you are riding.
4. tests/test_voice_register.py — the lint pattern to copy (roster +
   convention guard + named-exception discipline).

## the seam map (citations verified)

- gate/ledger.py:342-347 `pending_queue` — LIVE pending rows, oldest
  first; :350-355 `lapsed_queue` — lapsed surfaced separately, never as
  live waits. triage's input is pending_queue-shaped rows.
- gate/ledger.py:410-414 `_record` — the row dict shape: json fields
  impact/provenance/proposal/gate/outcome decoded; scalar columns ride
  as-is (id, ts, agent, action_type, status, expires_at, ...).
- gate/policy.py:35-39 — REVERSIBLE="reversible" ·
  CONSEQUENTIAL="consequential" · FIT_CRITICAL="fit_critical" · ORDER/
  RANK. triage groups on the row's action_type against these values
  (import nothing from policy — string-compare; triage stays pure).
- web/app.py:336-341 GATE_CLASS_PLAIN — the existing plain words for
  gate classes; fusion ticket meta lines may reuse this VOCABULARY but
  CS0 defines its own FUSION_*_PLAIN sets (fusion.py must not import
  app.py — that would drag fastapi into pure modules and create the
  collision CS0 exists to avoid).
- web/app.py:13 `from html import escape as html_escape` and :856,942
  usage — the escaping convention fusion.py copies (import html;
  html.escape at every interpolation site).
- tests/test_voice_register.py:29-51 the hand-enumerated roster ·
  :61-68 the convention guard (regex over module source for named sets)
  · :22 the named-exception allowlist discipline.

## prior art to copy

- lint shape: tests/test_voice_register.py (whole file, 92 lines).
- pure-function test shape: tests/test_gate.py feeds literal dicts —
  same style for test_triage.py.
- render-string assertion style: tests/test_seo_feature_web.py greps
  rendered HTML for exact strings (copy the assertion style, not the
  TestClient rig — CS0 renders by calling fusion.page directly, no app,
  no client, no db).

## binding laws

- the seven carried laws, spec/parts/collab-surface.md ("the laws
  carried") — CS0 implements 3 (ages via aged), 5 (one focus — the
  sentence), 7 (first person plain) at the string level.
- plain first: every string a stranger reads on first read; lowercase
  chrome except sentence-case for the triage sentence itself (it is
  prose, not chrome — it capitalizes as English).
- the record's escape law: every interpolated value through html.escape
  (regression precedent: commit 1f7936e escaped record-born strings
  after live ink crashed a page).
- stage never land: you stage nothing anyway (done contract) — the
  orchestrator stages the make note; the owner lands.

## cold-start env

    cd the cartridge root
    uv run pytest -q          # expect 508 passed, zero skips, ~90s
    # no db, no env pins needed for CS0's tests — everything is pure

## the test plan (pins NAMED — write these, watch them fail, make green)

test_triage.py:
- test_nothing_needs_you — [] → "Nothing needs you."
- test_one_thing — one reversible row → "One thing needs you." and it
  sits in routine.
- test_two_things_one_group — two consequential rows → "Two things
  need you." eyes_first has both, routine empty, no second sentence.
- test_heavy_day_triage — 3 consequential + 8 reversible → "Eleven
  things need you. Three deserve your eyes. Eight are routine and can
  go together." group order and membership pinned.
- test_stopped_appends — 2 reversible + 1 stopped → sentence ends
  " One job stopped." (amended from "stopped overnight" in CS1's
  producer round two); stopped list carries the row.
- test_thirteen_uses_digits — 13 mixed → sentence starts "13 things
  need you."
- test_order_preserved — rows keep ledger order within each group.
- test_unknown_action_type_is_eyes_first — an unrecognized
  action_type never lands in the batchable routine group (fail safe,
  same instinct as policy.py's unknown-method fail-high).

test_sf1_lints.py: the four tests per the pack's ruled contracts.

test_fusion_render.py:
- test_calm_day_fixture — 2 waits: sentence present exactly once,
  both tickets with amber edge class, doors line, aged("78.5",
  "last night") renders "78.5 as of last night".
- test_heavy_day_fixture — 11 waits + 1 stopped: triage sentence
  matches triage().sentence verbatim; one batch-shaped routine group
  label present; stopped ticket carries the stopped edge class.
- test_escape_proven — a ticket title "<b>sneaky</b>" appears only
  escaped in the HTML.
- test_edge_enum_loud — ticket(edge="sparkly") raises ValueError.
