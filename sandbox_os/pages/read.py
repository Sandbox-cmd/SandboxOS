# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""What each view needs from the store, read through its public calls only (lines, get, find, holds, heads, grant_state,
payload_path, units) and counted at every render: the maker's newest line, open cards, the story so far, the present
projection, a run's lines, the hosts' asks and silences, the links between lines, and the welcome's three answers; and the
short read handed to the model."""
import collections
import csv
import datetime as _dt
import glob
import hashlib
import json
import os
import re

from sandbox_os.store.line import BASES, RELATIONS, canonical, links_of, ends_ok, iso, strip_arabic_marks
from sandbox_os.store.seed import VERBS, TYPES, RELATIONS as SEED_RELATIONS, UNIT as SEED_UNIT, READ as SEED_READ
from sandbox_os.store.verbs import SERVICE_TYPES
from sandbox_os.pages.words import Words, plain

DOWN = ("erased", "deleted", "struck")
GONE = DOWN + ("superseded",)
FIELDS = ("text", "words", "sentence", "purpose", "decides", "intent", "direction", "thing", "why", "query", "says", "name")
CLOSED = ("yes", "no", "words")
FAILED = ("hook-failed", "failed")
DOORS = {"asks": "asks", "grant": "grant", "asks once": "once", "inside": "inside"}  # a verb's door (store.verbs.door) to its row door.<key>


def words_of(line, field=None):
    """A line's own words: the named field, or the first field a person reads; None when deleted, erased or wordless."""
    body = line.get("body") if line else None
    if not isinstance(body, dict):
        return None
    for f in (field,) if field else FIELDS:
        v = body.get(f)
        if isinstance(v, str) and v.strip():
            return v
    return None


def slug(name):
    """A name as its row's id carries it, as the command's verbs.slug makes it: lower case, each other run one underscore."""
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


SEED_ROWS = {("type", r["name"]) for r in TYPES} | {("relation", r["name"]) for r in SEED_RELATIONS} | {("verb", r["name"]) for r in VERBS}


def from_seed(line):
    """A line the tool wrote when seeding the vocabulary, which is not news (the reading, W7): by the tool in the workshop's own unit, an
    object of a seed row (a service or a host by its type alone, so an older seed's name is one too) or a verb's fact read as the seed reads it."""
    b = line.get("body") or {}
    if line.get("unit") != SEED_UNIT or (line.get("by") or {}).get("kind") != "tool":
        return False
    return (line["kind"] == "object" and ((b.get("type"), b.get("name")) in SEED_ROWS or b.get("type") in SERVICE_TYPES)
            or line["kind"] == "fact" and b.get("source") == SEED_READ["source"])


def seeded(w, line):
    """The strings table's row for a verb's or service's name the tool recorded (verb.<slug> or service.<slug> of the recorded name, so a
    name finds its row where the workshop's own table carries one, card 30), or None: a name the maker gave stays as it was recorded."""
    b = (line or {}).get("body") or {}
    pre = "verb." if b.get("type") == "verb" else "service." if b.get("type") in SERVICE_TYPES else None
    sid = pre + slug(b.get("name")) if pre and line.get("kind") == "object" and (line.get("by") or {}).get("kind") == "tool" else None
    return sid if sid and (sid, "") in w.tab else None


def standing(line):
    return line is not None and line.get("mark") not in GONE


def chosen(store, words, candidates):
    """The one candidate (an id, or a read carrying its id) whose standing alias fact, taught true by his answer, says these words, compared
    as the command's cards.plain compares them (trimmed, lower case, no closing stop, Arabic without its short vowels); else None. The one
    rule below the command and the pages: the partner's thing tool, find and names.which read it before saying several (Astra, finding 6)."""
    fold = lambda x: strip_arabic_marks(str(x).strip().lower().rstrip(".!,،"))  # noqa: E731
    said = fold(words or "")
    hit = [c for c in candidates if any(
        (f["body"] or {}).get("facet") == "alias" and f["body"].get("taught") is True and fold(f["body"].get("value")) == said and standing(f)
        for f in store.lines(about=c["id"] if isinstance(c, dict) else c, kinds=["fact"]))]
    return hit[0] if len(hit) == 1 else None


