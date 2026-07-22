# part: the web surface

serves: O4; the condition every part ships under (spec/jtbd.md)
state: draft v1 — 2026-07-11; open items ruled 2026-07-18. none remain.

## purpose

the brain's face. every part shows itself here or does not ship — if it
runs, it renders (O4). the surfaces are specified in spec/experience.md;
this part builds them. it never decides: viewing is free, acting goes only
through the gate's APIs and recorded config edits. home:
the cartridge root — FastAPI + a small frontend build, SQLite
reads, SSE, localhost/LAN (ruled 2026-07-11). one more ship condition:
the producer cold-reads every user-facing surface against
spec/experience.md before it ships (format amendment, RULED 2026-07-18
[owner]).

## owns — the part registry (self-report contract), the six surface routes, auth/session, push notification wiring, the store context

- **the part registry** — two SQLite tables; the no-blackbox contract
  every other part's `## renders` section fills. one row plus config
  seeds puts a part on the surface — no UI code per part.

  `parts` — one row per part, the part its only writer; upserted via a
  shared helper on startup and after every run:

      part         unique name — "watching", "catalog-loop", ...
      is           one plain sentence: what I am, which job rows I serve
      state        starting | running | idle | failed — paused/halted
                   overlay from the gate's flags, never self-set
      functions    names it acts under — autonomy, thresholds, and track
                   record join from the gate by these names
      last_run     { started, finished, ok, summary, ledger_ids }
      next_run     timestamp, cadence string, or "on demand"
      reported_at  freshness — a stale row renders stale, never vanishes

  `part_config` — part · key · value · kind · safe_edit (0|1) · note —
  seeded insert-if-missing on first start, read by the part every run.

  the honest split: a part reports what it is and does; the ledger grades
  it — track record (proposals, approved, rejected, reversed, time since
  last reversal) reads from the gate's ledger query by part and function.

- **part-owned satellite tables** — a part may own a small table of its
  own rows (e.g. catalog-workflows owns `workflow_features`, one row per
  feature) that a dedicated workspace route renders as a set. same
  no-blackbox contract as the registry — one writer per table — but many
  rows to one surface instead of one row per part. the `/catalog`
  dashboard renders its feature cards this way; the generic `/parts`
  registry stays one-row-per-part. this is a named pattern, not a
  bespoke exception.

- **the six routes** (spec/experience.md): `/` the brief · `/approvals` ·
  `/record` · `/parts` (+ `/parts/{name}`) · `/economics` · `/findings`.
- **auth and session** — localhost trusted by binding; any other origin
  carries a device-paired bearer token issued once on localhost.
  tailscale is reach, not auth. per-money-move confirm on top.
- **push wiring** — ntfy for consequential items, notify-only: the item
  and a deep link, never the decision (aligned with gate-and-record.md).
- **the store context** — the operator picks a store once; the masthead
  shows it on every surface; switching is explicit, never inferred. the
  store list and the active store come from the multi-store part's
  registry (spec/parts/multi-store.md; RULED 2026-07-18 [owner]).

## exposes — the registry contract other parts implement; the surfaces to the operator (desktop + phone browser)

- the registry contract above — parts view, brief lines, and staleness
  warnings render from the same rows for any part, present or future.
- `/api/*` reads (JSON) and one SSE stream (`/api/events`): queue,
  registry, and run-state changes.
