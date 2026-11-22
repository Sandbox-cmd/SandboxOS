# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""Taking back, typed (cards 32 and 43; P5; R-STORE-28 to 31, 61): delete ID prints the line, undelete ID only that a card asks; each raises a card on the
maker's desk and stops; only his binding yes there lets the same command, typed again, act as him, once, with a note naming the card and
the yes. snapshot, copy --to FOLDER and restore --from FOLDER --into NEW run when typed and write nothing in his name; a copy goes to a
folder on this Mac, a restore reads one, and an address on the network gets "not yet" before anything is written, sent or read."""
import os, re

from sandbox_os.command import MAKER, TOOL, cards, options, say

NEED = {"delete": (1, 1, ()), "undelete": (0, 1, ()), "snapshot": (0, 0, ()), "copy": (0, 0, ("--to",)), "restore": (0, 0, ("--from", "--into"))}


def _on_his_yes(s, out, verb, unit, key, slots, act, done, show=None):
    """Card 43: the act runs only on his binding yes at the desk, once; otherwise the tool asks there, or says how the card stands."""
    purpose = f"{verb}:{key}"
    c = max(map(s.get, cards._on(s, unit, purpose)), key=lambda c: c["body"].get("version", 1), default=None)
    d = c and cards.decision(s, c["id"])
    a = d and d["body"].get("answer")
    used = d and d["id"] in [(l["body"] or {}).get("yes") for l in s.lines(unit=unit, kinds=["note"]) if (l["body"] or {}).get("event") == "yes-acted"]
    if a == "yes" and not used:
        text = say("cli.take.note", verb=verb, id=slots["id"], card=c["id"], answer=d["id"])
        line = act(text)
        s.append(unit, "note", {"event": "yes-acted", "verb": verb, "target": key, "line": line, "card": c["id"], "yes": d["id"], "text": text}, by=TOOL)
        out(done(d["id"], line))
        return 0
    if c and a != "yes":
        out(say("cli.take.no" if a == "no" else "cli.take.waits", card=c["id"]))
        return 1
    body = dict(cards.five(f"cli.take.{verb}", lang=cards.language(s.root), **slots), purpose=purpose, line=slots["id"])
    new = cards.raise_(s, unit, dict(body, **({"changed": {"ruling": d["id"], "card": c["id"]}} if c else {})), by=TOOL, can_wait=False)
    c and s.link(new, "follows", c["id"], by=TOOL)
    show and out(show)
    out(say("cli.take.asked", card=new, verb=verb, id=slots["id"]))
    return 0


def main(argv, *, workshop=None, out=print):
    from sandbox_os import store as _store
    from sandbox_os.store import copy
    from sandbox_os.store.line import text_of
    verb, rest = (argv[0], list(argv[1:])) if argv else (None, [])
    low, high, flags = NEED.get(verb, (0, 0, ()))
    opts, args = options(rest, dict.fromkeys(flags))
    if verb not in NEED or not low <= len(args) <= high or None in opts.values() or any(a.startswith("-") for a in args):
        out(say("cli.take.usage"))
        return 2
    try:
        if verb == "restore":  # needs no workshop: it reads a folder on this Mac and writes only into the new one
            frm, into = opts["--from"], opts["--into"]
            if not os.path.isdir(frm):
                out(say("cli.take.restore.nofolder", folder=frm))
                return 1
            r = copy.restore(frm, into)
            out(say("cli.take.restore.done", into=into, lines=r["lines"], seconds=r["seconds"]) if r["matched"]
                else say("cli.take.restore.failed", into=into, failures="; ".join(r["failures"])))
            return 0 if r["matched"] else 1
        s = workshop if hasattr(workshop, "lines") else _store.open(workshop) if workshop and os.path.isfile(os.path.join(workshop, "home.json")) else None
        if s is None:
            out(say("cli.noworkshop"))
            return 1
        if verb == "snapshot":
            out(say("cli.take.snapshot", len(s.snapshot())))
            return 0
        if verb == "copy":
            to, path = opts["--to"], os.path.realpath(opts["--to"])
            hook = os.path.join(path, "hooks", "update")
            ours = os.path.isfile(os.path.join(path, "HEAD")) and os.path.isfile(hook) and "sandbox-os" in open(hook, errors="replace").read()
            why = ("notyet" if re.match(r"[^/]*[:@]", to) else "inside" if (path + os.sep).startswith(os.path.realpath(s.root) + os.sep)
                   else "notours" if not ours and (os.path.isfile(path) or os.path.isdir(path) and os.listdir(path)) else None)
            if why:
                out(say("cli.take.copy." + why, to=to))
                return 1
            r = copy.push(s, path if ours else copy.init_remote(path), by=TOOL)
            out(say("cli.take.copy.done", to=path, files=len(r["sent"])))
            r["erased"] and out(say("cli.take.snapshot", len(r["erased"])))
            return 0
        with s.locked():
            if verb == "delete":
                l = s.get(args[0])
                if not l or l["mark"] in ("deleted", "erased"):
                    out(say("cli.take.already", id=args[0], mark=l["mark"]) if l else say("cli.take.noline", id=args[0]))
                    return 1
                slots = dict(id=l["id"], kind=l["kind"], unit=l["unit"], day=l["t"][:10], who=l["by"]["kind"])
                until = lambda line: next(h["end"] for h in s.holds() if h["delete"] == line)[:10]
                return _on_his_yes(s, out, verb, l["unit"], l["id"], slots, lambda text: s.delete(l["id"], by=MAKER, why=text),
                                   lambda yes, line: say("cli.take.deleted", id=l["id"], answer=yes, end=until(line)),
                                   say("cli.take.line", words=text_of(l["body"])[:300], **slots))
            hs = [h for h in s.holds() if h["state"] in ("running", "not started")]
            day, end = lambda h: s.get(h["delete"])["t"][:10], lambda h: h["end"][:10] if h["end"] else say("cli.take.unseen")
            if not args:
                for h, t in ((h, s.get(h["target"])) for h in hs):
                    out(say("cli.take.held", id=t["id"], kind=t["kind"], unit=t["unit"], day=day(h), end=end(h)))
                hs or out(say("cli.take.held.none"))
                return 0
            h = next((h for h in hs if args[0] in (h["delete"], h["target"])), None)
            if not h:
                out(say("cli.take.nohold", id=args[0]))
                return 1
            return _on_his_yes(s, out, verb, s.get(h["target"])["unit"], h["delete"], dict(id=h["target"], day=day(h), end=end(h)),
                               lambda text: s.undelete(h["delete"], by=MAKER), lambda yes, line: say("cli.take.undeleted", id=h["target"], answer=yes))
    except _store.Refused as e:
        out(say("cli.take.refused", why=str(e)))
        return 1
