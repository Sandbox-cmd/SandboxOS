# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The acts: who may do which, then link, strike, take back, delete with its hold, undelete, erase as an in-place reseal, snapshot, payloads, receipts and rechecks."""
import datetime as _dt
import hashlib, json, os, re, shutil

from sandbox_os.store import Refused, verbs
from sandbox_os.store.line import (RELATIONS, CHAIN_KINDS, BASES, UNIT_RE, ID_RE, canonical, line_hash, mint_id, iso, iso_ms, check_by,
                                   links_of, ends_ok, find_secret, payload_refs, words_of, binds)
from sandbox_os.store.log import TOOL, _put, _read, _rows, _stat, _tail
from sandbox_os.store.answers import STRIKE_WORDS, read_choice  # noqa: F401 (STRIKE_WORDS read here by tests/store/test_review_d.py)

HOLD_DAYS = 7
FORMS = ("path", "journal", "sha256", "url", "read_back", "word", "fenced", "other")
GONE = "the words are gone; only the mark remains"
WORDS = {"goal": {"text": "what is wanted, in plain words"}, "assumption": {"text": "what is taken as true, in plain words"},
         "question": {"text": "what is asked, in plain words", "settles": "who or what could settle it",
                      "cost": "what it costs while it stays open"}}  # the fields each of the three knowing kinds must carry
DOWN = "('erased', 'deleted', 'struck')"
MAKER_OUT = "('erased', 'deleted', 'struck', 'superseded')"  # a maker's object with one of these marks no longer stands, so the flag is free
GUARDED = ("person", "secret", "host", "machine", "folder", "service", "tool", "verb", "type", "relation")  # each type a rule of the store names
GUESS_PERSON = "a guess about a person is never written: ask, or write an open question that the person settles; nothing was written"
RECEIPTS = f"""SELECT l.id FROM links k JOIN lines l ON l.id = k.made JOIN marks m ON m.id = l.id
WHERE k.target = ? AND k.rel = 'proves' AND l.kind = 'receipt' AND m.mark NOT IN {DOWN}
AND NOT EXISTS (SELECT 1 FROM links f JOIN lines fl ON fl.id = f.frm JOIN marks fm ON fm.id = f.made
  WHERE f.target = l.id AND f.rel = 'follows' AND fl.kind = 'receipt' AND fm.mark NOT IN {DOWN})"""


NEVER = "the tool never strikes, deletes or erases; it records what others do"


def _his_strike(target, body, look):
    """The one strike the tool records, his and not its own (batch D, Task 7; design section 2 point 5): of a standing type or relation the
    week's card lists, on his binding answer in words to that card, named as body.answer, whose words strike that item by its number
    (review of batch D, finding 3), read whole by the card's own strict reader, read_choice, so an unknown or negative word anywhere strikes
    nothing (Astra's challenge of batch D, finding 2). None when it is his; else the refusal, in the store's words."""
    a = look(body.get("answer")) if isinstance(body.get("answer"), str) else None
    card = look((a.get("body") or {}).get("card")) if a and a.get("kind") == "answer" and isinstance((a.get("body") or {}).get("card"), str) else None
    cb = (card or {}).get("body") or {}
    item = next((i for i in cb.get("items") or [] if isinstance(i, dict) and i.get("id") == target.get("id")), None)
    if not (card and card.get("kind") == "card" and card.get("mark") not in ("erased", "deleted", "struck") and cb.get("week_card") is True
            and binds(a) and a["body"].get("answer") == "words" and target.get("kind") == "object"
            and (target.get("body") or {}).get("type") in ("type", "relation") and item):
        return NEVER
    if (read_choice(a["body"].get("words"), len(cb["items"])) or {}).get(item.get("n")) != "strike":
        return (f"the tool records the maker's strike of an item on the week's card only where the maker's words strike it by its number, "
                f"strike {item.get('n')}; the words {str(a['body'].get('words'))[:60]!r} do not, so nothing was written")
    return None


PIN = "a pin names a file inside the workshop by its path and the exact words that must stay there"


