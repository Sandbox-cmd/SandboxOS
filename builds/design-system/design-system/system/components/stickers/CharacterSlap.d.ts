import * as React from 'react';
export interface CharacterSlapProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** A kaomoji mood for the rebel. */
  face?: string;
  /** A line in her voice. */
  label?: string;
  tone?: 'rebel' | 'cool' | 'go' | 'hazard';
  rotate?: number;
}
/** CharacterSlap — a posed die-cut character mood badge (the rebel's slaps). */
export function CharacterSlap(props: CharacterSlapProps): JSX.Element;
