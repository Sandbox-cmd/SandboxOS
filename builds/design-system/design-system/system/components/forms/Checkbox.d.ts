import * as React from 'react';

export interface CheckboxProps extends Omit<React.HTMLAttributes<HTMLLabelElement>, 'onChange'> {
  /** Controlled checked state. Omit for uncontrolled (use `defaultChecked`). */
  checked?: boolean;
  /** Uncontrolled initial state. */
  defaultChecked?: boolean;
  /** Fires with the next checked value + the native change event. */
  onChange?: (checked: boolean, event: React.ChangeEvent<HTMLInputElement>) => void;
  label?: React.ReactNode;
  disabled?: boolean;
  /** Form field name on the real hidden input. */
  name?: string;
  /** Value submitted when checked. */
  value?: string;
  /** Accent for the checked fill. Default amber. */
  accent?: string;
  /** Extra props forwarded to the real hidden <input>. */
  inputProps?: React.InputHTMLAttributes<HTMLInputElement>;
}

export interface RadioProps extends Omit<React.HTMLAttributes<HTMLLabelElement>, 'onChange'> {
  /** Controlled checked state. */
  checked?: boolean;
  /** Uncontrolled initial state. */
  defaultChecked?: boolean;
  /** Fires with this radio's `value` + the native change event. */
  onChange?: (value: any, event: React.ChangeEvent<HTMLInputElement>) => void;
  label?: React.ReactNode;
  /** Shared group name — required for radio grouping + keyboard arrows. */
  name?: string;
  value?: any;
  disabled?: boolean;
  /** Accent for the selected dot. Default magenta. */
  accent?: string;
  inputProps?: React.InputHTMLAttributes<HTMLInputElement>;
}

/**
 * Checkbox — die-cut box with amber ✕, driven by a real hidden native input.
 * @startingPoint section="Components" subtitle="Die-cut checkbox + radio" viewport="700x160"
 */
export function Checkbox(props: CheckboxProps): JSX.Element;
/** Radio — round die-cut with magenta dot; group with a shared `name`. */
export function Radio(props: RadioProps): JSX.Element;