- the act endpoints — the only writes here, each recorded: resolve an
  approval (the system's only approve verb, per gate-and-record.md) ·
  halt/resume · safe config edits.

## consumes — ledger + queue from the gate, facts summaries from the data spine, findings/metrics from watching, economics views, health from the catalog loop

- gate + record: ledger queries (record surface, drill-downs, track
  records) · pending queue feed · resolve, halt, threshold APIs.
- data spine: facts summaries behind brief lines; every drill to source.
- watching: the brief's flag feed, the findings stream, metric values.
- economics: contribution and P&L views, every number carrying source ids.
- catalog loop: health through its registry row; per-product ledger drill.

## mechanism vs config — registry-driven rendering (generic) vs per-store branding/labels (minimal)

- mechanism (store #2 unchanged): the registry contract and renderers, the
  six routes, SSE, auth/pairing, gate client, push wiring, kill-switch.
- config (the store's file, minimal): store name and labels · currency and
  locale · ntfy topic/server · tailscale hostname — a label, never a fork.

## behavior — numbered flows

1. **registration on part startup** — upsert the `parts` row, seed
   `part_config`. the part is on `/parts` at the next render and on the
   SSE stream at its next report — zero UI changes. no row, no ship.
2. **the brief assembles** — four reads: ledger since last visit · pending
   queue · open findings both directions · period money line vs baseline.
   every line carries the row ids it summarizes and links to the route
   filtered to them; no ids, no line. full picture in minutes, cold (O1).
3. **approval round-trip** — a pending item arrives over SSE → the card:
   intent · why now · impact · the exact change · evidence → the operator
   confirms (a second explicit gesture — a pocket-tap cannot move money)
   → the surface calls the gate's resolve → decision recorded, one-use
   handle minted, executor runs, outcome lands → SSE flips the card.
   stale money-moves render expired on the gate's clock, never execute late.
4. **phone path** — a consequential item fires ntfy: intent + impact + a
   deep link to `/approvals/{id}`; the phone opens it over tailscale with
   its paired token — same card, same confirm, same resolve.
5. **kill-switch** — in the header everywhere: global halt, per-function
   pause. the surface calls the halt API; the flag lives with the gate;
   parts check it before consequential work and runs refuse to spawn
   under it. halt and clear are ledger entries; unknown reads halted.
6. **config edit** — only `safe_edit = 1` rows are editable; the ledger
   entry (part, key, old → new, by, when) is written before the value
   changes, and the part reads it next run. `safe_edit = 0` rows are
   read-only here — thresholds move only through the gate's recorded path.

## renders — this part renders everything; its own self-report

the surface fills its own row through the same helper, no special path:
uptime · connected SSE clients · paired devices · last push attempt and
result · last error. a blackbox surface would break the rule it enforces.

## checks — runnable

1. register a throwaway part via the helper; `/api/parts` and the
   rendered parts view both show it, zero UI changes; remove it.
2. seed a pending consequential action; resolve it over HTTP with a
   paired token and the confirm field — the exact request a phone sends;
   the ledger holds decision and outcome, and SSE carried the flip.
3. fetch `/api/brief`; every line carries source ids; follow one id to
   the fact rows behind the number.
4. start a dummy part honoring the halt flag; call halt; the loop stops
   within its check interval; the halt and the clear are on the ledger.
5. edit a `safe_edit = 0` row: refused. edit a `safe_edit = 1` row: the
   ledger entry exists and the next read returns the new value.
6. a non-localhost request without the paired token is refused.

## v0 salvage — from inherited/specs/cockpit.md

carried: device-paired token + per-money-move confirm, localhost by
binding · SSE for queue and state · park-don't-block round-trip with the
executor as single chokepoint and expiry · trust-ratchet-beside-control
· kill-switch: global + per-function, fail-safe, journaled.

changed: stdlib http.server + vanilla no-build SPA → FastAPI + a small
frontend build (ruled 2026-07-11). fixed views growing one per function
→ registry-driven rendering: a new part costs a row, not a view. the
terminal-HUD quick-path died with the old kernel (ntfy carries alerts).
the CLI-approve fallback is dropped — one approve verb, one place; if
the surface is down, the gate keeps parking and push keeps firing.

views mapped: activity → the brief + parts view · ledger → the record ·
KPIs → economics · catalog → its registry row + product drill · trust →
inside `/parts/{name}` · approvals stays.

## open — all four ruled 2026-07-18

- RULED 2026-07-18 [owner]: frontend build — server-rendered + islands.
  registry-driven rendering leaned server-rendered; confirmed.
- RULED 2026-07-18 [owner]: pairing — QR pairing minting a long-lived
  revocable token, reach over tailscale. revoking a lost phone's token
  is the recorded config act; no re-pair cadence beyond that.
- RULED 2026-07-18 [owner]: SSE, not websocket — acting stays a POST;
  revisit only if the phone path shows reconnect pain.
- RULED 2026-07-18 [owner]: ntfy self-hosted, notify-only — the
  sovereignty call carried from cockpit.md, now confirmed.
