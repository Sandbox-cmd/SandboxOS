import React from 'react';

/**
 * BootCoin — a minted 3D coin (the boot token / scar-coin / achievement).
 * Dimension = ownership: use for the boot key and milestone/error rewards.
 */
export function BootCoin({ size = 120, label = 'SBX', serial = '982-V7', glyph = '▚', tone = 'amber', spin = true, style, ...props }) {
  const tones = { amber: 'var(--amber)', rebel: 'var(--magenta)', green: 'var(--green)', cyan: 'var(--cyan)' };
  const ink = tones[tone] || tones.amber;
  const faceBase = {
    position: 'absolute', inset: 0, borderRadius: '50%', display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', backfaceVisibility: 'hidden',
    background: 'radial-gradient(circle at 38% 32%, var(--hw-shell-lit), var(--hw-shell-deep) 75%)',
    border: `3px solid ${ink}`, boxShadow: `inset 0 0 ${size * 0.18}px rgba(0,0,0,0.7), 0 0 ${size * 0.14}px ${ink}`,
    color: ink, fontFamily: 'var(--font-crt)', textShadow: '0 0 8px currentColor',
  };
  return (
    <div style={{ perspective: size * 6, width: size, height: size, ...style }} {...props}>
      <style>{`@keyframes sbxcoinspin{from{transform:rotateY(0)}to{transform:rotateY(360deg)}}`}</style>
      <div
        style={{ width: '100%', height: '100%', position: 'relative', transformStyle: 'preserve-3d', animation: spin ? 'sbxcoinspin 6s linear infinite' : undefined }}
        onMouseEnter={spin ? (e) => { e.currentTarget.style.animationDuration = '1.6s'; } : undefined}
        onMouseLeave={spin ? (e) => { e.currentTarget.style.animationDuration = '6s'; } : undefined}
      >
        <div style={{ ...faceBase, transform: 'translateZ(3px)' }}>
          <span style={{ fontSize: size * 0.34, lineHeight: 1 }}>{glyph}</span>
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 900, fontSize: size * 0.16, letterSpacing: '.04em', marginTop: 2 }}>{label}</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: size * 0.075, color: 'var(--ash-400)', textShadow: 'none', marginTop: 3 }}>{serial}</span>
        </div>
        <div style={{ ...faceBase, transform: 'rotateY(180deg) translateZ(3px)' }}>
          <span style={{ fontSize: size * 0.26, lineHeight: 1 }}>✦</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: size * 0.08, color: 'var(--ash-400)', textShadow: 'none', marginTop: 4, textTransform: 'uppercase', letterSpacing: '.1em' }}>© nobody</span>
        </div>
      </div>
    </div>
  );
}
