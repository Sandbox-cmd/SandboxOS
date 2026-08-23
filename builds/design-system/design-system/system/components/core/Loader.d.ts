import * as React from 'react';
export interface LoaderProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 0–100, or null for indeterminate. */
  value?: number | null;
  label?: string;
  /** The teletext sign-off line. */
  caption?: string;
  width?: number | string;
}
/** Loader — CRT "THANK YOU FOR USING" progress bar. */
export function Loader(props: LoaderProps): JSX.Element;
