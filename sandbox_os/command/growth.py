# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""How the maker's vocabulary grows, by proposal and never by the partner's hand (design section 2 points 3 and 4). When the partner meets
a thing that fits no type, it records the thing under the nearest type with a fact saying it fits poorly; when a second such thing comes,
the tool proposes a type, with the two things, the nearest type, a gloss and a ground. Links the partner could not say with any relation
grow a relation the same way, and acts that left the machine that no verb names grow a verb. A proposal is a note in the workshop's queue;
it waits, with the others, for one card a week outside the asking budget, and his yes alone makes it data. The partner may also propose a
type or a relation itself (propose_type, propose_relation), from two instances, or from one in his own words; those only queue too.
The partner creates nothing here. Once a week the tool raises one card carrying the waiting proposals and the types and relations nobody
touched in ninety days (weekly); his answer settles them (settle): yes makes a proposal data by the tool, no keeps the things where they
are, later carries them to next week's card, and words answer each by its number, strike pruning an unused one (design section 2 points
4 and 5). Every refusal says why in plain words."""
import re

from sandbox_os.store import Refused
from sandbox_os.store.line import iso, strip_arabic_marks
from sandbox_os.command import DOWN, TOOL, cards, names, say, words
from sandbox_os.pages.measures import iso_week
from sandbox_os.pages.read import proposals
from sandbox_os.pages.views import STAYED

EVENTS = ("type proposed", "relation proposed", "verb proposed")  # the queue's three events (read.PROPOSED reads the same three)
UNIT = "workshop"  # the queue lives where the vocabulary does


def _bare(s):
    """Words as the maker's are compared: Arabic marks stripped, the spaces between words made one, outer spaces gone, lower case."""
    return " ".join(strip_arabic_marks(str(s)).split()).lower()


def _stands(line):
    return line is not None and line.get("mark") not in DOWN


def _to(fact):  # the thing a link wanted fact names at its other end: its value's to, when the value is an object holding one, else None
    v = ((fact or {}).get("body") or {}).get("value")
    return v["to"] if isinstance(v, dict) and isinstance(v.get("to"), str) else None


def _queue(store, event, body, *, by):
    """Appends one proposal to the queue, as a note in the workshop with its event and its one plain sentence; returns its id."""
    body = dict({"name_from": "your words" if body.get("said") else "the partner's word", "said": None, "nearest": None, "from": None,
                 "to": None, "ground": None}, **body)
    text = say("growth.proposed." + event.split()[0], name=body["name"], n=len(body["instances"]), nearest=str(body.get("nearest")))
    return store.append(UNIT, "note", dict(body, event=event, text=text), by=by)


def _why(store, event, name):
    """The store's own words refusing a proposal's name, the type's or the relation's (Store.may_name, append's check), else None."""
    try:
        store.may_name(NOUNS[event], name) if event in ("type proposed", "relation proposed") else None
    except Refused as e:
        return str(e)


def _refused(store, event, name, why, *, by, proposal=None, **more):
    """A note by the tool that a proposal's name was refused by the store, in the store's words: at queue time (no proposal), or at his
    yes (the proposal named, settled as refused, answer refused)."""
    return store.append(UNIT, "note", dict({"event": "proposal refused", "proposed": event, "name": name, "proposal": proposal, "why": why,
                                            "text": f"the {NOUNS[event]} {name} was " + ("not added on your yes: " if proposal else
                                                    "not proposed, because the store refuses its name: ") + why}, **more), by=by)


def _held(ls):
    """The instances a proposal already lists, waiting or settled (yes, no or refused), and the names, by event, of the proposals waiting
    or answered yes: a yes is never proposed again (the review of batch D, finding 1: a verb, which his yes does not make, came back)."""
    held, waiting = set(), set()
    for p in proposals(ls):
        held |= set((p["line"]["body"] or {}).get("instances") or [])
        if p["state"] in ("waiting", "yes"):
            waiting.add((p["event"], p["name"]))
    return held, waiting


def _type_of(objects, facts, oid):
    """A thing's present type: the newest standing fact with facet type about it (a thing moved to a new type), else its object's own."""
    moved = [f for f in facts.get(oid, []) if (f["body"] or {}).get("facet") == "type" and isinstance(f["body"].get("value"), str)]
    return moved[-1]["body"]["value"] if moved else (objects[oid]["body"] or {}).get("type")