class Reader:
    """One render's view of the record: the lines read once, then asked many ways."""

    def __init__(self, store):
        self.s, self._all, self._links, self._local, self._into, self._out = store, None, None, {}, None, None

    def all(self):
        if self._all is None:
            self._all = self.s.lines()
            self.by_id = {l["id"]: l for l in self._all}
        return self._all

    def get(self, id):
        self.all()
        return self.by_id.get(id) or self.s.get(id)

    def units(self):
        return self.s.units()

    def unit(self, u):
        return [l for l in self.all() if l["unit"] == u]

    def kind(self, *kinds, units=None, since=None):
        return [l for l in self.all() if l["kind"] in kinds and (units is None or l["unit"] in units) and (since is None or l["t"] > since)]

    def links(self):
        """Every link the record makes, as (made, from, relation, to), with ends inside the rules, as the index keeps them."""
        if self._links is None:
            self.all()
            out = []
            for l in self._all:
                if l["body"] is None or l.get("mark") in DOWN:
                    continue
                for frm, rel, to in links_of(l):
                    f, t = self.by_id.get(frm), self.by_id.get(to)
                    if f and t and (ends_ok(rel, f["kind"], t["kind"], f["unit"] != t["unit"] and t["seq"] == 1) if rel in RELATIONS  # across: card 22
                                    else f["kind"] == t["kind"] == "object"):  # between two things a relation is data, as the store keeps it
                        out.append((l["id"], frm, rel, to))
            self._links = out
        return self._links

    def into(self, to, rel):
        if self._into is None:
            self._into, self._out = collections.defaultdict(list), collections.defaultdict(list)
            for m, f, r, t in self.links():
                self._into[(t, r)].append(self.by_id[f])
                self._out[(f, r)].append(self.by_id[t])
        return self._into.get((to, rel), [])

    def out_of(self, frm, rel):
        self.into(None, None)
        return self._out.get((frm, rel), [])

    def day(self, t):
        if t not in self._local:
            self._local[t] = _dt.datetime.fromisoformat(t).astimezone().date().isoformat()
        return self._local[t]

    def today(self):
        return self.s.clock().astimezone().date().isoformat()

    def maker_newest(self):
        mine = [l for l in self.all() if l["by"]["kind"] == "maker" and l.get("mark") not in ("deleted", "erased")
                and (l["body"] or {}).get("presence") != "none" and not (l["body"] or {}).get("stale")]
        return mine[-1] if mine else None

    def head(self, unit=None):
        ls = self.unit(unit) if unit else self.all()
        return max(ls, key=lambda l: l["id"])["id"] if ls else None

    def answers(self, card_id):
        return [a for a in self.kind("answer") if (a["body"] or {}).get("card") == card_id]

    def closes_card(self, a):
        b = a["body"] or {}
        return standing(a) and a["by"]["kind"] == "maker" and b.get("answer") in CLOSED and b.get("presence") != "none" and not b.get("stale")

    def cards(self, units=None):
        return [c for c in self.kind("card", units=units) if standing(c)]

    def open_cards(self, units=None):
        return [c for c in self.cards(units) if not any(self.closes_card(a) for a in self.answers(c["id"]))]

    def story(self, units):
        """The newest standing present line for the projects in view, else the newest standing close by the partner."""
        for kind in ("present", "close"):
            ls = [l for l in self.kind(kind, units=units) if standing(l) and words_of(l) and l["by"]["kind"] == "partner"]
            if ls:
                return ls[-1]
        return None

    def present(self, unit):
        """The present projection: up to five newest standing closes by the partner with what checked them, the maker's newest line, and stale since."""
        ls = self.unit(unit)
        closes = [l for l in ls if l["kind"] == "close" and l["by"]["kind"] == "partner" and standing(l)][-5:][::-1]
        checks = {c["id"]: [x for x in self.into(c["id"], "proves") if x["kind"] in ("check", "receipt")] for c in closes}
        maker = [l for l in ls if l["by"]["kind"] == "maker" and standing(l) and words_of(l)]
        runs = [l for l in ls if l["kind"] == "run" and standing(l)]
        ended = [l for l in ls if l["kind"] in ("close", "abandoned")]
        stale = runs[-1] if runs and not any(e["t"] >= runs[-1]["t"] for e in ended) else None
        return {"unit": unit, "closes": closes, "checks": checks, "maker": maker[-1] if maker else None,
                "stale": stale, "head": self.head(unit)}

    def run(self, id):
        """A run's lines: the run, every line part of it, and the unit's lines up to the next run (its closing lines come after its close)."""
        run = self.get(id)
        ls = self.unit(run["unit"])
        k = next(i for i, l in enumerate(ls) if l["id"] == id)
        span = [run]
        for l in ls[k + 1:]:
            if l["kind"] == "run":
                break
            span.append(l)
        part = {l["id"] for l in self.into(id, "part_of")}
        span += [l for l in self.all() if l["id"] in part and l not in span]
        span.sort(key=lambda l: (l["t"], l["seq"]))
        end = next((l for l in span if l["kind"] in ("close", "abandoned")), None)
        if end:  # after its close, past the next run too, a line is the run's when part of it, naming it (a check's run, a card's about),
            at = (end["t"], end["seq"])  # or linking to a line already the run's, with the line a link line links from (R-READ-16, R-READ-21)
            keep = {l["id"] for l in span if (l["t"], l["seq"]) <= at} | part
            for l in (l for l in ls if (l["t"], l["seq"]) > at):
                b = l["body"] or {}
                tied = {f for f, _, to in links_of(l) if to in keep} | ({l["id"]} if b.get("run") == id or l["kind"] == "card" and b.get("about") == id else set())
                if tied:
                    keep |= tied | {l["id"]}
            span = sorted((l for l in self.all() if l["id"] in keep), key=lambda l: (l["t"], l["seq"]))
        accepted = any(a["kind"] == "accept" or self.closes_card(a) for a in self.into(id, "answers"))
        state = "abandoned" if end and end["kind"] == "abandoned" else "accepted" if accepted else "closed" if end else "open"
        return {"run": run, "lines": span, "end": end, "state": state}

    def hosts(self, since, units=None):
        """Per host and local day since a time: lines that show the host at work, and whether it kept a record of asks."""
        seen, asked = collections.defaultdict(set), set()
        for l in self.all():
            if (since and l["t"] <= since) or (units is not None and l["unit"] not in units):
                continue
            b = l["body"] or {}
            host = b.get("host") if l["kind"] in ("session", "host_ask", "host_ran", "hook", "usage", "not_seen") else None
            host = host or l["by"].get("host")
            if host:
                seen[host].add(self.day(l["t"]))
                if l["kind"] == "host_ask":
                    asked.add((host, self.day(l["t"])))
        return seen, asked

    def welcome(self):
        """welcome.md's answers, read by their English keys; an absent file gives None."""
        path = os.path.join(self.s.root, "welcome.md")
        if not os.path.exists(path):
            return None
        return open(path, encoding="utf-8").read()

    def opening(self, line, field="words", size=2048):
        """The opening of a text a line keeps beside as a payload ({"payload": sha256} in the field), its first size bytes read and no more, so
        a long prompt shows its first words (Astra's finding 6); None when the field holds no payload or the payload is not here."""
        v = (line.get("body") or {}).get(field) if line else None
        p = self.s.payload_path(v["payload"]) if isinstance(v, dict) and isinstance(v.get("payload"), str) else None
        try:
            with open(p, "rb") as f:
                return f.read(size).decode("utf-8", "ignore") or None
        except (OSError, TypeError):
            return None

    def payload_json(self, sha):
        p = self.s.payload_path(sha)
        try:
            return json.load(open(p, encoding="utf-8")) if p else None
        except (OSError, ValueError):
            return None


