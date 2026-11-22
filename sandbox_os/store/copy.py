# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The second copy: a bare remote whose heads only move forward, a push of the record's folders
alone, a restore checked against the remote's heads, and a fork of one unit: its folder as it stands
without the lines about the maker or his grants, less what a rule leaves. git runs here and nowhere
else in the store, with an empty global config and a fixed author, so none of this machine's hooks,
filters or signing take part."""
import hashlib, json, os, re, subprocess, time

import sandbox_os.store as _store
from sandbox_os import VERSION
from sandbox_os.store import FORMAT, Refused, gate
from sandbox_os.store.line import UNIT_RE, canonical, line_hash, find_secret, payload_refs, iso
from sandbox_os.store.log import GITATTR, _put, _read, _rows

WHO, MAIL, DROP = "sandbox-os", "sandbox-os@localhost", ("about_you", "grant", "grant_back")
HOSTED = "protecting heads on a remote I cannot reach by path is the host's setting (a protected branch), which I cannot check from here"
STUB = """---
name: {name}
description: A pointer, not a copy, to the skill {name} shared in the workshop the unit {unit} was forked from; ask there for a copy.
license: the source skill's own
compatibility: none here until a copy is made
metadata:
  source: {unit}:{name}@sha256:{sha}
  pinned: {blob}
allowed-tools:
---
"""  # a shared skill in a fork (row 80): the source unit, the skill's name, the sha256 of its SKILL.md and, pinned, that file's git blob id
WITHHELD = "it names the source machine's paths"
LEAVE = {  # what a fork leaves of the unit's folder, one line per rule on its page (card 21; git, settings, block and link are the builder's, as doubts)
    "projected": "projected from the source's record, that is written by the tool from its lines (its grants, its present page, its views); the tool here writes them again",
    "env": "named .env, which holds secrets by its name, and secrets never travel",
    "secret": "the tool's secret check refused what it holds or its name (a refused name shows as …), and secrets never travel",
    "cache": "a cache, rebuilt where it is used",
    "git": "a repository's history, whose packed objects the secret check cannot read; its files came as they stand",
    "settings": "the source workshop's host settings, which name its machine's paths; the tool here writes its own",
    "block": "carried with the tool's block taken out, which carries the source's charter, book and grants; the tool here places its own",
    "link": "a link that leads out of the project's folder, to a path of the source machine",
    "linked": "a link to a path a rule here leaves, which would carry it under another name"}
PAGE = ("# What the fork left out of the project's folder\n\nWritten by the tool (sandbox-os {version}) at {t}, when the project {unit} was forked into "
        "this workshop. The folder came as it stood, but for the paths below, each left out by the rule its line names; nothing here says what a file held.\n\n")
BLOCK = re.compile(rb"\n?<!-- sandbox:begin -->.*?<!-- sandbox:end -->\n?", re.S)  # the hosts' markers (hosts/claude_code.py), which the store may not import
HOOK = """#!/bin/sh
# sandbox-os: refs/heads/heads is the record's history, only moving forward and never deleted; refs/heads/snapshot may be forced.
[ "$1" = refs/heads/heads ] || exit 0
case "$3" in *[!0]*) ;; *) echo "heads is the record's history and is never deleted; nothing was changed" >&2; exit 1;; esac
case "$2" in *[!0]*) ;; *) exit 0;; esac
git merge-base --is-ancestor "$2" "$3" && exit 0
echo "heads only moves forward: this push would drop history another push left here; nothing was changed" >&2; exit 1
"""


def _env(config, when=None):
    """git's environment: this machine's GIT_ settings dropped, an empty global config, no system config or attributes, a fixed author."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=config, GIT_CONFIG_NOSYSTEM="1", GIT_ATTR_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
               GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.attributesFile", GIT_CONFIG_VALUE_0=os.devnull,
               GIT_AUTHOR_NAME=WHO, GIT_AUTHOR_EMAIL=MAIL, GIT_COMMITTER_NAME=WHO, GIT_COMMITTER_EMAIL=MAIL)
    return dict(env, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when) if when else env


