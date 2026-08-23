import React from 'react';

/**
 * Menu — a die-cut dropdown / context menu: a slap that popped up.
 * Hard 2px border, hard offset shadow (no soft blur), 0px radius, mono items.
 * Each item may carry a leading mark + trailing shortcut; hairline rules
 * between groups; a `danger` item burns single-ink, never a fill.
 *
 * A11y: role="menu" / role="menuitem", Arrow/Home/End/Enter/Esc keyboard,
 * focus trapped to the items while open, focus restored to the opener on close.
 * Motion is a single snap-down popping into place — honoured against
 * prefers-reduced-motion (end-state shown, motion skipped).
 */
export function Menu({
  items = [],
  onSelect,
  open = true,
  onClose,
  anchor = 'bottom-left',
  label = 'menu',
  style,
  ...rest
}) {
  const listRef = React.useRef(null);
  const itemRefs = React.useRef([]);
  const restoreRef = React.useRef(null);
  const [active, setActive] = React.useState(-1);
  const [mounted, setMounted] = React.useState(false);

  // reduced-motion: resolve once, react to OS changes.
  const [reduced, setReduced] = React.useState(false);
  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => setReduced(mq.matches);
    sync();
    mq.addEventListener ? mq.addEventListener('change', sync) : mq.addListener(sync);
    return () => { mq.removeEventListener ? mq.removeEventListener('change', sync) : mq.removeListener(sync); };
  }, []);

  // indices of the items that can actually take focus (skip separators + disabled).
  const focusable = React.useMemo(
    () => items.map((it, i) => ({ it, i })).filter(({ it }) => it && !it.separator && !it.disabled).map(({ i }) => i),
    [items]
  );

  const focusAt = React.useCallback((idx) => {
    setActive(idx);
    const el = itemRefs.current[idx];
    if (el) el.focus();
  }, []);

  const step = React.useCallback((dir) => {
    if (!focusable.length) return;
    const pos = focusable.indexOf(active);
    let next;
    if (pos === -1) next = dir > 0 ? focusable[0] : focusable[focusable.length - 1];
    else next = focusable[(pos + dir + focusable.length) % focusable.length];
    focusAt(next);
  }, [focusable, active, focusAt]);

  // open: remember opener, snap focus to first item, raise the slap.
  React.useEffect(() => {
    if (!open) { setMounted(false); return; }
    restoreRef.current = (typeof document !== 'undefined') ? document.activeElement : null;
    setMounted(true);
    if (focusable.length) focusAt(focusable[0]);
    else if (listRef.current) listRef.current.focus();
    // restore focus to opener on close.
    return () => {
      const el = restoreRef.current;
      if (el && typeof el.focus === 'function') el.focus();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // outside-click / outside-intent dismissal while open
  React.useEffect(() => {
    if (!open) return;
    const onDocPointer = (e) => {
      if (listRef.current && !listRef.current.contains(e.target)) onClose && onClose();
    };
    document.addEventListener('pointerdown', onDocPointer, true);
    return () => document.removeEventListener('pointerdown', onDocPointer, true);
  }, [open, onClose]);

  const choose = React.useCallback((it) => {
    if (!it || it.disabled || it.separator) return;
    onSelect && onSelect(it.id, it);
    onClose && onClose();
  }, [onSelect, onClose]);

  const onKeyDown = (e) => {
    switch (e.key) {
      case 'ArrowDown': e.preventDefault(); step(1); break;
      case 'ArrowUp':   e.preventDefault(); step(-1); break;
      case 'Home':      e.preventDefault(); focusable.length && focusAt(focusable[0]); break;
      case 'End':       e.preventDefault(); focusable.length && focusAt(focusable[focusable.length - 1]); break;
      case 'Tab':
        // trap focus: keep it on the menu, wrap with arrow semantics.
        e.preventDefault();
        step(e.shiftKey ? -1 : 1);
        break;
      case 'Enter':
      case ' ':
        e.preventDefault();
        if (active >= 0) choose(items[active]);
        break;
      case 'Escape':
        e.preventDefault();
        onClose && onClose();
        break;
      default: break;
    }
  };

  if (!open) return null;

  // anchored placement — corner the slap pops from.
  const anchors = {
    'bottom-left':  { top: '100%', left: 0,  marginTop: 6 },
    'bottom-right': { top: '100%', right: 0, marginTop: 6 },
    'top-left':     { bottom: '100%', left: 0,  marginBottom: 6 },
    'top-right':    { bottom: '100%', right: 0, marginBottom: 6 },
  };
  const place = anchors[anchor] || anchors['bottom-left'];
  // pop direction follows the anchor edge.
  const fromTop = anchor.indexOf('bottom') === 0;
  const popFrom = fromTop ? 'translateY(-6px)' : 'translateY(6px)';

  return (
    <div
      ref={listRef}
      role="menu"
      aria-label={label}
      aria-orientation="vertical"
      tabIndex={-1}
      onKeyDown={onKeyDown}
      style={{
        position: 'absolute',
        zIndex: 'var(--z-overlay, 1000)',
        minWidth: 200,
        background: 'var(--bg-raised)',
        color: 'var(--text)',
        border: '2px solid var(--ink)',
        borderRadius: 0,
        boxShadow: 'var(--shadow-slap-lg)',
        padding: '4px 0',
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--t-sm)',
        userSelect: 'none',
        opacity: mounted || reduced ? 1 : 0,
        transform: mounted || reduced ? 'translateY(0)' : popFrom,
        transition: reduced ? 'none' : 'opacity var(--dur-1) var(--ease-snap), transform var(--dur-1) var(--ease-snap)',
        ...place,
        ...style,
      }}
      {...rest}
    >
      {items.map((it, i) => {
        if (!it) return null;
        if (it.separator) {
          return (
            <div
              key={it.id || `sep-${i}`}
              role="separator"
              aria-hidden="true"
              style={{ height: 0, borderTop: '1px solid var(--border)', margin: '4px 0' }}
            />
          );
        }
        const isActive = active === i;
        const isDanger = !!it.danger;
        const isDisabled = !!it.disabled;
        const fg = isDisabled
          ? 'var(--text-faint)'
          : isDanger
            ? 'var(--danger)'
            : isActive ? 'var(--ink)' : 'var(--text)';
        return (
          <MenuRow
            key={it.id || `item-${i}`}
            ref={(el) => { itemRefs.current[i] = el; }}
            item={it}
            active={isActive}
            danger={isDanger}
            disabled={isDisabled}
            fg={fg}
            reduced={reduced}
            onMouseEnter={() => !isDisabled && setActive(i)}
            onClick={() => choose(it)}
          />
        );
      })}
    </div>
  );
}

const MenuRow = React.forwardRef(function MenuRow(
  { item, active, danger, disabled, fg, reduced, onMouseEnter, onClick },
  ref
) {
  // active background: amber for the live row, magenta-edged for danger — single accent per row.
  const bg = active && !disabled
    ? (danger ? 'var(--surface-2)' : 'var(--amber)')
    : 'transparent';
  return (
    <div
      ref={ref}
      role="menuitem"
      tabIndex={active ? 0 : -1}
      aria-disabled={disabled || undefined}
      onMouseEnter={onMouseEnter}
      onClick={disabled ? undefined : onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '6px 14px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        color: fg,
        background: bg,
        opacity: disabled ? 0.45 : 1,
        outline: 'none',
        // focus-visible ring: a hard inset die-cut edge, no glow.
        boxShadow: active && !disabled ? 'inset 0 0 0 2px var(--ink)' : 'none',
        transition: reduced ? 'none' : 'background var(--dur-1) var(--ease-snap)',
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 16,
          flex: 'none',
          textAlign: 'center',
          fontFamily: 'var(--font-crt)',
          color: active && danger ? 'var(--danger)' : 'inherit',
        }}
      >
        {item.mark || ''}
      </span>
      <span style={{ flex: 1, whiteSpace: 'nowrap', letterSpacing: 'var(--ls-normal)' }}>
        {item.label}
      </span>
      {item.shortcut && (
        <span
          style={{
            flex: 'none',
            marginLeft: 18,
            fontFamily: 'var(--font-mono)',
            fontSize: 'var(--t-2xs)',
            letterSpacing: 'var(--ls-wide)',
            color: active && !disabled ? (danger ? 'var(--danger)' : 'var(--ink)') : 'var(--text-faint)',
          }}
        >
          {item.shortcut}
        </span>
      )}
    </div>
  );
});
