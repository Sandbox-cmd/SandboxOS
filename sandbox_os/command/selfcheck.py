# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The shipped self-check and doctor. The self-check checks four things: the seal (every installed file against MANIFEST, nothing
unlisted, the seal itself against the key the tool holds), the budgets file against the installed tree, every view file of the workshop
opening from its file, and the store reading back (a scratch round trip, then a read-only pass over the maker's record). It writes one
check line by the tool with its output kept beside it. doctor runs it first, then names the workshop's health, each fault with its fix
in one line and none made, and writes one line.

    run(tree, workshop=None) -> dict    seal(tree, pub=None) -> dict    doctor(workshop) -> dict    main(argv)"""
import glob, hashlib, html.parser, importlib.util, json, os, re, shutil, sys, tempfile, time, urllib.parse

from sandbox_os import VERSION, store as _store
from sandbox_os.command import TOOL, counted, say, seal as _seal

TREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWN = {"LICENSE", "BUDGETS.md", "CHANGES.md", "suite-summary.json", "release-checks.txt", "MANIFEST", "MANIFEST.minisig"}
INSTALL = os.path.join(os.path.expanduser("~"), ".local", "share", "sandbox-os")


def _c(name, why, good, fix=None):
    """A check's result: red with its reasons when there are any, else green with what it saw; a health item carries its fix."""
    out = {"name": name, "ok": not why, "detail": "; ".join(why) or good}
    return out if fix is None else {"what": out.pop("name"), **out, "fix": fix}


def _five(xs):  # a list of files in a detail: five named, the rest counted
    return ", ".join(xs[:5]) + (f" and {len(xs) - 5} more" if len(xs) > 5 else "")


def _files(tree):
    for d, dirs, fs in os.walk(tree):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        yield from (os.path.relpath(os.path.join(d, f), tree) for f in fs if not f.endswith(".pyc"))


def _compiled_matches(pyc, src):
    """A compiled file's header read against its source: the source's size (bytes 12 to 16) in a timestamp header, the source's own hash
    (bytes 8 to 16) in a hash-based one. Python runs a compiled file in place of its source when its header matches."""
    head, body = open(pyc, "rb").read(16), open(src, "rb").read()
    if len(head) < 16:
        return False
    if int.from_bytes(head[4:8], "little") & 1:
        return head[8:16] == importlib.util.source_hash(body)
    return int.from_bytes(head[12:16], "little") == len(body) & 0xFFFFFFFF


def seal(tree, pub=None):
    """Every installed file against MANIFEST, nothing unlisted beside them, and the seal over MANIFEST against the key held."""
    man = os.path.join(tree, "MANIFEST")
    s = _seal.verify(man, man + ".minisig", pub or os.path.join(tree, "command", "release.pub")) if os.path.exists(man) else None
    if not (s and s["ok"]):
        return _c("seal", [f"the seal over MANIFEST: {s['reason']}" if s else "no MANIFEST beside the installed files: this tree is not a sealed release"], "")
    rows = [(r[:64], r[66:]) for r in open(man, encoding="utf-8").read().splitlines()]
    bad = [rel for h, rel in rows if not os.path.isfile(os.path.join(tree, rel)) or hashlib.sha256(open(os.path.join(tree, rel), "rb").read()).hexdigest() != h]
    listed = {os.path.normpath(rel) for _, rel in rows} | {"MANIFEST", "MANIFEST.minisig"}
    cache = lambda rel: re.fullmatch(r"(.*/)?__pycache__/([^/.]+)\.[^/]+\.pyc", rel)  # the interpreter's own, beside a listed source of its name
    every = sorted(os.path.relpath(os.path.join(d, f), tree) for d, _, fs in os.walk(tree) for f in fs)
    compiled = {rel: f"{m[1] or ''}{m[2]}.py" for rel in every if rel not in listed and (m := cache(rel)) and f"{m[1] or ''}{m[2]}.py" in listed}
    extra = [rel for rel in every if rel not in listed and rel not in compiled]
    forged = [rel for rel, src in compiled.items() if not _compiled_matches(os.path.join(tree, rel), os.path.join(tree, src))]
    why = ([f"differs from the seal: {_five(bad)}"] if bad else []) + ([f"unlisted: {_five(extra)}"] if extra else [])
    why += [f"a compiled file that does not match its source: {_five(forged)}"] if forged else []
    n = len(compiled)
    note = (f"{n} compiled file beside its listed source" if n == 1 else f"{n} compiled files beside their listed sources") + ", " + say("health.seal.compiled")
    return {"name": "seal", "ok": not why, "detail": "; ".join(why or [f"{len(rows)} files match the MANIFEST sealed by key {s['key_id']}, nothing unlisted"])
            + f"; {note}"}


def _matches(path, pattern):
    return re.fullmatch(re.escape(pattern).replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*").replace(r"\*", "[^/]*"), path) is not None


def budgets(tree):
    """BUDGETS.md read as the budgets test reads it, counted over the installed tree: a part over its limit or a file of no part is red."""
    p = os.path.join(tree, "BUDGETS.md")
    text = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    rows = [(c[0], [x.strip("` ") for x in c[2].split(",")], c[3].replace(",", ""), c[4]) for c in
            ([x.strip() for x in line.strip().strip("|").split("|")] for line in text.splitlines() if line.startswith("| ") and not line.startswith("| part |"))
            if len(c) >= 7]
    m = re.search(r"Excluded from every count and measured apart, by name: (.*?)\.\s", text, re.S)
    excluded, count, orphans = [x.strip("` ") for x in m.group(1).split(",")] if m else [], {}, []
    for rel in sorted(set(_files(tree)) - OWN):
        path = "sandbox_os/" + rel
        part = None if any(_matches(path, e) for e in excluded) else next((r for r in rows if any(_matches(path, g) for g in r[1])), False)
        if part is False:
            orphans.append(rel)
        elif part:
            t = open(os.path.join(tree, rel), encoding="utf-8", errors="replace").read()
            key = f"{part[0]} ({rel})" if part[3].endswith("each") else part[0]
            count[key] = (count.get(key, (0,))[0] + (len(t.split()) if part[3].startswith("word") else t.count("\n")), part)
    over = [f"{k}: {n} {r[3].replace(' each', '')}, limit {r[2]}" for k, (n, r) in sorted(count.items()) if r[2].isdigit() and n > int(r[2])]
    return _c("budgets", ["no BUDGETS.md in the installed tree"] * (not text) + ([f"over: {'; '.join(over)}"] if over else [])
              + ([f"in no part: {_five(orphans)}"] if orphans else []), f"{len(rows)} parts read from BUDGETS.md, each within its limit")


class _View(html.parser.HTMLParser):
    """A written view read whole: its title, classes, links, the text of each part's label, and which of its blocks were left open."""
    def __init__(self, path):
        super().__init__()
        self.titles, self.classes, self.hrefs, self.marks, self.open, self.labels, self.depth, self.sections = 0, [], [], set(), [], [], 0, 0
        self.head = False  # a page's title is the <title> inside <head>; a drawing's own <title> (the world graph's) is never there
        self.text = open(path, encoding="utf-8", errors="replace").read()
        self.feed(self.text)
        self.close()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.head = tag == "head" or (self.head and tag != "body")
        self.titles, self.classes, self.hrefs = self.titles + (tag == "title" and self.head), self.classes + (a.get("class") or "").split(), self.hrefs + [a.get("href")]
        self.marks |= {a.get("data-s"), f"view={a.get('data-view')}"}
        self.sections += tag == "section" and "part" in (a.get("class") or "").split()
        self.open += [tag] if tag in ("html", "head", "body", "script", "style") or (tag == "title" and self.head) else []
        if tag == "div" and (self.depth or "label" in (a.get("class") or "").split()):
            self.labels += [""] * (not self.depth)
            self.depth += 1

    def handle_endtag(self, tag):
        self.head = self.head and tag != "head"
        if tag in self.open:
            del self.open[len(self.open) - 1 - self.open[::-1].index(tag)]
        self.depth -= tag == "div" and self.depth > 0

    def handle_data(self, data):
        if self.depth:
            self.labels[-1] += data.strip()


def views(root):
    """Every view file of the workshop opens from its file: one title, its parts, one legend, its foot of links, every relative link on
    disk. A page another version wrote, by its own stamp, is held only to what every version shares (it closes, its links open) and counted."""
    found = sorted(glob.glob(os.path.join(root, "pages", "**", "*.html"), recursive=True)
                   + glob.glob(os.path.join(root, "projects", "*", "pages", "**", "*.html"), recursive=True)) if root else []
    bad, kept = [], 0
    for p in found:
        v = _View(p)
        wrote = re.search(r'<meta name="tenth-written" content="[^"]* tool=(\S+) ', v.text)
        old = bool(wrote) and wrote.group(1) != VERSION  # what this version alone expects is asked only of its own pages (card 41)
        kept += old
        links = [h for h in v.hrefs if h and not h.startswith(("?", "#", "http:", "https:", "mailto:"))
                 and not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), urllib.parse.unquote(h.split("#")[0].split("?")[0]))))]
        # every part named; two at least (an open card and the graph have two), the manual's first line, or the one part of a
        # thing with nothing said yet or of an answered card
        named = sum(map(bool, v.labels))
        one = named == 1 and ({"view=thing", "part.empty"} <= v.marks or {"view=card", "part.card.about"} <= v.marks)
        parts = "parts" in v.classes and named == v.sections and (named >= 2 or "manual.first" in v.marks or one)
        why = ["no top bar"] * ("top" not in v.classes) + ["no title"] * (v.titles != 1) + ["no parts, or a part with no name"] * (not parts)
        why = (why + ["no legend"] * (v.classes.count("legend") != 1) + ["no foot of links"] * ("foot" not in v.classes)) * (not old)
        why += ["not closed: no </html>"] * (not v.text.rstrip().endswith("</html>")) + [f"an unclosed <{t}>" for t in v.open]
        bad += [f"{os.path.relpath(p, root)}: {', '.join(why + [f'a link to {x} opens nothing' for x in links[:1]])}"] if why or links else []
    return _c("views", bad[:5] + [f"and {len(bad) - 5} more"] * (len(bad) > 5), f"{len(found)} view files open from their files" + f"; {kept} written by another version of this tool, held only to "
              "what every version shares: the file closes and its links open" * bool(kept) if root else "no workshop yet, so no view files to open")


