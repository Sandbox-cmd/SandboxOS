# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The release, for the tool's maker: the check that refuses an unready tree, the manifest over every shipped file and the suite's
counts, the seal made with minisign over it with a key named on the command line, the wheel built with zipfile, and the pack under
dist/<version>/, checked by the update's own function before it is called done. Tagging, pushing and publishing stay the maker's hand.

    check(root) -> (results, suite)    pack(root, key=...) -> dict    make_key(folder) -> (key, pub)    main(argv)"""
import base64, collections, hashlib, json, os, re, shutil, subprocess, sys, zipfile

from sandbox_os.command import DOWN, say
from sandbox_os.command.update import order, version_of

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEYS = os.path.join(ROOT, "work", "keys")
ROOT_FILES = ("LICENSE", "BUDGETS.md", "CHANGES.md")  # the first page is the release page's, read before install; it and the contract do not ship
ENTRY = "sandbox = sandbox_os.command.cli:main"


def _run(argv, root, env=None, timeout=1800):
    return subprocess.run(argv, cwd=root, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)


def _read(root, rel):
    p = os.path.join(root, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def format_of(text):
    m = re.search(r"^FORMAT = (\d+)", text, re.M)
    return int(m.group(1)) if m else 1


def changes_for(root, version):
    """The section of CHANGES.md under the heading that names the version, or the empty string."""
    out, level = [], None
    for line in _read(root, "CHANGES.md").splitlines():
        h = re.match(r"(#+)\s", line)
        if h and level and len(h.group(1)) <= level:
            break
        if level:
            out.append(line)
        elif h and re.search(rf"(?<![\w.]){re.escape(version or '-')}(?![\w.])", line):
            level = len(h.group(1))
    return "\n".join(out).strip()


def previous_format(root, version):
    """The format named in the newest earlier release's trusted comment kept under dist/, or None when there is none."""
    d = os.path.join(root, "dist")
    older = sorted((v for v in (os.listdir(d) if os.path.isdir(d) else []) if order(v) < order(version)
                    and os.path.exists(os.path.join(d, v, "MANIFEST.minisig"))), key=order)
    m = re.search(r"^trusted comment: .* format (\d+) ", _read(d, os.path.join(older[-1], "MANIFEST.minisig")), re.M) if older else None
    return int(m.group(1)) if m else None


def _limits(text):
    rows = ([c.strip() for c in line.strip().strip("|").split("|")] for line in text.splitlines() if line.startswith("| ") and not line.startswith("| part |"))
    return {c[0]: c[3:7] for c in rows if len(c) >= 7}


def moved_limits(old, new):
    """Each part whose limit or unit moved between two BUDGETS.md texts without a dated reason (row 74): a move is named when its reason
    stayed as it was, whatever its date, or when its date went back. Two releases on one day may each move a row with a new reason."""
    a, b = _limits(old), _limits(new)
    out = []
    for p in b:
        if p not in a or a[p][:2] == b[p][:2]:
            continue
        stayed = [k for k, i in (("date", 2), ("reason", 3)) if a[p][i] == b[p][i]]
        if "reason" in stayed:  # a move with no new reason is not a dated move, whatever its date says
            out.append(f"{p}: its limit moved from {a[p][0]} to {b[p][0]} {b[p][1]} while its " + " and ".join(stayed) + " stayed the same")
        elif b[p][2] < a[p][2]:
            out.append(f"{p}: its limit moved from {a[p][0]} to {b[p][0]} {b[p][1]} while its date went back from {a[p][2]} to {b[p][2]}")
    return out


def earlier_budgets(root, version, tags, env=None):
    """BUDGETS.md as the newest tag before this version had it, else as the commit before had it; (what, text) or (None, None)."""
    for ref in [t for t in sorted(tags, key=order) if order(t) < order(version)][-1:] + ["HEAD~1"]:
        p = _run(["git", "show", f"{ref}:BUDGETS.md"], root, env)
        if p.returncode == 0:
            return ref, p.stdout
    return None, None


PROOFS = ("noncompliant-night", "read-back-corrected", "taken-back-in-flight", "ruled-not-reasked", "B1", "B2", "B3", "B4")  # stage 3's
PROOFS_11 = PROOFS + ("verb-without-proposal", "belief-without-basis", "guess-about-the-maker", "replay-calls-out",
                      "about-the-maker-outside-its-page")  # the design's five new bypasses (section 12), each its own linked green check
