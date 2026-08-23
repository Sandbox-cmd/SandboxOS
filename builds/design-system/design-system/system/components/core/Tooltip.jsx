import React from 'react';

/** Tooltip — a die-cut slap that pops on hover. */
export function Tooltip({ label, children, tone = 'ink', side = 'top', style, ...props }) {
  const [show, setShow] = React.useState(false);
  const tones = { ink: { bg: 'var(--ink)', fg: 'var(--signal)' }, amber: { bg: 'var(--amber)', fg: 'var(--ink)' }, rebel: { bg: 'var(--magenta)', fg: 'var(--signal)' } };
  const t = tones[tone] || tones.ink;
  const pos = side === 'top'
    ? { bottom: '100%', left: '50%', transform: 'translateX(-50%) translateY(-7px)' }
    : { top: '100%', left: '50%', transform: 'translateX(-50%) translateY(7px)' };
  return (
    <span style={{ position: 'relative', display: 'inline-flex' }} onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)} {...props}>
      {children}
      {show && (
        <span style={{
          position: 'absolute', ...pos, zIndex: 100, whiteSpace: 'nowrap',
          fontFamily: 'var(--font-display)', fontWeight: 900, fontSize: 'var(--t-2xs)', textTransform: 'uppercase', letterSpacing: 'var(--ls-wide)',
          background: t.bg, color: t.fg, border: '2px solid var(--ink)', padding: '3px 8px',
          boxShadow: '0 0 0 2px var(--signal), 2px 3px 0 rgba(0,0,0,0.5)', ...style,
        }}>{label}</span>
      )}
    </span>
  );
}