def store_check(s, scratch):
    """A scratch round trip in a folder of its own, then a read-only pass over the maker's record: every chain verified, find answering."""
    os.makedirs(scratch, exist_ok=True)
    d, why, read = tempfile.mkdtemp(prefix="selfcheck-", dir=scratch), [], ""
    try:
        t = _store.open(d)
        i = t.append("selfcheck", "note", {"text": "a round trip"}, by=TOOL)
        why += [] if t.get(i)["body"]["text"] == "a round trip" and t.verify()["ok"] else ["the scratch round trip did not read back"]
        if s:
            r = _store.open(s.root, read_only=True)
            v = r.verify()
            why += [f"{f['file']} row {f['row']}: {f['what']}" for f in v["failures"][:5]]
            r.find("the", limit=1)
            read = f"; the record's {v['lines']} lines verified and find answered"
    except Exception as e:  # the self-check names any failure of the store as red; it never raises it
        why.append(f"the store did not read back: {type(e).__name__}: {e}")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return _c("store", why, "a scratch round trip read back" + read)


def _line(s, name, ok, text, extra):
    with s.locked():
        return s.append("workshop", "check", {"name": name, "command": f"sandbox {name}", "exit": 0 if ok else 1,
                                              "output": {"payload": s.payload(text.encode(), unit="workshop")}, **extra}, by=TOOL)