def _git(*args, inp=None, env=None):
    """Runs git and returns what it printed; a failure is refused in git's own words."""
    r = subprocess.run(["git", *args], input=inp, capture_output=True, env=env or _env(os.devnull))
    if r.returncode:
        raise Refused(f"git did not do it: {r.stderr.decode(errors='replace').strip()}")
    return r.stdout.decode(errors="replace").strip()


def _path(remote):
    """The remote's folder when it is reached by path (a folder, or file://), else None."""
    p = str(remote)[7:] if str(remote).startswith("file://") else str(remote)
    return os.path.realpath(p) if os.path.isdir(p) else None


def init_remote(path):
    """Makes a bare repository at path whose update hook refuses a heads that goes backwards or is deleted and lets snapshot be forced."""
    os.makedirs(path, exist_ok=True)
    path = os.path.realpath(path)
    hook = os.path.join(path, "hooks", "update")
    _git("init", "-q", "--bare", "--template=", path)
    _git("--git-dir", path, "config", "uploadpack.allowFilter", "true")
    _git("--git-dir", path, "symbolic-ref", "HEAD", "refs/heads/snapshot")
    _put(hook, HOOK.encode(), "wb")
    os.chmod(hook, 0o755)
    return path


def _check(store, theirs):
    """Refuses unless each unit's head on the remote sits here at its seq with its hash, or keeps its id there under a later erasure."""
    for u, h in sorted(theirs.items()):
        mine = store.lines(unit=u)
        resealed = any(e["kind"] == "erase" and e["seq"] > h["seq"] and  # an erasure rehashes every later line of its unit
                       ((store.get((e["body"] or {}).get("erased")) or {}).get("seq") or h["seq"] + 1) <= h["seq"] for e in mine)
        if not any(l["hash"] == h["hash"] or (l["id"] == h["id"] and resealed) for l in mine if l["seq"] == h["seq"]):
            raise Refused(f"the remote holds {u} line {h['seq']} ({h['hash'][:12]}…), which this record lacks: another live "
                          "record pushed there since this one last did, so nothing was pushed")


@gate.outbound("push to a remote")
def push(store, remote, *, by):
    """Sends the record's folders as two refs in one push: heads (each unit's head, a child of the remote's, never forced)
    and snapshot (one parentless commit, forced); prunes a remote reached by path. Returns heads, sent, erased, pruned, said."""
    store._writable()
    if hit := find_secret(str(remote)):
        raise Refused(f"the remote's address matches the secret pattern '{hit}'; give it without the secret, which never travels")
    erased, path, root = store.snapshot(), _path(remote), store.root
    url = "file://" + path if path else remote
    g, cfg, idx = (store._p("cache", n) for n in ("copy.git", "gitconfig", "copy.index"))
    os.path.exists(cfg) or _put(cfg, b"", "wb")
    env = _env(cfg, f"{int(store.clock().timestamp())} +0000")
    run = lambda *a, inp=None: _git("--git-dir", g, *a, inp=inp, env=env)
    ix = lambda *a, inp=None: _git("--git-dir", g, "--work-tree", root, *a, inp=inp, env=dict(env, GIT_INDEX_FILE=idx))
    os.path.isdir(g) or _git("init", "-q", "--bare", "--template=", g, env=env)
    with store.locked():
        files = sorted(os.path.relpath(os.path.join(d, f), root) for u in store.units() for d, _, fs in os.walk(store.unit_dir(u)) for f in fs)
        files += [f for f in ("home.json", ".gitattributes") if os.path.exists(os.path.join(root, f))]
        for rel in files:
            if hit := find_secret(_read(os.path.join(root, rel)).decode("utf-8", "replace")):
                raise Refused(f"{rel} matches the secret pattern '{hit}', so nothing was pushed; erase it or take it out of the record first")
        have = dict(l.split("\t")[::-1] for l in run("ls-remote", url, "refs/heads/heads", "refs/heads/snapshot").splitlines())
        have and run("fetch", "-q", "--no-write-fetch-head", url, *(f"+{r}:refs/remote/{r[11:]}" for r in have))
        old, before = have.get("refs/heads/heads"), have.get("refs/heads/snapshot")
        _check(store, json.loads(run("cat-file", "blob", f"{old}:heads.json")) if old else {})
        heads = {u: {k: hs[-1][k] for k in ("seq", "hash", "id")} for u, hs in store.heads().items() if hs}
        os.path.exists(idx) and os.remove(idx)
        ix("update-index", "--add", "-z", "--stdin", inp="".join(f + "\0" for f in files).encode())
        blob = run("hash-object", "-w", "--stdin", inp=(canonical(heads) + "\n").encode())
        ix("update-index", "--add", "--cacheinfo", f"100644,{blob},heads.json")
        snap = run("commit-tree", ix("write-tree"), "-m", "snapshot: the record's folders as they stand")
    hc = run("commit-tree", run("mktree", inp=f"100644 blob {blob}\theads.json\n".encode()), *(["-p", old] if old else []), "-m", "heads")
    run("push", "-q", "--atomic", url, f"{hc}:refs/heads/heads", f"+{snap}:refs/heads/snapshot")
    sent = run("diff-tree", "-r", "-z", "--name-only", "--diff-filter=AM", before, snap).split("\0") if before else files + ["heads.json"]
    run("update-ref", "--stdin", inp=f"update refs/remote/heads {hc}\nupdate refs/remote/snapshot {snap}\n".encode())
    for d in [g] + ([path] if path else []):  # the old snapshot's objects go, so an erased line's words leave
        _git("--git-dir", d, "reflog", "expire", "--expire=now", "--all", env=env)
        _git("--git-dir", d, "gc", "-q", "--prune=now", env=env)
    store.append("workshop", "copy", {"event": "push", "remote": path or remote, "heads": heads}, by=by)
    return {"heads": heads, "sent": sorted(s for s in sent if s), "erased": erased, "pruned": bool(path), "said": [] if path else [HOSTED]}


