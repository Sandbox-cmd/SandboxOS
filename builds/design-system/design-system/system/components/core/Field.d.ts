import * as React from 'react';
export interface FieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  /** Prompt glyph before the input. */
  prefix?: string;
}
/** Field — terminal-style input with amber prompt + blinking caret. */
export function Field(props: FieldProps): JSX.Element;
