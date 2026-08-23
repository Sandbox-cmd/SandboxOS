import * as React from 'react';
export interface FaceToggleProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'onChange'> {
  /** Controlled state. Omit for uncontrolled. */
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  /** The two kaomoji faces for the knob. */
  faces?: { off: string; on: string };
}
/**
 * FaceToggle — the character switch; her face is the knob.
 * @startingPoint section="Components" subtitle="Character face toggle" viewport="700x160"
 */
export function FaceToggle(props: FaceToggleProps): JSX.Element;
