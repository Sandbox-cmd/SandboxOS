# the pack runbook — the one execution contract every pack rides

a pack is a frozen thinking session: the research, seams, risks, and checks for ONE
backlog item, written so a cold session can build it without asking questions. packs
are derived, expiring artifacts — the specs in `spec/` are the contract; when a pack
and a spec disagree, the spec wins and the pack is stale.

## the cold-start ceremony (every execution, both paths)

1. **freshness first.** run line 1 of the PACK.md (the seam-diff command). if it
   says STALE: stop, re-true before building — re-run the command, run
   `uv run pytest -q` and compare the count to the pack's as-of, re-read only the
   seam lines that diffed, update the pack's citations, restamp as-of. never build
   on a stale map.
2. **read context.md fully**, then the required reading it names (AGENTS.md, the
   producer's memory, the plain-first guard test). these carry the laws you cannot
   infer from the diff you're about to write.
3. **build to the checkpoints** in the step plan. at each checkpoint, stop and
   review (orchestrated: the orchestrator reviews; standalone: you review against
   the laws checklist, honestly, before continuing).
4. **run the checks** exactly as written. read the output; "the command ran" is not
   "the check passed".
5. **stage, never land.** `sandbox note "make: commerceos: <id> …"` stages; the
   owner's keypress at a real terminal lands. nothing you do is durable without his
   k, and that is the design, not a limitation.

## the two paths

- **standalone**: `cd the cartridge root && claude --model <rec>`,
  then: "execute packs/<id> per packs/RUNBOOK.md". the pack must be enough; if you
  find yourself guessing, that is a pack defect — record it in the note.
- **orchestrated (default)**: the orchestrator (top-tier model) spawns you with the
  pack, reviews your diff at each checkpoint, runs the producer/challenger/checker
  gates, and stages the notes. same ceremony, second pair of eyes.
  producer cold reads run WHOLE-SURFACE every round (the CS1 lesson:
  repairs mint new lies beside the fixed strings) on sonnet 5 with the
  1m context window (owner-ruled 2026-07-22); the orchestrator's own
  firsthand capture/diff review stays the top-tier backstop.

## checkpoints

M-size items get three; S-size items drop the first.

1. **tests written and failing + seam confirmed** — the failing tests name the
   behavior; every file you plan to touch is in the pack's seam map.
2. **suite green** — review the diff against the laws checklist below. touching any
   file OUTSIDE the seam map is an automatic stop (escalate, don't proceed).
3. **live verify-render + producer captures** — the built thing proven on a real
   rendered surface, captures taken for the cold read where the item is [product].

## the laws checklist (reviewed at every checkpoint)

- **one write door**: every store write goes through `writes.execute` and a
  consumed one-use handle. no second door, ever.
- **the gate**: agents stage, a person lands. no approve verb on any agent-facing
  API. reversible batches HOLD for the glance-approve (WF-approve); consequential
  and fit-critical park per item.
- **append-only ledger**: never UPDATE ledger rows; render-time maps translate old
  ink to today's words.
- **spec-first**: a discovery that contradicts a spec updates the spec (staged)
  before the code.
- **plain words**: no code identifier or insider term reaches a screen — the guard
  test enforces it; write surface strings to pass it, and escape record-born ink
  before markup.
- **verify rendered, never files-exist**: done means the live surface read it back.
- **writer-class**: an agent writes its own field-class and nobody else's (the
  manifests in `.claude/agents/` name each).

## boundaries (defaults; each pack narrows them)

- `data/<store>.db` + `data/<store>.ledger.jsonl` are LIVE DATA. builds
  prove against scratch databases (tests) and the dev store fixture — never arm
  rhythm, never write the live store, unless the pack explicitly says otherwise.
- **the git/WAL trap**: live data files are git-tracked. commit code + tests + spec
  by path — NEVER `git add -A`. checkpoint WAL (`PRAGMA wal_checkpoint`) before any
  database file operation. data churn belongs to close-out, named in the commit.

## the six escalation triggers (stop and escalate — orchestrated: call the
## orchestrator; standalone: stage a note naming the block and end the session)

1. a discovered spec contradiction — propose the spec edit first.
2. any write beyond the pack's declared store/lane boundary.
3. the suite count DROPS or unrelated tests break.
4. the check as written cannot run (missing dependency, missing hardware).
5. a discovery that wants to become work — it becomes a new backlog item, never a
   side-quest inside this make (pull rule 3).
6. anything that needs the owner's keypress — landing, ratifying, arming.

## "done" — the five-line contract

(a) the backlog row's check ran and passed, verify-rendered · (b) full suite green
at the pack's expected count or higher, zero skips · (c) producer cold read to
SHIP-CLEAR for any [product] item — findings block until repaired or overruled by
the owner's recorded k · (d) notes staged (the make note with commit sha as
receipt) · (e) the backlog row's proof drafted for the sync. done is STAGED, not
landed.

## environment (the floor)

- `cd the cartridge root` · `uv run pytest -q` (the covenant; ~90s).
- the web surface: `uv run uvicorn commerceos.web.app:app --port 8848` — proven at
  127.0.0.1:8848. tests use FastAPI TestClient with `COMMERCEOS_DB` pointed at a
  scratch path (see tests/test_workflow_runs_web.py for the rig shape).
- store/db resolution is CALL-TIME via `commerceos/stores.py` (env overrides
  `COMMERCEOS_STORE` / `COMMERCEOS_DB` win first). never re-introduce an
  import-time path read.
- test conventions: pin against the LIVE data shape where a surface renders
  (minted-fixture tests that go green while the surface lies are the house's
  twice-paid lesson); replay-refusal and provenance assertions are mandatory for
  any executor; new tests go in `tests/test_<part>_*.py`.