def recur(store, *, by=TOOL):
    """The second recurrence, run by the tool: queues a type, a relation or a verb seen twice, with its instances, and returns the new
    proposals' ids, oldest first. It is idempotent: an instance a proposal already lists, waiting or settled, is never listed again, and
    a name already waiting or answered yes is not queued twice. A type: two or more standing things of one present type whose present fit is a
    standing fact "poor" with its reason, named by the newest would_be the partner gave (with none, nothing is queued). A relation: two or
    more standing "link wanted" facts about distinct pairs whose words match, lower-cased and trimmed. A verb: two or more standing unknown
    acts that left the machine with the same shape, its host and its first word."""
    with store.locked():
        ls = store.lines()
        objects = {l["id"]: l for l in ls if l["kind"] == "object" and _stands(l)}
        facts = {}
        for l in ls:
            if l["kind"] == "fact" and _stands(l) and l.get("about") in objects:
                facts.setdefault(l["about"], []).append(l)
        types = {t["body"]["name"]: t for t in store.types()}
        relations = {r["body"]["name"] for r in store.relations()}
        held, waiting = _held(ls)
        said = {((l["body"] or {}).get("proposed"), l["body"].get("name")) for l in ls if l["kind"] == "note" and _stands(l)
                and (l["body"] or {}).get("event") == "proposal refused" and not l["body"].get("proposal")}
        made = []

        def refused(event, name, instances):  # a name the store would refuse is never queued; the tool says why, once
            why = _why(store, event, name)
            if why and (event, name) not in said:
                said.add((event, name))
                _refused(store, event, name, why, by=by, instances=instances)
            return bool(why)

        groups = {}  # nearest type -> [(object id, its present fit fact)]
        for oid, fs in facts.items():
            fit = [f for f in fs if f["body"].get("facet") == "fit"]
            typ = _type_of(objects, facts, oid)
            if fit and fit[-1]["body"].get("value") == "poor" and typ in types and oid not in held:
                groups.setdefault(typ, []).append((oid, fit[-1]))
        for nearest, got in groups.items():
            got.sort(key=lambda x: (x[1]["t"], x[1]["id"]))
            names = [f["body"]["would_be"] for _, f in got if isinstance(f["body"].get("would_be"), str) and f["body"]["would_be"].strip()]
            if (len(got) < 2 or not names or names[-1] in types or ("type proposed", names[-1]) in waiting
                    or refused("type proposed", names[-1], [o for o, _ in got])):
                continue
            reasons = list(dict.fromkeys(str(f["body"].get("reason")) for _, f in got if f["body"].get("reason")))  # each reason once
            made.append(_queue(store, "type proposed", {
                "name": names[-1], "instances": [o for o, _ in got], "nearest": nearest, "ground": types[nearest]["body"].get("ground"),
                "gloss": f"{nearest}s that are not quite {nearest}s: " + "; ".join(reasons)}, by=by))

        links = {}  # the words, bared -> [link wanted fact], one per distinct pair
        for fs in facts.values():
            for f in fs:
                v = f["body"].get("value")
                if (f["body"].get("facet") == "link wanted" and isinstance(v, dict) and isinstance(v.get("words"), str) and v["words"].strip()
                        and v.get("to") in objects and f["id"] not in held):
                    same = links.setdefault(_bare(v["words"]), [])
                    if (f["about"], v["to"]) not in {(g["about"], g["body"]["value"]["to"]) for g in same}:
                        same.append(f)
        for words, got in links.items():
            name = words.replace(" ", "_")
            if len(got) < 2 or name in relations or ("relation proposed", name) in waiting or refused("relation proposed", name, [f["id"] for f in got]):
                continue
            ends = {(_type_of(objects, facts, f["about"]), _type_of(objects, facts, f["body"]["value"]["to"])) for f in got}
            frm, to = next(iter(ends)) if len(ends) == 1 else (None, None)
            reasons = [str(f["body"].get("reason")) for f in got if f["body"].get("reason")]
            made.append(_queue(store, "relation proposed", {
                "name": name, "instances": [f["id"] for f in got], "from": frm, "to": to,
                "gloss": f"what links one thing to another as \"{words}\"" + (": " + "; ".join(sorted(set(reasons))) if reasons else "")}, by=by))

        acts = {}  # "host: program" -> [unknown act note]
        for l in ls:
            b = l["body"] or {}
            if l["kind"] == "note" and _stands(l) and b.get("event") == "unknown act" and b.get("outcome") not in STAYED and l["id"] not in held:
                shape = b.get("shape") if isinstance(b.get("shape"), list) and b["shape"] else str(b.get("command") or "").split()
                host = b.get("host") or (l.get("by") or {}).get("host")
                if shape and host:
                    acts.setdefault(f"{host}: {shape[0]}", []).append(l)
        for name, got in acts.items():
            if len(got) < 2 or ("verb proposed", name) in waiting:
                continue
            host, program = name.split(": ", 1)
            made.append(_queue(store, "verb proposed", {
                "name": name, "instances": [l["id"] for l in got],
                "gloss": f"the acts of {program} on {host} that left the machine and that no verb names"}, by=by))
        return made


