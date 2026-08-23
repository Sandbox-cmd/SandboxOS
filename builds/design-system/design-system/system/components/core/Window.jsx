import React from 'react';

/**
 * Window — the SandboxOS window/panel frame. Inverted title bar, hard
 * border + offset shadow. `tone="blue"` is the bootleg error-screen takeover.
 */
export function Window({ title = 'SANDBOX_OS', children, onClose, width, tone = 'mono', tilt = 0, footer, style, ...props }) {
  const blue = tone === 'blue';
  return (
    <div style={{
      width, border: '2px solid var(--signal)',
      background: blue ? 'var(--blue)' : 'var(--bg-raised)',
      boxShadow: '5px 5px 0 rgba(0,0,0,0.55)', transform: tilt ? `rotate(${tilt}deg)` : undefined,
      fontFamily: 'var(--font-mono)', ...style,
    }} {...props}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        background: 'var(--signal)', color: 'var(--ink)', fontWeight: 700,
        fontSize: 'var(--t-xs)', padding: '3px 8px', letterSpacing: 'var(--ls-wide)', textTransform: 'uppercase',
      }}>
        <span>{title}</span>
        <span onClick={onClose} role={onClose ? 'button' : undefined} style={{
          border: '1.5px solid var(--ink)', width: 14, height: 14, display: 'inline-flex',
          alignItems: 'center', justifyContent: 'center', fontSize: 10, cursor: onClose ? 'pointer' : 'default',
        }}>✕</span>
      </div>
      <div style={{ padding: '13px 14px', color: blue ? 'var(--signal)' : 'var(--text)', fontSize: 'var(--t-sm)', lineHeight: 1.55 }}>
        {children}
      </div>
      {footer && <div style={{ padding: '0 14px 13px' }}>{footer}</div>}
    </div>
  );
}
