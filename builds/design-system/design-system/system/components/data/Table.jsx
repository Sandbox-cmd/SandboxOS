import React from 'react';

/**
 * Table — the maker's primary data surface: a mono, dense, die-cut grid.
 * 2px die-cut outer border, 1px hairline row rules, uppercase mono header
 * with optional sort caret, optional zebra, right-aligned numerics, and an
 * optional serial mono first column. Sortable headers are REAL buttons.
 *
 * Controlled (sortKey/sortDir/onSort) or uncontrolled (defaultSortKey/defaultSortDir),
 * matching the Switch pattern — pass the value to control it, omit to let it self-drive.
 */
export function Table({
  columns = [],
  rows = [],
  sortKey,
  sortDir,
  defaultSortKey = null,
  defaultSortDir = 'asc',
  onSort,
  dense = false,
  zebra = false,
  serial = false,
  caption,
  style,
  ...rest
}) {
  // reduced-motion: end-state only, skip the caret flip transition.
  const [still, setStill] = React.useState(false);
  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => setStill(!!mq.matches);
    sync();
    mq.addEventListener ? mq.addEventListener('change', sync) : mq.addListener(sync);
    return () => { mq.removeEventListener ? mq.removeEventListener('change', sync) : mq.removeListener(sync); };
  }, []);

  // uncontrolled sort state; controlled props win when present.
  const [ownKey, setOwnKey] = React.useState(defaultSortKey);
  const [ownDir, setOwnDir] = React.useState(defaultSortDir);
  const aKey = sortKey !== undefined ? sortKey : ownKey;
  const aDir = sortDir !== undefined ? sortDir : ownDir;

  const requestSort = (key) => {
    const nextDir = aKey === key && aDir === 'asc' ? 'desc' : 'asc';
    if (sortKey === undefined) setOwnKey(key);
    if (sortDir === undefined) setOwnDir(nextDir);
    onSort && onSort(key, nextDir);
  };

  // when uncontrolled AND a sort key is live, sort a copy locally.
  const selfSorting = sortKey === undefined && onSort == null && aKey != null;
  const data = React.useMemo(() => {
    if (!selfSorting) return rows;
    const col = columns.find((c) => c.key === aKey);
    const cmp = (col && col.compare) || defaultCompare;
    const sorted = rows.slice().sort((ra, rb) => cmp(ra[aKey], rb[aKey]));
    return aDir === 'desc' ? sorted.reverse() : sorted;
  }, [rows, columns, aKey, aDir, selfSorting]);

  useSortFocusStyle();

  const cellPadV = dense ? '4px' : '8px';
  const cellPadH = dense ? '8px' : '12px';
  const dataFs = dense ? 'var(--t-2xs)' : 'var(--t-xs)';
  const caretT = still ? 'none' : 'transform var(--dur-1) var(--ease-snap)';

  const headCell = (col, i) => {
    const align = col.align || 'left';
    const active = aKey === col.key;
    const base = {
      padding: `${cellPadV} ${cellPadH}`,
      textAlign: align,
      borderBottom: '2px solid var(--ink)',
      borderRight: i < columns.length - 1 ? '1px solid var(--border)' : undefined,
      background: 'var(--surface-2)',
      whiteSpace: 'nowrap',
      verticalAlign: 'bottom',
    };
    const labelStyle = {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-3xs)',
      fontWeight: 'var(--w-bold)',
      letterSpacing: 'var(--ls-wide)',
      textTransform: 'uppercase',
      color: active ? 'var(--amber)' : 'var(--text-dim)',
    };
    if (!col.sortable) {
      return (
        <th key={col.key} scope="col"
          aria-sort={align === 'right' ? undefined : 'none'}
          style={base}>
          <span style={labelStyle}>{col.label}</span>
        </th>
      );
    }
    const ariaSort = active ? (aDir === 'asc' ? 'ascending' : 'descending') : 'none';
    return (
      <th key={col.key} scope="col" aria-sort={ariaSort} style={base}>
        <button
          type="button"
          className="sbx-table-sort"
          onClick={() => requestSort(col.key)}
          style={{
            ...labelStyle,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            flexDirection: align === 'right' ? 'row-reverse' : 'row',
            width: '100%',
            justifyContent: align === 'right' ? 'flex-start' : 'flex-start',
            background: 'transparent',
            border: 'none',
            borderRadius: 0,
            padding: 0,
            margin: 0,
            cursor: 'pointer',
            font: 'inherit',
            color: 'inherit',
            textTransform: 'inherit',
            letterSpacing: 'inherit',
          }}
        >
          <span>{col.label}</span>
          <Caret active={active} dir={aDir} transition={caretT} />
        </button>
      </th>
    );
  };

  return (
    <div
      style={{
        border: '2px solid var(--ink)',
        boxShadow: 'var(--shadow-slap)',
        background: 'var(--surface)',
        overflowX: 'auto',
        ...style,
      }}
      {...rest}
    >
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text)',
        }}
      >
        {caption ? (
          <caption
            style={{
              captionSide: 'top',
              textAlign: 'left',
              padding: `${cellPadV} ${cellPadH}`,
              fontFamily: 'var(--font-mono)',
              fontSize: 'var(--t-3xs)',
              letterSpacing: 'var(--ls-wide)',
              textTransform: 'uppercase',
              color: 'var(--text-faint)',
              borderBottom: '1px solid var(--border)',
            }}
          >
            {caption}
          </caption>
        ) : null}
        <thead>
          <tr>
            {serial ? (
              <th
                scope="col"
                aria-hidden="true"
                style={{
                  padding: `${cellPadV} ${cellPadH}`,
                  textAlign: 'right',
                  borderBottom: '2px solid var(--ink)',
                  borderRight: '1px solid var(--border)',
                  background: 'var(--surface-2)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--t-3xs)',
                  fontWeight: 'var(--w-bold)',
                  letterSpacing: 'var(--ls-wide)',
                  color: 'var(--text-faint)',
                  width: 1,
                  whiteSpace: 'nowrap',
                }}
              >
                {'№'}
              </th>
            ) : null}
            {columns.map((col, i) => headCell(col, i))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length + (serial ? 1 : 0)}
                style={{
                  padding: dense ? '12px' : '20px',
                  textAlign: 'center',
                  fontFamily: 'var(--font-mono)',
                  fontSize: dataFs,
                  letterSpacing: 'var(--ls-wide)',
                  textTransform: 'uppercase',
                  color: 'var(--text-faint)',
                }}
              >
                {'—'} no rows {'—'}
              </td>
            </tr>
          ) : (
            data.map((row, ri) => {
              const zebraBg =
                zebra && ri % 2 === 1 ? 'var(--surface-2)' : 'transparent';
              return (
                <tr
                  key={row.id != null ? row.id : ri}
                  style={{ background: zebraBg }}
                >
                  {serial ? (
                    <td
                      style={{
                        padding: `${cellPadV} ${cellPadH}`,
                        textAlign: 'right',
                        borderBottom: '1px solid var(--border)',
                        borderRight: '1px solid var(--border)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 'var(--t-3xs)',
                        color: 'var(--text-faint)',
                        fontVariantNumeric: 'tabular-nums',
                        whiteSpace: 'nowrap',
                        userSelect: 'none',
                      }}
                    >
                      {String(ri + 1).padStart(2, '0')}
                    </td>
                  ) : null}
                  {columns.map((col, ci) => {
                    const align = col.align || 'left';
                    const numeric = align === 'right';
                    const raw = row[col.key];
                    const content = col.render ? col.render(raw, row, ri) : raw;
                    const isSortCol = aKey === col.key;
                    return (
                      <td
                        key={col.key}
                        style={{
                          padding: `${cellPadV} ${cellPadH}`,
                          textAlign: align,
                          borderBottom: '1px solid var(--border)',
                          borderRight:
                            ci < columns.length - 1
                              ? '1px solid var(--border)'
                              : undefined,
                          fontFamily: 'var(--font-mono)',
                          fontSize: dataFs,
                          lineHeight: 'var(--lh-mono)',
                          color: isSortCol ? 'var(--text)' : 'var(--text-dim)',
                          fontVariantNumeric: numeric ? 'tabular-nums' : undefined,
                          fontWeight: isSortCol
                            ? 'var(--w-medium)'
                            : 'var(--w-regular)',
                          whiteSpace: numeric ? 'nowrap' : undefined,
                        }}
                      >
                        {content}
                      </td>
                    );
                  })}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Inject the focus-visible ring for sort buttons once per document.
 * Inline styles can't express :focus-visible; a single scoped rule gives the
 * keyboard ring without leaking global selectors.
 */
function useSortFocusStyle() {
  React.useEffect(() => {
    if (typeof document === 'undefined') return;
    const id = 'sbx-table-sort-focus';
    if (document.getElementById(id)) return;
    const el = document.createElement('style');
    el.id = id;
    el.textContent =
      '.sbx-table-sort:focus-visible{outline:2px solid var(--cyan);outline-offset:2px;}' +
      '.sbx-table-sort:focus:not(:focus-visible){outline:none;}';
    document.head.appendChild(el);
  }, []);
}

/** Default ascending comparator: numbers numerically, everything else string-wise. */
function defaultCompare(a, b) {
  if (a == null && b == null) return 0;
  if (a == null) return -1;
  if (b == null) return 1;
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b));
}

/** The sort caret — a CRT pixel mark, not an emoji. Flips on snap motion. */
function Caret({ active, dir, transition }) {
  if (!active) {
    return (
      <span
        aria-hidden="true"
        style={{
          fontFamily: 'var(--font-crt)',
          fontSize: 'var(--t-xs)',
          lineHeight: 1,
          color: 'var(--text-faint)',
          opacity: 0.5,
        }}
      >
        {'↕'}
      </span>
    );
  }
  return (
    <span
      aria-hidden="true"
      style={{
        fontFamily: 'var(--font-crt)',
        fontSize: 'var(--t-xs)',
        lineHeight: 1,
        color: 'var(--amber)',
        display: 'inline-block',
        transform: dir === 'desc' ? 'rotate(180deg)' : 'rotate(0deg)',
        transition,
      }}
    >
      {'▲'}
    </span>
  );
}
