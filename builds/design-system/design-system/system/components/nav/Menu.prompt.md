# Menu — authoring notes

## Purpose
A die-cut dropdown / context menu: a slap that popped up off the surface. The
workshop primitive for "pick one action from a short list" — kebab/overflow menus,
right-click context actions, a button's drop-down of commands.

## When to use
- A trigger reveals a short list of **actions** (not values to persist — that's a
  Select/Radio). Verbs, not settings.
- 2–9 rows. Past that, reach for a searchable panel, not a menu.
- One row may be destructive (`danger`) — it burns single-ink, sits below a
  hairline separator by convention, never gets a red fill.

## Anatomy
- Each `items[]` row: `{ id, label, mark?, shortcut?, danger?, disabled?, separator? }`.
- `mark` is an optional leading CRT/pixel unicode glyph (▸ ⌫ ✕ ↻) — never emoji.
- `shortcut` is a trailing hint, right-aligned, dim until the row is live.
- `{ separator: true }` draws a hairline rule (`--border`) between groups.
- Mount inside a `position: relative` opener; `anchor` picks the corner it pops from.

## How it behaves
- Controlled via `open` / `onClose`. `onSelect(id, item)` fires, then `onClose`.
- Opening snaps focus to the first focusable row and remembers the opener.
- Closing (Esc, selection, parent flips `open`) restores focus to the opener.

## Laws honored
1. **Mono base.** Rows are ink-on-void mono; no color needed to read or operate it.
2. **One earned accent.** The single live row wears amber; the danger row is the
   lone status-ink (single-ink, never a fill). Only one row is ever lit at a time.
3. **Die-cut.** 0px radius, 2px ink border, hard offset shadow (`--shadow-slap-lg`,
   no blur). The live row gets a hard inset ink ring, not a soft glow.
4. **Snappy + reduced-motion.** One snap-down pop into place via `--ease-snap`;
   `window.matchMedia('(prefers-reduced-motion: reduce)')` shows the end-state and
   skips the motion, and re-syncs if the OS setting changes mid-session.
5. **No emoji.** Marks and shortcuts are CRT/pixel unicode only.

## A11y
- `role="menu"` + `role="menuitem"`, `role="separator"` for rules.
- Keyboard: Arrow up/down (wraps), Home/End, Enter/Space to choose, Esc to close,
  Tab kept inside the menu (focus trap) with wrap.
- Roving `tabIndex`; `aria-disabled` on dimmed rows; focus-visible ring on the live
  row; focus restored to the opener on close. Loud, never broken.

## Token discipline
`var(--token)` only — `--bg-raised`, `--ink`, `--text`, `--amber`, `--danger`,
`--border`, `--text-faint`, `--shadow-slap-lg`, `--font-mono`, `--font-crt`,
`--ease-snap`, `--dur-1`, type/tracking scale. No raw hex, no invented tokens.
