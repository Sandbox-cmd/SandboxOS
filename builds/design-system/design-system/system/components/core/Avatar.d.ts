import * as React from 'react';
export interface AvatarProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** A kaomoji mood for the character. */
  face?: string;
  /** Show initials instead of a face. */
  initials?: string;
  size?: number;
  status?: 'online' | 'building' | 'away' | 'rebel';
  serial?: string;
}
/** Avatar — die-cut frame holding the character (kaomoji) or initials. */
export function Avatar(props: AvatarProps): JSX.Element;
