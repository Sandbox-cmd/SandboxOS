# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""Cards: raised with every part, answered with the maker's words kept exactly, counted against the day's asks, never asked again once
ruled unless something changed. An answer is the maker's only when its words match a said line the maker typed in a terminal session
of that host; anything else is recorded as the recorder's report, with the person not established, and binds nothing."""
import datetime as _dt
import os, re

from sandbox_os.store import Refused, line
from sandbox_os.store.line import iso, strip_arabic_marks
from sandbox_os.command import MAKER, TOOL, DOWN, say, words
from sandbox_os.pages.frame import welcome_answers

PARTS = ("decides", "stand", "other", "wrong", "saw", "answers")
BUDGET = {"little": 2, "some": 5, "often": None}
ANSWERS = ("yes", "no", "later", "words")
KEYS = {"yes": "yes", "y": "yes", "no": "no", "n": "no", "later": "later", "l": "later", "غ": "yes", "ى": "no", "ل": "later"}  # the pages' keys too
NEEDLESS = ("needless", "بلا حاجة")  # the word after an answer, and the pages' Arabic for it
ID_FIRST = re.compile(r"\s*([0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26})\b(.*)", re.S)


def setting(root):
    """The ask setting from welcome.md ("some" when it is absent or was skipped) and its cap of cards a day."""
    p = os.path.join(root, "welcome.md")
    m = re.search(r"\bask:\s*(little|some|often)\b", open(p, encoding="utf-8").read()) if os.path.exists(p) else None
    return (m.group(1) if m else "some"), BUDGET[m.group(1) if m else "some"]


def language(root, before="en"):
    """The language the workshop was welcomed in, its welcome.md read as the pages read it (card 38); before there is one, `before`."""
    p = os.path.join(root, "welcome.md")
    return (welcome_answers(open(p, encoding="utf-8").read(), words()).get("language") if os.path.exists(p) else before) or "en"


def local_day(t):
    """The maker's local day of a line's time."""
    return _dt.datetime.strptime(t, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=_dt.timezone.utc).astimezone().date().isoformat()


def ask_count(store, day):
    """Every card raised on the maker's local day and every card asked in the terminal, except one raised before one of the five acts
    one of the move's (card 23) and the week's card of proposals, counted outside the budget as the move's are (design section 2 point 4)."""
    return sum(1 for l in store.lines(kinds=["card", "host_ask"]) if local_day(l["t"]) == day and (l["kind"] == "card" and not any(
               (l["body"] or {}).get(k) for k in ("before_act", "move", "week_card")) or l["kind"] == "host_ask" and (l["body"] or {}).get("card")))


def needless_count(store, day):
    return sum(1 for l in store.lines(kinds=["needless"]) if local_day(l["t"]) == day and l["by"]["kind"] == "maker")


def _after(a, b):
    """Whether line a was written after line b: by sequence within one unit, by time across units."""
    return a["seq"] > b["seq"] if a["unit"] == b["unit"] else a["t"] > b["t"]


def versions(store, card_id):
    """A card and each version that asks it again (a card with a follows link to it), oldest first."""
    cards = {c["id"]: c for c in store.lines(kinds=["card"])}
    follows = [l["body"] for l in store.lines(kinds=["link"]) if (l["body"] or {}).get("rel") == "follows" and l["mark"] not in DOWN]
    out = [cards[card_id]] if card_id in cards else []
    for c in out:
        out += [cards[f["from"]] for f in follows if f["to"] == c["id"] and f["from"] in cards and cards[f["from"]] not in out]
    return out


def said_for(store, after, session, words=None, said=None):
    """The said line an answer rests on: typed by the maker in a terminal session, after the line it answers (the card's newest version),
    and named by no other answer. None when the maker typed nothing that matches; refused when the words exist but were typed before the
    question or already answer another one, so they can answer nothing here."""
    cands = [store.get(said)] if said else [l for l in store.lines(kinds=["said"]) if session and (l["body"] or {}).get("session") == session
                                            and l["body"].get("words") == words]
    cands = [l for l in cands if l and l["kind"] == "said" and l["by"]["kind"] == "maker" and (l["body"] or {}).get("surface") == "terminal"
             and l["mark"] not in DOWN and (not session or l["body"].get("session") == session)]
    if not cands:
        return None
    used = {(l["body"] or {}).get("said") for l in store.lines(kinds=["answer", "needless", "grant_back"])}
    ok = [l for l in cands if l["id"] not in used and _after(l, after)]
    if not ok:
        raise Refused("the maker's words were typed before this question was asked, or already answer another one; they answer nothing here")
    return ok[-1]


