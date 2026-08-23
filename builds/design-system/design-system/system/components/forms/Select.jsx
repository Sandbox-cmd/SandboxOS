import React from 'react';

/**
 * Select — a mono dropdown with a hard amber caret. Built on a REAL native
 * <select>, so keyboard, type-ahead, screen-reader announcement and form
 * submission are all native. The caret is decorative (pointer-events: none);
 * a focus-visible ring is driven off the real control via :focus-within.
 * Controlled (`value`) or uncontrolled (`defaultValue`).
 */
export function Select({
  options = [], value, defaultValue, onChange, label, disabled, name, id,
  style, selectProps, ...props
}) {
  const autoId = React.useId ? React.useId() : undefined;
  const selectId = id || autoId;

  return (
    <label
      htmlFor={selectId}
      className="ds-select"
      style={{
        display: 'inline-block', fontFamily: 'var(--font-mono)',
        opacity: disabled ? 0.4 : 1, ...style,
      }}
      {...props}
    >
      {label && (
        <span style={{
          display: 'block', fontSize: 'var(--t-2xs)', textTransform: 'uppercase',
          letterSpacing: 'var(--ls-wide)', color: 'var(--text-faint)', marginBottom: 5,
        }}>
          {label}
        </span>
      )}
      <span
        className="ds-select-shell"
        style={{
          position: 'relative', display: 'inline-flex', alignItems: 'center',
          border: '2px solid var(--border-strong)', background: 'var(--bg-sunken)',
        }}
      >
        <select
          id={selectId}
          name={name}
          value={value}
          defaultValue={defaultValue}
          onChange={onChange}
          disabled={disabled}
          style={{
            appearance: 'none', WebkitAppearance: 'none', background: 'transparent',
            border: 0, color: 'var(--text)', fontFamily: 'var(--font-mono)',
            fontSize: 'var(--t-sm)', padding: '7px 34px 7px 11px', outline: 'none',
            cursor: disabled ? 'not-allowed' : 'pointer',
          }}
          {...selectProps}
        >
          {options.map((o, i) => (
            <option
              key={i}
              value={typeof o === 'object' ? o.value : o}
              style={{ background: 'var(--crt-900)' }}
            >
              {typeof o === 'object' ? o.label : o}
            </option>
          ))}
        </select>
        <span
          aria-hidden="true"
          style={{
            position: 'absolute', right: 0, top: 0, bottom: 0, width: 26,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            borderLeft: '2px solid var(--border-strong)', color: 'var(--amber)',
            fontFamily: 'var(--font-crt)', pointerEvents: 'none',
          }}
        >
          ▾
        </span>
      </span>
      <style>{`
        .ds-select-shell:focus-within {
          outline: 2px solid var(--amber);
          outline-offset: 2px;
        }
      `}</style>
    </label>
  );
}
