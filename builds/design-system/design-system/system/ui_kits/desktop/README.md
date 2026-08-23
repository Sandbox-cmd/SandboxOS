# SandboxOS Desktop — UI Kit

The flagship product surface: the **bootleg workbench desktop**. A high-fidelity, interactive recreation that *composes the design-system components* — it does not re-implement them.

## `index.html` — the interactive desktop
A typical session, click-through:
1. **Boot** — the OS develops out of the dither fabric: `warming up the workbench… memory: the bugs you beat, kept… running local · just you and the machine… ready. nobody's tool.` and she wakes (`⌐■_■ i'm awake`).
2. **Workbench** — the desktop: an inverted-bar top chrome, **draggable** `Window` / `Dialog` panels (talk-back voice), the left **sticker** slaps, the **terminal** (`Field`) where you type a build and hit enter, the **focus** `FaceToggle` + `Loader` in the corner.
3. **Cartridge shelf** — three 3D `Cartridge` modules (build / skill / persona); **install** one and she fires a `Toast`.
4. Everything sits on the animated **dither fabric** (cursor lifts it) under a custom rebel cursor.

## Components used
`Window`, `Dialog`, `SlapButton`, `Sticker`, `Barcode`, `Cartridge`, `Toast`, `Loader`, `Field`, `FaceToggle` — all from `window.SandboxOSDesignSystem_4526c4`.

## Notes
- Mono base, color earned (stickers, toasts, cartridge spines, her magenta).
- The dither fabric + custom cursor are inline here; they should graduate into reusable `lib/` modules.
- This is a recreation/spec, not production code — interactions are faked (drag, install, terminal echo).
