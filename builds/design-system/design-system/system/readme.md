# SandboxOS — Design System

> a bootleg operating system **for makers**. local, hand-assembled, yours. **nobody's tool.**
> *not an ai. you don't use it — you build on it.*
>
> **STATUS: v2 — a bootleg OS for makers (2026-06-20).** Loud at every level: notice a busted default, build the clean version, ship it. NEW in v2 — the workshop primitives (`Table · List · Stat · KeyValue · CodeBlock · Nav · Menu · Pagination`), forms rebuilt **a11y-first** on real native inputs, a documented **contrast contract** + **voice** guideline, and **fully self-hosted fonts** (no CDN, works offline). See `CANON.md` for the non-negotiable laws. Parked (need owner): the hero character art (licensed, run through the dither pipeline).

SandboxOS is a **rebel, anti-corporate, maker's machine** rendered as a **pirate / bootleg retro-OS**. It remembers what matters, heckles your worst ideas before you ship them, keeps what it learned, and **expands through cartridges** (shareable, plug-n-play builds). This design system is the visual + interaction language for that machine.

The compiler exposes everything under the global namespace **`window.SandboxOSDesignSystem_4526c4`** (used in `@dsCard` HTML to mount components). Consumers link the single entry stylesheet **`styles.css`**.

---

## The locked direction (the thesis)

1. **The base is mono.** Black ink on signal-white, dithered and dense. The structural UI is 1-bit — legible, calm, yours. *No color is required to use the product.*
2. **Color is earned.** Stickers, the character, status, and motion earn their color on top. One accent per context. **Magenta = "her" signal. Supercolor (rainbow) is reserved for cartridges only.**
3. **The dither is the material.** A living animated dither *substrate* everything emerges from — boot, loaders, the character, reveals. Move the cursor and it lifts; things pop out from under it.
4. **The rebel runs the UI.** A generative, dithered anime-rebel character woven *into* the interface (cursor, toggle, mascot, slaps, easter eggs) — the **spirit of seduction to build**, drawing you toward making. Personality, never a static hero.
5. **3D = ownership.** The UI is flat and brutal; dimension is reserved for *objects you own* — cartridges, boot-coins, save-disks, minted scar-coins.
6. **Provenance = identity.** Serial / QR / © NOBODY everywhere. Everything is owned, traceable, yours.
7. **Builder vs the norm.** This is for the maker who'd rather **own the workshop than rent the assistant** — and wear the weirdness as a badge.

---

## Sources (for the reader — you may not have access)

- **`SandboxOS2/`** — the product codebase (a personal OS that runs on Claude Code; `.mind/` canon, learning loop). *Provided for context only — the design was drawn purely from the moodboards, not this folder. Especially ignore `studio/`.*
- **Mood reference (Pinterest boards)** — captured to `uploads/Screenshot *.png` (+ `uploads/web-capture-*.json` raw DOM scrapes). Boards covered: astral/VHS/cassette-futurism, FLYERWRK stickerbomb, retro-OS UI kits, 1-bit dither, teletext/CEEFAX, anime-rebel character, dithered portraits.
- **Competitor benchmark** — `hermes-agent.nousresearch.com` (Nous). Studied for *why* it works (sovereign/open-source credibility via restraint), **not** copied — SandboxOS deliberately diverges into the hand-made / stickerbomb / character-warm register that the clean "tactical brutalist AI SaaS" lane lacks.

---

## CONTENT FUNDAMENTALS — how we write

- **Voice:** rebel, punk, defiant — but **warm and constructive** (positive rebellion: *build · own · weird · free* — never sin / hate / doom).
- **Casing:** **lowercase for UI** (calm machine), **UPPERCASE FOR SLAPS** (rebel shouts). e.g. body `run it yourself`, sticker `NOBODY'S TOOL`.
- **Person:** the machine talks back in *its own* first person — *"i'm the thing you built"*, *"not your assistant"*. Not servile; co-signs your work.
- **No emoji.** Ever. Unicode glyphs/kaomoji (`▸ ✶ ☠ つづく ⌐■_■`) and ASCII are the texture instead.
- **Arabic** as *rare* calligraphic spice / maker's-mark seal — never a theme.
- **Recurring cues (sprinkle as slaps/asides):** `NOT AN AI · JUST VIBES · STAY WEIRD · NOBODY'S TOOL · RUN IT YOURSELF · NO BAD VIBES · BUILD IT · OWN IT · SHIP IT · THANK YOU FOR USING`.
- **Numbering:** brutalist (`001/002`), serials (`982-V7`), editions (`001/500`), `© NOBODY`.
- **Error-as-celebration:** the OS rewards weirdness and breakage instead of apologizing. *"no smile detected. that's allowed here."*

