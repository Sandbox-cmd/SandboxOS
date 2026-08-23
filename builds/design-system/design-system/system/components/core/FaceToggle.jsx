import React from 'react';

/**
 * FaceToggle — the character switch. Her face is the knob: off she watches
 * `(•_•)`, on she's locked in `⌐■_■`. Controlled or uncontrolled.
 */
export function FaceToggle({ checked, onChange, faces = { off: '•_•', on: '■_■' }, style, ...props }) {
  const [internal, setInternal] = React.useState(!!checked);
  const isOn = checked != null ? checked : internal;
  const toggle = () => { const v = !isOn; if (checked == null) setInternal(v); onChange && onChange(v); };
  return (
    <button type="button" onClick={toggle} aria-pressed={isOn} style={{
      width: 80, height: 34, border: `2px solid ${isOn ? 'var(--magenta)' : 'var(--signal)'}`,
      background: isOn ? 'var(--magenta)' : 'var(--bg-sunken)', display: 'flex', alignItems: 'center',
      padding: 2, cursor: 'pointer', ...style,
    }} {...props}>
      <span style={{
        width: 30, height: 26, background: isOn ? 'var(--ink)' : 'var(--signal)',
        color: isOn ? 'var(--magenta)' : 'var(--ink)', display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: 'var(--font-crt)', fontSize: 'var(--t-sm)',
        transform: isOn ? 'translateX(44px)' : 'translateX(0)', transition: 'transform 160ms var(--ease-snap)',
      }}>{isOn ? faces.on : faces.off}</span>
    </button>
  );
}
