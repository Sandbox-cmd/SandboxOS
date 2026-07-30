# The Shelf — shared builds and apps for Sandbox OS

what people chose to share: saved builds (a card plus one payload, checksum
on the card) and installable apps (a manifest that declares exactly what it
places). this repo is public; the checksums are the trust, your keystroke
is the gate.

the system that reads this shelf lives at
https://github.com/Sandbox-cmd/SandboxOS-core — clone it, `./sandbox init`,
and you have your own workshop.

## take a build

```
git clone https://github.com/Sandbox-cmd/SandboxOS
sandbox fetch --from ./SandboxOS            # list what's here
sandbox fetch --from ./SandboxOS NAME       # pull one, hash-checked, your k decides
```

fetch verifies the bytes against the card BEFORE asking your key, and what
lands on your shelf is marked origin: external — where a thing came from
never washes off.

## install an app

```
sandbox app install NAME --catalog ./SandboxOS
```

index.json pins every app by a hash over its whole directory; your sandbox
recomputes it before calling anything official. install shows the manifest
and runs the app's own checks; `sandbox app remove NAME` takes out exactly
what install placed.

## give something

```
sandbox share NAME --to ./SandboxOS
```

the scrub runs first (nothing personal ships, git history never rides),
then the push is your own hand, always.

## what's here

| shape | name | what it is |
|---|---|---|
| app | commerceos | a commerce operating system — mechanism, specs, packs, its own test suite; bring your own store data (needs `uv`: brew install uv) |
| build | commerceos | the same, as a drop-in build |
| build | human | the language pack — one skill, four tones, research aboard |
| build | michael | the woodshop — a claude terminal that designs 3d-printable parts and drives your live blender |

`carts/` holds the same three as the seventh body shared them — kept as
they were, cards and history intact. the `builds/` cards carry the same
bytes re-pinned under the current hashing; if a card and this table ever
disagree, the card wins and this README owes a fix.
