# Checkbox · Radio

Die-cut checkbox (amber ✕) and round Radio (magenta dot). Use Checkbox for boolean
opt-ins, Radio for single-select from a named group.

## When to use
- Checkbox: independent on/off choices ("remember this device", "send updates").
- Radio: pick exactly one from a small set; give every radio in the set the same `name`.

## a11y (the rebuild)
Each control is a REAL hidden native `<input>` (focusable, AT-readable, form-submitting),
visually hidden but never `display:none`. The die-cut visual is a sibling driven off the
input's checked state; the `<label>` wraps both, so pointer, keyboard, screen reader and
form value all work. Focus shows a `:focus-visible` ring on the visual.

## Laws honored
- (1) mono base, (2) one earned accent (amber checkbox / magenta dot, single-ink),
  (3) 0px radius + 2px die-cut border (round only for the radio dot),
  (4) snap transition gated by `prefers-reduced-motion`, (5) no emoji (CRT ✕ mark).

```jsx
<Checkbox label="remember this device" defaultChecked />
<Checkbox label="send me updates" />
<Radio name="mode" checked={v==='local'} value="local" onChange={setV} label="on this machine" />
<Radio name="mode" checked={v==='cloud'} value="cloud" onChange={setV} label="in the cloud" />
```

Exports: Checkbox, Radio. Props: checked / defaultChecked · onChange · label · name · value · disabled · accent.
