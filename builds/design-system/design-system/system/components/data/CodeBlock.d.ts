import * as React from 'react';

/** Single-ink log tone — colors the text ink only, never a fill. */
export type CodeLogTone = 'ok' | 'warn' | 'err' | 'info' | 'dim' | 'rebel';

/** A log/code line: a bare string, or a string carrying one earned tone. */
export type CodeLine = string | { text: string; tone?: CodeLogTone };

export interface CodeBlockProps extends Omit<React.HTMLAttributes<HTMLElement>, 'children'> {
  /** Raw source as a single string; split on newlines. Use this OR `lines`. */
  code?: string;
  /** Pre-split lines; strings, or `{ text, tone }` for the log variant. */
  lines?: CodeLine[];
  /** Language label shown in the title bar (e.g. `bash`, `tsx`). `text` hides it. */
  lang?: string;
  /** Title-bar caption. Presence (or `copyable`) renders the bar. */
  title?: string;
  /** Show a faint, non-selectable line-number gutter. */
  showLineNumbers?: boolean;
  /** `code` = mono source surface; `log` = CRT log stream with single-ink tones. */
  variant?: 'code' | 'log';
  /** Render a small ghost copy-slap that writes the content to the clipboard. */
  copyable?: boolean;
  /** Cap the scroll height (any CSS length); the body scrolls past it. */
  maxHeight?: string | number;
}

/**
 * CodeBlock — a die-cut terminal/log/code surface: sunken void, mono ink,
 * optional line numbers, optional copy slap, single-ink log tones. Preserves
 * whitespace; honors prefers-reduced-motion; keyboard + AT operable.
 * @startingPoint section="Data" subtitle="Die-cut terminal / code surface" viewport="700x340"
 */
export function CodeBlock(props: CodeBlockProps): JSX.Element;
