# List — authoring notes

## Purpose
A dense vertical feed of die-cut rows — the workshop primitive for runs, queues,
inventory, log lines, anything that stacks. Each row carries a leading status dot
or serial, a mono primary label, optional faint meta, and an optional trailing
value or action. Built mono-first so it reads with zero color.

## When to use
- A list of records where density and scan-speed matter more than cards.
- A pickable feed (pass `onSelect`) — selecting one item from many.
- Status-bearing rows (a queue of jobs, a roster of devices) where a single-ink
  dot tells the state at a glance.

Reach for cards instead when each item needs its own rich layout; reach for a
table when columns must align across rows.

## Props
`items` (id, label, meta, status, serial, trailing) · `onSelect` (makes rows
focusable options) · `value` / `defaultValue` (controlled + uncontrolled) ·
`dense` · `divided`.

## Laws honored
1. **Mono base.** Ink-on-void rows on a sunken void, mono type, no color needed
   to read or operate the list.
2. **One earned accent.** Exactly one amber mark per view — the active row's edge
   bar and focus ring. Status dots stay single-ink (amber/green/magenta/cyan/
   hazard/alert) and are *hollow rings*, never fills, so they read as marks not
   blocks — two things never shout at once.
3. **Hard edges.** 0px radius throughout, 2px die-cut container border, hairline
   rules between rows. No soft blur anywhere.
4. **Snappy, reduced-motion safe.** The active-row marker slaps in on
   `--ease-snap` / `--dur-1`; `window.matchMedia('(prefers-reduced-motion: reduce)')`
   collapses the travel to the end-state with no animation.
5. **No emoji.** Status is a unicode/CSS dot; serials use tabular numerals.

## A11y
Loud but operable. Selectable lists render as a real `listbox` of `option`
buttons: roving `tabIndex` (one tab-stop), Arrow/Home/End move focus, Enter/Space
pick, `aria-selected` tracks the choice, and each row carries an `aria-label` that
speaks label + meta + status (the dot itself is `aria-hidden`). A focus-visible
amber ring lands via focus styling. Non-selectable lists degrade to a plain
`list` / `listitem` structure.

## Demo copy
Use felt outcomes only — "build queue", "last run 4m ago", "device offline" —
never insider vocabulary.