def _his_words(store, said, name):
    """The maker's standing said line a proposal names as his words, holding the name; else refused. None when no said line is named."""
    if said is None:
        return None
    l = store.get(said) if isinstance(said, str) else None
    if not l or l["kind"] != "said" or (l.get("by") or {}).get("kind") != "maker" or not _stands(l):
        raise Refused(f"a proposal in your words names a said line of yours that stands, and {str(said)[:40]!r} is not one; nothing was written")
    if _bare(name) not in _bare((l["body"] or {}).get("words") or ""):
        raise Refused(say("refuse.proposal.name", name=repr(str(name)[:60])))
    return said


def _enough(instances, said, what):
    if not isinstance(instances, (list, tuple)) or any(not isinstance(i, str) for i in instances):
        raise Refused(f"a proposal lists its instances, the ids of the {what}, as a list; nothing was written")
    ids = list(dict.fromkeys(instances))
    if len(ids) < (1 if said else 2):
        raise Refused(say("refuse.proposal.second", what=what, n=len(ids)))
    return ids


def _waiting(store, event, name):
    return next((p["id"] for p in proposals(store.lines(unit=UNIT, kinds=["note"])) if p["state"] == "waiting" and p["event"] == event
                 and _bare(p["name"]) == _bare(name)), None)


def propose_type(store, *, name, nearest, gloss, instances, by, ground=None, said=None):
    """The partner proposes a type, never creates one: a proposal in the queue, waiting for the week's card, with its name (from your words
    when said names a said line of yours that holds it, else the partner's word), the nearest standing type, a gloss, a ground (the nearest
    type's when none is given) and its instances, standing things. Refused for a name a standing type already has, a nearest that is no
    standing type, an instance that is no standing thing, or fewer than two instances without your words (one with them); a waiting
    proposal of the same name is returned, and nothing is queued again. Returns the proposal's id."""
    with store.locked():
        types = {_bare(t["body"]["name"]): t for t in store.types()}
        if not isinstance(name, str) or not name.strip() or _bare(name) in types:
            raise Refused(say("refuse.type.name." + ("taken" if isinstance(name, str) and name.strip() else "none"), name=repr(str(name)[:60])))
        if not isinstance(nearest, str) or _bare(nearest) not in types:
            raise Refused(f"a type proposed names the nearest type it grows from, and {str(nearest)[:60]!r} is no type that stands; nothing was written")
        if why := _why(store, "type proposed", name.strip()):
            raise Refused(f"a type proposed takes a name the store would write, and it refuses this one: {why}")
        said = _his_words(store, said, name)
        ids = _enough(instances, said, "things it would hold")
        if bad := _unfit(store, "type proposed", ids):
            raise Refused(f"each instance of a type proposed is a thing that stands, and {bad} is not one; nothing was written")
        old = _waiting(store, "type proposed", name)
        if old:
            return old
        t = types[_bare(nearest)]["body"]
        return _queue(store, "type proposed", {"name": name.strip(), "nearest": t["name"], "gloss": gloss, "instances": ids, "said": said,
                                               "ground": ground if ground is not None else t.get("ground")}, by=by)


