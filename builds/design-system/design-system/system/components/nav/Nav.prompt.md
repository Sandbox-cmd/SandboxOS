# Nav — workbench side navigation

## Purpose
The standing side rail of the workbench. Groups the places you work into labeled
sections and keeps one item lit as where-you-are. Built to feel like a die-cut
control panel, not a soft web sidebar.

## When to use
- The primary in-app navigation down the left of a workbench layout.
- Any grouped list of destinations where exactly one is "current" at a time.
- Use `collapsed` for a narrow rail (marks only) when horizontal room is tight.
- Not for tabbed content panes (use Tabs) and not for menus that fire actions
  and dismiss (use a menu component).

## Shape
```jsx
<Nav
  sections={[
    { label: 'BUILD', items: [
      { id: 'bench',  label: 'workbench', mark: '▣', count: 3 },
      { id: 'parts',  label: 'parts bin', mark: '▤' },
    ]},
    { label: 'SHIP', items: [
      { id: 'queue',  label: 'send queue', mark: '▶', count: 12 },
    ]},
  ]}
  activeId="bench"
  onSelect={(id) => setView(id)}
/>
```

## Laws honored
1. **Mono base.** The whole rail is ink-on-void mono — readable and usable with
   zero color. The accent is decoration on top of an already-working surface.
2. **One earned accent.** Only the single active row spends color: a left
   die-cut bar plus brand-ink label, mark, and count chip. Every other row is
   mono. Swap the hue per view via `accent` (amber active / magenta rebel /
   green ok / cyan link) — one per view, never two shouting.
3. **Hard edges.** 0px radius throughout, 2px die-cut border on the rail and the
   count chip, a hard offset `--shadow-slap`. No soft blur anywhere.
4. **Snappy, reduced-motion safe.** Hover/active swaps ride `--ease-snap` at
   `--dur-1`. `window.matchMedia('(prefers-reduced-motion: reduce)')` is read
   live; when reduced, transitions drop to `none` and the lit end-state shows
   instantly.
5. **No emoji.** Leading marks are CRT/pixel unicode glyphs supplied by the
   caller; counts are brutalist mono numerals.

## A11y
- Real `<nav>` landmark with a label; each section is a `role="group"` carrying
  its label (kept for AT even when the rail is collapsed to a `·`).
- Roving tabindex: one row is tabbable, Arrow Up/Down move focus (wrapping),
  Home/End jump to ends, Enter/Space select. Focus follows the active item.
- The live row gets `aria-current="page"`; focus paints a cyan `focus-visible`
  ring via inline outline.
- Collapsed rows hide the visible label/count but expose `title` plus a
  visually-hidden label+count span, so the rail stays legible to AT and pointer.
