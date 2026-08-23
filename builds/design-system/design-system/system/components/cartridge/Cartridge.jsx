import React from 'react';

/**
 * Cartridge — the SandboxOS build object as a real, rotating 3D module.
 * The one place the flat UI breaks into dimension (dimension = ownership).
 * `kind` color-codes the label spine; supercolor is the maker's default.
 */
export function Cartridge({ title = 'Cartridge', subtitle = 'SBX-CART · build', serial = '001 / 500', kind = 'build', spineStyle, spin = true, width = 184, style, ...props }) {
  const D = Math.round(width * 0.18);
  const H = Math.round(width * 1.35);
  const spines = {
    build: 'var(--supercolor)',
    skill: 'linear-gradient(90deg, var(--cyan), var(--blue))',
    persona: 'linear-gradient(90deg, var(--magenta), var(--alert))',
  };
  const sp = spineStyle || spines[kind] || spines.build;
  const face = { position: 'absolute', top: '50%', left: '50%', overflow: 'hidden' };
  const fb = { ...face, width, height: H, marginLeft: -width / 2, marginTop: -H / 2 };
  const side = { ...face, width: D, height: H, marginLeft: -D / 2, marginTop: -H / 2 };
  const cap = { ...face, width, height: D, marginLeft: -width / 2, marginTop: -D / 2 };
  const ridge = { height: '100%', background: 'repeating-linear-gradient(0deg, rgba(0,0,0,.5) 0 3px, transparent 3px 7px)' };

  return (
    <div style={{ perspective: width * 6, width: width * 1.25, height: H * 1.25, display: 'flex', alignItems: 'center', justifyContent: 'center', ...style }} {...props}>
      <style>{`@keyframes sbxcartspin{from{transform:rotateY(0)}to{transform:rotateY(360deg)}}`}</style>
      <div style={{ transform: 'rotateX(-8deg)', transformStyle: 'preserve-3d' }}>
        <div
          style={{ width, height: H, position: 'relative', transformStyle: 'preserve-3d', animation: spin ? 'sbxcartspin 11s linear infinite' : undefined }}
          onMouseEnter={spin ? (e) => { e.currentTarget.style.animationDuration = '3.2s'; } : undefined}
          onMouseLeave={spin ? (e) => { e.currentTarget.style.animationDuration = '11s'; } : undefined}
          onPointerDown={spin ? (e) => { if (e.pointerType === 'touch' || e.pointerType === 'pen') { const t = e.currentTarget; const fast = t.style.animationDuration === '3.2s'; t.style.animationDuration = fast ? '11s' : '3.2s'; } } : undefined}
        >
          {/* front */}
          <div style={{ ...fb, transform: `translateZ(${D / 2}px)`, background: 'var(--hw-shell)', border: '2px solid var(--signal)', borderRadius: '14px 14px 4px 4px' }}>
            <div style={{ position: 'absolute', left: 11, right: 11, top: 14, background: 'var(--signal)', color: 'var(--ink)', border: '2px solid var(--ink)' }}>
              <div style={{ height: 12, background: sp, borderBottom: '2px solid var(--ink)' }} />
              <div style={{ padding: '8px 9px' }}>
                <div style={{ fontFamily: 'var(--font-display)', fontWeight: 900, fontSize: 'var(--t-lg)', lineHeight: 0.86, textTransform: 'uppercase' }}>{title}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, letterSpacing: '.05em', textTransform: 'uppercase', color: 'var(--hw-label-dim)', marginTop: 4 }}>{subtitle}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 12, fontFamily: 'var(--font-mono)', fontSize: 8 }}>
                  <span>{serial}<br />© NOBODY</span>
                  <span style={{ width: 30, height: 30, border: '1.5px solid var(--ink)', background: 'radial-gradient(var(--ink) 34%,transparent 35%) 0 0/3px 3px' }} />
                </div>
              </div>
            </div>
            <div style={{ position: 'absolute', left: 11, right: 11, bottom: 10, top: H * 0.62, border: '1.5px solid var(--crt-700)', borderRadius: 3 }} />
          </div>
          {/* back */}
          <div style={{ ...fb, transform: `rotateY(180deg) translateZ(${D / 2}px)`, background: 'var(--hw-shell-deep)', border: '2px solid var(--ash-500)', borderRadius: '14px 14px 4px 4px' }}>
            <div style={{ padding: 14, color: 'var(--ash-300)', fontFamily: 'var(--font-mono)', fontSize: 9, lineHeight: 1.6, textTransform: 'uppercase', letterSpacing: '.05em' }}>
              SANDBOX·OS<br />CARTRIDGE MODULE<br />—<br />insert · install · run<br />fork · own · ship<br /><br />made by hand<br />not licensed
            </div>
          </div>
          {/* sides */}
          <div style={{ ...side, transform: `rotateY(90deg) translateZ(${width / 2}px)`, background: 'linear-gradient(90deg,var(--hw-shell-lit),var(--hw-ridge))', borderTop: '2px solid var(--signal)', borderBottom: '2px solid var(--signal)' }}><div style={ridge} /></div>
          <div style={{ ...side, transform: `rotateY(-90deg) translateZ(${width / 2}px)`, background: 'linear-gradient(90deg,var(--hw-ridge),var(--hw-shell-lit))', borderTop: '2px solid var(--signal)', borderBottom: '2px solid var(--signal)' }}><div style={ridge} /></div>
          {/* top */}
          <div style={{ ...cap, transform: `rotateX(90deg) translateZ(${H / 2}px)`, background: 'var(--hw-shell-lit)', borderRadius: '6px 6px 0 0' }} />
          {/* bottom — gold pins */}
          <div style={{ ...cap, transform: `rotateX(-90deg) translateZ(${H / 2}px)`, background: 'var(--hw-shell)', display: 'flex', gap: 3, padding: '8px 30px' }}>
            {Array.from({ length: 8 }).map((_, i) => <span key={i} style={{ flex: 1, background: 'linear-gradient(180deg,var(--amber-glow),var(--amber-deep))' }} />)}
          </div>
        </div>
      </div>
    </div>
  );
}
