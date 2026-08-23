# SandboxOS Website — UI Kit

The marketing/web design language for SandboxOS — the public face of the bootleg machine. Composes the same design-system components as the product, so web and app speak one language.

## `index.html` — the landing page
- **Nav** — mono wordmark + links + a `rebel` `SlapButton` ("get it").
- **Hero** — "you don't use it. you build on it." over the live **dither fabric**, with the **generated dithered character** portrait (silk Floyd–Steinberg + magenta eyes) and a terminal install command.
- **Ticker** — `BUILD IT · OWN IT · SHIP IT · …` marquee.
- **01 Who Builds Here** — the THEM // YOU builder-vs-norm manifesto.
- **02 Everything Is A Cartridge** — three 3D `Cartridge` modules (build / skill / persona).
- **03 What It Does** — mono feature cards in the machine's talk-back voice.
- **CTA** — "stop renting. start building." + download slaps.
- **Footer** — fastext color bar, serial, `Barcode`, © NOBODY.

## Web design language (the rules)
- Same mono base + earned color; the dither fabric is the page substrate (cursor lifts it).
- Display = Archivo 900 condensed slaps; body/data = JetBrains Mono; CRT = VT323.
- Sections are numbered (01/02/03); hard borders, 0px corners, slap buttons, no soft shadows, no emoji.
- The character appears once in the hero (woven in, not a stock illustration) — generated in code.
- Color earned: amber (build), magenta (her/rebel), supercolor (cartridges only), single-ink status.

## Components used
`SlapButton`, `Cartridge`, `Barcode` (from `window.SandboxOSDesignSystem_4526c4`) + the inline dither + character canvas engines.

> Extend with: `docs` (teletext-index register), `cartridge detail` (3D hero + provenance), `pricing` (cartridge packs). The landing establishes the language; these follow the same grid + token rules.
