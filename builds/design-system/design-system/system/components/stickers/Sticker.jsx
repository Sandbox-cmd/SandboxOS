import React from 'react';

/**
 * Sticker — the SandboxOS die-cut sticker system. Usable as UI (callouts,
 * awards, badges) AND as decoration. Many shapes; loud earned color.
 */
export function Sticker({
  children,
  shape = 'tag',
  tone = 'hazard',
  rotate = -4,
  halo = true,
  size = 'md',
  style,
  ...props
}) {
  const tones = {
    hazard:  { bg: 'var(--hazard)',  fg: 'var(--ink)' },
    alert:   { bg: 'var(--alert)',   fg: 'var(--signal)' },
    rebel:   { bg: 'var(--magenta)', fg: 'var(--signal)' },
    go:      { bg: 'var(--green)',   fg: 'var(--ink)' },
    cyan:    { bg: 'var(--cyan)',    fg: 'var(--ink)' },
    ink:     { bg: 'var(--ink)',     fg: 'var(--signal)' },
    paper:   { bg: 'var(--signal)',  fg: 'var(--ink)' },
  };
  const t = tones[tone] || tones.hazard;
  const fs = size === 'sm' ? 'var(--t-xs)' : size === 'lg' ? 'var(--t-xl)' : 'var(--t-md)';
  const base = {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
    fontFamily: 'var(--font-display)', fontWeight: 900, textTransform: 'uppercase',
    letterSpacing: 'var(--ls-wide)', lineHeight: 0.95,
    color: t.fg, background: t.bg,
    border: '2px solid var(--ink)',
    boxShadow: halo ? '0 0 0 3px var(--signal), 3px 4px 0 rgba(0,0,0,0.5)' : '3px 4px 0 rgba(0,0,0,0.5)',
    transform: `rotate(${rotate}deg)`,
  };
  const shapes = {
    tag:    { padding: '6px 13px', borderRadius: 0, fontSize: fs },
    pill:   { padding: '6px 16px', borderRadius: '999px', fontSize: fs },
    seal:   { width: '78px', height: '78px', borderRadius: '50%', fontSize: 'var(--t-xs)', padding: '4px' },
    burst:  { padding: '12px 16px', borderRadius: 0, fontSize: fs,
              clipPath: 'polygon(50% 0,63% 12%,80% 6%,82% 24%,100% 28%,90% 44%,100% 62%,82% 66%,78% 86%,60% 80%,50% 100%,40% 80%,22% 86%,18% 66%,0 62%,10% 44%,0 28%,18% 24%,20% 6%,37% 12%)' },
    ribbon: { padding: '6px 22px', borderRadius: 0, fontSize: fs,
              clipPath: 'polygon(0 0,100% 0,92% 50%,100% 100%,0 100%,8% 50%)' },
    price:  { padding: '6px 13px 6px 20px', borderRadius: 0, fontSize: fs,
              clipPath: 'polygon(13% 0,100% 0,100% 100%,13% 100%,0 50%)' },
    callout:{ padding: '8px 14px 16px', borderRadius: 0, fontSize: fs,
              clipPath: 'polygon(0 0,100% 0,100% 72%,34% 72%,22% 100%,18% 72%,0 72%)' },
    stamp:  { width: '82px', height: '82px', borderRadius: '50%', fontSize: 'var(--t-xs)', padding: '6px' },
  };
  // hazard-striped variant when tone is 'striped'
  const striped = tone === 'striped'
    ? { background: 'repeating-linear-gradient(45deg, var(--hazard) 0 12px, var(--ink) 12px 24px)', color: 'var(--ink)' }
    : null;
  // stamp = inked outline (postmark), tone becomes the ink color
  const stamp = shape === 'stamp'
    ? { background: 'transparent', color: t.bg, border: `2px double ${t.bg}`, boxShadow: 'none', opacity: 0.92 }
    : null;

  return (
    <span style={{ ...base, ...(shapes[shape] || shapes.tag), ...striped, ...stamp, ...style }} {...props}>
      {(shape === 'burst' || striped) ? <span style={{ background: 'var(--signal)', padding: '1px 6px' }}>{children}</span> : children}
    </span>
  );
}

/** Barcode — procedural; a brand provenance mark. */
export function Barcode({ height = 26, seed = '982V7', color = 'var(--signal)', style, ...props }) {
  const bars = React.useMemo(() => {
    let h = 7; const out = [];
    for (let i = 0; i < 26; i++) { h = (h * 31 + seed.charCodeAt(i % seed.length)) % 97; out.push(1 + (h % 4)); }
    return out;
  }, [seed]);
  return (
    <span style={{ display: 'inline-flex', gap: '2px', alignItems: 'stretch', height, color, ...style }} {...props}>
      {bars.map((w, i) => <span key={i} style={{ width: w, background: i % 2 ? 'currentColor' : 'transparent' }} />)}
    </span>
  );
}
