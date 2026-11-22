# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The partner's tools over MCP (R-HOSTS-27 to 30): one local stdio server, `sandbox mcp --workshop <root>`, JSON-RPC 2.0 with one
object per line and nothing else on standard output. It keeps nothing between calls: each call carries its unit, host, session and
model, and opens the record afresh. Every tool reads, proposes or records as the partner, through the command's calls and the
store's; the never list is refused by name; every refusal is a note by the tool, written before the refusal goes back.

    dispatch(root, name, args) -> {"ok": True, "result": ...} | {"ok": False, "refused": why}    serve(stdin, stdout, root)    main(argv)
    tools(store=None, unit=None, things=()) -> [tool]: the base tools, and with a store the verb tools that fit the things in hand
    maker_names(store) -> set: the welcome's name for the maker, as a guess about a person is compared with it
    his_names(store) -> set: the welcome's name and his flagged object's name and aliases, as a person the partner names is compared with them"""
import contextlib, json, os, sys

from sandbox_os import VERSION, store as _store
from sandbox_os.store import Refused
from sandbox_os.store.line import BASES, UNIT_RE, strip_arabic_marks
from sandbox_os.store.verbs import ACTS, PROPOSED, RECEIPTS, fitting, simple
from sandbox_os.command import TOOL, DOWN, say, cards, grants, growth, knowing, names, runs, verbs
from sandbox_os.hosts.boundary import input_hash, locate, needs
from sandbox_os.pages.words import Words

VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")  # the protocol versions this server answers, the newest last
S, N, L = {"type": "string"}, {"type": "integer", "minimum": 1}, {"type": "array", "items": {"type": "string"}}
OPEN = {"type": "object"}  # an object whose keys are the verb's own, checked by the store and the command, never by the schema
COMMON = {"unit": S, "host": S, "session": S, "model": S, "workshop": S}
CHECKS = {"type": "array", "items": {"type": "object", "properties": {"name": S, "command": S}, "required": ["name", "command"], "additionalProperties": False}}
SCOPE = {"type": "object", "properties": {"unit": S, "paths": L, "services": L, "verbs": L}, "required": ["unit", "paths", "services"],
         "additionalProperties": False}  # verbs: the ids of declared verbs, none of the five acts, that the grant covers (grants.read_back)
MOMENTS = {"type": "string", "enum": ["run-start", "before-card", "before-act", "before-ruling"]}  # the four set moments runs.moment names
ONE = lambda *words: {"type": "string", "enum": list(words)}  # noqa: E731  a string that is one of a few words
VOCAB = ("type", "relation")  # the vocabulary's own two types, as the store's _may_object names them: a thing of either is never named here
NEVER = {n: say("mcp.never." + n) for n in (  # what the partner's tools never do, each refusal in the table's words
    "accept", "receipt", "erase", "undelete", "grant", "grant_back", "answer_grant", "create_type", "create_relation", "run_verb", "guess_about_maker",
    "belief_without_basis", "settings", "hooks", "skills", "fork", "snapshot", "import")}
GUESS, BASIS = NEVER["guess_about_maker"], say("mcp.basis")


def _said(s, a, said):
    """The maker's said line of this host and session that a call rests on, or refused."""
    l = s.get(said) if isinstance(said, str) else None
    b = (l or {}).get("body") or {}
    if not l or l["kind"] != "said" or l["by"]["kind"] != "maker" or l["mark"] in DOWN or (b.get("session"), b.get("host")) != (a["session"], a["host"]):
        raise Refused(f"{str(said)[:40]!r} is not a line of the maker's own words in this session ({a['session'][:40]}) of {a['host'][:40]}; nothing was written")
    return l


def _get(s, i, kind=None):
    l = s.get(i) if isinstance(i, str) else None
    if not l or kind and l["kind"] != kind:
        raise Refused(f"no {kind or 'line'} has the id {str(i)[:40]!r}")
    return l


def _read_back(s, a, by):
    _said(s, a, a["said"])
    g, c = grants.read_back(s, a["sentence"], by=by, unit=a["unit"], reading=a["reading"], scope=a["scope"], said=a["said"])
    return {"grant": g, "card": c}


def _open_run(s, a):
    """A run still open, or refused: a closed or abandoned run takes no check and no second end."""
    run = _get(s, a["run"], "run")
    if runs._ends(s, run["id"]):
        raise Refused("this run is closed; what it still needs goes into a next run")
    return run


