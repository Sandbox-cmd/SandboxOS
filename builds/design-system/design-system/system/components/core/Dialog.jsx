import React from 'react';
import { Window } from './Window.jsx';
import { SlapButton } from './SlapButton.jsx';

/**
 * Dialog — a talk-back dialog. The machine speaks in its own voice and
 * offers slap actions. `glyph` = a CRT kaomoji aside (the character).
 */
export function Dialog({ title = '⚠ NOTICE', children, actions = [], tone = 'mono', glyph, ...props }) {
  return (
    <Window
      title={title}
      tone={tone}
      footer={actions.length ? (
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {actions.map((a, i) => (
            <SlapButton key={i} size="sm" tone={a.tone || (i === 0 ? 'default' : 'ghost')} onClick={a.onClick}>
              {a.label}
            </SlapButton>
          ))}
        </div>
      ) : null}
      {...props}
    >
      {glyph && <div style={{ fontFamily: 'var(--font-crt)', color: 'var(--magenta)', fontSize: 'var(--t-lg)', marginBottom: 6 }}>{glyph}</div>}
      <div>{children}</div>
    </Window>
  );
}
