# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""Verbs: an act that reaches outside the folder is declared once, as an object of type verb, and its definition is the facts about it:
the service it reaches, its parameters, which of the five acts it is, whether it stays inside, the command shapes that run it, what its
dry run shows and the receipt it expects. The door checks every such fact here; the maker and the tool write them, the partner only on
the maker's yes to a card about that verb, and only the maker strikes, deletes or supersedes a verb or its facts (the fence)."""
import collections, hashlib, json, os, re, shlex

from sandbox_os.store import Refused
from sandbox_os.store.line import ID_RE, DOWN_MARKS, RELATIONS, binds, canonical

ACTS = ("leaving this machine", "moving money", "destroying what the partner did not make", "deploying or pushing",
        "changing a live safety or legal claim")  # the hosts' words (boundary.LEAVES, MONEY, DESTROYS, DEPLOYS), in their order, then the fifth
RECEIPTS = ("commit", "deployment", "order", "transaction", "message", "address", "output")
FACETS = ("service", "params", "act", "inside", "shapes", "dry_run", "receipt")  # and alias, as batch A has it
PLAIN = ("text", "number")
SERVICE_TYPES = ("service", "host", "tool")
WRITERS = ("maker", "tool")  # who writes a verb's facts without a card
TAKE_BACK = ("strike", "unstrike", "delete", "undelete")
DOWN = DOWN_MARKS
OUT = DOWN + ("superseded",)  # a line with one of these marks no longer stands
FENCE = ("a verb and its facts, and a folder only the maker writes with its path, are the fence; only the maker strikes, deletes or "
         "supersedes them, and nothing was written")
# the word normalisation the hosts' five_act reads (boundary.WRAP, SHELLS, GIT_VALUED, _simple), kept here because the store imports no other
# part; a test pins the copies equal, and Task 6 points five_act at these
WRAP, SHELLS = {"sudo", "env", "command", "nohup", "time", "exec", "nice", "xargs"}, {"sh", "bash", "zsh", "dash", "fish", "env", "login"}
GIT_VALUED = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
# a wrapper's or a shell's own options that take a value as the next word (sudo -u x, nice -n 5, xargs -n 1, bash -o pipefail); its other
# options (-lc, -ic, env -i, time -p, command -p, xargs -n1, --user=x) are one word each; both are dropped before the inner command is read
WRAP_VALUED = {"sudo": {"-u", "-g", "-C", "-h", "-p", "-U", "-r", "-t", "-D", "-R", "-T", "--user", "--group", "--host", "--prompt", "--other-user",
                        "--role", "--type", "--chdir", "--chroot", "--close-from", "--command-timeout"},
               "env": {"-u", "-S", "-C", "-P", "--unset", "--split-string", "--chdir"}, "nice": {"-n", "--adjustment"},
               "xargs": {"-n", "-I", "-L", "-P", "-s", "-d", "-E", "-a", "--max-args", "--replace", "--max-lines", "--max-procs", "--max-chars",
                         "--delimiter", "--eof", "--arg-file"},
               "time": {"-f", "-o", "--format", "--output"}, "exec": {"-a"}, "bash": {"-o", "-O", "--rcfile", "--init-file"}, "zsh": {"-o"},
               "sh": {"-o"}, "dash": {"-o"}, "fish": {"-C", "--init-command"}}
LEAVES, MONEY, DESTROYS, DEPLOYS = ACTS[:4]
# the floor's words (row 34): the hosts' boundary.FIVE, the programs it names by their first words, and the two the seed verbs reach that
# it does not (codex leaves this machine, launchctl starts and stops a job); written as command lines and kept as their words, as the
# seed's shapes are (data only: the store runs none of them); five_act reads them, and the boundary may share it
FLOOR = tuple((tuple(line.split()), act) for line, act in (
    ("git push", DEPLOYS), ("git reset --hard", DESTROYS), ("git clean", DESTROYS), ("git branch -D", DESTROYS), ("rm", DESTROYS),
    ("gh pr merge", DEPLOYS), ("gh release", DEPLOYS), ("npm publish", DEPLOYS), ("vercel", DEPLOYS), ("fly deploy", DEPLOYS), ("stripe", MONEY),
    ("shopify", DEPLOYS), ("ssh", LEAVES), ("scp", LEAVES), ("mail", LEAVES), ("sendmail", LEAVES), ("mutt", LEAVES), ("osascript", LEAVES),
    ("codex", LEAVES), ("launchctl", DEPLOYS)))
SENDS = re.compile(r"^(-d|-F|-T|--data|--data-raw|--data-binary|--data-urlencode|--json|--form|--form-string|--upload-file|--post-data|--post-file|"
                   r"--body-data|--body-file)|^(-X|--request|--method)=?(POST|PUT|DELETE|PATCH)$")
