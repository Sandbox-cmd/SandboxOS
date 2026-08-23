import * as React from 'react';
export interface BootCoinProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: number;
  label?: string;
  serial?: string;
  glyph?: string;
  tone?: 'amber' | 'rebel' | 'green' | 'cyan';
  spin?: boolean;
}
/** BootCoin — a minted 3D coin (boot token / scar-coin / achievement). Dimension = ownership. */
export function BootCoin(props: BootCoinProps): JSX.Element;
