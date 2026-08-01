# giving something to the shelf

this shelf is a hub, not a store. what lands here is what someone chose to
share, with a checksum on the front so the next person can check it instead
of trusting it. the tool does the packing; the push is always a human hand.

you need Sandbox OS to contribute — it is the thing that packs a build and
runs the scrub. it lives at
https://github.com/Sandbox-cmd/SandboxOS-core.

## a build

a build is a card (`BUILD.md`) plus exactly one payload. you never write the
card by hand — `share` writes it, hash and all.

```
git clone https://github.com/Sandbox-cmd/SandboxOS
sandbox share NAME --to ./SandboxOS
```

that stages `builds/NAME/` in this repo's shape. then open a pull request
with just that directory.

`share` runs the scrub before it stages anything, and it refuses rather than
warns:

- **person data** — your home path, plus any terms you list yourself. point
  `SANDBOX_PRIVATE_TERMS` at a file of your own terms, one per line. without
  it only the floor scan runs, and the output says so instead of pretending
  otherwise.
- **deny-listed files** — `.env`, `.sqlite`, `.db`, `.pem`, `.key`,
  `id_rsa`. these never ship, no override.
- **unscannable files** — anything that will not read as text is named for
  you before the push. person data can hide in a binary, so those are your
  eyes' job, not the scrub's.

git history never rides along; the export is fresh.

before you open the pull request, fetch your own staged build back and watch
it verify. if this fails, the card and the bytes disagree and something went
wrong in the packing:

```
sandbox fetch --from ./SandboxOS NAME
```

then add your entry to `index.md`, taking every field from the card you just
staged. the card is the truth; the list is a convenience that owes the card
a fix whenever they disagree.

## an app

an app is bigger: it declares in a manifest exactly what it places, and it
places nothing outside `apps/<its own name>/`. that boundary is enforced in
code, before anyone's keystroke is asked for.

`apps/NAME/APP.md`:

```
# NAME
version: 1.0.0
min-core: 8.1.0
description: one line, said plainly

## placements
apps/NAME/

## checks
the command that proves it works
```

the files themselves go in `apps/NAME/payload/`, laid out exactly as they
should land. a placement line ending in `/` places that whole subtree.

your app also needs a pin in `index.json` — a sha256 over the whole app
directory, `APP.md` included. install recomputes it and refuses a catalog
whose own bytes disagree with its index. the tool has the hash function but
does not yet expose a verb for it, so compute it like this from the repo
root:

```
python3 -c "
import sys; sys.path.insert(0, '/path/to/your/SandboxOS-core')
from engine import catalog; import json
print(json.dumps(catalog.entry_for('apps/NAME'), indent=1))
"
```

that prints one name-to-entry pair. paste the pair *inside* the `apps` block
of `index.json` — not the surrounding braces, which would nest a second
object and break the file — and add your entry to `index.md`.

## what gets taken

- it works, and its checks say how you know
- it carries nobody's private data, including your own
- the card and the bytes agree — `fetch` verifies before it asks
- it says plainly what it does not do

what a thing leaves out belongs on its own card. "it ships with no
credentials and no data — bring your own" is a complete and honest answer.

## what a checksum proves

that the bytes match the card. not who wrote them, and not that they are
safe to run. an app pinned in `index.json` reads as pinned by this catalog;
a build fetched from anywhere reads as unverified, and lands marked
`origin: external`. provenance never washes off. read what you install.
