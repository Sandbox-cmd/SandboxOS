# voices — plain hands

one output style that makes writing sound like a person wrote it, whoever the
reader is. it replaces the five voices this build used to carry (work,
conversation, copy, artist, michael): they shared one core and six section
heads, and differed only in who was reading. plain hands writes the core once
and folds the five readers in as short "when the reader is…" paragraphs:
a colleague, a friend in chat, a customer, a gallery visitor, someone at the
bench.

## installing

copy the file into your output-styles folder:

    cp output-styles/plain-hands.md ~/.claude/output-styles/

then run `/output-style` and pick **plain hands**. it stays on for the session
and for new sessions until you switch.

## embedding it in a project

drop it into the project instead, and it travels with the repo:

    mkdir -p your-project/.claude/output-styles
    cp output-styles/plain-hands.md your-project/.claude/output-styles/

anyone who opens Claude Code in that project sees it in `/output-style`.

## the banned words

the style carries no word list of its own. it points at the soul's
forbidden-phrases table in Sandbox OS (`soul/voice.md`), so there is one list
and one set of reasons. if you use the style outside a Sandbox workshop, that
table is at https://github.com/Sandbox-cmd/SandboxOS-core/blob/main/soul/voice.md.

## the evidence

`references/` holds the research the style is built on, kept as provenance
rather than loaded at runtime:

- `framework.md` — the six-dimension authoring framework the style is set on.
- `research.md` — 50 verified findings on what makes language read as human.
- `tells.md` — the AI-tell catalog, read when rewriting existing text.
- `copy-canon.md` — 26 ranked sources and 53 verified rules behind the customer paragraph.
- `artist-canon.md` — the ranked sources and verified rules behind the gallery paragraph, including the International Art English corpus study.

both canons came from research runs with adversarial verification. folklore
that failed a check is named and killed at the bottom of each file.