---

**Foundation engines** — `lib/` (load via `<script src>` on HTML surfaces)
- `lib/substrate.js` (`window.SandboxSubstrate`) — the living 1-bit dither field everything sits on. Three **moods** (JAILBROKEN default · WORKBENCH · AFTER-HOURS) with a Bayer-ordered dissolve between them, cursor `poke()` ripple, `surface(word)` bloom, live knobs. Replaces all the old inline-dither copies.
- `lib/dither.js` (`window.SandboxDither`) — coalesce any image/text out of halftone particles (assemble → hold → dissolve), the "develops out of the fabric" move.
- `lib/sound.js` (`window.SandboxSound`) — a tiny WebAudio synth (boot · click · key · install · slap · error + a 60Hz hum). OFF by default; enable on a user gesture.
- `lib/fx.js` (`window.SandboxFX`) — the experiential/motion layer: `scramble`, `glitch` (RGB-split), `reveal` (dither-rise on scroll), `magnetic`, `tilt` (pointer + device gyro), `peel`, `ripple`, `marquee`. Auto-wire via `[data-fx]` attributes; pointer + touch + gyro aware.
- All four honour `prefers-reduced-motion`.

## VISUAL FOUNDATIONS

- **Color:** deep CRT black (`--crt-950`) + signal/paper cream (`--signal`/`--paper`) lead. Phosphor accents — amber (active/brand), green (ok/built), cyan (link/share), magenta (rebel/her), blue (broadcast/error-screen). Slap loud — hazard yellow, alert red. **Supercolor** rainbow gradient is cartridge-only. See `tokens/colors.css`.
- **Type:** `Archivo` (display/slaps, 900), `Anton` (poster condensed), `JetBrains Mono` (UI/data/serials), `VT323` (CRT/teletext/boot), `Silkscreen` (pixel labels). Two voices: lowercase UI vs UPPERCASE SLAPS. See `tokens/typography.css`. *(All Google Fonts — these are the chosen brand faces, not substitutions; swap in licensed binaries if desired.)*
- **Dither:** the signature material. Animated Bayer/blue-noise + Floyd–Steinberg error-diffusion. Tunable **per surface** — chunky for loud slaps, **silky (cell-1 blue-noise)** for ambient fabric, error-diffusion for the character. `--fx-*` tokens; engine prototyped in `north-star-v3.html` / `character-v2.html`.
- **Borders / corners:** hard. 2px die-cut borders, **0px radius** (brutalist) — round only for seals/pills and the few owned 3D objects.
- **Shadows:** hard offset (sticker slap `3px 3px 0`), white die-cut **halo** for stickers, phosphor **glow** for active CRT text. No soft blur drop-shadows.
- **Motion:** mechanical + snappy (`--ease-snap`), no soft bounce. Press = slap-DOWN (translate + lose shadow). Dither-reveals, type that "assembles", sticker corner-peel, the cartridge spin. `prefers-reduced-motion` respected.
- **Backgrounds:** the dither fabric (animated), scanlines, dotted engineering grid, hazard stripes, teletext color blocks. Warm analog grain over cold corporate gradients.
- **Registers (earned full-color skins, by job):** Teletext/CEEFAX (wayfinding), the blue Error-Screen (the one full takeover), Riso/photocopy (posters/physical), Sticker-wall (idle/celebration).

---

## ICONOGRAPHY

- **No icon-font dependency and no hand-drawn pictographic SVGs.** SandboxOS uses **typographic + glyph iconography**: monospace/CRT unicode marks (`▸ ▚ ✶ ◐ ✦ ☠ ↯ ⌐■_■`), brutalist numerals, and **the sticker system itself as iconography** (seals, bursts, hazard, barcode).
- **Provenance marks** — procedural `Barcode`, QR-style pixel grids, serials — act as the "system" icons.
- **The character** is the one illustrative element, and she is **generated in code** (dithered), not an icon set.
- **No emoji.** If a glyph is needed, prefer a CRT/pixel unicode mark or a sticker.