def question_state(reader, q):
    """Where an open question stands: dropped (struck, or taken away), settled (a standing line answers it through a standing link),
    raised (a standing card is about it), expired unread (past its day and none of those), else open."""
    if q.get("mark") in DOWN:
        return "dropped"
    if any(standing(x) for x in reader.into(q["id"], "answers")):
        return "settled"
    if any((c["body"] or {}).get("about") == q["id"] for c in reader.cards()):
        return "raised"
    return "expired unread" if q.get("mark") == "past" else "open"


def expired_unread(reader, units=None):
    """The questions that went past their day with nobody settling, dropping or raising them, oldest first."""
    return [q for q in reader.kind("question", units=units) if question_state(reader, q) == "expired unread"]


PROPOSED = ("type proposed", "relation proposed", "verb proposed")  # the queue's events, as the command's growth.EVENTS names them


def proposals(lines):
    """Every standing proposal in the workshop's queue (a note whose event is one of PROPOSED), oldest first, as {id, event, name, state,
    settled, line}: state is waiting unless a standing "proposal settled" note names it, then that note's answer, yes or no, or a standing
    "proposal refused" note does, the store's refusal at his yes, then refused; settled is that note's id, the newest when there are several."""
    ls = sorted((l for l in lines if l["kind"] == "note" and l["unit"] == "workshop" and standing(l)), key=lambda l: (l["t"], l["seq"]))
    ends = {(l["body"] or {}).get("proposal"): l for l in ls if ((l["body"] or {}).get("event"), (l["body"] or {}).get("answer")) in
            (("proposal settled", "yes"), ("proposal settled", "no"), ("proposal refused", "refused"))}
    return [{"id": l["id"], "event": l["body"]["event"], "name": l["body"].get("name"), "line": l,
             "state": ends[l["id"]]["body"]["answer"] if l["id"] in ends else "waiting", "settled": ends[l["id"]]["id"] if l["id"] in ends else None}
            for l in ls if (l["body"] or {}).get("event") in PROPOSED]

