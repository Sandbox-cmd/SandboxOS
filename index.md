# the list

everything on this shelf, row by row. each entry comes from the thing's own
card — `BUILD.md` for a build, `APP.md` plus the `index.json` pin for an app.
if a checksum here ever disagrees with the card, the card wins and this list
owes a fix.

your sandbox recomputes these before anything lands, so you never have to
take this page's word for it:

```
sandbox fetch --from ./SandboxOS NAME     # checks the bytes, then asks for your keystroke
```

## builds

a build is a card plus exactly one payload. `sandbox fetch` verifies the
payload against the card before your keystroke, and marks what lands
`origin: external`.

### [human](builds/human/)

the language pack, as a skill. five tones — work, conversation, copy, artist,
and michael the woodshop Canadian — every one of them authored on a single
framework of six validated dimensions: word stock, pace, fillers, assumed
context, opinion and certainty, relationship. `references/` carries what the
tones are built on: the framework, the copy canon (26 ranked sources, 53
rules that survived adversarial verification), the artist canon, 50 verified
research findings with sources, and the tells.

```
kept       2026-07-25
payload    human/ (11 files)
sha256     3d6333ad75b223628b6d16370355238664f589edbf5e4351384d454a34564d84
```

drop it in your skills folder as `human/`, or keep it inside one project.

### [voices](builds/voices/)

the same material in a different shape: five voices delivered as Claude Code
output styles rather than a skill. switch one on with `/output-style`, or
drop a single voice into a project's `.claude/output-styles` so it travels
with the repo.

```
kept       2026-07-25
payload    voices/ (11 files)
sha256     3f24435f5a0ecd6cf7438388b0ec3424161c2b453db74d3adc284d76db7e6df0
```

human is a skill you add; voices is a style you switch on. same tones, same
references, same research. take whichever fits how you work.

### [michael](builds/michael/)

michael, the woodshop. a Claude terminal that designs 3d-printable parts and
drives your live Blender. inside: `Michael.command` to open him, the app, a
mug as the example project, `michael-cartridge.html` (a one-page look at how
he thinks), and `michael.png` for the icon. git strips icons, so re-apply the
face after you clone.

```
kept       2026-07-22
payload    michael/ (21 files)
sha256     9ffcc88a146745ff2de1ea04f56159aa05dfae69d76566d4fea17cae97a10251
```

## apps

an app declares in its manifest exactly what it places, and places nothing
outside its own room. `index.json` pins each one by a hash over its whole
directory; install recomputes that hash before calling anything official.

### [commerceos](apps/commerceos/) 1.0.0

a template for running your own store. install it, register your store under
`stores/`, and the system is yours — it ships with nobody's catalog,
credentials, or numbers. mechanism, specs, execution packs, and 551 checks of
its own; 48 of those skip on purpose, each one naming a file you have not
written yet. needs `uv` (`brew install uv`).

```
version    1.0.0
min-core   8.1.0
places     208 files, all under apps/commerceos/
sha256     6b0044182dfb29240566b2b8b6aa74c347335eef84ddda51d22c82337a894f74
```

```
sandbox app install commerceos --catalog ./SandboxOS
```

## what was left out

what a thing does not ship sits on its own card. commerceos ships without the
owner's stores, data, or brand file — the owner pulled `spec/frames/brand.md`
before sharing and the hash was recomputed after. michael ships without the
owner's api key or personal projects.

## what used to be here

`carts/` held commerceos, human, and michael in the shape an older version of
Sandbox OS used, with their own `CART.md` cards and an older hashing. it was
removed on 2026-08-01: two of the three were byte-identical to what `builds/`
already carries, the third was a superseded version of the language pack, and
the current sandbox could not read any of it. it stays in this
repo's git history if you ever want to look.

`builds/commerceos` went the same day. commerceos ships as an app now — one
shape, with a manifest that declares what it places, its own checks, and a
removal that takes back exactly what install put down.