GH_FIELDS, WRITES = {"-f", "-F", "--field", "--raw-field", "--input"}, ("POST", "PUT", "DELETE", "PATCH")
REMOTE = re.compile(r"^(?:[\w.-]+@)?[\w.-]+:(?!//)|^rsync://")
SPENDS = ("failed", "not run")  # the notes that count against a proposal's acts, beside its receipts
SECRET_FACETS = ("lives_at", "held_by", "needed_by", "alias")  # a secret by name: where it lives, what holds it, which verbs use it; never its value
SECRET_KEYS = ("type", "name", "ground")
HOLDERS = ("host", "machine")


def _look(look, i):
    return look(i) if isinstance(i, str) and ID_RE.match(i) else None


def _is_verb(line):
    return bool(line) and line.get("kind") == "object" and (line.get("body") or {}).get("type") == "verb"


def _present(store, oid):
    """An object's present facets: the newest standing fact per facet, its value read back."""
    rows = store._db().execute("SELECT f.facet, f.value FROM facets f JOIN lines l ON l.id = f.line WHERE f.object=? AND f.standing = 1 "
                               "ORDER BY f.t, l.seq", (oid,))
    return {f: json.loads(v) for f, v in rows if v is not None}


def types_of(store, line):
    """The types an object is held to: its body's and its present one, the newest standing type fact's; a guard by type reads both, so a thing
    re-typed before the door refused it is still guarded (Astra's challenge of batch D, finding 1). An empty set for any other line."""
    if not line or line.get("kind") != "object":
        return set()
    return {(line.get("body") or {}).get("type"), _present(store, line["id"]).get("type")} - {None}


def _guarded(store, line):
    """Whether a line is a folder whose present written_only_by is the maker: one places() names."""
    return bool(line) and line.get("kind") == "object" and (line.get("body") or {}).get("type") == "folder" and \
        _present(store, line["id"]).get("written_only_by") == "maker"


def _fences(line, look, store):
    if not line:
        return False
    if _is_verb(line) or _guarded(store, line):
        return True
    about = _look(look, line.get("about")) if line.get("kind") == "fact" else None
    facet = (line.get("body") or {}).get("facet")
    return _is_verb(about) or (facet == "written_only_by" and ((about or {}).get("body") or {}).get("type") == "folder") or \
        (facet == "path" and _guarded(store, about))


def fences(store, line):
    """Whether a line is behind the fence: a verb object, a fact about one, a written_only_by fact about a folder (Task 10), or a folder
    only the maker writes and its path fact (the review of batch C)."""
    return _fences(line, store.get, store)


def _first(line, look):
    """The line a strike, unstrike, delete or undelete finally acts on, following the chain of such lines."""
    for _ in range(64):
        if not line or line.get("kind") not in TAKE_BACK:
            return line
        line = _look(look, (line.get("body") or {}).get("target"))
    return line


def _yes_card(store, answer, look):
    """The standing card a binding yes of the maker's answers, when that yes is still his newest binding answer to it; else None."""
    a = _look(look, answer)
    if not a or a.get("kind") != "answer" or not binds(a) or (a.get("body") or {}).get("answer") != "yes":
        return None
    card = _look(look, a["body"].get("card"))
    if not card or card.get("kind") != "card" or card.get("mark") in OUT:
        return None
    said = [x for x in store.lines(kinds=["answer"]) if (x["body"] or {}).get("card") == card["id"] and binds(x)]
    return card if not said or said[-1]["id"] == a["id"] or (said[-1]["body"] or {}).get("answer") == "yes" else None


def _words(ws):
    return isinstance(ws, list) and bool(ws) and all(isinstance(w, str) and w.strip() for w in ws)