CRITERIA = {"10.0.0": ("R-MOVE-26", "R-MOVE-27", "R-MOVE-28"), "11.0.0": ("R-11-MAKING", "R-11-SHAPE", "R-11-MORNING")}  # making, shape, vision


def gate(lines, payload=lambda sha, unit: None, version="10.0.0"):
    """R-MOVE-29 (row 19): what 10.0.0 lacks of the criterion's three lines, in words; an empty list when nothing. Only lines that stand
    count (not struck, deleted, erased or superseded), each record once (distinct line ids), and a check only when payload(sha, unit)
    gives a file that opens and hashes as its receipt names it, never from the body alone (morning/stage-6/challenge.md, finding 1):
    - making (R-MOVE-26): a line whose body.criterion is "R-MOVE-26", linked to two tool flow lines (first_run, opened) from two
      distinct sessions (body.session), another linked line in Arabic (the walk's record) and a tool measure line m7 with opens above 0;
    - shape (R-MOVE-27): a line whose body.criterion is "R-MOVE-27" and whose body.proofs maps each of PROOFS to its own linked tool
      check that exited 0, its output kept, dated after the newest move line; and, linked beside them, such a check of the suite (tests.run);
    - a new vision (R-MOVE-28): the maker's binding yes, its words kept, from the conversation or the page at the desk, to a card the tool
      raised with purpose "new-vision" about a tool measure line carrying export_sha256 (the side-by-side measures page's).
    For 11.0.0 (batch E, Task 17; CRITERIA's names, which 10.0's never satisfy): the making leg as 10.0's under R-11-MAKING; the shape leg
    as 10.0's under R-11-SHAPE with PROOFS_11; the vision R-11-MORNING: his newest binding answer (cards.decision's rule) a yes in his words,
    from the conversation or the page at the desk, to the tool's card the-morning about a tool note of event the-morning, and a standing
    tool note of that event with ok true read from the same sentence (the outcome's, tests/move/outcome.py); and, since row 39 rests his
    word on two lines (Astra's challenge of batch E, finding 9), the same yes to the tool's card the-measures about a tool note of event
    the-measures over four weeks, the first month's measures side by side (outcome.measures). Each missing judgment is named apart. Only the
    newest standing reading counts (finding 10): a sentence's newest morning note must be green and its card about a note of that sentence,
    and his yes must be to the card about the newest measures note."""
    from types import SimpleNamespace
    from sandbox_os.command.cards import binds, decision
    L, near = {l["id"]: dict(l, mark=l.get("mark")) for l in lines if l.get("mark") not in DOWN}, collections.defaultdict(dict)
    for b in [l["body"] for l in L.values() if l["kind"] == "link" and l["body"].get("from") in L and l["body"].get("to") in L]:
        near[b["from"]][b["to"]], near[b["to"]][b["from"]] = L[b["to"]], L[b["from"]]
    moved = max([l["t"] for l in L.values() if l["kind"] == "move"] or [""])
    tool = lambda x, k, **b: x["kind"] == k and x["by"]["kind"] == "tool" and all(x["body"].get(f) == v for f, v in b.items())  # noqa: E731

    def green(x, suite=False):
        out = x["body"].get("output") if isinstance(x["body"].get("output"), dict) else {}
        p = isinstance(out.get("payload"), str) and payload(out["payload"], x.get("unit"))
        kept = bool(p) and hashlib.sha256(open(p, "rb").read()).hexdigest() == out["payload"]
        return tool(x, "check", exit=0) and x["t"] > moved and kept and suite == ("tests.run" in str(x["body"].get("command")))

    def making(n):
        runs = {x["body"]["session"]: i for i, x in n.items() if tool(x, "flow", step="first_run", event="opened") and x["body"].get("session")}
        m7 = any(tool(x, "measure", measure="m7") and type(o := (x["body"].get("counts") or {}).get("opens")) is int and o > 0 for x in n.values())
        return ([] if len(runs) >= 2 else ["two first runs from two distinct sessions"]) + ([] if any(
            x.get("lang") == "ar" and i not in list(runs.values())[:2] for i, x in n.items()) else ["the Arabic walk's record"]) + ([] if m7 else ["an M7 line with a logged open"])

    def shape(n, proofs):
        names = PROOFS_11 if version == "11.0.0" else PROOFS
        ids = [proofs.get(k) for k in names]
        lack = [k for k, i in zip(names, ids) if not (i in n and ids.count(i) == 1 and green(n[i]))]
        return lack + ([] if any(green(x, suite=True) and i not in ids for i, x in n.items()) else ["the suite green since the move"])
    out, (made, shaped, seen) = [], CRITERIA[version]
    for rid, what, of in ((made, "making", lambda l: making(near[l["id"]])), (shaped, "shape", lambda l: shape(near[l["id"]], l["body"].get("proofs") or {}))):
        lacks = min((of(l) for l in L.values() if l["body"].get("criterion") == rid), key=len, default=None)
        out += [] if lacks == [] else [f"{rid}, {what}: " + ("no such line" if lacks is None else "its links lack " + ", ".join(lacks))]
    if version != "10.0.0":
        new = lambda e: sorted((x for x in L.values() if tool(x, "note", event=e)), key=lambda x: (x["t"], x.get("seq") or 0))  # noqa: E731
        notes, last = {x["id"]: x["body"] for x in new("the-morning")}, {x["body"].get("said"): x["body"] for x in new("the-morning")}
        read = {s for s, b in last.items() if b.get("ok") is True}  # the sentences whose newest reading has all six legs green (Astra E, 10)
        asked = [i for i, x in L.items() if tool(x, "card", purpose="the-morning") and x["body"].get("said") in read
                 and (notes.get(x["body"].get("about")) or {}).get("said") == x["body"].get("said")]
        month = {x["id"] for x in new("the-measures")[-1:] if len(x["body"].get("weeks") or []) == 4}  # the newest, over four weeks (9, 10)
        d = lambda cs: [decision(SimpleNamespace(lines=lambda kinds: [a for a in L.values() if a["kind"] in kinds]), c) for c in cs]  # noqa: E731
        said = lambda cs: [a for a in d(cs) if a and a["body"].get("answer") == "yes" and str(a["body"].get("words") or "").strip() and (  # noqa: E731
            a["body"].get("from") == "conversation" or (a["body"].get("from"), a["body"].get("presence")) == ("page", "desk"))]
        meant = [i for i, x in L.items() if tool(x, "card", purpose="the-measures") and x["body"].get("about") in month]
        return out + ([] if said(asked) else [say("release.gate.morning", rid=seen)]) + (
            [] if said(meant) else [say("release.gate.measures", rid=seen)])
    page = {i for i, x in L.items() if tool(x, "measure") and x["body"].get("export_sha256")}
    asked = {i for i, x in L.items() if tool(x, "card", purpose="new-vision") and x["body"].get("about") in page}
    said = [a for a in L.values() if a["kind"] == "answer" and a["body"].get("card") in asked and binds(a) and a["body"].get("answer") == "yes"
            and str(a["body"].get("words") or "").strip() and (a["body"].get("from") == "conversation" or (a["body"].get("from"), a["body"].get("presence")) == ("page", "desk"))]
    return out + ([] if said else ["R-MOVE-28, a new vision: no answer to the new-vision card"])


