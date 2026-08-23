# CodeBlock — authoring notes

## Purpose
A workshop primitive: the surface where source, terminal output, and logs live.
A sunken void framed by a die-cut border with a hard offset shadow — the place
the machine talks back to a builder.

## When to use
- **`variant="code"`** — show source (mono, tight `--t-xs`). Pair with
  `showLineNumbers` for files and snippets, `copyable` so a builder can grab it.
- **`variant="log"`** — show a run/terminal stream (CRT face, `--t-sm`). Feed it
  `lines={[{ text, tone }]}`; tones are single-ink only (`ok` green, `warn`,
  `err`, `info` cyan-link, `dim` faint, `rebel` magenta) — the ink changes,
  never a fill, so one earned accent can survive per view.
- Pass `code` (a string) for the common case, or `lines` when you already have
  rows or want per-line tones.

## Laws honored
1. **Mono base.** Default surface is ink-on-void, no color needed; tones are
   opt-in and never required to read the block.
2. **One earned accent.** Log tones color the text ink only — never a fill —
   and the copy control is a `ghost` slap, so nothing competes for the accent.
3. **Hard edges.** `--bw-1` die-cut border, `0` radius, `--shadow-slap` hard
   offset — no soft blur anywhere.
4. **Snappy / reduced-motion.** The only motion is the copy slap (SlapButton's
   90ms press) and the transient "copied" confirm; a live `matchMedia`
   `prefers-reduced-motion` hook shortens the confirm to its end-state instead
   of lingering. No idle animation to suppress.
5. **No emoji.** Bar mark is `■` (filled square), copy confirm is `✓`
   (check) — CRT/pixel unicode, never emoji.

## A11y
- The scroll body is a real `<pre><code>` so AT reads it as code, whitespace
  preserved (`white-space: pre`, `tab-size: 2`).
- The copy control is a real focusable button (reused SlapButton) with an
  `aria-label` that flips to "copied to clipboard"; a visually-hidden
  `aria-live="polite"` region announces the copy for screen readers.
- Line numbers are `aria-hidden` and non-selectable, so a copy or AT read never
  drags the gutter into the text.
- `clipboard.writeText` with an off-screen-`textarea` fallback for non-secure
  contexts; clipboard failure fails quiet, never throws into render.

## Notes
- Reuses `SlapButton` (`tone="ghost" size="sm"`) for copy — never re-implements it.
- Tokens only: `--bg-sunken`, `--font-mono`/`--font-crt`, `--text-faint` gutter,
  `--bw-1`/`--ink` border, `--shadow-slap`. No raw hex, no invented tokens.
- Visual-only component (no form value) so there is no controlled/uncontrolled
  value prop; it renders whatever `code`/`lines` it is handed.