def _value(store, facet, v, look, pending=()):
    """Refuses a value a verb's facet does not take, in one plain sentence naming the facet and what it takes; a type checked in the same
    write (pending) counts, as a carried workshop's types precede its verbs (Astra's challenge of batch E, finding 14)."""
    shown = repr(v)[:60]
    if facet == "alias":
        return
    if facet not in FACETS:
        raise Refused(f"a verb carries the facets {', '.join(FACETS)} and an alias; {str(facet)[:40]!r} is none of them, so nothing was written")
    if facet == "service":
        o = _look(look, v)
        if not o or o.get("kind") != "object" or o.get("mark") in OUT or (o.get("body") or {}).get("type") not in SERVICE_TYPES:
            raise Refused(f"a verb's service is the id of a standing thing of type service, host or tool; {shown} is not one, so nothing was written")
    elif facet == "params":
        known = {x["body"].get("name") for x in store.types()} | set(PLAIN) | {q["body"].get("name") for q in pending if q.get("kind") == "object"
                                                                              and isinstance(q.get("body"), dict) and q["body"].get("type") == "type"}
        bad = None if isinstance(v, dict) else shown
        for k, t in (v.items() if bad is None else ()):
            if not isinstance(k, str) or not k.strip() or t not in known:
                bad = f"{k!r} takes {str(t)[:40]!r}"
                break
        if bad:
            raise Refused(f"a verb's params name each parameter with a standing type's name, or text or number; {bad}, so nothing was written")
    elif facet == "act" and v not in ACTS + ("none",):
        raise Refused(f"a verb's act is one of the five acts ({'; '.join(ACTS)}) or none, not {shown}, so nothing was written")
    elif facet == "inside" and not isinstance(v, bool):
        raise Refused(f"a verb's inside is true or false, whether it stays inside the folder; {shown} is neither, so nothing was written")
    elif facet == "shapes" and not (isinstance(v, list) and all(_words(s) and not s[0].startswith("-") for s in v)):
        raise Refused(f"a verb's shapes are a list of command shapes, each a list of words whose first is a program, not an option; "
                      f"{shown} is not, so nothing was written")
    elif facet == "dry_run" and not (isinstance(v, dict) and set(v) == {"shows", "command"} and isinstance(v["shows"], str) and v["shows"].strip()
                                     and (v["command"] is None or _words(v["command"]))):
        raise Refused(f"a verb's dry run says what it shows, as shows, and the command that shows it, as command, a list of words or null; "
                      f"{shown} does not, so nothing was written")
    elif facet == "receipt":
        p = v.get("pattern") if isinstance(v, dict) else None
        try:
            groups = re.compile(p).groups if isinstance(p, str) else 0
        except re.error:
            groups = 0
        if not (isinstance(v, dict) and set(v) == {"kind", "pattern"} and v["kind"] in RECEIPTS and (p is None or groups >= 1)):
            raise Refused(f"a verb's receipt names its kind, one of {', '.join(RECEIPTS)}, and a pattern that finds it in the output, a "
                          f"regular expression with at least one group, or null; {shown} is not, so nothing was written")


def _standing(o, types):
    return bool(o) and o.get("kind") == "object" and o.get("mark") not in OUT and (o.get("body") or {}).get("type") in types


def _secret(store, kind, body, about, look):
    """A secret is an object by name (design section 3): its body holds only its type, its name and its ground, and each fact about it is
    one of SECRET_FACETS, so its value has no place to go; the secret scan (line.check_body) has already read every one of these bodies."""
    if kind == "object" and body.get("type") == "secret":
        extra = sorted(k for k in body if k not in SECRET_KEYS)
        if extra:
            said = "value" if "value" in extra else ", ".join(str(k)[:40] for k in extra)
            raise Refused(f"a secret is recorded by its name only: its type, its name and its ground; this one also carries {said}, and its "
                          "value stays where it lives (the Keychain or its file), so nothing was written")
        return
    sec = _look(look, about)
    if kind != "fact" or "secret" not in types_of(store, sec):
        return  # a fact about a struck secret is held to the same facets: the value never has a place, standing or not
    facet, v, shown = body.get("facet"), body.get("value"), repr(body.get("value"))[:60]
    if facet not in SECRET_FACETS:
        raise Refused(f"a secret carries the facets {', '.join(SECRET_FACETS)}, never its value; {str(facet)[:40]!r} is none of them, so "
                      "nothing was written")
    if facet == "lives_at" and not (isinstance(v, str) and v.strip()):
        raise Refused(f"a secret's lives_at names where it lives, the Keychain item's name or a file's path; {shown} is not, so nothing was written")
    if facet == "held_by" and not _standing(_look(look, v), HOLDERS):
        raise Refused(f"a secret's held_by is the id of a standing thing of type host or machine; {shown} is not one, so nothing was written")
    if facet == "needed_by" and not (isinstance(v, list) and all(_standing(_look(look, i), ("verb",)) for i in v)):
        raise Refused(f"a secret's needed_by is a list of the ids of standing verbs; {shown} is not, so nothing was written")


PROPOSED = ("name",) + FACETS + ("why", "seen")  # a proposed verb's body, a line of kind verb (batch C, Task 13)


def _proposed(store, body, about, look):
    """A proposed verb, a line of kind verb: each facet it proposes held to what a verb's fact takes (_value), its name and why in words,
    and the unknown acts it was seen as (seen, the ids of their notes); about, when given, is its service. What it must carry is the
    command's to say (verbs.propose_verb), as the record's other kinds keep their own words."""
    if "name" in body and not (isinstance(body["name"], str) and body["name"].strip()):
        raise Refused("a proposed verb is named in plain words for the act; this one is not, so nothing was written")
    for f in FACETS:
        if f in body:
            _value(store, f, body[f], look)
    if "why" in body and not (isinstance(body["why"], str) and body["why"].strip()):
        raise Refused("a proposed verb says why it is proposed, in a sentence; this one does not, so nothing was written")
    seen = body.get("seen", [])
    if not isinstance(seen, list) or any(((_look(look, i) or {}).get("body") or {}).get("event") != "unknown act" for i in seen):
        raise Refused("a proposed verb's seen lists the ids of the unknown act notes it was seen as; this one names another line, so nothing was written")
    why = _quiet(body.get("shapes"), body.get("act"), body.get("inside"))
    if why:
        raise Refused(why)
    if about is not None and "service" in body and about != body["service"]:
        raise Refused("a proposed verb is about the service it reaches, and this one is about another line, so nothing was written")


