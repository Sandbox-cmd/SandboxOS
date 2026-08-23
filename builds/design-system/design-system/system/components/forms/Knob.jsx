import React from 'react';

/* prefers-reduced-motion — show end-state, skip motion (law 4) */
function useReducedMotion() {
  const [reduced, setReduced] = React.useState(false);
  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => setReduced(mq.matches);
    sync();
    mq.addEventListener ? mq.addEventListener('change', sync) : mq.addListener(sync);
    return () => { mq.removeEventListener ? mq.removeEventListener('change', sync) : mq.removeListener(sync); };
  }, []);
  return reduced;
}

/**
 * Knob — the cassette-deck / instrument dial. Drag vertically (or use the
 * wheel) to turn it through `min`..`max`. A real dial — label it with what
 * it actually moves (gain, speed, threshold); it won't judge how hard you
 * crank it.
 *
 * a11y: role="slider" with aria-valuenow/min/max/valuetext and an accessible
 * name (from `label` or `aria-label`). Keyboard: Arrows step, PageUp/PageDown
 * jump, Home/End go to bounds. A focus-visible ring marks keyboard focus.
 */
export function Knob({
  value, defaultValue = 0.5, min = 0, max = 1, step, label, size = 56,
  accent = 'var(--amber)', onChange, 'aria-label': ariaLabel, style, ...rest
}) {
  const reduced = useReducedMotion();
  const [internal, setInternal] = React.useState(defaultValue);
  const v = value != null ? value : internal;
  const norm = (v - min) / (max - min);
  const angle = -135 + norm * 270; // -135°..+135°
  const ref = React.useRef(null);
  const drag = React.useRef(null);
  const range = max - min;
  const fine = step || range * 0.05;
  const coarse = range * 0.1;

  const set = (nv) => {
    nv = Math.max(min, Math.min(max, nv));
    if (value == null) setInternal(nv);
    onChange && onChange(nv);
  };

  const onDown = (e) => {
    e.preventDefault();
    const startY = (e.touches ? e.touches[0].clientY : e.clientY);
    drag.current = { y: startY, v };
    const mv = (ev) => {
      const cy = (ev.touches ? ev.touches[0].clientY : ev.clientY);
      const dy = drag.current.y - cy;
      set(drag.current.v + (dy / 120) * range);
      if (ev.cancelable) ev.preventDefault();
    };
    const up = () => {
      window.removeEventListener('pointermove', mv);
      window.removeEventListener('pointerup', up);
      window.removeEventListener('touchmove', mv);
      window.removeEventListener('touchend', up);
    };
    window.addEventListener('pointermove', mv);
    window.addEventListener('pointerup', up);
    window.addEventListener('touchmove', mv, { passive: false });
    window.addEventListener('touchend', up);
  };

  const onWheel = (e) => { e.preventDefault(); set(v + (e.deltaY < 0 ? 1 : -1) * fine); };

  const onKeyDown = (e) => {
    let nv = null;
    if (e.key === 'ArrowUp' || e.key === 'ArrowRight') nv = v + fine;
    else if (e.key === 'ArrowDown' || e.key === 'ArrowLeft') nv = v - fine;
    else if (e.key === 'PageUp') nv = v + coarse;
    else if (e.key === 'PageDown') nv = v - coarse;
    else if (e.key === 'Home') nv = min;
    else if (e.key === 'End') nv = max;
    if (nv == null) return;
    e.preventDefault();
    set(nv);
  };

  // round to avoid float noise in the AT announcement
  const announced = Math.round(v * 1000) / 1000;

  return (
    <div
      style={{
        display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: 6,
        fontFamily: 'var(--font-mono)', userSelect: 'none', ...style,
      }}
      {...rest}
    >
      <div
        ref={ref}
        role="slider"
        aria-label={ariaLabel || (typeof label === 'string' ? label : undefined)}
        aria-valuenow={announced}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuetext={String(announced)}
        tabIndex={0}
        onPointerDown={onDown}
        onWheel={onWheel}
        onKeyDown={onKeyDown}
        className="ds-knob"
        style={{
          width: size, height: size, borderRadius: '50%', position: 'relative',
          cursor: 'ns-resize', touchAction: 'none', outline: 'none',
          background: 'conic-gradient(from 200deg, var(--hw-shell-lit), var(--hw-ridge) 60%, var(--hw-shell-lit))',
          border: '2px solid var(--ink)',
          boxShadow: '0 3px 6px rgba(0,0,0,0.6), inset 0 0 0 2px var(--crt-700)',
        }}
      >
        {/* indicator */}
        <span
          style={{
            position: 'absolute', top: '12%', left: '50%', width: 2, height: '32%',
            background: accent, transformOrigin: '50% 130%',
            transform: `translateX(-50%) rotate(${angle}deg)`,
            boxShadow: `0 0 5px ${accent}`,
            transition: reduced ? 'none' : 'transform var(--dur-1) var(--ease-snap)',
          }}
        />
        {/* tick ring */}
        <span style={{ position: 'absolute', inset: -5, borderRadius: '50%', border: '1px dashed var(--crt-700)' }} />
      </div>
      {label && (
        <span style={{ fontSize: 9, color: 'var(--ash-400)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          {label}
        </span>
      )}
      <style>{`
        .ds-knob:focus-visible {
          outline: 2px solid var(--amber);
          outline-offset: 3px;
        }
      `}</style>
    </div>
  );
}
