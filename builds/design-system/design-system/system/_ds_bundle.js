/* @ds-bundle: {"format":3,"namespace":"SandboxOSDesignSystem_4526c4","components":[{"name":"GhostEye","sourcePath":"components/brand/GhostEye.jsx"},{"name":"VHSHeadline","sourcePath":"components/brand/VHSHeadline.jsx"},{"name":"BootCoin","sourcePath":"components/cartridge/BootCoin.jsx"},{"name":"Cartridge","sourcePath":"components/cartridge/Cartridge.jsx"},{"name":"Avatar","sourcePath":"components/core/Avatar.jsx"},{"name":"Dialog","sourcePath":"components/core/Dialog.jsx"},{"name":"FaceToggle","sourcePath":"components/core/FaceToggle.jsx"},{"name":"Field","sourcePath":"components/core/Field.jsx"},{"name":"Loader","sourcePath":"components/core/Loader.jsx"},{"name":"SlapButton","sourcePath":"components/core/SlapButton.jsx"},{"name":"Toast","sourcePath":"components/core/Toast.jsx"},{"name":"Tooltip","sourcePath":"components/core/Tooltip.jsx"},{"name":"Window","sourcePath":"components/core/Window.jsx"},{"name":"Checkbox","sourcePath":"components/forms/Checkbox.jsx"},{"name":"Radio","sourcePath":"components/forms/Checkbox.jsx"},{"name":"Knob","sourcePath":"components/forms/Knob.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"},{"name":"Switch","sourcePath":"components/forms/Switch.jsx"},{"name":"Tabs","sourcePath":"components/forms/Tabs.jsx"},{"name":"CharacterSlap","sourcePath":"components/stickers/CharacterSlap.jsx"},{"name":"Sticker","sourcePath":"components/stickers/Sticker.jsx"},{"name":"Barcode","sourcePath":"components/stickers/Sticker.jsx"},{"name":"Table","sourcePath":"components/data/Table.jsx"},{"name":"List","sourcePath":"components/data/List.jsx"},{"name":"Stat","sourcePath":"components/data/Stat.jsx"},{"name":"KeyValue","sourcePath":"components/data/Stat.jsx"},{"name":"CodeBlock","sourcePath":"components/data/CodeBlock.jsx"},{"name":"Nav","sourcePath":"components/nav/Nav.jsx"},{"name":"Menu","sourcePath":"components/nav/Menu.jsx"},{"name":"Pagination","sourcePath":"components/nav/Pagination.jsx"}],"sourceHashes":{"components/brand/GhostEye.jsx":"3bf3d68ae0d2","components/brand/VHSHeadline.jsx":"4892653cda2d","components/cartridge/BootCoin.jsx":"ddaae6cb5648","components/cartridge/Cartridge.jsx":"d59d44b7f931","components/core/Avatar.jsx":"e7ffc3ecf4d6","components/core/Dialog.jsx":"e874b9cbc0ec","components/core/FaceToggle.jsx":"457825184469","components/core/Field.jsx":"098a32e16aaa","components/core/Loader.jsx":"9f78792a8396","components/core/SlapButton.jsx":"cd4e1d15d8fb","components/core/Toast.jsx":"26faef696137","components/core/Tooltip.jsx":"1c8f52a0d5ba","components/core/Window.jsx":"b915d88e4d78","components/forms/Checkbox.jsx":"052180c1bc90","components/forms/Knob.jsx":"950b4ab594cd","components/forms/Select.jsx":"190cce055136","components/forms/Switch.jsx":"470939b84883","components/forms/Tabs.jsx":"1c175b1466cc","components/stickers/CharacterSlap.jsx":"29ac5e2ac60b","components/stickers/Sticker.jsx":"486f2038882b","lib/dither.js":"31254d5b3495","lib/fx.js":"1cad332b2ab2","lib/sound.js":"395e436ac968","lib/substrate.js":"d5a056e87e49","ui_kits/mobile/ios-frame.jsx":"be3343be4b51","components/data/Table.jsx":"541aa314617e","components/data/List.jsx":"87b1b6ca6cd0","components/data/Stat.jsx":"0545b55f24df","components/data/CodeBlock.jsx":"bed158007d50","components/nav/Nav.jsx":"bb8e1636172a","components/nav/Menu.jsx":"e2e6227912af","components/nav/Pagination.jsx":"2194bc1d3fb6"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.SandboxOSDesignSystem_4526c4 = window.SandboxOSDesignSystem_4526c4 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/brand/GhostEye.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * GhostEye — the SandboxOS character as an ownable 1-bit dithered GAZE.
 * "always watching, never owned." A halftone eye, drawn + Floyd–Steinberg
 * dithered entirely in code (no asset). This is the always-present mascot —
 * the full seductive figure is reserved for hero/dossier slots via real art
 * through the same dither pipeline. Avoids the uncanny-bust trap.
 *
 * The pupil tracks the cursor when `watch`; she blinks on an interval.
 * One magenta accent (the iris) — color earned on her. Reduced-motion safe.
 */
function GhostEye({
  size = 180,
  accent = 'var(--magenta)',
  mood = 'rebel',
  watch = true,
  blink = true,
  style,
  ...rest
}) {
  const ref = React.useRef(null);
  const wrapRef = React.useRef(null);
  const target = React.useRef({
    x: 0,
    y: 0
  });
  const state = React.useRef({
    x: 0,
    y: 0,
    lid: 0
  });
  const resolve = c => {
    if (typeof c === 'string' && c.startsWith('var(')) {
      const v = getComputedStyle(document.documentElement).getPropertyValue(c.slice(4, -1).split(',')[0].trim()).trim();
      return v || '#FF2E88';
    }
    return c;
  };
  React.useEffect(() => {
    const cv = ref.current;
    if (!cv) return;
    const W = size,
      H = Math.round(size * 0.62);
    cv.width = W;
    cv.height = H;
    const ctx = cv.getContext('2d');
    const irisCol = resolve(accent);
    const RM = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let raf = 0,
      blinkT = performance.now() + 2600,
      lidV = 0,
      lidDir = 0;
    function hexRGB(h) {
      const n = parseInt(h.replace('#', ''), 16);
      return [n >> 16 & 255, n >> 8 & 255, n & 255];
    }
    const IRIS = hexRGB(irisCol.startsWith('#') ? irisCol : '#FF2E88');
    function draw(px, py, lid) {
      const off = document.createElement('canvas');
      off.width = W;
      off.height = H;
      const g = off.getContext('2d');
      g.clearRect(0, 0, W, H);
      const cx = W / 2,
        cy = H / 2,
        ew = W * 0.46,
        eh = H * 0.42;
      // eyeball white (almond)
      g.fillStyle = '#efe9da';
      g.beginPath();
      g.moveTo(cx - ew, cy);
      g.quadraticCurveTo(cx, cy - eh * 1.25, cx + ew, cy);
      g.quadraticCurveTo(cx, cy + eh * 1.25, cx - ew, cy);
      g.closePath();
      g.fill();
      // radial iris striations (drawn gray, keyed to accent after dither via overlay)
      const ix = cx + px * ew * 0.42,
        iy = cy + py * eh * 0.4,
        ir = eh * 0.92;
      const grd = g.createRadialGradient(ix, iy, 2, ix, iy, ir);
      grd.addColorStop(0, '#fff');
      grd.addColorStop(0.4, '#bbb');
      grd.addColorStop(1, '#666');
      g.save();
      g.beginPath();
      g.moveTo(cx - ew, cy);
      g.quadraticCurveTo(cx, cy - eh * 1.25, cx + ew, cy);
      g.quadraticCurveTo(cx, cy + eh * 1.25, cx - ew, cy);
      g.closePath();
      g.clip();
      g.fillStyle = grd;
      g.beginPath();
      g.arc(ix, iy, ir, 0, 7);
      g.fill();
      g.strokeStyle = 'rgba(255,255,255,0.5)';
      g.lineWidth = 1;
      for (let a = 0; a < 24; a++) {
        const an = a / 24 * Math.PI * 2;
        g.beginPath();
        g.moveTo(ix + Math.cos(an) * ir * 0.3, iy + Math.sin(an) * ir * 0.3);
        g.lineTo(ix + Math.cos(an) * ir, iy + Math.sin(an) * ir);
        g.stroke();
      }
      // pupil
      g.fillStyle = '#0a0a08';
      g.beginPath();
      g.arc(ix, iy, ir * 0.42, 0, 7);
      g.fill();
      // catchlight = the life
      g.fillStyle = '#fff';
      g.beginPath();
      g.arc(ix - ir * 0.22, iy - ir * 0.24, ir * 0.16, 0, 7);
      g.fill();
      g.restore();
      // lid (blink) — cover from top & bottom
      if (lid > 0.01) {
        g.fillStyle = '#0f0f0d';
        const c = lid * eh * 1.25;
        g.fillRect(cx - ew, cy - eh * 1.25, ew * 2, c);
        g.fillRect(cx - ew, cy + eh * 1.25 - c, ew * 2, c);
      }
      // upper lid line + lashes
      g.strokeStyle = '#0f0f0d';
      g.lineWidth = Math.max(2, W * 0.012);
      g.lineCap = 'round';
      g.beginPath();
      g.moveTo(cx - ew, cy);
      g.quadraticCurveTo(cx, cy - eh * 1.3, cx + ew, cy);
      g.stroke();
      g.lineWidth = Math.max(1, W * 0.006);
      g.beginPath();
      g.moveTo(cx + ew, cy);
      g.lineTo(cx + ew * 1.12, cy - eh * 0.4);
      g.stroke();
      g.beginPath();
      g.moveTo(cx - ew, cy);
      g.lineTo(cx - ew * 1.12, cy - eh * 0.35);
      g.stroke();

      // ---- dither pass (Floyd–Steinberg) ----
      const dd = g.getImageData(0, 0, W, H).data;
      const lum = new Float32Array(W * H),
        isIris = new Uint8Array(W * H);
      for (let i = 0; i < W * H; i++) {
        const a = dd[i * 4 + 3] / 255;
        lum[i] = a * ((0.299 * dd[i * 4] + 0.587 * dd[i * 4 + 1] + 0.114 * dd[i * 4 + 2]) / 255);
        // iris ring = mid-bright pixels inside iris radius → accent
        const x = i % W,
          y = i / W | 0;
        const din = Math.hypot(x - ix, y - iy);
        if (a > 0.5 && din < ir * 0.95 && din > ir * 0.42) isIris[i] = 1;
      }
      const buf = lum.slice();
      const out = new Uint8Array(W * H);
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        const i = y * W + x;
        const o = buf[i];
        const nv = o > 0.5 ? 1 : 0;
        out[i] = nv;
        const e = o - nv;
        if (x + 1 < W) buf[i + 1] += e * 7 / 16;
        if (y + 1 < H) {
          if (x > 0) buf[i - 1 + W] += e * 3 / 16;
          buf[i + W] += e * 5 / 16;
          if (x + 1 < W) buf[i + 1 + W] += e * 1 / 16;
        }
      }
      const im = ctx.createImageData(W, H),
        p = im.data;
      const bone = [246, 242, 231];
      for (let i = 0; i < W * H; i++) {
        if (out[i]) {
          const c = isIris[i] ? IRIS : bone;
          p[i * 4] = c[0];
          p[i * 4 + 1] = c[1];
          p[i * 4 + 2] = c[2];
          p[i * 4 + 3] = 255;
        }
      }
      ctx.clearRect(0, 0, W, H);
      ctx.putImageData(im, 0, 0);
    }
    function loop(now) {
      raf = requestAnimationFrame(loop);
      // ease pupil toward target
      state.current.x += (target.current.x - state.current.x) * 0.12;
      state.current.y += (target.current.y - state.current.y) * 0.12;
      // blink
      if (blink && !RM) {
        if (lidDir === 0 && now > blinkT) {
          lidDir = 1;
        }
        if (lidDir === 1) {
          lidV += 0.18;
          if (lidV >= 1) lidDir = -1;
        } else if (lidDir === -1) {
          lidV -= 0.18;
          if (lidV <= 0) {
            lidV = 0;
            lidDir = 0;
            blinkT = now + 2200 + Math.random() * 2600;
          }
        }
      }
      draw(state.current.x, state.current.y, lidV);
      if (RM) cancelAnimationFrame(raf);
    }
    raf = requestAnimationFrame(loop);
    let onMove = null;
    if (watch && !RM) {
      onMove = e => {
        const r = (wrapRef.current || cv).getBoundingClientRect();
        const cx = r.left + r.width / 2,
          cy = r.top + r.height / 2;
        target.current.x = Math.max(-1, Math.min(1, (e.clientX - cx) / (window.innerWidth / 2)));
        target.current.y = Math.max(-1, Math.min(1, (e.clientY - cy) / (window.innerHeight / 2)));
      };
      window.addEventListener('mousemove', onMove);
    }
    return () => {
      cancelAnimationFrame(raf);
      if (onMove) window.removeEventListener('mousemove', onMove);
    };
  }, [size, accent, watch, blink]);
  return /*#__PURE__*/React.createElement("span", _extends({
    ref: wrapRef,
    style: {
      display: 'inline-block',
      lineHeight: 0,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("canvas", {
    ref: ref,
    style: {
      width: size,
      height: Math.round(size * 0.62),
      imageRendering: 'pixelated'
    }
  }));
}
Object.assign(__ds_scope, { GhostEye });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/brand/GhostEye.jsx", error: String((e && e.message) || e) }); }

// components/brand/VHSHeadline.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * VHSHeadline — the poster voice as a component. Archivo Black, uppercase,
 * hard offset shadow, RGB chromatic-aberration split + a tracking jitter.
 * Words flagged `liveWords` glow in the earned accent. Lines rise on mount.
 * Reduced-motion safe (shows the settled end-state).
 */
function VHSHeadline({
  children,
  size = 'xl',
  align = 'left',
  liveWords = [],
  accent = 'var(--magenta)',
  split = true,
  shadow = true,
  style,
  ...rest
}) {
  const sizes = {
    lg: {
      fs: 'clamp(34px,6vw,52px)',
      sh: '4px 4px 0 #000'
    },
    xl: {
      fs: 'clamp(44px,8vw,76px)',
      sh: '5px 5px 0 #000'
    },
    '2xl': {
      fs: 'clamp(56px,11vw,104px)',
      sh: '6px 6px 0 #000'
    }
  };
  const s = sizes[size] || sizes.xl;
  // robustly flatten children to text (string | number | array | element) → kills [object Object]
  const flat = n => n == null || n === false || n === true ? '' : typeof n === 'string' || typeof n === 'number' ? String(n) : Array.isArray(n) ? n.map(flat).join('') : n.props && n.props.children != null ? flat(n.props.children) : '';
  const text = flat(children);
  const lines = text.split(/\s*\/\s*|\n/).map(l => l.trim()).filter(Boolean);
  const live = new Set(liveWords.map(w => w.toLowerCase()));
  const wrap = {
    margin: 0,
    textAlign: align,
    font: `900 ${s.fs}/0.9 var(--font-display)`,
    letterSpacing: '-0.03em',
    textTransform: 'uppercase',
    color: 'var(--signal)',
    textShadow: split ? `-3px 0 var(--magenta), 3px 0 var(--cyan)${shadow ? ', ' + s.sh : ''}` : shadow ? s.sh : 'none',
    ...style
  };
  return /*#__PURE__*/React.createElement("h2", _extends({
    style: wrap
  }, rest), lines.map((line, li) => /*#__PURE__*/React.createElement("span", {
    key: li,
    style: {
      display: 'block',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-block',
      animation: 'sbx-vhs-rise var(--dur-3) var(--ease-out) both',
      animationDelay: li * 0.08 + 's'
    }
  }, line.split(' ').map((word, wi, arr) => {
    const on = live.has(word.toLowerCase().replace(/[.,!?]/g, ''));
    return /*#__PURE__*/React.createElement(React.Fragment, {
      key: wi
    }, /*#__PURE__*/React.createElement("span", {
      style: on ? {
        color: accent,
        textShadow: `0 0 12px ${accent}`
      } : undefined
    }, word), wi < arr.length - 1 ? ' ' : '');
  })))), /*#__PURE__*/React.createElement("style", null, `@keyframes sbx-vhs-rise{from{transform:translateY(108%)}to{transform:translateY(0)}}
      @media (prefers-reduced-motion:reduce){h2 [style*="sbx-vhs-rise"]{animation:none!important}}`));
}
Object.assign(__ds_scope, { VHSHeadline });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/brand/VHSHeadline.jsx", error: String((e && e.message) || e) }); }

// components/cartridge/BootCoin.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * BootCoin — a minted 3D coin (the boot token / scar-coin / achievement).
 * Dimension = ownership: use for the boot key and milestone/error rewards.
 */
function BootCoin({
  size = 120,
  label = 'SBX',
  serial = '982-V7',
  glyph = '▚',
  tone = 'amber',
  spin = true,
  style,
  ...props
}) {
  const tones = {
    amber: 'var(--amber)',
    rebel: 'var(--magenta)',
    green: 'var(--green)',
    cyan: 'var(--cyan)'
  };
  const ink = tones[tone] || tones.amber;
  const faceBase = {
    position: 'absolute',
    inset: 0,
    borderRadius: '50%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    backfaceVisibility: 'hidden',
    background: 'radial-gradient(circle at 38% 32%, var(--hw-shell-lit), var(--hw-shell-deep) 75%)',
    border: `3px solid ${ink}`,
    boxShadow: `inset 0 0 ${size * 0.18}px rgba(0,0,0,0.7), 0 0 ${size * 0.14}px ${ink}`,
    color: ink,
    fontFamily: 'var(--font-crt)',
    textShadow: '0 0 8px currentColor'
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      perspective: size * 6,
      width: size,
      height: size,
      ...style
    }
  }, props), /*#__PURE__*/React.createElement("style", null, `@keyframes sbxcoinspin{from{transform:rotateY(0)}to{transform:rotateY(360deg)}}`), /*#__PURE__*/React.createElement("div", {
    style: {
      width: '100%',
      height: '100%',
      position: 'relative',
      transformStyle: 'preserve-3d',
      animation: spin ? 'sbxcoinspin 6s linear infinite' : undefined
    },
    onMouseEnter: spin ? e => {
      e.currentTarget.style.animationDuration = '1.6s';
    } : undefined,
    onMouseLeave: spin ? e => {
      e.currentTarget.style.animationDuration = '6s';
    } : undefined
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...faceBase,
      transform: 'translateZ(3px)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: size * 0.34,
      lineHeight: 1
    }
  }, glyph), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 900,
      fontSize: size * 0.16,
      letterSpacing: '.04em',
      marginTop: 2
    }
  }, label), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: size * 0.075,
      color: 'var(--ash-400)',
      textShadow: 'none',
      marginTop: 3
    }
  }, serial)), /*#__PURE__*/React.createElement("div", {
    style: {
      ...faceBase,
      transform: 'rotateY(180deg) translateZ(3px)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: size * 0.26,
      lineHeight: 1
    }
  }, "\u2726"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: size * 0.08,
      color: 'var(--ash-400)',
      textShadow: 'none',
      marginTop: 4,
      textTransform: 'uppercase',
      letterSpacing: '.1em'
    }
  }, "\xA9 nobody"))));
}
Object.assign(__ds_scope, { BootCoin });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/cartridge/BootCoin.jsx", error: String((e && e.message) || e) }); }

