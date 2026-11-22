# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""Names are his (design section 2 point 6, and section 4 point 7's short read, which names things in his words): a thing's name is what
he calls it, and its other names are alias facts, so his words resolve to the thing he means. When his words fit several things, the
partner asks once which, as one card counted against the asking budget as any question; asked again before he answers, the open card
comes back and no second is raised. His answer, by the number or the name of one candidate, teaches the alias: a fact about the thing
he meant, by the tool on his word, so the same words resolve to it next time. Every refusal says why in plain words."""
import re

from sandbox_os.store import Refused
from sandbox_os.command import DOWN, TOOL, cards, say

VOCAB = ("type", "relation")  # the vocabulary's own objects are never a thing his words mean
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def _found(store, words):
    return [x["id"] for x in store.resolve(words) if x["type"] not in VOCAB]


def _taught(store, oid, words):
    """Whether a standing alias fact his answer taught says these words about this thing."""
    return any((f["body"] or {}).get("facet") == "alias" and f["body"].get("taught") is True and cards.plain(f["body"].get("value")) == cards.plain(words)
               and f["mark"] not in DOWN for f in store.lines(about=oid, kinds=["fact"]))


def which(store, words):
    """The thing his words mean: the one thing Store.resolve finds; among several, the one his answer taught these words as its alias; else None."""
    found = _found(store, words) if isinstance(words, str) and words.strip() else []
    if len(found) == 1:
        return found[0]
    taught = [o for o in found if _taught(store, o, words)]
    return taught[-1] if len(taught) == 1 else None


def _purpose(words):
    return f"which:{cards.plain(words)}"


def ask(store, unit, words, *, by):
    """His words resolved, or asked about once: {"thing": id} when they mean one thing (which); else the open card that already asks, as it
    is; else one card listing the candidates by number, with their name, type and unit, raised as any question (a ruled or needless one is
    applied by cards.raise_ and not asked again, unless he took back the alias the ruling taught: then the card is raised as a changed
    ruling naming his strike). Returns {"card": id or None, "candidates": [ids]}. Refused when no thing is named so."""
    if not isinstance(words, str) or not words.strip():
        raise Refused("the maker's words name the thing asked about, and these are empty; nothing was asked")
    t = which(store, words)
    if t:
        return {"thing": t}
    with store.locked():
        mine = next((c for c in cards.open_cards(store) if (c["body"] or {}).get("purpose") == _purpose(words)), None)
        if mine:
            return {"card": mine["id"], "candidates": list(mine["body"].get("candidates") or [])}
        found = _found(store, words)
        if not found:
            raise Refused(say("refuse.name", words=repr(words[:60])))
        things = [store.thing(o) for o in found]
        saw = "\n".join(f"{i}. {x['name']}, a {x['type']} in {x['object']['unit']}" for i, x in enumerate(things, 1))
        r, on = cards.ruling(store, unit, _purpose(words)), cards._on(store, unit, _purpose(words))
        back = [m for m in _taken_back(store, [f for f in store.lines(kinds=["fact"]) if (f["body"] or {}).get("taught") is True
                                               and f["body"].get("card") in on]) if r and cards._after(m, r)]
        card = cards.raise_(store, unit, dict(cards.five("card.which", saw, words=words), about=unit, purpose=_purpose(words), candidates=found, words=words,
            **({"changed": {"ruling": r["id"], "line": back[-1]["id"], "text": "you took back the alias your answer taught"}} if back else {})), by=by)
        return {"card": card, "candidates": found}


def chosen(words, cands, store):
    """The one candidate his answer names, by its number (Western or Arabic-Indic digits) or by its name; else None."""
    w = str(words or "").translate(DIGITS).strip().rstrip(".!،,")
    if re.fullmatch(r"[0-9]+", w):
        return cands[int(w) - 1] if 1 <= int(w) <= len(cands) else None
    hit = [c for c in cands if cards.plain(((store.get(c) or {}).get("body") or {}).get("name") or "") == cards.plain(w)]
    return hit[0] if len(hit) == 1 else None


def settle(store, *, by=TOOL):
    """Each which card his binding answer in words settles by naming one candidate, once per answer: an alias fact about the thing he meant,
    by the tool, his words as its value, taught true and the answer named; its basis he said with his said line when the answer rests on
    one, else I read it in with the answer named. A newer answer that changes the choice supersedes the alias the older one taught, and an
    answer from before he took an alias back teaches nothing (Astra's challenge of batch D, finding 7). Returns the facts' ids."""
    out = []
    with store.locked():
        taught = [f for f in store.lines(kinds=["fact"]) if (f["body"] or {}).get("taught") is True]
        for c in store.lines(kinds=["card"]):
            b = c["body"] or {}
            if not str(b.get("purpose") or "").startswith("which:") or c["mark"] in DOWN:
                continue
            d = cards.decision(store, c["id"])
            if not d or d["body"].get("answer") != "words":
                continue
            o = chosen(d["body"].get("words"), list(b.get("candidates") or []), store)
            mine = [f for f in taught if f["body"].get("card") == c["id"]]
            up = [f for f in mine if f["mark"] not in DOWN]
            if (not o or (store.get(o) or {}).get("mark") in DOWN or any(_from(f, d) for f in mine) or any(f["about"] == o for f in up)
                    or any(not cards._after(d, m) for m in _taken_back(store, mine))):
                continue  # taught by this answer already, the same choice standing, or words from before he took the alias back
            said = d["body"].get("said")
            src = {"basis": "he said", "source": said} if said else {"basis": "I read it in", "source": f"your answer {d['id']} on the page"}
            out.append(store.append(store.get(o)["unit"], "fact", dict({"facet": "alias", "value": b.get("words"), "taught": True, "card": c["id"],
                                                                       "answer": d["id"]}, **src), by=by, about=o))
            for old in up:  # his newer answer changed the choice: the alias it replaces is superseded, kept
                store.link(out[-1], "supersedes", old["id"], by=by)
    return out


def _taken_back(store, facts):
    """The lines that struck, deleted or erased these taught facts: his taking an alias back."""
    return [m for f in facts if f["mark"] in ("struck", "deleted", "erased") and (m := store.get(f.get("mark_set_by") or ""))]


def _from(f, d):
    """Whether a taught fact came from this answer: it names the answer, or (written before it did) its said line or its sentence."""
    b = f["body"]
    return b.get("answer") == d["id"] or b.get("source") in (d["body"].get("said") or d["id"], f"your answer {d['id']} on the page")