@gate.outbound("a restore from a remote")
def restore(remote, into, *, unit=None):
    """Clones the remote's snapshot into a new folder (one unit alone by a sparse partial clone), checks every chain and each
    head against the remote's heads, rebuilds the index and names any mismatch; it writes nowhere but into. It reaches the remote,
    so it is outbound: inside another replay it is refused before git runs."""
    started = time.monotonic()
    if unit is not None and not UNIT_RE.match(str(unit)):
        raise Refused(f"a unit is named in lower-case letters, digits, dots, dashes and underscores, not {unit!r}")
    if os.path.exists(into) and os.listdir(into):
        raise Refused(f"{into} already holds files; a restore goes into a new folder, never over another")
    url = "file://" + _path(remote) if _path(remote) else remote
    # the remote is reached here, before any line is read back; the replay below covers only the copied files (nothing leaves while they are read)
    _git("clone", "-q", "--template=", "--branch", "snapshot", "--single-branch", *(["--filter=blob:none", "--sparse"] if unit else []), url, into)
    unit and _git("-C", into, "sparse-checkout", "set", f"projects/{unit}/record")
    _git("-C", into, "fetch", "-q", "--no-write-fetch-head", url, "+refs/heads/heads:refs/heads/heads")
    want = json.loads(_git("-C", into, "cat-file", "blob", "refs/heads/heads:heads.json"))
    with gate.replaying():
        s = _store.open(into, read_only=True)
        report = s.verify(unit)
        s.rebuild_index()
        have = {u: hs[-1] for u, hs in s.heads().items() if hs}
        failures = [f["file"] + (f" row {f['row']}" if f["row"] else "") + f": {f['what']}" for f in report["failures"]]
        for u in [unit] if unit else sorted(set(want) | set(have)):
            w, h = want.get(u), have.get(u)
            if not (w and h and (w["seq"], w["hash"]) == (h["seq"], h["hash"])):
                failures.append(f"{u}: the copy's head is " + (f"line {h['seq']} ({h['hash'][:12]}…)" if h else "missing") +
                                ", but the remote's heads say " + (f"line {w['seq']} ({w['hash'][:12]}…)" if w else "nothing"))
        return {"seconds": round(time.monotonic() - started, 3), "matched": not failures, "failures": failures, "lines": report["lines"],
                "heads": {u: {k: h[k] for k in ("seq", "hash", "id")} for u, h in have.items()}}