// components/cartridge/Cartridge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Cartridge — the SandboxOS build object as a real, rotating 3D module.
 * The one place the flat UI breaks into dimension (dimension = ownership).
 * `kind` color-codes the label spine; supercolor is the maker's default.
 */
function Cartridge({
  title = 'Cartridge',
  subtitle = 'SBX-CART · build',
  serial = '001 / 500',
  kind = 'build',
  spineStyle,
  spin = true,
  width = 184,
  style,
  ...props
}) {
  const D = Math.round(width * 0.18);
  const H = Math.round(width * 1.35);
  const spines = {
    build: 'var(--supercolor)',
    skill: 'linear-gradient(90deg, var(--cyan), var(--blue))',
    persona: 'linear-gradient(90deg, var(--magenta), var(--alert))'
  };
  const sp = spineStyle || spines[kind] || spines.build;
  const face = {
    position: 'absolute',
    top: '50%',
    left: '50%',
    overflow: 'hidden'
  };
  const fb = {
    ...face,
    width,
    height: H,
    marginLeft: -width / 2,
    marginTop: -H / 2
  };
  const side = {
    ...face,
    width: D,
    height: H,
    marginLeft: -D / 2,
    marginTop: -H / 2
  };
  const cap = {
    ...face,
    width,
    height: D,
    marginLeft: -width / 2,
    marginTop: -D / 2
  };
  const ridge = {
    height: '100%',
    background: 'repeating-linear-gradient(0deg, rgba(0,0,0,.5) 0 3px, transparent 3px 7px)'
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      perspective: width * 6,
      width: width * 1.25,
      height: H * 1.25,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      ...style
    }
  }, props), /*#__PURE__*/React.createElement("style", null, `@keyframes sbxcartspin{from{transform:rotateY(0)}to{transform:rotateY(360deg)}}`), /*#__PURE__*/React.createElement("div", {
    style: {
      transform: 'rotateX(-8deg)',
      transformStyle: 'preserve-3d'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width,
      height: H,
      position: 'relative',
      transformStyle: 'preserve-3d',
      animation: spin ? 'sbxcartspin 11s linear infinite' : undefined
    },
    onMouseEnter: spin ? e => {
      e.currentTarget.style.animationDuration = '3.2s';
    } : undefined,
    onMouseLeave: spin ? e => {
      e.currentTarget.style.animationDuration = '11s';
    } : undefined,
    onPointerDown: spin ? e => {
      if (e.pointerType === 'touch' || e.pointerType === 'pen') {
        const t = e.currentTarget;
        const fast = t.style.animationDuration === '3.2s';
        t.style.animationDuration = fast ? '11s' : '3.2s';
      }
    } : undefined
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...fb,
      transform: `translateZ(${D / 2}px)`,
      background: 'var(--hw-shell)',
      border: '2px solid var(--signal)',
      borderRadius: '14px 14px 4px 4px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 11,
      right: 11,
      top: 14,
      background: 'var(--signal)',
      color: 'var(--ink)',
      border: '2px solid var(--ink)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      height: 12,
      background: sp,
      borderBottom: '2px solid var(--ink)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '8px 9px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 900,
      fontSize: 'var(--t-lg)',
      lineHeight: 0.86,
      textTransform: 'uppercase'
    }
  }, title), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 8.5,
      letterSpacing: '.05em',
      textTransform: 'uppercase',
      color: 'var(--hw-label-dim)',
      marginTop: 4
    }
  }, subtitle), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-end',
      marginTop: 12,
      fontFamily: 'var(--font-mono)',
      fontSize: 8
    }
  }, /*#__PURE__*/React.createElement("span", null, serial, /*#__PURE__*/React.createElement("br", null), "\xA9 NOBODY"), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 30,
      height: 30,
      border: '1.5px solid var(--ink)',
      background: 'radial-gradient(var(--ink) 34%,transparent 35%) 0 0/3px 3px'
    }
  })))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 11,
      right: 11,
      bottom: 10,
      top: H * 0.62,
      border: '1.5px solid var(--crt-700)',
      borderRadius: 3
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      ...fb,
      transform: `rotateY(180deg) translateZ(${D / 2}px)`,
      background: 'var(--hw-shell-deep)',
      border: '2px solid var(--ash-500)',
      borderRadius: '14px 14px 4px 4px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 14,
      color: 'var(--ash-300)',
      fontFamily: 'var(--font-mono)',
      fontSize: 9,
      lineHeight: 1.6,
      textTransform: 'uppercase',
      letterSpacing: '.05em'
    }
  }, "SANDBOX\xB7OS", /*#__PURE__*/React.createElement("br", null), "CARTRIDGE MODULE", /*#__PURE__*/React.createElement("br", null), "\u2014", /*#__PURE__*/React.createElement("br", null), "insert \xB7 install \xB7 run", /*#__PURE__*/React.createElement("br", null), "fork \xB7 own \xB7 ship", /*#__PURE__*/React.createElement("br", null), /*#__PURE__*/React.createElement("br", null), "made by hand", /*#__PURE__*/React.createElement("br", null), "not licensed")), /*#__PURE__*/React.createElement("div", {
    style: {
      ...side,
      transform: `rotateY(90deg) translateZ(${width / 2}px)`,
      background: 'linear-gradient(90deg,var(--hw-shell-lit),var(--hw-ridge))',
      borderTop: '2px solid var(--signal)',
      borderBottom: '2px solid var(--signal)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: ridge
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      ...side,
      transform: `rotateY(-90deg) translateZ(${width / 2}px)`,
      background: 'linear-gradient(90deg,var(--hw-ridge),var(--hw-shell-lit))',
      borderTop: '2px solid var(--signal)',
      borderBottom: '2px solid var(--signal)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: ridge
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      ...cap,
      transform: `rotateX(90deg) translateZ(${H / 2}px)`,
      background: 'var(--hw-shell-lit)',
      borderRadius: '6px 6px 0 0'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      ...cap,
      transform: `rotateX(-90deg) translateZ(${H / 2}px)`,
      background: 'var(--hw-shell)',
      display: 'flex',
      gap: 3,
      padding: '8px 30px'
    }
  }, Array.from({
    length: 8
  }).map((_, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    style: {
      flex: 1,
      background: 'linear-gradient(180deg,var(--amber-glow),var(--amber-deep))'
    }
  }))))));
}
Object.assign(__ds_scope, { Cartridge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/cartridge/Cartridge.jsx", error: String((e && e.message) || e) }); }

// components/core/Avatar.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Avatar — a die-cut frame holding the character (a kaomoji mood) or initials.
 * Optional status dot + serial. The rebel, woven in at avatar scale.
 */
function Avatar({
  face = '⌐■_■',
  initials,
  size = 44,
  status,
  serial,
  style,
  ...props
}) {
  const statusColors = {
    online: 'var(--green)',
    building: 'var(--amber)',
    away: 'var(--ash-500)',
    rebel: 'var(--magenta)'
  };
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      position: 'relative',
      display: 'inline-flex',
      ...style
    }
  }, props), /*#__PURE__*/React.createElement("span", {
    style: {
      width: size,
      height: size,
      border: '2px solid var(--signal)',
      background: 'var(--crt-900)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: '0 0 0 3px var(--ink), 3px 3px 0 rgba(0,0,0,0.5)',
      fontFamily: initials ? 'var(--font-display)' : 'var(--font-crt)',
      fontWeight: 900,
      color: 'var(--magenta)',
      fontSize: initials ? size * 0.4 : size * 0.34,
      textShadow: '0 0 8px var(--glow-magenta)',
      overflow: 'hidden'
    }
  }, initials || face), status && /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      right: -3,
      bottom: -3,
      width: 12,
      height: 12,
      borderRadius: '50%',
      border: '2px solid var(--ink)',
      background: statusColors[status] || statusColors.online
    }
  }), serial && /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      left: 0,
      bottom: -13,
      fontFamily: 'var(--font-mono)',
      fontSize: 7,
      color: 'var(--ash-500)',
      letterSpacing: '.06em',
      whiteSpace: 'nowrap'
    }
  }, serial));
}
Object.assign(__ds_scope, { Avatar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Avatar.jsx", error: String((e && e.message) || e) }); }

// components/core/FaceToggle.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * FaceToggle — the character switch. Her face is the knob: off she watches
 * `(•_•)`, on she's locked in `⌐■_■`. Controlled or uncontrolled.
 */
function FaceToggle({
  checked,
  onChange,
  faces = {
    off: '•_•',
    on: '■_■'
  },
  style,
  ...props
}) {
  const [internal, setInternal] = React.useState(!!checked);
  const isOn = checked != null ? checked : internal;
  const toggle = () => {
    const v = !isOn;
    if (checked == null) setInternal(v);
    onChange && onChange(v);
  };
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    onClick: toggle,
    "aria-pressed": isOn,
    style: {
      width: 80,
      height: 34,
      border: `2px solid ${isOn ? 'var(--magenta)' : 'var(--signal)'}`,
      background: isOn ? 'var(--magenta)' : 'var(--bg-sunken)',
      display: 'flex',
      alignItems: 'center',
      padding: 2,
      cursor: 'pointer',
      ...style
    }
  }, props), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 30,
      height: 26,
      background: isOn ? 'var(--ink)' : 'var(--signal)',
      color: isOn ? 'var(--magenta)' : 'var(--ink)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'var(--font-crt)',
      fontSize: 'var(--t-sm)',
      transform: isOn ? 'translateX(44px)' : 'translateX(0)',
      transition: 'transform 160ms var(--ease-snap)'
    }
  }, isOn ? faces.on : faces.off));
}
Object.assign(__ds_scope, { FaceToggle });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/FaceToggle.jsx", error: String((e && e.message) || e) }); }

// components/core/Field.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Field — a terminal-style input. Amber prompt prefix + blinking caret.
 */
function Field({
  label,
  prefix = '>',
  placeholder,
  style,
  ...props
}) {
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'block',
      fontFamily: 'var(--font-mono)',
      ...style
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'block',
      fontSize: 'var(--t-2xs)',
      textTransform: 'uppercase',
      letterSpacing: 'var(--ls-wide)',
      color: 'var(--text-faint)',
      marginBottom: 5
    }
  }, label), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      border: '2px solid var(--border-strong)',
      background: 'var(--bg-sunken)',
      padding: '7px 10px'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--amber)'
    }
  }, prefix), /*#__PURE__*/React.createElement("input", _extends({
    placeholder: placeholder,
    style: {
      flex: 1,
      minWidth: 0,
      background: 'transparent',
      border: 0,
      color: 'var(--text)',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-sm)',
      outline: 'none'
    }
  }, props)), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 8,
      height: 15,
      background: 'var(--amber)',
      animation: 'sbx-blink 1s steps(1) infinite',
      boxShadow: '0 0 6px var(--glow-amber)'
    }
  })));
}
Object.assign(__ds_scope, { Field });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Field.jsx", error: String((e && e.message) || e) }); }

// components/core/Loader.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Loader — the CRT "THANK YOU FOR USING" progress bar. Indeterminate when
 * `value` is null, otherwise a 0–100 fill. Phosphor amber.
 */
function Loader({
  value = null,
  label = 'LOADING',
  caption = 'THANK YOU FOR USING',
  width = 220,
  style,
  ...props
}) {
  const pct = value == null ? null : Math.max(0, Math.min(100, value));
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      fontFamily: 'var(--font-crt)',
      color: 'var(--amber)',
      width,
      ...style
    }
  }, props), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      fontSize: 'var(--t-base)',
      letterSpacing: 'var(--ls-wide)'
    }
  }, /*#__PURE__*/React.createElement("span", null, label, pct == null ? '…' : ''), /*#__PURE__*/React.createElement("span", null, pct == null ? '' : pct + '%')), /*#__PURE__*/React.createElement("div", {
    style: {
      height: 12,
      border: '1px solid var(--amber-deep)',
      marginTop: 4,
      overflow: 'hidden',
      background: 'var(--bg-sunken)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      height: '100%',
      width: pct == null ? '40%' : pct + '%',
      background: 'repeating-linear-gradient(90deg, var(--amber) 0 6px, transparent 6px 10px)',
      boxShadow: '0 0 8px var(--glow-amber)',
      animation: pct == null ? 'sbx-loader-indef 1.1s linear infinite' : undefined
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--t-sm)',
      letterSpacing: 'var(--ls-mega)',
      marginTop: 5,
      color: 'var(--amber-deep)'
    }
  }, caption), /*#__PURE__*/React.createElement("style", null, '@keyframes sbx-loader-indef{0%{margin-left:-40%}100%{margin-left:100%}}'));
}
Object.assign(__ds_scope, { Loader });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Loader.jsx", error: String((e && e.message) || e) }); }

// components/core/SlapButton.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * SlapButton — the SandboxOS button: a die-cut sticker slap.
 * Hard 2px border, hard offset shadow, presses DOWN like a real slap.
 * Mono by default; color is earned via `tone`.
 */
function SlapButton({
  children,
  tone = 'default',
  size = 'md',
  block = false,
  disabled = false,
  rotate = 0,
  style,
  ...props
}) {
  const [hover, setHover] = React.useState(false);
  const [press, setPress] = React.useState(false);
  const tones = {
    default: {
      bg: 'var(--signal)',
      fg: 'var(--ink)',
      edge: 'var(--ink)',
      sh: 'var(--signal)'
    },
    ghost: {
      bg: 'transparent',
      fg: 'var(--signal)',
      edge: 'var(--signal)',
      sh: 'var(--crt-700)'
    },
    go: {
      bg: 'var(--amber)',
      fg: 'var(--ink)',
      edge: 'var(--ink)',
      sh: 'var(--amber-deep)'
    },
    rebel: {
      bg: 'var(--magenta)',
      fg: 'var(--signal)',
      edge: 'var(--ink)',
      sh: 'var(--magenta-deep)'
    },
    ok: {
      bg: 'var(--green)',
      fg: 'var(--ink)',
      edge: 'var(--ink)',
      sh: 'var(--green-deep)'
    },
    danger: {
      bg: 'var(--alert)',
      fg: 'var(--signal)',
      edge: 'var(--ink)',
      sh: 'var(--ink)'
    }
  };
  const sizes = {
    sm: {
      pad: '4px 10px',
      fs: 'var(--t-xs)',
      sh: 2
    },
    md: {
      pad: '7px 15px',
      fs: 'var(--t-sm)',
      sh: 3
    },
    lg: {
      pad: '11px 22px',
      fs: 'var(--t-md)',
      sh: 4
    }
  };
  const t = tones[tone] || tones.default;
  const s = sizes[size] || sizes.md;
  const off = press ? 0 : hover ? s.sh - 1 : s.sh;
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    disabled: disabled,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => {
      setHover(false);
      setPress(false);
    },
    onMouseDown: () => setPress(true),
    onMouseUp: () => setPress(false),
    style: {
      display: block ? 'flex' : 'inline-flex',
      width: block ? '100%' : undefined,
      alignItems: 'center',
      justifyContent: 'center',
      gap: '7px',
      fontFamily: 'var(--font-display)',
      fontWeight: 900,
      fontSize: s.fs,
      letterSpacing: 'var(--ls-wide)',
      textTransform: 'uppercase',
      color: t.fg,
      background: t.bg,
      border: `2px solid ${t.edge}`,
      borderRadius: 0,
      padding: s.pad,
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.4 : 1,
      boxShadow: `${off}px ${off}px 0 ${t.sh}`,
      transform: `translate(${s.sh - off}px, ${s.sh - off}px) rotate(${rotate}deg)`,
      transition: 'box-shadow 90ms var(--ease-snap), transform 90ms var(--ease-snap)',
      userSelect: 'none',
      ...style
    }
  }, props), children);
}
Object.assign(__ds_scope, { SlapButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/SlapButton.jsx", error: String((e && e.message) || e) }); }

// components/core/Toast.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Toast — a talk-back aside in the character's voice. Color is earned via tone.
 */
function Toast({
  title,
  children,
  tone = 'rebel',
  glyph = '✦',
  style,
  ...props
}) {
  const tones = {
    rebel: 'var(--magenta)',
    alert: 'var(--alert)',
    ok: 'var(--green)',
    info: 'var(--cyan)',
    warn: 'var(--hazard)'
  };
  const ic = tones[tone] || tones.rebel;
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'stretch',
      border: '2px solid var(--signal)',
      background: 'var(--bg-raised)',
      maxWidth: 300,
      fontFamily: 'var(--font-mono)',
      ...style
    }
  }, props), /*#__PURE__*/React.createElement("div", {
    style: {
      width: 34,
      background: ic,
      color: 'var(--ink)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'var(--font-crt)',
      fontSize: 'var(--t-md)'
    }
  }, glyph), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '7px 11px',
      fontSize: 'var(--t-xs)',
      lineHeight: 1.45,
      color: 'var(--text)'
    }
  }, title && /*#__PURE__*/React.createElement("b", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 900,
      textTransform: 'uppercase',
      display: 'block',
      fontSize: 'var(--t-xs)'
    }
  }, title), children));
}
Object.assign(__ds_scope, { Toast });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Toast.jsx", error: String((e && e.message) || e) }); }

