# Knob

The cassette-deck / instrument dial — drag vertically, use the wheel, or use the
keyboard to turn it. A real dial — label it with what it actually moves (gain, speed,
threshold); it won't judge how hard you crank it.

## a11y (the rebuild)
`role="slider"` with `aria-valuenow` / `valuemin` / `valuemax` / `valuetext` and an
accessible name (from `label` or `aria-label`). Keyboard: Arrow keys step, PageUp/PageDown
jump by 10%, Home/End snap to the bounds; values round to avoid float noise in the
announcement. A `:focus-visible` ring marks keyboard focus.

## Laws honored
- (1) mono hardware shell, (2) one earned accent (the indicator needle, single-ink),
  (3) round is allowed here — it is a physical dial, not a flat control; 2px ink border,
  (4) needle rotation gated by `prefers-reduced-motion`, (5) no emoji.

```jsx
<Knob label="memory" defaultValue={0.7} onChange={v => …} />
<Knob label="speed" accent="var(--magenta)" min={0} max={11} defaultValue={11} />
```

Props: value/defaultValue · min · max · step · label · size · accent · onChange · aria-label.
Keyboard + wheel + drag accessible.
