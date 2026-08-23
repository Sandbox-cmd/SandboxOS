A talk-back dialog — the OS speaks in its own voice and offers slap actions. Use for confirmations, notices, the error-screen.

```jsx
<Dialog title="⚠ NOTICE" glyph="⌐■_■"
  actions={[{label:'build it',tone:'go'},{label:'later',tone:'ghost'}]}>
  no smile detected. that's allowed here.
</Dialog>
```

Props: title · tone (mono|blue) · actions[{label,onClick,tone}] · glyph (kaomoji aside).