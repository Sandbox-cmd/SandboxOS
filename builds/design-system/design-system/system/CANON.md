# CANON — SandboxOS Design System

> The single source of truth. One page. If something here conflicts with anything
> else in the repo, **this wins.** Built foundation-first, in this order.

---

## The one line
A local, hand-assembled **bootleg operating system for makers.** Not an assistant — a machine you *build on*: notice a busted default, build the clean version, ship it. Mono and dense for competence; sticker-bombed, dithered, and character-warm for soul. Loud at every level.

## Five laws (non-negotiable)
1. **The base is mono.** ~90% of every surface is ink-on-void, dithered, dense. No color is required to use the product.
2. **Color is earned — one live accent per view.** Amber = active/build · magenta = the rebel ("her") · green = ok · cyan = link · supercolor (rainbow) = **cartridges only**. Status hues are single-ink, never fills. If two things shout, neither does.
3. **The dither is the material — kept quiet.** A subtle living grain everything sits on; it can develop/dissolve for reveals, but it is **seasoning, never a light show.** Dim ink, low motion. The bootleg chrome (windows, stickers, teletext) is always the main event.
4. **3D = ownership.** Dimension is reserved for *objects you own* — cartridges, boot-coins. The rest of the UI is flat and brutal.
5. **Voice: positive rebel.** Lowercase UI, UPPERCASE SLAPS, talks back, **no emoji**, build·own·weird·free. Never doom/hate.
6. **Bootleg first, never mystical.** The soul is a hand-made pirate OS — stickerbomb, teletext, talk-back error boxes, "THANK YOU FOR USING." The character (an ownable dithered **eye/gaze**) and moods are *seasoning*: the eye is a small, curious detail keeping an eye on your build, never a hero; moods are a quiet manual knob, never an idle performance.

## Build order (foundation-first — how it was assembled, and how to extend it)
```
1. tokens/        →  styles.css imports every token + font file
2. lib/           →  substrate · dither · sound  (the engines; load via <script src>)
3. components/    →  consume tokens + lib ONLY. never re-implement them.
4. ui_kits/       →  compose components. never re-implement them.
5. templates/     →  one-click starting points (.dc.html, via ds-base.js)
```

## Foundation-first rules (the discipline)
- **Every component references tokens** (`var(--…)`), never raw hex — *except* pure-canvas
  components (GhostEye), which must resolve via `getComputedStyle` or fall back to a literal.
- **Physical-object material** comes from the `--hw-*` token group (shell/ridge/label), so even
  the 3D objects are systematic.
- **Components never re-implement the dither or sound** — they use `lib/`.
- **UI kits never re-implement a component** — they import from the namespace.
- **Every animation honours `prefers-reduced-motion`** (end-state shown, motion skipped).

## The character — settled
An ownable **1-bit dithered gaze** (`GhostEye`) is the always-on mascot — "always around,
never owned." It deliberately avoids the uncanny human-bust. The full seductive anime-rebel
figure is reserved for hero/dossier slots and is **supplied as real (licensed/commissioned)
art run through the dither pipeline** — never traced from copyrighted refs, never AI-faked into
the system. *(Parked by owner; pipeline + slots are ready.)*

## Namespace
`window.SandboxOSDesignSystem_4526c4` — e.g. `const { Window, Cartridge, GhostEye } = window.SandboxOSDesignSystem_4526c4`.

## Known, owned gaps (not drift — explicit)
- The hero character needs real art (above).
- 3D objects flatten oddly in html-to-image captures (a screenshot artifact); they render correctly live.

*v2 (2026-06-20): fonts are now self-hosted `.woff2` + `@font-face` — no CDN, fully offline. Forms rebuilt a11y-first on real native inputs. The workshop primitives (`components/data/` + `components/nav/`) and the accessibility + voice guidelines are new. Contrast contract documented in `guidelines/accessibility.html`.*

---
*build it · own it · ship it · stay weird — © NOBODY, copy it.*
