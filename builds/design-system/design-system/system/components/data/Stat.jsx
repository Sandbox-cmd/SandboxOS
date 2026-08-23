import React from 'react';

/* reduced-motion check, recomputed live (no calendar, only state) */
function useReducedMotion() {
  const [reduced, setReduced] = React.useState(false);
  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const apply = () => setReduced(!!mq.matches);
    apply();
    mq.addEventListener ? mq.addEventListener('change', apply) : mq.addListener(apply);
    return () => { mq.removeEventListener ? mq.removeEventListener('change', apply) : mq.removeListener(apply); };
  }, []);
  return reduced;
}

const TONES = {
  default: 'var(--text)',
  active:  'var(--amber)',
  rebel:   'var(--magenta)',
  ok:      'var(--green)',
  link:    'var(--cyan)',
};

/**
 * Stat — a workshop metric tile. Big brutalist display number on void,
 * uppercase mono label, optional unit, optional delta with a single-ink
 * up/down mark. Mono by default; ONE earned accent via `tone`. Die-cut:
 * 0px radius, 2px border, hard offset shadow, no soft blur.
 */
export function Stat({
  label,
  value,
  unit,
  delta,
  tone = 'default',
  style,
  ...rest
}) {
  const reduced = useReducedMotion();
  const accent = TONES[tone] || TONES.default;

  // delta: number → signed; string passes through. up = good (green-ink),
  // down = warn (alert-ink). Single-ink marks, never fills.
  let dDir = 0; // 1 up, -1 down, 0 flat
  if (typeof delta === 'number') dDir = delta > 0 ? 1 : delta < 0 ? -1 : 0;
  else if (typeof delta === 'string') dDir = /^-/.test(delta.trim()) ? -1 : /^\+/.test(delta.trim()) ? 1 : 0;

  const dMark = dDir > 0 ? '▲' : dDir < 0 ? '▼' : '—'; // ▲ ▼ —
  const dInk  = dDir > 0 ? 'var(--green)' : dDir < 0 ? 'var(--alert)' : 'var(--text-faint)';
  const dText = typeof delta === 'number'
    ? (delta > 0 ? '+' : '') + delta
    : delta;

  return (
    <div
      style={{
        display: 'inline-flex',
        flexDirection: 'column',
        gap: 6,
        minWidth: 132,
        padding: '14px 16px 13px',
        background: 'var(--bg-sunken)',
        border: '2px solid var(--border-ink)',
        borderRadius: 0,
        boxShadow: '3px 3px 0 var(--ink)',
        boxSizing: 'border-box',
        ...style,
      }}
      {...rest}
    >
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--t-3xs)',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: 'var(--ls-wide)',
        color: 'var(--text-faint)',
        lineHeight: 1,
        whiteSpace: 'nowrap',
      }}>
        {label}
      </span>

      <span style={{ display: 'flex', alignItems: 'baseline', gap: 5, lineHeight: 'var(--lh-tight)' }}>
        <span style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 900,
          fontSize: 'var(--t-3xl)',
          letterSpacing: 'var(--ls-tight)',
          color: accent,
          fontVariantNumeric: 'tabular-nums',
          textShadow: tone !== 'default' ? '0 0 8px currentColor' : 'none',
        }}>
          {value}
        </span>
        {unit != null && unit !== '' && (
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 'var(--t-sm)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: 'var(--ls-wide)',
            color: 'var(--text-dim)',
          }}>
            {unit}
          </span>
        )}
      </span>

      {delta != null && delta !== '' && (
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 5,
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--t-xs)',
          fontWeight: 700,
          letterSpacing: 'var(--ls-normal)',
          color: dInk,
          lineHeight: 1,
        }}>
          <span aria-hidden="true" style={{ fontSize: 9, transform: reduced ? 'none' : 'translateY(0.5px)' }}>{dMark}</span>
          <span>{dText}</span>
        </span>
      )}
    </div>
  );
}

/**
 * KeyValue — a tight mono definition list: key → value rows, hairline-
 * separated, dense. The see-the-parts surface for a small spec of facts.
 * Renders a real <dl>/<dt>/<dd> so it is a definition list to assistive tech.
 */
export function KeyValue({
  pairs = [],
  dense = false,
  align = 'right',
  style,
  ...rest
}) {
  const rows = Array.isArray(pairs) ? pairs : [];
  const padY = dense ? 4 : 7;

  return (
    <dl
      style={{
        margin: 0,
        display: 'grid',
        gridTemplateColumns: 'max-content 1fr',
        columnGap: 14,
        rowGap: 0,
        fontFamily: 'var(--font-mono)',
        fontSize: dense ? 'var(--t-xs)' : 'var(--t-sm)',
        lineHeight: 'var(--lh-mono)',
        border: '2px solid var(--border-ink)',
        borderRadius: 0,
        background: 'var(--bg-sunken)',
        boxShadow: '3px 3px 0 var(--ink)',
        boxSizing: 'border-box',
        ...style,
      }}
      {...rest}
    >
      {rows.map((p, i) => {
        const last = i === rows.length - 1;
        const line = last ? 'none' : '1px solid var(--border)';
        return (
          <React.Fragment key={i}>
            <dt style={{
              padding: `${padY}px 0 ${padY}px 12px`,
              borderBottom: line,
              color: 'var(--text-faint)',
              textTransform: 'uppercase',
              letterSpacing: 'var(--ls-wide)',
              fontSize: 'var(--t-3xs)',
              fontWeight: 700,
              whiteSpace: 'nowrap',
              alignSelf: 'center',
            }}>
              {p.k}
            </dt>
            <dd style={{
              margin: 0,
              padding: `${padY}px 12px ${padY}px 0`,
              borderBottom: line,
              color: 'var(--text)',
              textAlign: align,
              fontVariantNumeric: 'tabular-nums',
              alignSelf: 'center',
              overflowWrap: 'anywhere',
            }}>
              {p.v}
            </dd>
          </React.Fragment>
        );
      })}
    </dl>
  );
}