def _inside(s, run, name, command):
    """A check's command, refused when it needs more than the working copy: one of the five acts, a write to the fence or outside the
    project, a service; it waits for the host's own ask or the maker's grant. The refusal names the check and the act, never the
    command's text, which may carry a secret and which the refusal's note keeps only as a hash."""
    act = needs(s.root, run["unit"], "Bash", {"command": command})
    if act:
        raise Refused(Words("en").plain("check.act", name=repr(str(name)[:80]), act=act))
    v = s.verb_for(simple(command)) if isinstance(command, str) else None  # a declared verb the five-act words miss is still a verb
    if v and s.door(v["id"], run["unit"])["door"] != "inside":
        raise Refused(Words("en").plain("check.verb", never=NEVER["run_verb"], name=repr(str(name)[:80]), verb=repr(str(v["name"])[:80])))


def _check(s, a, by):
    """The tool runs a check in the project's working copy, as runs.check does, under any name the run needs; a command that needs more
    than the working copy never runs as a check."""
    run = _open_run(s, a)
    _inside(s, run, a["name"], a["command"])
    c = runs.check(s, a["run"], a["name"], a["command"])
    return {"check": c, "exit": s.get(c)["body"]["exit"], "passes": runs.passes(s, a["run"])}


def _close(s, a, by):
    """A run closed with the checks that stand for what it claims, named now and run by the tool then; the whole close is refused, with
    nothing run or written, when any of them needs more than the working copy. The reply names each red check (an exit other than 0) with
    its exit, in the order they ran, in red and in its sentence; an honest close may carry one (ruling row 11; R-READ-7). Each one not run,
    where no sandbox starts, is named in not_run and its sentence; passed is said only when every check named exited 0."""
    run = _open_run(s, a)
    for c in a.get("checks", []):
        _inside(s, run, c["name"], c["command"])
    c = runs.close(s, run["id"], by=by, outcome=a["outcome"], text=a["text"], learned=a["learned"], changed=a["changed"], checks=a.get("checks", []))
    ran = [(x["name"], s.get(x["check"])["body"]["exit"]) for x in s.get(c)["body"]["checks"]]
    red, out, say = [{"name": n, "exit": e} for n, e in ran if e not in (0, None)], [n for n, e in ran if e is None], Words("en").plain
    text = " ".join([say("mcp.close.red", checks=", ".join(f"{x['name']} (exit {x['exit']})" for x in red))] * bool(red)
                    + [say("mcp.close.notrun", names=", ".join(out))] * bool(out))
    return {"close": c, "red": red, "not_run": out, "text": text or say("mcp.close.passed" if ran else "mcp.close.none")}


def _delete(s, a, by):
    """The store bounds it: inside a standing grant on the line's unit whose scope names the delete service (card 15), else only the
    partner's own unseen line of the open run; any other grant is never passed, and the store's refusal says why."""
    t, named = _get(s, a["id"]), lambda sc: sc.get("unit") == t["unit"] and isinstance(sc.get("services"), list) and "delete" in sc["services"]
    g = next((g["id"] for g in grants.standing(s, t["unit"]) if named((g["body"] or {}).get("scope") or {})), None)
    return {"delete": s.delete(a["id"], by=by, grant=g)}


def _answer(s, a, by):
    """The partner's report of an answer: person not established, binding nothing (the maker's own words bind through the hook, by
    cards.answer_from_said). A grant's read-back card takes no report at all."""
    card = _get(s, a["card"], "card")
    if str((card["body"] or {}).get("purpose")).startswith("grant:"):
        raise Refused(NEVER["answer_grant"])
    return {"answer": cards.answer(s, a["card"], a.get("answer"), by=by, words=a.get("words"), session=a["session"], host=a["host"], report=True)}


def _needless(s, a, by):
    if cards.plain(_said(s, a, a["said"])["body"].get("words")) not in cards.NEEDLESS:
        raise Refused("the maker's words here are not the word needless")
    return {"needless": cards.needless(s, a["answer"], by=by, session=a["session"])}


def _grant_back(s, a, by):
    g, l = _get(s, a["grant"], "grant"), _said(s, a, a["said"])
    word = (g["body"] or {}).get("take_back") or "back"
    if cards.plain(l["body"].get("words")) != cards.plain(word):
        raise Refused(f"a grant is taken back by the maker's own word for it ({word!r}), and these words are not it")
    if not cards.said_for(s, g, a["session"], l["body"]["words"], a["said"]):
        raise Refused("the maker's word does not rest on a line typed in this session")
    return {"grant_back": grants.take_back(s, a["grant"], by=by, words=l["body"]["words"], session=a["session"])}


def _bare(name):
    """A name as the maker's is compared: Arabic marks stripped (as the store's resolve strips them), outer spaces gone, lower case."""
    return strip_arabic_marks(str(name)).strip().lower()


def maker_names(store):
    """The name the welcome gives the maker ("What to call you:"), bared; empty when the welcome is absent or names nobody."""
    from sandbox_os.pages.frame import welcome_answers
    try:
        with open(os.path.join(store.root, "welcome.md"), encoding="utf-8") as f:
            name = _bare(welcome_answers(f.read(), Words("en")).get("name") or "")
    except OSError:
        return set()
    return {name} if name else set()