# the short read handed to the model: a projection of the things in hand; rendering it writes no line
RESTS, VOCAB, READ_MAX = "rests on a struck line", ("type", "relation"), 6 * 1024


def maker_id(store):
    """The maker's person object: the standing object with body.maker true (the store's door keeps one), or None before it is recorded."""
    return next((t["id"] for t in store.things(type="person") if ((store.get(t["id"]) or {}).get("body") or {}).get("maker") is True), None)


def you_lines(store, *, every=False):
    """Every line about the maker's object and every about_you line, newest first: those standing and not waiting for his yes, or with
    every, all of them but the erased, each with its mark. The one query any read of him uses (the you page, the read handed to the model)."""
    me = maker_id(store)
    got = {l["id"]: l for l in (store.lines(about=me) if me else []) + store.lines(kinds=["about_you"])}
    keep = (lambda l: l.get("mark") != "erased") if every else (lambda l: standing(l) and l.get("mark") != "waiting")
    return sorted((l for l in got.values() if keep(l)), key=lambda l: (l["t"], l["id"]), reverse=True)


def skill_uses(root, lines, *, now, days=90):
    """Every skill folder at the workshop's root, by name: its standing "skill used" notes since `days` before now, the newest one's time,
    and unused when it has none and its SKILL.md is older than `days` (by modification time), so an unused skill is said out loud and can
    be deleted by its folder, which the tool records for a skill it placed (design section 8)."""
    src, since = os.path.join(root, ".agents", "skills"), now - _dt.timedelta(days=days)
    used = [l for l in lines if l["kind"] == "note" and standing(l) and (l.get("body") or {}).get("event") == "skill used" and l["t"] >= iso(since)]
    out = []
    for n in sorted(x for x in os.listdir(src) if os.path.isdir(os.path.join(src, x))) if os.path.isdir(src) else []:
        mine, page = [l["t"] for l in used if l["body"].get("skill") == n], os.path.join(src, n, "SKILL.md")
        born = os.path.getmtime(page if os.path.exists(page) else os.path.join(src, n))
        out.append({"name": n, "uses": len(mine), "last": max(mine, default=None), "unused": not mine and born < since.timestamp()})
    return out


# the portraits: pages others wrote about him, read where they live and never copied (03-design.md section 6 point 6)
PORTRAITS = "portraits.tsv"
SENTENCE_END = re.compile(r"(?<=[.!?؟])\s+")
MARKER = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
HEADING = re.compile(r"^(#+)\s+(.*?)\s*#*$")


