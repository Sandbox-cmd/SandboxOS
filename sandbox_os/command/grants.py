# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""Grants: born only from the maker's own words, read back as a card before they stand, corrected in the box with both readings kept,
taken back by one word, and come back as a card on their last day. The partner never widens one; a grant's state is computed."""
from sandbox_os.store import Refused, verbs
from sandbox_os.command import MAKER, TOOL, DOWN, cards, say
from sandbox_os.hosts.boundary import standing_grants


def covers(scope, until, *, store=None):
    """What a grant would cover, as the partner proposes it, in words for its read-back card; the verbs it names by their names when the
    store is given; deleting is said apart (card 15)."""
    paths, services, vs = scope.get("paths") or [], scope.get("services") or [], scope.get("verbs") or []
    names = [((store.verb(v) if store else None) or {}).get("name") or v for v in vs]
    return (f"what it would cover, as I propose it: the project {scope.get('unit')}; " + (f"the paths {', '.join(paths)}" if paths else "no paths")
            + "; " + (f"the services {', '.join(services)}" if services else "no services") + (f"; the verbs {', '.join(names)}" if names else "")
            + "; " + (f"until {until}" if until else "until you take it back")
            + (f"; this grant also lets the partner delete lines in {scope.get('unit')}, with the mark and the hold" if "delete" in list(services) else ""))


def _verbs(store, scope):
    """Refuses a scope whose verbs are not a list of declared, standing verbs, or that names one of the five acts, which never has a grant."""
    vs = scope.get("verbs", [])
    if not isinstance(vs, list):
        raise Refused("a grant's verbs are a list of the declared verbs it covers, by their ids; this one is not, so nothing was written")
    for v in vs:
        view = store.verb(v) if isinstance(v, str) else None
        if not view or not view["declared"] or view["mark"] in DOWN:
            raise Refused(f"a grant names only declared verbs that stand, and {str(v)[:40]!r} is not one, so nothing was written")
        if view["act"] in verbs.ACTS:
            raise Refused(say("refuse.grant.five", name=view["name"], act=view["act"]))


def read_back(store, sentence, *, by, unit, reading, scope, said, until=None, take_back="back"):
    """Appends a grant line (the sentence exactly, the partner's one-line reading, what it covers, until when, how to take it back) and
    its read-back card quoting the sentence. A sentence the maker did not type (a fetched file, a tool's output) raises nothing. scope may
    name verbs (scope.verbs, declared standing verb ids); a five act among them is refused."""
    if not reading or not isinstance(scope, dict) or not {"unit", "paths", "services"} <= set(scope):
        raise Refused("a grant carries the partner's reading and what it covers (unit, paths, services); this one lacks one, so nothing was written")
    _verbs(store, scope)
    s = store.get(said) if isinstance(said, str) else None
    if not s or s["kind"] != "said" or s["by"]["kind"] != "maker" or sentence not in str((s["body"] or {}).get("words")):
        raise Refused("a grant is born only from the maker's own words, typed in the terminal or on the page; this sentence is not among them")
    with store.locked():
        g = store.append(unit, "grant", {"sentence": sentence, "reading": reading, "scope": scope, "until": until, "take_back": take_back, "said": said}, by=by)
        c = cards.raise_(store, unit, dict(cards.five("card.grant", sentence=sentence, reading=reading, take_back=take_back, day=s["t"][:10], covers=covers(scope, until, store=store)),
                                       about=g, purpose=f"grant:{g}", **{k: s["body"][k] for k in ("session", "host") if s["body"].get(k)}), by=by)
    return g, c


def correct(store, card_id, *, by, reading, scope):
    """A correction typed in the box of a read-back card: a second reading superseding the first (both kept), read back on the same card
    asked again (its next version, following it), so the grant stands only on the maker's yes to the reading that will stand."""
    _verbs(store, scope if isinstance(scope, dict) else {})
    chain = cards.versions(store, card_id)
    first = store.get((chain[0]["body"] if chain else {}).get("about") or "")
    said = [a for c in chain for a in store.lines(kinds=["answer"]) if (a["body"] or {}).get("card") == c["id"] and a["by"]["kind"] == "maker"
            and a["body"].get("answer") == "words"]
    if not first or first["kind"] != "grant" or not said:
        raise Refused("a second reading answers the maker's own correction in the box of a grant's read-back card, and there is none")
    last = chain[-1]
    with store.locked():
        g = store.append(first["unit"], "grant", dict(first["body"], reading=reading, scope=scope, card=card_id, corrects=said[-1]["id"]), by=by)
        store.link(g, "supersedes", last["body"]["about"], by=by)
        c = cards.raise_(store, first["unit"], dict({k: last["body"][k] for k in ("stand", "other", "answers")}, about=g, version=(last["body"].get("version") or 1) + 1,
                                                    decides=say("card.grant.again.decides", sentence=first["body"]["sentence"], reading=reading),
                                                    wrong=say("card.grant.again.wrong", reading=reading),
                                                    saw=say("card.grant.again.saw", words=str(said[-1]["body"].get("words")), covers=covers(scope, first["body"].get("until"), store=store)),
                                                    purpose=f"grant:{g}", changed={"correction": said[-1]["id"], "reading": g}), by=by)
        store.link(c, "follows", last["id"], by=by)
    return g, c


def take_back(store, grant_id, *, by, words="back", session=None):
    """One word takes a grant back: a dated line, the grant kept readable, covering nothing after. Narrowing needs no proof of person."""
    g = store.get(grant_id)
    if not g or g["kind"] != "grant":
        raise Refused(f"no grant has the id {grant_id!r}")
    try:
        said = cards.said_for(store, g, session, words)
    except Refused:
        said = None
    with store.locked():
        return store.append(g["unit"], "grant_back", {"grant": grant_id, "words": words, "said": said["id"]} if said else {"grant": grant_id, "words": words, "person": "not established"},
                            by=MAKER if said else by if by.get("kind") != "maker" else TOOL)


def standing(store, unit):
    """The grants that stand for a unit now."""
    return standing_grants(store, unit)


def expiring(store, day, *, by):
    """Each standing grant whose time runs out today comes back as a card, once."""
    out = []
    for g in (g for u in store.units() for g in standing_grants(store, u) if (g["body"] or {}).get("until") == day and g["unit"] == u):
        b = g["body"]
        if cards._on(store, g["unit"], f"expiring:{g['id']}"):
            continue
        c = cards.raise_(store, g["unit"], dict(cards.five("card.expiring", sentence=b["sentence"], id=g["id"], reading=b["reading"]),
                                            about=g["id"], purpose=f"expiring:{g['id']}"), by=by)
        out += [c] if c else []
    return out
