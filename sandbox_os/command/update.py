# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""Update and the way back. A packed release is refused, with a line naming the reason, or checked, staged in the install folder,
self-checked here and offered as a card; it is applied only on the maker's yes to that card, after the running version is packed from
its sealed files and the way back recorded, by uv over the very file whose seal was checked; a file the tool placed in the workshop, and
the block it placed between the markers (the release's own block code run in a subprocess), is refreshed when the maker never changed
it and held when he did; and back reinstalls the kept previous version offline.

    check(src, pub=, running=) -> dict   offer(src, workshop=) -> dict   apply(version, workshop=) -> dict   back(workshop=) -> dict"""
import glob, hashlib, io, json, os, re, shlex, shutil, subprocess, sys, zipfile

from sandbox_os import VERSION
from sandbox_os.store import open as _open
from sandbox_os.command import TOOL, cards, say, seal
from sandbox_os.hosts.claude_code import BEGIN, END

TREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(TREE, "command", "release.pub")
COMMENT = re.compile(r"sandbox-os (\S+) format (\d+) commit (\S+)")
PLACED, UNIT, SEALS = ("charter.md", "book.md", "CLAUDE.md#block", "AGENTS.md#block"), "workshop", ("sandbox_os/MANIFEST", "sandbox_os/MANIFEST.minisig")
# a #block entry is the text from BEGIN to END in that file (the markers included, as each adapter hashes it) and nothing around it
HOSTS = {"CLAUDE.md": "Claude Code", "AGENTS.md": "Codex"}
PROGRAM = """import importlib, json, sys
sys.path.insert(0, sys.argv[1])
out, answer, sys.stdout = {}, sys.stdout, sys.stderr  # a print in the release's code never mixes into the answer
for name, mod in (("CLAUDE.md", "claude_code"), ("AGENTS.md", "codex")):
    try:
        out[name] = importlib.import_module("sandbox_os.hosts." + mod).block(sys.argv[2])
    except Exception as e:  # an adapter the release lacks is no block; any other failure is named, never read as none
        absent = isinstance(e, ModuleNotFoundError) and (e.name or "").startswith("sandbox_os.hosts")
        out[name] = None if absent else {"failed": type(e).__name__ + ": " + str(e)}
answer.write(json.dumps(out))
"""


def order(v):
    """A version's place: 10.0.0a1 < 10.0.0b1 < 10.0.0rc1 < 10.0.0 < 10.0.1; anything else sorts first."""
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?", v or "")
    return (int(m[1]), int(m[2]), int(m[3]), {"a": 0, "b": 1, "rc": 2, None: 3}[m[4]], int(m[5] or 0)) if m else (-1,)


def version_of(text):
    m = re.search(r'^VERSION = "([^"]+)"', text or "", re.M)
    return m.group(1) if m else None


def install_folder(home=None):
    return os.path.join(home or os.path.expanduser("~"), ".local", "share", "sandbox-os")


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest() if path and os.path.exists(path) else None


def _record(store, kind, body):
    with store.locked():
        return store.append(UNIT, kind, body, by=TOOL)


def check(src, *, pub=PUB, running=None):
    """Reads a packed release (its folder or its wheel) and refuses it, with the reason, unless its seal matches the key held, every
    listed hash matches, nothing is unlisted, the trusted comment, the version file and the file name agree, and it is newer."""
    out = {"ok": False, "reason": None, "version": None, "wheel": None}
    no = lambda why: dict(out, reason=why)
    hits = [src] if src.endswith(".whl") else glob.glob(os.path.join(src, "*.whl"))
    if len(hits) != 1:
        return no(f"not a release: {src} holds {len(hits)} wheels, not one")
    try:
        raw = open(hits[0], "rb").read()  # read once: every judgement below, and what uv installs, is these bytes
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            members = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    except (OSError, zipfile.BadZipFile) as e:
        return no(f"not a release: {e}")
    man, sig = (members.get(n) for n in SEALS)
    if not (man and sig):
        return no("the release carries no MANIFEST and seal")
    for n, data in zip(SEALS, (man, sig)):
        beside = os.path.join(src, os.path.basename(n))
        if not src.endswith(".whl") and os.path.exists(beside) and open(beside, "rb").read() != data:
            return no(f"the release folder's {os.path.basename(n)} is not the wheel's own")
    s = seal.verify_bytes(man, sig, pub)
    if not s["ok"]:
        return no(s["reason"])
    rows = [re.fullmatch(r"([0-9a-f]{64})  (.+)", r) for r in man.decode("utf-8", "replace").splitlines()]
    if not all(rows):
        return no("a line of the MANIFEST is not in shasum's form")
    listed = {os.path.normpath(os.path.join("sandbox_os", m[2])): m for m in rows}
    for name, m in sorted(listed.items()):
        if hashlib.sha256(members.get(name, b"")).hexdigest() != m[1]:
            return no(f"a hash differs: {m[2]} " + ("is not the file that was sealed" if name in members else "is listed and missing"))
    c, named = COMMENT.fullmatch(s["trusted_comment"]), re.fullmatch(r"sandbox_os-(.+)-py3-none-any\.whl", os.path.basename(hits[0]))
    own = {f"sandbox_os-{c[1]}.dist-info/RECORD"} if c else set()  # the one file an installer writes: the release's own RECORD
    extra = sorted(n for n in members if n not in listed and n not in SEALS and n not in own)
    if extra:
        return no(f"a file unlisted in the MANIFEST: {extra[0]}")
    vfile = version_of(members.get("sandbox_os/__init__.py", b"").decode("utf-8", "replace"))
    if not (c and named and c[1] == named[1] == vfile):
        return no(f"the trusted comment ({s['trusted_comment']}), the version file ({vfile}) and the file name ({os.path.basename(hits[0])}) disagree")
    if running and order(c[1]) <= order(running):
        return no(f"{c[1]} is not newer than the running {running}")
    return dict(out, ok=True, version=c[1], format=int(c[2]), commit=c[3], key_id=s["key_id"], wheel=hits[0], comment=s["trusted_comment"],
                members=members, data=raw, sha256=hashlib.sha256(raw).hexdigest())


def _placed(home):
    p = os.path.join(install_folder(home), "placed.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def release_blocks(r, ws, folder):
    """The release's own blocks, by its own adapters: the verified bytes written under folder/tree/ and its block code run there in a
    subprocess, never imported here (the welcome alone writes a block, so the update runs the new welcome's code). None for a host whose
    adapter the tree lacks (no block to place); when its code raises, exits, answers no JSON or runs past 30 seconds, None too and a line
    under "failed" naming the host and the failure's first line (Astra's finding 8 of batch D): that block is neither refreshed nor held."""
    tree, out, failed, why, got = os.path.join(folder, "tree"), {}, {}, None, None
    shutil.rmtree(tree, ignore_errors=True)
    for n, data in r["members"].items():
        rel = os.path.normpath(n)
        if rel.startswith("sandbox_os" + os.sep) and not os.path.isabs(rel):
            os.makedirs(os.path.dirname(os.path.join(tree, rel)), exist_ok=True)
            open(os.path.join(tree, rel), "wb").write(data)
    try:
        p = subprocess.run([sys.executable, "-I", "-c", PROGRAM, tree, ws], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        last = ([x for x in (p.stderr or "").splitlines() if x.strip()] or ["no words"])[-1]  # a traceback's own line is its last
        why = f"its block code exited {p.returncode}: {_plain(last, ws, tree)}" if p.returncode else None
        got = None if why else json.loads(p.stdout)
    except subprocess.TimeoutExpired:
        why = "its block code ran past 30 seconds"
    except OSError as e:
        why = f"its block code could not be run: {_plain(str(e), ws, tree)}"
    except ValueError:
        why = "its block code's answer was not JSON"
    why = why or (None if isinstance(got, dict) else "its block code's answer was not JSON")
    for n, host in HOSTS.items():
        v = None if why else got.get(n)
        out[n] = v if isinstance(v, str) else None
        w = why or (None if v is None or isinstance(v, str) else f"it raised {_plain(v['failed'], ws, tree)}"
                    if isinstance(v, dict) and "failed" in v else "its block is not text")
        if w:
            failed[n] = f"{host}'s adapter in the release failed here: {w}"
    return dict(out, failed=failed)


def _plain(text, *known):
    """A failure's first line as the card may show it: no path (the known ones first, whole), no long token that could be a secret, at
    most 160 characters."""
    first = next((x.strip() for x in (text or "").splitlines() if x.strip()), "no words")
    for p in sorted({k for x in (*known, os.path.expanduser("~")) if x for k in (x, os.path.realpath(x))}, key=len, reverse=True):
        first = first.replace(p, "(a path)")
    first = re.sub(r"(?<![\w.)])~?/[^\s'\",;)]*", "(a path)", first)
    return re.sub(r"[A-Za-z0-9_+=-]{24,}", "(a long token)", first)[:160]


def _failed(failed):
    """The failed blocks in one phrase: each entry with its host and the failure's first line."""
    return "; ".join(f"{n} ({w})" for n, w in failed.items())


def _found(ws, n):
    """A file's bytes and where its block lies (BEGIN to the first END after it), or (data, None, None) when it holds no block; bytes, never
    text, so every byte the maker wrote outside the markers, a CRLF line among them, comes back as it was (Astra's finding 9 of batch D)."""
    p = os.path.join(ws, n)
    data = open(p, "rb").read() if os.path.exists(p) else b""
    i = data.find(BEGIN.encode())
    j = data.find(END.encode(), i) if i >= 0 else -1
    return (data, i, j + len(END.encode())) if j >= 0 else (data, None, None)


def _judged(ws, n, members, running_tree, known, blocks):
    """One placed entry's (release, now, placed) hashes: a file by its sealed bytes, its hash in the workshop and the hash kept at the last
    apply (else the running version's own copy); a block by the release's block, the block found in the file and the adapter's own cache."""
    if not n.endswith("#block"):
        sealed = members.get("sandbox_os/partner/" + n)
        return (sealed and hashlib.sha256(sealed).hexdigest(), _sha(os.path.join(ws, n)),
                known.get(n) or (_sha(os.path.join(running_tree, "partner", n)) if running_tree else None))
    f = n[:-len("#block")]
    new, (data, i, j), cache = (blocks or {}).get(f), _found(ws, f), os.path.join(ws, "cache", "placed", f + ".sha256")
    was = open(cache).read().strip() or None if os.path.exists(cache) else None
    now = hashlib.sha256(data[i:j]).hexdigest() if i is not None else None
    return (new and (now or was) and hashlib.sha256(new.encode()).hexdigest()), now, was  # a block the tool never placed is neither


def plan(ws, members, running_tree, home, blocks=None):
    """Which placed files and blocks the release would refresh (unchanged since the tool placed them: by the hash kept at the last apply,
    else the running version's own copy; a block by its adapter's cache) and which it would hold (changed or deleted by the maker); each
    with the hashes it was judged by. The release's copies are the sealed bytes read out of the wheel whose seal was checked, never the
    extracted folder, and its blocks are those release_blocks gives; a placed block whose release code failed is under failed, and stays."""
    known, out = _placed(home).get(os.path.realpath(ws), {}), {"refreshed": [], "held": [], "failed": {}, "hashes": {}}
    for n in PLACED:
        new, now, was = _judged(ws, n, members, running_tree, known, blocks)
        if n.removesuffix("#block") in (blocks or {}).get("failed", {}) and (now or was):
            out["failed"][n] = blocks["failed"][n.removesuffix("#block")]
        elif new and now != new:
            out["refreshed" if now and now == was else "held"].append(n)
            out["hashes"][n] = {"placed": was, "now": now, "release": new}
    return out


def offer(src, *, workshop, home=None, pub=PUB, running=VERSION, running_tree=TREE, env=None, shim=None):
    """update --from FILE: the check; a refusal is a line with its reason and nothing staged; a pass is staged in the install folder,
    self-checked against its unpacked files, and offered as a card with every field the walk's release page shows, its last words the
    command that applies it after his yes (R-READ-14)."""
    from sandbox_os.command import selfcheck
    from sandbox_os.command.release import changes_for, format_of
    s = workshop if hasattr(workshop, "lines") else _open(workshop)
    r = check(src, pub=pub, running=running)
    if not r["ok"]:
        _record(s, "release", {"event": "refused", "from": src, "reason": r["reason"], "text": f"a release was refused before you saw it: {r['reason']}"})
        return r
    v, rel = r["version"], os.path.join(install_folder(home), "releases")
    dest, tree = os.path.join(rel, v), os.path.join(rel, v, "tree", "sandbox_os")
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)
    for p in glob.glob(os.path.join(src, "*")) if os.path.isdir(src) else [src]:
        shutil.copyfile(p, os.path.join(dest, os.path.basename(p)))
    with zipfile.ZipFile(os.path.join(dest, os.path.basename(r["wheel"]))) as z:
        z.extractall(os.path.join(dest, "tree"))
        for n in SEALS:
            open(os.path.join(dest, os.path.basename(n)), "wb").write(z.read(n))
    sc = selfcheck.run(tree, s, scratch=os.path.join(install_folder(home), "tmp"), pub=pub)
    red, pg = ([c["detail"] for c in sc["checks"] if not c["ok"] and (c["name"] == "views") == x] for x in (False, True))
    if red:  # only a fault in the release itself or in the record refuses it; one in the workshop's pages is said on the card (card 41)
        shutil.rmtree(dest)
        _record(s, "release", {"event": "self-check-failed", "version": v, "checks": sc["checks"],
                               "text": f"release {v} passed its seal but failed its self-check here; nothing is offered and the staged files are gone"})
        return dict(r, ok=False, reason="the self-check failed here: " + "; ".join(red))
    blocks = release_blocks(r, s.root, os.path.join(dest, f"verified-{r['sha256'][:16]}"))
    p, changes = plan(s.root, r["members"], running_tree, home, blocks), changes_for(tree, v)
    was = format_of(open(os.path.join(running_tree, "store", "__init__.py")).read()) if running_tree else r["format"]
    fmt = {"from": was, "to": r["format"], "migration": None if was == r["format"] else next(
        (x for x in changes.splitlines() if "migration" in x.lower()), None)}
    back, ending = _line(os.path.join(rel, running, f'sandbox_os-{running}-py3-none-any.whl'), bin_dir(env, shim)), seal.public(pub)[2][-8:]
    held, fresh = ", ".join(p["held"]) or "none", ", ".join(p["refreshed"]) or "none"
    lang = cards.language(s.root)  # card 38: the card in the language the workshop was welcomed in, as it is raised
    w = lambda k, **x: say("card.update." + k, lang=lang, **x)  # noqa: E731 (the card's sentences, in the table's words)
    body = {**cards.five(
        "card.update", lang=lang, running=running, v=v, back=back, held=held, fresh=fresh, comment=str(r["comment"]), ending=ending, changes=changes or w("nothing"),
        checks=w("checks.release" if pg else "checks.self"), page=" " + w("page", page=pg[0]) if pg else "", notgreen="; " + w("notgreen", page=pg[0]) if pg else "",
        notwhole=" " + w("notwhole", failed=", ".join(p["failed"])) if p["failed"] else "", green=sum(c["ok"] for c in sc["checks"]), all=len(sc["checks"]),
        seconds=sc["seconds"], block=w("block.failed", failed=_failed(p["failed"])) if p["failed"] else w("block"), was=str(fmt["from"]), to=str(fmt["to"]),
        migration=f", {fmt['migration']}" if fmt["migration"] else ""),
        "about": UNIT, "purpose": f"update:{v}", "release": v, "from": running, "changes": changes,
        "key_ending": ending, "selfcheck": {k: sc[k] for k in ("ok", "checks", "seconds")}, "held": p["held"], "refreshed": p["refreshed"],
        "failed": p["failed"], "format": fmt, "back": back, "staged": dest}
    return dict(r, card=cards.raise_(s, UNIT, body, by=TOOL), staged=dest, selfcheck=sc, held=p["held"], refreshed=p["refreshed"], failed=p["failed"])


def keep_running(rel, running, running_tree, pub):
    """The running version kept in the install folder: its kept release when one passes its seal, else packed from the files the running
    tool's own MANIFEST lists, every one matching; an edited tool cannot be packed, and the edit is named. Returns (wheel, reason)."""
    from sandbox_os.command.release import build_wheel
    folder, man = os.path.join(rel, running), os.path.join(running_tree or "", "MANIFEST")
    if os.path.isdir(folder) and check(folder, pub=pub)["ok"]:
        return check(folder, pub=pub)["wheel"], None
    if not os.path.exists(man):
        return None, f"the running tool ({running}) carries no MANIFEST, so it cannot be packed as the way back; nothing was applied"
    rows = [(r[:64], r[66:]) for r in open(man, encoding="utf-8").read().splitlines()]
    bad = [p for h, p in rows if _sha(os.path.normpath(os.path.join(running_tree, p))) != h]
    if bad:
        return None, say("update.back.differs", bad=", ".join(bad))
    shutil.rmtree(folder, ignore_errors=True)
    os.makedirs(folder)
    for n in ("MANIFEST", "MANIFEST.minisig"):
        shutil.copyfile(os.path.join(running_tree, n), os.path.join(folder, n))
    build_wheel({p: open(os.path.normpath(os.path.join(running_tree, p)), "rb").read() for _, p in rows}, open(man, "rb").read(),
                open(man + ".minisig", "rb").read(), running, folder)
    r = check(folder, pub=pub)
    return (r["wheel"], None) if r["ok"] else (None, f"the running version, packed, fails its own seal: {r['reason']}; nothing was applied")


def bin_dir(env=None, shim=None):
    """The folder uv must keep the command in: the one the maker's shell names (uv's bin-folder variable), else the folder the running
    command was typed from (the shim uv placed, named sandbox), else none and uv's default stands. Found 2026-11-06: an apply run from
    a shell that named no folder let uv move the command to its default folder, over another tool's command that lived there."""
    env = os.environ if env is None else env
    if env.get("UV_TOOL_BIN_DIR"):
        return env["UV_TOOL_BIN_DIR"]
    shim = shim or sys.argv[0]
    return os.path.dirname(os.path.abspath(shim)) if os.path.basename(shim) == "sandbox" else None


def _line(wheel, folder):
    """The uv line as the maker would type it by hand, naming the command's folder when one is known."""
    return (f"UV_TOOL_BIN_DIR={shlex.quote(folder)} " if folder else "") + f"uv tool install --force --offline {wheel}"


def _uv(wheel, env, folder=None):
    e = dict(os.environ if env is None else env)
    if folder:
        e["UV_TOOL_BIN_DIR"] = folder
    return subprocess.run(["uv", "tool", "install", "--force", "--offline", wheel], env=e, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=600)


def apply(version, *, workshop, home=None, pub=PUB, running=VERSION, running_tree=TREE, env=None, shim=None):
    """update --apply VERSION: only on the maker's standing yes to the card that offered this version; the running version packed first and
    the way back recorded and printed; uv over the very wheel whose seal was checked; placed files refreshed or held; one applied line."""
    s, rel = workshop if hasattr(workshop, "lines") else _open(workshop), os.path.join(install_folder(home), "releases")
    card = ([c for c in s.lines(unit=UNIT, kinds=["card"]) if (c["body"] or {}).get("purpose") == f"update:{version}"] or [None])[-1]
    d = card and cards.decision(s, card["id"])
    if not (d and d["body"].get("answer") == "yes"):
        return {"ok": False, "reason": say("update.noyes", version=version, card=card["id"], has=say("update.noyes.has", answer=str(d["body"]["answer"])) if d
                                           else say("update.noyes.none")) if card else say("update.nocard", version=version)}
    r = check(os.path.join(rel, version), pub=pub, running=running)
    kept, why = keep_running(rel, running, running_tree, pub) if r["ok"] else (None, f"the staged {version} no longer passes its check: {r['reason']}")
    if not kept:
        return {"ok": False, "reason": why}
    tree = os.path.join(rel, version, "tree", "sandbox_os")
    verified = os.path.join(rel, version, f"verified-{r['sha256'][:16]}", os.path.basename(r["wheel"]))  # uv needs a wheel's own name
    os.makedirs(os.path.dirname(verified), exist_ok=True)
    blocks = release_blocks(r, s.root, os.path.dirname(verified))  # the new blocks from the verified bytes, before uv replaces the running copy
    pl, placed = plan(s.root, r["members"], running_tree, home, blocks), _placed(home)  # the placed hashes, read before uv replaces the running copies
    folder, line = bin_dir(env, shim), _line(kept, bin_dir(env, shim))
    _record(s, "release", {"event": "way-back", "from": version, "to": running, "back": line, "text": f"the way back from {version}: {line}"})
    print(f"the way back, recorded before anything changes: {line}")
    with open(verified, "wb") as f:  # a fresh copy of the very bytes the check verified, so a wheel swapped at its path since is never read
        f.write(r["data"])
    p = _uv(verified, env, folder)
    if p.returncode:
        _record(s, "release", {"event": "failed", "to": version, "uv": (p.stdout + p.stderr)[-2000:], "back": line})
        return {"ok": False, "reason": f"uv could not install {version}: {p.stderr.strip()[-400:]}; the way back: {line}", "back": line}
    mine, done = placed.setdefault(os.path.realpath(s.root), {}), {"refreshed": [], "held": [], "failed": pl["failed"]}
    for n, h in pl["hashes"].items():  # judged again at the moment of writing: a change made while uv ran is held, never overwritten
        f, block = n.removesuffix("#block"), n.endswith("#block")
        now = _judged(s.root, n, r["members"], running_tree, mine, blocks)[1]
        if now == h["release"]:
            continue
        if not (now and now == h["placed"]):
            done["held"].append(n)
            copy = os.path.join(os.path.dirname(verified), f + ".block") if block else os.path.join(tree, "partner", n)
            if block:  # the release's block, readable beside the kept release as a file's copy is
                open(copy, "w", encoding="utf-8").write(blocks[f] + "\n")
            _record(s, "held", {"path": n, "placed": h["placed"], "now": now, "release": version, "copy": copy,
                                "text": say("update.held.block" if block else "update.held.file", file=f if block else n)})
            continue
        if block:  # only the bytes between the markers are replaced, his prefix and suffix exactly, and the adapter's cache takes the new hash
            cur, i, j = _found(s.root, f)
            for dest, data in ((os.path.join(s.root, f), cur[:i] + blocks[f].encode() + cur[j:]),
                               (os.path.join(s.root, "cache", "placed", f + ".sha256"), (h["release"] + "\n").encode())):
                with open(dest + ".part", "wb") as out:
                    out.write(data)
                os.replace(dest + ".part", dest)
            done["refreshed"].append(n)
            continue
        for dest in [os.path.join(s.root, n)] + [os.path.join(s.root, "cache", "placed", n)] * os.path.isdir(os.path.join(s.root, "cache", "placed")):
            with open(dest + ".part", "wb") as f:  # the sealed bytes from the checked wheel; the start's own memory too, so it reads no edit
                f.write(r["members"]["sandbox_os/partner/" + n])
            os.replace(dest + ".part", dest)
        done["refreshed"].append(n)
        mine[n] = h["release"]
    json.dump(placed, open(os.path.join(install_folder(home), "placed.json"), "w"), indent=1, sort_keys=True)
    stale = f"; not refreshed, because the release's block code failed here, so yours stays: {_failed(done['failed'])}" if done["failed"] else ""
    _record(s, "release", {"event": "applied", "from": running, "to": version, "back": line, "card": card["id"], "answer": d["id"], **done,
                           "wheel": verified, "sha256": r["sha256"],
                           "text": f"the tool moved from {running} to {version}{stale}"})
    print(f"applied {version}; refreshed: {', '.join(done['refreshed']) or 'none'}; held: {', '.join(done['held']) or 'none'}{stale}")
    return {"ok": True, "version": version, "back": line, **done}


def back(*, workshop, home=None, to=None, pub=PUB, env=None, shim=None):
    """back: the kept previous version reinstalled offline, its line printed and recorded first so it works by hand when the tool does not."""
    s, rel = workshop if hasattr(workshop, "lines") else _open(workshop), os.path.join(install_folder(home), "releases")
    applied = [l["body"] for l in s.lines(unit=UNIT, kinds=["release"]) if l["body"].get("event") == "applied"]
    to = to or (applied[-1]["from"] if applied else None)
    r = check(os.path.join(rel, to), pub=pub) if to else {"ok": False, "reason": "no version was applied here, so there is none to go back to"}
    if not r["ok"]:
        return {"ok": False, "none": not to, "reason": f"the kept {to or 'version'} cannot be reinstalled: {r['reason']}"}
    folder, line = bin_dir(env, shim), _line(r['wheel'], bin_dir(env, shim))
    print(line)
    _record(s, "release", {"event": "back", "from": applied[-1]["to"] if applied else None, "to": to, "line": line,
                           "text": f"going back to {to}, by this line: {line}"})
    p = _uv(r["wheel"], env, folder)
    return {"ok": p.returncode == 0, "line": line, "reason": None if p.returncode == 0 else f"uv could not reinstall {to}: {p.stderr.strip()[-400:]}"}


def main(argv):
    """update --from FILE | update --apply VERSION | back [--to VERSION], each with --workshop PATH where the install folder names none."""
    opt = lambda flag: argv[argv.index(flag) + 1] if flag in argv[:-1] else None
    pointer = os.path.join(install_folder(), "workshop")
    ws = opt("--workshop") or (open(pointer).read().strip() if os.path.exists(pointer) else None)
    if not ws or not (argv[:1] == ["back"] or opt("--from") or opt("--apply")):
        print(say("update.noworkshop") if not ws else say("cli.update.what") + "\n" + say("update.usage"), file=sys.stderr)
        return 1 if not ws else 2
    r = back(workshop=ws, to=opt("--to")) if argv[:1] == ["back"] else offer(opt("--from"), workshop=ws) if opt("--from") else apply(
        opt("--apply"), workshop=ws)
    print(say("cli.update.offered", card=r["card"], version=r["version"]) if r.get("card") else "" if r["ok"] else say("cli.back.none") if r.get("none")
          else say("cli.update.refused", why=r["reason"]))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