def propose_relation(store, *, name, gloss, instances, by, frm=None, to=None, said=None):
    """The partner proposes a relation, never creates one: a proposal in the queue, waiting for the week's card, with its name (from your
    words when said holds it), a gloss, the types at its two ends when given and its instances, standing "link wanted" facts. Refused for a
    name a standing relation already has, an end that is no standing type, an instance that is no standing link wanted fact, or fewer than
    two instances without your words (one with them); a waiting proposal of the same name is returned. Returns the proposal's id."""
    with store.locked():
        types = {_bare(t["body"]["name"]): t["body"]["name"] for t in store.types()}
        if not isinstance(name, str) or not name.strip() or _bare(name) in {_bare(r["body"]["name"]) for r in store.relations()}:
            raise Refused(say("refuse.relation.name." + ("taken" if isinstance(name, str) and name.strip() else "none"), name=repr(str(name)[:60])))
        for end, v in (("from", frm), ("to", to)):
            if v is not None and (not isinstance(v, str) or _bare(v) not in types):
                raise Refused(f"a relation's {end} end is a type that stands, and {str(v)[:60]!r} is not one; nothing was written")
        if why := _why(store, "relation proposed", name.strip()):
            raise Refused(f"a relation proposed takes a name the store would write, and it refuses this one: {why}")
        said = _his_words(store, said, name.replace("_", " ")) if said is not None else None
        ids = _enough(instances, said, "links it would say")
        if bad := _unfit(store, "relation proposed", ids):
            raise Refused(say("refuse.relation.unfit", bad=str(bad)))
        old = _waiting(store, "relation proposed", name)
        if old:
            return old
        return _queue(store, "relation proposed", {"name": name.strip(), "gloss": gloss, "instances": ids, "said": said,
                                                   "from": types[_bare(frm)] if frm else None, "to": types[_bare(to)] if to else None}, by=by)


# the week's card (batch D, Task 7): one a week, outside the asking budget, raised by the tool, settled by his answer
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")  # Arabic-Indic digits and their eastern forms, read as Western
NOUNS = {"type proposed": "type", "relation proposed": "relation", "verb proposed": "verb"}


def _and(parts, w):
    parts = [p for p in parts if p]
    return w.plain("read.sep").join(parts[:-1]) + w.plain("growth.and") + parts[-1] if len(parts) > 1 else "".join(parts)


def _item(store, p, en):
    """A proposal's line on the week's card: its sentence, then what his yes changes, the things by their names (never their ids), its
    gloss and its ground where it has one, in the strings table's words of the card's language (the review of batch D, finding 5; card 38)."""
    b = p["line"]["body"] or {}
    name = lambda i: (((store.get(i) or {}).get("body") or {}).get("name") if isinstance(i, str) else None) or en.plain("growth.gone")
    got = [store.get(i) or {"body": {}} for i in b.get("instances") or []]
    if p["event"] == "type proposed":
        yes = en.plain("growth.yes.type", things=_and([name(i) for i in b.get("instances") or []], en))
    elif p["event"] == "relation proposed":
        yes = en.plain("growth.yes.relation", pairs=_and([en.plain("growth.pair", frm=name(f.get("about")), to=name(_to(f)) if _to(f)
                                                                   else en.plain("growth.nolink")) for f in got], en))
    else:
        yes = en.plain("growth.yes.verb", acts=_and([str((l["body"] or {}).get("command") or " ".join((l["body"] or {}).get("shape") or []))
                                                     or en.plain("growth.gone") for l in got], en))
    g, ground = b.get("gloss"), b.get("ground")
    plain = en.raw("ground." + ground) if isinstance(ground, str) and ("ground." + ground, "") in en.tab else None
    return "; ".join([b.get("text") or p["name"], yes] + ([en.plain("growth.gloss", gloss=g)] if g else [])
                     + ([en.plain("growth.ground", ground=ground, plain=plain) if plain else en.plain("growth.ground.bare", ground=ground)]
                        if ground else []))


