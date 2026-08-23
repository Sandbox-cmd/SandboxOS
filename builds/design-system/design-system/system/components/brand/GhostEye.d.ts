import * as React from 'react';
export interface GhostEyeProps extends React.HTMLAttributes<HTMLSpanElement> {
  size?: number;
  /** Iris accent color (CSS var or hex). The one earned color on her. */
  accent?: string;
  mood?: 'rebel' | 'calm' | 'watch';
  /** Pupil tracks the cursor. */
  watch?: boolean;
  blink?: boolean;
}
/**
 * GhostEye — the character as an ownable 1-bit dithered gaze. The always-on mascot.
 * @startingPoint section="Brand" subtitle="The always-around dithered eye" viewport="700x240"
 */
export function GhostEye(props: GhostEyeProps): JSX.Element;