def check(store, kind, body, by, about, look, pending=()):
    """The door's check for verbs, called once from the store's _may: a fact about a verb takes only what its facet takes and is written by
    the maker, the tool, or the partner on the maker's yes to a card about that verb; a verb object by the partner rests on his yes to a card
    naming its proposal; a proposed verb, a line of kind verb, holds each facet it proposes to the same rules (_proposed); a strike,
    unstrike, delete or undelete, or a supersedes, strikes or deletes link, that reaches a fenced line is the maker's alone; a secret and
    the facts about it hold its name, where it lives and which verbs use it, never its value (_secret)."""
    _secret(store, kind, body, about, look)
    if kind == "verb":
        _proposed(store, body, about, look)
    who = by["kind"]
    if kind in TAKE_BACK or kind == "link" and body.get("rel") in ("supersedes", "strikes", "deletes"):
        target = _first(_look(look, body.get("target" if kind in TAKE_BACK else "to")), look)
        if who != "maker" and _fences(target, look, store):
            raise Refused(FENCE)
        return
    if kind == "fact" and body.get("facet") in ("path", "written_only_by") and who != "maker" and _guarded(store, _look(look, about)):
        card = _yes_card(store, body.get("answer"), look) if who == "tool" else None
        if ((card or {}).get("body") or {}).get("purpose") != f"folder:{about}":
            raise Refused("a folder only the maker writes keeps its path and its written_only_by by the maker's hand, or the tool's on the maker's yes "
                          f"to a card about it (purpose folder:{about}); this fact rests on neither, so nothing was written")
    if kind == "object" and body.get("type") == "verb" and who not in WRITERS:
        card, prop = _yes_card(store, body.get("answer"), look), body.get("proposal")
        verbs = ((card or {}).get("body") or {}).get("verbs")
        if who != "partner" or not card or (_look(look, prop) or {}).get("kind") != "verb" or not isinstance(verbs, list) or prop not in verbs:
            raise Refused("a verb is declared by the maker or the tool, or by the partner on your yes to a card whose verbs name its proposal "
                          "(body.answer, your yes; body.proposal, the queued verb line); this one rests on none, so nothing was written")
        return
    if kind == "fact" and _is_verb(_look(look, about)):
        _value(store, body.get("facet"), body.get("value"), look, pending)
        if body.get("facet") in ("shapes", "act", "inside"):
            would = dict(_present(store, about), **{body["facet"]: body.get("value")})
            why = _quiet(would.get("shapes"), would.get("act"), would.get("inside"))
            if why:
                raise Refused(why)
        if who in WRITERS:
            return
        card = _yes_card(store, body.get("answer"), look) if who == "partner" else None
        if ((card or {}).get("body") or {}).get("purpose") != f"verb:{about}":
            names = "names none" if card is None else "names a card about something else"
            raise Refused(f"the partner changes a verb only through your yes to a card about it (purpose verb:{about}), and this fact {names}; "
                          "nothing was written")
        said = card["body"]
        if said.get("facet") != body.get("facet") or "value" not in said or canonical(said["value"]) != canonical(body.get("value")):
            raise Refused("your yes to a card about a verb lets the partner write the one fact the card names, its facet and its value as the "
                          "card words them; this fact is not that one, so nothing was written")
        if any((x["body"] or {}).get("answer") == body.get("answer") for x in store.lines(about=about, kinds=["fact"])):
            raise Refused("your yes to a card about a verb lets the partner write its fact once, and that fact is already written; nothing was written")


def view(store, obj):
    """A verb as the other parts read it, from the object's present facets: the newest standing fact per facet. declared is true when the
    six facets other than inside stand, and inside too when its act is none."""
    present = _present(store, obj["id"])
    need = [f for f in FACETS if f != "inside"] + (["inside"] if present.get("act") == "none" else [])
    return {"id": obj["id"], "name": (obj.get("body") or {}).get("name"), "unit": obj.get("unit"), **{f: present.get(f) for f in FACETS},
            "declared": all(f in present for f in need), "mark": obj.get("mark")}


def standing(store):
    """Every standing verb's view, struck and superseded ones left out, by name."""
    return sorted((view(store, o) for o in store.lines(kinds=["object"]) if _is_verb(o) and o["mark"] not in OUT), key=lambda v: (v["name"] or "", v["id"]))


SEPARATORS = ";&|()`\n"


