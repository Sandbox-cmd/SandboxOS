# The Shelf — shared builds for Sandbox OS

saved builds people chose to share: each one a card plus one payload, with
a checksum the card itself carries. this repo is public; the checksums are
the trust, your keystroke is the gate.

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

## give a build

```
sandbox share NAME --to ./SandboxOS
```

the scrub runs first (nothing personal ships, git history never rides),
then the push is your own hand, always.

## the shapes on this shelf

- `builds/` — the current shape (BUILD.md + payload), what `sandbox fetch`
  reads.
- `carts/` — builds shared by the seventh body, kept as they were; their
  cards and checksums still hold. read them by hand or re-press them into
  the new shape.

if a checksum here ever disagrees with a card, the card wins and this
README owes a fix.
