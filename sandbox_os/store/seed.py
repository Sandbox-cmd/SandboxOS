# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The plain starting set a new workshop records, as data: types and relations anyone's work has and the tool's own working ones, none
of the maker's business (card 30). His own set from the census (03-design.md section 2) is a data file outside the release,
morning/census/seed.json, which load() records once. And the functions that record them."""
import hashlib, json

from sandbox_os.store.log import _read, _rows

UNIT = "workshop"  # the contract's reserved unit, where the vocabulary lives
STANDING_OUT = ("erased", "deleted", "struck", "superseded")  # marks that take a type or a relation out of the vocabulary
GROUPS = ("things a project is about", "decisions and their reasons", "tools and services", "people", "places and environments")
_P, _D, _T, _H, _E = GROUPS


def _t(name, group, gloss, ground):
    return {"name": name, "group": group, "gloss": gloss, "ground": ground}


# ground: a schema.org type, or a Wikidata item named by its English label (its Q-number is not looked up from here), or None; build is
# here because the welcome names it when no other type is near his words (command.flow.propose_first), and the last four are the tool's
# working vocabulary: its own code declares and runs a verb, guards a secret and a folder only he writes, and shows a decision
TYPES = (
    _t("project", _P, "A piece of work with its own folder and its own record, from its first line to its close.", "schema.org/Project"),
    _t("page", _P, "A page someone opens and reads, on the web or from a file.", "schema.org/WebPage"),
    _t("person", _H, "One human being, named as the maker names them.", "schema.org/Person"),
    _t("service", _T, "An outside system the work reaches over a connection.", "schema.org/WebAPI"),
    _t("file", _E, "One named file on a disk.", "schema.org/DigitalDocument"),
    _t("idea", _P, "A thought worth keeping before it is a piece of work.", 'Wikidata "idea"'),
    _t("build", _P, "One made copy of a program or a page, ready to open or hand on.", "schema.org/SoftwareApplication"),
    _t("verb", _T, "A declared act that reaches outside the folder: the service it reaches, its parameters, which of the five acts it is, "
       "what its dry run shows and the receipt it expects.", "schema.org/Action"),
    _t("secret", _E, "A password or a key, recorded by its name only; its value never touches the record.", None),
    _t("folder", _E, "A named place on a disk that holds files.", 'Wikidata "directory"'),
    _t("decision", _D, "A ruling the maker made, with what it rests on and where it applies.", 'Wikidata "decision"'),
)


def _r(name, gloss, frm, to):
    return {"name": name, "gloss": gloss, "from": frm, "to": to}


# from and to: the type names a relation usually joins, or None where several fit; the names are the census's own, so his set adds none twice
RELATIONS = (
    _r("belongs_to", "A thing is owned by a person.", None, None),
    _r("runs_on", "A thing works on top of a service or another thing.", None, None),
    _r("lives_at", "A thing is kept at a place: a folder, a disk or an address.", None, None),
    _r("made_by", "A thing was made by a person or a program.", None, None),
    _r("for", "A thing is made for the person it serves.", None, "person"),
)
SERVICES, VERBS = (), ()  # the release seeds no service and no verb; the pages read these names (pages.read), his are in the census file
WAS = {"Sandbox OS": "Sandbox OS, the tenth"}  # a seeded name, and the earlier name a store seeded before batch F holds and keeps (R-READ-3)
READ = {"basis": "I read it in", "source": "morning/ontology/03-design.md, section 3 point 8"}  # each seed verb facet's basis and source
SETS = ("types", "relations", "services", "verbs")  # the four lists a seed holds, in the order they are recorded


def standing(store, kind):
    """The standing object lines of type 'type' or 'relation', in time order: not struck, deleted, erased or superseded."""
    return [x for x in store.lines(kinds=["object"]) if (x["body"] or {}).get("type") == kind and x["mark"] not in STANDING_OUT]


def ever(store, *kinds):
    """Every name of a thing of these types (a type, a relation, a service, a verb) the workshop unit's files ever recorded, standing or not:
    a struck, superseded or deleted one is still there, read from the files because a deleted line's body is out of the index (an erased
    one's name is gone)."""
    rows = (json.loads(b) for f in store._files(UNIT) for b in _rows(_read(f)) if b.strip())
    return {r["body"].get("name") for r in rows if isinstance(r, dict) and r.get("kind") == "object"
            and isinstance(r.get("body"), dict) and r["body"].get("type") in kinds}


def seed(store, *, by):
    """Records the plain set once: each type and relation the workshop unit never recorded, as an object line (record). Returns how many
    of each it recorded."""
    return record(store, {"types": TYPES, "relations": RELATIONS, "services": SERVICES, "verbs": VERBS}, by=by)


def load(store, path, *, by):
    """His own set from a data file outside the release (card 30; the census's is morning/census/seed.json): its rows recorded as the plain
    ones are, each name once ever, then, when any line was recorded, one note naming the file, its sha256 and how many of each it added;
    a second load records nothing, the note included. Returns how many of each it recorded."""
    raw = open(path, "rb").read()
    data = json.loads(raw)
    with store.locked():
        made = record(store, {k: data.get(k) or () for k in SETS}, by=by)
        if any(made.values()):
            store.append(UNIT, "note", {"event": "seed loaded", "file": path, "sha256": hashlib.sha256(raw).hexdigest(), **made}, by=by)
        return made


def record(store, rows, *, by):
    """Records each type and relation of rows, then each service and verb, once, ever, as an object line in the workshop unit, and each
    verb's facets as facts about it, through the store's door (verbs.check judges them): a name the unit recorded before, standing or taken
    away, is never recorded again, so a second call records nothing. A verb whose service no longer stands waits. Returns how many of each
    it recorded."""
    from sandbox_os.store.verbs import FACETS, SERVICE_TYPES
    with store.locked():
        made = {k: 0 for k in SETS}
        for kind, key in (("type", "types"), ("relation", "relations")):
            have = ever(store, kind)
            for row in rows[key]:
                if row["name"] not in have:
                    store.append(UNIT, "object", {"type": kind, **row}, by=by)
                    made[key] += 1
        have = ever(store, *SERVICE_TYPES)
        for row in rows["services"]:
            if not {row["name"], WAS.get(row["name"], row["name"])} & have:  # recorded under its earlier name is recorded
                store.append(UNIT, "object", dict(row), by=by)
                made["services"] += 1
        stand = {x["body"]["name"]: x["id"] for x in store.lines(unit=UNIT, kinds=["object"])
                 if (x["body"] or {}).get("type") in SERVICE_TYPES and x["mark"] not in STANDING_OUT}
        stand = {**{new: stand[old] for new, old in WAS.items() if old in stand}, **stand}  # a verb reaches it by either name
        have = ever(store, "verb")
        for row in rows["verbs"]:
            if row["name"] in have or row["service"] not in stand:
                continue
            v = store.append(UNIT, "object", {"type": "verb", "name": row["name"]}, by=by)
            for f in (f for f in FACETS if f in row):
                value = stand[row["service"]] if f == "service" else row[f]
                store.append(UNIT, "fact", {"facet": f, "value": value, **READ}, by=by, about=v)
            made["verbs"] += 1
        return made
