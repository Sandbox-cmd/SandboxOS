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
  const BAYER = [
    [0,32,8,40,2,34,10,42],[48,16,56,24,50,18,58,26],
    [12,44,4,36,14,46,6,38],[60,28,52,20,62,30,54,22],
    [3,35,11,43,1,33,9,41],[51,19,59,27,49,17,57,25],
    [15,47,7,39,13,45,5,37],[63,31,55,23,61,29,53,21]
  ].map(r => r.map(v => (v + 0.5) / 64));
  const RM = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // SandboxOS moods — three states of one machine
  const MOODS = {
    // everyday bootleg: dim warm grain, rare amber spark
    jailbroken: { bg:[12,12,10],  ink:[66,63,53],  accent:[176,122,0],  accentAmt:0.035,
                  amp:0.10, speed:0.20, bloom:0.05, bloomCol:[176,122,0],  turb:0.06 },
    // focused maker mode: quietest, faint cool grain
    workbench:  { bg:[12,12,10],  ink:[56,60,52],  accent:[40,150,80],  accentAmt:0.025,
                  amp:0.06, speed:0.12, bloom:0.04, bloomCol:[40,150,80], turb:0.02 },
    // after dark: a touch of dim magenta in the grain — subtle, not mystical
    afterhours: { bg:[12,9,15],   ink:[70,60,68],  accent:[150,60,108], accentAmt:0.06,
                  amp:0.09, speed:0.11, bloom:0.08, bloomCol:[110,60,120], turb:0.04 },
  };

  function mount(canvas, opts) {
    opts = opts || {};
    const cell = opts.cell || 4;
    // Ambient field cadence. Painting the whole weave costs real milliseconds at
    // large/HiDPI sizes, so we cap the rAF: 60fps reads as smooth (24fps stepped);
    // higher would just burn budget the eye can't use. Default 30fps for calm
    // ambient consumers; a foreground hero wants 60.
    const fps = opts.fps || 30;
    const frameInterval = 1000 / fps;
    // sleepAtRest: once the field has fully settled (energy spent, no word/poke/
    // dissolve), stop the loop and hold the last frame. A still texture cannot
    // step or lag and burns zero idle CPU; interaction wakes it. Opt-in so the
    // ambient always-on consumers keep their continuous drift.
    const sleepAtRest = !!opts.sleepAtRest;
    const ctx = canvas.getContext('2d', { alpha: false });
    const off = document.createElement('canvas');
    const octx = off.getContext('2d');
    let cols = 0, rows = 0, img = null, W = 0, H = 0, raf = 0, dead = false, awake = false;
    let rect = { left: 0, top: 0 };
    let t = 0, lastPaint = performance.now();
    // energy: 1 = just poked (lively), decays to 0 = at rest (near-static drift).
    // The field only truly "lifts" on interaction; idle it barely breathes.
    let energy = 0; const IDLE = 0.12;
    let cur = opts.mood || 'jailbroken', from = cur, prog = 1;
    let knobs = { chaos: 0.5, scan: 0.5, vhs: 0.35 };
    let poke = { x: -1, y: -1, age: 1 };
    let word = null; // {grid:Float32Array, cols, rows, born}

    function resize() {
      W = canvas.clientWidth || canvas.width || window.innerWidth;
      H = canvas.clientHeight || canvas.height || window.innerHeight;
      canvas.width = W; canvas.height = H;
      cols = Math.max(2, Math.ceil(W / cell)); rows = Math.max(2, Math.ceil(H / cell));
      off.width = cols; off.height = rows;
      img = octx.createImageData(cols, rows);
      ctx.imageSmoothingEnabled = false;
      // cache the canvas origin so poke() maps pointer→field without a layout
      // read on every move (the pointer path stays write-only).
      const r = canvas.getBoundingClientRect(); rect.left = r.left; rect.top = r.top;
      if (word) word = bakeWord(word.text);
    }

    function bakeWord(text) {
      const c = document.createElement('canvas'); c.width = cols; c.height = rows;
      const g = c.getContext('2d');
      g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.font = '900 ' + Math.floor(rows * 0.42) + "px Archivo, Arial, sans-serif";
      g.fillText(text, cols / 2, rows / 2);
      const d = g.getImageData(0, 0, cols, rows).data;
      const grid = new Float32Array(cols * rows);
      for (let i = 0; i < cols * rows; i++) grid[i] = d[i * 4 + 3] / 255;
      return { text, grid, born: performance.now() };
    }

    function field(M, nx, ny, time, bx, by) {
      let v = 0.40
        + M.amp * Math.sin(nx * 6.0 + time * M.speed)
        + M.amp * Math.sin(ny * 5.0 - time * M.speed * 0.8)
        + M.amp * 0.7 * Math.sin((nx + ny) * 4.0 + time * M.speed * 1.3);
      if (M.turb) v += M.turb * 0.18 * Math.sin(nx * 23 + time * 2) * Math.sin(ny * 19 - time * 1.7);
      const dx = nx - bx, dy = ny - by;
      v += M.bloom * Math.max(0, 1 - Math.sqrt(dx * dx + dy * dy) * 1.6);
      return v;
    }

    // One paint. `dt` is real elapsed seconds since the last PAINTED frame.
    function render(dt, now) {
      // motion scale: at rest the weave barely drifts; a poke/word/mood lifts it.
      const live = IDLE + (1 - IDLE) * energy;
      if (!RM) t += dt * live;
      if (prog < 1) prog = Math.min(1, prog + dt / 0.9);
      const A = MOODS[from], Bm = MOODS[cur];
      const chaos = knobs.chaos, vhs = knobs.vhs;
      const bxA = 0.5 + 0.32 * Math.sin(t * 0.13), byA = 0.32 + 0.2 * Math.cos(t * 0.11);
      const bxB = 0.5 + 0.32 * Math.sin(t * 0.13 + 1), byB = 0.6 + 0.2 * Math.cos(t * 0.11 + 1);
      const tearRow = vhs > 0.05 ? Math.floor((Math.sin(t * 0.7) * 0.5 + 0.5) * rows) : -99;
      const tearAmt = vhs > 0.05 && Math.random() < 0.04 ? Math.floor(vhs * 6) : 0;
      let wf = 0, wg = null;
      if (word) { wf = Math.max(0, 1 - (now - word.born) / 2600); if (wf <= 0) word = null; else wg = word.grid; }
      const pokeLive = poke.age < 1;              // hoist the ripple gate out of the cell loop
      const invCols = 1 / cols, invRows = 1 / rows;

      const data = img.data;
      for (let cy = 0; cy < rows; cy++) {
        const brow = BAYER[cy & 7];
        const ny = cy * invRows;
        const rowBase = cy * cols;
        for (let cx = 0; cx < cols; cx++) {
          const useB = prog >= 1 ? true : (prog > brow[cx & 7]);
          const M = useB ? Bm : A;
          const nx = cx * invCols;
          const bx = useB ? bxB : bxA, by = useB ? byB : byA;
          let v = field(M, nx, ny, t, bx, by);
          if (chaos > 0.01) v += chaos * 0.12 * Math.sin(nx * 40 + t * 3) * Math.sin(ny * 36 - t * 2.3);
          if (pokeLive) {
            const pdx = nx - poke.x, pdy = ny - poke.y, pd = Math.sqrt(pdx * pdx + pdy * pdy);
            if (pd < 0.167) v += (1 - poke.age) * 0.3 * (1 - pd * 6) * Math.cos(pd * 40 - t * 8);
          }
          if (wg) v += wf * 0.95 * wg[rowBase + cx];
          const thr = brow[((cx + (tearAmt && cy > tearRow && cy < tearRow + 4 ? tearAmt : 0)) & 7)];
          const i = (rowBase + cx) * 4;
          let col;
          if (v > thr) {
            const acc = M.accentAmt;
            // only roll the accent die on bright cells — saves a Math.random per dim cell
            col = (acc > 0 && v > 0.6 && Math.random() < acc * (v - 0.6)) ? M.accent : M.ink;
          } else col = M.bg;
          data[i] = col[0]; data[i+1] = col[1]; data[i+2] = col[2]; data[i+3] = 255;
        }
      }
      octx.putImageData(img, 0, 0);
      ctx.drawImage(off, 0, 0, W, H);
      if (pokeLive) poke.age = Math.min(1, poke.age + dt / 0.6);
      if (!RM) energy = Math.max(0, energy - dt / 2.4);   // lively → rest over ~2.4s
    }

    // Fully at rest: energy spent, no dissolve, no live poke or word. The last
    // painted frame is the calm field — safe to hold and stop the loop.
    function settled() {
      return energy <= 0.002 && prog >= 1 && !word && poke.age >= 1;
    }

    // Time-gated loop: rAF ticks at display rate but we only PAINT at `fps`
    // (60fps reads smooth; 24 stepped). When sleepAtRest, we stop the loop the
    // moment the field settles and re-arm it on the next interaction.
    function frame(now) {
      if (dead) return;
      const gap = now - lastPaint;
      if (gap >= frameInterval) {
        lastPaint = now - (gap % frameInterval);       // keep cadence, avoid drift
        render(Math.min(0.05, gap / 1000), now);
        if (sleepAtRest && settled()) { awake = false; raf = 0; return; }  // hold last frame
      }
      raf = requestAnimationFrame(frame);
    }

    // Re-arm the loop after a sleep (interaction woke the field).
    function wake() {
      if (dead || RM || awake) return;
      awake = true;
      lastPaint = performance.now() - frameInterval;    // paint on the very next rAF
      raf = requestAnimationFrame(frame);
    }

    const onResize = () => { resize(); if (RM) render(0, performance.now()); else if (awake) { /* loop repaints */ } else wake(); };
    resize();
    window.addEventListener('resize', onResize);
    if (RM) {
      render(0, performance.now());                     // one calm static paint, no loop
    } else {
      awake = true;
      raf = requestAnimationFrame(frame);
    }

    return {
      setMood: (m) => { if (MOODS[m] && m !== cur) { from = cur; cur = m; prog = 0; energy = 1; wake(); } },
      mood: () => cur,
      set: (k) => { Object.assign(knobs, k); wake(); },
      poke: (px, py) => { poke = { x: (px - rect.left) / W, y: (py - rect.top) / H, age: 0 }; energy = 1; wake(); },
      surface: (text) => { word = bakeWord(String(text)); energy = 1; wake(); },
      destroy: () => { dead = true; cancelAnimationFrame(raf); window.removeEventListener('resize', onResize); },
      MOODS,
    };
  }
  window.SandboxSubstrate = { mount, MOODS };
})();
