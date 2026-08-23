import * as React from 'react';
export interface ToastProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  tone?: 'rebel' | 'alert' | 'ok' | 'info' | 'warn';
  /** CRT glyph in the colored tab. */
  glyph?: string;
}
/** Toast — a talk-back aside in the character's voice. */
export function Toast(props: ToastProps): JSX.Element;