---

## INDEX / MANIFEST

**Foundations**
- `styles.css` — entry point (import list only)
- `tokens/` — `colors.css`, `typography.css`, `fonts.css`, `effects.css` (spacing/radii/shadow/motion/fx), `base.css`

**Components** (`window.SandboxOSDesignSystem_4526c4`)
- `components/core/` — `SlapButton`, `Window`, `Dialog`, `Field`, `Toast`, `Loader`, `FaceToggle`, `Avatar` (the character), `Tooltip`
- `components/forms/` — `Tabs`, `Checkbox`, `Radio`, `Select`, `Knob` (cassette dial), `Switch`
- `components/brand/` — `GhostEye` (the dithered gaze that watches your build come together — the mascot), `VHSHeadline` (kinetic poster voice)
- `components/stickers/` — `Sticker` (tag/pill/seal/burst/ribbon/price/stamp/callout), `Barcode`, `CharacterSlap` (the rebel's mood badges)
- `components/cartridge/` — `Cartridge` (3D build object), `BootCoin` (3D minted coin / scar-coin)

**Brand assets** — `assets/` — `wordmark.svg`, `mark.svg`, `sticker-*.svg`, `barcode.svg`, `arabic-seal.svg` (the rare Arabic maker's-mark, حُرّ). The character is generated at runtime, not a static file.

**Foundation & spec (the locked creative direction — archived in `explorations/`)**
- `explorations/north-star-v3.html` — **the system spec**: mono base · earned color · registers · dither substrate · builder-vs-norm · cartridge (+ `north-star-v1.html`, `north-star.html` = v2)
- `explorations/character-v2.html` — the generative dithered character (anatomy pass) + `character-over-shoulder.html`, `character-lab.html` (engine + dither ladder + packs + 3D extension)
- `explorations/explorations.html`, `explorations-2/3/4.html` — the full divergent direction studies (rounds 1–4)

**Guidelines / cards** — `guidelines/` — Type (display, body, mono, **VHS motion**), Colors (neutrals, accents), Spacing, Brand (live dither fabric, **riso/photocopy register**)

**UI kits** — `ui_kits/desktop/` (boot → workbench → shelf → terminal; + `gate.html`, `error.html`) · `ui_kits/website/` (landing + docs teletext + pricing packs + cartridge detail + `marketplace.html`) · `ui_kits/mobile/` (touch-native phone kit: boot · workbench · the wall) · `ui_kits/living-machine/` (the flagship)

**Templates** — `templates/landing/` (DC hero) · `templates/poster/` (stickerbomb + VHS + data-UI poster)

---

## ITERATION LOG

**v2 — consolidated comparative pass** (vs. the sibling *GHOSTLINE* solution to the same brief, + our own iteration map). Lessons adopted, adapted into our identity (never cloned):
- **Killed the inline-dither debt** → extracted `lib/substrate.js` + `lib/dither.js` as shared engines.
- **Added a sound layer** (`lib/sound.js`) — the "living machine" now breathes; OFF by default.
- **Resolved the character trap.** GHOSTLINE avoided the uncanny human-bust (the exact thing that kept reading "creepy" in ours) with an ownable **dithered gaze**. We adopted `GhostEye` as the *always-on mascot* and kept the seductive figure for hero/dossier slots via real art through the dither pipeline.
- **Componentised** the VHS headline (`VHSHeadline`) instead of per-page CSS; added `Knob` (cassette dial) + `Switch`.
- **Discipline:** the "one live accent per view" rule is now a foundation card; mono stays ~90%.
- **Moods:** the substrate carries JAILBROKEN / WORKBENCH / AFTER-HOURS as states of one machine (live in the desktop kit).
- **Motion spec** documented as a card; reduced-motion honoured across engines + animations.

**What we keep that's ours:** the **3D `Cartridge` + `BootCoin`** (dimension = ownership), the **magenta "her"** signal, the interactive desktop, `FaceToggle`, the talk-back voice.

**Still open (next):** self-host fonts for an offline bundle · port real character art into hero slots · optional WebGL substrate fallback.

---

*build it · own it · ship it · stay weird — © NOBODY, copy it.*