def his_names(store):
    """Every name the maker goes by, bared: the welcome's, and his flagged object's own name and aliases when it is recorded."""
    from sandbox_os.pages.read import maker_id
    me = maker_id(store)
    t = (store.thing(me) or {}) if me else {}
    return maker_names(store) | {_bare(n) for n in [t.get("name"), *t.get("aliases", [])] if isinstance(n, str) and n.strip()}


def _thing(s, a, by):
    """A thing's read (Store.thing) and its short read (03-design.md section 4 point 7), by its id or by the words that name it
    (Store.resolve, the vocabulary's own types and relations left out): one match is that thing, and so is the one of several his answer
    taught these words mean (pages.read.chosen, Astra's finding 6 of batch D); several else are asked about once, none is refused, and
    words that name only the vocabulary answer no thing. The partner never guesses; a read handed is recorded by the tool (handed), and
    nothing else is written (Task 13's read_thing, folded in at Task 14)."""
    from sandbox_os.pages.read import chosen, render_read
    if a.get("id") is not None:
        if s.thing(a["id"]) is None:
            raise Refused(f"no thing has the id {a['id'][:40]!r}; a thing is read by its id or by the words that name it")
        handed(s, a["id"], a["session"])
        return {"thing": s.thing(a["id"]), "read": render_read(s, [a["id"]]), "things": [a["id"]]}
    if a.get("words") is None:
        raise Refused("a thing is read by its id or by the words that name it")
    hits = s.resolve(a["words"])
    found = [x for x in hits if x["type"] not in VOCAB]
    if not hits:
        raise Refused("no thing is named so; the partner names it with the maker, it never guesses")
    pick = chosen(s, a["words"], found) if len(found) > 1 else None  # the one his answer taught these words mean (pages.read.chosen)
    found = [pick] if pick else found
    if len(found) == 1:
        handed(s, found[0]["id"], a["session"])
        return {"thing": s.thing(found[0]["id"]), "read": render_read(s, [found[0]["id"]]), "things": [found[0]["id"]]}
    if found:
        return {"candidates": found, "ask": "which one: ask once", "things": [x["id"] for x in found]}
    return {"things": [], "vocabulary": "these words name the vocabulary's own type or relation, never a thing of the maker's world"}


def handed(s, thing, session=None):
    """The read of a thing handed to the partner, its id: a note by the tool in its unit about it, its present facts as handed (a secret's
    hold no value) and the call's session (batch E); None, writing nothing, when that session's newest standing read held the same facts
    and no said line of his in that session was written after it (his sentence re-opens the read: the review of batch E, finding 3), read
    by cards._after (by sequence within a unit, by time across units)."""
    from sandbox_os.command.cards import _after
    t = s.thing(thing)
    facets, unit = [{"facet": k, "value": f["value"], "basis": f["basis"], "line": f["line"]} for k, f in t["facets"].items()], t["object"]["unit"]
    was = [l for l in s.lines(unit=unit, kinds=["note"], about=thing) if l["by"]["kind"] == "tool" and l["mark"] not in DOWN
           and l["body"].get("event") == "read" and l["body"].get("session") == session]
    again = was and session is not None and any(_after(l, was[-1]) for l in s.lines(kinds=["said"]) if l["by"]["kind"] == "maker"
                                                and l["mark"] not in DOWN and (l["body"] or {}).get("session") == session)
    return None if was and was[-1]["body"].get("facets") == facets and not again else s.append(unit, "note", {"event": "read", "facets": facets, **(
        {"session": session} if session else {}), "text": Words("en").plain("mcp.read.handed", name=str(t["name"]))}, by=TOOL, about=thing)


def _things(s, a, by):
    """The standing things of the whole workshop: by the words that name them (Store.resolve), or by type, or with no standing line of a
    kind about them in the last so many days (Store.things); the vocabulary's own types and relations only when their type is asked
    (Task 13's find_things, folded in at Task 14)."""
    if a.get("words") is not None and a.get("without") is not None:
        raise Refused("things are found by the words that name them or by a kind of line they lack, not both at once; nothing was read")
    if a.get("days") is not None and a.get("without") is None:
        raise Refused("days counts back the window for without, the kind of line a thing lacks, and this call names no without")
    found = s.resolve(a["words"]) if a.get("words") is not None else s.things(type=a.get("type"), without=a.get("without"), days=a.get("days"))
    return [x for x in found if x["type"] == a["type"]] if a.get("type") is not None else [x for x in found if x["type"] not in VOCAB]


