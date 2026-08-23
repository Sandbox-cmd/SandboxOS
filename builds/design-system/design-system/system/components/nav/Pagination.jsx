import React from 'react';

/**
 * Pagination — a brutalist pager. Numbered slaps (001/002), prev/next with
 * unicode marks, the current page is the one earned accent. Mono, die-cut,
 * 0px radius, hard offset shadow. Snappy slap-down on press; honors
 * prefers-reduced-motion (end-state shown, motion skipped).
 *
 * Controlled (`page`) + uncontrolled (`defaultPage`). Real <button>s,
 * aria-label per page, aria-current on the active page, prev/next disabled
 * at the ends, focus-visible ring via focus-within.
 */
export function Pagination({
  page,
  defaultPage = 1,
  pageCount,
  onChange,
  siblingCount = 1,
  accent = 'var(--amber)',
  accentEdge = 'var(--amber-deep)',
  style,
  ...rest
}) {
  const [inner, setInner] = React.useState(defaultPage);
  const current = page != null ? page : inner;
  const count = Math.max(1, pageCount | 0);
  const reduce = usePrefersReducedMotion();

  const go = (next) => {
    const n = clamp(next, 1, count);
    if (n === current) return;
    if (page == null) setInner(n);
    onChange && onChange(n);
  };

  const items = buildRange(current, count, Math.max(0, siblingCount | 0));
  const atStart = current <= 1;
  const atEnd = current >= count;

  return (
    <nav
      role="navigation"
      aria-label="Pagination"
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        fontFamily: 'var(--font-mono)', ...style,
      }}
      {...rest}
    >
      <Slap
        kind="edge"
        reduce={reduce}
        disabled={atStart}
        ariaLabel="Previous page"
        onActivate={() => go(current - 1)}
      >
        {'◀'}
      </Slap>

      {items.map((it, i) =>
        it === GAP ? (
          <span
            key={`gap-${i}`}
            aria-hidden="true"
            style={{
              minWidth: 16, textAlign: 'center', color: 'var(--text-faint)',
              fontFamily: 'var(--font-crt)', fontSize: 'var(--t-md)',
              letterSpacing: 'var(--ls-wide)', userSelect: 'none',
            }}
          >
            {'•••'}
          </span>
        ) : (
          <Slap
            key={it}
            kind="page"
            reduce={reduce}
            active={it === current}
            accent={accent}
            accentEdge={accentEdge}
            ariaLabel={`Page ${it} of ${count}`}
            ariaCurrent={it === current ? 'page' : undefined}
            onActivate={() => go(it)}
          >
            {pad(it)}
          </Slap>
        )
      )}

      <Slap
        kind="edge"
        reduce={reduce}
        disabled={atEnd}
        ariaLabel="Next page"
        onActivate={() => go(current + 1)}
      >
        {'▶'}
      </Slap>
    </nav>
  );
}

/* ---- one numbered/edge slap ----------------------------------------- */
function Slap({
  kind, children, active = false, disabled = false,
  ariaLabel, ariaCurrent, onActivate, reduce,
  accent = 'var(--amber)', accentEdge = 'var(--amber-deep)',
}) {
  const [hover, setHover] = React.useState(false);
  const [press, setPress] = React.useState(false);

  // resting die-cut offset; mechanical slap-down on press.
  const base = 3;
  const off = disabled ? base : press ? 0 : hover ? base - 1 : base;
  const shift = reduce ? 0 : base - off;

  const isEdge = kind === 'edge';
  const bg = active ? accent : 'var(--bg-sunken)';
  const fg = active ? 'var(--ink)' : disabled ? 'var(--text-faint)' : 'var(--text)';
  const edge = active ? 'var(--ink)' : 'var(--signal)';
  const shadow = active ? accentEdge : 'var(--ink)';

  return (
    <button
      type="button"
      disabled={disabled}
      aria-label={ariaLabel}
      aria-current={ariaCurrent}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => { setHover(false); setPress(false); }}
      onMouseDown={() => setPress(true)}
      onMouseUp={() => setPress(false)}
      onClick={onActivate}
      style={{
        appearance: 'none',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        minWidth: isEdge ? 30 : 38, height: 30, padding: isEdge ? '0 6px' : '0 8px',
        fontFamily: isEdge ? 'var(--font-crt)' : 'var(--font-mono)',
        fontWeight: 700,
        fontSize: isEdge ? 'var(--t-md)' : 'var(--t-sm)',
        letterSpacing: isEdge ? 'var(--ls-normal)' : 'var(--ls-wide)',
        lineHeight: 1,
        color: fg,
        background: bg,
        border: `2px solid ${edge}`,
        borderRadius: 0,
        boxShadow: disabled ? 'none' : `${off}px ${off}px 0 ${shadow}`,
        transform: `translate(${shift}px, ${shift}px)`,
        transition: reduce
          ? 'none'
          : 'box-shadow var(--dur-1) var(--ease-snap), transform var(--dur-1) var(--ease-snap)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.4 : 1,
        outline: 'none',
        userSelect: 'none',
      }}
      onFocus={(e) => {
        e.currentTarget.style.boxShadow =
          (disabled ? 'none ' : `${off}px ${off}px 0 ${shadow}, `) +
          `0 0 0 2px var(--bg), 0 0 0 4px var(--cyan)`;
      }}
      onBlur={(e) => {
        e.currentTarget.style.boxShadow = disabled ? 'none' : `${off}px ${off}px 0 ${shadow}`;
      }}
    >
      {children}
    </button>
  );
}

/* ---- prefers-reduced-motion (law 4) --------------------------------- */
function usePrefersReducedMotion() {
  const [reduce, setReduce] = React.useState(false);
  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const on = () => setReduce(!!mq.matches);
    on();
    mq.addEventListener ? mq.addEventListener('change', on) : mq.addListener(on);
    return () => {
      mq.removeEventListener ? mq.removeEventListener('change', on) : mq.removeListener(on);
    };
  }, []);
  return reduce;
}

/* ---- range math ----------------------------------------------------- */
const GAP = 'gap';

function buildRange(current, count, siblings) {
  // first + last always shown; window of `siblings` either side of current.
  const total = siblings * 2 + 5; // first, last, current, 2 gaps, 2*siblings
  if (count <= total) return seq(1, count);

  const left = Math.max(current - siblings, 1);
  const right = Math.min(current + siblings, count);
  const showLeftGap = left > 2;
  const showRightGap = right < count - 1;

  const out = [1];
  if (showLeftGap) out.push(GAP);
  else for (let n = 2; n < left; n++) out.push(n);
  for (let n = left; n <= right; n++) if (n !== 1 && n !== count) out.push(n);
  if (showRightGap) out.push(GAP);
  else for (let n = right + 1; n < count; n++) out.push(n);
  out.push(count);
  return out;
}

function seq(a, b) {
  const r = [];
  for (let n = a; n <= b; n++) r.push(n);
  return r;
}
function clamp(n, lo, hi) { return Math.min(hi, Math.max(lo, n)); }
function pad(n) { return String(n).padStart(3, '0'); }
