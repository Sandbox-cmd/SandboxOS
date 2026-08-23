import React from 'react';
import { SlapButton } from '../core/SlapButton.jsx';

/**
 * CodeBlock — a die-cut terminal/log/code surface. Sunken void, mono ink,
 * optional line numbers, an optional copy slap, an optional title bar, and
 * single-ink log tones. Whitespace is preserved; nothing is highlighted in
 * color unless a log line earns one accent. Mono by default — color is earned.
 *
 * Pass `code` (a string) OR `lines` (array of strings, or array of
 * `{ text, tone }` for the log variant). Controlled-free: it just renders.
 */
export function CodeBlock({
  code,
  lines,
  lang = 'text',
  title,
  showLineNumbers = false,
  variant = 'code',     // 'code' | 'log'
  copyable = false,
  maxHeight,
  style,
  ...props
}) {
  const [copied, setCopied] = React.useState(false);
  const reduce = usePrefersReducedMotion();
  const liveRef = React.useRef(null);

  // ---- normalize input to an array of { text, tone } -----------------------
  const rows = React.useMemo(() => {
    let src = lines;
    if (src == null && code != null) src = String(code).split('\n');
    if (src == null) src = [''];
    return src.map((row) =>
      typeof row === 'string' ? { text: row, tone: undefined } : { text: row.text ?? '', tone: row.tone }
    );
  }, [code, lines]);

  const rawText = React.useMemo(() => rows.map((r) => r.text).join('\n'), [rows]);

  // ---- single-ink log tones (NEVER fills — only the text-ink changes) ------
  const toneInk = {
    ok:    'var(--green)',
    warn:  'var(--warn)',
    err:   'var(--alert)',
    info:  'var(--link)',
    dim:   'var(--text-faint)',
    rebel: 'var(--magenta)',
  };

  const copy = React.useCallback(() => {
    const done = () => {
      setCopied(true);
      if (liveRef.current) liveRef.current.textContent = 'copied to clipboard';
      window.setTimeout(() => setCopied(false), reduce ? 600 : 1400);
    };
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(rawText).then(done, () => fallbackCopy(rawText, done));
      } else {
        fallbackCopy(rawText, done);
      }
    } catch (e) {
      fallbackCopy(rawText, done);
    }
  }, [rawText, reduce]);

  const gutterW = String(rows.length).length;
  const showBar = title != null || copyable;

  return (
    <figure
      style={{
        margin: 0,
        background: 'var(--bg-sunken)',
        border: 'var(--bw-1) solid var(--ink)',
        boxShadow: 'var(--shadow-slap)',
        fontFamily: variant === 'log' ? 'var(--font-crt)' : 'var(--font-mono)',
        fontSize: variant === 'log' ? 'var(--t-sm)' : 'var(--t-xs)',
        lineHeight: 'var(--lh-mono)',
        color: 'var(--text)',
        ...style,
      }}
      {...props}
    >
      {showBar && (
        <figcaption
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--sp-3)',
            padding: '6px 8px 6px 10px',
            borderBottom: 'var(--bw-1) solid var(--border)',
            background: 'var(--surface-2)',
            fontFamily: 'var(--font-mono)', fontSize: 'var(--t-3xs)',
            textTransform: 'uppercase', letterSpacing: 'var(--ls-wide)',
            color: 'var(--text-dim)',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--sp-2)', minWidth: 0 }}>
            <span aria-hidden="true" style={{ color: 'var(--text-faint)' }}>{'■'}</span>
            {title != null && (
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{title}</span>
            )}
            {lang && lang !== 'text' && (
              <span style={{ color: 'var(--text-faint)' }}>{'·'} {lang}</span>
            )}
          </span>
          {copyable && (
            <SlapButton
              tone="ghost"
              size="sm"
              onClick={copy}
              aria-label={copied ? 'copied to clipboard' : 'copy code to clipboard'}
            >
              {copied ? '✓ copied' : 'copy'}
            </SlapButton>
          )}
        </figcaption>
      )}

      <div
        style={{
          overflow: 'auto',
          maxHeight: maxHeight,
        }}
      >
        <pre
          aria-label={title ? `${variant === 'log' ? 'log' : 'code'}: ${title}` : (variant === 'log' ? 'log output' : `${lang} code`)}
          style={{
            margin: 0,
            padding: '10px 12px',
            display: 'grid',
            gridTemplateColumns: showLineNumbers ? 'auto 1fr' : '1fr',
            columnGap: showLineNumbers ? 'var(--sp-3)' : 0,
            whiteSpace: 'pre',
            tabSize: 2,
            overflow: 'visible',
            fontFamily: 'inherit',
          }}
        >
          {rows.map((row, i) => (
            <React.Fragment key={i}>
              {showLineNumbers && (
                <span
                  aria-hidden="true"
                  style={{
                    color: 'var(--text-faint)',
                    textAlign: 'right',
                    userSelect: 'none',
                    minWidth: `${gutterW}ch`,
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {i + 1}
                </span>
              )}
              <code
                style={{
                  fontFamily: 'inherit',
                  color: row.tone && toneInk[row.tone] ? toneInk[row.tone] : 'inherit',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {row.text.length ? row.text : ' '}
              </code>
            </React.Fragment>
          ))}
        </pre>
      </div>

      {/* polite announce for the copy action — AT hears it, eyes don't */}
      <span
        ref={liveRef}
        aria-live="polite"
        style={{
          position: 'absolute', width: 1, height: 1, padding: 0, margin: -1,
          overflow: 'hidden', clip: 'rect(0 0 0 0)', whiteSpace: 'nowrap', border: 0,
        }}
      />
    </figure>
  );
}

/** Imperative clipboard fallback for non-secure contexts / old browsers. */
function fallbackCopy(text, done) {
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'absolute';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    done && done();
  } catch (e) {
    /* clipboard unavailable — fail quiet, never throw into render */
  }
}

/** Reads prefers-reduced-motion live via matchMedia; SSR-safe. */
function usePrefersReducedMotion() {
  const query = '(prefers-reduced-motion: reduce)';
  const get = () =>
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia(query).matches
      : false;
  const [reduce, setReduce] = React.useState(get);
  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return undefined;
    const mq = window.matchMedia(query);
    const onChange = () => setReduce(mq.matches);
    if (mq.addEventListener) mq.addEventListener('change', onChange);
    else mq.addListener(onChange);
    return () => {
      if (mq.removeEventListener) mq.removeEventListener('change', onChange);
      else mq.removeListener(onChange);
    };
  }, []);
  return reduce;
}
