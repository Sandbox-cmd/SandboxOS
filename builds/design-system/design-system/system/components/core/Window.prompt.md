The bootleg-OS window/panel frame with an inverted title bar, hard border + offset shadow. Use to frame any panel; `tone="blue"` is the full-screen error-screen takeover.

```jsx
<Window title="WONDER.TXT" onClose={fn} footer={<SlapButton size="sm">ok</SlapButton>}>
  ever wonder why it's more fun on your own machine?
</Window>
```

Props: title · tone (mono|blue) · width · tilt · footer · onClose.