import React from 'react';

/**
 * Nav — the workbench side navigation: a die-cut control rail.
 *
 * Sections carry an uppercase mono group label; each item is a flat row. The
 * active item is the ONE earned accent in the view — a left die-cut bar plus
 * brand-ink text. Items can carry a leading mark (a CRT/pixel unicode glyph,
 * never emoji) and a trailing count. Mono base, hard 0px radius, 2px die-cut
 * edges. Keyboard-driven (Arrow Up/Down roves, Enter/Space selects), real
 * <nav> landmark, aria-current on the live item.
 */
const REDUCED =
  typeof window !== 'undefined' && window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : null;

function useReducedMotion() {
  const [reduced, setReduced] = React.useState(REDUCED ? REDUCED.matches : false);
  React.useEffect(() => {
    if (!REDUCED) return;
    const on = () => setReduced(REDUCED.matches);
    REDUCED.addEventListener ? REDUCED.addEventListener('change', on) : REDUCED.addListener(on);
    return () =>
      REDUCED.removeEventListener ? REDUCED.removeEventListener('change', on) : REDUCED.removeListener(on);
  }, []);
  return reduced;
}

export function Nav({
  sections = [],
  activeId,
  onSelect,
  collapsed = false,
  accent = 'var(--amber)',
  ariaLabel = 'Workbench',
  style,
  ...rest
}) {
  const reduced = useReducedMotion();

  // Flat ordered list of selectable item ids — the keyboard roving order.
  const flat = React.useMemo(() => {
    const out = [];
    sections.forEach((sec) => (sec.items || []).forEach((it) => out.push(it)));
    return out;
  }, [sections]);

  // Roving tabindex focus: track the focused row independent of the active row.
  const startIndex = Math.max(0, flat.findIndex((it) => it.id === activeId));
  const [focusIndex, setFocusIndex] = React.useState(startIndex === -1 ? 0 : startIndex);
  const itemRefs = React.useRef({});

  React.useEffect(() => {
    const i = flat.findIndex((it) => it.id === activeId);
    if (i >= 0) setFocusIndex(i);
  }, [activeId, flat]);

  const focusRow = (i) => {
    const clamped = (i + flat.length) % flat.length;
    setFocusIndex(clamped);
    const el = itemRefs.current[flat[clamped] && flat[clamped].id];
    if (el) el.focus();
  };

  const onKeyDown = (e, idx) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        focusRow(idx + 1);
        break;
      case 'ArrowUp':
        e.preventDefault();
        focusRow(idx - 1);
        break;
      case 'Home':
        e.preventDefault();
        focusRow(0);
        break;
      case 'End':
        e.preventDefault();
        focusRow(flat.length - 1);
        break;
      case 'Enter':
      case ' ':
        e.preventDefault();
        onSelect && onSelect(flat[idx].id);
        break;
      default:
        break;
    }
  };

  const trans = reduced
    ? 'none'
    : 'background var(--dur-1) var(--ease-snap), color var(--dur-1) var(--ease-snap)';

  return (
    <nav
      aria-label={ariaLabel}
      style={{
        boxSizing: 'border-box',
        width: collapsed ? 60 : 232,
        background: 'var(--bg-sunken)',
        border: '2px solid var(--ink)',
        boxShadow: 'var(--shadow-slap)',
        fontFamily: 'var(--font-mono)',
        color: 'var(--text)',
        padding: '10px 0',
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
        userSelect: 'none',
        ...style,
      }}
      {...rest}
    >
      {sections.map((sec, si) => (
        <div key={sec.label || si} role="group" aria-label={sec.label}>
          {/* GROUP LABEL — uppercase mono, hidden visually when collapsed but kept for AT */}
          {sec.label ? (
            <div
              aria-hidden={collapsed ? true : undefined}
              style={{
                fontSize: 'var(--t-3xs)',
                letterSpacing: 'var(--ls-mega)',
                textTransform: 'uppercase',
                color: 'var(--text-faint)',
                padding: collapsed ? '0 0 6px' : '0 14px 6px',
                textAlign: collapsed ? 'center' : 'left',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
              }}
            >
              {collapsed ? '·' : sec.label}
            </div>
          ) : null}

          {(sec.items || []).map((it) => {
            const idx = flat.findIndex((f) => f.id === it.id);
            const isActive = it.id === activeId;
            const isFocusTarget = idx === focusIndex;
            return (
              <button
                key={it.id}
                type="button"
                ref={(el) => (itemRefs.current[it.id] = el)}
                onClick={() => onSelect && onSelect(it.id)}
                onKeyDown={(e) => onKeyDown(e, idx)}
                onMouseEnter={(e) => {
                  if (!isActive) e.currentTarget.style.background = 'var(--surface-2)';
                }}
                onMouseLeave={(e) => {
                  if (!isActive) e.currentTarget.style.background = 'transparent';
                }}
                aria-current={isActive ? 'page' : undefined}
                title={collapsed ? it.label : undefined}
                tabIndex={isFocusTarget ? 0 : -1}
                style={{
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                  gap: collapsed ? 0 : 10,
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  width: '100%',
                  boxSizing: 'border-box',
                  // left die-cut bar carries the earned accent on the active row
                  borderLeft: `4px solid ${isActive ? accent : 'transparent'}`,
                  borderTop: 'none',
                  borderRight: 'none',
                  borderBottom: 'none',
                  borderRadius: 0,
                  background: isActive ? 'var(--surface)' : 'transparent',
                  color: isActive ? accent : 'var(--text-dim)',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: isActive ? 'var(--w-bold)' : 'var(--w-regular)',
                  fontSize: 'var(--t-sm)',
                  letterSpacing: 'var(--ls-wide)',
                  textAlign: 'left',
                  padding: collapsed ? '8px 0' : '7px 14px 7px 12px',
                  margin: 0,
                  cursor: 'pointer',
                  outline: 'none',
                  transition: trans,
                }}
                onFocus={(e) => {
                  e.currentTarget.style.outline = '2px solid var(--cyan)';
                  e.currentTarget.style.outlineOffset = '-2px';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.outline = 'none';
                  if (!isActive) e.currentTarget.style.background = 'transparent';
                }}
              >
                {/* leading mark — CRT glyph slot, fixed width so labels align */}
                {it.mark ? (
                  <span
                    aria-hidden="true"
                    style={{
                      flex: 'none',
                      width: 16,
                      textAlign: 'center',
                      fontFamily: 'var(--font-crt)',
                      fontSize: 'var(--t-md)',
                      lineHeight: 1,
                      color: isActive ? accent : 'var(--text-faint)',
                    }}
                  >
                    {it.mark}
                  </span>
                ) : null}

                {!collapsed && (
                  <span
                    style={{
                      flex: '1 1 auto',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {it.label}
                  </span>
                )}

                {/* trailing count — single-ink mono numeral, never a fill */}
                {!collapsed && it.count != null ? (
                  <span
                    aria-hidden="true"
                    style={{
                      flex: 'none',
                      fontFamily: 'var(--font-mono)',
                      fontSize: 'var(--t-2xs)',
                      letterSpacing: 'var(--ls-normal)',
                      color: isActive ? accent : 'var(--text-faint)',
                      border: `2px solid ${isActive ? accent : 'var(--border)'}`,
                      borderRadius: 0,
                      padding: '0 5px',
                      minWidth: 16,
                      textAlign: 'center',
                    }}
                  >
                    {it.count}
                  </span>
                ) : null}

                {/* collapsed: surface the count to AT since label/badge are hidden */}
                {collapsed && it.count != null ? (
                  <span
                    style={{
                      position: 'absolute',
                      width: 1,
                      height: 1,
                      padding: 0,
                      margin: -1,
                      overflow: 'hidden',
                      clip: 'rect(0 0 0 0)',
                      whiteSpace: 'nowrap',
                      border: 0,
                    }}
                  >
                    {it.label} — {it.count}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
