import * as React from 'react';

export interface PaginationProps
  extends Omit<React.HTMLAttributes<HTMLElement>, 'onChange'> {
  /** Controlled current page (1-based). Omit for uncontrolled. */
  page?: number;
  /** Uncontrolled initial page (1-based). Default `1`. */
  defaultPage?: number;
  /** Total number of pages (>= 1). */
  pageCount: number;
  /** Fired with the next 1-based page when a slap is pressed. */
  onChange?: (page: number) => void;
  /** How many numbered slaps to show either side of the current page. Default `1`. */
  siblingCount?: number;
  /** The one earned accent for the active page fill. Default amber. */
  accent?: string;
  /** Hard offset-shadow ink under the active page. Default deep amber. */
  accentEdge?: string;
}

/**
 * Pagination — a brutalist pager: numbered slaps (001/002), prev/next unicode
 * marks, the current page is the one earned accent. Mono, die-cut, 0px radius,
 * hard offset shadow, slap-down on press. Real buttons, aria-label per page,
 * aria-current on active, prev/next disabled at the ends, focus-visible ring.
 * Honors prefers-reduced-motion.
 * @startingPoint section="Navigation" subtitle="Brutalist numbered pager" viewport="700x140"
 */
export function Pagination(props: PaginationProps): JSX.Element;
