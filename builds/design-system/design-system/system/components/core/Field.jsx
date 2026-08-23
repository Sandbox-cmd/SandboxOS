import React from 'react';

/**
 * Field — a terminal-style input. Amber prompt prefix + blinking caret.
 */
export function Field({ label, prefix = '>', placeholder, style, ...props }) {
  return (
    <label style={{ display: 'block', fontFamily: 'var(--font-mono)', ...style }}>
      {label && (
        <span style={{ display: 'block', fontSize: 'var(--t-2xs)', textTransform: 'uppercase', letterSpacing: 'var(--ls-wide)', color: 'var(--text-faint)', marginBottom: 5 }}>
          {label}
        </span>
      )}
      <span style={{ display: 'flex', alignItems: 'center', gap: 8, border: '2px solid var(--border-strong)', background: 'var(--bg-sunken)', padding: '7px 10px' }}>
        <span style={{ color: 'var(--amber)' }}>{prefix}</span>
        <input
          placeholder={placeholder}
          style={{ flex: 1, minWidth: 0, background: 'transparent', border: 0, color: 'var(--text)', fontFamily: 'var(--font-mono)', fontSize: 'var(--t-sm)', outline: 'none' }}
          {...props}
        />
        <span style={{ width: 8, height: 15, background: 'var(--amber)', animation: 'sbx-blink 1s steps(1) infinite', boxShadow: '0 0 6px var(--glow-amber)' }} />
      </span>
    </label>
  );
}