// components/core/Tooltip.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Tooltip — a die-cut slap that pops on hover. */
function Tooltip({
  label,
  children,
  tone = 'ink',
  side = 'top',
  style,
  ...props
}) {
  const [show, setShow] = React.useState(false);
  const tones = {
    ink: {
      bg: 'var(--ink)',
      fg: 'var(--signal)'
    },
    amber: {
      bg: 'var(--amber)',
      fg: 'var(--ink)'
    },
    rebel: {
      bg: 'var(--magenta)',
      fg: 'var(--signal)'
    }
  };
  const t = tones[tone] || tones.ink;
  const pos = side === 'top' ? {
    bottom: '100%',
    left: '50%',
    transform: 'translateX(-50%) translateY(-7px)'
  } : {
    top: '100%',
    left: '50%',
    transform: 'translateX(-50%) translateY(7px)'
  };
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      position: 'relative',
      display: 'inline-flex'
    },
    onMouseEnter: () => setShow(true),
    onMouseLeave: () => setShow(false)
  }, props), children, show && /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      ...pos,
      zIndex: 100,
      whiteSpace: 'nowrap',
      fontFamily: 'var(--font-display)',
      fontWeight: 900,
      fontSize: 'var(--t-2xs)',
      textTransform: 'uppercase',
      letterSpacing: 'var(--ls-wide)',
      background: t.bg,
      color: t.fg,
      border: '2px solid var(--ink)',
      padding: '3px 8px',
      boxShadow: '0 0 0 2px var(--signal), 2px 3px 0 rgba(0,0,0,0.5)',
      ...style
    }
  }, label));
}
Object.assign(__ds_scope, { Tooltip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tooltip.jsx", error: String((e && e.message) || e) }); }

// components/core/Window.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Window — the SandboxOS window/panel frame. Inverted title bar, hard
 * border + offset shadow. `tone="blue"` is the bootleg error-screen takeover.
 */
function Window({
  title = 'SANDBOX_OS',
  children,
  onClose,
  width,
  tone = 'mono',
  tilt = 0,
  footer,
  style,
  ...props
}) {
  const blue = tone === 'blue';
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      width,
      border: '2px solid var(--signal)',
      background: blue ? 'var(--blue)' : 'var(--bg-raised)',
      boxShadow: '5px 5px 0 rgba(0,0,0,0.55)',
      transform: tilt ? `rotate(${tilt}deg)` : undefined,
      fontFamily: 'var(--font-mono)',
      ...style
    }
  }, props), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      background: 'var(--signal)',
      color: 'var(--ink)',
      fontWeight: 700,
      fontSize: 'var(--t-xs)',
      padding: '3px 8px',
      letterSpacing: 'var(--ls-wide)',
      textTransform: 'uppercase'
    }
  }, /*#__PURE__*/React.createElement("span", null, title), /*#__PURE__*/React.createElement("span", {
    onClick: onClose,
    role: onClose ? 'button' : undefined,
    style: {
      border: '1.5px solid var(--ink)',
      width: 14,
      height: 14,
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: 10,
      cursor: onClose ? 'pointer' : 'default'
    }
  }, "\u2715")), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '13px 14px',
      color: blue ? 'var(--signal)' : 'var(--text)',
      fontSize: 'var(--t-sm)',
      lineHeight: 1.55
    }
  }, children), footer && /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '0 14px 13px'
    }
  }, footer));
}
Object.assign(__ds_scope, { Window });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Window.jsx", error: String((e && e.message) || e) }); }

// components/core/Dialog.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Dialog — a talk-back dialog. The machine speaks in its own voice and
 * offers slap actions. `glyph` = a CRT kaomoji aside (the character).
 */
function Dialog({
  title = '⚠ NOTICE',
  children,
  actions = [],
  tone = 'mono',
  glyph,
  ...props
}) {
  return /*#__PURE__*/React.createElement(__ds_scope.Window, _extends({
    title: title,
    tone: tone,
    footer: actions.length ? /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: '8px',
        flexWrap: 'wrap'
      }
    }, actions.map((a, i) => /*#__PURE__*/React.createElement(__ds_scope.SlapButton, {
      key: i,
      size: "sm",
      tone: a.tone || (i === 0 ? 'default' : 'ghost'),
      onClick: a.onClick
    }, a.label))) : null
  }, props), glyph && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-crt)',
      color: 'var(--magenta)',
      fontSize: 'var(--t-lg)',
      marginBottom: 6
    }
  }, glyph), /*#__PURE__*/React.createElement("div", null, children));
}
Object.assign(__ds_scope, { Dialog });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Dialog.jsx", error: String((e && e.message) || e) }); }

// components/forms/Checkbox.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Checkbox — die-cut box, amber ✕ when checked. */
function Checkbox({
  checked,
  onChange,
  label,
  disabled,
  style,
  ...props
}) {
  const [on, setOn] = React.useState(!!checked);
  const v = checked != null ? checked : on;
  const toggle = () => {
    if (disabled) return;
    if (checked == null) setOn(!v);
    onChange && onChange(!v);
  };
  return /*#__PURE__*/React.createElement("label", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 9,
      cursor: disabled ? 'not-allowed' : 'pointer',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-sm)',
      color: 'var(--text)',
      opacity: disabled ? 0.4 : 1,
      ...style
    }
  }, props), /*#__PURE__*/React.createElement("span", {
    onClick: toggle,
    style: {
      width: 18,
      height: 18,
      flex: 'none',
      border: '2px solid var(--signal)',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: v ? 'var(--amber)' : 'var(--bg-sunken)',
      color: 'var(--ink)',
      fontFamily: 'var(--font-crt)',
      fontSize: 14,
      lineHeight: 1
    }
  }, v ? '✕' : ''), label);
}

/** Radio — round die-cut, magenta dot when selected. */
function Radio({
  checked,
  onChange,
  label,
  name,
  value,
  disabled,
  style,
  ...props
}) {
  return /*#__PURE__*/React.createElement("label", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 9,
      cursor: disabled ? 'not-allowed' : 'pointer',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-sm)',
      color: 'var(--text)',
      opacity: disabled ? 0.4 : 1,
      ...style
    }
  }, props), /*#__PURE__*/React.createElement("span", {
    onClick: () => !disabled && onChange && onChange(value),
    style: {
      width: 18,
      height: 18,
      flex: 'none',
      borderRadius: '50%',
      border: '2px solid var(--signal)',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-sunken)'
    }
  }, checked && /*#__PURE__*/React.createElement("span", {
    style: {
      width: 9,
      height: 9,
      borderRadius: '50%',
      background: 'var(--magenta)',
      boxShadow: '0 0 6px var(--glow-magenta)'
    }
  })), label);
}
Object.assign(__ds_scope, { Checkbox, Radio });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/forms/Knob.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Knob — the cassette-deck / instrument dial. Drag vertically (or use the
 * wheel) to turn it through `min`..`max`. A hardware control for the
 * sovereign machine — labeled MEMORY / SCARS / VIBES / AGENCY, etc.
 */
function Knob({
  value,
  defaultValue = 0.5,
  min = 0,
  max = 1,
  label,
  size = 56,
  accent = 'var(--amber)',
  onChange,
  style,
  ...rest
}) {
  const [internal, setInternal] = React.useState(defaultValue);
  const v = value != null ? value : internal;
  const norm = (v - min) / (max - min);
  const angle = -135 + norm * 270; // -135°..+135°
  const ref = React.useRef(null);
  const drag = React.useRef(null);
  const set = nv => {
    nv = Math.max(min, Math.min(max, nv));
    if (value == null) setInternal(nv);
    onChange && onChange(nv);
  };
  const onDown = e => {
    e.preventDefault();
    const startY = e.touches ? e.touches[0].clientY : e.clientY;
    drag.current = {
      y: startY,
      v
    };
    const mv = ev => {
      const cy = ev.touches ? ev.touches[0].clientY : ev.clientY;
      const dy = drag.current.y - cy;
      set(drag.current.v + dy / 120 * (max - min));
      if (ev.cancelable) ev.preventDefault();
    };
    const up = () => {
      window.removeEventListener('pointermove', mv);
      window.removeEventListener('pointerup', up);
      window.removeEventListener('touchmove', mv);
      window.removeEventListener('touchend', up);
    };
    window.addEventListener('pointermove', mv);
    window.addEventListener('pointerup', up);
    window.addEventListener('touchmove', mv, {
      passive: false
    });
    window.addEventListener('touchend', up);
  };
  const onWheel = e => {
    e.preventDefault();
    set(v + (e.deltaY < 0 ? 1 : -1) * (max - min) * 0.05);
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'inline-flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 6,
      fontFamily: 'var(--font-mono)',
      userSelect: 'none',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    ref: ref,
    role: "slider",
    "aria-valuenow": v,
    "aria-valuemin": min,
    "aria-valuemax": max,
    tabIndex: 0,
    onPointerDown: onDown,
    onWheel: onWheel,
    onKeyDown: e => {
      if (e.key === 'ArrowUp' || e.key === 'ArrowRight') set(v + (max - min) * 0.05);
      if (e.key === 'ArrowDown' || e.key === 'ArrowLeft') set(v - (max - min) * 0.05);
    },
    style: {
      width: size,
      height: size,
      borderRadius: '50%',
      position: 'relative',
      cursor: 'ns-resize',
      touchAction: 'none',
      background: 'conic-gradient(from 200deg, var(--hw-shell-lit), var(--hw-ridge) 60%, var(--hw-shell-lit))',
      border: '2px solid var(--ink)',
      boxShadow: '0 3px 6px rgba(0,0,0,0.6), inset 0 0 0 2px var(--crt-700)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      top: '12%',
      left: '50%',
      width: 2,
      height: '32%',
      background: accent,
      transformOrigin: '50% 130%',
      transform: `translateX(-50%) rotate(${angle}deg)`,
      boxShadow: `0 0 5px ${accent}`
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      inset: -5,
      borderRadius: '50%',
      border: '1px dashed var(--crt-700)'
    }
  })), label && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 9,
      color: 'var(--ash-400)',
      textTransform: 'uppercase',
      letterSpacing: '0.08em'
    }
  }, label));
}
Object.assign(__ds_scope, { Knob });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Knob.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Select — a mono dropdown with a hard caret. */
function Select({
  options = [],
  value,
  onChange,
  label,
  style,
  ...props
}) {
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'inline-block',
      fontFamily: 'var(--font-mono)',
      ...style
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'block',
      fontSize: 'var(--t-2xs)',
      textTransform: 'uppercase',
      letterSpacing: 'var(--ls-wide)',
      color: 'var(--text-faint)',
      marginBottom: 5
    }
  }, label), /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'relative',
      display: 'inline-flex',
      alignItems: 'center',
      border: '2px solid var(--border-strong)',
      background: 'var(--bg-sunken)'
    }
  }, /*#__PURE__*/React.createElement("select", _extends({
    value: value,
    onChange: onChange,
    style: {
      appearance: 'none',
      WebkitAppearance: 'none',
      background: 'transparent',
      border: 0,
      color: 'var(--text)',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-sm)',
      padding: '7px 34px 7px 11px',
      outline: 'none',
      cursor: 'pointer'
    }
  }, props), options.map((o, i) => /*#__PURE__*/React.createElement("option", {
    key: i,
    value: typeof o === 'object' ? o.value : o,
    style: {
      background: 'var(--crt-900)'
    }
  }, typeof o === 'object' ? o.label : o))), /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      right: 0,
      top: 0,
      bottom: 0,
      width: 26,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderLeft: '2px solid var(--border-strong)',
      color: 'var(--amber)',
      fontFamily: 'var(--font-crt)',
      pointerEvents: 'none'
    }
  }, "\u25BE")));
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// components/forms/Switch.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Switch — a hard-edged power switch (rocker). Snaps; amber when on. Use for
 * binary system settings (sound, sovereign mode). For the character-flavored
 * variant use FaceToggle instead.
 */
function Switch({
  checked,
  onChange,
  label,
  disabled,
  accent = 'var(--amber)',
  style,
  ...rest
}) {
  const [on, setOn] = React.useState(!!checked);
  const v = checked != null ? checked : on;
  const toggle = () => {
    if (disabled) return;
    if (checked == null) setOn(!v);
    onChange && onChange(!v);
  };
  return /*#__PURE__*/React.createElement("label", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 10,
      cursor: disabled ? 'not-allowed' : 'pointer',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-sm,12px)',
      color: 'var(--text)',
      opacity: disabled ? 0.4 : 1,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("span", {
    onClick: toggle,
    "aria-checked": v,
    role: "switch",
    style: {
      width: 46,
      height: 24,
      flex: 'none',
      border: '2px solid var(--signal)',
      background: v ? accent : 'var(--bg-sunken)',
      display: 'flex',
      alignItems: 'center',
      padding: 2,
      transition: 'background var(--dur-1) var(--ease-snap)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 16,
      height: 16,
      background: v ? 'var(--ink)' : 'var(--signal)',
      transform: v ? 'translateX(22px)' : 'translateX(0)',
      transition: 'transform var(--dur-2) var(--ease-snap)'
    }
  })), label);
}
Object.assign(__ds_scope, { Switch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Switch.jsx", error: String((e && e.message) || e) }); }

// components/forms/Tabs.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Tabs — teletext-style segmented tabs (STAT · INV · DATA). Inverted active. */
function Tabs({
  tabs = [],
  value,
  onChange,
  style,
  ...props
}) {
  const [i, setI] = React.useState(0);
  const active = value != null ? value : i;
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      borderBottom: '2px solid var(--signal)',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-xs)',
      ...style
    }
  }, props), tabs.map((t, idx) => /*#__PURE__*/React.createElement("button", {
    key: idx,
    type: "button",
    onClick: () => {
      if (value == null) setI(idx);
      onChange && onChange(idx);
    },
    style: {
      padding: '5px 13px',
      border: 0,
      cursor: 'pointer',
      textTransform: 'uppercase',
      letterSpacing: 'var(--ls-wide)',
      fontFamily: 'inherit',
      fontSize: 'inherit',
      fontWeight: idx === active ? 700 : 400,
      background: idx === active ? 'var(--signal)' : 'transparent',
      color: idx === active ? 'var(--ink)' : 'var(--text-dim)'
    }
  }, t)));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Tabs.jsx", error: String((e && e.message) || e) }); }

// components/stickers/CharacterSlap.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * CharacterSlap — a posed die-cut character mood badge. The rebel's slaps:
 * a kaomoji + a line in her voice. Usable as award, callout, easter-egg.
 */
function CharacterSlap({
  face = '⌐■_■',
  label = "nobody's tool",
  tone = 'rebel',
  rotate = -5,
  style,
  ...props
}) {
  const tones = {
    rebel: {
      bg: 'var(--ink)',
      face: 'var(--magenta)',
      label: 'var(--signal)'
    },
    cool: {
      bg: 'var(--signal)',
      face: 'var(--blue)',
      label: 'var(--ink)'
    },
    go: {
      bg: 'var(--ink)',
      face: 'var(--cyan)',
      label: 'var(--signal)'
    },
    hazard: {
      bg: 'var(--hazard)',
      face: 'var(--ink)',
      label: 'var(--ink)'
    }
  };
  const t = tones[tone] || tones.rebel;
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: 'inline-flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 3,
      background: t.bg,
      border: '2px solid var(--ink)',
      padding: '8px 10px 5px',
      minWidth: 78,
      boxShadow: '0 0 0 3px var(--signal), 3px 3px 0 rgba(0,0,0,0.5)',
      transform: `rotate(${rotate}deg)`,
      ...style
    }
  }, props), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-crt)',
      fontSize: 'var(--t-lg)',
      lineHeight: 1,
      color: t.face,
      textShadow: tone === 'cool' ? 'none' : '0 0 8px currentColor'
    }
  }, face), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 900,
      fontSize: 9,
      textTransform: 'uppercase',
      letterSpacing: '.02em',
      textAlign: 'center',
      color: t.label
    }
  }, label));
}
Object.assign(__ds_scope, { CharacterSlap });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/stickers/CharacterSlap.jsx", error: String((e && e.message) || e) }); }

// components/stickers/Sticker.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Sticker — the SandboxOS die-cut sticker system. Usable as UI (callouts,
 * awards, badges) AND as decoration. Many shapes; loud earned color.
 */
function Sticker({
  children,
  shape = 'tag',
  tone = 'hazard',
  rotate = -4,
  halo = true,
  size = 'md',
  style,
  ...props
}) {
  const tones = {
    hazard: {
      bg: 'var(--hazard)',
      fg: 'var(--ink)'
    },
    alert: {
      bg: 'var(--alert)',
      fg: 'var(--signal)'
    },
    rebel: {
      bg: 'var(--magenta)',
      fg: 'var(--signal)'
    },
    go: {
      bg: 'var(--green)',
      fg: 'var(--ink)'
    },
    cyan: {
      bg: 'var(--cyan)',
      fg: 'var(--ink)'
    },
    ink: {
      bg: 'var(--ink)',
      fg: 'var(--signal)'
    },
    paper: {
      bg: 'var(--signal)',
      fg: 'var(--ink)'
    }
  };
  const t = tones[tone] || tones.hazard;
  const fs = size === 'sm' ? 'var(--t-xs)' : size === 'lg' ? 'var(--t-xl)' : 'var(--t-md)';
  const base = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
    fontFamily: 'var(--font-display)',
    fontWeight: 900,
    textTransform: 'uppercase',
    letterSpacing: 'var(--ls-wide)',
    lineHeight: 0.95,
    color: t.fg,
    background: t.bg,
    border: '2px solid var(--ink)',
    boxShadow: halo ? '0 0 0 3px var(--signal), 3px 4px 0 rgba(0,0,0,0.5)' : '3px 4px 0 rgba(0,0,0,0.5)',
    transform: `rotate(${rotate}deg)`
  };
  const shapes = {
    tag: {
      padding: '6px 13px',
      borderRadius: 0,
      fontSize: fs
    },
    pill: {
      padding: '6px 16px',
      borderRadius: '999px',
      fontSize: fs
    },
    seal: {
      width: '78px',
      height: '78px',
      borderRadius: '50%',
      fontSize: 'var(--t-xs)',
      padding: '4px'
    },
    burst: {
      padding: '12px 16px',
      borderRadius: 0,
      fontSize: fs,
      clipPath: 'polygon(50% 0,63% 12%,80% 6%,82% 24%,100% 28%,90% 44%,100% 62%,82% 66%,78% 86%,60% 80%,50% 100%,40% 80%,22% 86%,18% 66%,0 62%,10% 44%,0 28%,18% 24%,20% 6%,37% 12%)'
    },
    ribbon: {
      padding: '6px 22px',
      borderRadius: 0,
      fontSize: fs,
      clipPath: 'polygon(0 0,100% 0,92% 50%,100% 100%,0 100%,8% 50%)'
    },
    price: {
      padding: '6px 13px 6px 20px',
      borderRadius: 0,
      fontSize: fs,
      clipPath: 'polygon(13% 0,100% 0,100% 100%,13% 100%,0 50%)'
    },
    callout: {
      padding: '8px 14px 16px',
      borderRadius: 0,
      fontSize: fs,
      clipPath: 'polygon(0 0,100% 0,100% 72%,34% 72%,22% 100%,18% 72%,0 72%)'
    },
    stamp: {
      width: '82px',
      height: '82px',
      borderRadius: '50%',
      fontSize: 'var(--t-xs)',
      padding: '6px'
    }
  };
  // hazard-striped variant when tone is 'striped'
  const striped = tone === 'striped' ? {
    background: 'repeating-linear-gradient(45deg, var(--hazard) 0 12px, var(--ink) 12px 24px)',
    color: 'var(--ink)'
  } : null;
  // stamp = inked outline (postmark), tone becomes the ink color
  const stamp = shape === 'stamp' ? {
    background: 'transparent',
    color: t.bg,
    border: `2px double ${t.bg}`,
    boxShadow: 'none',
    opacity: 0.92
  } : null;
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      ...base,
      ...(shapes[shape] || shapes.tag),
      ...striped,
      ...stamp,
      ...style
    }
  }, props), shape === 'burst' || striped ? /*#__PURE__*/React.createElement("span", {
    style: {
      background: 'var(--signal)',
      padding: '1px 6px'
    }
  }, children) : children);
}

