import * as React from 'react';

/** Single-ink status of a row — rendered as a hollow tinted dot, never a fill. */
export type ListStatus =
  | 'active'
  | 'ok'
  | 'rebel'
  | 'link'
  | 'warn'
  | 'danger'
  | 'idle';

export interface ListItem {
  /** Stable identity — returned by onSelect, used as the React key. */
  id: string | number;
  /** Primary mono label (the line). */
  label: React.ReactNode;
  /** Optional secondary metadata, rendered faint under the label. */
  meta?: React.ReactNode;
  /** Single-ink status dot. Omit for a plain row. */
  status?: ListStatus;
  /** Leading serial/index instead of a status dot (tabular numerals). */
  serial?: string | number;
  /** Trailing value or action — a count, a timestamp, a node. */
  trailing?: React.ReactNode;
}

export interface ListProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onSelect'> {
  /** Rows to render, top to bottom. */
  items: ListItem[];
  /** Makes rows focusable, keyboard-roving options; fires with the picked id. */
  onSelect?: (id: ListItem['id']) => void;
  /** Controlled selected id. */
  value?: ListItem['id'] | null;
  /** Uncontrolled initial selected id. */
  defaultValue?: ListItem['id'] | null;
  /** Tighter rows for high-density feeds. */
  dense?: boolean;
  /** Hairline rule between rows (on by default). */
  divided?: boolean;
}

/**
 * List — a dense vertical feed of die-cut rows: leading status dot or serial,
 * mono label, faint meta, trailing value. Mono base, one earned amber accent on
 * the active row, single-ink status dots. Selectable rows are real focusable
 * options with arrow-key roving; motion honours prefers-reduced-motion.
 * @startingPoint section="Data" subtitle="Dense die-cut feed list" viewport="700x340"
 */
export function List(props: ListProps): JSX.Element;