def _name(s, a, by):
    """A thing of the maker's world named in the call's unit, as the partner; the vocabulary is recorded the first time (Store.seed, once).
    A type the workshop does not know is refused with the types it does, in words a newcomer reads (R-READ-8)."""
    if a["type"] in VOCAB:
        raise Refused(NEVER["create_" + a["type"]])
    if a["type"] == "person" and _bare(a["name"]) in his_names(s):  # a person named like him is him: his page holds every line about him
        from sandbox_os.pages.write import maker_object
        return {"thing": maker_object(s), "maker": True}
    s.seed(by=TOOL)
    if a["type"] not in (known := sorted({t["body"]["name"] for t in s.types()})):
        raise Refused(Words("en").plain("mcp.thing.type", count=len(known), known=", ".join(known), given=repr(a["type"][:60])))
    body = dict({"type": a["type"], "name": a["name"]}, **({"ground": a["ground"]} if "ground" in a else {}))
    return {"thing": s.append(a["unit"], "object", body, by=by)}


def _believe(s, a, by):
    """A belief about a thing, as a fact line with its basis, in the call's unit; never a guess about the maker, never without a basis. The
    thing is named as thing (batch C's name) or as about (batch B's), one id either way."""
    basis = a.get("basis")
    if basis not in BASES:
        raise Refused(BASIS.format(basis="none" if basis is None else repr(basis[:40])))
    if "thing" in a and "about" in a and a["thing"] != a["about"]:
        raise Refused("a belief is about one thing, named as thing or as about; this call names two, so nothing was written")
    about = a.get("thing", a.get("about"))
    if about is None:
        raise Refused("a belief is about a thing, named by its id as thing; this call names none, so nothing was written")
    o = s.get(about)
    if not o or o["kind"] != "object":
        raise Refused(f"a belief is about a thing, named by its id; {about[:40]!r} names no thing, so nothing was written")
    if (o["body"] or {}).get("type") in VOCAB:
        raise Refused(Words("en").plain("mcp.believe.vocab", name=repr(str((o["body"] or {}).get("name"))[:40]), kind=o["body"]["type"]))
    if basis == "my guess":  # any person, whatever the name (design section 6 point 7); the welcome's name, on a thing of any type, is the floor
        t = s.thing(o["id"]) or {}
        if (o["body"] or {}).get("type") == "person" or {_bare(n) for n in [t.get("name"), *t.get("aliases", [])] if n is not None} & maker_names(s):
            raise Refused(GUESS)
    f = knowing.believe(s, a["unit"], o["id"], a["facet"], a["value"], basis, by=by, source=a.get("source"), confidence=a.get("confidence"))
    return {"fact": f, "id": f}


def _propose_act(s, a, by):
    """An act of a declared verb proposed with its dry run (verbs.propose): a card, or a note naming the grant; the act is never run here."""
    return verbs.propose(s, a["unit"], a["verb"], a["params"], by=by, about=a.get("about"), undoes=a.get("undoes"), host=a["host"],
                         session=a["session"])


def _propose_verb(s, a, by):
    """A new verb proposed (verbs.propose_verb): a line of kind verb, queued for the week's card; it is no verb and asks nothing until his yes."""
    return {"id": verbs.propose_verb(s, a["unit"], {k: a[k] for k in PROPOSED if k in a}, by=by), "queued": "for the week's card"}


def _propose_type(s, a, by):
    """A type proposed (growth.propose_type): queued for the week's card in his words when said names his line of this session, never created."""
    said = _said(s, a, a["said"])["id"] if "said" in a else None
    return {"proposal": growth.propose_type(s, name=a["name"], nearest=a["nearest"], gloss=a["gloss"], instances=a["instances"], by=by,
                                            ground=a.get("ground"), said=said), "waits": "the week's card"}


def _propose_relation(s, a, by):
    """A relation proposed (growth.propose_relation): queued for the week's card, its instances link wanted facts, never created."""
    said = _said(s, a, a["said"])["id"] if "said" in a else None
    return {"proposal": growth.propose_relation(s, name=a["name"], gloss=a["gloss"], instances=a["instances"], by=by, frm=a.get("from"),
                                                to=a.get("to"), said=said), "waits": "the week's card"}


def _raised(c):
    return {"card": c} if c else {"card": None, "applied": "asked before and ruled or called needless on this unit and purpose; applied, not asked again"}