def simple(cmd):
    """A shell command as word lists, one per simple command, read as the shell reads its words (shlex, Astra's audit, finding 9: git
    p"us"h is git push, git -C "a b" push keeps "a b" one word) and split at each separator outside quotes, assignments, wrappers and shells
    dropped, each program by its base name: the hosts' boundary._simple, word for word. A shell's -c string is read as commands of its own,
    and so is a substitution, $(...) or `...`, even inside quotes; a command whose quotes do not close is read as before, every quote a space."""
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=SEPARATORS)
        lex.whitespace, lex.whitespace_split = " \t\r", True
        tokens = list(lex)
    except ValueError:  # an unclosed quote: the old reading, every separator a split and every quote a space
        return [c for piece in re.split(r"&&|\|\||[;|&\n()`]|\$\(", cmd) for c in _one(re.sub(r"[\"']", " ", piece).split())]
    out, seg = [], []
    for t in tokens + [";"]:
        if t and set(t) <= set(SEPARATORS):  # an empty word ('') is a word, never a separator
            out, seg = out + _one(seg[:-1] if seg[-1:] == ["$"] and "(" in t else seg), []
        else:
            seg.append(t)
    return out


def _one(seg):
    """One simple command's words as simple() keeps them: unwrapped, its program by its base name; a shell's command string read as the
    commands it holds, and each substitution inside a word after it."""
    a = _unwrap(seg)
    if not a:
        return []
    if any(os.path.basename(w) in SHELLS for w in seg[:len(seg) - len(a)]) and re.search(r"[\s;&|()`]", a[0]):  # sh -c "...": its commands
        return simple(a[0])
    inner = [c for w in a for m in re.findall(r"\$\(([^()]*)\)|`([^`]*)`", w) for c in simple(m[0] or m[1])]
    return [[os.path.basename(a[0])] + a[1:]] + inner


def _unwrap(a):
    """The words with leading assignments, wrappers and shells dropped, each wrapper's or shell's own options after it too (an option
    that takes a value with its value, WRAP_VALUED), so the inner command is what is read: sudo -u x git push is git push."""
    while a and (re.match(r"\w+=", a[0]) or os.path.basename(a[0]) in WRAP | SHELLS or a[0] == "-c"):
        assigned, valued, a = re.match(r"\w+=", a[0]), WRAP_VALUED.get(os.path.basename(a[0]), set()), a[1:]
        while not assigned and a and a[0].startswith("-") and a[0] != "-":
            a = a[2:] if a[0] in valued else a[1:]
    return a


def words(argv):
    """One simple command's words as a verb's shape is matched against them: assignments, wrappers and shells dropped, the program by its
    base name, and the options before its subcommand skipped (a valued one with its value), as five_act reads git push behind any option;
    every program's are skipped, not git's alone, so a shape matches behind an option the hosts' table does not name; the store's files name
    no program it could run (tests/store/test_line.py). A command given as a string is read through shlex first (Astra's audit, finding 9)."""
    if isinstance(argv, str):
        try:
            argv = shlex.split(argv)
        except ValueError:  # an unclosed quote: every quote a space, as simple() reads it
            argv = re.sub(r"[\"']", " ", argv).split()
    a = _unwrap([w for w in argv if isinstance(w, str)])
    if not a:
        return []
    prog, rest = os.path.basename(a[0]), a[1:]
    while rest and rest[0].startswith("-"):
        rest = rest[2:] if rest[0] in GIT_VALUED else rest[1:]
    return [prog] + rest


def fits(shape, argv):
    """Whether one simple command is of a verb's shape: the shape's program and subcommand words (those not options) in order at the front
    of its words, and each of the shape's option words anywhere after its program (as itself, or as itself=value), since words() drops
    the options before a subcommand: stripe charges create --amount 5 --live is of the shape stripe charges create --live."""
    front, opts = [w for w in shape if not w.startswith("-")], [w for w in shape if w.startswith("-")]
    a = _unwrap([w for w in argv if isinstance(w, str)])
    return bool(a) and words(a)[:len(front)] == front and all(any(x == o or x.startswith(o + "=") for x in a[1:]) for o in opts)


def five_act(argv):
    """Which of the five acts one simple command (a list of words) is by the floor's words, or None: its wrappers and their options
    dropped (_unwrap), its program and subcommand read past their options (words) against FLOOR, and the hosts' other forms on its words as
    written: data sent by curl or wget in any spelling, gh api writes, aws s3 copies out, rsync to a host. A verb's shape is classed so."""
    raw = _unwrap([w for w in argv or () if isinstance(w, str)])
    if not raw:
        return None
    prog, rest, w = os.path.basename(raw[0]), raw[1:], words(raw)
    args, pairs = [x for x in rest if not x.startswith("-")], list(zip(rest, rest[1:]))
    if prog in ("curl", "wget", "http", "xh") and (any(SENDS.match(x) for x in rest) or any(x in ("-X", "--request", "--method") and y in WRITES for x, y in pairs)):
        return LEAVES
    if prog == "gh" and w[1:2] == ["api"] and (set(rest) & GH_FIELDS or any(x in ("-X", "--method") and y in WRITES for x, y in pairs)
                                               or any(re.match(r"--method=(POST|PUT|DELETE|PATCH)$", x) for x in rest)):
        return LEAVES
    if prog == "aws" and args[:1] == ["s3"] and len(args) > 2 and args[1] in ("cp", "mv", "sync") and args[-1].startswith("s3://"):
        return LEAVES
    if prog == "rsync" and any(REMOTE.match(x) for x in args):
        return LEAVES
    return next((act for prefix, act in FLOOR if tuple(w)[:len(prefix)] == prefix or tuple([prog] + rest)[:len(prefix)] == prefix), None)


