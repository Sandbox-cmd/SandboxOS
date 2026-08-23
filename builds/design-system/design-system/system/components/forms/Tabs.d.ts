import * as React from 'react';

export interface TabsProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onChange'> {
  tabs: string[];
  /** Controlled active index. Omit for uncontrolled. */
  value?: number;
  onChange?: (index: number) => void;
}

/**
 * Tabs — teletext-style segmented tabs. ARIA tablist with roving tabIndex and
 * Arrow/Home/End keyboard navigation.
 * @startingPoint section="Components" subtitle="Teletext segmented tabs" viewport="700x120"
 */
export function Tabs(props: TabsProps): JSX.Element;