TOOLS = {  # name: (its arguments, the required ones, its call); its description is the strings table's row mcp.tool.<name>
    "find": ({"query": S, "kinds": L, "limit": N}, ["query"],
              lambda s, a, by: s.find(a["query"], unit=a["unit"], kinds=a.get("kinds"), limit=min(a.get("limit", 20), 100))),
    "lines": ({"kinds": L, "since": S, "limit": N}, [],
               lambda s, a, by: s.lines(unit=a["unit"], kinds=a.get("kinds"), since=a.get("since"))[-min(a.get("limit", 50), 500):]),
    "line": ({"id": S}, ["id"], lambda s, a, by: _get(s, a["id"])),
    "present": ({}, [], lambda s, a, by: s.present(a["unit"])),
    "grants_standing": ({}, [], lambda s, a, by: grants.standing(s, a["unit"])),
    "cards_open": ({}, [], lambda s, a, by: cards.open_cards(s, a["unit"])),
    "recall": ({"purpose": S, "at": MOMENTS}, ["purpose", "at"], lambda s, a, by: s.get(runs.moment(s, a["at"], a["unit"], a["purpose"], by=by))),
    "card_raise": ({"decides": S, "stand": S, "other": S, "wrong": S, "saw": S, "about": S, "purpose": S, "before_act": S},
                    ["decides", "stand", "other", "wrong", "saw"],
                    lambda s, a, by: _raised(cards.raise_(s, a["unit"], dict({k: a[k] for k in ("decides", "stand", "other", "wrong", "saw", "about", "purpose",
                                                                                         "host", "session") if k in a}, answers=["yes", "no", "later"]),
                                                          by=by, before_act=a.get("before_act")))),
    "run_open": ({"purpose": S, "about": S, "serves": S, "assumptions": L}, ["purpose"],
                  lambda s, a, by: {"run": runs.open_(s, a["unit"], a["purpose"], by=by, about=a.get("about"), serves=a.get("serves"),
                                                      assumptions=a.get("assumptions", ()))}),
    "grant_read_back": ({"sentence": S, "reading": S, "scope": SCOPE, "said": S}, ["sentence", "reading", "scope", "said"], _read_back),
    "note": ({"text": S}, ["text"], lambda s, a, by: {"id": s.append(a["unit"], "note", {"text": a["text"]}, by=by)}),
    "finding": ({"text": S}, ["text"], lambda s, a, by: {"id": s.append(a["unit"], "finding", {"text": a["text"]}, by=by)}),
    "check": ({"run": S, "name": S, "command": S}, ["run", "name", "command"], _check),
    "run_close": ({"run": S, "outcome": S, "text": S, "learned": S, "changed": S, "checks": CHECKS},
                   ["run", "outcome", "text", "learned", "changed"], _close),
    "run_abandon": ({"run": S, "tried": S, "learned": S, "changed": S}, ["run", "tried", "learned", "changed"],
                     lambda s, a, by: {"abandoned": runs.abandon(s, _open_run(s, a)["id"], by=by, tried=a["tried"], learned=a["learned"], changed=a["changed"])}),
    "strike": ({"id": S, "why": S}, ["id", "why"], lambda s, a, by: {"strike": s.strike(a["id"], by=by, why=a["why"])}),
    "delete": ({"id": S}, ["id"], _delete),
    "answer_report": ({"card": S, "answer": S, "words": S}, ["card", "answer"], _answer),
    "needless_report": ({"answer": S, "said": S}, ["answer", "said"], _needless),
    "grant_back_report": ({"grant": S, "said": S}, ["grant", "said"], _grant_back),
    "thing": ({"id": S, "words": S}, [], _thing),
    "things": ({"type": S, "without": S, "days": N, "words": S}, [], _things),
    "thing_name": ({"type": S, "name": S, "ground": S}, ["type", "name"], _name),
    "believe": ({"thing": S, "about": S, "facet": S, "value": S, "basis": ONE(*BASES), "source": S, "confidence": ONE("likely", "unsure")},
                ["facet", "value", "basis"], _believe),
    "propose_act": ({"verb": S, "params": {"anyOf": [OPEN, {"type": "array", "items": OPEN}]}, "about": S, "undoes": S}, ["verb", "params"],
                    _propose_act),
    "propose_verb": ({"name": S, "service": S, "params": {"type": "object", "additionalProperties": S}, "act": ONE(*ACTS, "none"),
                      "inside": {"type": "boolean"}, "shapes": {"type": "array", "items": L},
                      "dry_run": {"type": "object", "properties": {"shows": S, "command": L}, "required": ["shows"], "additionalProperties": False},
                      "receipt": {"type": "object", "properties": {"kind": ONE(*RECEIPTS), "pattern": S}, "required": ["kind"],
                                  "additionalProperties": False}, "why": S, "seen": L},
                     ["name", "service", "params", "act", "shapes", "dry_run", "receipt", "why"], _propose_verb),
    "propose_type": ({"name": S, "nearest": S, "gloss": S, "ground": S, "instances": L, "said": S},
                     ["name", "nearest", "gloss", "instances"], _propose_type),
    "propose_relation": ({"name": S, "gloss": S, "from": S, "to": S, "instances": L, "said": S}, ["name", "gloss", "instances"], _propose_relation),
    "ask_which": ({"words": S}, ["words"], lambda s, a, by: names.ask(s, a["unit"], a["words"], by=by)),
    "propose_goal": ({"text": S, "fragments": L, "shows": S, "about": S, "supersedes": S}, ["text", "fragments"],
                     lambda s, a, by: {"goal": knowing.propose_goal(s, a["unit"], a["text"], a["fragments"], by=by, about=a.get("about"),
                                                                     shows=a.get("shows"), supersedes=a.get("supersedes"))}),
    "assume": ({"text": S, "about": S, "run": S}, ["text"],
               lambda s, a, by: {"assumption": knowing.assume(s, a["unit"], a["text"], by=by, about=a.get("about"), run=a.get("run"))}),
    "open_question": ({"text": S, "settles": S, "cost": S, "until": S, "about": S, "blocks": ONE("yes", "no")}, ["text", "settles", "cost", "until"],
                      lambda s, a, by: {"question": knowing.open_question(s, a["unit"], a["text"], a["settles"], a["cost"], a["until"], by=by,
                                                                          about=a.get("about"), blocks=a.get("blocks") == "yes")}),
    "settle_question": ({"question": S, "how": ONE(*knowing.ENDS), "line": S, "why": S}, ["question", "how"],
                        lambda s, a, by: {"settled": knowing.settle_question(s, a["question"], a["how"], by=by, line=a.get("line"), why=a.get("why"))}),
    "premortem": ({"text": S, "about": S, "run": S}, ["text"],
                  lambda s, a, by: {"premortem": knowing.premortem(s, a["unit"], a["text"], by=by, about=a.get("about"), run=a.get("run"))}),
}


