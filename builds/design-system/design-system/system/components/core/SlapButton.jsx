import React from 'react';

/**
 * SlapButton — the SandboxOS button: a die-cut sticker slap.
 * Hard 2px border, hard offset shadow, presses DOWN like a real slap.
 * Mono by default; color is earned via `tone`.
 */
export function SlapButton({
  children,
  tone = 'default',
  size = 'md',
  block = false,
  disabled = false,
  rotate = 0,
  style,
  ...props
}) {
  const [hover, setHover] = React.useState(false);
  const [press, setPress] = React.useState(false);

  const tones = {
    default: { bg: 'var(--signal)', fg: 'var(--ink)', edge: 'var(--ink)', sh: 'var(--signal)' },
    ghost:   { bg: 'transparent',   fg: 'var(--signal)', edge: 'var(--signal)', sh: 'var(--crt-700)' },
    go:      { bg: 'var(--amber)',  fg: 'var(--ink)', edge: 'var(--ink)', sh: 'var(--amber-deep)' },
    rebel:   { bg: 'var(--magenta)',fg: 'var(--signal)', edge: 'var(--ink)', sh: 'var(--magenta-deep)' },
    ok:      { bg: 'var(--green)',  fg: 'var(--ink)', edge: 'var(--ink)', sh: 'var(--green-deep)' },
    danger:  { bg: 'var(--alert)',  fg: 'var(--signal)', edge: 'var(--ink)', sh: 'var(--ink)' },
  };
  const sizes = {
    sm: { pad: '4px 10px', fs: 'var(--t-xs)', sh: 2 },
    md: { pad: '7px 15px', fs: 'var(--t-sm)', sh: 3 },
    lg: { pad: '11px 22px', fs: 'var(--t-md)', sh: 4 },
  };
  const t = tones[tone] || tones.default;
  const s = sizes[size] || sizes.md;
  const off = press ? 0 : hover ? s.sh - 1 : s.sh;

  return (
    <button
      type="button"
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => { setHover(false); setPress(false); }}
      onMouseDown={() => setPress(true)}
      onMouseUp={() => setPress(false)}
      style={{
        display: block ? 'flex' : 'inline-flex',
        width: block ? '100%' : undefined,
        alignItems: 'center', justifyContent: 'center', gap: '7px',
        fontFamily: 'var(--font-display)', fontWeight: 900,
        fontSize: s.fs, letterSpacing: 'var(--ls-wide)', textTransform: 'uppercase',
        color: t.fg, background: t.bg,
        border: `2px solid ${t.edge}`, borderRadius: 0,
        padding: s.pad, cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.4 : 1,
        boxShadow: `${off}px ${off}px 0 ${t.sh}`,
        transform: `translate(${s.sh - off}px, ${s.sh - off}px) rotate(${rotate}deg)`,
        transition: 'box-shadow 90ms var(--ease-snap), transform 90ms var(--ease-snap)',
        userSelect: 'none', ...style,
      }}
      {...props}
    >
      {children}
    </button>
  );
}
