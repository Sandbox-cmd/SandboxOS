import React from 'react';

/**
 * List — a dense vertical feed of die-cut rows. The workshop primitive for
 * runs, inventory, log lines, queues. Each row: a leading status dot or serial,
 * a mono primary label, optional faint meta, optional trailing value/action.
 *
 * Mono by the law: ink-on-void, no color required to read it. Status is a
 * SINGLE-INK dot (hollow ring → tinted ink), never a fill. Selectable rows are
 * real focusable buttons (keyboard + AT + pointer all land), the active row
 * wears one earned amber edge. Motion is a hard mechanical slide on the active
 * marker; prefers-reduced-motion shows the end-state with no travel.
 */
export function List({
  items = [],
  onSelect,
  value,
  defaultValue = null,
  dense = false,
  divided = true,
  style,
  ...rest
}) {
  const selectable = typeof onSelect === 'function';
  const [internal, setInternal] = React.useState(defaultValue);
  const sel = value !== undefined ? value : internal;

  const [reduced, setReduced] = React.useState(false);
  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => setReduced(mq.matches);
    sync();
    mq.addEventListener ? mq.addEventListener('change', sync) : mq.addListener(sync);
    return () => { mq.removeEventListener ? mq.removeEventListener('change', sync) : mq.removeListener(sync); };
  }, []);

  // single-ink status inks — dots, never fills
  const statusInk = {
    active: 'var(--amber)',
    ok:     'var(--green)',
    rebel:  'var(--magenta)',
    link:   'var(--cyan)',
    warn:   'var(--hazard)',
    danger: 'var(--alert)',
    idle:   'var(--text-faint)',
  };

  const pick = (id) => {
    if (!selectable) return;
    if (value === undefined) setInternal(id);
    onSelect(id);
  };

  // roving arrow-key movement across rows (focusable rows are real buttons)
  const onKeyDown = (e, idx) => {
    if (!selectable) return;
    const rows = e.currentTarget.parentElement?.querySelectorAll('[data-row="1"]');
    if (!rows) return;
    let next = -1;
    if (e.key === 'ArrowDown') next = Math.min(idx + 1, rows.length - 1);
    else if (e.key === 'ArrowUp') next = Math.max(idx - 1, 0);
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = rows.length - 1;
    if (next >= 0) { e.preventDefault(); rows[next].focus(); }
  };

  const rowPadV = dense ? '5px' : '9px';

  return (
    <div
      role={selectable ? 'listbox' : 'list'}
      style={{
        fontFamily: 'var(--font-mono)',
        fontSize: dense ? 'var(--t-xs)' : 'var(--t-sm)',
        color: 'var(--text)',
        background: 'var(--bg-sunken)',
        border: '2px solid var(--border)',
        borderRadius: 0,
        ...style,
      }}
      {...rest}
    >
      {items.map((it, idx) => {
        const isSel = selectable && sel != null && it.id === sel;
        const ink = statusInk[it.status] || (it.status ? 'var(--text-faint)' : null);
        const serial = it.serial != null ? String(it.serial) : null;

        const lead = (
          <span style={{ flex: 'none', width: 18, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
            {serial != null ? (
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 'var(--t-3xs)',
                color: 'var(--text-faint)', letterSpacing: 'var(--ls-normal)', fontVariantNumeric: 'tabular-nums',
              }}>{serial}</span>
            ) : ink ? (
              // single-ink status dot — hollow ring with a tinted ink core, never a fill
              <span aria-hidden="true" style={{
                width: 9, height: 9, borderRadius: 'var(--r-seal)',
                border: `2px solid ${ink}`, background: 'transparent', boxSizing: 'border-box',
              }} />
            ) : (
              <span aria-hidden="true" style={{ color: 'var(--text-faint)' }}>·</span>
            )}
          </span>
        );

        const body = (
          <span style={{ flex: '1 1 auto', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 1, textAlign: 'left' }}>
            <span style={{
              color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              fontWeight: isSel ? 700 : 400,
            }}>{it.label}</span>
            {it.meta != null && (
              <span style={{
                color: 'var(--text-faint)', fontSize: 'var(--t-3xs)',
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              }}>{it.meta}</span>
            )}
          </span>
        );

        const trailing = it.trailing != null && (
          <span style={{
            flex: 'none', color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums',
            letterSpacing: 'var(--ls-normal)', whiteSpace: 'nowrap', paddingLeft: 'var(--sp-3)',
          }}>{it.trailing}</span>
        );

        // status label for AT (the dot is decorative)
        const statusWord = it.status ? `, ${it.status}` : '';

        const inner = (
          <>
            {/* active marker — a hard amber bar that slaps into place; reduced-motion = no travel */}
            <span aria-hidden="true" style={{
              position: 'absolute', left: 0, top: 0, bottom: 0, width: 3,
              background: 'var(--amber)',
              transform: isSel ? 'scaleY(1)' : 'scaleY(0)',
              transformOrigin: 'top',
              transition: reduced ? 'none' : 'transform var(--dur-1) var(--ease-snap)',
            }} />
            {lead}
            {body}
            {trailing}
          </>
        );

        const sharedStyle = {
          position: 'relative',
          display: 'flex', alignItems: 'center', gap: 'var(--sp-2)',
          width: '100%', boxSizing: 'border-box',
          padding: `${rowPadV} var(--sp-3) ${rowPadV} var(--sp-3)`,
          borderTop: divided && idx > 0 ? '1px solid var(--border)' : 'none',
          background: isSel ? 'var(--surface-2)' : 'transparent',
          color: 'inherit', fontFamily: 'inherit', fontSize: 'inherit',
          textAlign: 'left',
        };

        if (selectable) {
          return (
            <button
              key={it.id ?? idx}
              type="button"
              data-row="1"
              role="option"
              aria-selected={isSel}
              aria-label={`${it.label}${it.meta != null ? ', ' + it.meta : ''}${statusWord}`}
              tabIndex={isSel || (sel == null && idx === 0) ? 0 : -1}
              onClick={() => pick(it.id)}
              onKeyDown={(e) => onKeyDown(e, idx)}
              style={{
                ...sharedStyle,
                border: 'none',
                cursor: 'pointer',
                outline: 'none',
                appearance: 'none',
                WebkitTapHighlightColor: 'transparent',
              }}
              onFocus={(e) => { e.currentTarget.style.boxShadow = 'inset 0 0 0 2px var(--amber)'; }}
              onBlur={(e) => { e.currentTarget.style.boxShadow = 'none'; }}
            >
              {inner}
            </button>
          );
        }

        return (
          <div
            key={it.id ?? idx}
            data-row="1"
            role="listitem"
            style={sharedStyle}
          >
            {inner}
          </div>
        );
      })}
    </div>
  );
}