def gate_lines(env, path):
    """The lines the gate reads, where from, and how it opens their payloads: the file the maker names (JSON lines, its payloads in a
    payloads/ folder beside it), else the workshop the tool points at, read-only."""
    from sandbox_os import store
    from sandbox_os.command.cli import INSTALL, pointer
    ws = None if path else pointer(os.path.join((env or os.environ).get("HOME", ""), *INSTALL))
    beside = lambda sha, unit: (p if re.fullmatch(r"[0-9a-f]{64}", sha) and os.path.isfile(p := os.path.join(os.path.dirname(os.path.abspath(path)), "payloads", sha))
                                else None)  # noqa: E731
    try:
        if path or not (ws and os.path.isfile(os.path.join(ws, "home.json"))):
            return ([json.loads(x) for x in _read("", path).splitlines() if x.strip()], path, beside) if path else ([], "nowhere: no workshop, no --criterion file", beside)
        s = store.open(ws, read_only=True)
        return s.lines(), ws, lambda sha, unit: s.payload_path(sha, unit=unit)
    except (ValueError, KeyError) as e:
        return [], f"{path or ws}, which could not be read ({e})", beside


def check(root, *, env=None, criterion=None):
    """Every condition of the release check, each with its reason; and what the suite said (its output and summary). Each version CRITERIA
    names (10.0.0, 11.0.0) adds its criterion (R-MOVE-29, R-MOVE-47), read from the file named by criterion or else from the workshop the
    tool points at; a pre-release does not."""
    from sandbox_os.command import licence
    v, out = version_of(_read(root, "sandbox_os/__init__.py")), []
    add = lambda name, ok, yes, no: out.append({"name": name, "ok": bool(ok), "detail": yes if ok else no})
    st = _run(["git", "status", "--porcelain"], root, env)
    dirty = [x[3:] for x in st.stdout.splitlines() if not x[3:].startswith("dist/")]
    add("committed", st.returncode == 0 and not dirty, "the tree is committed but for dist/",
        f"not committed: {', '.join(dirty[:6]) or st.stderr.strip()}" + (f" and {len(dirty) - 6} more" if len(dirty) > 6 else ""))
    try:  # the suite's own clock: the 11.0.0a5 pack's run took 1,533 seconds; every other call keeps _run's 1,800
        p = _run([sys.executable, "-m", "tests.run"], root, env, timeout=3600)
    except subprocess.TimeoutExpired as e:  # a stopped suite is a failing result in one sentence, never a traceback
        kept = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else e.stdout or ""
        p = subprocess.CompletedProcess(e.cmd, None, f"{kept}\nthe full suite did not finish in {e.timeout:,} seconds and was stopped, so it has not passed\n", "")
    tail = [x for x in p.stdout.splitlines() if x.strip()][-1:] or [""]
    try:
        summary = json.loads(tail[0])
    except ValueError:
        summary = {}
    suite = {"output": p.stdout + p.stderr, "summary": dict(summary, exit=p.returncode, command="python3 -m tests.run", stdin="/dev/null")}
    add("suite", p.returncode == 0, f"the full suite passed with standard input closed: {tail[0]}",
        tail[0] if p.returncode is None else f"the full suite exited {p.returncode}: {tail[0]}")
    b, tags = _run([sys.executable, "-m", "unittest", "-q", "tests.test_budgets"], root, env), _run(["git", "tag"], root, env).stdout.split()
    ref, before = earlier_budgets(root, v, tags, env)
    moved = moved_limits(before, _read(root, "BUDGETS.md")) if ref else []
    add("budgets", b.returncode == 0 and not moved, "the budgets test passes; " + (f"no limit moved without its date and reason since {ref}" if ref
        else "no earlier BUDGETS.md to compare (no earlier tag, no commit before)"), "; ".join(
        (["the budgets test fails: " + " | ".join((b.stdout + b.stderr).strip().splitlines()[-6:])] if b.returncode else []) + [f"since {ref}, {m}" for m in moved]))
    problems = licence.licence_file(root) + licence.headers(os.path.join(root, "sandbox_os")) + licence.no_other_grant(root) + licence.first_page(root)
    add("licence", not problems, "the licence file, the headers, no other grant and the first page's words hold",
        "; ".join(problems[:6]) + (f"; and {len(problems) - 6} more" if len(problems) > 6 else ""))
    add("version", v and v not in tags, f"{v} is no existing tag", f"{v} is already a tag" if v else "no VERSION in sandbox_os/__init__.py")
    fmt, prev, section = format_of(_read(root, "sandbox_os/store/__init__.py")), previous_format(root, v), changes_for(root, v)
    add("format", prev in (None, fmt) or re.search(r"(?i)\bmigration\b", section), f"format {fmt}" + (f", migration named" if prev not in (None, fmt) else
        ", unchanged" if prev else ", no earlier release kept to compare"), f"the format moved from {prev} to {fmt} and CHANGES.md names no migration for {v}")
    add("changes", section, f"CHANGES.md names {v}", f"CHANGES.md names no {v} under a heading")
    if v == "10.0.0":
        lines, src, payload = gate_lines(env, criterion)
        miss = gate(lines, payload)
        add("criterion", not miss, say("release.ten.ok", src=src), say("release.ten.no", src=src, miss="; ".join(miss)))
    elif v in CRITERIA:  # 11.0.0 (batch E, Task 17): its own three lines, in the strings table's words
        lines, src, payload = gate_lines(env, criterion)
        miss = gate(lines, payload, version=v)
        add("criterion", not miss, say("release.criterion.ok", version=v, src=src), say("release.criterion.no", version=v, src=src, miss="; ".join(miss)))
    return out, suite