def _open(workshop):
    return workshop if hasattr(workshop, "lines") else _store.open(workshop) if workshop else None


def run(tree=TREE, workshop=None, *, scratch=None, record=True, pub=None):
    """The four checks, one check line with the output kept (when there is a workshop and record is on); under ten seconds here."""
    started, s = time.monotonic(), _open(workshop)
    checks = [seal(tree, pub), budgets(tree), views(s.root if s else None), store_check(s, scratch or os.path.join(INSTALL, "tmp"))]
    out = {"ok": all(c["ok"] for c in checks), "checks": checks, "seconds": round(time.monotonic() - started, 2), "line": None}
    out["text"] = "\n".join(f"{'pass' if c['ok'] else 'FAIL'}: {c['name']}: {c['detail']}" for c in checks) + f"\nTook {out['seconds']} seconds."
    if record and s:
        out["line"] = _line(s, "self-check", out["ok"], out["text"], {"checks": [{k: c[k] for k in ("name", "ok")} for c in checks], "seconds": out["seconds"]})
    return out


def health(s):
    """The workshop's health: placed files, the five acts at ask, each host's last hook line, lock and index, skills, the second copy."""
    from sandbox_os.hosts import claude_code as cc
    from sandbox_os.command import partner
    root, p = s.root, os.path.join(s.root, "CLAUDE.md")
    cl, g = open(p, encoding="utf-8").read() if os.path.exists(p) else "", partner.gone(s)
    gone, his = [n for n in g if g[n][2] != "no"], [n for n in g if g[n][2] == "no"]  # card 42: a missing one he said no to placing again is his removal, no fault
    big = cc.BEGIN in cl and cc.END in cl and len(cl[cl.index(cc.BEGIN):cl.index(cc.END)].encode()) > cc.LIMIT
    out = [_c("placed files", [f"missing: {', '.join(gone)}"] * bool(gone) + ["the block in CLAUDE.md is past Claude Code's 12 KiB"] * big,
              say("health.placed.kept" if his else "health.placed.ok"), say("health.placed.fix"))]
    out[0]["detail"] += f"; removed by you, which is no fault: {', '.join(his)}" * bool(his)
    try:
        missing = [a for a in cc.ASK if a not in json.load(open(os.path.join(root, ".claude", "settings.json")))["permissions"]["ask"]]
    except (OSError, ValueError, KeyError, TypeError):
        missing = cc.ASK
    out.append(_c("the five acts", [say("health.acts.no", n=len(missing), all=len(cc.ASK))] * bool(missing), say("health.acts.ok"), say("health.acts.fix")))
    hooks = [l for l in s.lines(kinds=["hook"]) if (l["body"] or {}).get("host") == cc.NAME]
    out.append(_c("hooks", [] if hooks else [say("health.hooks.no", host=cc.NAME)], say("health.hooks.ok", host=cc.NAME, t=hooks[-1]["t"] if hooks else ""), say("health.hooks.fix", host=cc.NAME)))
    try:
        with s.locked(timeout=0.2):
            lock = []
    except _store.Busy as e:
        lock = [str(e)]
    out.append(_c("lock and index", lock, say("health.lock.cached" if os.path.exists(os.path.join(root, "cache", "index-2.sqlite")) else "health.lock.rebuilt"), say("health.lock.fix")))
    try:
        from sandbox_os.command import skills
        out.append(_c("skills", [str(x) for x in skills.check(root)], say("health.skills.ok"), say("health.skills.fix")))
    except ImportError:
        out.append({"what": "skills", "ok": None, "detail": "not yet: the skills check is not in this build", "fix": "none needed"})
    push = [l for l in s.lines(kinds=["copy"]) if (l["body"] or {}).get("event") == "push"]
    out.append({"what": "second copy", "ok": True if push else None, "fix": "none needed",  # not yet, and no fault, until sandbox copy --to FOLDER has made one (R-READ-10, card 32)
                "detail": f"last copied {push[-1]['t'][:10]}" if push else say("health.copy")})
    return out + _world(s, cc, cl, his, say) + [_pins(s)]


