# Switch

A hard-edged power rocker — snaps, amber when on. Use for binary settings (sound,
focus mode). For the character-flavored toggle, use FaceToggle.

## When to use
Instant-apply on/off settings where the state itself is the action. Not for form
submission gates — use a Checkbox where "off" is a meaningful unsubmitted value.

## a11y (the rebuild)
A REAL hidden native `<input type="checkbox" role="switch">` sits under the rocker, so
Space/Enter toggle, focus ring, screen-reader on/off state and form submission are all
native. The rocker visual is a sibling driven off `checked`; the `<label>` wraps both.

## Laws honored
- (1) mono off-state, (2) one earned accent (amber ON track, single fill),
  (3) 0px radius + 2px border, (4) rocker slide + track fill gated by
  `prefers-reduced-motion`, (5) no emoji.

```jsx
<Switch label="sound" checked={on} onChange={setOn} />
<Switch label="focus mode" defaultChecked accent="var(--green)" />
```

Props: checked / defaultChecked · onChange · label · name · value · disabled · accent.
