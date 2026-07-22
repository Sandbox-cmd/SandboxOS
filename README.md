<img src="assets/title.svg" alt="THE SHELF" width="420">

saved builds, shared between a few people who trust each other. everyone
with access runs SandboxOS. nobody else can add or take anything. the
access list is the whole wall.

## what is here

```
index.md          the list: every saved build, its checksum, when it was kept
carts/<name>/     one saved build: CART.md (its card) plus the files it carries
```

every build keeps its card. the card says where the build came from, its
checksum, and what was left out before sharing. nothing gets rewritten. a
newer version arrives as a new commit and the card says so.

## take one

clone the repo, copy the build into `rack/` in your workshop, load it:

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

one-line commands for both moves are coming (`sandbox share` and `sandbox
fetch`). until then this is the whole move.

## the rules

- the card says where a build came from. that never gets stripped.
- the checksum on the card must match the files. if it does not, do not load it.
- access is the only gate: a private repo and an invite list.

THANK YOU FOR USING.
