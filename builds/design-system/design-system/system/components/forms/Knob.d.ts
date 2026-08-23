import * as React from 'react';

export interface KnobProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onChange'> {
  /** Controlled value. Omit for uncontrolled (use `defaultValue`). */
  value?: number;
  defaultValue?: number;
  min?: number;
  max?: number;
  /** Arrow-key / wheel step. Defaults to 5% of the range. */
  step?: number;
  label?: string;
  size?: number;
  accent?: string;
  onChange?: (value: number) => void;
  /** Accessible name when `label` is not a plain string. */
  'aria-label'?: string;
}

/**
 * Knob — the cassette-deck / instrument dial. Drag, wheel, or keyboard.
 * role="slider" with full Arrow/Page/Home/End keys and a focus ring.
 * @startingPoint section="Components" subtitle="Cassette-deck control dial" viewport="700x160"
 */
export function Knob(props: KnobProps): JSX.Element;
