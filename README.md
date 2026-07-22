# the shelf — a shared cart rack for SandboxOS

this repo is not a program. it is a **shelf**: a place where a small group of
makers keep the carts they want to hand each other. a cart is a saved build —
one reusable thing, pressed once, loaded into any project after. here they live
where the whole group can reach them.

everyone with access to this repo runs SandboxOS. nobody outside can share a
cart, and nobody outside can take one — the access list is the whole wall.

## what's on the shelf

```
index.md          the catalog — every cart, its checksum, when it was kept
carts/<name>/     one cart: CART.md (its card) + the files it carries
```

each cart keeps the card it was pressed with: where it came from, its sha256,
what was withheld. nothing here is rewritten — a new version rides in as a new
commit, and the card carries the history.

## the moves (today: plain git — verbs are coming)

take the shelf:

```
git clone https://github.com/Sandbox-cmd/SandboxOS.git shelf
```

**take a cart** — copy it into your own rack, then load it:

```
cp -R shelf/carts/commerceos ~/Sandbox/rack/commerceos
sandbox load commerceos        # drops it into the project that's on
```

**share a cart** — copy one of yours from your rack onto the shelf and push:

```
cp -R ~/Sandbox/rack/<name> shelf/carts/<name>
# add it to index.md, then commit + push
```

`sandbox shelf` / `sandbox share` / `sandbox fetch` will make these one-line
moves; until then the copies above are the whole ritual.

## the rules the shelf keeps

- a cart you take keeps its origin — the card says whose rack pressed it.
- the checksum on the card must match the files, or don't load it.
- access is the only gate. this repo is private; sharing is invitation, not
  publication.

pressed by hands that trust each other. that is the whole idea.