def portraits(root):
    """The rows of portraits.tsv at the workshop's root, which he edits: each path with ~ expanded and a * globbed, its label, its section."""
    p = os.path.join(root, PORTRAITS)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)][1:]
    out = []
    for n, r in enumerate((r for r in rows if any(c.strip() for c in r)), 1):
        path, label, section = (r + ["", "", ""])[:3]
        path = os.path.expanduser(path.strip())
        files = [x for x in (sorted(glob.glob(path)) if "*" in path else [path]) if os.path.isfile(x)]
        out.append({"n": n, "path": path, "label": label.strip(), "section": section.strip(), "files": files, "found": bool(files)})
    return out


def sentences(path, section=None):
    """A page's sentences with their hashes: headings, comments, tables and code fences skipped, list markers and *, _ and backticks
    stripped, a paragraph's lines joined, split after . ! ? or ؟ and a space; a sentence of three words or more; with a section, only
    the lines under the heading of that text, until a heading of its level or above."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return []
    paras, cur, fence, inside, level = [], [], False, not section, 0
    for line in re.sub(r"<!--.*?-->", "", text, flags=re.S).splitlines() + [""]:
        s, head = line.strip(), HEADING.match(line.strip())
        if s.startswith(("```", "~~~")):
            fence = not fence
        if s.startswith(("```", "~~~")) or fence or head or not s or s.startswith("|") or MARKER.match(line):
            paras += [" ".join(cur)] if cur else []  # a paragraph ends; a list item starts its own
            cur = []
        if head and section:
            inside = head.group(2) == section or (inside and len(head.group(1)) > level)
            level = len(head.group(1)) if head.group(2) == section else level
        if inside and s and not (fence or head or s.startswith(("|", "```", "~~~"))):
            cur.append(re.sub(r"[*_`]", "", MARKER.sub("", line)).strip())
    return [(hashlib.sha256(x.encode("utf-8")).hexdigest(), x) for p in paras for x in SENTENCE_END.split(" ".join(p.split()))
            if len(x.split()) >= 3]


def ticked(store):
    """His standing ticks, by the page they came from and the sentence's hash: a sentence ticked once is not recorded twice."""
    return {(b.get("source"), hashlib.sha256(b["words"].encode("utf-8")).hexdigest()): l for l in store.lines(kinds=["said"])
            for b in [l["body"] or {}] if b.get("surface") == "tick" and isinstance(b.get("words"), str) and standing(l)}


def touched(store, id):
    """The newest time among a thing's object line and every line about it."""
    o = store.get(id)
    return max([o["t"] if o else ""] + [l["t"] for l in store.lines(about=id)])


def read_ids(store, unit):
    """The standing things in hand of a unit (of every unit at the workshop's root), never a type, a relation or a verb, and never a thing
    only the seed has touched, newest touched first: the store's one index query (Store.in_hand)."""
    return store.in_hand(unit)


def _said(line):
    """A line's own words in the read: a fact as its facet and value, a source not seen as what it was, else its words or its kind."""
    b = line.get("body") or {}
    if line["kind"] == "fact" and isinstance(b.get("facet"), str):
        v = b.get("value")
        return f"{b['facet']}: {v if isinstance(v, str) else canonical(v)}"
    return (words_of(line, "what") if line["kind"] == "not_seen" else words_of(line)) or line["kind"]


def _who(w, line):
    by = (line or {}).get("by") or {}
    k, name = by.get("kind") or "tool", by.get("name") or ""  # the partner's tools record its kind as its name: said once, as the by-lines say it (R-DESIGN-4)
    return w.plain("read.who.maker" if k == "maker" else "row.meta.partner" if k == "partner" and name in ("", "partner") else "who." + k, name=name)


def _age(w, t):
    n = (w.local(w.now).date() - w.local(t).date()).days
    return w.plain("age.today") if n <= 0 else w.plain("age.days", days=w.count("day", n))


