import * as React from 'react';

export interface StickerProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Die-cut shape. */
  shape?: 'tag' | 'pill' | 'seal' | 'burst' | 'ribbon' | 'price' | 'callout' | 'stamp';
  /** Loud earned color. Use `striped` for hazard tape. */
  tone?: 'hazard' | 'alert' | 'rebel' | 'go' | 'cyan' | 'ink' | 'paper' | 'striped';
  /** Hand-stuck tilt, degrees. */
  rotate?: number;
  /** White die-cut halo behind the sticker. */
  halo?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export interface BarcodeProps extends React.HTMLAttributes<HTMLSpanElement> {
  height?: number;
  /** Seed string → deterministic bars (use a serial). */
  seed?: string;
  color?: string;
}

/**
 * Sticker — die-cut sticker system, usable as UI (callouts, awards, buttons).
 * @startingPoint section="Components" subtitle="Die-cut sticker / slap system" viewport="700x240"
 */
export function Sticker(props: StickerProps): JSX.Element;
/** Barcode — procedural provenance mark. */
export function Barcode(props: BarcodeProps): JSX.Element;