def _quiet(shapes, act, inside):
    """The refusal for a verb whose shape the floor classes as one of the five acts, said to stay inside or to be of no act; else None."""
    hit = next((s for s in shapes if isinstance(shapes, list) and _words(s) and five_act(s)), None) if isinstance(shapes, list) else None
    if hit and (act == "none" or inside is True):
        return (f"a verb whose shape is one of the five acts by the floor's words ({' '.join(hit)[:60]} is {five_act(hit)}) is never declared "
                "inside the folder nor of no act, by any hand; it asks every time, so nothing was written")


def acts_in(store, argvs):
    """The acts in a call, in order, one per simple command (a shell command is split by simple() on ; && || | newlines and the rest,
    or the word lists given): for each command, the declared, standing verb with the longest shape it is of (fits), as its view plus the
    shape and argv, the command's words; a command no verb names gives nothing. The hook writes one line per act."""
    cmds = simple(argvs) if isinstance(argvs, str) else [a for a in argvs or () if isinstance(a, (list, tuple))]
    vs, out = [v for v in standing(store) if v["declared"] and v["shapes"]], []
    for c in cmds:
        best = None
        for v in vs:
            for shape in v["shapes"]:
                if (best is None or len(shape) > len(best["shape"])) and fits(shape, c):
                    best = dict(v, shape=shape, argv=[w for w in c if isinstance(w, str)])
        best and out.append(best)
    return out


match = acts_in  # the name the store's verb_for reads; verb_for is its first


def _acts(body):
    p = body.get("params")
    return len(p) if isinstance(p, list) else 0


def _used(store):
    """Per proposal, the acts spent: its receipts, and its failed and not-run notes, every one whatever its mark so a yes is never spent
    twice; the first failure that says retry 1 is not counted, the one retry under the same yes that ruling row 36 allows, and every
    failure after it is (a second failure spends the yes; a retry is then a new card). unseen counts apart the acts that ran with their
    receipt not seen (a not_seen line carrying the proposal): each spends an act, and the proposal stays waiting, a yes with no receipt."""
    used, retried, unseen = collections.Counter(), {}, collections.Counter()
    for x in store.lines(kinds=["receipt", "note", "not_seen"]):
        b = x["body"] or {}
        p = b.get("proposal")
        if not isinstance(p, str) or x["kind"] == "note" and b.get("event") not in SPENDS:
            continue
        if x["kind"] == "not_seen":
            unseen[p] += 1
        elif x["kind"] == "note" and b.get("event") == "failed" and b.get("retry") == 1 and p not in retried:
            retried[p] = x["id"]  # the failed note, whose retry retry_allowed judges
        else:
            used[p] += 1
    return used, retried, unseen


def _open(store, unit=None, verb=None, waiting=False):
    """Every proposal not spent, oldest first: a standing card naming a verb whose newest binding answer is yes, or a standing proposal
    note whose grant stands; each as proposal_for returns it, with its verb and unit. An act that ran with its receipt not seen is spent,
    except when waiting asks which yeses have no receipt yet."""
    said = {}
    for a in store.lines(kinds=["answer"]):
        if binds(a):
            said[(a["body"] or {}).get("card")] = a
    used, retried, unseen = _used(store)
    out = []
    for x in store.lines(unit=unit, kinds=["card", "note"]):
        b = x["body"] or {}
        if x["mark"] in OUT or not isinstance(b.get("verb"), str) or verb is not None and b["verb"] != verb:
            continue
        if x["kind"] == "card":
            a = said.get(x["id"])
            if not a or a["body"].get("answer") != "yes":
                continue
            answer, grant = a["id"], None
        elif b.get("event") == "proposal" and isinstance(b.get("grant"), str) and store.grant_state(b["grant"]) == "standing":
            answer, grant = None, b["grant"]
        else:
            continue
        n, spent = _acts(b), used[x["id"]] + (0 if waiting else unseen[x["id"]])
        if spent < n:
            out.append({"proposal": x["id"], "answer": answer, "grant": grant, "index": spent + 1, "of": n, "undoes": b.get("undoes"),
                        "failures": int(x["id"] in retried), "retry_note": retried.get(x["id"]), "verb": b["verb"], "unit": x["unit"]})
    return out


def act_sha256(cmd):
    """The words hash of an act: SHA-256 over the canonical JSON of the command's simple commands as simple() reads them (a shell
    command), or of the word lists given, so the same words however quoted or spaced hash alike. A failed note carries it as act_sha256,
    and the hook passes it to proposal_for so the one retry under row 36 covers that same command only."""
    cmds = simple(cmd) if isinstance(cmd, str) else [[w for w in a if isinstance(w, str)] for a in cmd or () if isinstance(a, (list, tuple))]
    return hashlib.sha256(canonical(cmds).encode()).hexdigest()


