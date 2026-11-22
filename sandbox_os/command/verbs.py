# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""Proposing a verb (an act declared once in the record, design section 3): the partner never runs one, it proposes one. Which door the
proposal takes is the verb's: one of the five acts is a card that asks every time, in the host's own prompt; a verb that leaves the folder
but is none of the five is a note naming the standing grant whose scope names it, or else a card that asks once; a verb that stays inside
the folder writes nothing. Each proposal carries its dry run (what the act would do, shown without doing it), kept beside the record as a
payload, with any words matching a secret pattern left out and the line saying so. This is also the one place the tool runs a verb's
command (runner), behind the gate that refuses it while the record is being read. A new verb is proposed too (propose_verb): it waits in
the queue for the week's card and is no verb until the maker's yes. Every refusal says why in plain words."""
import os, re, shlex, subprocess

from sandbox_os.store import Refused, gate
from sandbox_os.store.line import SECRET_PATTERNS, ID_RE
from sandbox_os.store.verbs import PROPOSED
from sandbox_os.command import DOWN, cards, runs, say
from sandbox_os.hosts.boundary import needs

PLAIN = ("text", "number")
NEEDED = ("name", "service", "params", "act", "shapes", "dry_run", "receipt", "why")  # what a proposed verb always carries; inside too when its act is none
SAFE = re.compile(r"[\w@%+=:,./{}^~-]+")  # a word shown as it is in the dry run's command; any other is quoted, as shlex quotes it
LEFT_OUT = re.compile(r"\[left out: words matching the secret pattern '(\w+)'\]")


def slug(name):
    """A name as a tool's name carries it: lower case, each run of characters outside a to z and 0 to 9 one underscore, none at either end."""
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


def tool_name(verb_name, service_name):
    """The name of a verb's tool over MCP, namespaced by the service it reaches (design section 8 point 3): the service's slug, two
    underscores, the verb's slug, cut to 64 characters, as the protocol's names are held."""
    return (slug(service_name) + "__" + slug(verb_name))[:64]