def _pins(s):
    """Batch E's pinned words (Task 14): for each standing rule or answer that pins words in a file of the workshop, a fault per pin whose
    file is not there or no longer holds its words, naming the line, the path and the words' first sixty characters, and a fault, unread, per
    pin whose path a symbolic link now leads outside the workshop's real path (the review of batch E, finding 11b); none mended."""
    from sandbox_os.command import DOWN
    why = []
    for l in s.lines(kinds=["rule", "answer"]):
        pins = (l["body"] or {}).get("pins") if l["mark"] not in DOWN else None
        for p in [p for p in pins if isinstance(p, dict) and isinstance(p.get("path"), str) and isinstance(p.get("words"), str)] if isinstance(pins, list) else []:
            f, real = os.path.join(s.root, p["path"]), os.path.realpath(s.root)
            if not os.path.realpath(f).startswith(real + os.sep):  # a link that now leads out: faulted, never read (finding 11b)
                why.append(say("health.pins.outside", line=l["id"], path=p["path"]))
                continue
            if not os.path.isfile(f):
                why.append(say("health.pins.gone", line=l["id"], path=p["path"]))
                continue
            with open(f, encoding="utf-8", errors="replace") as h:
                held = h.read()
            if p["words"] not in held:
                why.append(say("health.pins.missing", line=l["id"], path=p["path"], words=p["words"][:60]))
    return _c(say("health.pins"), why, say("health.pins.ok"), say("health.pins.fix"))


