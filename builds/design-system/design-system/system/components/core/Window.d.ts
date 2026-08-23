import * as React from 'react';
export interface WindowProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  /** `mono` (default) or `blue` (the bootleg error-screen takeover). */
  tone?: 'mono' | 'blue';
  width?: number | string;
  /** Hand-stuck tilt, degrees. */
  tilt?: number;
  /** Footer row (e.g. action SlapButtons). */
  footer?: React.ReactNode;
  onClose?: () => void;
}
/**
 * Window — the SandboxOS window/panel frame with inverted title bar.
 * @startingPoint section="Components" subtitle="Bootleg OS window frame" viewport="700x260"
 */
export function Window(props: WindowProps): JSX.Element;
