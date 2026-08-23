import * as React from 'react';

export interface SwitchProps extends Omit<React.HTMLAttributes<HTMLLabelElement>, 'onChange'> {
  /** Controlled on/off. Omit for uncontrolled (use `defaultChecked`). */
  checked?: boolean;
  /** Uncontrolled initial state. */
  defaultChecked?: boolean;
  /** Fires with the next on value + the native change event. */
  onChange?: (checked: boolean, event: React.ChangeEvent<HTMLInputElement>) => void;
  label?: React.ReactNode;
  disabled?: boolean;
  /** Form field name on the real hidden checkbox. */
  name?: string;
  value?: string;
  /** Accent for the ON track. Default amber. */
  accent?: string;
  /** Extra props forwarded to the real hidden <input>. */
  inputProps?: React.InputHTMLAttributes<HTMLInputElement>;
}

/**
 * Switch — a hard-edged rocker for binary settings, on a real hidden native input.
 * @startingPoint section="Components" subtitle="Die-cut power rocker" viewport="700x160"
 */
export function Switch(props: SwitchProps): JSX.Element;
