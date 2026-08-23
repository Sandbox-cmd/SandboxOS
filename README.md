![THE SHELF](assets/title.svg)

# the shelf — shared builds and apps for Sandbox OS

what people chose to share: saved builds (one folder of files, with a card in
front of it carrying the checksum) and installable apps (each one declaring,
up front, exactly what it puts on your disk). this repo is public. the
checksum is there so you can check a thing instead of trusting us; your
keystroke is what lands it.

the system that reads this shelf lives at
https://github.com/Sandbox-cmd/SandboxOS-core — clone it, `./sandbox init`,
and you have your own workshop.

## take a build

```
git clone https://github.com/Sandbox-cmd/SandboxOS
sandbox fetch --from ./SandboxOS            # list what's here
sandbox fetch --from ./SandboxOS NAME       # pull one; checked first, then your keystroke decides
```

fetch checks the bytes against the card first, and only then asks for your
key. what lands on your shelf is marked origin: external — where a thing came
from never washes off.

## install an app

```
sandbox app install NAME --catalog ./SandboxOS
```

index.json pins every app by a hash over its whole directory; your copy
recomputes that hash and refuses the app if it disagrees. install shows the
manifest and runs the app's own checks; `sandbox app remove NAME` takes out
exactly what install placed.

## give something

```
sandbox share NAME --to ./SandboxOS
```

a scrub runs first — it looks for private data and refuses rather than warns,
and git history never comes along — then the push is your own hand, always.
[CONTRIBUTING.md](CONTRIBUTING.md) has the whole path: what the scrub
refuses, how to shape an app, and how to pin it in the catalog.

## what's here

the full list with every checksum is in [index.md](index.md).

| shape | name | what it is |
|---|---|---|
| app | commerceos | a template for running your own store — install it, register your store, and the system is yours. it ships with nobody's catalog, credentials, or numbers. 551 checks of its own (needs `uv`: brew install uv) |
| build | human | the language pack as a skill — five tones on one framework (superseded by voices' one voice; kept for its research) |
| build | voices | plain hands — one Claude Code output style for every reader, the five voices consolidated |
| build | michael | the woodshop — a Claude terminal that designs 3d-printable parts and drives your live Blender |

if a card and this table ever disagree, the card wins and this README owes a
fix.