def _person(store, line):
    """Whether a line is an object of type person; a fork is a copy of the work, and the people and every line about them stay behind."""
    return bool(line) and line.get("kind") == "object" and (line.get("body") or {}).get("type") == "person"


def _named(rel):
    """The rule a path of the project's folder is left by for its own name, a link or not (a key of LEAVE, or record, whose lines the fork
    writes itself), else None."""
    top, name = "/" not in rel, rel.rsplit("/", 1)[-1]
    return ("record" if top and name == "record" else "projected" if top and name in ("grants.md", "where-it-stands.md", "pages")
            else "env" if name == ".env" or name.startswith(".env.") else "cache" if name == "__pycache__" or top and name == "cache"
            else "git" if name == ".git" else "settings" if rel in (".claude/settings.json", ".claude/settings.local.json", ".codex") else None)


def _rule(src, rel, e):
    """The rule a path is left by: its own name; for a link, also every hop of its chain and where it lands (outside the folder, on a
    path a rule leaves, or on a file the secret check refuses), so no link carries a leaving by another name (Astra's finding 4)."""
    leaves = lambda p: any(_named("/".join(p.split(os.sep)[:i])) for i in range(1, len(p.split(os.sep)) + 1))
    if (named := _named(rel)) or not e.is_symlink():
        return named
    base, cur, seen = os.path.realpath(src), rel, set()
    while os.path.islink(os.path.join(src, cur)) and cur not in seen:
        seen.add(cur)
        t = os.readlink(os.path.join(src, cur))
        cur = os.path.normpath(os.path.join(os.path.dirname(cur), t))
        if os.path.isabs(t) or cur.split(os.sep)[0] == "..":
            return "link"
        if leaves(cur):
            return "linked"
    real = os.path.realpath(e.path)
    if not real.startswith(base + os.sep):
        return "link"
    to = os.path.relpath(real, base)
    return "linked" if leaves(to) or os.path.isfile(real) and (find_secret(to) or find_secret(_read(real).decode("utf-8", "replace"))) else None


def _folder(src, dst, rel="", left=None):
    """The unit's folder into dst as it stands, a link inside it kept as a link, each file through the secret check; returns {rule: paths}."""
    left = {} if left is None else left
    for e in sorted(os.scandir(os.path.join(src, rel)), key=lambda e: e.name):
        p, rule = rel + e.name, _rule(src, rel + e.name, e)
        if rule:
            rule == "record" or left.setdefault(rule, []).append(p + ("/" if e.is_dir(follow_symlinks=False) else ""))
        elif e.is_symlink():
            os.makedirs(os.path.join(dst, rel), exist_ok=True)
            os.symlink(os.readlink(e.path), os.path.join(dst, p))
        elif e.is_dir():
            _folder(src, dst, p + "/", left)
        elif e.is_file():
            data = _read(e.path)
            if find_secret(p) or find_secret(data.decode("utf-8", "replace")):  # named by path, never by content; a refused name is not written
                left.setdefault("secret", []).append(os.path.join(os.path.dirname(p), "…") if find_secret(p) else p)
                continue
            if e.name in ("AGENTS.md", "CLAUDE.md") and BLOCK.search(data):
                data = BLOCK.sub(b"", data)
                left.setdefault("block", []).append(p)
            if data.strip() or e.name not in ("AGENTS.md", "CLAUDE.md"):
                _put(os.path.join(dst, p), data, "wb")
                os.chmod(os.path.join(dst, p), e.stat().st_mode & 0o777)
    return left


