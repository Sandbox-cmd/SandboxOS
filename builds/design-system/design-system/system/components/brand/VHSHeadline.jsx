import React from 'react';

/**
 * VHSHeadline — the poster voice as a component. Archivo Black, uppercase,
 * hard offset shadow, RGB chromatic-aberration split + a tracking jitter.
 * Words flagged `liveWords` glow in the earned accent. Lines rise on mount.
 * Reduced-motion safe (shows the settled end-state).
 */
export function VHSHeadline({ children, size = 'xl', align = 'left', liveWords = [], accent = 'var(--magenta)', split = true, shadow = true, style, ...rest }) {
  const sizes = {
    lg:   { fs: 'clamp(34px,6vw,52px)', sh: '4px 4px 0 #000' },
    xl:   { fs: 'clamp(44px,8vw,76px)', sh: '5px 5px 0 #000' },
    '2xl':{ fs: 'clamp(56px,11vw,104px)', sh: '6px 6px 0 #000' },
  };
  const s = sizes[size] || sizes.xl;
  // robustly flatten children to text (string | number | array | element) → kills [object Object]
  const flat = (n) => (n == null || n === false || n === true) ? '' :
    (typeof n === 'string' || typeof n === 'number') ? String(n) :
    Array.isArray(n) ? n.map(flat).join('') :
    (n.props && n.props.children != null) ? flat(n.props.children) : '';
  const text = flat(children);
  const lines = text.split(/\s*\/\s*|\n/).map(l => l.trim()).filter(Boolean);
  const live = new Set(liveWords.map(w => w.toLowerCase()));
  const wrap = {
    margin: 0, textAlign: align, font: `900 ${s.fs}/0.9 var(--font-display)`,
    letterSpacing: '-0.03em', textTransform: 'uppercase', color: 'var(--signal)',
    textShadow: split ? `-3px 0 var(--magenta), 3px 0 var(--cyan)${shadow ? ', ' + s.sh : ''}` : (shadow ? s.sh : 'none'),
    ...style,
  };
  return (
    <h2 style={wrap} {...rest}>
      {lines.map((line, li) => (
        <span key={li} style={{ display: 'block', overflow: 'hidden' }}>
          <span style={{ display: 'inline-block', animation: 'sbx-vhs-rise var(--dur-3) var(--ease-out) both', animationDelay: (li * 0.08) + 's' }}>
            {line.split(' ').map((word, wi, arr) => {
              const on = live.has(word.toLowerCase().replace(/[.,!?]/g, ''));
              return (
                <React.Fragment key={wi}>
                  <span style={on ? { color: accent, textShadow: `0 0 12px ${accent}` } : undefined}>{word}</span>
                  {wi < arr.length - 1 ? ' ' : ''}
                </React.Fragment>
              );
            })}
          </span>
        </span>
      ))}
      <style>{`@keyframes sbx-vhs-rise{from{transform:translateY(108%)}to{transform:translateY(0)}}
      @media (prefers-reduced-motion:reduce){h2 [style*="sbx-vhs-rise"]{animation:none!important}}`}</style>
    </h2>
  );
}
