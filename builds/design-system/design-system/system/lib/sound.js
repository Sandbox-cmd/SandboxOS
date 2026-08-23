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
    let ac = null, hum = null, on = false;
    const ctx = () => (ac || (ac = new (window.AudioContext || window.webkitAudioContext)()));
    function env(o, g, t0, dur, peak) {
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.exponentialRampToValueAtTime(peak, t0 + 0.008);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      o.start(t0); o.stop(t0 + dur + 0.02);
    }
    function beep(freq, dur, type, peak, when) {
      if (!on) return; const c = ctx(); const t0 = when || c.currentTime;
      const o = c.createOscillator(), g = c.createGain();
      o.type = type || 'square'; o.frequency.value = freq;
      o.connect(g); g.connect(c.destination); env(o, g, t0, dur, peak || 0.07);
    }
    function startHum() {
      if (!on || hum) return; const c = ctx();
      hum = c.createOscillator(); const hg = c.createGain();
      hum.type = 'sawtooth'; hum.frequency.value = 58;
      const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 130;
      hg.gain.value = 0.012; hum.connect(lp); lp.connect(hg); hg.connect(c.destination); hum.start();
    }
    function stopHum() { if (hum) { try { hum.stop(); } catch (e) {} hum = null; } }
    return {
      get enabled() { return on; },
      enable(v) { on = !!v; if (on) { ctx().resume && ctx().resume(); startHum(); } else stopHum(); },
      toggle() { this.enable(!on); return on; },
      click() { beep(820 + Math.random() * 120, 0.05, 'square', 0.05); },
      key()   { beep(1180, 0.03, 'square', 0.03); },
      boot()  { if (!on) return; const c = ctx(), b = c.currentTime; [294, 392, 523, 698].forEach((f, i) => beep(f, 0.18, 'square', 0.06, b + i * 0.11)); beep(880, 0.4, 'sine', 0.04, b + 0.46); },
      install(){ if (!on) return; const c = ctx(), t0 = c.currentTime; const o = c.createOscillator(), g = c.createGain(); o.type = 'square'; o.frequency.setValueAtTime(330, t0); o.frequency.exponentialRampToValueAtTime(990, t0 + 0.16); o.connect(g); g.connect(c.destination); env(o, g, t0, 0.2, 0.06); },
      slap()  { beep(180, 0.06, 'square', 0.07); },
      error() { beep(130, 0.24, 'square', 0.08); },
      destroy(){ stopHum(); if (ac) ac.close(); },
    };
  }
  window.SandboxSound = { create };
})();
