import * as React from 'react';

export interface MenuItem {
  /** Stable id passed to `onSelect`. */
  id: string;
  /** Visible row text (mono, lowercase by convention). */
  label?: string;
  /** Optional leading CRT/pixel mark (unicode, never emoji), e.g. '▸' '⌫' '✕'. */
  mark?: string;
  /** Optional trailing keyboard shortcut hint, e.g. '⌘K' or 'ctrl-x'. */
  shortcut?: string;
  /** Burn this row single-ink in the danger hue (delete / wipe). Never a fill. */
  danger?: boolean;
  /** Dimmed + unfocusable + unselectable. */
  disabled?: boolean;
  /** Render a hairline rule instead of a row (id still recommended). */
  separator?: boolean;
}

export interface MenuProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onSelect'> {
  /** Rows, top to bottom. Use `{ separator: true }` for hairline groups. */
  items: MenuItem[];
  /** Fired with the chosen item's id (and the item) before close. */
  onSelect?: (id: string, item: MenuItem) => void;
  /** Controlled visibility. Defaults open; render conditionally for context menus. */
  open?: boolean;
  /** Requested close (Esc, outside-intent, or a selection). Restore focus is automatic. */
  onClose?: () => void;
  /** Which corner the slap pops from, relative to its positioned parent. */
  anchor?: 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right';
  /** Accessible name for the menu (role="menu"). */
  label?: string;
}

/**
 * Menu — a die-cut dropdown / context menu that pops up like a slapped sticker:
 * 2px ink border, hard offset shadow, mono rows, optional mark + shortcut,
 * hairline separators, single-ink danger row. Full keyboard + ARIA, focus trap,
 * focus restore, reduced-motion safe.
 *
 * Mount inside a `position: relative` parent (the opener) for anchoring.
 * @startingPoint section="Navigation" subtitle="Die-cut dropdown menu" viewport="700x340"
 */
export function Menu(props: MenuProps): JSX.Element | null;
