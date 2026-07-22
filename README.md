# the shelf

saved builds, shared between a few people who trust each other. everyone
with access runs SandboxOS. nobody else can put anything here or take
anything away — the access list is the whole wall.

## what is here

```
index.md          the list — every saved build, its checksum, when it was kept
carts/<name>/     one saved build: CART.md (its card) + the files it carries
```

every build keeps its card: where it came from, its checksum, what was left
out before sharing. nothing here gets rewritten — a newer version arrives as
a new commit, and the card says so.

## take one

clone this repo, copy the build into `rack/` in your own workshop, load it:

```
git clone https://github.com/Sandbox-cmd/SandboxOS.git shelf
cp -R shelf/carts/commerceos ~/Sandbox/rack/commerceos
sandbox load commerceos
```

## share one

copy one of yours in, add a line to `index.md`, commit, push:

```
cp -R ~/Sandbox/rack/<name> shelf/carts/<name>
```

one-line commands for both moves are coming (`sandbox share`, `sandbox
fetch`). until then, the copies above are the whole move.

## the rules

- the card says where a build came from. that never gets stripped.
- the checksum on the card must match the files. if it doesn't, don't load it.
- access is the only gate: private repo, invited people, nobody else.

THANK YOU FOR USING.
