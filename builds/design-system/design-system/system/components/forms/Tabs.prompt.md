# Tabs

Teletext-style segmented tabs with an inverted active tab. Use for view switching
(STAT · INV · DATA).

## a11y (the rebuild)
`role="tablist"` with `role="tab"` children, roving tabIndex (only the active tab is in
the Tab order), and Arrow / Home / End keyboard navigation that moves focus and selection
together. `aria-selected` tracks the active tab; a `:focus-visible` ring marks keyboard
focus. Pair the active index with your own `role="tabpanel"` region for full semantics.

## Laws honored
- (1) mono inactive tabs, (2) one earned accent via the inverted active block (single fill),
  (3) 0px radius + 2px bottom rule, (4) no motion required (instant invert; no animation to gate),
  (5) no emoji.

```jsx
<Tabs tabs={["STAT","INV","DATA"]} value={i} onChange={setI} />
```

Controlled via value/onChange, or uncontrolled.