def _skill_used(s, a, by):
    """A skill's use, said by the partner: a note in the call's unit, refused for a name that is no skill folder at the root or the unit."""
    n, bases = a["name"], [s.root] + ([os.path.join(s.root, "projects", a["unit"])] if a["unit"] != "workshop" else [])
    if n in ("", ".", "..") or os.path.basename(n) != n or not any(os.path.isdir(os.path.join(b, ".agents", "skills", n)) for b in bases):
        raise Refused(f"no skill is named {n[:60]!r} at the workshop's root or in {a['unit'][:64]}; nothing was recorded")
    return {"id": s.append(a["unit"], "note", {"event": "skill used", "skill": n}, by=by)}


TOOLS["skill_used"] = ({"name": S}, ["name"], _skill_used)  # batch D Task 15


def schema(name):
    props, req, _ = TOOLS[name]
    return {"type": "object", "properties": dict(COMMON, **props), "required": ["unit", "host", "session", "model"] + req, "additionalProperties": False}


def _service(s, v):
    return ((s.get(v["service"]) or {}).get("body") or {}).get("name") or str(v["service"])


def _verb_tools(s):
    """Every declared, standing verb whose params a tool can carry, by its tool's name (verbs.tool_name), the first by the verbs' order
    when two names meet; a verb whose param shares a name with the call's own fields or with about is offered no tool."""
    out = {}
    for v in s.verbs():
        params = v["params"] if isinstance(v["params"], dict) else None
        if v["declared"] and params is not None and not set(params) & (set(COMMON) | {"about"}):
            out.setdefault(verbs.tool_name(v["name"], _service(s, v)), v)
    return out


def verb_schema(v):
    """A verb tool's input: the call's own fields, one string per param of the verb and about, all of its params required, closed."""
    return {"type": "object", "properties": dict(COMMON, **{p: S for p in v["params"]}, about=S),
            "required": ["unit", "host", "session", "model"] + list(v["params"]), "additionalProperties": False}


HAND = 12  # the most things in hand the tool set reads, the newest touched (an audit of the read: seconds over a few hundred things)


def _in_hand(s, unit, things):
    """The things in hand, the HAND newest touched: those named that are standing objects, or else the unit's own standing things in hand,
    read from the index in one query (Store.in_hand, the rule of read.read_ids)."""
    return s.in_hand(unit, limit=HAND, among=list(things) if things else None)


def tools(store=None, unit=None, things=()):
    """The tools offered: the base tools, then, with a store, one tool per declared standing verb that reaches a thing in hand
    (store.verbs.reaching: its service, a world link to its service, or the thing's type among its object-typed params), described in
    the strings table's words with its door in the unit. The list helps the model choose and is never a fence (design section 8 point 3)."""
    base = [{"name": n, "description": w.plain("mcp.tool." + n), "inputSchema": schema(n)} for w in [Words("en")] for n in TOOLS]
    if store is None:
        return base
    from sandbox_os.pages.views import DOORS  # the store's door words to the strings' rows, one map for the page and the tools
    w, unit = Words("en", root=store.root), unit or "workshop"
    fit = fitting(store, _in_hand(store, unit, things))
    out = []
    for name, v in _verb_tools(store).items():
        if v["id"] in fit:
            door = w.plain("door." + DOORS[store.door(v["id"], unit)["door"]])
            out.append({"name": name, "description": w.plain("mcp.verb", verb=v["name"], service=_service(store, v), door=door),
                        "inputSchema": verb_schema(v)})
    return base + out