binds = line.binds  # the page's and the index's answer rules, kept in the store since batch C's Task 4 so its verbs read the same rule


def plain(w):
    return strip_arabic_marks(str(w).strip().lower().rstrip(".!,،"))


def answer_words(_cache={}):
    """Every word that answers a card: the keys, and the labels the pages show for a card's three answers in each language of the strings
    table, so the conversation and the pages read one list; Arabic without its short vowels."""
    if not _cache:
        from sandbox_os.pages.words import table, locales
        tab, langs = table(), {r["language"] for r in locales().values()}
        _cache.update({plain(k): a for k, a in KEYS.items()}, **{plain(tab[(f"answer.{a}", "")][g]): a for a in ("yes", "no", "later") for g in langs
                                                                 if tab[(f"answer.{a}", "")].get(g)})
    return _cache


def read_words(w):
    """(the card id the words begin with, or None; the answer they give, or None): an answer word, after an optional id."""
    m = ID_FIRST.fullmatch(w) if isinstance(w, str) else None
    return (m.group(1).upper() if m else None), answer_words().get(plain(m.group(2) if m else w if isinstance(w, str) else ""))


def open_cards(store, unit=None):
    """The cards no binding answer has settled (later settles nothing), not asked again in a newer version, not struck or gone; oldest first."""
    mine, settled = {c["id"]: c for c in store.lines(unit=unit, kinds=["card"])}, {}
    newer = {(l["body"] or {}).get("to") for l in store.lines(unit=unit, kinds=["link"]) if (l["body"] or {}).get("rel") == "follows"
             and (l["body"] or {}).get("from") in mine}
    for a in (a for a in store.lines(kinds=["answer"]) if binds(a)):
        settled[a["body"].get("card")] = a["body"].get("answer") != "later"
    return [c for i, c in mine.items() if c["mark"] not in DOWN and i not in newer and not settled.get(i)]


def decision(store, card_id):
    """The maker's newest answer to a card that binds (a newer one supersedes an older), or None."""
    a = [l for l in store.lines(kinds=["answer"]) if (l["body"] or {}).get("card") == card_id and binds(l)]
    return a[-1] if a else None


def may_act(store, card_id):
    """Whether the act a card decides may run: only on the maker's yes; a card waiting on the day's budget has none."""
    d = decision(store, card_id)
    return bool(d and d["body"].get("answer") == "yes")


def _on(store, unit, purpose):
    return {c["id"] for c in store.lines(unit=unit, kinds=["card"]) if (c["body"] or {}).get("purpose") == purpose}


def ruling(store, unit, purpose):
    """The maker's newest standing answer (later is not one) to a card on this unit and purpose: the ruling that settles it."""
    on = _on(store, unit, purpose)
    r = [a for a in store.lines(unit=unit, kinds=["answer"]) if a["body"].get("card") in on and binds(a) and a["body"].get("answer") != "later"]
    return r[-1] if r else None


def five(key, saw=None, /, lang="en", **slots):
    """A card's five parts in the table's words in lang, and its three answers; `saw` is passed where it is the record's words and not the tool's."""
    return dict({p: saw if p == "saw" and saw is not None else say(f"{key}.{p}", lang=lang, **slots) for p in PARTS[:5]}, answers=["yes", "no", "later"])