def _may_pins(pins, root=None):
    """A rule's or an answer's pins (batch E, Task 14): a list of {path, words}, the path relative to the workshop's root, not empty, not
    absolute and with no .. segment, and, given the root, still inside its real path once its symbolic links are resolved (the review of
    batch E, finding 11b), the words not empty and at most 500 characters; anything else refused, so the doctor reads only files inside
    the workshop."""
    real = os.path.realpath(root) if root else None
    for p in pins if isinstance(pins, list) and pins else [None]:
        path, words = (p.get("path"), p.get("words")) if isinstance(p, dict) and set(p) == {"path", "words"} else (None, None)
        if not (isinstance(path, str) and path.strip() and isinstance(words, str) and words.strip() and len(words) <= 500) \
                or os.path.isabs(path) or path.startswith(("/", "\\", "~")) or ".." in re.split(r"[/\\]", path) \
                or real and not os.path.realpath(os.path.join(real, path)).startswith(real + os.sep):
            raise Refused(PIN)


class Acts:
    def _may(self, unit, kind, body, by, look, about=None, valid_until=None, pending=(), carried=False):
        """Who may do which, and whether the links a line makes have real ends; refused here, inside the one door, so no call writes around it.
        carried: a line re-keyed from another workshop's record (move.rekey), set only through _append_many's planned dict."""
        if kind in WORDS:
            self._may_know(kind, body, valid_until)
        if kind == "fact" and (about is not None or "facet" in body):
            self._knowing(body, look)
        if kind == "fact" and about is not None and body.get("facet") == "type":
            self._may_retype(body, pending, look(about) if isinstance(about, str) else None)
        if kind in ("fact", "assumption", "note") and about is not None:
            self._may_person(kind, body, look, about)
        if kind == "goal":
            self._may_goal(body, look)
        if kind == "answer" and by["kind"] == "person":
            raise Refused("a second person's words are recorded as theirs, never as an answer to a card")
        if kind in ("rule", "answer") and "pins" in body:
            _may_pins(body["pins"], self.root)
        if kind == "close" and by["kind"] != "tool" and not body.get("imported"):
            for k in ("learned", "changed"):
                ln = look(body.get(k)) if isinstance(body.get(k), str) else None
                if not ln or ln.get("kind") != k or ln.get("unit") not in (None, unit):
                    raise Refused(f"a run's close names its two learning lines, body.learned and body.changed, each a line of that kind "
                                  f"written before it in this unit; this close is missing {k}")
        if kind in ("receipt", "check") and by["kind"] != "tool":
            raise Refused("a receipt or a check is recorded by the tool from what it saw, never by the partner or a person; "
                          "the partner proposes a check and the tool runs it, and the maker's word proves through a proves link")
        if kind == "strike" and (look(body.get("target")) or {}).get("kind") in CHAIN_KINDS:
            raise Refused(f"an {look(body['target'])['kind']} line explains the chain, so it is never struck")
        if kind == "object":
            self._may_object(body, pending)
            if "maker" in body and body["maker"] is not True:
                raise Refused(f"the maker's flag, body.maker, is true or left out; {str(body['maker'])[:40]!r} is neither, so nothing was written")
            if body.get("maker") is True:
                self._may_maker(body, by, pending)
        for frm, rel, to in links_of({"id": None, "kind": kind, "body": body, "about": about}):
            f = {"kind": kind} if frm is None else look(frm) if isinstance(frm, str) else None
            t = look(to) if isinstance(to, str) else None
            if f is not None and t is not None and f["kind"] == t["kind"] == "object" and rel != "supersedes":
                known = [x["body"]["name"] for x in self.relations()]
                if rel not in known:
                    raise Refused(f"a link between two things uses a relation the workshop declares, or supersedes for a duplicate; "
                                  f"{rel!r} is not one of the {len(known)} declared: {', '.join(known) or 'none yet'}")
                continue
            if rel not in RELATIONS:
                raise Refused(f"{rel!r} is not a relation; the relations are: {', '.join(RELATIONS)}")
            if f is None or t is None:
                raise Refused(f"no line has the id {(frm if f is None else to)!r}, so nothing was written")
            if not ends_ok(rel, f["kind"], t["kind"], f.get("unit") not in (None, t.get("unit")) and t.get("seq") == 1):
                raise Refused(f"{'an' if rel[:1] in 'aeiou' else 'a'} {rel} link does not run from {'an' if f['kind'][:1] in 'aeiou' else 'a'} {f['kind']} line to {'an' if t['kind'][:1] in 'aeiou' else 'a'} {t['kind']} line")
            if rel == "supersedes" and t["kind"] == "said":  # only the one who said it replaces it, with a newer said line of their own
                who, src = (t["by"]["kind"], t["by"]["name"]), f.get("by") or by
                if f["kind"] != "said" or (src["kind"], src["name"]) != who:
                    whose = "the maker's" if who[0] == "maker" else f"the {who[0]}'s" if who[0] in ("partner", "tool") else f"{who[1]}'s"
                    raise Refused(f"that said line is {whose} word, so only a newer said line by the same voice replaces it; "
                                  "anything else is written beside it, and the word stays as it was said")
        verbs.check(self, kind, body, by, about, look, pending)  # a verb and its facts: what each facet takes, who writes it, and the fence
        if kind not in ("strike", "unstrike", "delete", "undelete"):
            return
        target, k = look(body["target"]) if isinstance(body.get("target"), str) else None, by["kind"]
        if target is None:
            raise Refused(f"a {kind} names the line it acts on as body.target")
        why = (NEVER if kind != "strike" else _his_strike(target, body, look)) if k == "tool" else None
        if why:
            raise Refused(why)
        own = (target["by"]["kind"], target["by"]["name"]) == (k, by["name"])
        if kind in ("unstrike", "undelete"):
            want = ("strike", "unstrike") if kind == "unstrike" else ("delete",)
            if target["kind"] not in want:
                raise Refused(f"{kind} takes back a {' or '.join(want)} line, not a {target['kind']} line")
            if k != "maker" and not own:
                raise Refused(f"only the maker takes back another's {target['kind']}; the {k} takes back only its own")
            first = target
            while first and first["kind"] in ("strike", "unstrike", "delete", "undelete"):
                first = look((first["body"] or {}).get("target"))
            if first and first.get("mark") == "erased":
                raise Refused(GONE)
            if target["kind"] in ("strike", "delete") and first and first["kind"] == "object" and (first.get("body") or {}).get("maker") is True:
                other = self._db().execute("SELECT l.id FROM lines l LEFT JOIN marks m ON m.id = l.id WHERE l.kind='object' AND l.id != ? AND "
                                           f"json_extract(l.body,'$.maker') = 1 AND (m.mark IS NULL OR m.mark NOT IN {MAKER_OUT})", (first["id"],)).fetchone()
                if other:
                    raise Refused(f"the workshop has one maker, and {other[0]} now carries the flag; taking this {target['kind']} back would make "
                                  "two, so nothing was written")
            end = self._db().execute("SELECT end_at FROM holds WHERE delete_id=?", (target["id"],)).fetchone() if kind == "undelete" else None
            if end and end[0] and end[0] <= iso(self.clock()):
                raise Refused(f"the hold ended at {end[0]}; the words wait for the maker's next snapshot and are not taken back")
        if kind == "delete" and not self._may_delete(target, body, by, own, carried, look):
            raise Refused("the partner deletes only inside a standing grant on this unit whose scope names the delete service, or a line "
                          "of its own that no brief has shown; a second person deletes only their own lines")

    def may_name(self, typ, name):
        """Refuses, in append's own words, a name a type or a relation could not take (the one check append makes, _may_object): the
        growth queue asks it before a proposal waits, so his yes never meets a refusal (the review of batch D, finding 2)."""
        self._may_object({"type": typ, "name": name})

    def _may_object(self, body, pending=()):
        """A thing has a name and a type the workshop knows: 'type', 'relation', or the name of a standing type; a type's or a relation's
        name is used once, counting the lines already checked in the same write (pending), which the index does not hold yet."""
        name, typ = body.get("name"), body.get("type")
        if not isinstance(name, str) or not name.strip():
            raise Refused("a thing is recorded with its name, as body.name, in the maker's words")
        if typ in ("type", "relation"):
            if any(c in name for c in "/\\\0") or name.startswith("."):  # the pages write pages/types/<name>.html, so a name is never a path
                raise Refused(f"a {typ}'s name becomes a file's name on the pages, so it holds no slash, backslash or NUL and does not "
                              f"begin with a dot; {name!r} is refused, nothing was written")
            if typ == "relation" and name in RELATIONS:
                raise Refused(f"{name!r} is one of the tool's own relations and keeps its meaning; a relation between things takes another name")
            taken = [x["body"] for x in (self.types() if typ == "type" else self.relations())]
            taken += [q["body"] for q in pending if q.get("kind") == "object" and isinstance(q.get("body"), dict) and q["body"].get("type") == typ]
            if name in {b.get("name") for b in taken}:
                raise Refused(f"a {typ} named {name!r} already stands in this workshop; a {typ}'s name is its identity, so it is used once")
            return
        known = {x["body"].get("name") for x in self.types()}
        known |= {q["body"].get("name") for q in pending if q.get("kind") == "object" and isinstance(q.get("body"), dict) and q["body"].get("type") == "type"}
        if typ not in known:
            raise Refused(f"a thing's type is 'type', 'relation' or one of the {len(known)} types this workshop knows, "
                          f"and {typ!r} is none of them; the seed records the first ones (Store.seed)")

    def _may_retype(self, body, pending=(), thing=None):
        """A fact with facet 'type' moves a thing to another type, so its value is a standing type's name, counting a type checked in the
        same write (pending); the index reads the thing's type from the newest standing one (design section 2 point 3). Never the
        vocabulary's own three, whoever writes it (review of batch D, finding 9); never the maker's own thing, and never into or out of a
        type a rule of the store names (GUARDED), since those rules read the type (Astra's challenge of batch D, finding 1)."""
        v = body.get("value")
        if v in ("type", "relation", "verb"):
            raise Refused(f"a thing is never re-typed as a type, a relation or a verb; {v!r} is the vocabulary's own, nothing was written")
        if (thing or {}).get("kind") == "object" and (thing.get("body") or {}).get("maker") is True:
            raise Refused("the maker's own thing is a person and stays one, whoever writes the type fact, so the maker's page keeps the maker; nothing was written")
        was = verbs.types_of(self, thing)
        if was and was != {v} and (was | {v}) & set(GUARDED):
            raise Refused(f"a thing is never moved into or out of a type the store guards by name ({', '.join(GUARDED)}), because its rules "
                          f"for people, secrets, hosts, folders and verbs read the type; {'/'.join(sorted(was))} to {str(v)[:40]!r} is refused, "
                          "nothing was written")
        known = {x["body"].get("name") for x in self.types()}
        known |= {q["body"].get("name") for q in pending if q.get("kind") == "object" and isinstance(q.get("body"), dict) and q["body"].get("type") == "type"}
        if not isinstance(body.get("value"), str) or body["value"] not in known:
            raise Refused(f"a type fact names a standing type; {body.get('value')!r} is none")

    def _may_person(self, kind, body, look, about):
        """A guess about a person is never written, the maker's or anyone's (design section 6 points 1 and 7): a my-guess fact, an
        assumption or a pre-mortem (a note with event pre-mortem) about a person object is refused; he is asked, or a question he settles
        stays open."""
        t = look(about) if isinstance(about, str) else None
        guess = kind == "assumption" or (kind == "fact" and body.get("basis") == "my guess") or (kind == "note" and body.get("event") == "pre-mortem")
        if "person" in verbs.types_of(self, t) and guess:
            raise Refused(GUESS_PERSON)

    def _may_goal(self, body, look):
        """A goal is read from his own words: body.fragments names at least one line, and each is a said line the maker wrote that still
        stands (not struck, deleted, erased or superseded)."""
        frags = body.get("fragments")
        bad = None if isinstance(frags, list) and frags else "it cites none"
        for f in frags if not bad else ():
            ln = look(f) if isinstance(f, str) else None
            if not ln or ln.get("kind") != "said" or (ln.get("by") or {}).get("kind") != "maker" or ln.get("mark") in ("erased", "deleted", "struck", "superseded"):
                bad = f"{str(f)[:40]!r} is not"
                break
        if bad:
            raise Refused(f"a goal is read from the maker's words, so each fragment, as body.fragments, is the maker's own standing said line, and "
                          f"there is at least one; {bad}, so nothing was written")

    def _may_maker(self, body, by, pending=()):
        """One maker: the flag body.maker stands on a person object only, written by the tool or by him, and on no second standing object,
        counting the lines already checked in the same write (pending)."""
        if body.get("type") != "person":
            raise Refused(f"the maker's flag, body.maker, marks the person object that is the maker; a thing of type {body.get('type')!r} "
                          "never carries it, and nothing was written")
        if by["kind"] not in ("tool", "maker"):
            raise Refused(f"the maker's flag is written by the tool or by the maker, never by the {by['kind']}; nothing was written")
        rows = self._db().execute("SELECT l.id FROM lines l LEFT JOIN marks m ON m.id = l.id WHERE l.kind='object' AND "
                                  f"json_extract(l.body,'$.maker') = 1 AND (m.mark IS NULL OR m.mark NOT IN {MAKER_OUT})").fetchall()
        if rows or any(q.get("kind") == "object" and isinstance(q.get("body"), dict) and q["body"].get("maker") is True for q in pending):
            raise Refused(f"the workshop has one maker, and a person object already carries the flag ({rows[0][0] if rows else 'in this write'}); "
                          "a second is never flagged, and nothing was written")

    def _may_know(self, kind, body, valid_until):
        """A goal, an assumption and a question each say their words; a question also says who or what could settle it, what it costs while open, and the day it lapses."""
        for k in WORDS[kind]:
            if not isinstance(body.get(k), str) or not body[k].strip():
                raise Refused(f"a {kind} says {WORDS[kind][k]}, as body.{k}; this one does not")
        if kind == "question" and valid_until is None:
            raise Refused("a question says the day it lapses, as valid_until (YYYY-MM-DD); after that day it is marked past and leaves the thing's open questions")

    def _knowing(self, body, look):
        """A fact about a thing names its facet and its basis: he said (a said line), a check showed (a check line), I read it in (a path or an address) or my guess (no source)."""
        words = ", ".join(f"'{b}'" for b in BASES)
        if not isinstance(body.get("facet"), str) or not body["facet"].strip():
            raise Refused("a fact about a thing names which of its facets it sets, as body.facet, a short name such as 'commission'")
        if "value" not in body:
            raise Refused(f"a fact about a thing says what its {body['facet']} is, as body.value; write null when the value is none, "
                          "and nothing was written")
        basis, src = body.get("basis"), body.get("source")
        if basis not in BASES:
            raise Refused(f"a fact about a thing says how it came to be known, as body.basis, one of {words}; this one says {basis!r}")
        want, step = {"he said": ("said", "record what was said"), "a check showed": ("check", "run the check")}.get(basis, (None, None))
        if want:
            is_id = isinstance(src, str) and bool(ID_RE.match(src))
            line = look(src) if is_id else None
            if not line or line.get("kind") != want:
                raise Refused(f"the basis '{basis}' needs the line it rests on: {step} first (a {want} line), then pass that line's id as source; {src!r} "
                              + (f"is {'an' if str(line.get('kind'))[:1] in 'aeiou' else 'a'} {line.get('kind')} line" if line else "names no line" if is_id else "is not a line's id"))
            if basis == "a check showed" and ((line.get("by") or {}).get("kind") != "tool" or (line.get("body") or {}).get("exit") != 0):
                ex = (line.get("body") or {}).get("exit")
                raise Refused("'a check showed' rests on a check the tool ran that passed, one that exited 0; this check "
                              + (f"exited {ex}" if (line.get("by") or {}).get("kind") == "tool" else "was not run by the tool")
                              + ", so it shows nothing, and nothing was written")
            if basis == "he said" and (line.get("by") or {}).get("kind") != "maker":
                raise Refused(f"'he said' rests on the maker's own words, a said line the maker wrote; this said line was written by the "
                              f"{(line.get('by') or {}).get('kind') or 'unknown'}, so the belief is 'my guess' until the maker says it")
        if basis == "I read it in" and (not isinstance(src, str) or not src.strip() or ID_RE.match(src)):
            raise Refused("the basis 'I read it in' names where it was read, as body.source, a path or an address, not a line id; "
                          "a line is 'he said' or 'a check showed'")
        if "confidence" in body and body["confidence"] not in ("likely", "unsure"):
            raise Refused(f"a fact's confidence is 'likely' or 'unsure', or left out; {body['confidence']!r} is neither")

    def _may_delete(self, target, body, by, own, carried=False, look=None):
        if by["kind"] in ("maker", "person"):
            return by["kind"] == "maker" or own
        g = body.get("grant")
        if carried and not g:  # the partner's own, carried: its state window was judged when first written, against a record not held here
            return own
        if carried:  # under a grant, carried: its authority was judged against the source's own history (move._grant_held; Astra's
            gl = look(g) if look and isinstance(g, str) else None  # challenge of batch E, finding 13); here, the grant carried with it
            sc = ((gl or {}).get("body") or {}).get("scope") or {}
            return bool(gl and gl.get("kind") == "grant" and "delete" in (sc.get("services") if isinstance(sc.get("services"), list) else []))
        if g:  # a standing grant on the unit whose scope's services name delete (the contract's version 3, card 15)
            gl = self.get(g) if isinstance(g, str) else None
            sc = ((gl or {}).get("body") or {}).get("scope") or {}
            return bool(gl and gl["kind"] == "grant" and self.grant_state(g) == "standing" and sc.get("unit") == target["unit"]
                        and "delete" in (sc.get("services") if isinstance(sc.get("services"), list) else []))
        c, u, t = self._db(), target["unit"], target.get("t") or ""
        newest = c.execute("SELECT max(t) FROM lines WHERE kind='brief'").fetchone()[0]
        shown = c.execute("SELECT 1 FROM lines l, json_each(l.body, '$.listed') j WHERE l.kind='brief' AND j.value=?", (target["id"],)).fetchone()
        run = c.execute("SELECT id, t FROM lines WHERE unit=? AND kind='run' ORDER BY t DESC, seq DESC LIMIT 1", (u,)).fetchone()
        closed = run and c.execute("SELECT 1 FROM lines WHERE unit=? AND kind IN ('close', 'abandoned') AND t >= ? AND (json_extract(body, '$.run') = ? "
                                   "OR id IN (SELECT frm FROM links WHERE rel = 'part_of' AND target = ?))", (u, run[1], run[0], run[0])).fetchone()
        return own and not shown and bool(run) and not closed and t >= run[1] and (newest is None or t > newest)

    def _target(self, id):
        line = self.get(id) if isinstance(id, str) else None
        if line is None:
            raise Refused(f"no line has the id {id!r}")
        return line

    def link(self, frm, rel, to, *, by):
        """A link line naming two lines that already exist and one of the nine relations; it lives in the unit of its from."""
        return self._append(self._target(frm)["unit"], "link", {"from": frm, "rel": rel, "to": to}, by=by)

    def strike(self, id, *, by, why, answer=None):
        """Keeps the line and takes its weight away; a word takes it back. answer names the maker's words on the week's card when the tool
        records his strike of an unused type or relation (_his_strike)."""
        return self._append(self._target(id)["unit"], "strike", dict({"target": id, "why": why}, **({"answer": answer} if answer else {})), by=by)

    def unstrike(self, id, *, by):
        return self._append(self._target(id)["unit"], "unstrike", {"target": id}, by=by)

    def delete(self, id, *, by, grant=None, why=None):
        """The line leaves find and the pages at once; its words stay in the file as the hold, seven days."""
        until = iso(self.clock() + _dt.timedelta(days=HOLD_DAYS)) if isinstance(by, dict) and by.get("kind") == "maker" else None
        return self._append(self._target(id)["unit"], "delete", {"target": id, "why": why, "grant": grant,
                                                                 "hold_days": HOLD_DAYS, "hold_until": until}, by=by)

    def undelete(self, mark_id, *, by):
        return self._append(self._target(mark_id)["unit"], "undelete", {"target": mark_id}, by=by)

    def erase(self, id, *, by):
        """The maker's erasure, at once: the words replaced by the mark in place, every later line rehashed forward, an erase line naming both heads, a block, a fresh index."""
        if check_by(by)["kind"] != "maker":
            raise Refused("only the maker erases; the partner strikes, or deletes inside a grant, and a hold ends at the maker's snapshot")
        return self._erase(id, check_by(by), "the maker's erase")

    def _erase(self, id, asked_by, why):
        with self.locked():
            self._writable()
            target = self._target(id)
            if target["mark"] == "erased":
                raise Refused("this line is already erased; only its mark remains")
            unit, e, remap, renames, old = target["unit"], mint_id(iso_ms(iso(self.clock()))), {}, [], None
            files = self._files(unit)
            old_head = new_head = _tail(files[-1])[0]["hash"]
            for path in files:
                data, out, changed = _read(path), [], False
                for b in _rows(data):
                    obj = json.loads(b)
                    if obj.get("id") == id and not obj["body"].get("erased"):
                        old, obj["body"] = obj["body"], {"erased": True, "by": e}
                    obj["prev"] = remap.get(obj.get("prev"), obj.get("prev"))
                    if old is not None and line_hash(obj) != obj["hash"]:
                        remap[obj["hash"]] = obj["hash"] = line_hash(obj)
                        changed = True
                    out.append((canonical(obj) + "\n").encode())
                    new_head = obj["hash"]
                if changed:
                    _put(path + ".new", b"".join(out) + data[data.rfind(b"\n") + 1:], "wb")
                    renames.append((path + ".new", path))
            if old is None:
                raise Refused(f"the line {id} is in the index but not in its unit's files; run verify")
            salt, src = os.urandom(16).hex(), (old.get("imported") or {}).get("sha256") if isinstance(old.get("imported"), dict) else None
            sha = lambda s: hashlib.sha256((salt + s).encode()).hexdigest()
            pending = {"erase": e, "unit": unit, "target": id, "old_head": old_head, "new_head": new_head, "asked_by": asked_by,
                       "why": why, "renames": renames, "payloads": sorted(set(payload_refs(old))),
                       "block": {"salt": salt, "body_sha256": sha(canonical(old)), "words_sha256": sha(words_of(old)),
                                 "source_sha256": sha(src) if src else None}}
            _put(self._p("cache", "reseal.pending"), canonical(pending).encode(), "wb")
            return self._finish_reseal(pending)

    def _finish_reseal(self, p):
        """Finishes an erasure, after a crash too: the renames, the erase line once, the erasure list and block, the payloads no kept line names, a fresh index."""
        for new, path in p["renames"]:
            os.path.exists(new) and os.replace(new, path)
            self._known[path] = _stat(path)
        unit, rec = p["unit"], self.unit_dir(p["unit"])
        rows = [json.loads(b) for u in self.units() for f in self._files(u) for b in _rows(_read(f))] if p["payloads"] else []
        kept = {s: [r["id"] for r in rows if s in payload_refs(r.get("body"))] for s in p["payloads"]}
        if f'"id":"{p["erase"]}"'.encode() not in _read(self._files(unit)[-1]):
            self._append_many(unit, [{"kind": "erase", "id": p["erase"], "by": TOOL, "_internal": True, "body": {
                "erased": p["target"], "old_head": p["old_head"], "new_head": p["new_head"], "asked_by": p["asked_by"],
                "why": p["why"], "kept": [{"sha256": s, "ids": ids} for s, ids in kept.items() if ids]}}])
        listed = os.path.join(rec, "erased.jsonl")
        if not os.path.exists(listed) or p["erase"].encode() not in _read(listed):
            _put(listed, (canonical({"id": p["target"], "t": iso(self.clock()), "by": p["asked_by"], "erase": p["erase"]}) + "\n").encode())
            _put(os.path.join(rec, "blocked.jsonl"), (canonical(p["block"]) + "\n").encode())
        for s in (s for s, ids in kept.items() if not ids):
            for u in self.units():
                f = os.path.join(self.unit_dir(u), "payloads", s)
                os.path.exists(f) and os.remove(f)
        shutil.rmtree(self._p("cache", "copy.git"), ignore_errors=True)  # the disposable copy repository held the old words
        self.rebuild_index()
        os.remove(self._p("cache", "reseal.pending"))
        return p["erase"]

    def snapshot(self, *, force=False):
        """Erases every deletion whose hold has ended and returns the erase ids; nothing erases on a timer, and force changes nothing at this stage."""
        with self.locked():
            return [self._erase(h["target"], None, "the hold ended") for h in self.holds(ended=True) if self.marks(h["target"]) != "erased"]

    def blocks(self, unit):
        """The secret blocks an erasure left in a unit: a salt and salted hashes, never the words."""
        p = os.path.join(self.unit_dir(unit), "blocked.jsonl")
        return [json.loads(b) for b in _rows(_read(p))] if os.path.exists(p) else []

    def payload(self, data, *, unit):
        """Keeps bytes beside the record, named by their sha256, after the secret scan; returns the sha256."""
        if not isinstance(data, (bytes, bytearray)):
            raise Refused("a payload is bytes")
        name = find_secret(bytes(data).decode("utf-8", "replace"))
        if name:
            raise Refused(f"the payload matches the secret pattern '{name}', so nothing was kept; keep secrets out of the record")
        if not isinstance(unit, str) or not UNIT_RE.match(unit):
            raise Refused(f"a unit is named in lower-case letters, digits, dots, dashes and underscores, not {unit!r}")
        sha = hashlib.sha256(data).hexdigest()
        with self.locked():
            self._writable()
            path = os.path.join(self.unit_dir(unit), "payloads", sha)
            if not os.path.exists(path):
                _put(path + ".part", bytes(data), "wb")
                os.replace(path + ".part", path)
        return sha

    def payload_path(self, sha256, *, unit=None):
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            return None
        return next((p for u in ([unit] if unit else self.units()) for p in [os.path.join(self.unit_dir(u), "payloads", sha256)]
                     if os.path.exists(p)), None)

    def _try(self, form, pointer):
        """Tries a receipt's pointer where its form can be tried: a path opens (a file's sha256 kept, a folder opens with none), a journal id resolves; nothing reaches the network."""
        if form == "path" and isinstance(pointer, str):
            if ".sandbox" in pointer.split("/"):
                return "fenced", None, None
            if os.path.isdir(pointer):
                return "path", True, None
            try:
                return "path", True, hashlib.sha256(_read(pointer)).hexdigest()
            except OSError:
                return "path", False, None
        if form == "journal" and isinstance(pointer, str):
            x = pointer.split(":", 1)[-1]
            hit = self.get(x) or self._db().execute("SELECT 1 FROM lines WHERE json_extract(body, '$.imported.id') = ?", (x,)).fetchone()
            return "journal", bool(hit), None
        return form, None, None

    def receipt(self, claim_id, form, *, pointer=None, payload=None, by, opened=None, sha256=None, opens_at=None, why=None, ids=None):
        """A receipt line for a claim, tried at once where its form can be tried, or carrying a result the caller already tried (opened, sha256, opens_at)."""
        if form not in FORMS:
            raise Refused(f"a receipt's form is one of {', '.join(FORMS)}, not {form!r}")
        claim = self._target(claim_id)
        form, opened, sha = (form, opened, sha256) if opened is not None else self._try(form, pointer)
        body = {"claim": claim_id, "form": form, "pointer": pointer, "opened": opened, "sha256": sha}
        body.update({k: v for k, v in (("opens_at", opens_at), ("why", why), ("ids", ids)) if v is not None})
        if payload is not None:
            body["output"] = {"payload": payload if isinstance(payload, str) else self.payload(payload, unit=claim["unit"])}
        return self._append(claim["unit"], "receipt", body, by=by)

    def recheck(self, id, *, by):
        """Tries a claim's receipts again where they opened (opens_at, else the pointer) and writes a new receipt that follows the old only when the result changed; returns the claim's mark."""
        x = self._target(id)
        for r in map(self.get, [r[0] for r in self._db().execute(RECEIPTS, (id,)).fetchall()]):
            b = r["body"]
            form, opened, sha = self._try(b.get("form"), b.get("opens_at") or b.get("pointer"))
            opened = False if opened and b.get("sha256") and sha != b["sha256"] else opened
            if opened != b.get("opened"):
                with self.locked():
                    new = self._append(x["unit"], "receipt", {k: v for k, v in (("claim", id), ("form", form), ("pointer", b.get("pointer")),
                                       ("opens_at", b.get("opens_at")), ("opened", opened), ("sha256", b.get("sha256") or sha)) if k != "opens_at" or v}, by=by)
                    self.link(new, "follows", r["id"], by=by)
        return self.marks(id)