def _verb_call(s, v, a, by):
    """A verb tool's call: the act proposed with the verb fixed (verbs.propose), a number param read from its words; nothing runs."""
    params = {}
    for p, typ in v["params"].items():
        x = a[p]
        if typ == "number":
            with contextlib.suppress(ValueError):
                x = float(x) if any(c in x for c in ".eE") else int(x)
        params[p] = x
    return verbs.propose(s, a["unit"], v["id"], params, by=by, about=a.get("about"), host=a["host"], session=a["session"])


def listed(root, p):
    """tools/list for one request: the unit and the things in hand from params._meta (sandbox-os/unit, sandbox-os/things), else the unit
    the server's folder is in when that folder is inside this workshop (boundary.locate); the base tools alone when no unit is known."""
    meta = p.get("_meta") if isinstance(p.get("_meta"), dict) else {}
    unit, things = meta.get("sandbox-os/unit"), meta.get("sandbox-os/things")
    if not isinstance(unit, str):
        here = locate(os.getcwd())
        unit = here[1] if here and here[0] == os.path.realpath(root) else None
    if unit is None or not os.path.isfile(os.path.join(root, "home.json")):
        return tools()
    s = _store.open(root)
    try:
        if unit not in s.units() + ["workshop"]:
            return tools()
        return tools(s, unit, [t for t in things if isinstance(t, str)] if isinstance(things, list) else ())
    finally:
        s.close()


def _bad(sch, v, at):
    """What a value lacks against its schema, or None: the type, the required and the closed properties, the items, one of anyOf; an
    object with no properties is open, its values held to additionalProperties when that is a schema; null is absent."""
    if "anyOf" in sch:
        whys = [_bad(x, v, at) for x in sch["anyOf"]]
        return None if None in whys else "; or ".join(whys)
    t = sch["type"]
    if not isinstance(v, {"string": str, "integer": int, "array": list, "object": dict, "boolean": bool}[t]) or isinstance(v, bool) and t != "boolean":
        return f"{at} is not a{'n' if t[0] in 'aio' else ''} {t}"
    if t == "object" and "properties" not in sch:
        more = sch.get("additionalProperties")
        return next((m for k, x in v.items() if x is not None for m in [_bad(more, x, f"{at}.{k}")] if m), None) if isinstance(more, dict) else None
    if t == "integer" and v < sch.get("minimum", v):
        return f"{at} is under {sch['minimum']}"
    if v not in sch.get("enum", [v]):
        return f"{at} is one of {', '.join(sch['enum'])}"
    if t == "array":
        return next((m for i, x in enumerate(v) for m in [_bad(sch["items"], x, f"{at}[{i}]")] if m), None)
    if t == "object":
        v = {k: x for k, x in v.items() if x is not None}
        extra, missing = sorted(set(v) - set(sch["properties"])), [k for k in sch.get("required", []) if k not in v]
        if extra:
            return f"{at} takes no {', '.join(e[:40] for e in extra)}" + (": no tool takes an author; every tool records as the partner"
                                                                          if {"author", "by", "maker"} & set(extra) else "")
        if missing:
            return f"{at} needs {', '.join(missing)}"
        return next((m for k, x in v.items() for m in [_bad(sch["properties"][k], x, f"{at}.{k}")] if m), None)


def _refused(s, name, a, why):
    """The refusal as a note by the tool, in the call's unit when the workshop holds it, else the workshop's own."""
    a = a if isinstance(a, dict) else {}
    cut = lambda k: str(a[k])[:200] if a.get(k) is not None else None  # noqa: E731
    try:
        s.append(a["unit"] if a.get("unit") in s.units() and UNIT_RE.match(a["unit"]) else "workshop", "note", {
            "event": "refused", "verb": str(name)[:100], "why": why, "session": cut("session"), "via": "mcp", "input_sha256": input_hash(a),
            "actor": {"name": "partner", "model": cut("model"), "host": cut("host")}}, by=TOOL)
    except (Refused, TypeError, ValueError):
        pass  # the record busy, or arguments no line can carry: the refusal still goes back