/** Barcode — procedural; a brand provenance mark. */
function Barcode({
  height = 26,
  seed = '982V7',
  color = 'var(--signal)',
  style,
  ...props
}) {
  const bars = React.useMemo(() => {
    let h = 7;
    const out = [];
    for (let i = 0; i < 26; i++) {
      h = (h * 31 + seed.charCodeAt(i % seed.length)) % 97;
      out.push(1 + h % 4);
    }
    return out;
  }, [seed]);
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: 'inline-flex',
      gap: '2px',
      alignItems: 'stretch',
      height,
      color,
      ...style
    }
  }, props), bars.map((w, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    style: {
      width: w,
      background: i % 2 ? 'currentColor' : 'transparent'
    }
  })));
}
Object.assign(__ds_scope, { Sticker, Barcode });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/stickers/Sticker.jsx", error: String((e && e.message) || e) }); }

// lib/dither.js
try { (() => {
/* ============================================================
   SandboxOS · lib/dither.js  →  window.SandboxDither
   Coalesce ANY image or short text out of halftone particles: a scanline
   reveal assembles it, it holds with a faint shimmer, then dissolves —
   then loops. The brand's "develops out of the fabric" move, reusable.

   Honours prefers-reduced-motion (paints the assembled state, no motion).

   API:
     const inst = SandboxDither.coalesce(canvasEl, {
       src:'../assets/eye.png' | text:'k!',
       cell:5, color:'#F6F2E7', accent:'#FF2E88', loop:true,
       scanline:true, hold:2400
     });
     inst.destroy();
   ============================================================ */
(function () {
  'use strict';

  const RM = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function sampleSource({
    src,
    text,
    cols,
    rows,
    font
  }, cb) {
    const c = document.createElement('canvas');
    c.width = cols;
    c.height = rows;
    const g = c.getContext('2d');
    const finish = () => {
      const d = g.getImageData(0, 0, cols, rows).data;
      const lum = new Float32Array(cols * rows);
      for (let i = 0; i < cols * rows; i++) lum[i] = d[i * 4 + 3] / 255 * ((0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2]) / 255);
      cb(lum);
    };
    if (src) {
      const im = new Image();
      im.crossOrigin = 'anonymous';
      im.onload = () => {
        const s = Math.min(cols / im.width, rows / im.height) * 0.92;
        const w = im.width * s,
          h = im.height * s;
        g.drawImage(im, (cols - w) / 2, (rows - h) / 2, w, h);
        finish();
      };
      im.onerror = finish;
      im.src = src;
    } else {
      g.fillStyle = '#fff';
      g.textAlign = 'center';
      g.textBaseline = 'middle';
      g.font = font || '900 ' + Math.floor(rows * 0.7) + "px Archivo, Arial, sans-serif";
      g.fillText(String(text || ''), cols / 2, rows / 2);
      finish();
    }
  }
  function coalesce(canvas, opts) {
    opts = opts || {};
    const cell = opts.cell || 5;
    const color = opts.color || '#F6F2E7';
    const accent = opts.accent || null;
    const loop = opts.loop !== false;
    const scanline = opts.scanline !== false;
    const hold = opts.hold || 2400;
    const ctx = canvas.getContext('2d');
    let W,
      H,
      cols,
      rows,
      lum = null,
      raf = 0,
      dead = false;
    let phase = 'in',
      t0 = performance.now();
    const rgb = hex => {
      const n = parseInt(hex.replace('#', ''), 16);
      return [n >> 16 & 255, n >> 8 & 255, n & 255];
    };
    const C = rgb(color),
      AC = accent ? rgb(accent) : null;
    function resize() {
      W = canvas.clientWidth || canvas.width;
      H = canvas.clientHeight || canvas.height;
      canvas.width = W;
      canvas.height = H;
      ctx.imageSmoothingEnabled = false;
      cols = Math.max(2, Math.ceil(W / cell));
      rows = Math.max(2, Math.ceil(H / cell));
      sampleSource({
        src: opts.src,
        text: opts.text,
        cols,
        rows,
        font: opts.font
      }, l => {
        lum = l;
      });
    }
    function frame(now) {
      if (dead) return;
      raf = requestAnimationFrame(frame);
      if (!lum) return;
      const off = document.createElement('canvas');
      off.width = cols;
      off.height = rows;
      const octx = off.getContext('2d');
      const img = octx.createImageData(cols, rows);
      const d = img.data;
      let prog;
      const dt = now - t0;
      if (RM) prog = 1;else if (phase === 'in') {
        prog = Math.min(1, dt / 700);
        if (prog >= 1) {
          phase = 'hold';
          t0 = now;
        }
      } else if (phase === 'hold') {
        prog = 1;
        if (dt > hold) {
          if (loop) {
            phase = 'out';
            t0 = now;
          }
        }
      } else {
        prog = Math.max(0, 1 - dt / 600);
        if (prog <= 0) {
          phase = 'in';
          t0 = now;
        }
      }
      const reveal = phase === 'in' ? prog : 1; // scanline sweep top→bottom on entrance
      const shimmer = phase === 'hold' && !RM ? 0.85 + 0.15 * Math.sin(now / 220) : 1;
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const i = y * cols + x;
          let v = lum[i] * shimmer;
          if (scanline && phase === 'in' && y / rows > reveal) v = 0; // not yet revealed
          if (phase === 'out') v *= prog;
          const thr = ((x * 7 + y * 13) % 16 + 0.5) / 16; // ordered-ish
          if (v > thr) {
            const col = AC && lum[i] > 0.62 && (x + y & 3) === 0 ? AC : C;
            d[i * 4] = col[0];
            d[i * 4 + 1] = col[1];
            d[i * 4 + 2] = col[2];
            d[i * 4 + 3] = 255;
          }
        }
      }
      octx.putImageData(img, 0, 0);
      ctx.clearRect(0, 0, W, H);
      ctx.drawImage(off, 0, 0, W, H);
      // acid scanline line on entrance
      if (scanline && phase === 'in' && !RM) {
        ctx.fillStyle = accent || color;
        ctx.globalAlpha = 0.5;
        ctx.fillRect(0, reveal * H - 2, W, 2);
        ctx.globalAlpha = 1;
      }
    }
    const onR = () => resize();
    resize();
    window.addEventListener('resize', onR);
    raf = requestAnimationFrame(frame);
    return {
      destroy: () => {
        dead = true;
        cancelAnimationFrame(raf);
        window.removeEventListener('resize', onR);
      }
    };
  }
  window.SandboxDither = {
    coalesce
  };
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "lib/dither.js", error: String((e && e.message) || e) }); }

