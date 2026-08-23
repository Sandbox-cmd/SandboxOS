import * as React from 'react';

export interface SelectOption { label: string; value: string; }

export interface SelectProps extends Omit<React.HTMLAttributes<HTMLLabelElement>, 'onChange'> {
  options: (string | SelectOption)[];
  /** Controlled value. */
  value?: string;
  /** Uncontrolled initial value. */
  defaultValue?: string;
  onChange?: React.ChangeEventHandler<HTMLSelectElement>;
  label?: string;
  disabled?: boolean;
  /** Form field name on the real native <select>. */
  name?: string;
  id?: string;
  /** Extra props forwarded to the real native <select>. */
  selectProps?: React.SelectHTMLAttributes<HTMLSelectElement>;
}

/**
 * Select — mono dropdown with a hard amber caret, built on a real native <select>.
 * @startingPoint section="Components" subtitle="Mono dropdown, native under the hood" viewport="700x140"
 */
export function Select(props: SelectProps): JSX.Element;
