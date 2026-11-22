# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The files: every view written where the contract names it (pages/*.html at the workshop root, each morning's brief
kept, projects/<unit>/pages/*.html with its runs, cards and things), each atomically and stamped; where-it-stands.md and grants.md
projected, and the read of the things in hand, a hand edit to the present page or a read recorded as a line before it is projected again; charter.md and book.md
copied in once and never written again; welcome.md written once; the faces copied beside every folder of views."""
import json
import os
import shutil

from sandbox_os import store as _store
from sandbox_os.pages import frame, measures, read, views
from sandbox_os.pages.frame import Ctx
from sandbox_os.pages.read import Reader, VOCAB
from sandbox_os.pages.words import Words

TOOL = {"kind": "tool", "name": "sandbox-os", "model": None, "host": None}
FILE_EDIT = {"kind": "person", "name": "file edit", "model": None, "host": None}
ACTS = ("delete", "erase", "undelete")
ROOT_VIEWS = ("brief", "find", "learned", "charter", "book", "tool", "welcome", "things", "you", "world")


def put(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".part", "w", encoding="utf-8", newline="") as f:
        f.write(data)
    os.replace(path + ".part", path)
    return path


def writable(s, clock=None, machine=None):
    return s if not s.read_only else _store.open(s.root, clock=clock or s.clock, machine=machine)


def write_views(workshop, unit=None, *, clock=None, machine=None, lang=None):
    """Writes the workshop's views (every unit's, or one unit's and the workshop's own) and returns the paths written."""
    s = workshop if hasattr(workshop, "lines") else _store.open(workshop, read_only=True, clock=clock, machine="pages")
    root, written = s.root, []
    for name in ("charter.md", "book.md"):
        if not os.path.exists(os.path.join(root, name)):
            shutil.copyfile(os.path.join(views.TREE, "sandbox_os", "partner", name), os.path.join(root, name))
    memo_path = os.path.join(root, "cache", "pages-written.json")

    def project(st):  # the cache read, compared, the projected files written and the cache saved, under the record's lock
        memo = read_memo(root) or {}
        newest, act_units, gone, acts = acts_since(st, memo.get("acts"))
        units = sorted(set([unit] if unit else st.units()) | (act_units & set(st.units())))
        met = []
        paths = [p for u in units for p in project_files(st, u, memo, met)]
        put(memo_path, json.dumps(memo, ensure_ascii=False, sort_keys=True, indent=0))
        say_refused(st, met)
        return newest, units, gone, acts, paths
    newest, units, gone, acts, written = under_lock(s, project, clock, machine)
    r = Reader(s)

    def view(which, rel, **ids):
        c = Ctx(s, as_file=True, here=rel, reader=r, lang=lang)
        written.append(put(os.path.join(root, rel), views.VIEWS[which](c, **ids)))
    for name in ROOT_VIEWS:
        view(name, f"pages/{name}.html")
    for t in s.types():  # each type's page, at the type's name as recorded
        view("type", f"pages/types/{t['body']['name']}.html", name=t["body"]["name"])
    view("cards", "pages/cards-move.html")  # the move's cards, which the brief's and-more opens (card 23)
    view("brief", f"pages/briefs/{r.today()}.html")
    for week in dict.fromkeys((measures.last_week(s.clock()), measures.iso_week(s.clock()))):  # the last complete week, and this one
        view("week", f"pages/week-{week}.html", week=week)
    for u in units:
        base = f"projects/{u}/pages"
        view("project", f"{base}/brief.html", unit=u)
        for name in ("present", "graph"):
            view(name, f"{base}/{name}.html", unit=u)
        if r.kind("move", units=[u]):
            view("moved", f"{base}/moved.html", unit=u)
        for x in r.kind("run", units=[u]):
            view("run", f"{base}/runs/{r.day(x['t'])}-{x['id']}.html", id=x["id"])
        for x in r.kind("card", units=[u]):
            view("card", f"{base}/cards/{r.day(x['t'])}-{x['id']}.html", id=x["id"])
        for x in [x for x in s.things(unit=u) if x["type"] not in VOCAB]:  # each thing's page; a type's is at the root, a relation has none
            view("thing", f"{base}/things/{r.day(r.get(x['id'])['t'])}-{x['id']}.html", id=x["id"])
    faces = [f for f in (os.listdir(frame.FONTS) if os.path.isdir(frame.FONTS) else []) if f.endswith(".woff2")]
    for folder in ["pages"] + [f"projects/{u}/pages" for u in units]:
        for f in faces:
            dst = os.path.join(root, folder, "fonts", f)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(frame.FONTS, f), dst)
            written.append(dst)
    if gone:  # a file written earlier (a dated brief, another unit's page) that still names a line taken back is rewritten too
        done = set(written)
        for rel in written_views(root):
            if os.path.join(root, rel) not in done and any(f'data-l="{i}"' in open(os.path.join(root, rel), encoding="utf-8").read() for i in gone):
                name, ids = view_of(rel)
                c = Ctx(s, as_file=True, here=rel, reader=r, lang=lang)
                c.extra = [c.w.t("file.rewritten", date=c.w.date(acts[-1]["t"]))]
                written.append(put(os.path.join(root, rel), views.VIEWS[name](c, **ids)))
    with s.locked():  # the cache read again under the lock, so what another writer saved meanwhile is kept; the newer act wins
        memo = read_memo(root) or {}
        memo["acts"] = max((a for a in (memo.get("acts"), newest) if a), default=None)
        put(memo_path, json.dumps(memo, ensure_ascii=False, sort_keys=True, indent=0))
    return written


def read_memo(root):
    p = os.path.join(root, "cache", "pages-written.json")
    return json.load(open(p)) if os.path.exists(p) else None


def acts_since(s, after):
    """The deletions, undeletions and erasures newer than a line id: the newest act, their units, and the lines they touched."""
    acts = s.lines(kinds=list(ACTS))
    new = [a for a in acts if after is None or a["id"] > after]
    gone = set()
    for a in new:
        t = (a["body"] or {}).get("erased" if a["kind"] == "erase" else "target")
        if isinstance(t, str):
            gone.add(t)
            back = s.get(t) if a["kind"] == "undelete" else None
            gone |= {(back["body"] or {}).get("target")} - {None} if back else set()
    return (acts[-1]["id"] if acts else after), {a["unit"] for a in new}, gone, new


def written_views(root):
    for base in ["pages"] + [f"projects/{u}/pages" for u in sorted(os.listdir(os.path.join(root, "projects")))]:
        for d, _, fs in os.walk(os.path.join(root, base)):
            yield from (os.path.relpath(os.path.join(d, f), root) for f in fs if f.endswith(".html"))


def view_of(rel):
    """Which view a written file holds, read from where it lives."""
    p = rel.split("/")
    if p[0] == "pages":
        if p[1].startswith("week-"):
            return "week", {"week": p[1][5:-5]}
        if p[1] == "types":
            return "type", {"name": p[2][:-5]}
        return ("brief", {}) if p[1] == "briefs" else (p[1][:-5], {})
    if p[3] in ("runs", "cards", "things"):
        return p[3][:-1], {"id": p[4][11:-5]}
    return ("project" if p[3] == "brief.html" else p[3][:-5]), {"unit": p[1]}


class _Edit(Exception):
    """A hand edit met on a store opened to read: the projection runs again on the store opened to write, which records it."""


def under_lock(s, work, clock=None, machine=None):
    """work(st) with the record's lock held by st across the cache's read, the compare, the files written and the cache saved, so two
    writers never lose each other's entries; st is s, or s opened to write once a hand edit is met, the lock then held by that one."""
    try:
        with s.locked():
            return work(s)
    except _Edit:
        w = writable(s, clock, machine)
        with w.locked():
            return work(w)


def projected(s, rel, render, memo, unit, refused, *, file=None):
    """render() written at rel; a hand edit since the last projection (the file differs from both) is first a note in unit, then rendered
    again; an edit the store refuses (a secret in it) is projected over all the same, its refusal's sentence added to refused, never its words."""
    path, new = os.path.join(s.root, rel), render()
    if os.path.exists(path):
        old, last = open(path, encoding="utf-8").read(), memo.get(rel)
        if old != new and old != last:
            if s.read_only:
                raise _Edit(rel)
            kept = set((last or new).splitlines())
            added = "\n".join(l for l in old.splitlines() if l.strip() and l not in kept)
            try:
                sha = s.payload(old.encode("utf-8"), unit=unit)
                text = added if added and len(added.encode()) < 16000 else Ctx(s, reader=Reader(s)).w.plain("file.edit", file=file or rel)
                s.append(unit, "note", {"event": "file edit", "file": file or rel, "text": text, "edited": {"payload": sha}}, by=FILE_EDIT)
            except _store.Refused as e:
                refused.append((unit, file or rel, str(e)))
            new = render()
    memo[rel] = new
    return put(path, new)


def say_refused(s, refused):
    """Each refused hand edit as a note by the tool in its unit, in the refusal's own sentence (a hook says it in its failed line instead)."""
    for unit, file, why in refused:
        s.append(unit, "note", {"event": "file edit refused", "file": file,
                                "text": Ctx(s, reader=Reader(s)).w.plain("file.edit.refused", file=file, why=why)}, by=TOOL)


def project_files(s, u, memo, refused):
    """where-it-stands.md and grants.md for a unit; an edit made by hand since the last projection is recorded first."""
    page = projected(s, f"projects/{u}/where-it-stands.md", lambda: views.present_md(Ctx(s, reader=Reader(s)), u), memo, u, refused,
                     file="where-it-stands.md")
    return [page, put(os.path.join(s.root, f"projects/{u}/grants.md"), views.grants_md(Ctx(s, reader=Reader(s)), u))]


def write_read(workshop, unit, *, clock=None, machine=None, refused=None):
    """The read of a unit's things at projects/<unit>/read.md (its projection) and at the workshop's read.md (the session's, which Claude
    Code's block imports and Codex's names), in the welcome's language; only the workshop's carries the section about him, since a project
    that is its own repository may commit and push its read.md (ruling row 41's reason); a hand edit to either is a note before it is projected
    again; one the store refuses is a note saying so, or, when the caller passes a list as refused (the hook), its (unit, file, sentence) there."""
    s = workshop if hasattr(workshop, "lines") else _store.open(workshop, read_only=True, clock=clock, machine="pages")
    lang = frame.welcome_answers(Reader(s).welcome(), Words("en", root=s.root)).get("language") or "en"
    render = lambda you=True: read.render_read(s, read.read_ids(s, unit), lang=lang, you=you)  # noqa: E731

    def project(st):  # the cache read, compared, both files written and the cache saved, under the record's lock
        memo, met = read_memo(st.root) or {}, []
        out = [projected(st, f"projects/{unit}/read.md", lambda: render(you=False), memo, unit, met), projected(st, "read.md", render, memo, "workshop", met)]
        put(os.path.join(st.root, "cache", "pages-written.json"), json.dumps(memo, ensure_ascii=False, sort_keys=True, indent=0))
        say_refused(st, met) if refused is None else refused.extend(met)
        return out
    return under_lock(s, project, clock, machine)


def save_welcome(workshop, answers, *, clock=None, machine=None):
    """welcome.md, once: each answer verbatim, "some" when the ask setting is left out; a flow line per step, by the tool."""
    s = workshop if hasattr(workshop, "lines") else _store.open(workshop, clock=clock, machine=machine)
    s = writable(s, clock, machine)
    w = Words("en", root=s.root)
    ask = answers.get("ask") if answers.get("ask") in views.LIMITS else ""
    values = {"name": answers.get("name") or "", "making": answers.get("making") or "", "ask": ask or "some",
              "language": answers.get("language") or "en", "locale": answers.get("locale") or "en-GB"}
    text = "\n".join([f"# {w.plain('md.welcome.title')}", ""] + [f"{w.tab[('md.welcome.' + k, '')]['en']} {v}" for k, v in values.items()]) + "\n"
    path = os.path.join(s.root, "welcome.md")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    sid = next((l["body"]["session"] for l in reversed(s.lines(unit="workshop", kinds=["flow"])) if l["by"]["kind"] == "tool" and l["body"].get("session")), None)
    for step, given in (("name", answers.get("name")), ("making", answers.get("making")), ("ask", ask)):  # the welcome's session, as its shown line carries it
        s.append("workshop", "flow", dict({"step": step, "event": "answered" if given else "skipped", "seconds": answers.get("seconds")},
                                          **({"session": sid} if sid else {})), by=TOOL)
    maker_object(s, name=answers.get("name"))
    return path


def maker_object(workshop, *, name=None):
    """The maker's person object: the standing one, else recorded once by the tool in the workshop unit, flagged as the maker, named by
    his answer, the welcome's name or, when he gave none, the words for the maker in the welcome's language (design section 6)."""
    s = writable(workshop)
    with s.locked():  # the look and the write under one lock, so two first needs never record two
        me = read.maker_id(s)
        if me:
            return me
        answers = frame.welcome_answers(Reader(s).welcome(), Words("en", root=s.root))
        name = next((n for n in (name, answers.get("name")) if isinstance(n, str) and n.strip()), None) or Words(
            answers.get("language") or "en", root=s.root).plain("you.name")  # his words kept as typed
        s.seed(by=TOOL)
        return s.append("workshop", "object", {"type": "person", "name": name, "maker": True, "ground": "schema.org/Person"}, by=TOOL)
