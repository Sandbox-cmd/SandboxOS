import * as React from 'react';
export interface VHSHeadlineProps extends React.HTMLAttributes<HTMLHeadingElement> {
  /** String (use '/' for line breaks) or array of lines. */
  children: React.ReactNode;
  size?: 'lg' | 'xl' | '2xl';
  align?: 'left' | 'center' | 'right';
  /** Words to glow in the accent. */
  liveWords?: string[];
  accent?: string;
  /** RGB chromatic-aberration split. */
  split?: boolean;
  shadow?: boolean;
}
/**
 * VHSHeadline — the kinetic poster voice: RGB-split, tracking, rise-on-mount.
 * @startingPoint section="Type" subtitle="Kinetic VHS poster headline" viewport="700x200"
 */
export function VHSHeadline(props: VHSHeadlineProps): JSX.Element;
