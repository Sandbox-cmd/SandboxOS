import * as React from 'react';

export interface NavItem {
  /** Stable identity — passed to `onSelect`, matched against `activeId`. */
  id: string;
  /** Row text. */
  label: string;
  /** Optional leading glyph — a CRT/pixel unicode mark, never an emoji. */
  mark?: string;
  /** Optional trailing count — a brutalist numeral in a die-cut chip. */
  count?: number | string;
}

export interface NavSection {
  /** Uppercase mono group label. Omit for an unlabeled run of items. */
  label?: string;
  items: NavItem[];
}

export interface NavProps
  extends Omit<React.HTMLAttributes<HTMLElement>, 'onSelect'> {
  /** Grouped items. Order here is the keyboard roving order. */
  sections: NavSection[];
  /** Id of the live item — gets the earned accent + `aria-current="page"`. */
  activeId?: string;
  /** Fired with an item id on click or Enter/Space. */
  onSelect?: (id: string) => void;
  /** Rail mode: labels/counts hide to marks only; AT still reads them. */
  collapsed?: boolean;
  /** The one earned accent for the active row. Default amber. */
  accent?: string;
  /** Landmark label for the `<nav>`. Default `Workbench`. */
  ariaLabel?: string;
}

/**
 * Nav — the workbench side navigation: a die-cut control rail. Uppercase mono
 * group labels; the active item carries the one earned accent as a left
 * die-cut bar + brand text, with an optional leading mark and trailing count.
 * Arrow-key roving, Enter/Space to select, real `<nav>` landmark, reduced-motion safe.
 * @startingPoint section="Navigation" subtitle="Workbench side rail" viewport="320x420"
 */
export function Nav(props: NavProps): JSX.Element;
