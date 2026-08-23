import * as React from 'react';

export type TableAlign = 'left' | 'right' | 'center';
export type SortDir = 'asc' | 'desc';

export interface TableColumn<R = Record<string, any>> {
  /** Row-object key this column reads. */
  key: string;
  /** Uppercase mono header label. */
  label: React.ReactNode;
  /** Text alignment. `right` is the numeric column (tabular nums, nowrap). */
  align?: TableAlign;
  /** Make the header a real sort button with a caret. */
  sortable?: boolean;
  /** Custom comparator for uncontrolled self-sort (default: numeric or locale string). */
  compare?: (a: any, b: any) => number;
  /** Render override for the cell value. */
  render?: (value: any, row: R, index: number) => React.ReactNode;
}

export interface TableProps<R = Record<string, any>>
  extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onSort'> {
  /** Column definitions, left to right. */
  columns: TableColumn<R>[];
  /** Row objects; an `id` field keys them, else array index is used. */
  rows: R[];
  /** Controlled sorted column key. Omit for uncontrolled. */
  sortKey?: string | null;
  /** Controlled sort direction. */
  sortDir?: SortDir;
  /** Initial sort key when uncontrolled. */
  defaultSortKey?: string | null;
  /** Initial sort direction when uncontrolled. */
  defaultSortDir?: SortDir;
  /** Fired on a header sort click with the next (key, dir). */
  onSort?: (key: string, dir: SortDir) => void;
  /** Tighter row padding + smaller type for high-density data. */
  dense?: boolean;
  /** Alternating row shading. */
  zebra?: boolean;
  /** Prepend a serial mono first column (zero-padded row numbers). */
  serial?: boolean;
  /** Uppercase mono caption above the grid. */
  caption?: React.ReactNode;
}

/**
 * Table — a mono, dense, die-cut data grid: the maker's primary data surface.
 * Sortable headers are real buttons; numeric columns right-align with tabular
 * nums; controlled (sortKey/sortDir/onSort) or uncontrolled, reduced-motion safe.
 * @startingPoint section="Data" subtitle="Mono die-cut data table" viewport="760x360"
 */
export function Table<R = Record<string, any>>(props: TableProps<R>): JSX.Element;