def weekly(store, *, by=TOOL):
    """Once per ISO week of the maker's local days, when a proposal waits or a type or a relation went unused for ninety days, one card in
    the workshop by the tool, outside the asking budget: its items numbered, the waiting proposals oldest first, each with what his yes
    changes (_item), then the unused types, then the unused relations, each a numbered line of what I saw. A week whose card exists raises
    none. Returns the card's id or None."""
    with store.locked():
        week = iso_week(cards.local_day(iso(store.clock())))
        purpose = f"proposals:{week}"
        if any((c["body"] or {}).get("purpose") == purpose for c in store.lines(unit=UNIT, kinds=["card"])):
            return None
        waiting = [p for p in proposals(store.lines(unit=UNIT, kinds=["note"])) if p["state"] == "waiting"]
        un, live = store.unused(), {x["id"] for x in store.types() + store.relations()}
        types, rels = [t for t in un["types"] if t["id"] in live], [r for r in un["relations"] if r["id"] in live]
        w = words(cards.language(store.root))  # card 38: the card in the language the workshop was welcomed in, once, as it is raised
        lines = ([("proposal", p["id"], " ".join(_item(store, p, w).split())) for p in waiting]
                 + [("unused", t["id"], w.plain("card.week.type", name=t["name"], things=w.plain("count.thing", t["objects"]))) for t in types]
                 + [("unused", r["id"], w.plain("card.week.relation", name=r["name"], links=w.plain("count.link", r["links"]))) for r in rels])
        if not lines:
            return None
        p = _and([w.plain("count." + noun, k) for noun in ("type", "relation", "verb") if (k := sum(1 for x in waiting if NOUNS.get(x["event"]) == noun))], w)
        u = _and([w.plain("count.type", len(types)) if types else "", w.plain("count.relation", len(rels)) if rels else ""], w)
        decides = w.plain("growth.and").join(([w.plain("card.week.add", p=p)] if p else []) + ([w.plain("card.week.strike", u=u)] if u else []))
        return cards.raise_(store, UNIT, {
            "decides": decides, **{k: w.plain("card.week." + k) for k in ("stand", "other", "wrong")},
            "saw": "\n".join(f"{i}. {text}" for i, (_, _, text) in enumerate(lines, 1)), "answers": ["yes", "no", "later"],
            "about": UNIT, "purpose": purpose, "week": week,
            "items": [{"n": i, "kind": kind, "id": oid} for i, (kind, oid, _) in enumerate(lines, 1)]}, by=by, of_the_week=True)


def _strike_words():
    from sandbox_os.pages.words import table
    row = table().get(("growth.strike", "")) or {}
    return {cards.plain(row[g]) for g in ("en", "ar") if row.get(g)} | {"strike"}


from sandbox_os.store.answers import read_choice  # noqa: E402,F401 (one strict reader, the store's: Astra's challenge of batch D, finding 2)


def _thing(store, i):  # the standing object a line id names, else None
    return o if isinstance(i, str) and _stands(o := store.get(i)) and o["kind"] == "object" else None


def _unfit(store, event, ids):
    """The first instance unfit for its proposal, by its thing's name, else None: for a type a thing that stands and is no type or
    relation, for a relation a standing link wanted fact between two things that stand (R-READ-9). No line's id is said (Codex 14a)."""
    for i in ids:
        o, f = _thing(store, i), store.get(i) if isinstance(i, str) else None
        if not ((o and (o["body"] or {}).get("type") not in ("type", "relation")) if event == "type proposed" else (_stands(f) and f["kind"]
                == "fact" and (f["body"] or {}).get("facet") == "link wanted" and _thing(store, f.get("about")) and _thing(store, _to(f)))):
            n = ((o or _thing(store, (f or {}).get("about")) or {}).get("body") or {}).get("name")
            return repr(str(n)[:60]) if n else "one of the things named"


