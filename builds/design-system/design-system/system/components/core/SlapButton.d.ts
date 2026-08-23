import * as React from 'react';

export interface SlapButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual tone. Mono `default`/`ghost` are the norm; color is earned. */
  tone?: 'default' | 'ghost' | 'go' | 'rebel' | 'ok' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  /** Full-width. */
  block?: boolean;
  /** Tilt the slap, in degrees, for stuck-on-by-hand energy. */
  rotate?: number;
  disabled?: boolean;
}

/**
 * SlapButton — the SandboxOS button, a die-cut sticker that presses down like a real slap.
 * @startingPoint section="Components" subtitle="Die-cut slap button" viewport="700x200"
 */
export function SlapButton(props: SlapButtonProps): JSX.Element;