def _facet(store, w, name, f):
    """One present belief: its facet and value, then its basis (with where it was read), its confidence, its age and its mark."""
    line = store.get(f["line"]) or {}
    b = line.get("body") or {}
    ran = store.get(f["source"]) if f["basis"] == BASES[1] and isinstance(f["source"], str) else None  # a check showed: its command (R-READ-17)
    ran = (ran["body"] or {}).get("command") if ran and ran["kind"] == "check" and ran["by"]["kind"] == "tool" else None
    why = [w.plain("read.basis." + f["basis"], source=f["source"] or "") + (" " + w.plain("basis.command", command=ran) if ran else "")] \
        if f["basis"] in BASES else []
    why += [w.plain("confidence." + b["confidence"])] if b.get("confidence") else []
    why += [_age(w, f["t"])] + ([w.plain("mark." + RESTS)] if line.get("mark") == RESTS else [])
    v = f["value"]
    return "- " + w.plain("read.facet", facet=name, value=v if isinstance(v, str) else canonical(v), about=w.raw("read.sep").join(why))


def _verbs(store, t, w):
    """The verbs that reach a thing (store.thing(id)["verbs"]), each by its name with its door in the strings table's words."""
    if not t.get("verbs"):
        return ["- " + w.plain("read.verbs.none")]
    name = lambda v: w.plain(seeded(w, store.get(v["verb"])) or "read.verb.name", name=str(v["name"]))  # noqa: E731
    door = lambda v: w.plain("door." + DOORS[v["door"]]) if v["door"] in DOORS else str(v["door"])  # noqa: E731
    return ["- " + w.plain("read.verbs", verbs=w.raw("read.verbs.sep").join(w.plain("read.verb", verb=name(v), door=door(v)) for v in t["verbs"]))]


def _section(store, w, t, his=frozenset()):
    """One thing's section: its name line, beliefs, open questions, last strikes, goals, verbs, assumptions and sources not seen; a line
    about him (his, every line of his page) is never one of them, struck or standing: it is read from his page alone."""
    o, g = t["object"], t["ground"] if t["ground"] is None or isinstance(t["ground"], str) else canonical(t["ground"])
    out = ["## " + w.plain("read.name" if g else "read.name.bare", name=str(t["name"]), type=str(t["type"]), ground=g or ""), ""]
    out += [_facet(store, w, k, f) for k, f in t["facets"].items() if k != "alias"]
    for q in t["questions"]:
        qb = q["body"] or {}
        out.append("- " + w.plain("read.question", text=words_of(q) or "-", settles=qb.get("settles") or "-", cost=qb.get("cost") or "-"))
    out += ["- " + w.plain("read.struck.here", words=_said(l), date=plain(w.date(l["mark_since"] or l["t"]))) for l in t["struck"]
            if l["id"] not in his and l["kind"] != "about_you"]
    out += ["- " + w.plain("read.goal", text=words_of(l) or "-") for l in t["goals"]]
    out += _verbs(store, t, w)
    out += ["- " + w.plain("read.assumption", text=words_of(l) or "-") for l in t["assumptions"]]
    return out + ["- " + w.plain("read.notseen", text=_said(l)) for l in store.lines(about=o["id"], kinds=["not_seen"]) if standing(l)]


YOU_MAX = 12  # the newest lines about the maker the read carries


def _you_basis(w, line):
    """How a line about the maker came to be known, and from where: a fact's basis and source; a note about him his words from a said
    line, or his own line; else no basis word, only where it is."""
    b, by = line.get("body") or {}, (line.get("by") or {}).get("kind")
    basis = b.get("basis") if b.get("basis") in BASES else BASES[0] if b.get("said") or by == "maker" else None  # BASES[0], his word
    source = next((x for x in (b.get("source"), b.get("said")) if isinstance(x, str) and x), None) or line["id"]
    word = [w.plain("read.basis." + basis, source=source)] if basis else []
    reading = basis == BASES[2]  # a reading names its source in its own words
    return w.raw("read.sep").join(word + ([] if reading else [w.plain("read.you.source", source=source)]))


def _you(w, ls, cut):
    """The read's one section about the maker: the lines given (the newest YOU_MAX of you_lines), each with its basis and its source."""
    out = ["", "## " + w.plain("read.you"), ""]
    out += ["- " + w.plain("read.you.line", words=cut(_said(l)), about=_you_basis(w, l)) for l in ls] or [w.plain("read.you.none")]
    return "\n".join(out + [""])