def retry_allowed(store, failed, words_hash):
    """Whether the one retry under the same yes (ruling row 36) covers an act: failed is a standing failed note, the act's words hash
    (act_sha256 of the command about to run) equals the one it carries, and a standing note by the partner, event retry, names it as
    body.failed and says in its words why the failure was transient. The hook calls it; proposal_for reads it."""
    f = store.get(failed) if isinstance(failed, str) else None
    fb = (f or {}).get("body") or {}
    if not f or f["kind"] != "note" or f["mark"] in OUT or fb.get("event") != "failed" or not isinstance(words_hash, str) \
            or fb.get("act_sha256") != words_hash:
        return False
    return any((n.get("by") or {}).get("kind") == "partner" and n["mark"] not in OUT and (n["body"] or {}).get("event") == "retry"
               and (n["body"] or {}).get("failed") == failed and isinstance(n["body"].get("words"), str) and n["body"]["words"].strip()
               for n in store.lines(about=f.get("about"), kinds=["note"]))


def proposal_for(store, verb_id, unit, act_sha256=None):
    """The oldest proposal of this verb in this unit with an act not yet spent, or None: {proposal, answer, grant, index, of, undoes,
    failures}. index is the next act's number, 1-based; answer is the yes's id, or None under a grant; failures is 1 when the act is the
    one retry. A first failure is retried under the same yes only when retry_allowed (the partner said on the record why it was transient,
    and act_sha256, the words hash of the command about to run, equals the failed act's); otherwise that failure spends its act, and a
    retry is a new act with no yes."""
    for x in _open(store, unit=unit, verb=verb_id):
        if x["failures"] and not retry_allowed(store, x["retry_note"], act_sha256):
            if x["index"] >= x["of"]:
                continue
            x = dict(x, index=x["index"] + 1, failures=0)
        return {k: x[k] for k in ("proposal", "answer", "grant", "index", "of", "undoes", "failures")}
    return None


def parse_receipt(verb, text, folder=None):
    """The receipt the outside gave back, read from its output where the verb says it is: {kind, value}, value the first group of the
    verb's pattern that matched, or None (no pattern, no match, or no output); a receipt of kind output keeps at most the first 80
    characters of its first line, one word that is a path inside folder (the workshop's) excepted, kept whole (Astra's audit, finding 8)."""
    r = (verb or {}).get("receipt") or {}
    m = re.search(r["pattern"], text) if isinstance(r.get("pattern"), str) and isinstance(text, str) else None
    value = next((g for g in m.groups() if g is not None), None) if m else None
    if r.get("kind") == "output" and value:  # its first line, at most 80 characters of it; the rest only in the kept payload (the hook's)
        value = (value.splitlines() or [""])[0]
        value = value if len(value) <= 80 or not re.search(r"\s", value) and _within(value, folder) else value[:80]
    return {"kind": r.get("kind"), "value": value}


def _within(path, folder):
    """Whether a word is a path inside folder, read as the file system resolves it (a .. that climbs out is not inside)."""
    if not (isinstance(folder, str) and folder and os.path.isabs(path)):
        return False
    return os.path.realpath(path).startswith(os.path.realpath(folder).rstrip(os.sep) + os.sep)


def _last(store, verb_id):
    receipt = failure = None
    for x in store.lines(about=verb_id, kinds=["receipt", "note"]):
        b = x["body"] or {}
        if x["mark"] in OUT or b.get("verb") != verb_id:
            continue
        if x["kind"] == "receipt":
            r = b.get("receipt") if isinstance(b.get("receipt"), dict) else {}
            receipt = {"id": x["id"], "t": x["t"], "kind": r.get("kind"), "value": r.get("value")}
        elif b.get("event") == "failed":
            failure = {"id": x["id"], "t": x["t"], "words": b.get("words")}
    return receipt, failure


def door(store, verb, unit):
    """Which of the three doors a verb (its view, or its id) takes in a unit: {door, grant}. "asks" every time for one of the five acts,
    whatever any grant line says, and for a verb whose act is not declared or that no longer stands; "inside" for a verb of no act that
    stays inside the folder; "grant", with its id, under the oldest standing grant for the unit (or *), not superseded, whose scope.verbs
    names the verb; else "asks once" (design section 3 point 2)."""
    v = store.verb(verb) if isinstance(verb, str) else verb
    if not v or v.get("act") != "none" or v.get("mark") in OUT:
        return {"door": "asks", "grant": None}
    if v.get("inside") is True:
        return {"door": "inside", "grant": None}
    for g in store.lines(kinds=["grant"]):
        sc = (g["body"] or {}).get("scope") or {}
        if sc.get("unit") in (unit, "*") and g["mark"] not in OUT and isinstance(sc.get("verbs"), list) and v["id"] in sc["verbs"] \
                and store.grant_state(g["id"]) == "standing":
            return {"door": "grant", "grant": g["id"]}
    return {"door": "asks once", "grant": None}