def _world(s, cc, cl, his, say):
    """Batch D's four: types and relations unused ninety days (the store's list), questions past their date with no answer linked, the
    read of a unit that cannot be made or named by the block's import and absent (a unit no session opened is named not yet read, no
    fault), and a placed block that does not say exactly one version, this tool's, inside its own markers."""
    from sandbox_os.command import DOWN
    from sandbox_os.pages import read
    root, out = s.root, []
    if hasattr(s, "unused"):
        u = s.unused()
        n, m, names = len(u["types"]), len(u["relations"]), [x["name"] for x in u["types"] + u["relations"]]
        out.append(_c("unused types", [f"{counted(n, 'type')} and {counted(m, 'relation')} with no new line in ninety days: " + _five(names)] * bool(n or m),
                      say("health.unused.ok"), say("health.unused.fix")))
    else:
        out.append({"what": "unused types", "ok": None, "detail": "not yet: the store's list of unused types is not in this build", "fix": "none needed"})
    answered = {(l["body"] or {}).get("to") for l in s.lines(kinds=["link"]) if (l["body"] or {}).get("rel") == "answers" and l["mark"] not in DOWN}
    past = [l for l in s.lines(kinds=["question"]) if l["mark"] == "past" and l["id"] not in answered]
    out.append(_c("expired questions", [f"{counted(len(past), 'question')} past {'its' if len(past) == 1 else 'their'} date, unanswered: "
                                        + "; ".join(f"{(l['body'] or {}).get('text')} ({l['unit']}, until {l.get('valid_until')})" for l in past[:5])] * bool(past),
                  "no question is past its date unanswered", "settle each, drop it with a line, or raise it as a card"))
    block = cl[cl.index(cc.BEGIN):cl.index(cc.END, cl.index(cc.BEGIN))] if cc.BEGIN in cl and cc.END in cl[cl.find(cc.BEGIN):] else ""
    imports = [x[1:].strip() for x in block.splitlines() if x.startswith("@")]
    why, unread, gone = [], [], [x for x in imports if not all(os.path.exists(os.path.join(root, f)) for f in (x, os.path.basename(x))) and os.path.basename(x) not in his]
    mine = [os.path.basename(x) for x in imports if os.path.basename(x) in his]  # card 42: a file he removed and said no to is no fault; card 31: a cut stands for its page
    for u in s.units():  # the read made as the hook makes it, written nowhere; a unit no session has opened has none yet, and that is no fault
        try:
            read.render_read(s, read.read_ids(s, u), you=False)
            unread += [u] * (not os.path.exists(os.path.join(root, "projects", u, "read.md")))
        except Exception as e:
            why.append(f"the read of {u} cannot be made: {type(e).__name__}: {str(e)[:160]}")
    start = [x for x in gone if x == "read.md" or x.startswith("cache/handed/") and os.path.exists(os.path.join(root, os.path.basename(x)))]  # what a start writes
    fix = [say("health.imports.tool")] * bool(why) + [say("health.imports.start")] * bool(start) + [say("health.imports.back", file=os.path.basename(x)) for x in gone if x not in start]
    out.append(_c("the read per unit", why + [f"the block in CLAUDE.md imports {x}, which names no file" for x in gone], f"every unit's read can be made, and the block's {counted(len(imports), 'import')} each name a file"
                  + f", or one removed by you: {', '.join(mine)}" * bool(mine)
                  + (f"; not yet read in a session, which is no fault: {', '.join(unread)}" if unread else ""), "; ".join(fix) or "none needed"))
    old = []
    for name in ("CLAUDE.md", "AGENTS.md"):
        p = os.path.join(root, name)
        t = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
        i = t.find(cc.BEGIN)
        j = t.find(cc.END, i) if i >= 0 else -1
        if i < 0:  # no block placed in this file: nothing to say about its version
            continue
        vs = re.findall(r"^Sandbox OS (\S+):", t[i:j], re.M) if j >= 0 else []  # inside its own markers only: a line outside is his
        why = ("has no closing marker, so no version inside its markers" if j < 0 else "says no version" if not vs else
               f"says {'two' if len(vs) == 2 else len(vs)} versions ({', '.join(vs)}), not one" if len(vs) > 1 else
               f"says Sandbox OS {vs[0]}, and this tool is {VERSION}" if vs[0] != VERSION else None)
        old += [f"the block in {name} {why}"] if why else []
    out.append(_c("the block's version", old, f"every placed block says Sandbox OS {VERSION}, this tool's version, once", say("health.block.fix")))
    return out


