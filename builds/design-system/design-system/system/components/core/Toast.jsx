import React from 'react';

/**
 * Toast — a talk-back aside in the character's voice. Color is earned via tone.
 */
export function Toast({ title, children, tone = 'rebel', glyph = '✦', style, ...props }) {
  const tones = { rebel: 'var(--magenta)', alert: 'var(--alert)', ok: 'var(--green)', info: 'var(--cyan)', warn: 'var(--hazard)' };
  const ic = tones[tone] || tones.rebel;
  return (
    <div style={{ display: 'inline-flex', alignItems: 'stretch', border: '2px solid var(--signal)', background: 'var(--bg-raised)', maxWidth: 300, fontFamily: 'var(--font-mono)', ...style }} {...props}>
      <div style={{ width: 34, background: ic, color: 'var(--ink)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-crt)', fontSize: 'var(--t-md)' }}>{glyph}</div>
      <div style={{ padding: '7px 11px', fontSize: 'var(--t-xs)', lineHeight: 1.45, color: 'var(--text)' }}>
        {title && <b style={{ fontFamily: 'var(--font-display)', fontWeight: 900, textTransform: 'uppercase', display: 'block', fontSize: 'var(--t-xs)' }}>{title}</b>}
        {children}
      </div>
    </div>
  );
}