def raise_(store, unit, body, *, by, before_act=None, can_wait=True, of_the_move=False, of_the_week=False, thing=None):
    """Raises a card with every part, or refuses it. A question ruled on this unit and purpose, or called needless, is not raised again
    unless body.changed names the ruling and the line that changed: the ruling is applied and shown under since you left. A card over the
    day's budget waits for the next day (nothing it decides runs meanwhile) and a line says by how many the day ran over. One of the move's,
    raised by the tool with of_the_move (card 23), carries body.move, never counts against the budget and never waits for it; the week's card
    of proposals, raised by the tool with of_the_week, carries body.week_card and is counted the same way. A body's own move or week_card
    is dropped: only the tool's flag marks a card so. thing names the object the card is about, as the line's about field."""
    missing = [k for k in PARTS if not body.get(k)]
    if missing or len(body.get("answers") or []) != 3:
        raise Refused(say("refuse.card.parts", lacks=", ".join(missing) or "its three answers"))
    if of_the_move and by.get("kind") != "tool":
        raise Refused("the move's cards are raised by the tool on the day (R-MOVE-16), never by the partner or a person")
    if of_the_week and by.get("kind") != "tool":
        raise Refused("the week's card of proposals is raised by the tool, never by the partner or a person")
    apart = of_the_move or of_the_week  # outside the asking budget, never waiting for it
    body, purpose = dict({k: v for k, v in body.items() if k not in ("move", "week_card")}, about=body.get("about") or unit,
                         version=body.get("version") or 1, **({"move": True} if of_the_move else {}),
                         **({"week_card": True} if of_the_week else {})), body.get("purpose")
    with store.locked():
        if purpose and not body.get("changed"):
            r = ruling(store, unit, purpose)
            nl = [n for n in store.lines(unit=unit, kinds=["needless"]) if makers_needless(store, n)
                  and (store.get(n["body"]["answer"]) or {}).get("body", {}).get("card") in _on(store, unit, purpose)]
            if r or nl:
                store.append(unit, "note", {"event": "ruling-applied" if r else "needless-applied", "ruling": (r or nl[-1])["id"], "purpose": purpose,
                                            "text": f"asked before and {'ruled' if r else 'called needless'}: {purpose}; applied, not asked again"}, by=by)
                return None
        if body.get("changed") and body["version"] == 1:
            body["version"] = max([store.get(c)["body"].get("version", 1) for c in _on(store, unit, purpose)] + [1]) + 1
        name, cap = setting(store.root)
        day = local_day(iso(store.clock()))
        n = ask_count(store, day) + (0 if before_act or apart else 1)
        over = cap is not None and n > cap and not before_act and not apart
        body.update({"before_act": before_act} if before_act else {})
        body.update({"waits": (_dt.date.fromisoformat(day) + _dt.timedelta(days=1)).isoformat()} if over and can_wait else {})
        cid = store.append(unit, "card", body, by=by, about=thing)
        if over:
            store.append(unit, "note", {"event": "asks-over", "day": day, "setting": name, "cap": cap, "count": n, "over_by": n - cap,
                                        "text": f"the day ran over its asks by {n - cap}: {n} cards against '{name}' ({cap})"}, by=TOOL)
    return cid


def answer(store, card_id, answer=None, *, by, words=None, session=None, said=None, host=None, act_ran=False, report=False):
    """Records an answer. From the conversation it is the maker's only when it rests on a said line the maker typed in a terminal session
    after the card's newest version and no other answer names; the decision is then read from those words (yes, no or later, trimmed and
    lower-cased, else words) and never supplied, and a decision that contradicts them is refused. Anything else is the recorder's report,
    person not established, binding nothing, and so is every report (the partner's answer_report). A second answer supersedes the first,
    both kept; when the first one's act already ran, the second becomes a card about undoing it. An answer to an older version is kept with
    stale: true."""
    card = store.get(card_id)
    if not card or card["kind"] != "card":
        raise Refused(f"no card has the id {card_id!r}")
    newest = versions(store, card_id)[-1]
    s = None if report else said_for(store, newest, session, words if words is not None else answer, said)
    if s:
        w = s["body"]["words"]
        read = read_words(w)[1] or "words"
        if answer is not None and answer != read:
            raise Refused(f"the maker's words read '{read}', so an answer of '{answer}' is refused; the decision is read from the words, never supplied")
        body = {"card": card_id, "answer": read, "words": w, "said": s["id"], "from": "conversation", "host": host,
                "transcript": {"session": s["body"].get("session"), "position": s["id"]}}
    else:
        if answer not in ANSWERS:
            raise Refused(f"an answer is yes, no, later or words, not {answer!r}")
        body = {"card": card_id, "answer": answer, "words": words, "from": "conversation", "host": host, "person": "not established",
                "transcript": {"session": session, "position": None}, "actor": {k: by.get(k) for k in ("kind", "name", "model", "host")}}
    body.update({"stale": True} if newest["id"] != card_id else {})
    with store.locked():
        prev = decision(store, card_id) if s else None
        a = store.append(card["unit"], "answer", body, by=MAKER if s else TOOL)  # no person established: the tool records it, naming who recorded it
        if prev:
            store.link(a, "supersedes", prev["id"], by=TOOL)
        if prev and act_ran and prev["body"].get("answer") != body["answer"]:
            raise_(store, card["unit"], dict(five("card.undo", decides=card["body"]["decides"], first=prev["id"], then=a),
                                         about=card["body"].get("about"), undoes=card_id, purpose=f"undo:{card_id}"), by=by)
    return a


