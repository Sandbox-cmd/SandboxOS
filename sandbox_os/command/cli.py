# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The verbs a maker types (R-CMD-21, 22): sandbox (the welcome where it stopped, or the pages), stop, doctor, update, back, secret,
remove, the five that take something back (delete, undelete, snapshot, copy, restore), move (one stream of the move) and release; hook and mcp routed for the hosts. Every verb counts the files it wrote and the lines it recorded in one sentence,
in the strings table's English, and exits 0 done, 1 refused with the reason, 2 misused. The pages run in a child process that holds a
lock file in the install folder while it lives; stop ends it, and nothing else is ever signalled."""
import contextlib, fcntl, importlib, json, os, re, shutil, signal, subprocess, sys, time

from sandbox_os import VERSION
from sandbox_os.command import say, words

VERBS = ("stop", "doctor", "update", "back", "secret", "remove", "delete", "undelete", "snapshot", "copy", "restore", "move", "release")
INSTALL = (".local", "share", "sandbox-os")
SKIP = ("cache/index-2.sqlite", "cache/record.lock")  # rebuilt on demand and touched by every read: never named
CHILD = ("import fcntl, signal, sys; lock = open(sys.argv[2], 'a'); fcntl.flock(lock, fcntl.LOCK_EX); "
         "signal.signal(signal.SIGTERM, signal.default_int_handler); from sandbox_os import pages; pages.serve(sys.argv[1], background=False)")


def ask(prompt):
    """A question on its own line, the answer from standard input; a closed input is a quit."""
    print(prompt, flush=True)
    line = sys.stdin.readline()
    if not line:
        raise EOFError
    return line.rstrip("\n")


def pointer(inst):
    p = os.path.join(inst, "workshop")
    return (open(p).read().strip() or None) if os.path.exists(p) else None


def _snap(roots):
    out = {}
    for r in roots:
        for d, _, fs in os.walk(r):
            for f in fs:
                p = os.path.join(d, f)
                if not any(s in p for s in SKIP):
                    st = os.lstat(p)
                    out[p] = (st.st_size, st.st_mtime_ns)
    return out


def _ids(ws):
    from sandbox_os import store as _store
    try:
        return {l["id"]: l for l in _store.open(ws, read_only=True, machine="cli").lines()} if ws and os.path.exists(os.path.join(ws, "home.json")) else {}
    except Exception:
        return {}


def _place(p, inst, roots, books):
    """Where a file is, by name: the tool's own folder, a project by the maker's words for it, else the workshop (Codex's finding 14)."""
    r = max((r for r in roots if p.startswith(r + os.sep)), key=len)
    parts = os.path.relpath(p, r).split(os.sep)
    unit = parts[1] if r != inst and parts[0] == "projects" and len(parts) > 2 and parts[1] != "workshop" else None
    made = [b.get("words") for b in (l["body"] or {} for l in books.get(r, {}).values() if l["unit"] == unit) if b.get("event") == "project-made"]
    return (0, say("cli.where.tool")) if r == inst else (2, say("cli.where.project", name=made[0] or unit)) if made else (1, say("cli.where.workshop"))


def _and(ts):
    return " and ".join([", ".join(ts[:-1]), ts[-1]] if len(ts) > 2 else ts)


@contextlib.contextmanager
def named(inst, extra=None, kinds=False):
    """Once the verb ends, one sentence counts the files written under the install folder and the workshop, and the lines recorded, and
    says where they are, by name; one more counts the files removed (a line per file and per line read as noise: the reading, R-READ-11).
    The lines counted are those each workshop gained during the verb, so a switch between two workshops records none (Codex's 11). With
    kinds, a welcome already done (sandbox only starting the pages) says its lines by their kinds (batch G, R-DESIGN-23)."""
    roots = {r for r in (inst, pointer(inst), extra) if r}
    words()  # loaded before the verb runs: an update swaps the tool's files, and the closing sentence loads none of the new ones
    before, ids = _snap(roots), {r: _ids(r) for r in roots - {inst}}
    kinds = kinds and any(l["kind"] == "flow" and (l["body"] or {}).get("step") == "flow" for b in ids.values() for l in b.values())
    try:
        yield
    finally:
        roots.add(pointer(inst) or inst)
        after, books = _snap(roots), {r: _ids(r) for r in roots - {inst}}
        new = [l for r, b in books.items() for i, l in b.items() if i not in ids.get(r, {})]
        wrote, gone = [p for p in after if before.get(p) != after[p]], [p for p in before if p not in after]
        where = lambda ps: _and([t for _, t in sorted({_place(p, inst, roots, books) for p in ps})])
        n, what = words().count, _and(sorted({say("kind." + l["kind"]) for l in new})) if kinds else ""
        print(say(("cli.recorded.what" if kinds else "cli.recorded") if new else "cli.wrote", files=n("file", len(wrote)), lines=n("line", len(new)),
                  where=where(wrote), kinds=what)) if wrote or new else None
        print(say("cli.removed", files=n("file", len(gone)), where=where(gone))) if gone else None


def _held(lock):
    """Whether the pages' child, which takes this lock before it serves and holds it while it lives, is still alive."""
    if not os.path.exists(lock):
        return False
    with open(lock, "a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(f, fcntl.LOCK_UN)
    return False


def stop(inst, quiet=False):
    p, lock = os.path.join(inst, "pages.json"), os.path.join(inst, "pages.lock")
    info = json.load(open(p)) if os.path.exists(p) else None
    if info and _held(lock):
        os.kill(info["pid"], signal.SIGTERM)
        end = time.time() + 10
        while _held(lock) and time.time() < end:
            time.sleep(0.05)
    for f in (p, lock):
        os.remove(f) if os.path.exists(f) else None
    if not quiet:
        print(say("cli.stopped", address=info["address"]) if info else say("cli.nopages"))
    return 0


def weeks(ws, quiet=False):
    """measures.catch_up before the pages or the doctor; a record taking no writes here (a copy, a held lock) is said so, in one line (the
    doctor says it once, for its own line); any other refusal is said in the store's words, never as a record taking no writes (the review
    of batch D, finding 2)."""
    if ws and os.path.isfile(os.path.join(ws, "home.json")):
        from sandbox_os import store as _store
        from sandbox_os.command import measures
        s = None
        try:
            s = _store.open(ws)
            measures.catch_up(s)
        except _store.Busy:
            quiet or print(say("cli.readonly"), flush=True)
        except _store.Refused as e:  # the read-only line only for a record that takes no writes here; any other refusal in its own words
            if s is not None and s.away:
                quiet or print(say("cli.readonly"), flush=True)
            else:
                print(say("cli.weekrefused", why=str(e)), flush=True)


def pages(inst, root):
    """Starts the pages for a workshop in a child of their own (any earlier ones stopped first) and returns the one-time desk link."""
    stop(inst, quiet=True)
    weeks(root)
    os.makedirs(inst, exist_ok=True)
    child = subprocess.Popen([sys.executable, "-u", "-c", CHILD, root, os.path.join(inst, "pages.lock")], stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True, text=True)
    first = child.stdout.readline()
    child.stdout.close()
    m = re.search(r"(http://127\.0\.0\.1:\d+)/desk/[\w-]+", first)
    if not m:
        raise RuntimeError(say("cli.pagesfailed", why=first.strip() or f"exit {child.poll()}"))
    with open(os.path.join(inst, "pages.json"), "w") as f:
        json.dump({"pid": child.pid, "address": m.group(1), "workshop": root}, f)
    return m.group(0)


def usage():
    print(say("cli.help.head", version=VERSION))
    for v in ("sandbox",) + VERBS[:-2]:  # a person's; move (the maker's census only) is left out, and release, the tool's maker's, is in the closing line
        print("  " + say("cli.help." + v))
    print(say("cli.help.hosts"))
    return 0


def misused(what):
    print(say("cli.misused", what=what), file=sys.stderr)
    return 2


def delegated(verb, argv, inst):
    """doctor, update, back and release are the release builder's modules, imported only when typed, given the workshop this tool points at."""
    name = {"doctor": "selfcheck", "back": "update"}.get(verb, verb)
    try:
        mod = importlib.import_module("sandbox_os.command." + name)
    except ImportError as e:
        print(say("cli.notbuilt", verb=verb, why=str(e)))
        return 1
    ws = pointer(inst)
    rest = argv[1:] + (["--workshop", ws] if ws and verb != "release" and "--workshop" not in argv else [])
    if verb == "doctor":
        weeks(argv[argv.index("--workshop") + 1] if "--workshop" in argv[:-1] else ws, quiet=True)
    r = mod.main(rest if verb in ("doctor", "release") else [verb] + rest)
    return r if isinstance(r, int) else 0


def main(argv=None, env=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    env = os.environ if env is None else env
    home, path = env.get("HOME") or "", env.get("PATH") or ""
    inst = os.path.join(home, *INSTALL)
    verb = argv[0] if argv else None
    if verb in ("--help", "-h", "help"):
        return usage()
    if verb == "--version":
        return print(say("cli.version", version=VERSION)) or 0
    if verb == "hook" and len(argv) == 2:  # the boundary records; the command binds a maker's answer; exit 0, nothing printed
        from sandbox_os.command import hook
        hook.main(argv[1])
    if verb == "hook":  # with no host's name, or more than one
        return print(say("cli.hook.nohost"), file=sys.stderr) or 2
    if verb == "mcp":  # the partner's tools for a host: the workshop named, else the one this tool points at; nothing but JSON-RPC once served
        ws = argv[argv.index("--workshop") + 1] if "--workshop" in argv[:-1] else pointer(inst)
        if not ws or not os.path.isfile(os.path.join(ws, "home.json")):
            return print(say("cli.mcp")) or 1
        from sandbox_os.command import mcp
        return mcp.main(["--workshop", ws])
    if verb is not None and not verb.startswith("-") and verb not in VERBS:
        return misused(verb)
    if verb in VERBS:
        with named(inst):
            if verb == "stop":
                return stop(inst)
            if verb in ("secret",) + VERBS[6:12]:  # secret, the five that take something back (cards 32 and 43) and the move (card 52)
                mod = importlib.import_module("sandbox_os.command." + {"secret": "secret", "move": "moving"}.get(verb, "takeback"))
                return mod.main(argv[1:] if verb == "secret" else argv, workshop=pointer(inst))
            if verb == "remove":
                ws = pointer(inst)
                stop(inst, quiet=True)
                shutil.rmtree(inst, ignore_errors=True)
                print(say("cli.remove.kept", path=ws)) if ws else None
                return print(say("cli.remove.line")) or 0
            return delegated(verb, argv, inst)
    opts, rest = {"--terminal": False, "--no-browser": False, "--workshop": None}, list(argv)
    while rest:
        a = rest.pop(0)
        if a == "--workshop" and rest:
            opts[a] = os.path.abspath(rest.pop(0))
        elif a in ("--terminal", "--no-browser"):
            opts[a] = True
        else:
            return misused(a)
    from sandbox_os.command import flow
    with named(inst, opts["--workshop"], kinds=True):
        try:
            return flow.run(home, path_env=path, ask=ask, out=lambda t="": print(t, flush=True), terminal=opts["--terminal"], folder=opts["--workshop"],
                            serve=lambda root: pages(inst, root))
        except KeyboardInterrupt:
            return print(say("cli.interrupted")) or 1
        except RuntimeError as e:
            print(str(e)) if str(e) else None
            return 1
