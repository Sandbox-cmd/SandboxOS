import * as React from 'react';
export interface CartridgeProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
  serial?: string;
  /** Color-codes the label spine. */
  kind?: 'build' | 'skill' | 'persona';
  /** Override the spine gradient. */
  spineStyle?: string;
  /** Auto-rotate (hover speeds up). */
  spin?: boolean;
  /** Front face width in px; the module scales from this. */
  width?: number;
}
/**
 * Cartridge — the build object as a rotating 3D module. Dimension = ownership.
 * @startingPoint section="Components" subtitle="3D plug-n-play cartridge" viewport="700x420"
 */
export function Cartridge(props: CartridgeProps): JSX.Element;