def answer_from_said(store, said, *, host, session, named):
    """The conversation's answer path, the only one by which the maker's words in a session become an answer line, bound by id (row 54): a
    said line the maker typed in a terminal whose words are an answer binds to the card its words name by id, or to the one card the
    partner's last message named while that card is open; several named, or none and no id in the words, bind nothing, and a note names
    the cards it could have been and says the partner must name one. Words no whole answer are still one when the card the partner named
    takes them in its own form (_reads; Astra's challenge of batch D, finding 5), by the same rule. Returns the answer's id or None."""
    l = store.get(said) if isinstance(said, str) else said
    if not l or l["kind"] != "said" or l["by"]["kind"] != "maker" or (l["body"] or {}).get("surface") != "terminal":
        return None
    cid, read = read_words(l["body"].get("words"))
    ours, named = {c["id"]: c for c in open_cards(store)}, sorted(set(named or []))
    if not read:  # a card's own form binds only to a card named, never after an id, so the words read whole as said
        cid = None
        if not any(c in ours and _reads(store, ours[c], l["body"].get("words")) for c in named):
            return None
    if cid:
        card = cid if (store.get(cid) or {}).get("kind") == "card" else None
    else:
        card = named[0] if len(named) == 1 and named[0] in ours else None
    if not card:
        could = [c for c in named if c in ours] or [i for i, c in ours.items() if (c["body"] or {}).get("session") == session]
        with store.locked():
            store.append(l["unit"], "note", {"event": "answer-unbound", "said": l["id"], "session": session, "host": host, "candidates": could,
                                             "text": say("note.answer.unbound", words=str(l["body"]["words"]), n=len(could))}, by=TOOL)
        return None
    return answer(store, card, None, by=TOOL, session=session, said=l["id"], host=host)


def _reads(store, card, words):
    """Whether words that are no whole yes, no or later answer this card in its own form: on the week's card, words read item by item
    (growth.read_choice); on a which card (names.ask's), one candidate's number or exact name (names.chosen); on any other, never."""
    b = card["body"] or {}
    if b.get("week_card") is True:
        from sandbox_os.command import growth
        return growth.read_choice(words, len(b.get("items") or [])) is not None
    if str(b.get("purpose") or "").startswith("which:"):
        from sandbox_os.command import names
        return names.chosen(words, list(b.get("candidates") or []), store) is not None
    return own_answer(b, words) is not None


def own_answer(body, words):
    """The answer words give on a card in its own form (Astra's challenge of batch E, finding 6), or None: one of the answers the card
    declares, read by its words (cold, delete), or on a card of form unit, which asks for a name in his words, a unit's name. A card of
    yes, no and later alone takes no other word, and a bare yes, no or later is read as a whole answer before this."""
    labels = body.get("answers") if isinstance(body.get("answers"), list) else []
    w = words.strip() if isinstance(words, str) else ""
    hit = next((x for x in labels if isinstance(x, str) and plain(x) == plain(w) and plain(x) not in ANSWERS), None)
    if hit:
        return hit
    if body.get("form") == "unit" and line.UNIT_RE.match(w) and plain(w) not in answer_words():
        return w
    return None


def _desk(a):
    return a["by"]["kind"] == "maker" and (a["body"] or {}).get("from") == "page" and a["body"].get("presence") == "desk"


