import React from 'react';

/**
 * Avatar — a die-cut frame holding the character (a kaomoji mood) or initials.
 * Optional status dot + serial. The rebel, woven in at avatar scale.
 */
export function Avatar({ face = '⌐■_■', initials, size = 44, status, serial, style, ...props }) {
  const statusColors = { online: 'var(--green)', building: 'var(--amber)', away: 'var(--ash-500)', rebel: 'var(--magenta)' };
  return (
    <span style={{ position: 'relative', display: 'inline-flex', ...style }} {...props}>
      <span style={{
        width: size, height: size, border: '2px solid var(--signal)', background: 'var(--crt-900)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: '0 0 0 3px var(--ink), 3px 3px 0 rgba(0,0,0,0.5)',
        fontFamily: initials ? 'var(--font-display)' : 'var(--font-crt)', fontWeight: 900,
        color: 'var(--magenta)', fontSize: initials ? size * 0.4 : size * 0.34,
        textShadow: '0 0 8px var(--glow-magenta)', overflow: 'hidden',
      }}>
        {initials || face}
      </span>
      {status && <span style={{ position: 'absolute', right: -3, bottom: -3, width: 12, height: 12, borderRadius: '50%', border: '2px solid var(--ink)', background: statusColors[status] || statusColors.online }} />}
      {serial && <span style={{ position: 'absolute', left: 0, bottom: -13, fontFamily: 'var(--font-mono)', fontSize: 7, color: 'var(--ash-500)', letterSpacing: '.06em', whiteSpace: 'nowrap' }}>{serial}</span>}
    </span>
  );
}
