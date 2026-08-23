import React from 'react';

/**
 * Tabs — teletext-style segmented tabs (STAT · INV · DATA). Inverted active.
 * Full ARIA tablist: role="tablist" / role="tab", roving tabIndex (only the
 * active tab is in the Tab order), Arrow/Home/End keyboard navigation, and a
 * focus-visible ring. Controlled (`value`) or uncontrolled.
 */
export function Tabs({ tabs = [], value, onChange, style, ...props }) {
  const [i, setI] = React.useState(0);
  const controlled = value != null;
  const active = controlled ? value : i;
  const refs = React.useRef([]);

  const select = (idx) => {
    if (!controlled) setI(idx);
    onChange && onChange(idx);
  };

  const onKeyDown = (e) => {
    const last = tabs.length - 1;
    let next = null;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = active >= last ? 0 : active + 1;
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = active <= 0 ? last : active - 1;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = last;
    if (next == null) return;
    e.preventDefault();
    select(next);
    const el = refs.current[next];
    el && el.focus();
  };

  return (
    <div
      role="tablist"
      onKeyDown={onKeyDown}
      className="ds-tablist"
      style={{
        display: 'flex', borderBottom: '2px solid var(--signal)',
        fontFamily: 'var(--font-mono)', fontSize: 'var(--t-xs)', ...style,
      }}
      {...props}
    >
      {tabs.map((t, idx) => {
        const is = idx === active;
        return (
          <button
            key={idx}
            ref={(el) => { refs.current[idx] = el; }}
            type="button"
            role="tab"
            aria-selected={is}
            tabIndex={is ? 0 : -1}
            onClick={() => select(idx)}
            style={{
              padding: '5px 13px', border: 0, cursor: 'pointer', textTransform: 'uppercase',
              letterSpacing: 'var(--ls-wide)', fontFamily: 'inherit', fontSize: 'inherit',
              fontWeight: is ? 700 : 400,
              background: is ? 'var(--signal)' : 'transparent',
              color: is ? 'var(--ink)' : 'var(--text-dim)',
            }}
          >
            {t}
          </button>
        );
      })}
      <style>{`
        .ds-tablist > [role="tab"] { outline: none; }
        .ds-tablist > [role="tab"]:focus-visible {
          outline: 2px solid var(--amber);
          outline-offset: -2px;
        }
      `}</style>
    </div>
  );
}
