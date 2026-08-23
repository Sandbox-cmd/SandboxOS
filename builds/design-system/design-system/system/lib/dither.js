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

  function sampleSource({ src, text, cols, rows, font }, cb) {
    const c = document.createElement('canvas'); c.width = cols; c.height = rows;
    const g = c.getContext('2d');
    const finish = () => {
      const d = g.getImageData(0, 0, cols, rows).data;
      const lum = new Float32Array(cols * rows);
      for (let i = 0; i < cols * rows; i++) lum[i] = (d[i * 4 + 3] / 255) * ((0.299 * d[i*4] + 0.587 * d[i*4+1] + 0.114 * d[i*4+2]) / 255);
      cb(lum);
    };
    if (src) {
      const im = new Image(); im.crossOrigin = 'anonymous';
      im.onload = () => { const s = Math.min(cols / im.width, rows / im.height) * 0.92; const w = im.width * s, h = im.height * s; g.drawImage(im, (cols - w) / 2, (rows - h) / 2, w, h); finish(); };
      im.onerror = finish; im.src = src;
    } else {
      g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.font = font || ('900 ' + Math.floor(rows * 0.7) + "px Archivo, Arial, sans-serif");
      g.fillText(String(text || ''), cols / 2, rows / 2); finish();
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
    let W, H, cols, rows, lum = null, raf = 0, dead = false;
    let phase = 'in', t0 = performance.now();
    const rgb = (hex) => { const n = parseInt(hex.replace('#',''), 16); return [n>>16 & 255, n>>8 & 255, n & 255]; };
    const C = rgb(color), AC = accent ? rgb(accent) : null;

    function resize() {
      W = canvas.clientWidth || canvas.width; H = canvas.clientHeight || canvas.height;
      canvas.width = W; canvas.height = H; ctx.imageSmoothingEnabled = false;
      cols = Math.max(2, Math.ceil(W / cell)); rows = Math.max(2, Math.ceil(H / cell));
      sampleSource({ src: opts.src, text: opts.text, cols, rows, font: opts.font }, (l) => { lum = l; });
    }

    function frame(now) {
      if (dead) return;
      raf = requestAnimationFrame(frame);
      if (!lum) return;
      const off = document.createElement('canvas'); off.width = cols; off.height = rows;
      const octx = off.getContext('2d'); const img = octx.createImageData(cols, rows); const d = img.data;
      let prog;
      const dt = now - t0;
      if (RM) prog = 1;
      else if (phase === 'in') { prog = Math.min(1, dt / 700); if (prog >= 1) { phase = 'hold'; t0 = now; } }
      else if (phase === 'hold') { prog = 1; if (dt > hold) { if (loop) { phase = 'out'; t0 = now; } } }
      else { prog = Math.max(0, 1 - dt / 600); if (prog <= 0) { phase = 'in'; t0 = now; } }
      const reveal = phase === 'in' ? prog : 1; // scanline sweep top→bottom on entrance
      const shimmer = phase === 'hold' && !RM ? (0.85 + 0.15 * Math.sin(now / 220)) : 1;
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const i = y * cols + x;
          let v = lum[i] * shimmer;
          if (scanline && phase === 'in' && (y / rows) > reveal) v = 0; // not yet revealed
          if (phase === 'out') v *= prog;
          const thr = (((x * 7 + y * 13) % 16) + 0.5) / 16; // ordered-ish
          if (v > thr) {
            const col = (AC && lum[i] > 0.62 && ((x + y) & 3) === 0) ? AC : C;
            d[i*4] = col[0]; d[i*4+1] = col[1]; d[i*4+2] = col[2]; d[i*4+3] = 255;
          }
        }
      }
      octx.putImageData(img, 0, 0);
      ctx.clearRect(0, 0, W, H); ctx.drawImage(off, 0, 0, W, H);
      // acid scanline line on entrance
      if (scanline && phase === 'in' && !RM) {
        ctx.fillStyle = accent || color; ctx.globalAlpha = 0.5;
        ctx.fillRect(0, reveal * H - 2, W, 2); ctx.globalAlpha = 1;
      }
    }
    const onR = () => resize();
    resize(); window.addEventListener('resize', onR); raf = requestAnimationFrame(frame);
    return { destroy: () => { dead = true; cancelAnimationFrame(raf); window.removeEventListener('resize', onR); } };
  }
  window.SandboxDither = { coalesce };
})();