// lib/fx.js
try { (() => {
/* ============================================================
   SandboxOS · lib/fx.js  →  window.SandboxFX
   The experiential / motion-graphics layer. Pointer + touch + gyro aware.
   Every effect is opt-in, cheap, and honours prefers-reduced-motion
   (reduced → instant end-state, no animation).

   FX.scramble(el, text, {dur})      decode text out of glyph noise
   FX.glitch(el, {dur})              RGB-split + slice glitch burst
   FX.reveal(selectorOrEls)          dither-rise on scroll (IntersectionObserver)
   FX.magnetic(el, {strength})       element leans toward pointer (desktop)
   FX.tilt(el, {max})                3D tilt to pointer; gyro on mobile
   FX.peel(el)                       sticker corner-peel on hover/press
   FX.ripple(el)                     press ripple (pointer/touch) on slaps
   FX.marquee(el)                    duplicate children for seamless scroll
   FX.autoAll(root)                  wire everything via [data-fx] attributes
   ============================================================ */
(function () {
  'use strict';

  const RM = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const TOUCH = matchMedia('(hover: none)').matches || 'ontouchstart' in window;
  const GLYPHS = '▚▞▙▟◤◥◣◢01░▒▓█▤▥▦∷⌁¦/\\<>=+*'.split('');
  const rnd = a => a[Math.random() * a.length | 0];
  function scramble(el, text, opts) {
    opts = opts || {};
    text = text == null ? el.textContent : String(text);
    if (RM) {
      el.textContent = text;
      return Promise.resolve();
    }
    const dur = opts.dur || 800,
      t0 = performance.now(),
      n = text.length;
    return new Promise(res => {
      function tick(now) {
        const p = Math.min(1, (now - t0) / dur);
        let out = '';
        for (let i = 0; i < n; i++) {
          if (text[i] === ' ') {
            out += ' ';
            continue;
          }
          out += p * n > i ? text[i] : rnd(GLYPHS);
        }
        el.textContent = out;
        if (p < 1) requestAnimationFrame(tick);else {
          el.textContent = text;
          res();
        }
      }
      requestAnimationFrame(tick);
    });
  }
  function glitch(el, opts) {
    if (RM) return;
    opts = opts || {};
    const dur = opts.dur || 420;
    el.style.willChange = 'transform, filter';
    const t0 = performance.now(),
      base = el.style.textShadow || '';
    function tick(now) {
      const p = (now - t0) / dur;
      if (p >= 1) {
        el.style.transform = '';
        el.style.textShadow = base;
        el.style.clipPath = '';
        el.style.willChange = '';
        return;
      }
      const j = (1 - p) * 5;
      el.style.transform = `translate(${(Math.random() - 0.5) * j}px,${(Math.random() - 0.5) * j}px)`;
      el.style.textShadow = `${(Math.random() - 0.5) * j}px 0 var(--magenta), ${(Math.random() - 0.5) * -j}px 0 var(--cyan)`;
      if (Math.random() < 0.5) {
        const y = Math.random() * 100;
        el.style.clipPath = `polygon(0 ${y}%,100% ${y}%,100% ${y + 6}%,0 ${y + 6}%)`;
        setTimeout(() => el.style.clipPath = '', 40);
      }
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }
  function reveal(sel) {
    const els = typeof sel === 'string' ? [].slice.call(document.querySelectorAll(sel)) : sel.length ? [].slice.call(sel) : [sel];
    if (RM) {
      els.forEach(e => {
        e.style.opacity = 1;
        e.style.transform = 'none';
        e.style.filter = 'none';
      });
      return;
    }
    els.forEach(e => {
      e.style.opacity = '0';
      e.style.transform = 'translateY(14px)';
      e.style.filter = 'blur(0) contrast(3) brightness(0.4)';
      e.style.transition = 'opacity .5s, transform .55s var(--ease-out, cubic-bezier(.2,.8,.2,1)), filter .6s';
    });
    const io = new IntersectionObserver(ents => {
      ents.forEach(en => {
        if (en.isIntersecting) {
          const e = en.target;
          e.style.opacity = '1';
          e.style.transform = 'none';
          e.style.filter = 'none';
          io.unobserve(e);
        }
      });
    }, {
      threshold: 0.18
    });
    els.forEach(e => io.observe(e));
  }
  function magnetic(el, opts) {
    if (RM || TOUCH) return;
    const s = opts && opts.strength || 0.3;
    el.style.transition = 'transform .18s var(--ease-out, cubic-bezier(.2,.8,.2,1))';
    el.addEventListener('pointermove', e => {
      const r = el.getBoundingClientRect();
      el.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * s}px,${(e.clientY - r.top - r.height / 2) * s}px)`;
    });
    el.addEventListener('pointerleave', () => {
      el.style.transform = '';
    });
  }
  function tilt(el, opts) {
    if (RM) return;
    const max = opts && opts.max || 12;
    el.style.transformStyle = 'preserve-3d';
    el.style.transition = 'transform .15s ease-out';
    const set = (px, py) => {
      el.style.transform = `perspective(700px) rotateY(${px * max}deg) rotateX(${-py * max}deg)`;
    };
    if (TOUCH && window.DeviceOrientationEvent) {
      window.addEventListener('deviceorientation', e => {
        set(Math.max(-1, Math.min(1, (e.gamma || 0) / 30)), Math.max(-1, Math.min(1, ((e.beta || 0) - 45) / 30)));
      });
    } else {
      el.addEventListener('pointermove', e => {
        const r = el.getBoundingClientRect();
        set((e.clientX - r.left) / r.width - 0.5, (e.clientY - r.top) / r.height - 0.5);
      });
      el.addEventListener('pointerleave', () => {
        el.style.transform = '';
      });
    }
  }
  function peel(el) {
    el.style.transition = 'transform .2s var(--ease-snap, cubic-bezier(.6,0,.2,1)), box-shadow .2s';
    el.style.transformOrigin = 'top right';
    const on = () => {
      if (RM) return;
      el.style.transform = 'rotate(2deg) translateY(-2px)';
      el.style.boxShadow = '0 0 0 3px var(--signal), 6px 8px 0 rgba(0,0,0,.55)';
    };
    const off = () => {
      el.style.transform = '';
      el.style.boxShadow = '';
    };
    el.addEventListener('pointerenter', on);
    el.addEventListener('pointerleave', off);
    el.addEventListener('pointerdown', on);
    el.addEventListener('pointerup', off);
  }
  function ripple(el) {
    el.style.position = el.style.position || 'relative';
    el.style.overflow = 'hidden';
    const fire = e => {
      if (RM) return;
      const r = el.getBoundingClientRect();
      const d = document.createElement('span');
      const size = Math.max(r.width, r.height);
      const x = (e.touches ? e.touches[0].clientX : e.clientX) - r.left,
        y = (e.touches ? e.touches[0].clientY : e.clientY) - r.top;
      d.style.cssText = `position:absolute;left:${x - size / 2}px;top:${y - size / 2}px;width:${size}px;height:${size}px;border-radius:50%;background:var(--accent-live,var(--signal));opacity:.35;transform:scale(0);pointer-events:none;transition:transform .45s ease-out,opacity .6s;`;
      el.appendChild(d);
      requestAnimationFrame(() => {
        d.style.transform = 'scale(1)';
        d.style.opacity = '0';
      });
      setTimeout(() => d.remove(), 650);
    };
    el.addEventListener('pointerdown', fire);
  }
  function marquee(el) {
    if (el.dataset.fxMarquee) return;
    el.dataset.fxMarquee = '1';
    el.innerHTML += el.innerHTML;
  }
  function autoAll(root) {
    root = root || document;
    root.querySelectorAll('[data-fx~="reveal"]').forEach(e => reveal(e));
    root.querySelectorAll('[data-fx~="magnetic"]').forEach(e => magnetic(e));
    root.querySelectorAll('[data-fx~="tilt"]').forEach(e => tilt(e));
    root.querySelectorAll('[data-fx~="peel"]').forEach(e => peel(e));
    root.querySelectorAll('[data-fx~="ripple"]').forEach(e => ripple(e));
    root.querySelectorAll('[data-fx~="marquee"]').forEach(e => marquee(e));
    root.querySelectorAll('[data-fx~="glitch-hover"]').forEach(e => e.addEventListener('pointerenter', () => glitch(e)));
    root.querySelectorAll('[data-fx-scramble]').forEach(e => scramble(e, e.getAttribute('data-fx-scramble') || e.textContent));
  }
  window.SandboxFX = {
    scramble,
    glitch,
    reveal,
    magnetic,
    tilt,
    peel,
    ripple,
    marquee,
    autoAll,
    RM,
    TOUCH
  };
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "lib/fx.js", error: String((e && e.message) || e) }); }

// lib/sound.js
try { (() => {
/* ============================================================
   SandboxOS · lib/sound.js  →  window.SandboxSound
   A tiny WebAudio synth for the living machine. OFF by default; only makes
   sound after enable(true) (call from a user gesture). No assets — every
   sound is synthesized. The 60Hz hum is the machine "breathing".

   API:
     const snd = SandboxSound.create();
     snd.enable(true);   // or snd.toggle()
     snd.click(); snd.key(); snd.boot(); snd.install(); snd.error(); snd.slap();
   ============================================================ */
(function () {
  'use strict';

  function create() {
    let ac = null,
      hum = null,
      on = false;
    const ctx = () => ac || (ac = new (window.AudioContext || window.webkitAudioContext)());
    function env(o, g, t0, dur, peak) {
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.exponentialRampToValueAtTime(peak, t0 + 0.008);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      o.start(t0);
      o.stop(t0 + dur + 0.02);
    }
    function beep(freq, dur, type, peak, when) {
      if (!on) return;
      const c = ctx();
      const t0 = when || c.currentTime;
      const o = c.createOscillator(),
        g = c.createGain();
      o.type = type || 'square';
      o.frequency.value = freq;
      o.connect(g);
      g.connect(c.destination);
      env(o, g, t0, dur, peak || 0.07);
    }
    function startHum() {
      if (!on || hum) return;
      const c = ctx();
      hum = c.createOscillator();
      const hg = c.createGain();
      hum.type = 'sawtooth';
      hum.frequency.value = 58;
      const lp = c.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.value = 130;
      hg.gain.value = 0.012;
      hum.connect(lp);
      lp.connect(hg);
      hg.connect(c.destination);
      hum.start();
    }
    function stopHum() {
      if (hum) {
        try {
          hum.stop();
        } catch (e) {}
        hum = null;
      }
    }
    return {
      get enabled() {
        return on;
      },
      enable(v) {
        on = !!v;
        if (on) {
          ctx().resume && ctx().resume();
          startHum();
        } else stopHum();
      },
      toggle() {
        this.enable(!on);
        return on;
      },
      click() {
        beep(820 + Math.random() * 120, 0.05, 'square', 0.05);
      },
      key() {
        beep(1180, 0.03, 'square', 0.03);
      },
      boot() {
        if (!on) return;
        const c = ctx(),
          b = c.currentTime;
        [294, 392, 523, 698].forEach((f, i) => beep(f, 0.18, 'square', 0.06, b + i * 0.11));
        beep(880, 0.4, 'sine', 0.04, b + 0.46);
      },
      install() {
        if (!on) return;
        const c = ctx(),
          t0 = c.currentTime;
        const o = c.createOscillator(),
          g = c.createGain();
        o.type = 'square';
        o.frequency.setValueAtTime(330, t0);
        o.frequency.exponentialRampToValueAtTime(990, t0 + 0.16);
        o.connect(g);
        g.connect(c.destination);
        env(o, g, t0, 0.2, 0.06);
      },
      slap() {
        beep(180, 0.06, 'square', 0.07);
      },
      error() {
        beep(130, 0.24, 'square', 0.08);
      },
      destroy() {
        stopHum();
        if (ac) ac.close();
      }
    };
  }
  window.SandboxSound = {
    create
  };
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "lib/sound.js", error: String((e && e.message) || e) }); }

// lib/substrate.js
try { (() => {
/* ============================================================
   SandboxOS · lib/substrate.js  →  window.SandboxSubstrate
   The living 1-bit dither field the whole OS sits on. Ordered (Bayer 8×8)
   dither rendered low-res into an offscreen ImageData and upscaled pixelated
   (cheap, ~60fps). Moods reshape palette + motion; switching mood plays a
   Bayer-ordered DISSOLVE wipe. Cursor poke ripples the weave.

   Adapted to the SandboxOS palette (void / bone / magenta-"her" / amber / violet).
   Honours prefers-reduced-motion (paints a calm static field, no animation).

   API:
     const sub = SandboxSubstrate.mount(canvasEl, { cell:4 });
     sub.setMood('jailbroken'|'workbench'|'afterhours');   // animated dissolve
     sub.set({ chaos, scan, vhs });                         // 0..1 live knobs
     sub.poke(clientX, clientY);                            // cursor ripple
     sub.surface('BUILD');                                  // word blooms out of the weave
     sub.destroy();
   ============================================================ */
(function () {
  'use strict';

  const BAYER = [[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26], [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22], [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25], [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]].map(r => r.map(v => (v + 0.5) / 64));
  const RM = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // SandboxOS moods — three states of one machine
  const MOODS = {
    // everyday bootleg: dim warm grain, rare amber spark
    jailbroken: {
      bg: [12, 12, 10],
      ink: [66, 63, 53],
      accent: [176, 122, 0],
      accentAmt: 0.035,
      amp: 0.10,
      speed: 0.20,
      bloom: 0.05,
      bloomCol: [176, 122, 0],
      turb: 0.06
    },
    // focused maker mode: quietest, faint cool grain
    workbench: {
      bg: [12, 12, 10],
      ink: [56, 60, 52],
      accent: [40, 150, 80],
      accentAmt: 0.025,
      amp: 0.06,
      speed: 0.12,
      bloom: 0.04,
      bloomCol: [40, 150, 80],
      turb: 0.02
    },
    // after dark: a touch of dim magenta in the grain — subtle, not mystical
    afterhours: {
      bg: [12, 9, 15],
      ink: [70, 60, 68],
      accent: [150, 60, 108],
      accentAmt: 0.06,
      amp: 0.09,
      speed: 0.11,
      bloom: 0.08,
      bloomCol: [110, 60, 120],
      turb: 0.04
    }
  };
  function mount(canvas, opts) {
    opts = opts || {};
    const cell = opts.cell || 4;
    const ctx = canvas.getContext('2d');
    const off = document.createElement('canvas');
    const octx = off.getContext('2d');
    let cols = 0,
      rows = 0,
      img = null,
      W = 0,
      H = 0,
      raf = 0,
      dead = false;
    let t = 0,
      last = performance.now();
    let cur = opts.mood || 'jailbroken',
      from = cur,
      prog = 1;
    let knobs = {
      chaos: 0.5,
      scan: 0.5,
      vhs: 0.35
    };
    let poke = {
      x: -1,
      y: -1,
      age: 1
    };
    let word = null; // {grid:Float32Array, cols, rows, born}

    function resize() {
      W = canvas.clientWidth || canvas.width || window.innerWidth;
      H = canvas.clientHeight || canvas.height || window.innerHeight;
      canvas.width = W;
      canvas.height = H;
      cols = Math.max(2, Math.ceil(W / cell));
      rows = Math.max(2, Math.ceil(H / cell));
      off.width = cols;
      off.height = rows;
      img = octx.createImageData(cols, rows);
      ctx.imageSmoothingEnabled = false;
      if (word) word = bakeWord(word.text);
    }
    function bakeWord(text) {
      const c = document.createElement('canvas');
      c.width = cols;
      c.height = rows;
      const g = c.getContext('2d');
      g.fillStyle = '#fff';
      g.textAlign = 'center';
      g.textBaseline = 'middle';
      g.font = '900 ' + Math.floor(rows * 0.42) + "px Archivo, Arial, sans-serif";
      g.fillText(text, cols / 2, rows / 2);
      const d = g.getImageData(0, 0, cols, rows).data;
      const grid = new Float32Array(cols * rows);
      for (let i = 0; i < cols * rows; i++) grid[i] = d[i * 4 + 3] / 255;
      return {
        text,
        grid,
        born: performance.now()
      };
    }
    function field(M, nx, ny, time, bx, by) {
      let v = 0.40 + M.amp * Math.sin(nx * 6.0 + time * M.speed) + M.amp * Math.sin(ny * 5.0 - time * M.speed * 0.8) + M.amp * 0.7 * Math.sin((nx + ny) * 4.0 + time * M.speed * 1.3);
      if (M.turb) v += M.turb * 0.18 * Math.sin(nx * 23 + time * 2) * Math.sin(ny * 19 - time * 1.7);
      const dx = nx - bx,
        dy = ny - by;
      v += M.bloom * Math.max(0, 1 - Math.sqrt(dx * dx + dy * dy) * 1.6);
      return v;
    }
    function frame(now) {
      if (dead) return;
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (!RM) t += dt;
      if (prog < 1) prog = Math.min(1, prog + dt / 0.9);
      const A = MOODS[from],
        Bm = MOODS[cur];
      const chaos = knobs.chaos,
        vhs = knobs.vhs;
      const bxA = 0.5 + 0.32 * Math.sin(t * 0.13),
        byA = 0.32 + 0.2 * Math.cos(t * 0.11);
      const bxB = 0.5 + 0.32 * Math.sin(t * 0.13 + 1),
        byB = 0.6 + 0.2 * Math.cos(t * 0.11 + 1);
      const tearRow = vhs > 0.05 ? Math.floor((Math.sin(t * 0.7) * 0.5 + 0.5) * rows) : -99;
      const tearAmt = vhs > 0.05 && Math.random() < 0.04 ? Math.floor(vhs * 6) : 0;
      let wf = 0,
        wg = null;
      if (word) {
        wf = Math.max(0, 1 - (now - word.born) / 2600);
        if (wf <= 0) word = null;else wg = word.grid;
      }
      const data = img.data;
      for (let cy = 0; cy < rows; cy++) {
        for (let cx = 0; cx < cols; cx++) {
          const useB = prog >= 1 ? true : prog > BAYER[cy & 7][cx & 7];
          const M = useB ? Bm : A;
          const nx = cx / cols,
            ny = cy / rows;
          const bx = useB ? bxB : bxA,
            by = useB ? byB : byA;
          let v = field(M, nx, ny, t, bx, by);
          if (chaos > 0.01) v += chaos * 0.12 * Math.sin(nx * 40 + t * 3) * Math.sin(ny * 36 - t * 2.3);
          if (poke.age < 1) {
            const pd = Math.hypot(nx - poke.x, ny - poke.y);
            v += (1 - poke.age) * 0.3 * Math.max(0, 1 - pd * 6) * Math.cos(pd * 40 - t * 8);
          }
          if (wg) v += wf * 0.95 * wg[cy * cols + cx];
          const thr = BAYER[cy & 7][cx + (tearAmt && cy > tearRow && cy < tearRow + 4 ? tearAmt : 0) & 7];
          const on = v > thr;
          const i = (cy * cols + cx) * 4;
          let col;
          if (on) {
            const acc = M.accentAmt;
            col = acc > 0 && Math.random() < acc * Math.max(0, v - 0.6) ? M.accent : M.ink;
          } else col = M.bg;
          data[i] = col[0];
          data[i + 1] = col[1];
          data[i + 2] = col[2];
          data[i + 3] = 255;
        }
      }
      octx.putImageData(img, 0, 0);
      ctx.drawImage(off, 0, 0, W, H);
      if (poke.age < 1) poke.age = Math.min(1, poke.age + dt / 0.6);
      raf = requestAnimationFrame(frame);
    }
    const onResize = () => resize();
    resize();
    window.addEventListener('resize', onResize);
    raf = requestAnimationFrame(frame);
    if (RM) {
      // single calm paint already done via first frame; stop the loop
      cancelAnimationFrame(raf);
      requestAnimationFrame(frame); // one frame
    }
    return {
      setMood: m => {
        if (MOODS[m] && m !== cur) {
          from = cur;
          cur = m;
          prog = 0;
        }
      },
      mood: () => cur,
      set: k => Object.assign(knobs, k),
      poke: (px, py) => {
        const r = canvas.getBoundingClientRect();
        poke = {
          x: (px - r.left) / W,
          y: (py - r.top) / H,
          age: 0
        };
      },
      surface: text => {
        word = bakeWord(String(text));
      },
      destroy: () => {
        dead = true;
        cancelAnimationFrame(raf);
        window.removeEventListener('resize', onResize);
      },
      MOODS
    };
  }
  window.SandboxSubstrate = {
    mount,
    MOODS
  };
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "lib/substrate.js", error: String((e && e.message) || e) }); }

// ui_kits/mobile/ios-frame.jsx
try { (() => {
// @ds-adherence-ignore -- omelette starter scaffold (raw elements/hex/px by design)

/* BEGIN USAGE */
// iOS.jsx — Simplified iOS 26 (Liquid Glass) device frame
// Based on the iOS 26 UI Kit + Figma status bar spec. No assets, no deps.
// Exports (to window): IOSDevice, IOSStatusBar, IOSNavBar, IOSGlassPill, IOSList, IOSListRow, IOSKeyboard
//
// Usage — wrap your screen content in <IOSDevice> to get the bezel, status bar
// and home indicator (props: title, dark, keyboard):
//
//   <IOSDevice title="Settings">
//     ...your screen content...
//   </IOSDevice>
//   <IOSDevice dark title="Search" keyboard>…</IOSDevice>
/* END USAGE */

// ─────────────────────────────────────────────────────────────
// Status bar
// ─────────────────────────────────────────────────────────────
function IOSStatusBar({
  dark = false,
  time = '9:41'
}) {
  const c = dark ? '#fff' : '#000';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 154,
      alignItems: 'center',
      justifyContent: 'center',
      padding: '21px 24px 19px',
      boxSizing: 'border-box',
      position: 'relative',
      zIndex: 20,
      width: '100%'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      height: 22,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      paddingTop: 1.5
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: '-apple-system, "SF Pro", system-ui',
      fontWeight: 590,
      fontSize: 17,
      lineHeight: '22px',
      color: c
    }
  }, time)), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      height: 22,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 7,
      paddingTop: 1,
      paddingRight: 1
    }
  }, /*#__PURE__*/React.createElement("svg", {
    width: "19",
    height: "12",
    viewBox: "0 0 19 12"
  }, /*#__PURE__*/React.createElement("rect", {
    x: "0",
    y: "7.5",
    width: "3.2",
    height: "4.5",
    rx: "0.7",
    fill: c
  }), /*#__PURE__*/React.createElement("rect", {
    x: "4.8",
    y: "5",
    width: "3.2",
    height: "7",
    rx: "0.7",
    fill: c
  }), /*#__PURE__*/React.createElement("rect", {
    x: "9.6",
    y: "2.5",
    width: "3.2",
    height: "9.5",
    rx: "0.7",
    fill: c
  }), /*#__PURE__*/React.createElement("rect", {
    x: "14.4",
    y: "0",
    width: "3.2",
    height: "12",
    rx: "0.7",
    fill: c
  })), /*#__PURE__*/React.createElement("svg", {
    width: "17",
    height: "12",
    viewBox: "0 0 17 12"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M8.5 3.2C10.8 3.2 12.9 4.1 14.4 5.6L15.5 4.5C13.7 2.7 11.2 1.5 8.5 1.5C5.8 1.5 3.3 2.7 1.5 4.5L2.6 5.6C4.1 4.1 6.2 3.2 8.5 3.2Z",
    fill: c
  }), /*#__PURE__*/React.createElement("path", {
    d: "M8.5 6.8C9.9 6.8 11.1 7.3 12 8.2L13.1 7.1C11.8 5.9 10.2 5.1 8.5 5.1C6.8 5.1 5.2 5.9 3.9 7.1L5 8.2C5.9 7.3 7.1 6.8 8.5 6.8Z",
    fill: c
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "8.5",
    cy: "10.5",
    r: "1.5",
    fill: c
  })), /*#__PURE__*/React.createElement("svg", {
    width: "27",
    height: "13",
    viewBox: "0 0 27 13"
  }, /*#__PURE__*/React.createElement("rect", {
    x: "0.5",
    y: "0.5",
    width: "23",
    height: "12",
    rx: "3.5",
    stroke: c,
    strokeOpacity: "0.35",
    fill: "none"
  }), /*#__PURE__*/React.createElement("rect", {
    x: "2",
    y: "2",
    width: "20",
    height: "9",
    rx: "2",
    fill: c
  }), /*#__PURE__*/React.createElement("path", {
    d: "M25 4.5V8.5C25.8 8.2 26.5 7.2 26.5 6.5C26.5 5.8 25.8 4.8 25 4.5Z",
    fill: c,
    fillOpacity: "0.4"
  }))));
}

// ─────────────────────────────────────────────────────────────
// Liquid glass pill — blur + tint + shine
// ─────────────────────────────────────────────────────────────
function IOSGlassPill({
  children,
  dark = false,
  style = {}
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      height: 44,
      minWidth: 44,
      borderRadius: 9999,
      position: 'relative',
      overflow: 'hidden',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: dark ? '0 2px 6px rgba(0,0,0,0.35), 0 6px 16px rgba(0,0,0,0.2)' : '0 1px 3px rgba(0,0,0,0.07), 0 3px 10px rgba(0,0,0,0.06)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: 9999,
      backdropFilter: 'blur(12px) saturate(180%)',
      WebkitBackdropFilter: 'blur(12px) saturate(180%)',
      background: dark ? 'rgba(120,120,128,0.28)' : 'rgba(255,255,255,0.5)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: 9999,
      boxShadow: dark ? 'inset 1.5px 1.5px 1px rgba(255,255,255,0.15), inset -1px -1px 1px rgba(255,255,255,0.08)' : 'inset 1.5px 1.5px 1px rgba(255,255,255,0.7), inset -1px -1px 1px rgba(255,255,255,0.4)',
      border: dark ? '0.5px solid rgba(255,255,255,0.15)' : '0.5px solid rgba(0,0,0,0.06)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      zIndex: 1,
      display: 'flex',
      alignItems: 'center',
      padding: '0 4px'
    }
  }, children));
}

// ─────────────────────────────────────────────────────────────
// Navigation bar — glass pills + large title
// ─────────────────────────────────────────────────────────────
function IOSNavBar({
  title = 'Title',
  dark = false,
  trailingIcon = true
}) {
  const muted = dark ? 'rgba(255,255,255,0.6)' : '#404040';
  const text = dark ? '#fff' : '#000';
  const pillIcon = content => /*#__PURE__*/React.createElement(IOSGlassPill, {
    dark: dark
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 36,
      height: 36,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, content));
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      paddingTop: 62,
      paddingBottom: 10,
      position: 'relative',
      zIndex: 5
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 16px'
    }
  }, pillIcon(/*#__PURE__*/React.createElement("svg", {
    width: "12",
    height: "20",
    viewBox: "0 0 12 20",
    fill: "none",
    style: {
      marginLeft: -1
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "M10 2L2 10l8 8",
    stroke: muted,
    strokeWidth: "2.5",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }))), trailingIcon && pillIcon(/*#__PURE__*/React.createElement("svg", {
    width: "22",
    height: "6",
    viewBox: "0 0 22 6"
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "3",
    cy: "3",
    r: "2.5",
    fill: muted
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "11",
    cy: "3",
    r: "2.5",
    fill: muted
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "19",
    cy: "3",
    r: "2.5",
    fill: muted
  })))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '0 16px',
      fontFamily: '-apple-system, system-ui',
      fontSize: 34,
      fontWeight: 700,
      lineHeight: '41px',
      color: text,
      letterSpacing: 0.4
    }
  }, title));
}

// ─────────────────────────────────────────────────────────────
// Grouped list (inset card, r:26) + row (52px)
// ─────────────────────────────────────────────────────────────
function IOSListRow({
  title,
  detail,
  icon,
  chevron = true,
  isLast = false,
  dark = false
}) {
  const text = dark ? '#fff' : '#000';
  const sec = dark ? 'rgba(235,235,245,0.6)' : 'rgba(60,60,67,0.6)';
  const ter = dark ? 'rgba(235,235,245,0.3)' : 'rgba(60,60,67,0.3)';
  const sep = dark ? 'rgba(84,84,88,0.65)' : 'rgba(60,60,67,0.12)';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      minHeight: 52,
      padding: '0 16px',
      position: 'relative',
      fontFamily: '-apple-system, system-ui',
      fontSize: 17,
      letterSpacing: -0.43
    }
  }, icon && /*#__PURE__*/React.createElement("div", {
    style: {
      width: 30,
      height: 30,
      borderRadius: 7,
      background: icon,
      marginRight: 12,
      flexShrink: 0
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      color: text
    }
  }, title), detail && /*#__PURE__*/React.createElement("span", {
    style: {
      color: sec,
      marginRight: 6
    }
  }, detail), chevron && /*#__PURE__*/React.createElement("svg", {
    width: "8",
    height: "14",
    viewBox: "0 0 8 14",
    style: {
      flexShrink: 0
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "M1 1l6 6-6 6",
    stroke: ter,
    strokeWidth: "2",
    fill: "none",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  })), !isLast && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      bottom: 0,
      right: 0,
      left: icon ? 58 : 16,
      height: 0.5,
      background: sep
    }
  }));
}
function IOSList({
  header,
  children,
  dark = false
}) {
  const hc = dark ? 'rgba(235,235,245,0.6)' : 'rgba(60,60,67,0.6)';
  const bg = dark ? '#1C1C1E' : '#fff';
  return /*#__PURE__*/React.createElement("div", null, header && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: '-apple-system, system-ui',
      fontSize: 13,
      color: hc,
      textTransform: 'uppercase',
      padding: '8px 36px 6px',
      letterSpacing: -0.08
    }
  }, header), /*#__PURE__*/React.createElement("div", {
    style: {
      background: bg,
      borderRadius: 26,
      margin: '0 16px',
      overflow: 'hidden'
    }
  }, children));
}

// ─────────────────────────────────────────────────────────────
// Device frame
// ─────────────────────────────────────────────────────────────
function IOSDevice({
  children,
  width = 402,
  height = 874,
  dark = false,
  title,
  keyboard = false
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      width,
      height,
      borderRadius: 48,
      overflow: 'hidden',
      position: 'relative',
      background: dark ? '#000' : '#F2F2F7',
      boxShadow: '0 40px 80px rgba(0,0,0,0.18), 0 0 0 1px rgba(0,0,0,0.12)',
      fontFamily: '-apple-system, system-ui, sans-serif',
      WebkitFontSmoothing: 'antialiased'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 11,
      left: '50%',
      transform: 'translateX(-50%)',
      width: 126,
      height: 37,
      borderRadius: 24,
      background: '#000',
      zIndex: 50
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      zIndex: 10
    }
  }, /*#__PURE__*/React.createElement(IOSStatusBar, {
    dark: dark
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      height: '100%',
      display: 'flex',
      flexDirection: 'column'
    }
  }, title !== undefined && /*#__PURE__*/React.createElement(IOSNavBar, {
    title: title,
    dark: dark
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      overflow: 'auto'
    }
  }, children), keyboard && /*#__PURE__*/React.createElement(IOSKeyboard, {
    dark: dark
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      bottom: 0,
      left: 0,
      right: 0,
      zIndex: 60,
      height: 34,
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'flex-end',
      paddingBottom: 8,
      pointerEvents: 'none'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 139,
      height: 5,
      borderRadius: 100,
      background: dark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.25)'
    }
  })));
}

// ─────────────────────────────────────────────────────────────
// Keyboard — iOS 26 liquid glass
// ─────────────────────────────────────────────────────────────
function IOSKeyboard({
  dark = false
}) {
  const glyph = dark ? 'rgba(255,255,255,0.7)' : '#595959';
  const sugg = dark ? 'rgba(255,255,255,0.6)' : '#333';
  const keyBg = dark ? 'rgba(255,255,255,0.22)' : 'rgba(255,255,255,0.85)';

  // special-key icons
  const icons = {
    shift: /*#__PURE__*/React.createElement("svg", {
      width: "19",
      height: "17",
      viewBox: "0 0 19 17"
    }, /*#__PURE__*/React.createElement("path", {
      d: "M9.5 1L1 9.5h4.5V16h8V9.5H18L9.5 1z",
      fill: glyph
    })),
    del: /*#__PURE__*/React.createElement("svg", {
      width: "23",
      height: "17",
      viewBox: "0 0 23 17"
    }, /*#__PURE__*/React.createElement("path", {
      d: "M7 1h13a2 2 0 012 2v11a2 2 0 01-2 2H7l-6-7.5L7 1z",
      fill: "none",
      stroke: glyph,
      strokeWidth: "1.6",
      strokeLinejoin: "round"
    }), /*#__PURE__*/React.createElement("path", {
      d: "M10 5l7 7M17 5l-7 7",
      stroke: glyph,
      strokeWidth: "1.6",
      strokeLinecap: "round"
    })),
    ret: /*#__PURE__*/React.createElement("svg", {
      width: "20",
      height: "14",
      viewBox: "0 0 20 14"
    }, /*#__PURE__*/React.createElement("path", {
      d: "M18 1v6H4m0 0l4-4M4 7l4 4",
      fill: "none",
      stroke: "#fff",
      strokeWidth: "1.8",
      strokeLinecap: "round",
      strokeLinejoin: "round"
    }))
  };
  const key = (content, {
    w,
    flex,
    ret,
    fs = 25,
    k
  } = {}) => /*#__PURE__*/React.createElement("div", {
    key: k,
    style: {
      height: 42,
      borderRadius: 8.5,
      flex: flex ? 1 : undefined,
      width: w,
      minWidth: 0,
      background: ret ? '#08f' : keyBg,
      boxShadow: '0 1px 0 rgba(0,0,0,0.075)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: '-apple-system, "SF Compact", system-ui',
      fontSize: fs,
      fontWeight: 458,
      color: ret ? '#fff' : glyph
    }
  }, content);
  const row = (keys, pad = 0) => /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 6.5,
      justifyContent: 'center',
      padding: `0 ${pad}px`
    }
  }, keys.map(l => key(l, {
    flex: true,
    k: l
  })));
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      zIndex: 15,
      borderRadius: 27,
      overflow: 'hidden',
      padding: '11px 0 2px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      boxShadow: dark ? '0 -2px 20px rgba(0,0,0,0.09)' : '0 -1px 6px rgba(0,0,0,0.018), 0 -3px 20px rgba(0,0,0,0.012)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: 27,
      backdropFilter: 'blur(12px) saturate(180%)',
      WebkitBackdropFilter: 'blur(12px) saturate(180%)',
      background: dark ? 'rgba(120,120,128,0.14)' : 'rgba(255,255,255,0.25)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: 27,
      boxShadow: dark ? 'inset 1.5px 1.5px 1px rgba(255,255,255,0.15)' : 'inset 1.5px 1.5px 1px rgba(255,255,255,0.7), inset -1px -1px 1px rgba(255,255,255,0.4)',
      border: dark ? '0.5px solid rgba(255,255,255,0.15)' : '0.5px solid rgba(0,0,0,0.06)',
      pointerEvents: 'none'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 20,
      alignItems: 'center',
      padding: '8px 22px 13px',
      width: '100%',
      boxSizing: 'border-box',
      position: 'relative'
    }
  }, ['"The"', 'the', 'to'].map((w, i) => /*#__PURE__*/React.createElement(React.Fragment, {
    key: i
  }, i > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      width: 1,
      height: 25,
      background: '#ccc',
      opacity: 0.3
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      textAlign: 'center',
      fontFamily: '-apple-system, system-ui',
      fontSize: 17,
      color: sugg,
      letterSpacing: -0.43,
      lineHeight: '22px'
    }
  }, w)))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 13,
      padding: '0 6.5px',
      width: '100%',
      boxSizing: 'border-box',
      position: 'relative'
    }
  }, row(['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p']), row(['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'], 20), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 14.25,
      alignItems: 'center'
    }
  }, key(icons.shift, {
    w: 45,
    k: 'shift'
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 6.5,
      flex: 1
    }
  }, ['z', 'x', 'c', 'v', 'b', 'n', 'm'].map(l => key(l, {
    flex: true,
    k: l
  }))), key(icons.del, {
    w: 45,
    k: 'del'
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 6,
      alignItems: 'center'
    }
  }, key('ABC', {
    w: 92.25,
    fs: 18,
    k: 'abc'
  }), key('', {
    flex: true,
    k: 'space'
  }), key(icons.ret, {
    w: 92.25,
    ret: true,
    k: 'ret'
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      height: 56,
      width: '100%',
      position: 'relative'
    }
  }));
}
Object.assign(window, {
  IOSDevice,
  IOSStatusBar,
  IOSNavBar,
  IOSGlassPill,
  IOSList,
  IOSListRow,
  IOSKeyboard
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/mobile/ios-frame.jsx", error: String((e && e.message) || e) }); }


// components/data/Table.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Table — the maker's primary data surface: a mono, dense, die-cut grid.
 * 2px die-cut outer border, 1px hairline row rules, uppercase mono header
 * with optional sort caret, optional zebra, right-aligned numerics, and an
 * optional serial mono first column. Sortable headers are REAL buttons.
 *
 * Controlled (sortKey/sortDir/onSort) or uncontrolled (defaultSortKey/defaultSortDir),
 * matching the Switch pattern — pass the value to control it, omit to let it self-drive.
 */
function Table({
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
    return () => {
      mq.removeEventListener ? mq.removeEventListener('change', sync) : mq.removeListener(sync);
    };
  }, []);

  // uncontrolled sort state; controlled props win when present.
  const [ownKey, setOwnKey] = React.useState(defaultSortKey);
  const [ownDir, setOwnDir] = React.useState(defaultSortDir);
  const aKey = sortKey !== undefined ? sortKey : ownKey;
  const aDir = sortDir !== undefined ? sortDir : ownDir;
  const requestSort = key => {
    const nextDir = aKey === key && aDir === 'asc' ? 'desc' : 'asc';
    if (sortKey === undefined) setOwnKey(key);
    if (sortDir === undefined) setOwnDir(nextDir);
    onSort && onSort(key, nextDir);
  };

  // when uncontrolled AND a sort key is live, sort a copy locally.
  const selfSorting = sortKey === undefined && onSort == null && aKey != null;
  const data = React.useMemo(() => {
    if (!selfSorting) return rows;
    const col = columns.find(c => c.key === aKey);
    const cmp = col && col.compare || defaultCompare;
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
      verticalAlign: 'bottom'
    };
    const labelStyle = {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-3xs)',
      fontWeight: 'var(--w-bold)',
      letterSpacing: 'var(--ls-wide)',
      textTransform: 'uppercase',
      color: active ? 'var(--amber)' : 'var(--text-dim)'
    };
    if (!col.sortable) {
      return /*#__PURE__*/React.createElement("th", {
        key: col.key,
        scope: "col",
        "aria-sort": align === 'right' ? undefined : 'none',
        style: base
      }, /*#__PURE__*/React.createElement("span", {
        style: labelStyle
      }, col.label));
    }
    const ariaSort = active ? aDir === 'asc' ? 'ascending' : 'descending' : 'none';
    return /*#__PURE__*/React.createElement("th", {
      key: col.key,
      scope: "col",
      "aria-sort": ariaSort,
      style: base
    }, /*#__PURE__*/React.createElement("button", {
      type: "button",
      className: "sbx-table-sort",
      onClick: () => requestSort(col.key),
      style: {
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
        letterSpacing: 'inherit'
      }
    }, /*#__PURE__*/React.createElement("span", null, col.label), /*#__PURE__*/React.createElement(Caret, {
      active: active,
      dir: aDir,
      transition: caretT
    })));
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      border: '2px solid var(--ink)',
      boxShadow: 'var(--shadow-slap)',
      background: 'var(--surface)',
      overflowX: 'auto',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("table", {
    style: {
      width: '100%',
      borderCollapse: 'collapse',
      fontFamily: 'var(--font-mono)',
      color: 'var(--text)'
    }
  }, caption ? /*#__PURE__*/React.createElement("caption", {
    style: {
      captionSide: 'top',
      textAlign: 'left',
      padding: `${cellPadV} ${cellPadH}`,
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-3xs)',
      letterSpacing: 'var(--ls-wide)',
      textTransform: 'uppercase',
      color: 'var(--text-faint)',
      borderBottom: '1px solid var(--border)'
    }
  }, caption) : null, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, serial ? /*#__PURE__*/React.createElement("th", {
    scope: "col",
    "aria-hidden": "true",
    style: {
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
      whiteSpace: 'nowrap'
    }
  }, '№') : null, columns.map((col, i) => headCell(col, i)))), /*#__PURE__*/React.createElement("tbody", null, data.length === 0 ? /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("td", {
    colSpan: columns.length + (serial ? 1 : 0),
    style: {
      padding: dense ? '12px' : '20px',
      textAlign: 'center',
      fontFamily: 'var(--font-mono)',
      fontSize: dataFs,
      letterSpacing: 'var(--ls-wide)',
      textTransform: 'uppercase',
      color: 'var(--text-faint)'
    }
  }, '—', " no rows ", '—')) : data.map((row, ri) => {
    const zebraBg = zebra && ri % 2 === 1 ? 'var(--surface-2)' : 'transparent';
    return /*#__PURE__*/React.createElement("tr", {
      key: row.id != null ? row.id : ri,
      style: {
        background: zebraBg
      }
    }, serial ? /*#__PURE__*/React.createElement("td", {
      style: {
        padding: `${cellPadV} ${cellPadH}`,
        textAlign: 'right',
        borderBottom: '1px solid var(--border)',
        borderRight: '1px solid var(--border)',
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--t-3xs)',
        color: 'var(--text-faint)',
        fontVariantNumeric: 'tabular-nums',
        whiteSpace: 'nowrap',
        userSelect: 'none'
      }
    }, String(ri + 1).padStart(2, '0')) : null, columns.map((col, ci) => {
      const align = col.align || 'left';
      const numeric = align === 'right';
      const raw = row[col.key];
      const content = col.render ? col.render(raw, row, ri) : raw;
      const isSortCol = aKey === col.key;
      return /*#__PURE__*/React.createElement("td", {
        key: col.key,
        style: {
          padding: `${cellPadV} ${cellPadH}`,
          textAlign: align,
          borderBottom: '1px solid var(--border)',
          borderRight: ci < columns.length - 1 ? '1px solid var(--border)' : undefined,
          fontFamily: 'var(--font-mono)',
          fontSize: dataFs,
          lineHeight: 'var(--lh-mono)',
          color: isSortCol ? 'var(--text)' : 'var(--text-dim)',
          fontVariantNumeric: numeric ? 'tabular-nums' : undefined,
          fontWeight: isSortCol ? 'var(--w-medium)' : 'var(--w-regular)',
          whiteSpace: numeric ? 'nowrap' : undefined
        }
      }, content);
    }));
  }))));
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
    el.textContent = '.sbx-table-sort:focus-visible{outline:2px solid var(--cyan);outline-offset:2px;}' + '.sbx-table-sort:focus:not(:focus-visible){outline:none;}';
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
function Caret({
  active,
  dir,
  transition
}) {
  if (!active) {
    return /*#__PURE__*/React.createElement("span", {
      "aria-hidden": "true",
      style: {
        fontFamily: 'var(--font-crt)',
        fontSize: 'var(--t-xs)',
        lineHeight: 1,
        color: 'var(--text-faint)',
        opacity: 0.5
      }
    }, '↕');
  }
  return /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      fontFamily: 'var(--font-crt)',
      fontSize: 'var(--t-xs)',
      lineHeight: 1,
      color: 'var(--amber)',
      display: 'inline-block',
      transform: dir === 'desc' ? 'rotate(180deg)' : 'rotate(0deg)',
      transition
    }
  }, '▲');
}
Object.assign(__ds_scope, { Table });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/Table.jsx", error: String((e && e.message) || e) }); }

// components/data/List.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * List — a dense vertical feed of die-cut rows. The workshop primitive for
 * runs, inventory, log lines, queues. Each row: a leading status dot or serial,
 * a mono primary label, optional faint meta, optional trailing value/action.
 *
 * Mono by the law: ink-on-void, no color required to read it. Status is a
 * SINGLE-INK dot (hollow ring → tinted ink), never a fill. Selectable rows are
 * real focusable buttons (keyboard + AT + pointer all land), the active row
 * wears one earned amber edge. Motion is a hard mechanical slide on the active
 * marker; prefers-reduced-motion shows the end-state with no travel.
 */
function List({
  items = [],
  onSelect,
  value,
  defaultValue = null,
  dense = false,
  divided = true,
  style,
  ...rest
}) {
  const selectable = typeof onSelect === 'function';
  const [internal, setInternal] = React.useState(defaultValue);
  const sel = value !== undefined ? value : internal;
  const [reduced, setReduced] = React.useState(false);
  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => setReduced(mq.matches);
    sync();
    mq.addEventListener ? mq.addEventListener('change', sync) : mq.addListener(sync);
    return () => {
      mq.removeEventListener ? mq.removeEventListener('change', sync) : mq.removeListener(sync);
    };
  }, []);

  // single-ink status inks — dots, never fills
  const statusInk = {
    active: 'var(--amber)',
    ok: 'var(--green)',
    rebel: 'var(--magenta)',
    link: 'var(--cyan)',
    warn: 'var(--hazard)',
    danger: 'var(--alert)',
    idle: 'var(--text-faint)'
  };
  const pick = id => {
    if (!selectable) return;
    if (value === undefined) setInternal(id);
    onSelect(id);
  };

  // roving arrow-key movement across rows (focusable rows are real buttons)
  const onKeyDown = (e, idx) => {
    if (!selectable) return;
    const rows = e.currentTarget.parentElement?.querySelectorAll('[data-row="1"]');
    if (!rows) return;
    let next = -1;
    if (e.key === 'ArrowDown') next = Math.min(idx + 1, rows.length - 1);else if (e.key === 'ArrowUp') next = Math.max(idx - 1, 0);else if (e.key === 'Home') next = 0;else if (e.key === 'End') next = rows.length - 1;
    if (next >= 0) {
      e.preventDefault();
      rows[next].focus();
    }
  };
  const rowPadV = dense ? '5px' : '9px';
  return /*#__PURE__*/React.createElement("div", _extends({
    role: selectable ? 'listbox' : 'list',
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: dense ? 'var(--t-xs)' : 'var(--t-sm)',
      color: 'var(--text)',
      background: 'var(--bg-sunken)',
      border: '2px solid var(--border)',
      borderRadius: 0,
      ...style
    }
  }, rest), items.map((it, idx) => {
    const isSel = selectable && sel != null && it.id === sel;
    const ink = statusInk[it.status] || (it.status ? 'var(--text-faint)' : null);
    const serial = it.serial != null ? String(it.serial) : null;
    const lead = /*#__PURE__*/React.createElement("span", {
      style: {
        flex: 'none',
        width: 18,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center'
      }
    }, serial != null ? /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--t-3xs)',
        color: 'var(--text-faint)',
        letterSpacing: 'var(--ls-normal)',
        fontVariantNumeric: 'tabular-nums'
      }
    }, serial) : ink ?
    /*#__PURE__*/
    // single-ink status dot — hollow ring with a tinted ink core, never a fill
    React.createElement("span", {
      "aria-hidden": "true",
      style: {
        width: 9,
        height: 9,
        borderRadius: 'var(--r-seal)',
        border: `2px solid ${ink}`,
        background: 'transparent',
        boxSizing: 'border-box'
      }
    }) : /*#__PURE__*/React.createElement("span", {
      "aria-hidden": "true",
      style: {
        color: 'var(--text-faint)'
      }
    }, "\xB7"));
    const body = /*#__PURE__*/React.createElement("span", {
      style: {
        flex: '1 1 auto',
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        textAlign: 'left'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        color: 'var(--text)',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        fontWeight: isSel ? 700 : 400
      }
    }, it.label), it.meta != null && /*#__PURE__*/React.createElement("span", {
      style: {
        color: 'var(--text-faint)',
        fontSize: 'var(--t-3xs)',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis'
      }
    }, it.meta));
    const trailing = it.trailing != null && /*#__PURE__*/React.createElement("span", {
      style: {
        flex: 'none',
        color: 'var(--text-dim)',
        fontVariantNumeric: 'tabular-nums',
        letterSpacing: 'var(--ls-normal)',
        whiteSpace: 'nowrap',
        paddingLeft: 'var(--sp-3)'
      }
    }, it.trailing);

    // status label for AT (the dot is decorative)
    const statusWord = it.status ? `, ${it.status}` : '';
    const inner = /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("span", {
      "aria-hidden": "true",
      style: {
        position: 'absolute',
        left: 0,
        top: 0,
        bottom: 0,
        width: 3,
        background: 'var(--amber)',
        transform: isSel ? 'scaleY(1)' : 'scaleY(0)',
        transformOrigin: 'top',
        transition: reduced ? 'none' : 'transform var(--dur-1) var(--ease-snap)'
      }
    }), lead, body, trailing);
    const sharedStyle = {
      position: 'relative',
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--sp-2)',
      width: '100%',
      boxSizing: 'border-box',
      padding: `${rowPadV} var(--sp-3) ${rowPadV} var(--sp-3)`,
      borderTop: divided && idx > 0 ? '1px solid var(--border)' : 'none',
      background: isSel ? 'var(--surface-2)' : 'transparent',
      color: 'inherit',
      fontFamily: 'inherit',
      fontSize: 'inherit',
      textAlign: 'left'
    };
    if (selectable) {
      return /*#__PURE__*/React.createElement("button", {
        key: it.id ?? idx,
        type: "button",
        "data-row": "1",
        role: "option",
        "aria-selected": isSel,
        "aria-label": `${it.label}${it.meta != null ? ', ' + it.meta : ''}${statusWord}`,
        tabIndex: isSel || sel == null && idx === 0 ? 0 : -1,
        onClick: () => pick(it.id),
        onKeyDown: e => onKeyDown(e, idx),
        style: {
          ...sharedStyle,
          border: 'none',
          cursor: 'pointer',
          outline: 'none',
          appearance: 'none',
          WebkitTapHighlightColor: 'transparent'
        },
        onFocus: e => {
          e.currentTarget.style.boxShadow = 'inset 0 0 0 2px var(--amber)';
        },
        onBlur: e => {
          e.currentTarget.style.boxShadow = 'none';
        }
      }, inner);
    }
    return /*#__PURE__*/React.createElement("div", {
      key: it.id ?? idx,
      "data-row": "1",
      role: "listitem",
      style: sharedStyle
    }, inner);
  }));
}
Object.assign(__ds_scope, { List });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/List.jsx", error: String((e && e.message) || e) }); }

// components/data/Stat.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* reduced-motion check, recomputed live (no calendar, only state) */
function useReducedMotion() {
  const [reduced, setReduced] = React.useState(false);
  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const apply = () => setReduced(!!mq.matches);
    apply();
    mq.addEventListener ? mq.addEventListener('change', apply) : mq.addListener(apply);
    return () => {
      mq.removeEventListener ? mq.removeEventListener('change', apply) : mq.removeListener(apply);
    };
  }, []);
  return reduced;
}
const TONES = {
  default: 'var(--text)',
  active: 'var(--amber)',
  rebel: 'var(--magenta)',
  ok: 'var(--green)',
  link: 'var(--cyan)'
};

/**
 * Stat — a workshop metric tile. Big brutalist display number on void,
 * uppercase mono label, optional unit, optional delta with a single-ink
 * up/down mark. Mono by default; ONE earned accent via `tone`. Die-cut:
 * 0px radius, 2px border, hard offset shadow, no soft blur.
 */
function Stat({
  label,
  value,
  unit,
  delta,
  tone = 'default',
  style,
  ...rest
}) {
  const reduced = useReducedMotion();
  const accent = TONES[tone] || TONES.default;

  // delta: number → signed; string passes through. up = good (green-ink),
  // down = warn (alert-ink). Single-ink marks, never fills.
  let dDir = 0; // 1 up, -1 down, 0 flat
  if (typeof delta === 'number') dDir = delta > 0 ? 1 : delta < 0 ? -1 : 0;else if (typeof delta === 'string') dDir = /^-/.test(delta.trim()) ? -1 : /^\+/.test(delta.trim()) ? 1 : 0;
  const dMark = dDir > 0 ? '▲' : dDir < 0 ? '▼' : '—'; // ▲ ▼ —
  const dInk = dDir > 0 ? 'var(--green)' : dDir < 0 ? 'var(--alert)' : 'var(--text-faint)';
  const dText = typeof delta === 'number' ? (delta > 0 ? '+' : '') + delta : delta;
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'inline-flex',
      flexDirection: 'column',
      gap: 6,
      minWidth: 132,
      padding: '14px 16px 13px',
      background: 'var(--bg-sunken)',
      border: '2px solid var(--border-ink)',
      borderRadius: 0,
      boxShadow: '3px 3px 0 var(--ink)',
      boxSizing: 'border-box',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-3xs)',
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: 'var(--ls-wide)',
      color: 'var(--text-faint)',
      lineHeight: 1,
      whiteSpace: 'nowrap'
    }
  }, label), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'flex',
      alignItems: 'baseline',
      gap: 5,
      lineHeight: 'var(--lh-tight)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 900,
      fontSize: 'var(--t-3xl)',
      letterSpacing: 'var(--ls-tight)',
      color: accent,
      fontVariantNumeric: 'tabular-nums',
      textShadow: tone !== 'default' ? '0 0 8px currentColor' : 'none'
    }
  }, value), unit != null && unit !== '' && /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-sm)',
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: 'var(--ls-wide)',
      color: 'var(--text-dim)'
    }
  }, unit)), delta != null && delta !== '' && /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 5,
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-xs)',
      fontWeight: 700,
      letterSpacing: 'var(--ls-normal)',
      color: dInk,
      lineHeight: 1
    }
  }, /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      fontSize: 9,
      transform: reduced ? 'none' : 'translateY(0.5px)'
    }
  }, dMark), /*#__PURE__*/React.createElement("span", null, dText)));
}

/**
 * KeyValue — a tight mono definition list: key → value rows, hairline-
 * separated, dense. The see-the-parts surface for a small spec of facts.
 * Renders a real <dl>/<dt>/<dd> so it is a definition list to assistive tech.
 */
function KeyValue({
  pairs = [],
  dense = false,
  align = 'right',
  style,
  ...rest
}) {
  const rows = Array.isArray(pairs) ? pairs : [];
  const padY = dense ? 4 : 7;
  return /*#__PURE__*/React.createElement("dl", _extends({
    style: {
      margin: 0,
      display: 'grid',
      gridTemplateColumns: 'max-content 1fr',
      columnGap: 14,
      rowGap: 0,
      fontFamily: 'var(--font-mono)',
      fontSize: dense ? 'var(--t-xs)' : 'var(--t-sm)',
      lineHeight: 'var(--lh-mono)',
      border: '2px solid var(--border-ink)',
      borderRadius: 0,
      background: 'var(--bg-sunken)',
      boxShadow: '3px 3px 0 var(--ink)',
      boxSizing: 'border-box',
      ...style
    }
  }, rest), rows.map((p, i) => {
    const last = i === rows.length - 1;
    const line = last ? 'none' : '1px solid var(--border)';
    return /*#__PURE__*/React.createElement(React.Fragment, {
      key: i
    }, /*#__PURE__*/React.createElement("dt", {
      style: {
        padding: `${padY}px 0 ${padY}px 12px`,
        borderBottom: line,
        color: 'var(--text-faint)',
        textTransform: 'uppercase',
        letterSpacing: 'var(--ls-wide)',
        fontSize: 'var(--t-3xs)',
        fontWeight: 700,
        whiteSpace: 'nowrap',
        alignSelf: 'center'
      }
    }, p.k), /*#__PURE__*/React.createElement("dd", {
      style: {
        margin: 0,
        padding: `${padY}px 12px ${padY}px 0`,
        borderBottom: line,
        color: 'var(--text)',
        textAlign: align,
        fontVariantNumeric: 'tabular-nums',
        alignSelf: 'center',
        overflowWrap: 'anywhere'
      }
    }, p.v));
  }));
}
Object.assign(__ds_scope, { Stat, KeyValue });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/Stat.jsx", error: String((e && e.message) || e) }); }

// components/data/CodeBlock.jsx
try { (() => {
const SlapButton = __ds_scope.SlapButton;
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * CodeBlock — a die-cut terminal/log/code surface. Sunken void, mono ink,
 * optional line numbers, an optional copy slap, an optional title bar, and
 * single-ink log tones. Whitespace is preserved; nothing is highlighted in
 * color unless a log line earns one accent. Mono by default — color is earned.
 *
 * Pass `code` (a string) OR `lines` (array of strings, or array of
 * `{ text, tone }` for the log variant). Controlled-free: it just renders.
 */
function CodeBlock({
  code,
  lines,
  lang = 'text',
  title,
  showLineNumbers = false,
  variant = 'code',
  // 'code' | 'log'
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
    return src.map(row => typeof row === 'string' ? {
      text: row,
      tone: undefined
    } : {
      text: row.text ?? '',
      tone: row.tone
    });
  }, [code, lines]);
  const rawText = React.useMemo(() => rows.map(r => r.text).join('\n'), [rows]);

  // ---- single-ink log tones (NEVER fills — only the text-ink changes) ------
  const toneInk = {
    ok: 'var(--green)',
    warn: 'var(--warn)',
    err: 'var(--alert)',
    info: 'var(--link)',
    dim: 'var(--text-faint)',
    rebel: 'var(--magenta)'
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
  return /*#__PURE__*/React.createElement("figure", _extends({
    style: {
      margin: 0,
      background: 'var(--bg-sunken)',
      border: 'var(--bw-1) solid var(--ink)',
      boxShadow: 'var(--shadow-slap)',
      fontFamily: variant === 'log' ? 'var(--font-crt)' : 'var(--font-mono)',
      fontSize: variant === 'log' ? 'var(--t-sm)' : 'var(--t-xs)',
      lineHeight: 'var(--lh-mono)',
      color: 'var(--text)',
      ...style
    }
  }, props), showBar && /*#__PURE__*/React.createElement("figcaption", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 'var(--sp-3)',
      padding: '6px 8px 6px 10px',
      borderBottom: 'var(--bw-1) solid var(--border)',
      background: 'var(--surface-2)',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-3xs)',
      textTransform: 'uppercase',
      letterSpacing: 'var(--ls-wide)',
      color: 'var(--text-dim)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 'var(--sp-2)',
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      color: 'var(--text-faint)'
    }
  }, '■'), title != null && /*#__PURE__*/React.createElement("span", {
    style: {
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, title), lang && lang !== 'text' && /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--text-faint)'
    }
  }, '·', " ", lang)), copyable && /*#__PURE__*/React.createElement(SlapButton, {
    tone: "ghost",
    size: "sm",
    onClick: copy,
    "aria-label": copied ? 'copied to clipboard' : 'copy code to clipboard'
  }, copied ? '✓ copied' : 'copy')), /*#__PURE__*/React.createElement("div", {
    style: {
      overflow: 'auto',
      maxHeight: maxHeight
    }
  }, /*#__PURE__*/React.createElement("pre", {
    "aria-label": title ? `${variant === 'log' ? 'log' : 'code'}: ${title}` : variant === 'log' ? 'log output' : `${lang} code`,
    style: {
      margin: 0,
      padding: '10px 12px',
      display: 'grid',
      gridTemplateColumns: showLineNumbers ? 'auto 1fr' : '1fr',
      columnGap: showLineNumbers ? 'var(--sp-3)' : 0,
      whiteSpace: 'pre',
      tabSize: 2,
      overflow: 'visible',
      fontFamily: 'inherit'
    }
  }, rows.map((row, i) => /*#__PURE__*/React.createElement(React.Fragment, {
    key: i
  }, showLineNumbers && /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      color: 'var(--text-faint)',
      textAlign: 'right',
      userSelect: 'none',
      minWidth: `${gutterW}ch`,
      fontVariantNumeric: 'tabular-nums'
    }
  }, i + 1), /*#__PURE__*/React.createElement("code", {
    style: {
      fontFamily: 'inherit',
      color: row.tone && toneInk[row.tone] ? toneInk[row.tone] : 'inherit',
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word'
    }
  }, row.text.length ? row.text : ' '))))), /*#__PURE__*/React.createElement("span", {
    ref: liveRef,
    "aria-live": "polite",
    style: {
      position: 'absolute',
      width: 1,
      height: 1,
      padding: 0,
      margin: -1,
      overflow: 'hidden',
      clip: 'rect(0 0 0 0)',
      whiteSpace: 'nowrap',
      border: 0
    }
  }));
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
  const get = () => typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(query).matches : false;
  const [reduce, setReduce] = React.useState(get);
  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return undefined;
    const mq = window.matchMedia(query);
    const onChange = () => setReduce(mq.matches);
    if (mq.addEventListener) mq.addEventListener('change', onChange);else mq.addListener(onChange);
    return () => {
      if (mq.removeEventListener) mq.removeEventListener('change', onChange);else mq.removeListener(onChange);
    };
  }, []);
  return reduce;
}
Object.assign(__ds_scope, { CodeBlock });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/CodeBlock.jsx", error: String((e && e.message) || e) }); }

// components/nav/Nav.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Nav — the workbench side navigation: a die-cut control rail.
 *
 * Sections carry an uppercase mono group label; each item is a flat row. The
 * active item is the ONE earned accent in the view — a left die-cut bar plus
 * brand-ink text. Items can carry a leading mark (a CRT/pixel unicode glyph,
 * never emoji) and a trailing count. Mono base, hard 0px radius, 2px die-cut
 * edges. Keyboard-driven (Arrow Up/Down roves, Enter/Space selects), real
 * <nav> landmark, aria-current on the live item.
 */
const REDUCED = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
function useReducedMotion() {
  const [reduced, setReduced] = React.useState(REDUCED ? REDUCED.matches : false);
  React.useEffect(() => {
    if (!REDUCED) return;
    const on = () => setReduced(REDUCED.matches);
    REDUCED.addEventListener ? REDUCED.addEventListener('change', on) : REDUCED.addListener(on);
    return () => REDUCED.removeEventListener ? REDUCED.removeEventListener('change', on) : REDUCED.removeListener(on);
  }, []);
  return reduced;
}
function Nav({
  sections = [],
  activeId,
  onSelect,
  collapsed = false,
  accent = 'var(--amber)',
  ariaLabel = 'Workbench',
  style,
  ...rest
}) {
  const reduced = useReducedMotion();

  // Flat ordered list of selectable item ids — the keyboard roving order.
  const flat = React.useMemo(() => {
    const out = [];
    sections.forEach(sec => (sec.items || []).forEach(it => out.push(it)));
    return out;
  }, [sections]);

  // Roving tabindex focus: track the focused row independent of the active row.
  const startIndex = Math.max(0, flat.findIndex(it => it.id === activeId));
  const [focusIndex, setFocusIndex] = React.useState(startIndex === -1 ? 0 : startIndex);
  const itemRefs = React.useRef({});
  React.useEffect(() => {
    const i = flat.findIndex(it => it.id === activeId);
    if (i >= 0) setFocusIndex(i);
  }, [activeId, flat]);
  const focusRow = i => {
    const clamped = (i + flat.length) % flat.length;
    setFocusIndex(clamped);
    const el = itemRefs.current[flat[clamped] && flat[clamped].id];
    if (el) el.focus();
  };
  const onKeyDown = (e, idx) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        focusRow(idx + 1);
        break;
      case 'ArrowUp':
        e.preventDefault();
        focusRow(idx - 1);
        break;
      case 'Home':
        e.preventDefault();
        focusRow(0);
        break;
      case 'End':
        e.preventDefault();
        focusRow(flat.length - 1);
        break;
      case 'Enter':
      case ' ':
        e.preventDefault();
        onSelect && onSelect(flat[idx].id);
        break;
      default:
        break;
    }
  };
  const trans = reduced ? 'none' : 'background var(--dur-1) var(--ease-snap), color var(--dur-1) var(--ease-snap)';
  return /*#__PURE__*/React.createElement("nav", _extends({
    "aria-label": ariaLabel,
    style: {
      boxSizing: 'border-box',
      width: collapsed ? 60 : 232,
      background: 'var(--bg-sunken)',
      border: '2px solid var(--ink)',
      boxShadow: 'var(--shadow-slap)',
      fontFamily: 'var(--font-mono)',
      color: 'var(--text)',
      padding: '10px 0',
      display: 'flex',
      flexDirection: 'column',
      gap: 14,
      userSelect: 'none',
      ...style
    }
  }, rest), sections.map((sec, si) => /*#__PURE__*/React.createElement("div", {
    key: sec.label || si,
    role: "group",
    "aria-label": sec.label
  }, sec.label ? /*#__PURE__*/React.createElement("div", {
    "aria-hidden": collapsed ? true : undefined,
    style: {
      fontSize: 'var(--t-3xs)',
      letterSpacing: 'var(--ls-mega)',
      textTransform: 'uppercase',
      color: 'var(--text-faint)',
      padding: collapsed ? '0 0 6px' : '0 14px 6px',
      textAlign: collapsed ? 'center' : 'left',
      whiteSpace: 'nowrap',
      overflow: 'hidden'
    }
  }, collapsed ? '·' : sec.label) : null, (sec.items || []).map(it => {
    const idx = flat.findIndex(f => f.id === it.id);
    const isActive = it.id === activeId;
    const isFocusTarget = idx === focusIndex;
    return /*#__PURE__*/React.createElement("button", {
      key: it.id,
      type: "button",
      ref: el => itemRefs.current[it.id] = el,
      onClick: () => onSelect && onSelect(it.id),
      onKeyDown: e => onKeyDown(e, idx),
      onMouseEnter: e => {
        if (!isActive) e.currentTarget.style.background = 'var(--surface-2)';
      },
      onMouseLeave: e => {
        if (!isActive) e.currentTarget.style.background = 'transparent';
      },
      "aria-current": isActive ? 'page' : undefined,
      title: collapsed ? it.label : undefined,
      tabIndex: isFocusTarget ? 0 : -1,
      style: {
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        gap: collapsed ? 0 : 10,
        justifyContent: collapsed ? 'center' : 'flex-start',
        width: '100%',
        boxSizing: 'border-box',
        // left die-cut bar carries the earned accent on the active row
        borderLeft: `4px solid ${isActive ? accent : 'transparent'}`,
        borderTop: 'none',
        borderRight: 'none',
        borderBottom: 'none',
        borderRadius: 0,
        background: isActive ? 'var(--surface)' : 'transparent',
        color: isActive ? accent : 'var(--text-dim)',
        fontFamily: 'var(--font-mono)',
        fontWeight: isActive ? 'var(--w-bold)' : 'var(--w-regular)',
        fontSize: 'var(--t-sm)',
        letterSpacing: 'var(--ls-wide)',
        textAlign: 'left',
        padding: collapsed ? '8px 0' : '7px 14px 7px 12px',
        margin: 0,
        cursor: 'pointer',
        outline: 'none',
        transition: trans
      },
      onFocus: e => {
        e.currentTarget.style.outline = '2px solid var(--cyan)';
        e.currentTarget.style.outlineOffset = '-2px';
      },
      onBlur: e => {
        e.currentTarget.style.outline = 'none';
        if (!isActive) e.currentTarget.style.background = 'transparent';
      }
    }, it.mark ? /*#__PURE__*/React.createElement("span", {
      "aria-hidden": "true",
      style: {
        flex: 'none',
        width: 16,
        textAlign: 'center',
        fontFamily: 'var(--font-crt)',
        fontSize: 'var(--t-md)',
        lineHeight: 1,
        color: isActive ? accent : 'var(--text-faint)'
      }
    }, it.mark) : null, !collapsed && /*#__PURE__*/React.createElement("span", {
      style: {
        flex: '1 1 auto',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis'
      }
    }, it.label), !collapsed && it.count != null ? /*#__PURE__*/React.createElement("span", {
      "aria-hidden": "true",
      style: {
        flex: 'none',
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--t-2xs)',
        letterSpacing: 'var(--ls-normal)',
        color: isActive ? accent : 'var(--text-faint)',
        border: `2px solid ${isActive ? accent : 'var(--border)'}`,
        borderRadius: 0,
        padding: '0 5px',
        minWidth: 16,
        textAlign: 'center'
      }
    }, it.count) : null, collapsed && it.count != null ? /*#__PURE__*/React.createElement("span", {
      style: {
        position: 'absolute',
        width: 1,
        height: 1,
        padding: 0,
        margin: -1,
        overflow: 'hidden',
        clip: 'rect(0 0 0 0)',
        whiteSpace: 'nowrap',
        border: 0
      }
    }, it.label, " \u2014 ", it.count) : null);
  }))));
}
Object.assign(__ds_scope, { Nav });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/nav/Nav.jsx", error: String((e && e.message) || e) }); }

// components/nav/Menu.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Menu — a die-cut dropdown / context menu: a slap that popped up.
 * Hard 2px border, hard offset shadow (no soft blur), 0px radius, mono items.
 * Each item may carry a leading mark + trailing shortcut; hairline rules
 * between groups; a `danger` item burns single-ink, never a fill.
 *
 * A11y: role="menu" / role="menuitem", Arrow/Home/End/Enter/Esc keyboard,
 * focus trapped to the items while open, focus restored to the opener on close.
 * Motion is a single snap-down popping into place — honoured against
 * prefers-reduced-motion (end-state shown, motion skipped).
 */
function Menu({
  items = [],
  onSelect,
  open = true,
  onClose,
  anchor = 'bottom-left',
  label = 'menu',
  style,
  ...rest
}) {
  const listRef = React.useRef(null);
  const itemRefs = React.useRef([]);
  const restoreRef = React.useRef(null);
  const [active, setActive] = React.useState(-1);
  const [mounted, setMounted] = React.useState(false);

  // reduced-motion: resolve once, react to OS changes.
  const [reduced, setReduced] = React.useState(false);
  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => setReduced(mq.matches);
    sync();
    mq.addEventListener ? mq.addEventListener('change', sync) : mq.addListener(sync);
    return () => {
      mq.removeEventListener ? mq.removeEventListener('change', sync) : mq.removeListener(sync);
    };
  }, []);

  // indices of the items that can actually take focus (skip separators + disabled).
  const focusable = React.useMemo(() => items.map((it, i) => ({
    it,
    i
  })).filter(({
    it
  }) => it && !it.separator && !it.disabled).map(({
    i
  }) => i), [items]);
  const focusAt = React.useCallback(idx => {
    setActive(idx);
    const el = itemRefs.current[idx];
    if (el) el.focus();
  }, []);
  const step = React.useCallback(dir => {
    if (!focusable.length) return;
    const pos = focusable.indexOf(active);
    let next;
    if (pos === -1) next = dir > 0 ? focusable[0] : focusable[focusable.length - 1];else next = focusable[(pos + dir + focusable.length) % focusable.length];
    focusAt(next);
  }, [focusable, active, focusAt]);

  // open: remember opener, snap focus to first item, raise the slap.
  React.useEffect(() => {
    if (!open) {
      setMounted(false);
      return;
    }
    restoreRef.current = typeof document !== 'undefined' ? document.activeElement : null;
    setMounted(true);
    if (focusable.length) focusAt(focusable[0]);else if (listRef.current) listRef.current.focus();
    // restore focus to opener on close.
    return () => {
      const el = restoreRef.current;
      if (el && typeof el.focus === 'function') el.focus();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // outside-click / outside-intent dismissal while open
  React.useEffect(() => {
    if (!open) return;
    const onDocPointer = e => {
      if (listRef.current && !listRef.current.contains(e.target)) onClose && onClose();
    };
    document.addEventListener('pointerdown', onDocPointer, true);
    return () => document.removeEventListener('pointerdown', onDocPointer, true);
  }, [open, onClose]);
  const choose = React.useCallback(it => {
    if (!it || it.disabled || it.separator) return;
    onSelect && onSelect(it.id, it);
    onClose && onClose();
  }, [onSelect, onClose]);
  const onKeyDown = e => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        step(1);
        break;
      case 'ArrowUp':
        e.preventDefault();
        step(-1);
        break;
      case 'Home':
        e.preventDefault();
        focusable.length && focusAt(focusable[0]);
        break;
      case 'End':
        e.preventDefault();
        focusable.length && focusAt(focusable[focusable.length - 1]);
        break;
      case 'Tab':
        // trap focus: keep it on the menu, wrap with arrow semantics.
        e.preventDefault();
        step(e.shiftKey ? -1 : 1);
        break;
      case 'Enter':
      case ' ':
        e.preventDefault();
        if (active >= 0) choose(items[active]);
        break;
      case 'Escape':
        e.preventDefault();
        onClose && onClose();
        break;
      default:
        break;
    }
  };
  if (!open) return null;

  // anchored placement — corner the slap pops from.
  const anchors = {
    'bottom-left': {
      top: '100%',
      left: 0,
      marginTop: 6
    },
    'bottom-right': {
      top: '100%',
      right: 0,
      marginTop: 6
    },
    'top-left': {
      bottom: '100%',
      left: 0,
      marginBottom: 6
    },
    'top-right': {
      bottom: '100%',
      right: 0,
      marginBottom: 6
    }
  };
  const place = anchors[anchor] || anchors['bottom-left'];
  // pop direction follows the anchor edge.
  const fromTop = anchor.indexOf('bottom') === 0;
  const popFrom = fromTop ? 'translateY(-6px)' : 'translateY(6px)';
  return /*#__PURE__*/React.createElement("div", _extends({
    ref: listRef,
    role: "menu",
    "aria-label": label,
    "aria-orientation": "vertical",
    tabIndex: -1,
    onKeyDown: onKeyDown,
    style: {
      position: 'absolute',
      zIndex: 'var(--z-overlay, 1000)',
      minWidth: 200,
      background: 'var(--bg-raised)',
      color: 'var(--text)',
      border: '2px solid var(--ink)',
      borderRadius: 0,
      boxShadow: 'var(--shadow-slap-lg)',
      padding: '4px 0',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-sm)',
      userSelect: 'none',
      opacity: mounted || reduced ? 1 : 0,
      transform: mounted || reduced ? 'translateY(0)' : popFrom,
      transition: reduced ? 'none' : 'opacity var(--dur-1) var(--ease-snap), transform var(--dur-1) var(--ease-snap)',
      ...place,
      ...style
    }
  }, rest), items.map((it, i) => {
    if (!it) return null;
    if (it.separator) {
      return /*#__PURE__*/React.createElement("div", {
        key: it.id || `sep-${i}`,
        role: "separator",
        "aria-hidden": "true",
        style: {
          height: 0,
          borderTop: '1px solid var(--border)',
          margin: '4px 0'
        }
      });
    }
    const isActive = active === i;
    const isDanger = !!it.danger;
    const isDisabled = !!it.disabled;
    const fg = isDisabled ? 'var(--text-faint)' : isDanger ? 'var(--danger)' : isActive ? 'var(--ink)' : 'var(--text)';
    return /*#__PURE__*/React.createElement(MenuRow, {
      key: it.id || `item-${i}`,
      ref: el => {
        itemRefs.current[i] = el;
      },
      item: it,
      active: isActive,
      danger: isDanger,
      disabled: isDisabled,
      fg: fg,
      reduced: reduced,
      onMouseEnter: () => !isDisabled && setActive(i),
      onClick: () => choose(it)
    });
  }));
}
const MenuRow = React.forwardRef(function MenuRow({
  item,
  active,
  danger,
  disabled,
  fg,
  reduced,
  onMouseEnter,
  onClick
}, ref) {
  // active background: amber for the live row, magenta-edged for danger — single accent per row.
  const bg = active && !disabled ? danger ? 'var(--surface-2)' : 'var(--amber)' : 'transparent';
  return /*#__PURE__*/React.createElement("div", {
    ref: ref,
    role: "menuitem",
    tabIndex: active ? 0 : -1,
    "aria-disabled": disabled || undefined,
    onMouseEnter: onMouseEnter,
    onClick: disabled ? undefined : onClick,
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '6px 14px',
      cursor: disabled ? 'not-allowed' : 'pointer',
      color: fg,
      background: bg,
      opacity: disabled ? 0.45 : 1,
      outline: 'none',
      // focus-visible ring: a hard inset die-cut edge, no glow.
      boxShadow: active && !disabled ? 'inset 0 0 0 2px var(--ink)' : 'none',
      transition: reduced ? 'none' : 'background var(--dur-1) var(--ease-snap)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      width: 16,
      flex: 'none',
      textAlign: 'center',
      fontFamily: 'var(--font-crt)',
      color: active && danger ? 'var(--danger)' : 'inherit'
    }
  }, item.mark || ''), /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1,
      whiteSpace: 'nowrap',
      letterSpacing: 'var(--ls-normal)'
    }
  }, item.label), item.shortcut && /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 'none',
      marginLeft: 18,
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--t-2xs)',
      letterSpacing: 'var(--ls-wide)',
      color: active && !disabled ? danger ? 'var(--danger)' : 'var(--ink)' : 'var(--text-faint)'
    }
  }, item.shortcut));
});
Object.assign(__ds_scope, { Menu });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/nav/Menu.jsx", error: String((e && e.message) || e) }); }

// components/nav/Pagination.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Pagination — a brutalist pager. Numbered slaps (001/002), prev/next with
 * unicode marks, the current page is the one earned accent. Mono, die-cut,
 * 0px radius, hard offset shadow. Snappy slap-down on press; honors
 * prefers-reduced-motion (end-state shown, motion skipped).
 *
 * Controlled (`page`) + uncontrolled (`defaultPage`). Real <button>s,
 * aria-label per page, aria-current on the active page, prev/next disabled
 * at the ends, focus-visible ring via focus-within.
 */
function Pagination({
  page,
  defaultPage = 1,
  pageCount,
  onChange,
  siblingCount = 1,
  accent = 'var(--amber)',
  accentEdge = 'var(--amber-deep)',
  style,
  ...rest
}) {
  const [inner, setInner] = React.useState(defaultPage);
  const current = page != null ? page : inner;
  const count = Math.max(1, pageCount | 0);
  const reduce = usePrefersReducedMotion();
  const go = next => {
    const n = clamp(next, 1, count);
    if (n === current) return;
    if (page == null) setInner(n);
    onChange && onChange(n);
  };
  const items = buildRange(current, count, Math.max(0, siblingCount | 0));
  const atStart = current <= 1;
  const atEnd = current >= count;
  return /*#__PURE__*/React.createElement("nav", _extends({
    role: "navigation",
    "aria-label": "Pagination",
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      fontFamily: 'var(--font-mono)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement(Slap, {
    kind: "edge",
    reduce: reduce,
    disabled: atStart,
    ariaLabel: "Previous page",
    onActivate: () => go(current - 1)
  }, '◀'), items.map((it, i) => it === GAP ? /*#__PURE__*/React.createElement("span", {
    key: `gap-${i}`,
    "aria-hidden": "true",
    style: {
      minWidth: 16,
      textAlign: 'center',
      color: 'var(--text-faint)',
      fontFamily: 'var(--font-crt)',
      fontSize: 'var(--t-md)',
      letterSpacing: 'var(--ls-wide)',
      userSelect: 'none'
    }
  }, '•••') : /*#__PURE__*/React.createElement(Slap, {
    key: it,
    kind: "page",
    reduce: reduce,
    active: it === current,
    accent: accent,
    accentEdge: accentEdge,
    ariaLabel: `Page ${it} of ${count}`,
    ariaCurrent: it === current ? 'page' : undefined,
    onActivate: () => go(it)
  }, pad(it))), /*#__PURE__*/React.createElement(Slap, {
    kind: "edge",
    reduce: reduce,
    disabled: atEnd,
    ariaLabel: "Next page",
    onActivate: () => go(current + 1)
  }, '▶'));
}

/* ---- one numbered/edge slap ----------------------------------------- */
function Slap({
  kind,
  children,
  active = false,
  disabled = false,
  ariaLabel,
  ariaCurrent,
  onActivate,
  reduce,
  accent = 'var(--amber)',
  accentEdge = 'var(--amber-deep)'
}) {
  const [hover, setHover] = React.useState(false);
  const [press, setPress] = React.useState(false);

  // resting die-cut offset; mechanical slap-down on press.
  const base = 3;
  const off = disabled ? base : press ? 0 : hover ? base - 1 : base;
  const shift = reduce ? 0 : base - off;
  const isEdge = kind === 'edge';
  const bg = active ? accent : 'var(--bg-sunken)';
  const fg = active ? 'var(--ink)' : disabled ? 'var(--text-faint)' : 'var(--text)';
  const edge = active ? 'var(--ink)' : 'var(--signal)';
  const shadow = active ? accentEdge : 'var(--ink)';
  return /*#__PURE__*/React.createElement("button", {
    type: "button",
    disabled: disabled,
    "aria-label": ariaLabel,
    "aria-current": ariaCurrent,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => {
      setHover(false);
      setPress(false);
    },
    onMouseDown: () => setPress(true),
    onMouseUp: () => setPress(false),
    onClick: onActivate,
    style: {
      appearance: 'none',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      minWidth: isEdge ? 30 : 38,
      height: 30,
      padding: isEdge ? '0 6px' : '0 8px',
      fontFamily: isEdge ? 'var(--font-crt)' : 'var(--font-mono)',
      fontWeight: 700,
      fontSize: isEdge ? 'var(--t-md)' : 'var(--t-sm)',
      letterSpacing: isEdge ? 'var(--ls-normal)' : 'var(--ls-wide)',
      lineHeight: 1,
      color: fg,
      background: bg,
      border: `2px solid ${edge}`,
      borderRadius: 0,
      boxShadow: disabled ? 'none' : `${off}px ${off}px 0 ${shadow}`,
      transform: `translate(${shift}px, ${shift}px)`,
      transition: reduce ? 'none' : 'box-shadow var(--dur-1) var(--ease-snap), transform var(--dur-1) var(--ease-snap)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.4 : 1,
      outline: 'none',
      userSelect: 'none'
    },
    onFocus: e => {
      e.currentTarget.style.boxShadow = (disabled ? 'none ' : `${off}px ${off}px 0 ${shadow}, `) + `0 0 0 2px var(--bg), 0 0 0 4px var(--cyan)`;
    },
    onBlur: e => {
      e.currentTarget.style.boxShadow = disabled ? 'none' : `${off}px ${off}px 0 ${shadow}`;
    }
  }, children);
}

/* ---- prefers-reduced-motion (law 4) --------------------------------- */
function usePrefersReducedMotion() {
  const [reduce, setReduce] = React.useState(false);
  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const on = () => setReduce(!!mq.matches);
    on();
    mq.addEventListener ? mq.addEventListener('change', on) : mq.addListener(on);
    return () => {
      mq.removeEventListener ? mq.removeEventListener('change', on) : mq.removeListener(on);
    };
  }, []);
  return reduce;
}

/* ---- range math ----------------------------------------------------- */
const GAP = 'gap';
function buildRange(current, count, siblings) {
  // first + last always shown; window of `siblings` either side of current.
  const total = siblings * 2 + 5; // first, last, current, 2 gaps, 2*siblings
  if (count <= total) return seq(1, count);
  const left = Math.max(current - siblings, 1);
  const right = Math.min(current + siblings, count);
  const showLeftGap = left > 2;
  const showRightGap = right < count - 1;
  const out = [1];
  if (showLeftGap) out.push(GAP);else for (let n = 2; n < left; n++) out.push(n);
  for (let n = left; n <= right; n++) if (n !== 1 && n !== count) out.push(n);
  if (showRightGap) out.push(GAP);else for (let n = right + 1; n < count; n++) out.push(n);
  out.push(count);
  return out;
}
function seq(a, b) {
  const r = [];
  for (let n = a; n <= b; n++) r.push(n);
  return r;
}
function clamp(n, lo, hi) {
  return Math.min(hi, Math.max(lo, n));
}
function pad(n) {
  return String(n).padStart(3, '0');
}
Object.assign(__ds_scope, { Pagination });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/nav/Pagination.jsx", error: String((e && e.message) || e) }); }

__ds_ns.GhostEye = __ds_scope.GhostEye;

__ds_ns.VHSHeadline = __ds_scope.VHSHeadline;

__ds_ns.BootCoin = __ds_scope.BootCoin;

__ds_ns.Cartridge = __ds_scope.Cartridge;

__ds_ns.Avatar = __ds_scope.Avatar;

__ds_ns.Dialog = __ds_scope.Dialog;

__ds_ns.FaceToggle = __ds_scope.FaceToggle;

__ds_ns.Field = __ds_scope.Field;

__ds_ns.Loader = __ds_scope.Loader;

__ds_ns.SlapButton = __ds_scope.SlapButton;

__ds_ns.Toast = __ds_scope.Toast;

__ds_ns.Tooltip = __ds_scope.Tooltip;

__ds_ns.Window = __ds_scope.Window;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.Radio = __ds_scope.Radio;

__ds_ns.Knob = __ds_scope.Knob;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Switch = __ds_scope.Switch;

__ds_ns.Tabs = __ds_scope.Tabs;

__ds_ns.CharacterSlap = __ds_scope.CharacterSlap;

__ds_ns.Sticker = __ds_scope.Sticker;

__ds_ns.Barcode = __ds_scope.Barcode;


__ds_ns.Table = __ds_scope.Table;

__ds_ns.List = __ds_scope.List;

__ds_ns.Stat = __ds_scope.Stat;

__ds_ns.KeyValue = __ds_scope.KeyValue;

__ds_ns.CodeBlock = __ds_scope.CodeBlock;

__ds_ns.Nav = __ds_scope.Nav;

__ds_ns.Menu = __ds_scope.Menu;

__ds_ns.Pagination = __ds_scope.Pagination;

})();