def fork(store, unit, into, *, by):
    """Writes one unit's record into a new workshop at into, without its about_you, grant and grant_back lines, its person objects
    and every line about a person, or any line naming them, every other line kept with its id and time and chained again from the first; the unit's folder as it stands, less what a rule
    of LEAVE leaves, named by path on the fork's page move/fork.md (card 21), none written when nothing was left; the workshop's shared
    skills as stubs naming their source, never a path or a copy, each linked into .claude/skills; a home.json naming no machine and no
    path, so the forker's first open adopts it (row 80: wholly theirs); a check's receipt without the profile that names this machine's
    paths; then a fork line in the source unit."""
    with gate.replaying():
        store._writable()
        if unit not in store.units():
            raise Refused(f"there is no unit {unit!r} in this record to fork")
        if os.path.exists(into) and os.listdir(into):
            raise Refused(f"{into} already holds files; a fork goes into a new folder, never over another")
        if (os.path.realpath(into) + os.sep).startswith(os.path.realpath(os.path.join(store.root, "projects", unit)) + os.sep):
            raise Refused(f"{into} is inside the project's own folder, which the fork carries; a fork goes into a folder outside it")
        rows = [json.loads(b) for f in store._files(unit) for b in _rows(_read(f))]
        text, gone = {r["id"]: canonical(r["body"]) for r in rows}, {r["id"] for r in rows if r["kind"] in DROP}
        gone |= {r["id"] for r in rows if _person(store, r) or (r.get("about") and _person(store, store.get(r["about"])))}  # the people stay behind
        while True:  # a line naming one left behind is left behind too, and so is the target of a deletion left behind
            more = {r["id"] for r in rows if r["id"] not in gone and (r.get("about") in gone or any(i in text[r["id"]] for i in gone))}
            more |= {r["body"].get("target") for r in rows if r["id"] in more and r["kind"] == "delete"} - {None}
            if not more - gone:
                break
            gone |= more
        def carry(r):  # a check's receipt travels; the sandbox profile beside it spells out the source machine's paths and stays (row 80)
            sb = (r["body"] or {}).get("sandbox") if r["kind"] == "check" else None
            return dict(r, body=dict(r["body"], sandbox=dict({k: v for k, v in sb.items() if k != "profile"}, profile_withheld=WITHHELD))) \
                if isinstance(sb, dict) and "profile" in sb else r
        kept, prev, years = [carry(r) for r in rows if r["id"] not in gone], None, {}
        os.makedirs(into, exist_ok=True)
        root = os.path.realpath(into)
        rec = os.path.join(root, "projects", unit, "record")
        for n, r in enumerate(kept, 1):
            r = dict({k: v for k, v in r.items() if k != "hash"}, seq=n, prev=prev)
            r["hash"] = prev = line_hash(r)
            years.setdefault(r["t"][:4], []).append(canonical(r) + "\n")
        for year, ls in years.items():
            _put(os.path.join(rec, year + ".jsonl"), "".join(ls).encode(), "wb")
        for sha in sorted({p for r in kept for p in payload_refs(r["body"])}):
            src = store.payload_path(sha)
            src and _put(os.path.join(rec, "payloads", sha), _read(src), "wb")
        _put(os.path.join(root, ".gitattributes"), GITATTR.encode(), "wb")
        shared = os.path.join(store.root, ".agents", "skills")
        for n in sorted(x for x in (os.listdir(shared) if os.path.isdir(shared) else []) if os.path.isfile(os.path.join(shared, x, "SKILL.md"))):
            b = _read(os.path.join(shared, n, "SKILL.md"))
            stub = STUB.format(name=n, unit=unit, sha=hashlib.sha256(b).hexdigest(), blob=hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest())
            _put(os.path.join(root, ".agents", "skills", n, "SKILL.md"), stub.encode(), "wb")
            os.makedirs(os.path.join(root, ".claude", "skills"), exist_ok=True)
            os.symlink(os.path.join("..", "..", ".agents", "skills", n), os.path.join(root, ".claude", "skills", n))
        left = _folder(os.path.join(store.root, "projects", unit), os.path.join(root, "projects", unit))
        lines = [f"- {LEAVE[k]}: " + ", ".join(f"`{p}`" for p in dict.fromkeys(left[k])) for k in LEAVE if k in left]
        lines and _put(os.path.join(root, "move", "fork.md"), (PAGE.format(version=VERSION, t=iso(store.clock()), unit=unit) + "\n".join(lines) + "\n").encode(), "wb")
        _put(os.path.join(root, "home.json"), (canonical({"format": FORMAT, "machine": None, "path": None, "since": iso(store.clock())}) + "\n").encode(), "wb")
        store.append(unit, "fork", {"into": root, "unit": unit, "lines": len(kept)}, by=by)
        return root
