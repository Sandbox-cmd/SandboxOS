---
name: sandboxos-design
description: Use this skill to generate well-branded interfaces and assets for SandboxOS — a bootleg, rebel "maker's operating system" — for production or throwaway prototypes/mocks. Contains the design guidelines, colors, type, fonts, the dither + character engines, and the UI-kit components for prototyping.
user-invocable: true
---

# SandboxOS Design

Read `readme.md` first — it holds the full guide (the locked thesis, content fundamentals, visual foundations, iconography, and the file manifest). Then explore the other files.

**The one-line soul:** a hand-assembled, *unlicensed* machine that's yours. **The base is mono** (ink on signal-white, dithered, dense); **color is earned** (stickers, status, the character, motion); **the dither is the material** everything emerges from; **the rebel runs the UI** (woven in, never a hero); **3D = ownership** (cartridges, coins); **provenance = identity** (serials, © NOBODY). Voice: lowercase UI, UPPERCASE SLAPS, talks back, **no emoji**, positive-rebel only (build · own · weird · free).

## How to use
- **Visual artifacts** (slides, mocks, throwaway prototypes): copy assets/tokens out and write static HTML. Link `styles.css`; reach for the CSS custom properties in `tokens/`. Reuse the dither + character canvas engines from `north-star-v3.html` / `character-v2.html` (they're self-contained). Build with the registers (teletext / error-screen / riso / sticker-wall) as earned-color skins.
- **Production code**: read the rules here to become an expert; mount the React components from `window.SandboxOSDesignSystem_4526c4` (`SlapButton`, `Window`, `Dialog`, `Field`, `Toast`, `Loader`, `FaceToggle`, `Sticker`, `Barcode`, `Cartridge`). See the `@dsCard` HTML in each `components/<group>/` for usage.

## Defaults to honor
- Mono first; one earned accent per context; **supercolor (rainbow) is cartridge-only; magenta is the character's signal.**
- Hard 0px corners, 2px die-cut borders, hard offset shadows, snappy mechanical motion (press = slap-down). No soft blur shadows, no gradient-slop, no emoji.
- Numbering brutalist (`001/002`), serials (`982-V7`), `© NOBODY`. "THANK YOU FOR USING."

If invoked without guidance, ask what they want to build, ask a few sharp questions, then act as an expert SandboxOS designer — output HTML artifacts *or* production code as needed.
