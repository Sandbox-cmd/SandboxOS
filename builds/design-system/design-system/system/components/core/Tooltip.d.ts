import * as React from 'react';
export interface TooltipProps extends React.HTMLAttributes<HTMLSpanElement> {
  label: React.ReactNode;
  tone?: 'ink' | 'amber' | 'rebel';
  side?: 'top' | 'bottom';
}
/** Tooltip — a die-cut slap that pops on hover. */
export function Tooltip(props: TooltipProps): JSX.Element;