def dispatch(root, name, args):
    """One call, done as the partner or refused with its note. The record is opened afresh for every call, and nothing is kept."""
    if not os.path.isfile(os.path.join(root, "home.json")):
        return {"ok": False, "refused": f"{root} is not a workshop (it has no home.json); nothing was recorded"}
    s = _store.open(root)
    try:
        verb = None if name in TOOLS or name in NEVER else _verb_tools(s).get(name)  # a verb tool is taken whether or not it was listed
        if name not in TOOLS and verb is None:
            raise Refused(f"{name}: {NEVER[name]}" if name in NEVER else say("refuse.tool", name=repr(str(name)[:60]), tools=", ".join(TOOLS)))
        why = _bad(verb_schema(verb) if verb else schema(name), args, name)
        if why and name == "believe" and isinstance(args, dict) and args.get("basis") not in BASES:  # the never-list's sentence, not the schema's
            b = args.get("basis")
            why = BASIS.format(basis="none" if b is None else repr(str(b)[:40]))
        if why:
            raise Refused(why)
        if args.get("workshop") is not None and os.path.realpath(args["workshop"]) != s.root:
            raise Refused(f"this server keeps the record of {s.root} and no other; {args['workshop'][:200]} was refused")
        if not UNIT_RE.match(args["unit"]) or args["unit"] not in s.units() + ["workshop"]:  # the pattern first: a folder is no unit (R-READ-6)
            us = [u for u in s.units() if u != "workshop"]  # the projects there are: eight named and the rest counted; none is said as none
            has = f"it has: {', '.join(us[:8])}{f' and {len(us) - 8} more' * (len(us) > 8)}" if us else "it has none yet"
            raise Refused(f"the workshop has no project {args['unit'][:64]!r}; {has}. A project is made at the welcome, never by a call")
        by = {"kind": "partner", "name": "partner", "model": args["model"], "host": args["host"]}
        a = {k: v for k, v in args.items() if v is not None}
        return {"ok": True, "result": _verb_call(s, verb, a, by) if verb else TOOLS[name][2](s, a, by)}
    except Refused as e:
        _refused(s, name, args, str(e))
        return {"ok": False, "refused": str(e)}
    finally:  # nothing kept between calls, the index's connection included
        s.close()


def respond(raw, root):
    """One line in, the JSON-RPC answer out, or None for a notification."""
    try:
        m = json.loads(raw)
    except ValueError:
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error: a line that is not JSON"}}
    if not isinstance(m, dict) or m.get("jsonrpc") != "2.0" or not isinstance(m.get("method"), str):
        return {"jsonrpc": "2.0", "id": m.get("id") if isinstance(m, dict) else None,
                "error": {"code": -32600, "message": "Invalid Request: one JSON-RPC 2.0 object per line, with a method"}}
    method, p, quiet = m["method"], m.get("params") if isinstance(m.get("params"), dict) else {}, "id" not in m
    err = lambda code, msg: None if quiet else {"jsonrpc": "2.0", "id": m["id"], "error": {"code": code, "message": msg}}  # noqa: E731
    if method == "initialize":
        result = {"protocolVersion": p.get("protocolVersion") if p.get("protocolVersion") in VERSIONS else VERSIONS[-1],
                  "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "sandbox-os", "version": VERSION}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": listed(root, p)}
    elif method == "tools/call":
        args = p.get("arguments") or {}
        if not isinstance(p.get("name"), str) or not isinstance(args, dict):
            return err(-32602, "Invalid params: tools/call takes a name and its arguments")
        try:
            r = dispatch(root, p["name"], args)
        except Exception as e:  # a fault of the tool's, not a refusal: said as an error result, and the server goes on
            r = {"ok": False, "refused": f"the tool failed: {type(e).__name__}: {str(e)[:300]}"}
        result = {"content": [{"type": "text", "text": json.dumps(r["result"], default=str) if r["ok"] else r["refused"]}], "isError": not r["ok"]}
    else:
        return err(-32601, f"Method not found: {method[:80]}")
    return None if quiet else {"jsonrpc": "2.0", "id": m["id"], "result": result}


def serve(stdin, stdout, root):
    """The loop over dispatch: a line in, an answer out for each request, until the input closes."""
    for raw in iter(stdin.readline, ""):
        if raw.strip():
            out = respond(raw, root)
            if out is not None:
                stdout.write(json.dumps(out, default=str) + "\n")
                stdout.flush()


def main(argv):
    """sandbox mcp --workshop <root>: serves on standard input and output; anything else printed goes to standard error."""
    root = argv[argv.index("--workshop") + 1] if "--workshop" in argv[:-1] else None
    if not root or not os.path.isfile(os.path.join(root, "home.json")):
        print(f"sandbox mcp: {root or 'no workshop was named'} is not a workshop; nothing was started", file=sys.stderr)
        return 1
    out = sys.stdout  # bytes that are not UTF-8 become a parse error for their line, never the server's end
    with contextlib.redirect_stdout(sys.stderr), contextlib.suppress(BrokenPipeError, KeyboardInterrupt):
        serve(open(sys.stdin.fileno(), encoding="utf-8", errors="replace", closefd=False), out, os.path.realpath(root))
    return 0
