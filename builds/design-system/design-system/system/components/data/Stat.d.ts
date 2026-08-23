import * as React from 'react';

export type StatTone = 'default' | 'active' | 'rebel' | 'ok' | 'link';

export interface StatProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'children'> {
  /** Uppercase mono caption above the number. */
  label: React.ReactNode;
  /** The big display number (string or number — pre-formatted is fine). */
  value: React.ReactNode;
  /** Optional unit, set small + dim beside the value (e.g. "ms", "x", "%"). */
  unit?: React.ReactNode;
  /**
   * Optional delta. A number renders signed with an up/down mark
   * (▲ green-ink for >0, ▼ alert-ink for <0, — faint for 0). A string
   * passes through; lead with + or - to set the mark direction.
   */
  delta?: number | string;
  /** ONE earned accent on the number. Mono `default` is the norm. */
  tone?: StatTone;
}

/**
 * Stat — a workshop metric tile: big brutalist display number, uppercase
 * label, optional unit + single-ink delta. Die-cut, mono-by-default.
 * @startingPoint section="Data" subtitle="Metric tile + key/value list" viewport="720x280"
 */
export function Stat(props: StatProps): JSX.Element;

export interface KeyValuePair {
  /** Row key (rendered uppercase, faint). */
  k: React.ReactNode;
  /** Row value (rendered ink, tabular-aligned). */
  v: React.ReactNode;
}

export interface KeyValueProps extends Omit<React.HTMLAttributes<HTMLDListElement>, 'children'> {
  /** The rows, in order. Rendered as a real <dl>/<dt>/<dd>. */
  pairs: KeyValuePair[];
  /** Tighter rows + smaller type for a packed spec block. */
  dense?: boolean;
  /** Value-column alignment. Default `right` for number columns. */
  align?: 'left' | 'right';
}

/**
 * KeyValue — a tight, hairline-separated mono definition list: key → value
 * rows. The dense see-the-parts surface for a small spec of facts.
 */
export function KeyValue(props: KeyValueProps): JSX.Element;
