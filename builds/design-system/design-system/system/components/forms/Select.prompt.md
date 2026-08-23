# Select

A mono dropdown with a hard amber caret. Use for compact option pickers.

## a11y (the rebuild)
Built on a REAL native `<select>`, so keyboard, type-ahead, screen-reader announcement
and form submission are all native — no custom listbox to get wrong. The caret is
decorative (`pointer-events:none`, `aria-hidden`); a `:focus-within` ring on the shell
marks focus. Supports controlled (`value`) and uncontrolled (`defaultValue`), `name`,
and `disabled`.

## Laws honored
- (1) mono shell, (2) one earned accent (amber caret, single-ink),
  (3) 0px radius + 2px border with a hard divider, (4) native open — no custom motion,
  (5) no emoji (CRT ▾ caret).

```jsx
<Select label="mode" options={["sovereign","workbench","night shift"]} />
<Select label="speed" defaultValue="fast" options={[{label:"Fast",value:"fast"},{label:"Careful",value:"careful"}]} />
```

Options accept strings or `{label,value}`.
