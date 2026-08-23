# Table

**Purpose.** The maker's primary data surface: a mono, dense, die-cut grid for
records, runs, ledgers, inventories — anything that reads as rows and columns. Built
to feel like a printout off a workshop terminal, not a web dashboard.

**When to use.** Tabular data with shared columns and many rows. Reach for it when
the data is comparable down a column (counts, sizes, timestamps) and the maker needs
to scan and sort. For a handful of key/value facts, use a definition list instead —
a table earns its borders only when there are real rows.

**Shape.**
- `columns`: `{ key, label, align?, sortable?, compare?, render? }[]`. `align: 'right'`
  marks a numeric column — tabular nums, nowrap.
- `rows`: objects keyed by `column.key`; an `id` field keys React rows, else index.
- Sort: controlled with `sortKey` / `sortDir` / `onSort`, or uncontrolled with
  `defaultSortKey` / `defaultSortDir` (self-sorts a local copy when no `onSort`).
- `dense` tightens padding + type; `zebra` shades alternate rows; `serial` prepends a
  zero-padded mono row-number column; `caption` sits above as an uppercase mono label.

**Laws honored.**
1. *Mono base.* Whole surface is ink-on-void mono type; no color needed to read or
   sort it. Inactive headers and data sit in dim ink.
2. *One earned accent.* Amber marks exactly the active sort column — its header label
   and caret. Everything else stays neutral. The keyboard focus ring is cyan (link),
   the one other hue, and it only appears on keyboard focus — never both shouting at rest.
3. *Hard die-cut.* 0px radius throughout, 2px ink outer border with a hard offset
   `--shadow-slap`, 2px ink header underline, 1px `--border` hairline row + column rules.
   No soft blur anywhere.
4. *Snappy + reduced-motion safe.* The only motion is the active caret flipping
   asc/desc on `--ease-snap`. `window.matchMedia('(prefers-reduced-motion: reduce)')`
   kills that transition and shows the end-state caret immediately.
5. *No emoji.* Sort marks are CRT unicode (`↕` idle, `▲` active, rotated for desc); the
   serial header is `№`; the empty state is em-dashes. Numerals are mono/tabular.

**A11y.** Native `<table>`/`<thead>`/`<tbody>` semantics. Sortable headers are real
`<button>`s inside `<th scope="col">`; the `<th>` carries `aria-sort`
(ascending/descending/none) so AT announces sort state. Keyboard-operable by default
with a visible cyan `:focus-visible` ring (injected once, scoped to `.sbx-table-sort`).
The serial column is decorative and `aria-hidden`. Loud, not broken.
