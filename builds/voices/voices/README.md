# voices

Five voices that make writing sound like a person wrote it, each one an output
style you can switch on or drop into a project. This started as a skill you
invoked per task. It is output styles now, so a voice stays on until you change
it, and a project can carry its own.

## the voices

- **work** — professional prose: emails, docs, reports, READMEs, plans. The default.
- **conversation** — chat, DMs, replies, community posts. Short and uneven.
- **copy** — landing pages, product pages, ads, sales email, microcopy.
- **artist** — the academic art register: artist statements, curatorial statements, wall text, catalogue essays.
- **michael** — the woodshop voice. Warm, brief, a maker at the bench.

Every voice is self-contained. It carries the universal core (the rules that
hold in all of them, like no em dashes and no contrast constructions) folded in,
then its own settings on six dimensions: word stock, pace, fillers, assumed
context, opinion and certainty, relationship.

## installing

Copy the files into your output-styles folder:

    cp output-styles/voice-*.md ~/.claude/output-styles/

Then run `/output-style` and scroll to the one you want. It stays on for the
session and for new sessions until you switch.

## embedding one in a project

Drop a single voice into the project instead, and it travels with the repo:

    mkdir -p your-project/.claude/output-styles
    cp output-styles/voice-michael.md your-project/.claude/output-styles/

Anyone who opens Claude Code in that project sees the voice in `/output-style`.
This is how the michael app carries its own voice: the file sits in the app and
the app loads it into every reply.

## the evidence

`references/` holds the research the voices are built on, kept as provenance
rather than loaded at runtime:

- `framework.md` — the six-dimension authoring framework every voice is set on.
- `research.md` — 50 verified findings on what makes language read as human.
- `tells.md` — the AI-tell catalog, read when rewriting existing text.
- `copy-canon.md` — 26 ranked sources and 53 verified rules behind the copy voice.
- `artist-canon.md` — the ranked sources and verified rules behind the artist voice, including the International Art English corpus study.

Both canons came from research runs with adversarial verification. Folklore that
failed a check is named and killed at the bottom of each file.