def makers_needless(store, n):
    """Whether a needless line is the maker's by the rule, and so settles a question: on his own word typed in a terminal session (its said
    line), or after his answer from the page at the desk."""
    b, s = n["body"] or {}, store.get((n["body"] or {}).get("said") or "")
    if n["by"]["kind"] != "maker" or n["mark"] in DOWN:
        return False
    if s:
        return s["kind"] == "said" and s["by"]["kind"] == "maker" and plain(s["body"].get("words")) in NEEDLESS
    return _desk(store.get(b.get("answer") or "") or {"by": {}, "body": {}})


def needless(store, answer_id, *, by, session=None, presence=None):
    """The word needless after an answer, the maker's on his own word typed in this session (or its Arabic), or in the page's box at the desk
    after his answer there; anything else is refused. Counted in the week; the question comes back only when something changed."""
    a = store.get(answer_id)
    if not a or a["kind"] != "answer":
        raise Refused(f"needless follows an answer, and {answer_id!r} is not one")
    said = next((s for w in NEEDLESS for s in [said_for(store, a, session, w)] if s), None) if session else None
    if not (said or presence == "desk" and _desk(a)):
        raise Refused(say("refuse.needless"))
    with store.locked():
        return store.append(a["unit"], "needless", {"answer": answer_id, "said": said["id"]} if said else {"answer": answer_id, "from": "page",
                                                                                                          "presence": "desk"}, by=MAKER)


def not_established(store, since=None):
    """Every said line not typed in a terminal and every answer whose person is not established: the brief lists them as such."""
    return [l for l in store.lines(kinds=["said", "answer"], since=since) if l["by"]["kind"] != "maker" and (
        l["kind"] == "said" and (l["body"] or {}).get("surface") != "terminal" or l["kind"] == "answer" and (l["body"] or {}).get("person") == "not established"
        or (l["body"] or {}).get("presence") == "none")]


def correction(store, unit, subject, said_id, *, by):
    """The partner's reading of a correction, a note with its subject (shown, strikeable); the second on one subject raises
    "make it a rule?", quoting the maker both times with dates and projects. Returns (note, card or None)."""
    with store.locked():
        n = store.append(unit, "note", {"event": "correction", "subject": subject, "said": said_id, "text": f"a correction about {subject}"}, by=by)
        same = [l for l in store.lines(kinds=["note"]) if (l["body"] or {}).get("event") == "correction" and l["body"].get("subject") == subject
                and l["mark"] not in DOWN]
        if len(same) != 2:
            return n, None
        quotes = [(store.get(l["body"]["said"]), l["unit"]) for l in same]
        saw = "; ".join(f"{s['t'][:10]} on {u}: \"{s['body'].get('words')}\"" for s, u in quotes if s)
        return n, raise_(store, unit, dict(five("card.rule", saw, subject=subject), about=unit, purpose=f"rule:{subject}", subject=subject), by=by)


def repeat_count(store, subject):
    return sum(1 for l in store.lines(kinds=["note"]) if (l["body"] or {}).get("event") == "correction" and l["body"].get("subject") == subject and l["mark"] not in DOWN)


def make_rule(store, card_id, *, by, text):
    """A rule stands only on the maker's yes to its card; the rule line comes from that answer."""
    d, card = decision(store, card_id), store.get(card_id)
    if not d or d["body"].get("answer") != "yes":
        raise Refused("a rule about how the partner behaves stands only on the maker's yes to its card")
    with store.locked():
        r = store.append(card["unit"], "rule", {"text": text, "card": card_id, "subject": card["body"].get("subject")}, by=by)
        store.link(r, "came_from", d["id"], by=TOOL)
    return r


def split(store, unit, said_id, *, by, about_you=None, fact=None):
    """A sentence mixing the maker and the work, split: the half about the maker waits on a card that says which half it was; the half
    about the work is a fact at once, the partner's, strikeable. Returns (about_you, card, fact)."""
    said = store.get(said_id)
    words = said["body"].get("words") if said else None
    with store.locked():
        ab = store.append(unit, "about_you", {"text": about_you, "said": said_id}, by=by) if about_you else None
        card = raise_(store, unit, dict(five("card.you", about_you=about_you, day=said["t"][:10], words=str(words), rest=" " + say("card.you.rest", fact=fact) if fact else ""),
                                    about=ab, purpose=f"about you: {about_you}"), by=by) if ab else None
        f = store.append(unit, "fact", {"text": fact, "said": said_id}, by=by) if fact else None
    return ab, card, f