def reaching(store, thing_id):
    """The declared, standing verbs that reach a thing: it is their service, one of their object-typed params is its type, or a standing
    link between things joins it and their service; each with its door in the thing's unit (door), its act, and its newest receipt and
    failure, by the verb's name."""
    o = store.get(thing_id) if isinstance(thing_id, str) else None
    if not o or o["kind"] != "object":
        return []
    typ, out = (o["body"] or {}).get("type"), []
    joined = {f if t == thing_id else t for f, t in store._db().execute(
        f"SELECT k.frm, k.target FROM links k LEFT JOIN marks m ON m.id = k.made WHERE ? IN (k.frm, k.target) AND k.rel NOT IN {RELATIONS} "
        f"AND coalesce(m.mark, '') NOT IN {OUT}", (thing_id,))}
    for v in standing(store):
        params = v["params"] if isinstance(v["params"], dict) else {}
        if v["declared"] and (v["service"] == thing_id or typ in {t for t in params.values() if t not in PLAIN} or v["service"] in joined):
            receipt, failure = _last(store, v["id"])
            out.append({"verb": v["id"], "name": v["name"], **door(store, v, o["unit"]), "act": v["act"], "last_receipt": receipt,
                        "last_failure": failure})
    return out


def fitting(store, thing_ids):
    """The ids of the declared, standing verbs that reach any of these things (reaching's rule: the thing is their service, its type is
    one of their object-typed params, or a standing link between things joins it and their service), in one pass over the standing verbs
    and two queries, whatever the number of things."""
    ids = sorted({t for t in thing_ids or () if isinstance(t, str)})
    if not ids:
        return set()
    marks, c = ",".join("?" * len(ids)), store._db()
    types = {r[0] for r in c.execute(f"SELECT DISTINCT type FROM objects WHERE id IN ({marks})", ids)}
    joined = set()
    for f, t in c.execute(f"SELECT k.frm, k.target FROM links k LEFT JOIN marks m ON m.id = k.made WHERE (k.frm IN ({marks}) OR k.target IN "
                          f"({marks})) AND k.rel NOT IN {RELATIONS} AND coalesce(m.mark, '') NOT IN {OUT}", ids + ids):
        joined |= {f, t}
    have, out = set(ids), set()
    for v in standing(store):
        params = v["params"] if isinstance(v["params"], dict) else {}
        if v["declared"] and (v["service"] in have or types & {t for t in params.values() if t not in PLAIN} or v["service"] in joined):
            out.add(v["id"])
    return out


def waiting(store, units=None):
    """The proposals answered yes whose acts are not all spent, oldest first: the maker's yes is on the record and no receipt yet, so
    nothing is written as done (design section 3 point 3)."""
    names = {v["id"]: v["name"] for v in standing(store)}
    return [{"proposal": p["proposal"], "verb": p["verb"], "verb_name": names.get(p["verb"]) or (store.get(p["verb"]) or {}).get("body", {}).get("name"),
             "answer": p["answer"], "unit": p["unit"]} for p in _open(store, waiting=True) if p["answer"] and (units is None or p["unit"] in units)]


def queued(store):
    """The partner's proposed verbs, standing lines of kind verb, that no card naming them in body.verbs has settled with a binding
    answer (later settles nothing, as for every card); batch D's weekly card reads them (Task 13)."""
    cards = {c["id"]: (c["body"] or {}).get("verbs") for c in store.lines(kinds=["card"])}
    settled = {q for a in store.lines(kinds=["answer"]) if binds(a) and a["body"].get("answer") != "later"
               for q in (cards.get(a["body"].get("card")) or []) if isinstance(cards.get(a["body"].get("card")), list)}
    return [x for x in store.lines(kinds=["verb"]) if x["mark"] not in OUT and x["id"] not in settled]


def places(store):
    """The folders only the maker writes (design section 10 point 4): the present path of each standing object of type folder whose present
    written_only_by is "maker", ~ expanded, once each; the hosts deny each to the partner. That fact is behind the fence (fences)."""
    out = []
    for o in (x for x in store.lines(kinds=["object"]) if _standing(x, ("folder",))):
        f = _present(store, o["id"])
        p = os.path.expanduser(f["path"]) if f.get("written_only_by") == "maker" and isinstance(f.get("path"), str) and f["path"].strip() else None
        p and p not in out and out.append(p)
    return out


def secrets(store):
    """The secrets by name (design section 10 point 5): each standing object of type secret as {id, name, lives_at}, lives_at its present
    facet (the Keychain item's name or a file's path) or None; never a value, which has no place in the record (_secret)."""
    out = []
    for o in (x for x in store.lines(kinds=["object"]) if _standing(x, ("secret",))):
        f = _present(store, o["id"])
        out.append({"id": o["id"], "name": (o.get("body") or {}).get("name"), "lives_at": f.get("lives_at")})
    return out


def unfenced(store):
    """The declared, standing verbs with no command shape: nothing in the hosts asks before them but their card."""
    return [v for v in standing(store) if v["declared"] and not v["shapes"]]