def shipped(root):
    """Every file the release carries, by its path in the manifest (relative to the installed sandbox_os/ folder), with its bytes."""
    out, pkg = {}, os.path.join(root, "sandbox_os")
    for d, dirs, fs in os.walk(pkg):
        dirs[:] = sorted(x for x in dirs if x != "__pycache__")
        for f in fs:
            if not f.endswith(".pyc") and f not in (".DS_Store", "MANIFEST", "MANIFEST.minisig"):
                out[os.path.relpath(os.path.join(d, f), pkg)] = open(os.path.join(d, f), "rb").read()
    return out | {n: open(os.path.join(root, n), "rb").read() for n in ROOT_FILES if os.path.exists(os.path.join(root, n))}


def _b64(data):
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def build_wheel(files, manifest, sig, version, folder):
    """The wheel with zipfile: the package under sandbox_os/, its manifest and seal beside it, the dist-info, and RECORD last."""
    members = {os.path.normpath(os.path.join("sandbox_os", p)): data for p, data in files.items()}
    members |= {"sandbox_os/MANIFEST": manifest, "sandbox_os/MANIFEST.minisig": sig}
    record = f"sandbox_os-{version}.dist-info/RECORD"
    rows = [f"{n},sha256={_b64(d)},{len(d)}" for n, d in sorted(members.items())] + [f"{record},,"]
    path = os.path.join(folder, f"sandbox_os-{version}-py3-none-any.whl")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in sorted(members.items(), key=lambda x: (".dist-info/" in x[0], x[0])) + [(record, "\n".join(rows).encode() + b"\n")]:
            info = zipfile.ZipInfo(n, date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr, info.compress_type = 0o644 << 16, zipfile.ZIP_DEFLATED
            z.writestr(info, d)
    return path


def dist_info(version):
    meta = (f"Metadata-Version: 2.1\nName: sandbox-os\nVersion: {version}\nSummary: A workshop on your own machine, worked with an AI partner in "
            "your terminal.\nLicense: LicenseRef-Winktank-Person-1.0\nRequires-Python: >=3.14\n")
    info = f"../sandbox_os-{version}.dist-info/"
    return {info + "METADATA": meta.encode(), info + "WHEEL": b"Wheel-Version: 1.0\nGenerator: sandbox-os release.py\nRoot-Is-Purelib: true\n"
            b"Tag: py3-none-any\n", info + "entry_points.txt": f"[console_scripts]\n{ENTRY}\n".encode()}


def pack(root, *, key, unchecked=False, env=None, criterion=None):
    """Checks the tree, then packs dist/<version>/: the wheel, MANIFEST, its seal, and beside them the suite's printout, unshipped. Refused, nothing is written;
    with unchecked (the orchestrator's, while a tree is mid-build) every check still runs and a line of its own names each one let through."""
    from sandbox_os.command import seal, update
    v, pub = version_of(_read(root, "sandbox_os/__init__.py")), os.path.join(root, "sandbox_os", "command", "release.pub")
    try:
        same = seal.public(pub)[0] == seal.public(os.path.splitext(key)[0] + ".pub")[0] and os.path.exists(key)
    except (OSError, ValueError, IndexError):
        same = False
    if not same:
        return {"ok": False, "reason": f"the key that would seal ({key}) is not the key the tool ships (sandbox_os/command/release.pub); nothing was packed"}
    results, suite = check(root, env=env, criterion=criterion)
    failed = [r["name"] for r in results if not r["ok"]]
    if failed and not unchecked:
        return {"ok": False, "refused": failed, "results": results, "reason": "the release check refused: " + "; ".join(
            f"{r['name']}: {r['detail']}" for r in results if not r["ok"])}
    head = _run(["git", "rev-parse", "--short", "HEAD"], root, env).stdout.strip() or "none"
    dirty = [r for r in results if r["name"] == "committed" and not r["ok"]]
    comment = f"sandbox-os {v} format {format_of(_read(root, 'sandbox_os/store/__init__.py'))} commit {head}{'-dirty' if dirty else ''}"
    checks = "".join(f"{'pass' if r['ok'] else 'FAIL'}: {r['name']}: {r['detail']}\n" for r in results) + (say("release.unchecked", failed=", ".join(failed)) + "\n" if failed else "")
    files = shipped(root) | dist_info(v) | {"suite-summary.json": json.dumps(suite["summary"], indent=1).encode() + b"\n",
                                            "release-checks.txt": checks.encode()}  # the counts ship; the suite's printout stays beside the wheel
    manifest = "".join(f"{hashlib.sha256(files[p]).hexdigest()}  {p}\n" for p in sorted(files)).encode()
    folder = os.path.join(root, "dist", v)
    shutil.rmtree(folder, ignore_errors=True)
    os.makedirs(folder)
    with open(os.path.join(folder, "MANIFEST"), "wb") as f:
        f.write(manifest)
    s = _run(["minisign", "-S", "-H", "-s", key, "-m", os.path.join(folder, "MANIFEST"), "-x", os.path.join(folder, "MANIFEST.minisig"),
              "-t", comment], root, env, timeout=60)
    if s.returncode:
        shutil.rmtree(folder)
        return {"ok": False, "reason": f"minisign could not seal: {s.stderr.strip()}"}
    wheel = build_wheel(files, manifest, open(os.path.join(folder, "MANIFEST.minisig"), "rb").read(), v, folder)
    for n, data in (("suite-output.txt", suite["output"].encode()), *((n, files[n]) for n in ("suite-summary.json", "release-checks.txt"))):
        with open(os.path.join(folder, n), "wb") as f:
            f.write(data)
    tags = sorted((t for t in _run(["git", "tag"], root, env).stdout.split() if order(t) < order(v)), key=order)
    r = update.check(folder, pub=pub, running=tags[-1] if tags else None)
    if not r["ok"]:
        shutil.rmtree(folder)
        return {"ok": False, "reason": f"the packed release failed the update's own check: {r['reason']}"}
    return {"ok": True, "folder": folder, "wheel": wheel, "version": v, "comment": comment, "unchecked": failed, "results": results,
            "checked_by_update": True, "key_id": r["key_id"]}


def make_key(folder=KEYS, *, env=None):
    """The release key made with minisign, unencrypted, inside the folder named, when it is absent; an existing key is never replaced."""
    key, pub = os.path.join(folder, "sandbox-os.key"), os.path.join(folder, "sandbox-os.pub")
    if os.path.exists(key) and os.path.exists(pub):
        return key, pub
    if os.path.exists(key) or os.path.exists(pub):
        raise FileExistsError(f"half a key pair in {folder}; nothing was made")
    os.makedirs(folder, exist_ok=True)
    p = _run(["minisign", "-G", "-W", "-f", "-p", pub, "-s", key], folder, env, timeout=60)
    if p.returncode:
        raise RuntimeError(f"minisign could not make a key: {p.stderr.strip()}")
    return key, pub


def main(argv):
    """release --check | release --pack [--unchecked] [--key FILE]: the tool's maker's verb, run from the tree; the key defaults to one made
    under work/keys/ when absent, its public half shipped as sandbox_os/command/release.pub when that is absent."""
    crit = argv[argv.index("--criterion") + 1] if "--criterion" in argv[:-1] else None
    if argv[:1] not in (["--check"], ["--pack"]) or {a for a in argv if a.startswith("--")} - {"--check", "--pack", "--unchecked", "--key", "--criterion"} or (
            "--criterion" in argv and not crit):
        print("usage: release --check | release --pack [--unchecked] [--key FILE] [--criterion FILE]", file=sys.stderr)
        return 2
    key, pub = argv[argv.index("--key") + 1] if "--key" in argv[:-1] else None, os.path.join(ROOT, "sandbox_os", "command", "release.pub")
    if argv[0] == "--pack" and not key:
        key = make_key()[0]
        if not os.path.exists(pub):
            shutil.copyfile(os.path.splitext(key)[0] + ".pub", pub)
            print(f"wrote {pub}: the public half of {key}, shipped inside the tool")
    r = pack(ROOT, key=key, unchecked="--unchecked" in argv, criterion=crit) if argv[0] == "--pack" else dict(zip(("results", "suite"), check(ROOT, criterion=crit)))
    print("\n".join(f"{'pass' if x['ok'] else 'FAIL'}: {x['name']}: {x['detail']}" for x in r.get("results", [])))
    if argv[0] == "--check":
        return 0 if all(x["ok"] for x in r["results"]) else 1
    print(say("release.packed", folder=r["folder"], wheel=os.path.basename(r["wheel"]), comment=r["comment"])
          + (f"; unchecked: {', '.join(r['unchecked'])}" if r["unchecked"] else "") if r["ok"] else f"refused: {r['reason']}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
