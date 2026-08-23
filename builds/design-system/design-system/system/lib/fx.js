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
  const rnd = (a) => a[(Math.random() * a.length) | 0];

  function scramble(el, text, opts) {
    opts = opts || {}; text = text == null ? el.textContent : String(text);
    if (RM) { el.textContent = text; return Promise.resolve(); }
    const dur = opts.dur || 800, t0 = performance.now(), n = text.length;
    return new Promise((res) => {
      function tick(now) {
        const p = Math.min(1, (now - t0) / dur);
        let out = '';
        for (let i = 0; i < n; i++) {
          if (text[i] === ' ') { out += ' '; continue; }
          out += (p * n > i) ? text[i] : rnd(GLYPHS);
        }
        el.textContent = out;
        if (p < 1) requestAnimationFrame(tick); else { el.textContent = text; res(); }
      }
      requestAnimationFrame(tick);
    });
  }

  function glitch(el, opts) {
    if (RM) return;
    opts = opts || {}; const dur = opts.dur || 420;
    el.style.willChange = 'transform, filter';
    const t0 = performance.now(), base = el.style.textShadow || '';
    function tick(now) {
      const p = (now - t0) / dur;
      if (p >= 1) { el.style.transform = ''; el.style.textShadow = base; el.style.clipPath = ''; el.style.willChange = ''; return; }
      const j = (1 - p) * 5;
      el.style.transform = `translate(${(Math.random() - 0.5) * j}px,${(Math.random() - 0.5) * j}px)`;
      el.style.textShadow = `${(Math.random() - 0.5) * j}px 0 var(--magenta), ${(Math.random() - 0.5) * -j}px 0 var(--cyan)`;
      if (Math.random() < 0.5) { const y = Math.random() * 100; el.style.clipPath = `polygon(0 ${y}%,100% ${y}%,100% ${y + 6}%,0 ${y + 6}%)`; setTimeout(() => el.style.clipPath = '', 40); }
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  function reveal(sel) {
    const els = typeof sel === 'string' ? [].slice.call(document.querySelectorAll(sel)) : (sel.length ? [].slice.call(sel) : [sel]);
    if (RM) { els.forEach(e => { e.style.opacity = 1; e.style.transform = 'none'; e.style.filter = 'none'; }); return; }
    els.forEach(e => { e.style.opacity = '0'; e.style.transform = 'translateY(14px)'; e.style.filter = 'blur(0) contrast(3) brightness(0.4)'; e.style.transition = 'opacity .5s, transform .55s var(--ease-out, cubic-bezier(.2,.8,.2,1)), filter .6s'; });
    const io = new IntersectionObserver((ents) => {
      ents.forEach(en => { if (en.isIntersecting) { const e = en.target; e.style.opacity = '1'; e.style.transform = 'none'; e.style.filter = 'none'; io.unobserve(e); } });
    }, { threshold: 0.18 });
    els.forEach(e => io.observe(e));
  }

  function magnetic(el, opts) {
    if (RM || TOUCH) return; const s = (opts && opts.strength) || 0.3;
    el.style.transition = 'transform .18s var(--ease-out, cubic-bezier(.2,.8,.2,1))';
    el.addEventListener('pointermove', (e) => { const r = el.getBoundingClientRect(); el.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * s}px,${(e.clientY - r.top - r.height / 2) * s}px)`; });
    el.addEventListener('pointerleave', () => { el.style.transform = ''; });
  }

  function tilt(el, opts) {
    if (RM) return; const max = (opts && opts.max) || 12;
    el.style.transformStyle = 'preserve-3d'; el.style.transition = 'transform .15s ease-out';
    const set = (px, py) => { el.style.transform = `perspective(700px) rotateY(${px * max}deg) rotateX(${-py * max}deg)`; };
    if (TOUCH && window.DeviceOrientationEvent) {
      window.addEventListener('deviceorientation', (e) => { set(Math.max(-1, Math.min(1, (e.gamma || 0) / 30)), Math.max(-1, Math.min(1, ((e.beta || 0) - 45) / 30))); });
    } else {
      el.addEventListener('pointermove', (e) => { const r = el.getBoundingClientRect(); set((e.clientX - r.left) / r.width - 0.5, (e.clientY - r.top) / r.height - 0.5); });
      el.addEventListener('pointerleave', () => { el.style.transform = ''; });
    }
  }

  function peel(el) {
    el.style.transition = 'transform .2s var(--ease-snap, cubic-bezier(.6,0,.2,1)), box-shadow .2s';
    el.style.transformOrigin = 'top right';
    const on = () => { if (RM) return; el.style.transform = 'rotate(2deg) translateY(-2px)'; el.style.boxShadow = '0 0 0 3px var(--signal), 6px 8px 0 rgba(0,0,0,.55)'; };
    const off = () => { el.style.transform = ''; el.style.boxShadow = ''; };
    el.addEventListener('pointerenter', on); el.addEventListener('pointerleave', off);
    el.addEventListener('pointerdown', on); el.addEventListener('pointerup', off);
  }

  function ripple(el) {
    el.style.position = el.style.position || 'relative'; el.style.overflow = 'hidden';
    const fire = (e) => {
      if (RM) return; const r = el.getBoundingClientRect();
      const d = document.createElement('span'); const size = Math.max(r.width, r.height);
      const x = ((e.touches ? e.touches[0].clientX : e.clientX) - r.left), y = ((e.touches ? e.touches[0].clientY : e.clientY) - r.top);
      d.style.cssText = `position:absolute;left:${x - size / 2}px;top:${y - size / 2}px;width:${size}px;height:${size}px;border-radius:50%;background:var(--accent-live,var(--signal));opacity:.35;transform:scale(0);pointer-events:none;transition:transform .45s ease-out,opacity .6s;`;
      el.appendChild(d); requestAnimationFrame(() => { d.style.transform = 'scale(1)'; d.style.opacity = '0'; });
      setTimeout(() => d.remove(), 650);
    };
    el.addEventListener('pointerdown', fire);
  }

  function marquee(el) {
    if (el.dataset.fxMarquee) return; el.dataset.fxMarquee = '1';
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

  window.SandboxFX = { scramble, glitch, reveal, magnetic, tilt, peel, ripple, marquee, autoAll, RM, TOUCH };
})();
