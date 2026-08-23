import * as React from 'react';
export interface DialogAction { label: string; onClick?: () => void; tone?: 'default' | 'ghost' | 'go' | 'rebel' | 'ok' | 'danger'; }
export interface DialogProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  tone?: 'mono' | 'blue';
  /** Slap action buttons; first is primary. */
  actions?: DialogAction[];
  /** A CRT kaomoji aside — the character talking back. */
  glyph?: string;
}
/**
 * Dialog — a talk-back dialog box; the OS speaks in its own voice.
 * @startingPoint section="Components" subtitle="Talk-back dialog box" viewport="700x260"
 */
export function Dialog(props: DialogProps): JSX.Element;
