# Pagination — authoring notes

## Purpose
A brutalist pager. Numbered slaps stamped as 3-digit serials (`001`, `002`, …),
prev/next as unicode marks (`◀` / `▶`), the current page wearing the single earned
accent. Mono, die-cut, dense — it reads like a cartridge index, not a web widget.

## When to use
- Stepping through pages of records, results, or a long catalog.
- Anywhere a list outgrows one screen and the user needs to jump by index.
- For "load more" / infinite feeds, do NOT use this — those have no fixed page count.

## Props
- `page` / `defaultPage` — controlled vs uncontrolled, exactly like `Switch`.
- `pageCount` — total pages (clamped to >= 1).
- `onChange(nextPage)` — fired with the 1-based target.
- `siblingCount` — numbered slaps either side of current (default 1); first + last
  are always shown, the middle collapses to a `•••` gap mark.
- `accent` / `accentEdge` — the one earned accent + its hard shadow ink.

## Laws honored
1. **Mono base** — every resting slap is ink-on-void mono; no color needed to read or
   operate it.
2. **One earned accent per view** — only the *current* page is filled (amber by default);
   everything else stays mono. One thing shouts.
3. **Die-cut** — 0px radius, 2px borders, hard offset shadow (`Npx Npx 0`), zero blur.
4. **Snappy mechanical motion** — press = slap-down (shadow collapses, the slap translates
   into its own shadow). Every transition is gated by `prefers-reduced-motion` via
   `window.matchMedia`; when reduced, the end-state shows and motion is skipped.
5. **No emoji** — prev/next use geometric unicode marks (`◀`/`▶`); the overflow gap is a
   bullet run (`•••`). Numbers are zero-padded brutalist serials.

## A11y (loud, not broken)
- Real `<button>` elements — keyboard, pointer, AT, and form submission all work.
- `<nav aria-label="Pagination">` landmark wrapper.
- Per-page `aria-label="Page N of total"`; `aria-current="page"` on the active slap.
- Prev/Next get `disabled` at the ends (no dead clicks, correct AT state).
- Focus-visible: a cyan ring is layered over the existing hard shadow via focus handlers,
  so the die-cut shadow survives focus.

## Demo copy
Use felt outcomes only — "page 1 of 9", "next", "prev". No insider vocabulary on any
visible surface.