def _make(store, p, answer_id, by):
    """A proposal made data by the tool on his yes: a type, with the type fact that moves each instance to it; a relation, with the links its
    instances wanted; for a verb, a note asking the partner to draft it with propose_verb, since a verb's facets are read with him first.
    Every instance is checked before the first write, and a body that does not read or an unfit instance is refused with nothing written;
    a fault midway stops the start, and the next start writes only what is not there yet (R-READ-9)."""
    src, out = f"your answer {answer_id} on the week's card", []
    try:
        b = p["line"]["body"]
        name, ids = b["name"], list(b.get("instances") or [])
        bad = p["event"] != "verb proposed" and _unfit(store, p["event"], ids)
        made = name in {x["body"]["name"] for x in (store.types() if p["event"] == "type proposed" else store.relations())}
    except (AttributeError, KeyError, TypeError):
        raise Refused("its words in the record do not read as a proposal, so there was nothing to make and nothing was written") from None
    if bad:
        raise Refused(say("refuse.make." + ("thing" if p["event"] == "type proposed" else "link"), bad=str(bad)))
    if p["event"] == "type proposed":
        if not made:
            near = ({t["body"]["name"]: t for t in store.types()}.get(b.get("nearest")) or {}).get("body") or {}
            out.append(store.append(UNIT, "object", {"type": "type", "name": name, "group": near.get("group"), "gloss": b.get("gloss"),
                                                     "ground": b.get("ground"), "parent": b.get("nearest")}, by=by))
        for o in ids:
            had = [tuple(map((f["body"] or {}).get, ("facet", "value", "source"))) for f in store.lines(about=o, kinds=["fact"]) if _stands(f)]
            if ("type", name, src) not in had:  # a fact a stopped start already wrote is not written twice
                out.append(store.append(store.get(o)["unit"], "fact", {"facet": "type", "value": name, "basis": "I read it in", "source": src},
                                        by=by, about=o))
    elif p["event"] == "relation proposed":
        if not made:
            out.append(store.append(UNIT, "object", {"type": "relation", "name": name, "gloss": b.get("gloss"), "from": b.get("from"),
                                                     "to": b.get("to")}, by=by))
        have = {tuple(map(l["body"].get, ("from", "rel", "to"))) for l in store.lines(kinds=["link"]) if _stands(l)}
        for f in map(store.get, ids):
            if (f["about"], name, _to(f)) not in have:
                out.append(store.link(f["about"], name, _to(f), by=by))
    else:
        out.append(store.append(UNIT, "note", {"event": "verb asked for", "shape": b["name"], "proposal": p["id"],
                                               "text": f"you said yes to a verb for {b['name']}; the partner drafts it with propose_verb"}, by=by))
    return out


def _settled(store, p, said, card, answer_id, by):
    what = say({"yes": "growth.settled.verb" if p["event"] == "verb proposed" else "growth.settled.yes", "no": "growth.settled.no"}[said])
    return store.append(UNIT, "note", {"event": "proposal settled", "proposal": p["id"], "answer": said, "card": card, "from_answer": answer_id,
                                       "text": f"{p['name']}: {what}, on your answer to the week's card"}, by=by)


def _unread(store, card, d, by):
    """Words on the week's card that do not read item by item: named once, nothing applied."""
    if any((l["body"] or {}).get("event") == "week card unread" and l["body"].get("answer") == d["id"] for l in store.lines(unit=UNIT, kinds=["note"])):
        return []
    return [store.append(UNIT, "note", {"event": "week card unread", "card": card["id"], "answer": d["id"],
                                        "text": say("note.week.unread", words=str(d["body"].get("words"))[:120])}, by=by)]


