import React from 'react';

/**
 * Loader — the CRT "THANK YOU FOR USING" progress bar. Indeterminate when
 * `value` is null, otherwise a 0–100 fill. Phosphor amber.
 */
export function Loader({ value = null, label = 'LOADING', caption = 'THANK YOU FOR USING', width = 220, style, ...props }) {
  const pct = value == null ? null : Math.max(0, Math.min(100, value));
  return (
    <div style={{ fontFamily: 'var(--font-crt)', color: 'var(--amber)', width, ...style }} {...props}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--t-base)', letterSpacing: 'var(--ls-wide)' }}>
        <span>{label}{pct == null ? '…' : ''}</span><span>{pct == null ? '' : pct + '%'}</span>
      </div>
      <div style={{ height: 12, border: '1px solid var(--amber-deep)', marginTop: 4, overflow: 'hidden', background: 'var(--bg-sunken)' }}>
        <div style={{
          height: '100%',
          width: pct == null ? '40%' : pct + '%',
          background: 'repeating-linear-gradient(90deg, var(--amber) 0 6px, transparent 6px 10px)',
          boxShadow: '0 0 8px var(--glow-amber)',
          animation: pct == null ? 'sbx-loader-indef 1.1s linear infinite' : undefined,
        }} />
      </div>
      <div style={{ fontSize: 'var(--t-sm)', letterSpacing: 'var(--ls-mega)', marginTop: 5, color: 'var(--amber-deep)' }}>{caption}</div>
      <style>{'@keyframes sbx-loader-indef{0%{margin-left:-40%}100%{margin-left:100%}}'}</style>
    </div>
  );
}
