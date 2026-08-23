# Stat + KeyValue — authoring notes

## Purpose
Two see-the-parts data primitives for the workshop surfaces — the places that show
you the numbers behind a thing.

- **Stat** — a single metric tile. Big die-cut display number on void, uppercase
  mono label, optional unit, optional delta with a single-ink up/down mark.
- **KeyValue** — a tight, hairline-separated definition list of key → value rows.
  Dense by intent; the small spec block beside a tile.

## When to use
- Reach for **Stat** when one number is the headline: a count, a speed, a budget
  left, a percentage. Group three or four in a row for a readout strip.
- Reach for **KeyValue** when a handful of facts travel together and none of them
  is the hero: a serial, a mode, a last-touched time. It is a `<dl>`, so it reads
  as a real definition list to a screen reader.
- Use a Stat's `delta` only when the change is the story. A number `delta` renders
  signed; `>0` gets a green ▲, `<0` an alert ▼, `0` a faint dash — single-ink
  marks, never fills.

## Laws honored
1. **Mono base.** Both default to ink-on-void: faint mono labels, signal-ink
   values. No color is needed to read either one.
2. **One earned accent.** Stat takes exactly one accent on the number via `tone`
   (amber=active, magenta=rebel, green=ok, cyan=link). Default is mono. The delta
   mark is single-ink status, never a fill — it does not count as the view's accent
   spend.
3. **Die-cut.** 0px radius, 2px ink border, hard 3px offset shadow, no soft blur,
   on every tile and the list.
4. **Reduced-motion safe.** Neither primitive animates; both are static end-state
   surfaces. The delta mark's half-pixel nudge is dropped under
   `prefers-reduced-motion` via `window.matchMedia`, recomputed live.
5. **No emoji.** Direction is shown with the geometric marks ▲ ▼ — and CRT/mono
   numerals; nothing pictographic.

## A11y
- **Stat** is a plain labeled container; label, value, unit, and delta are all
  rendered text, so the full reading is in the DOM in order. The delta mark is
  `aria-hidden` (decorative) — its meaning is carried by the signed text beside it.
- **KeyValue** renders a true `<dl>` with `<dt>`/`<dd>` pairs, so assistive tech
  announces it as a definition list with proper key/value association. No ARIA
  bolt-ons needed — the native semantics carry it.
- Both are read-only display surfaces, so there is no keyboard interaction to trap;
  they sit naturally in tab order around interactive siblings.

## Copy discipline
Visible labels are felt outcomes only — `BUILT THIS WEEK`, `RUNS LEFT`, `LAST TOUCH`
— never the system's private vocabulary.
