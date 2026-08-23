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

/* visually-hidden but focusable, AT-readable, form-participating native input */
const SR_ONLY = {
  position: 'absolute', width: 1, height: 1, margin: -1, padding: 0,
  border: 0, clip: 'rect(0 0 0 0)', clipPath: 'inset(50%)',
  overflow: 'hidden', whiteSpace: 'nowrap',
};

/**
 * Checkbox — die-cut box, amber ✕ when checked.
 * A real hidden native <input type="checkbox"> drives the visual: keyboard,
 * focus ring, screen readers and form submission all work. Controlled
 * (`checked`) or uncontrolled (`defaultChecked`).
 */
export function Checkbox({
  checked, defaultChecked, onChange, label, disabled, name, value,
  accent = 'var(--amber)', style, inputProps, ...props
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
        position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 9,
        cursor: disabled ? 'not-allowed' : 'pointer', fontFamily: 'var(--font-mono)',
        fontSize: 'var(--t-sm)', color: 'var(--text)', opacity: disabled ? 0.4 : 1,
        userSelect: 'none', ...style,
      }}
      {...props}
    >
      <input
        type="checkbox"
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
        className="ds-checkbox-box"
        style={{
          width: 18, height: 18, flex: 'none', border: '2px solid var(--signal)',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          background: v ? accent : 'var(--bg-sunken)', color: 'var(--ink)',
          fontFamily: 'var(--font-crt)', fontSize: 14, lineHeight: 1,
          transition: reduced ? 'none' : 'background var(--dur-1) var(--ease-snap)',
        }}
      >
        {v ? '✕' : ''}
      </span>
      {label}
      {/* focus-visible ring driven by the real input via :focus-visible */}
      <style>{`
        .ds-checkbox-box { box-shadow: none; }
        label:has(> input:focus-visible) > .ds-checkbox-box {
          outline: 2px solid var(--amber);
          outline-offset: 2px;
        }
      `}</style>
    </label>
  );
}

/**
 * Radio — round die-cut, magenta dot when selected. Real hidden native
 * <input type="radio">; group with a shared `name`. Keyboard arrow-key
 * navigation and form submission come from the browser for free.
 */
export function Radio({
  checked, defaultChecked, onChange, label, name, value, disabled,
  accent = 'var(--magenta)', style, inputProps, ...props
}) {
  const reduced = useReducedMotion();
  const controlled = checked != null;
  const [on, setOn] = React.useState(!!defaultChecked);
  const v = controlled ? checked : on;

  const handle = (e) => {
    if (disabled) return;
    if (!controlled) setOn(e.target.checked);
    onChange && onChange(value, e);
  };

  return (
    <label
      style={{
        position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 9,
        cursor: disabled ? 'not-allowed' : 'pointer', fontFamily: 'var(--font-mono)',
        fontSize: 'var(--t-sm)', color: 'var(--text)', opacity: disabled ? 0.4 : 1,
        userSelect: 'none', ...style,
      }}
      {...props}
    >
      <input
        type="radio"
        name={name} value={value}
        checked={controlled ? checked : undefined}
        defaultChecked={controlled ? undefined : defaultChecked}
        disabled={disabled}
        onChange={handle}
        style={SR_ONLY}
        {...inputProps}
      />
      <span
        aria-hidden="true"
        className="ds-radio-ring"
        style={{
          width: 18, height: 18, flex: 'none', borderRadius: '50%',
          border: '2px solid var(--signal)', display: 'inline-flex',
          alignItems: 'center', justifyContent: 'center', background: 'var(--bg-sunken)',
        }}
      >
        <span
          style={{
            width: 9, height: 9, borderRadius: '50%', background: accent,
            boxShadow: '0 0 6px var(--glow-magenta)',
            transform: v ? 'scale(1)' : 'scale(0)',
            transition: reduced ? 'none' : 'transform var(--dur-1) var(--ease-snap)',
          }}
          className="ds-radio-dot"
        />
      </span>
      {label}
      <style>{`
        label:has(> input:checked) > .ds-radio-ring > .ds-radio-dot { transform: scale(1) !important; }
        label:has(> input:not(:checked)) > .ds-radio-ring > .ds-radio-dot { transform: scale(0) !important; }
        label:has(> input:focus-visible) > .ds-radio-ring {
          outline: 2px solid var(--magenta);
          outline-offset: 2px;
        }
      `}</style>
    </label>
  );
}
