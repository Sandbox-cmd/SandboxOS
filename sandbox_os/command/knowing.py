# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""What the partner knows, written down where the maker can read and strike it (design section 4): a belief about a thing with how it
came to be known, a goal read from his own words, an assumption made before the work, an open question with who could settle it, what
it costs and the day it lapses, that question's three ends, and a pre-mortem before anything costly. Each write goes through the store's
one door as its caller, the partner on the tools, never as the maker; each returns the id it wrote, and each refusal says why in plain words."""
from sandbox_os.store import Refused
from sandbox_os.command import DOWN, cards, say
from sandbox_os.pages.read import Reader, question_state

ENDS = ("settled", "dropped", "card")  # how an open question ends: a line answers it, it is dropped with a reason, or it goes to him as a card


def believe(store, unit, about, facet, value, basis, *, by, source=None, confidence=None):
    """A belief: a fact about the thing, naming the facet, the value and its basis (he said, a check showed, I read it in, my guess), with
    its source and a likely or unsure word when given; the store refuses a basis outside the four and a guess about a person."""
    body = {"facet": facet, "value": value, "basis": basis}
    body.update({k: v for k, v in (("source", source), ("confidence", confidence)) if v is not None})
    with store.locked():
        return store.append(unit, "fact", body, by=by, about=about)


def _his(store, id):
    """Whether a line is the maker's own said line and still stands (not struck, deleted, erased or replaced by a newer word of his)."""
    line = store.get(id) if isinstance(id, str) else None
    return bool(line and line["kind"] == "said" and line["by"]["kind"] == "maker" and line["mark"] not in DOWN)


def propose_goal(store, unit, text, fragments, *, by, about=None, shows=None, supersedes=None):
    """A goal in the partner's words, read from the maker's standing said lines (each one a came_from link), with what would show it
    reached; with supersedes, it replaces an earlier standing goal, which his correction made wrong."""
    if not isinstance(fragments, (list, tuple)) or not fragments:
        raise Refused(say("refuse.goal.cites"))
    bad = next((f for f in fragments if not _his(store, f)), None)
    if bad is not None:
        raise Refused(f"a goal is read from your own words: {bad} is not a said line of yours that stands")
    body = {"text": text, "fragments": list(fragments), **({"shows": shows} if shows is not None else {})}
    with store.locked():
        old = store.get(supersedes) if isinstance(supersedes, str) else None
        if supersedes is not None and not (old and old["kind"] == "goal" and old["mark"] not in DOWN):
            raise Refused(f"a goal replaces only a goal that still stands; {supersedes} is "
                          + (f"a {old['kind']} line" if old and old["kind"] != "goal" else "a goal that no longer stands" if old else "no line")
                          + ", and nothing was written")
        g = store.append(unit, "goal", body, by=by, about=about)
        if old:
            store.link(g, "supersedes", supersedes, by=by)
    return g


def _run(store, run):
    line = store.get(run) if isinstance(run, str) else None
    if not line or line["kind"] != "run":
        raise Refused(f"the run named, {run!r}, is not a run line, so nothing was written")


def assume(store, unit, text, *, by, about=None, run=None):
    """An assumption, written before the work it is made for; with run, the run leans on it (a came_from link), so striking it marks the run."""
    with store.locked():
        if run is not None:
            _run(store, run)
        a = store.append(unit, "assumption", {"text": text}, by=by, about=about)
        if run is not None:
            store.link(run, "came_from", a, by=by)
    return a


def open_question(store, unit, text, settles, cost, until, *, by, about=None, blocks=False):
    """An open question: what is asked, who or what could settle it, what leaving it open costs, whether it blocks the work, and the day
    it lapses (until, YYYY-MM-DD), after which it shows as past."""
    with store.locked():
        return store.append(unit, "question", {"text": text, "settles": settles, "cost": cost, "blocks": bool(blocks)}, by=by,
                            about=about, valid_until=until)


def settle_question(store, question, how, *, by, line=None, why=None):
    """Ends an open question one of three ways: settled (the line that settles it, a fact, a check or an answer, answers it), dropped
    (struck, with why), or card (raised to the maker as a card about it). A question already ended, or another how, is refused."""
    if how not in ENDS:
        raise Refused(f"a question ends settled, dropped or card, not {how!r}; nothing was written")
    with store.locked():
        q = store.get(question) if isinstance(question, str) else None
        if not q or q["kind"] != "question":
            raise Refused(f"{question!r} is not a question line, so there is nothing to settle")
        state = question_state(Reader(store), q)
        if state not in ("open", "expired unread"):
            raise Refused(f"the question {question} is already {state}, so it is not ended again; nothing was written")
        if how == "settled":
            if not isinstance(line, str):
                raise Refused("a settled question names the line that settles it, a fact, a check or an answer, as line; nothing was written")
            return store.link(line, "answers", question, by=by)
        if how == "dropped":
            if not isinstance(why, str) or not why.strip():
                raise Refused("a dropped question says why it was dropped, as why, so the drop is a line the maker can read; nothing was written")
            return store.strike(question, by=by, why=why)
        b, purpose, past = q["body"], f"question:{question}", q.get("mark") == "past"  # yes keeps it open, no drops it, later asks again
        cid = cards.raise_(store, q["unit"], dict(cards.five(
            "card.question", now=say("card.question.now") if past else "", text=b["text"], settles=b["settles"], cost=b["cost"], id=question, asked=q["t"][:10],
            when=say("card.question.past" if past else "card.question.open", day=str(q.get("valid_until")))), wrong=b["cost"], about=question, purpose=purpose), by=by)
        if cid is None:  # ruled before on this purpose: the ruling stands and is applied, not asked again
            r = cards.ruling(store, q["unit"], purpose)
            return r["id"] if r else None
        return cid


def premortem(store, unit, text, *, by, about=None, run=None):
    """A pre-mortem before anything costly: a note saying how it will have failed in a week, part of the run when one is named."""
    with store.locked():
        if run is not None:
            _run(store, run)
        p = store.append(unit, "note", {"event": "pre-mortem", "text": text}, by=by, about=about)
        if run is not None:
            store.link(p, "part_of", run, by=by)
    return p