def settle(store, *, by=TOOL):
    """Every week's card with a binding answer, read first and applied after: yes speaks for every proposal it lists, no declines each,
    later postpones all, and words are read item by item (read_choice), yes and no only on proposals and strike only on unused types and
    relations; words that do not read so apply nothing and are named once in a week card unread note. Per item, his newest word across
    every card that lists it is the one applied (Astra's challenge of batch D, finding 4); a newer word on a proposal another answer already
    settled otherwise is not undone here, an undo being its own path, and a note by the tool names both answers, once. A strike is the
    tool's record of his, naming his answer (Store.strike's answer), once per answer and item, and a type he restored is struck again only
    on his fresh words (_fresh). A proposal the store refuses at his yes is settled as refused, in a proposal refused note with the
    store's words, and the rest go on (the review of batch D, finding 2). Returns the ids written, oldest first."""
    out, newest = [], {}  # item id -> (his answer, the card, its number there, his word on it)
    with store.locked():
        for card in [c for c in store.lines(unit=UNIT, kinds=["card"]) if (c["body"] or {}).get("week_card") is True and _stands(c)]:
            d, items = cards.decision(store, card["id"]), {i["n"]: i for i in card["body"].get("items") or []}
            said = ((d or {}).get("body") or {}).get("answer")
            if said is None:
                continue
            choice = ({k: said for k, i in items.items() if said == "later" or i["kind"] == "proposal"} if said in ("yes", "no", "later")
                      else read_choice(d["body"].get("words"), len(items)))
            if choice is None or any(v != "later" and (v == "strike") != (items[k]["kind"] == "unused") for k, v in choice.items()):
                out += _unread(store, card, d, by)
                continue
            for k, v in choice.items():
                was = newest.get(items[k]["id"])
                if was is None or cards._after(d, was[0]):
                    newest[items[k]["id"]] = (d, card, k, v)
        state = {p["id"]: p for p in proposals(store.lines(unit=UNIT, kinds=["note"]))}
        for i, (d, card, k, v) in sorted(newest.items(), key=lambda x: (x[1][1]["seq"], x[1][2])):
            p, t = state.get(i), store.get(i)
            if v in ("yes", "no") and p and p["state"] == "waiting":
                try:
                    made = _make(store, p, d["id"], by) if v == "yes" else []
                except Refused as e:  # that one settled as refused, in the store's words; the rest go on; another fault stops the start (R-READ-9)
                    out.append(_refused(store, p["event"], p["name"], str(e), by=by, proposal=p["id"], answer="refused", card=card["id"],
                                        from_answer=d["id"]))
                    continue
                out += made + [_settled(store, p, v, card["id"], d["id"], by)]
            elif v in ("yes", "no") and p and (v == "yes") != (p["state"] == "yes"):
                out += _not_applied(store, p, v, card, d, by)
            elif v == "strike" and _stands(t) and not _struck_refused(store, d["id"], t["id"]) and _fresh(store, d, t["id"]):
                try:
                    out.append(store.strike(t["id"], by=by, answer=d["id"],
                                            why=f"your answer {d['id']} on the week's card: strike {t['body'].get('name')}, unused for ninety days"))
                except Refused as e:  # recorded once per answer and item, in the store's words; the rest of his answer goes on (the review of batch D)
                    name = t["body"].get("name")
                    out.append(store.append(UNIT, "note", {"event": "proposal refused", "proposed": "strike", "name": name, "proposal": None, "item": t["id"],
                                                           "why": str(e), "card": card["id"], "from_answer": d["id"], "answer": "refused",
                                                           "text": f"the strike of {name} on your answer was refused by the store: {e}"}, by=by))
    return out


def _not_applied(store, p, said, card, d, by):
    """His newer word on a proposal an older answer already settled otherwise: named once, in a note by the tool naming both answers."""
    ls = store.lines(unit=UNIT, kinds=["note"])
    if any((l["body"] or {}).get("event") == "answer not applied" and l["body"].get("from_answer") == d["id"] and l["body"].get("proposal") == p["id"] for l in ls):
        return []
    old = (next((l for l in ls if l["id"] == p["settled"]), None) or {"body": {}})["body"].get("from_answer")
    return [store.append(UNIT, "note", {"event": "answer not applied", "proposal": p["id"], "said": said, "card": card["id"], "from_answer": d["id"],
                                        "applied": old, "text": say("note.answer.notapplied", name=p["name"], answer=d["id"], said=str(said), old=str(old), state=p["state"])}, by=by)]


def _struck_refused(store, answer, item):
    """Whether the store already refused this item's strike on this answer: said once, not on every run."""
    return any((l["body"] or {}).get("event") == "proposal refused" and l["body"].get("proposed") == "strike" and l["body"].get("from_answer") == answer
               and l["body"].get("item") == item for l in store.lines(unit=UNIT, kinds=["note"]))


def _fresh(store, d, item):
    """Whether his answer d may still strike this item: it struck nothing here before (the tool's strike line names the answer it applied,
    so each answer strikes an item once), and it came after his last taking back of a strike of the item (a strike or a delete of it
    undone), so a type he restored is struck again only on his fresh words (Astra's challenge of batch D, finding 3)."""
    mine = {l["id"]: l for l in store.lines(kinds=["strike"]) if (l["body"] or {}).get("target") == item}
    if any(l["body"].get("answer") == d["id"] for l in mine.values()):
        return False
    back = [l for l in store.lines(kinds=["unstrike", "delete"]) if (l["body"] or {}).get("target") in mine]
    return not back or cards._after(d, back[-1])


def catch_up(store, *, by=TOOL):
    """The week's run, called from the measures' catch-up after the kill rule: his answers settled first, the aliases his which answers
    taught (names.settle) before the week's card's, then the second recurrence, then this week's card when it is due. Returns {"queued":
    [...], "card": id or None, "settled": [...]}."""
    settled = names.settle(store, by=by) + settle(store, by=by)
    queued = recur(store, by=by)
    return {"queued": queued, "card": weekly(store, by=by), "settled": settled}