def runner(verb):
    """The one place the tool runs a verb's command: run(argv, *, cwd, timeout=20), text, output captured with stderr into stdout, wrapped by
    the gate under the verb's name, so nothing runs while the record is being read."""
    @gate.outbound(verb["name"])
    def run(argv, *, cwd, timeout=20):
        return subprocess.run(list(argv), cwd=cwd, timeout=timeout, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return run


def _joined(argv):
    return " ".join(w if SAFE.fullmatch(w) else shlex.quote(w) for w in argv)


def _keep_out(text):
    """The text with every run of words matching a secret pattern replaced by a mark naming the pattern, never the words."""
    for name, rx in SECRET_PATTERNS.items():
        text = rx.sub(f"[left out: words matching the secret pattern '{name}']", text)
    return text


def _path(store, oid):
    t = store.thing(oid) if isinstance(oid, str) else None
    p = ((t or {}).get("facets") or {}).get("path", {}).get("value") if t else None
    return p if isinstance(p, str) and p else None


def _name(store, oid):
    return ((store.get(oid) or {}).get("body") or {}).get("name") or oid


def _shown(store, typ, value):
    """A param's value as the dry run shows it: an object by its present path facet, else its name; text and numbers as they are."""
    return str(value) if typ in PLAIN else _path(store, value) or _name(store, value)


def _inside(root, p):
    real = os.path.realpath(p)
    return (real + "/").startswith(os.path.realpath(root) + "/") and ".sandbox" not in real.split(os.sep)


def _files(root, p):
    """A folder inside the workshop, by its files' names and sizes in bytes; hidden entries are left out, and nothing is read."""
    if not (isinstance(p, str) and os.path.isdir(p) and _inside(root, p)):
        return []
    out = []
    for n in sorted(os.listdir(p)):
        f = os.path.join(p, n)
        if not n.startswith(".") and os.path.isfile(f):
            out.append(f"  {n}, {os.path.getsize(f)} bytes")
    return out


def dry_run(store, unit, verb, acts):
    """What the verb would do for each act, shown without doing it, as bytes: "act i of n", then the dry run's command and its output, run
    inside the check's fence (runs.profile with the unit, R-READ-6), when the verb has one and running it here needs nothing more than the
    working copy (boundary.needs) and its sandbox starts (runs.starts), else "not run here: <why>; it would show: <shows>"; then each param
    as "<name>: <value>", a folder inside the workshop with its files by name and size. Words matching a secret pattern are left out, and
    the mark that replaces them names the pattern."""
    root, params, dr = store.root, verb.get("params") or {}, verb.get("dry_run") or {}
    home = root if unit == "workshop" else os.path.join(root, "projects", unit)
    out = []
    for i, act in enumerate(acts, 1):
        out.append(f"act {i} of {len(acts)}")
        shown = {k: _shown(store, params.get(k), v) for k, v in act.items()}
        argv = [w for w in dr.get("command") or []]
        for k, v in shown.items():
            argv = [w.replace("{" + k + "}", v) for w in argv]
        why = None if argv else "this verb has no command that shows it without doing it"
        if argv:
            joined = _joined(argv)
            why = needs(os.path.realpath(root), unit, "Bash", {"command": joined})
            why = why and f"running its command here would be {why}"
            why = why or (None if runs.starts(prof := runs.profile(root, unit)) else runs.NONE)  # tried first, as a check is
        if why is None:
            try:
                r = runner(verb)([runs.SANDBOX, "-p", prof, *argv], cwd=home if os.path.isdir(home) else root)
                out += [f"$ {joined}", r.stdout.rstrip("\n")] + ([f"(it exited {r.returncode})"] if r.returncode else [])
            except (OSError, subprocess.TimeoutExpired) as e:
                why = f"its command could not run ({type(e).__name__})"
        if why is not None:
            out.append(f"not run here: {why}; it would show: {dr.get('shows')}")
        for k, v in act.items():
            out.append(f"{k}: {shown[k]}")
            if params.get(k) == "folder":
                out += _files(root, _path(store, v))
    return _keep_out("\n".join(out) + "\n").encode("utf-8")


def _object(store, name, typ, value):
    """The id of the one standing object of this type the value names, by its id or by its words (Store.resolve); else refused."""
    o = store.get(value) if isinstance(value, str) and ID_RE.match(value) else None
    if o and o["kind"] == "object" and o["mark"] not in DOWN and (o["body"] or {}).get("type") == typ:
        return value
    hits = [h for h in store.resolve(value) if h["type"] == typ and (store.get(h["id"]) or {}).get("mark") not in DOWN] if isinstance(value, str) else []
    if len(hits) != 1:
        raise Refused(say("refuse.verb.object." + ("some" if hits else "none"), name=name, typ=typ, value=repr(str(value)[:60]), count=len(hits)))
    return hits[0]["id"]


def _acts(store, verb, params):
    staged = params if isinstance(params, list) else [params]
    want, out = verb.get("params") or {}, []
    if not staged:
        raise Refused(f"a proposal of {verb['name']} carries at least one act's params; this one carries none, so nothing was written")
    for p in staged:
        if not isinstance(p, dict) or set(p) != set(want):
            got = sorted(p) if isinstance(p, dict) else repr(p)[:40]
            raise Refused(f"{verb['name']} takes the params {', '.join(sorted(want))}, and this act gives {got}; nothing was written")
        act = {}
        for k, typ in want.items():
            v = p[k]
            if typ == "number" and (isinstance(v, bool) or not isinstance(v, (int, float))):
                raise Refused(f"{k} takes a number, and {str(v)[:40]!r} is not one; nothing was written")
            act[k] = v if typ in PLAIN else _object(store, k, typ, v)
        out.append(act)
    return out


def _words(store, verb, acts):
    params = verb.get("params") or {}
    return "; ".join(", ".join(f"{k} {v if params.get(k) in PLAIN else _name(store, v)}" for k, v in a.items()) for a in acts)


def propose(store, unit, verb_id, params, *, by, about=None, undoes=None, host=None, session=None):
    """Proposes a verb with its params (one dict, or a list of dicts for a staged set) and returns {door, proposal, card, grant, dry_run}:
    nothing is written inside the folder; a card about the thing (about, else the verb) under asks and asks once, before the act when the
    verb is one of the five so it waits on no budget; a note naming the grant under a grant. The proposal's id is the card's or the note's,
    and dry_run is the payload's sha256. Refused for a verb not declared or not standing, params the verb does not take, an object value
    that is not one standing object of its type, a number that is not one, and an undoes that is not an act's receipt or whose act's verb
    reaches another service. An undo takes the door of the act it undoes when that door is stricter: a five act's undo asks, and the undo of
    an act that left the folder never runs as inside."""
    v = store.verb(verb_id)
    if not v or v["mark"] in DOWN or not v["declared"]:
        raise Refused(f"only a declared verb that stands is proposed, and {str(verb_id)[:40]!r} is not one; nothing was written")
    acts = _acts(store, v, params)
    u = store.get(undoes) if isinstance(undoes, str) else None
    if undoes is not None and not (u and u["kind"] == "receipt" and (u["body"] or {}).get("proposal")):
        raise Refused("an undo names the receipt of the act it undoes, and this one names no such line; nothing was written")
    done = store.verb((u["body"] or {}).get("verb")) if u else None
    if u and (not done or done["service"] != v["service"]):
        raise Refused(say("refuse.undo.service", name=v["name"]))
    d, act = store.door(verb_id, unit), v["act"]
    if done:
        was = store.door(done["id"], unit)
        if was["door"] == "asks":
            d, act = was, act if act != "none" else done["act"] if done["act"] != "none" else act
        elif d["door"] == "inside" and was["door"] != "inside":
            d = {"door": "asks once", "grant": None}
    if d["door"] == "inside":
        return {"door": "inside", "proposal": None, "card": None, "grant": None, "dry_run": None}
    dry = dry_run(store, unit, v, acts)
    text = dry.decode("utf-8")
    left = sorted(set(LEFT_OUT.findall(text)))
    why = say("verb.left.out", names=", ".join(repr(n) for n in left)) if left else None
    extra = {k: x for k, x in (("undoes", undoes), ("left_out", why)) if x is not None}
    with store.locked():
        sha = store.payload(dry, unit=unit)
        if d["door"] == "grant":
            n = store.append(unit, "note", {"event": "proposal", "verb": verb_id, "params": acts, "dry_run": {"payload": sha}, "door": "grant",
                                            "grant": d["grant"], "act": act, **extra}, by=by, about=about or verb_id)
            return {"door": "grant", "proposal": n, "card": None, "grant": d["grant"], "dry_run": sha}
        times = f", {len(acts)} times" if len(acts) > 1 else ""
        body = dict(cards.five("card.verb", name=v["name"], times=times, words=_words(store, v, acts), act=act if act != "none" else say("card.verb.outside"),
                               bytes=len(dry), opening=repr((text.splitlines() or [""])[0][:80]), why=f"; {why}" if why else ""),  # Astra's audit, finding 8: a payload only
                    verb=verb_id, params=acts, dry_run={"payload": sha}, door=d["door"], act=act, **extra,
                    **{k: x for k, x in (("host", host), ("session", session)) if x is not None})
        c = cards.raise_(store, unit, body, by=by, before_act=act if d["door"] == "asks" else None, thing=about or verb_id)
    return {"door": d["door"], "proposal": c, "card": c, "grant": None, "dry_run": sha}


def propose_verb(store, unit, body, *, by):
    """Proposes a new verb, from acts seen (batch C, Task 13): a line of kind verb, about the service it reaches, whose body is the proposed
    facets (the store holds each to what a verb's fact takes), why it is proposed, and seen, the ids of the unknown act notes it was seen
    as. It is a proposal, a card's matter and never the verb's facts: queued for the week's card (the store's verbs.queued), not in
    Store.verbs(), and its shapes ask nothing until the maker's yes declares it. Returns the line's id."""
    missing = [k for k in NEEDED if body.get(k) is None] + (["inside"] if body.get("act") == "none" and body.get("inside") is None else [])
    if missing:
        raise Refused(say("refuse.verb.needs", needed=", ".join(NEEDED), missing=", ".join(missing)))
    return store.append(unit, "verb", {k: body[k] for k in PROPOSED if body.get(k) is not None}, by=by, about=body["service"])