def render_read(store, object_ids, *, lang="en", you=True):
    """The read of the things in hand, as markdown, within READ_MAX bytes whole: the corrections and what rests on them first on the page,
    then the section about the maker from his page alone (you_lines; his own object is never a thing's section, and a struck line about
    him is named only as that, design section 6 point 2), then one section per thing in the order given; the things' sections are kept
    whole first, the rest named by count in the last line, and the corrections fill what remains, struck line by struck line, their words
    cut to 200 characters, those left out named by count. With you false (a project's own read.md, which its repository may commit and
    push: ruling row 41's reason), no section about him is written and no line of his page is read in."""
    w, me = Words(lang, root=store.root, now=store.clock()), maker_id(store)
    held = [t for t in (store.thing(i) for i in object_ids) if t]
    things = [t for t in held if t["object"]["id"] != me]  # his own object is read from his page alone, never as a thing's section
    his, mine = {l["id"] for l in you_lines(store, every=True)}, you_lines(store)[:YOU_MAX] if you else []
    about = {t["object"]["id"]: store.lines(about=t["object"]["id"]) for t in things}
    shown = {t["object"]["id"] for t in things} | {l["id"] for ls in about.values() for l in ls} | {l["id"] for l in mine}
    struck = {l["mark_set_by"] for ls in about.values() for l in ls if l.get("mark") == RESTS and l.get("mark_set_by")}
    groups, cut = [], lambda x: x if len(x) <= 200 else x[:200] + "…"  # each struck line with what rests on it, its words cut short
    for s in sorted(filter(None, map(store.get, struck)), key=lambda s: (s["t"], s["id"])):
        shown.add(s["id"])
        deps = store.rests_on(s["id"])
        act = store.get(s["mark_set_by"]) if s.get("mark_set_by") else None
        words = w.plain("read.you.struck") if s["id"] in his else cut(_said(s))  # a struck line about him: its words never read in
        groups.append(["- " + w.plain("read.struck", len(deps), words=words, who=_who(w, act or s), date=plain(w.date(s.get("mark_since") or s["t"])),
                                      lines=w.count("line", len(deps)))] + ["  - " + w.plain("read.rests", words=cut(_said(d))) for d in deps])
    units = w.raw("read.sep").join(dict.fromkeys(t["object"]["unit"] for t in held))
    newest = max(filter(None, map(store.get, shown)), key=lambda l: (l["t"], l["unit"], l["seq"], l["id"]), default=None)  # the store's order
    stamp = w.plain("read.stamp.from", project=units, id=newest["id"]) if units and newest else w.plain("read.stamp")  # what it knows (R-READ-30)
    top = "\n".join(["# " + w.plain("read.title"), "", stamp, ""])
    left = lambda n: [w.plain("read.corrected.more", n, corrections=w.count("correction", n))] if n else []  # noqa: E731
    fixes = lambda k: ["", "## " + w.plain("read.corrected"), ""] + [x for g in groups[:k] for x in g] + left(len(groups) - k) + [""] if groups else []  # noqa: E731
    size = lambda *parts: len("".join(parts).encode())  # noqa: E731

    def within(rest):  # the corrections, struck line by struck line, while the whole read stays within READ_MAX
        k = 0
        while k < len(groups) and size(top, "\n".join(fixes(k + 1)), rest) <= READ_MAX:
            k += 1
        return "\n".join(fixes(k))
    you = _you(w, mine, cut) if you else ""
    if not things:
        return top + within(you + "\n" + w.plain("read.none") + "\n") + you + "\n" + w.plain("read.none") + "\n"
    more = lambda n: "\n" + w.plain("read.more", n, things=w.count("thing", n)) + "\n" if n else ""  # noqa: E731
    secs, kept = "", 0
    for i, t in enumerate(things):
        sec = "\n" + "\n".join(_section(store, w, t, his)) + "\n"
        if size(top, "\n".join(fixes(0)), you, secs, sec, more(len(things) - i - 1)) > READ_MAX:
            break
        secs, kept = secs + sec, kept + 1
    return top + within(you + secs + more(len(things) - kept)) + you + secs + more(len(things) - kept)
