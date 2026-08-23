import React from 'react';

/**
 * GhostEye — the SandboxOS character as an ownable 1-bit dithered GAZE.
 * "always around, never owned" — a curious, nosy little companion that
 * watches your build come together. A halftone eye, drawn + Floyd–Steinberg
 * dithered entirely in code (no asset). This is the always-present mascot —
 * the full seductive figure is reserved for hero/dossier slots via real art
 * through the same dither pipeline. Avoids the uncanny-bust trap.
 *
 * The pupil tracks the cursor when `watch`; she blinks on an interval.
 * One magenta accent (the iris) — color earned on her. Reduced-motion safe.
 */
export function GhostEye({ size = 180, accent = 'var(--magenta)', mood = 'rebel', watch = true, blink = true, style, ...rest }) {
  const ref = React.useRef(null);
  const wrapRef = React.useRef(null);
  const target = React.useRef({ x: 0, y: 0 });
  const state = React.useRef({ x: 0, y: 0, lid: 0 });

  const resolve = (c) => {
    if (typeof c === 'string' && c.startsWith('var(')) {
      const v = getComputedStyle(document.documentElement).getPropertyValue(c.slice(4, -1).split(',')[0].trim()).trim();
      return v || '#FF2E88';
    }
    return c;
  };

  React.useEffect(() => {
    const cv = ref.current; if (!cv) return;
    const W = size, H = Math.round(size * 0.62); cv.width = W; cv.height = H;
    const ctx = cv.getContext('2d');
    const irisCol = resolve(accent);
    const RM = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let raf = 0, blinkT = performance.now() + 2600, lidV = 0, lidDir = 0;

    function hexRGB(h){ const n = parseInt(h.replace('#',''),16); return [n>>16&255,n>>8&255,n&255]; }
    const IRIS = hexRGB(irisCol.startsWith('#') ? irisCol : '#FF2E88');

    function draw(px, py, lid) {
      const off = document.createElement('canvas'); off.width = W; off.height = H;
      const g = off.getContext('2d'); g.clearRect(0, 0, W, H);
      const cx = W/2, cy = H/2, ew = W*0.46, eh = H*0.42;
      // eyeball white (almond)
      g.fillStyle = '#efe9da';
      g.beginPath();
      g.moveTo(cx-ew, cy);
      g.quadraticCurveTo(cx, cy-eh*1.25, cx+ew, cy);
      g.quadraticCurveTo(cx, cy+eh*1.25, cx-ew, cy);
      g.closePath(); g.fill();
      // radial iris striations (drawn gray, keyed to accent after dither via overlay)
      const ix = cx + px*ew*0.42, iy = cy + py*eh*0.4, ir = eh*0.92;
      const grd = g.createRadialGradient(ix, iy, 2, ix, iy, ir);
      grd.addColorStop(0, '#fff'); grd.addColorStop(0.4, '#bbb'); grd.addColorStop(1, '#666');
      g.save(); g.beginPath(); g.moveTo(cx-ew, cy); g.quadraticCurveTo(cx, cy-eh*1.25, cx+ew, cy); g.quadraticCurveTo(cx, cy+eh*1.25, cx-ew, cy); g.closePath(); g.clip();
      g.fillStyle = grd; g.beginPath(); g.arc(ix, iy, ir, 0, 7); g.fill();
      g.strokeStyle = 'rgba(255,255,255,0.5)'; g.lineWidth = 1;
      for (let a=0; a<24; a++){ const an=a/24*Math.PI*2; g.beginPath(); g.moveTo(ix+Math.cos(an)*ir*0.3, iy+Math.sin(an)*ir*0.3); g.lineTo(ix+Math.cos(an)*ir, iy+Math.sin(an)*ir); g.stroke(); }
      // pupil
      g.fillStyle = '#0a0a08'; g.beginPath(); g.arc(ix, iy, ir*0.42, 0, 7); g.fill();
      // catchlight = the life
      g.fillStyle = '#fff'; g.beginPath(); g.arc(ix-ir*0.22, iy-ir*0.24, ir*0.16, 0, 7); g.fill();
      g.restore();
      // lid (blink) — cover from top & bottom
      if (lid > 0.01) { g.fillStyle = '#0f0f0d'; const c = lid*eh*1.25; g.fillRect(cx-ew, cy-eh*1.25, ew*2, c); g.fillRect(cx-ew, cy+eh*1.25-c, ew*2, c); }
      // upper lid line + lashes
      g.strokeStyle = '#0f0f0d'; g.lineWidth = Math.max(2, W*0.012); g.lineCap='round';
      g.beginPath(); g.moveTo(cx-ew, cy); g.quadraticCurveTo(cx, cy-eh*1.3, cx+ew, cy); g.stroke();
      g.lineWidth = Math.max(1, W*0.006);
      g.beginPath(); g.moveTo(cx+ew, cy); g.lineTo(cx+ew*1.12, cy-eh*0.4); g.stroke();
      g.beginPath(); g.moveTo(cx-ew, cy); g.lineTo(cx-ew*1.12, cy-eh*0.35); g.stroke();

      // ---- dither pass (Floyd–Steinberg) ----
      const dd = g.getImageData(0,0,W,H).data;
      const lum = new Float32Array(W*H), isIris = new Uint8Array(W*H);
      for (let i=0;i<W*H;i++){ const a=dd[i*4+3]/255; lum[i]=a*((0.299*dd[i*4]+0.587*dd[i*4+1]+0.114*dd[i*4+2])/255);
        // iris ring = mid-bright pixels inside iris radius → accent
        const x=i%W, y=(i/W)|0; const din=Math.hypot(x-ix,y-iy);
        if (a>0.5 && din<ir*0.95 && din>ir*0.42) isIris[i]=1;
      }
      const buf = lum.slice();
      const out = new Uint8Array(W*H);
      for (let y=0;y<H;y++)for(let x=0;x<W;x++){ const i=y*W+x; const o=buf[i]; const nv=o>0.5?1:0; out[i]=nv; const e=o-nv;
        if(x+1<W)buf[i+1]+=e*7/16; if(y+1<H){ if(x>0)buf[i-1+W]+=e*3/16; buf[i+W]+=e*5/16; if(x+1<W)buf[i+1+W]+=e*1/16; } }
      const im = ctx.createImageData(W,H), p = im.data;
      const bone = [246,242,231];
      for (let i=0;i<W*H;i++){ if(out[i]){ const c = isIris[i]?IRIS:bone; p[i*4]=c[0];p[i*4+1]=c[1];p[i*4+2]=c[2];p[i*4+3]=255; } }
      ctx.clearRect(0,0,W,H); ctx.putImageData(im,0,0);
    }

    function loop(now) {
      raf = requestAnimationFrame(loop);
      // ease pupil toward target
      state.current.x += (target.current.x - state.current.x) * 0.12;
      state.current.y += (target.current.y - state.current.y) * 0.12;
      // blink
      if (blink && !RM) {
        if (lidDir === 0 && now > blinkT) { lidDir = 1; }
        if (lidDir === 1) { lidV += 0.18; if (lidV >= 1) lidDir = -1; }
        else if (lidDir === -1) { lidV -= 0.18; if (lidV <= 0) { lidV = 0; lidDir = 0; blinkT = now + 2200 + Math.random()*2600; } }
      }
      draw(state.current.x, state.current.y, lidV);
      if (RM) cancelAnimationFrame(raf);
    }
    raf = requestAnimationFrame(loop);

    let onMove = null;
    if (watch && !RM) {
      onMove = (e) => { const r = (wrapRef.current||cv).getBoundingClientRect(); const cx=r.left+r.width/2, cy=r.top+r.height/2;
        target.current.x = Math.max(-1, Math.min(1, (e.clientX-cx)/(window.innerWidth/2)));
        target.current.y = Math.max(-1, Math.min(1, (e.clientY-cy)/(window.innerHeight/2))); };
      window.addEventListener('mousemove', onMove);
    }
    return () => { cancelAnimationFrame(raf); if (onMove) window.removeEventListener('mousemove', onMove); };
  }, [size, accent, watch, blink]);

  return (
    <span ref={wrapRef} style={{ display: 'inline-block', lineHeight: 0, ...style }} {...rest}>
      <canvas ref={ref} style={{ width: size, height: Math.round(size * 0.62), imageRendering: 'pixelated' }} />
    </span>
  );
}
