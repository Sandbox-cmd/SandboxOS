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

const SR_ONLY = {
  position: 'absolute', width: 1, height: 1, margin: -1, padding: 0,
  border: 0, clip: 'rect(0 0 0 0)', clipPath: 'inset(50%)',
  overflow: 'hidden', whiteSpace: 'nowrap',
};

/**
 * Switch — a hard-edged power switch (rocker). Snaps; amber when on. A real
 * hidden native <input type="checkbox"> sits under the rocker, so keyboard
 * (Space/Enter toggle), focus ring, screen-reader state and form submission
 * all work. Controlled (`checked`) or uncontrolled (`defaultChecked`).
 * For the character-flavored variant use FaceToggle instead.
 */
export function Switch({
  checked, defaultChecked, onChange, label, disabled, name, value,
  accent = 'var(--amber)', style, inputProps, ...rest
}) {
  const reduced = useReducedMotion();
  const [on, setOn] = React.useState(!!defaultChecked);
  const controlled = checked != null;
  const v = controlled ? checked : on;

  const handle = (e) => {
    if (disabled) return;
    if (!controlled) setOn(e.target.checked);
    onChange && onChange(e.target.checked, e);
  };

  return (
    <label
      style={{
        position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 10,
        cursor: disabled ? 'not-allowed' : 'pointer', fontFamily: 'var(--font-mono)',
        fontSize: 'var(--t-sm,12px)', color: 'var(--text)', opacity: disabled ? 0.4 : 1,
        userSelect: 'none', ...style,
      }}
      {...rest}
    >
      <input
        type="checkbox" role="switch"
        name={name} value={value}
        checked={controlled ? v : undefined}
        defaultChecked={controlled ? undefined : defaultChecked}
        disabled={disabled}
        onChange={handle}
        style={SR_ONLY}
        {...inputProps}
      />
      <span
        aria-hidden="true"
        className="ds-switch-track"
        style={{
          width: 46, height: 24, flex: 'none', border: '2px solid var(--signal)',
          background: v ? accent : 'var(--bg-sunken)',
          display: 'flex', alignItems: 'center', padding: 2,
          transition: reduced ? 'none' : 'background var(--dur-1) var(--ease-snap)',
        }}
      >
        <span
          style={{
            width: 16, height: 16, background: v ? 'var(--ink)' : 'var(--signal)',
            transform: v ? 'translateX(22px)' : 'translateX(0)',
            transition: reduced ? 'none' : 'transform var(--dur-2) var(--ease-snap)',
          }}
        />
      </span>
      {label}
      <style>{`
        label:has(> input:focus-visible) > .ds-switch-track {
          outline: 2px solid var(--amber);
          outline-offset: 2px;
        }
      `}</style>
    </label>
  );
}
