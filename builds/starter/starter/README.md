# starter — a pressed start for a real project

one build, kept on the shelf. starting a new project takes three moves:

    sandbox project new NAME "goal"       # the project — its memory lives here
    # add `root: ~/path/to/repo` to PROJECT.md when the code lives elsewhere
    sandbox use starter                   # this build, copied onto the project

then move what belongs in the repo (the two-body rule below), fill the
blanks in AGENTS.md, and write one line under `## checks` in PROJECT.md —
a ship without a check is just a claim.

## the two-body rule

the repo carries what's buildable; the project carries what's earned.

- repo (git, shareable, tool-agnostic): AGENTS.md · CLAUDE.md (the bridge)
  · claude/agents/ · claude/skills/ · claude/rules/ — rename `claude/` to
  `.claude/` after copying (kept unhidden here so the shelf carries it
  whole).
- project (the workshop): PROJECT.md (goal, sketch, state, checks, root) ·
  CANON.md (landed knowledge — the record projects it; never hand-edit)
  · .make/ (the seam's paper).

copy the project directory and the earned memory travels. clone the repo
and the capability travels. both together are the whole project.

## how it grows

- facts: work sessions stage notes; the owner lands; canon fills.
- corrections: staged verbatim the moment they happen; a stop-hook
  backstop mines the transcript too.
- procedures: the same steps run twice → draft a skill in claude/skills/
  (eval first: prove the task fails without it, then write the minimum
  that passes).
- specialists: a domain accumulates → raise one agent in claude/agents/
  (see the README there; few, restricted, never trusted unaudited).
