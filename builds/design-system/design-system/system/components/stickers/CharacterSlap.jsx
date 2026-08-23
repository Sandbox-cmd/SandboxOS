import React from 'react';

/**
 * CharacterSlap — a posed die-cut character mood badge. The rebel's slaps:
 * a kaomoji + a line in her voice. Usable as award, callout, easter-egg.
 */
export function CharacterSlap({ face = '⌐■_■', label = "nobody's tool", tone = 'rebel', rotate = -5, style, ...props }) {
  const tones = {
    rebel: { bg: 'var(--ink)', face: 'var(--magenta)', label: 'var(--signal)' },
    cool:  { bg: 'var(--signal)', face: 'var(--blue)', label: 'var(--ink)' },
    go:    { bg: 'var(--ink)', face: 'var(--cyan)', label: 'var(--signal)' },
    hazard:{ bg: 'var(--hazard)', face: 'var(--ink)', label: 'var(--ink)' },
  };
  const t = tones[tone] || tones.rebel;
  return (
    <span style={{
      display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: 3,
      background: t.bg, border: '2px solid var(--ink)', padding: '8px 10px 5px', minWidth: 78,
      boxShadow: '0 0 0 3px var(--signal), 3px 3px 0 rgba(0,0,0,0.5)', transform: `rotate(${rotate}deg)`, ...style,
    }} {...props}>
      <span style={{ fontFamily: 'var(--font-crt)', fontSize: 'var(--t-lg)', lineHeight: 1, color: t.face, textShadow: tone === 'cool' ? 'none' : '0 0 8px currentColor' }}>{face}</span>
      <span style={{ fontFamily: 'var(--font-display)', fontWeight: 900, fontSize: 9, textTransform: 'uppercase', letterSpacing: '.02em', textAlign: 'center', color: t.label }}>{label}</span>
    </span>
  );
}
