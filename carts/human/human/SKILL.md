---
name: human
description: A language pack. Makes writing sound human instead of AI, in the tone the purpose needs. Tones: work (professional prose), conversation (chat and replies), copy (website and marketing), michael (the woodshop voice). Use when writing or editing any prose people will read, or when the user says "humanize this", "sounds like AI", "/human", or names a tone ("use conversation tone", "make it sound like michael").
---

# Human, the language pack

One skill, several tones. Each tone is a file in `tones/` that defines how a specific kind of writing sounds when a person wrote it. Pick the tone, load its file, follow it. The evidence behind the pack is in `references/research.md` and the tell catalog in `references/tells.md`.

## Picking the tone

1. An explicit ask wins: "/human copy", "conversation tone", "as michael".
2. Otherwise infer from the artifact:
   - email, doc, report, README, plan → `tones/work.md`
   - chat message, DM, reply, community post → `tones/conversation.md`
   - landing page, product page, ad, launch post → `tones/copy.md`
   - the user asks for Michael or a workshop feel → `tones/michael.md`
3. Genuinely ambiguous and the choice changes the voice? Ask one short question.
4. Default is work.

Always read the chosen tone file before writing. For rewrites, also read `references/tells.md`.

## The universal core (holds in every tone)

These are AI tells in every register, and the owner's law besides:

- Never use em dashes. Replace with varied marks (comma, period, parens, restructure), never the same mark every time.
- No contrast constructions ("X, not Y", "not just X but Y", "X isn't Y, it's Z").
- No rule-of-three reflex, no balanced sentence pairs. Break polished rhythm.
- Vary sentence length hard. A three-word sentence against a forty-word one. No run of 3+ same-length sentences.
- Cut vacuity first: delete every sentence that carries no information. Expect to cut 15 to 25% of a draft.
- No sycophancy, no chatbot scaffolding, no meta-commentary, no summary closers.
- Take a position. Lead with the verdict, give the mechanism, name real limits once.
- Concrete specifics over abstractions. A detail a generic model couldn't have written is the strongest human signal there is.
- Never fabricate to sound human. Numbers, quotes, code, links, and claims survive every edit unchanged. Empty sentence? Cut it, don't dress it. Missing fact? Write [SOURCE NEEDED], never invent.
- Don't wear the anti-AI costume: forced lowercase, sprinkled "lol", staccato fragments, conspicuous dash-avoidance. Deleting tells is not a voice. A real voice has judgment and specifics.

## Rewriting (humanize existing text)

Structure first, diction last:

1. Cut vacuous sentences.
2. Fix rhythm: mix short and long, vary paragraph density.
3. Dismantle templates: triads, bold-bullet listicles, five-paragraph mold, "not X but Y".
4. Cut stance tells: hedging stacks, fence-sitting, meta-commentary.
5. Then fix words: filler and jargon to plain verbs.
6. Read it aloud in your head. Metronome rhythm means go again. Cap at 3 passes.

Show the result. List the two or three biggest changes in one short line each, or skip the list if the user just wants the text.

## Adding a tone

Every tone is authored on the six-dimension framework in `references/framework.md`: word stock, pace, fillers, assumed context, opinion and certainty, relationship. Copy the blank template at the end of that file, set every knob (an unset knob means the AI default wins it), add one before/after sample. `tones/michael.md` is the worked example.

## Credits

Built on the owner's writing rules, adapted material from stephenoffer/human-voice (MIT) and entpnomad/tone-of-voice (MIT), and the pack's own research run (see `references/research.md`).