def _said(sc, h=(), ws=True):
    """What the doctor prints and keeps: a line of context, the self-check, the health under three labels (pass, not yet, FAIL; the ok
    values stay True, False and None), and a line that counts what needs you, naming each (batch G, R-DESIGN-24)."""
    bad = [c["name"] for c in sc["checks"] if c["ok"] is False] + [x["what"] for x in h if x["ok"] is False]
    first = f"Checking this tool{' and this workshop' * ws}; nothing is fixed, only named."  # with no workshop yet, the tool alone
    return "\n".join([first, "the self-check:", sc["text"]] + ["the workshop's health:"] * bool(h)
                     + [f"{ {True: 'pass', False: 'FAIL', None: 'not yet'}[x['ok']] }: {x['what']}: {x['detail']}" + (f"; fix: {x['fix']}" if x["ok"] is False else "") for x in h]
                     + [f"{counted(len(bad), 'check')} need{'s' * (len(bad) == 1)} you: {', '.join(bad)}." if bad else "Nothing needs you."])


def doctor(workshop, *, tree=TREE, scratch=None, pub=None):
    """The self-check first, then the workshop's health; each fault named with its fix in one line, none made; one line written."""
    s = _open(workshop)
    sc, h = run(tree, s, scratch=scratch, record=False, pub=pub), health(s)
    text = _said(sc, h)
    ok = sc["ok"] and all(x["ok"] is not False for x in h)
    try:
        line = _line(s, "doctor", ok, text, {"checks": [{k: c[k] for k in ("name", "ok")} for c in sc["checks"]], "health": [{k: x[k] for k in ("what", "ok")} for x in h]})
    except _store.Refused:  # a record that takes no writes here (a copy whose home is elsewhere, a held lock): the findings stand, unwritten
        line = None
    return {"ok": ok, "selfcheck": sc, "health": h, "text": text, "line": line}


def main(argv):
    """doctor [--workshop PATH] [--json]: the self-check of the running tool, then the workshop's health."""
    pointer = os.path.join(INSTALL, "workshop")
    ws = argv[argv.index("--workshop") + 1] if "--workshop" in argv[:-1] else open(pointer).read().strip() if os.path.exists(pointer) else None
    r = doctor(ws) if ws else run(TREE)
    text = r["text"] if ws else _said(r, ws=False) + "\nno workshop yet: run sandbox to make one"
    print(json.dumps({k: v for k, v in r.items() if k != "text"}, indent=1) if "--json" in argv else text)
    if ws and r["line"] is None:
        print(say("cli.readonly"))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
