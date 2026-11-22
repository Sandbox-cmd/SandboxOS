# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The move: the ninth's export read into the tenth as a transform, never as a copy.

plan() says, for each source line, the one tenth line it becomes or why it was dropped, with
the ledger, the loss list, the receipts to try and the link lines to write after; it reads the
export and writes nothing. try_receipt() tries one pointer, read-only, never past a .sandbox
folder and never over the network. reexport_rows() gives the record back in the ninth's shape
and the test's reexport_diff names every difference against the loss list. import_export() and
reexport() are the thin layer that writes and reads through a store, by its one writer."""
import collections
import datetime as _dt
import hashlib
import json
import os
import re

from sandbox_os.store import line

SEVENTH_ROOT = os.path.join(os.path.expanduser("~"), "Sandbox")  # the older workshop, under the home folder of whoever runs the move
ARCHIVE_ROOT = os.path.join(os.path.expanduser("~"), "Sandbox-seventh[archived]")
CUTOFF = "2026-07-30T11:53:00Z"  # the seventh moved out then; older paths under its root live on in the archive
EXPECTED = {"as written": 36, "through the archive": 631, "gone": 70, "fenced": 32}  # the import appendix, section 1
UNIT_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
MAKER = {"kind": "maker", "name": "maker", "model": None, "host": None}
TOOL = {"kind": "tool", "name": "sandbox-os", "model": None, "host": None}
NINTH = {"kind": "tool", "name": "ninth", "model": None, "host": "ninth"}
EXTERNAL = {"kind": "person", "name": "external", "model": None, "host": None}
UNITF, PAYF = ["project", "bench", "target"], ["diff", "artifacts", "checks", "proves"]
GONE = {"op", "id", "ts", "ink", "key", "supersedes"}
SPECIAL = {"assert": {"cls"}, "make": {"phase"}, "session": {"phase"}, "invalidate": {"ref", "of"}}

# a ninth line -> (tenth kind, fixed body fields, [(source field, body key)], [(payload field, body key)])
MAP = {
    "genesis": ("move", {"event": "genesis"}, [("note", "text")], []),
    "session": ("session", {}, [("body", "text"), ("n", "n"), ("agents", "agents")], []),
    "make/open": ("run", {}, [("body", "purpose")], []),
    "make/close": ("close", {"outcome": "closed"}, [("body", "text")], [("diff", "diff"), ("checks", "checks")]),
    "make/": ("close", {"outcome": "closed", "opened": "not recorded"}, [("intent", "intent"), ("status", "status"), ("seam", "seam")], [("artifacts", "artifacts")]),
    "assert/make-summary": ("note", {"event": "make-summary", "learned": "not recorded", "changed": "not recorded"}, [("body", "text")], []),
    "assert/ruling": ("answer", {"card": None, "answer": "words", "from": "conversation", "host": "ninth"}, [("body", "words"), ("subject", "subject")], []),
    "assert/project-state": ("note", {"event": "project-state"}, [("body", "text")], []),
    "assert/": ("note", {}, [("cls", "cls"), ("body", "text"), ("subject", "subject")], []),
    "check": ("check", {"exit": None}, [("body", "text"), ("hash", "checks_hash"), ("green", "green")], [("proves", "named")]),
    "halt": ("check", {"exit": 1}, [("failed_cmd", "command"), ("checks_hash", "checks_hash")], []),
    "ship": ("accept", {"run": None}, [("body", "text")], [("checks", "checks"), ("artifacts", "artifacts")]),
    "ratify": ("note", {"event": "ratify", "carried": "the old workshop's ratification, not carried; a line with no words of its own"}, [("hash", "hash"), ("checks_hash", "checks_hash")], []),
    "invalidate/ref": ("strike", {"form": "ref"}, [("reason", "why")], []),
    "invalidate/of": ("strike", {"form": "of"}, [("body", "why")], []),
    "board": ("note", {"event": "board", "archived": True}, [], []),
    "place": ("note", {"event": "place", "archived": True}, [], []),
    "export": ("note", {"event": "export", "archived": True}, [("body", "text")], []),
}

# the loss list: (change, the source fields it explains, whether the re-export "differs" or has it "restored", says)
LOSSES = [
    ("ink-dropped", ["ink"], "differs", "The old workshop wrote a mark into each claim when it was recorded (claimed, checked or receipted). This tool works marks out from the record each time it reads, so the stored mark is not carried."),
    ("key-hashed", ["key"], "differs", "Host keys on session and board lines are not kept. Each is replaced by its SHA-256 fingerprint, so lines from one session can still be matched."),
    ("secret-dropped", ["*row"], "differs", "A line whose words match a secret pattern was not written. The ledger keeps its row number and the pattern's name, never the words."),
    ("blocked", ["*row"], "differs", "A line matching a secret erased earlier was not written again."),
    ("id-reminted", ["id"], "restored", "Every line got a new id made from its own time. The old workshop's id stays with the line as where it came from, and the ledger pairs the two."),
    ("id-shared-split", ["id"], "restored", "In July some lines were filed again under another project with the same id. Each copy now has an id of its own."),
    ("id-given", ["id"], "restored", "The old workshop's first line (the genesis, where the record began) had no id. It was given one."),
    ("ms-added", ["ts"], "restored", "Times gained milliseconds, always .000, because the old workshop recorded whole seconds."),
    ("unit-from-bench", UNITF, "restored", "A line naming no project was placed in the project its bench names (a bench was the old workshop's word for a project's working area)."),
    ("unit-from-target", UNITF, "restored", "A line naming no project or bench was placed in the project its target names."),
    ("unit-from-none", UNITF, "restored", "A line naming no project at all was placed in the workshop's own record."),
    ("unit-from-struck-line", UNITF, "restored", "A strike was placed in the project of the line it strikes."),
    ("unit-renamed", UNITF, "restored", "A project name was lower-cased to fit this tool's folder names."),
    ("kind-mapped", ["op", "cls", "phase"], "restored", "Each of the old workshop's event types became one of this tool's kinds: a statement a note, a make a run or its close, a ship an acceptance, a halt a failed check, an invalidate a strike; boards, placements and exports became archived notes."),
    ("ruling-as-answer", ["op", "cls"], "restored", "Rulings became answers with no question card, because the old workshop never recorded the question each one answered."),
    ("recommended-pick", ["body"], "restored", "These rulings picked an option marked (Recommended). The other options offered were already lost in the old workshop; only the pick survives."),
    ("ratify-not-carried", ["op"], "restored", "The old workshop's ratifications are kept as notes. They ratify nothing in this tool; a check is run again before anything is accepted."),
    ("check-proves-nothing", ["proves"], "restored", "The old workshop's checks kept no output, so in this tool they prove nothing. The list of what each one named is kept beside it for a re-run. They are recorded as the old workshop's tool, which ran them."),
    ("payload-beside", PAYF, "restored", "Large fields (a make's file changes and checks, a ship's artifacts, a check's list) moved out of the line into a file beside it, named by the hash of its bytes."),
    ("strike-expanded", ["ref", "of"], "restored", "A strike named an id that several lines shared. It now strikes every one of them: one link line for each further copy."),
    ("supersedes-linked", ["supersedes"], "restored", "The one ruling that named the ruling it replaced is now joined to it by a link line."),
    ("supersession-in-prose", ["body"], "restored", "These lines say in words that they replace something. Nothing was linked: which line they mean is a question for a card, never a guess."),
    ("author-approved", ["origin"], "restored", "Lines the old workshop marked as human are written in the name of the writer it named, with the mark kept on the line; "
     "one that names no writer, or names the owner, is yours. In the old workshop and an older workshop before it, human meant who approved the line, not who typed it."),
    ("late-for-a-moved-unit", ["*row"], "differs", "The old workshop wrote this line after its project had moved, at an earlier sitting. It was not "
     "written, because that project's record is never rewritten; it is listed apart, with its time and kind, so a card can ask what becomes of it."),
    ("held-for-its-stream", ["*row"], "differs", "A line of a project whose sitting has not come yet was not written at this one; it is imported at its own sitting, from that day's export, under the id this ledger gives it."),
    ("prior-imported", [], "restored", "A line imported at an earlier sitting keeps the id it was given then and is not written again."),
    ("unit-folded", UNITF, "restored", "A project folded into another unit by your ruling (card 25) has its lines there; the old workshop's project name stays with each line."),
    ("about-set", [], "restored", "The line names one thing of its unit by its name, as a whole word, and is about that thing."),
    ("about-unset", [], "restored", "The line is about no thing: its words name none of its unit's things, or more than one, or a thing of another unit; the ledger says which."),
]
HELD = "held for its stream's sitting"
PENDING = ("cache", "sitting.pending")  # a sitting's snapshot while it writes, read by _resume after a stop nothing in the process saw
LATE = "late for a unit already moved"


def _n(k, word):
    """A count in words that fits one and many: 1 line, 2 lines."""
    return f"{k} {word}" + ("" if k == 1 else "s")


class Plan:
    """What the import will write, in source order; nothing here has touched a store."""
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __repr__(self):
        return f"Plan({len(self.ledger)} source lines, {len(self.units)} units)"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _ms(ts):
    return int(_dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.timezone.utc).timestamp() * 1000)


def _key(d):
    op = d.get("op")
    if op == "make":
        return "make/" + (d.get("phase") or "")
    if op == "assert":
        return "assert/" + (d["cls"] if d.get("cls") in ("make-summary", "ruling", "project-state") else "")
    return "invalidate/" + ("of" if "of" in d else "ref") if op == "invalidate" else op


def _spec(key):
    return MAP.get(key) or ("note", {"event": key}, [("body", "text")], [])


def _unit(d):
    if d.get("project"):
        u, how = d["project"], None
    elif d.get("bench"):
        u, how = d["bench"], "unit-from-bench"
    elif str(d.get("target") or "").startswith("bench:"):
        u, how = d["target"][6:], "unit-from-target"
    else:
        u, how = "workshop", "unit-from-none"
    name = re.sub(r"[^a-z0-9._-]", "-", str(u).lower())[:64]
    name = name if UNIT_RE.match(name) else ("u-" + name)[:64]
    return name, how, name != u


def _by(d):
    o = d.get("origin")
    if d.get("op") in ("check", "halt"):
        return dict(NINTH)  # the ninth's tool ran its checks; a check or a receipt is the tool's line (contract section 5)
    if o == "machine" or o == "human" and d.get("writer") not in (None, "", "owner"):  # card 55: his approval, another's words; "owner" is he
        return {"kind": "partner", "name": d.get("writer") or "partner", "model": "not recorded", "host": "ninth"}
    return dict(MAKER if o == "human" else EXTERNAL if o == "external" else NINTH)


def plan(export_dir, *, mint, secret, blocks=(), units=None, prior=(), objects=(), named_at=None):
    """Reads journal.jsonl and path-map.json and plans one tenth line or a named drop per source line. units maps a ninth unit to the
    eleventh unit its lines go into (None: every unit, as itself); a row of a unit not in it is held, with an id. prior is the ledger of
    earlier sittings: a row it holds keeps its id there, and one it wrote is not written again (batch E, Task 3). objects are the census's
    things, named in the same act and set as about (_things, Task 4). A row of a unit an earlier sitting wrote is late-for-a-moved-unit, listed
    apart in late (the review of batch E, finding 1); units with a value that is not a unit's name is refused before anything (finding 5)."""
    from sandbox_os.store import Refused
    bad = next(((k, v) for k, v in (units or {}).items() if not isinstance(v, str) or not UNIT_RE.match(v)), None)
    if bad:
        raise Refused(f"units maps each of the old workshop's projects to the unit its lines go into, a name in lower-case letters, digits, dots, dashes "
                      f"and underscores; {bad[0]!r} maps to {bad[1]!r}, so nothing was planned or written")
    path = os.path.join(export_dir, "journal.jsonl")
    with open(path, "rb") as f:
        data = f.read()
    raws = data.split(b"\n")[:-1] if data.endswith(b"\n") else data.split(b"\n")
    docs = [json.loads(r) for r in raws]
    shared = collections.Counter(d.get("id") for d in docs)
    ledger, by_old, unit_of, pri = [], collections.defaultdict(list), {}, {r["sha256"]: r for r in prior if r.get("id")}
    for row, (raw, d) in enumerate(zip(raws, docs), 1):
        r = {"row": row, "sha256": _sha(raw), "old": d.get("id")}
        name = secret(raw.decode("utf-8")) or secret(canonical(d))
        words = str(d.get("body") or d.get("note") or "")
        if name or any(b.get("source_sha256") == _sha((str(b.get("salt")) + r["sha256"]).encode())
                       or (b.get("words_sha256") and words and b["words_sha256"] == _sha((str(b.get("salt")) + words).encode())) for b in blocks):
            r.update(drop="secret pattern: " + name if name else "blocked", changes=["secret-dropped" if name else "blocked"])
        else:
            r["id"] = pri[r["sha256"]]["id"] if r["sha256"] in pri else mint(_ms(d["ts"]))
            if r["old"] is not None:
                by_old[r["old"]].append(r["id"])
            if d.get("op") != "invalidate":
                unit_of[r["id"]] = _unit(d)
        ledger.append(r)
    streams, units, links, receipts, prose, seq, open_run, words, late = units, {}, [], [], [], collections.Counter(), {}, {}, []
    moved = {x for r in prior if r.get("seq") and not r.get("held") for x in (r.get("unit"), r.get("ninth_unit")) if x}
    for r, d in zip(ledger, docs):
        if "id" not in r:
            continue
        key = _key(d)
        kind, fixed, renames, pays = _spec(key)
        body, ch = dict(fixed), ["ms-added", "id-given" if r["old"] is None else
                                 "id-shared-split" if shared[r["old"]] > 1 else "id-reminted"]
        if kind == "close" and key == "make/close":  # a make's close names the open before it in the same project, as a close does
            body["run"] = open_run.get(unit_of[r["id"]][0])
        taken = GONE | SPECIAL.get(d.get("op"), set())
        if kind == "strike":
            old = d.get("ref") if "ref" in d else d.get("of")
            first, *rest = by_old.get(old) or [None]
            body["target"] = first
            links += [{"from": r["id"], "rel": "strikes", "to": x} for x in rest]
            ch += ["strike-expanded"] if rest else []
            unit_of[r["id"]] = (unit_of[first][0] if first else "workshop", "unit-from-struck-line", False)
        sup = by_old.get(d["supersedes"]) if "supersedes" in d else None
        links += [{"from": r["id"], "rel": "supersedes", "to": sup[0]}] if sup else []
        name, how, renamed = unit_of[r["id"]]
        was = pri.get(r["sha256"]) or {}
        was = was if was and not (was.get("held") or was.get("late")) else None  # written at an earlier sitting
        if was is None and name in moved:  # the ninth wrote it after its unit moved: its own loss, never held for a sitting that has passed
            r.update(unit=name, late=True, drop=LATE, changes=["late-for-a-moved-unit"])
            late.append({"sha256": r["sha256"], "unit": name, "t": d["ts"], "kind": key.rstrip("/"),
                         "words": " ".join(str(d.get(k) or "") for k in ("body", "note")).strip()[:80]})
            continue
        if was is None and streams is not None and name not in streams:
            r.update(unit=name, held=True, drop=HELD, changes=["held-for-its-stream"])
            continue
        unit = was["unit"] if was else streams[name] if streams is not None else name
        ch += [c for c in (how, "unit-renamed" if renamed else None, "unit-folded" if unit != name else None) if c]
        body.update({dst: d[src] for src, dst in renames if src in d})
        blobs = [(dst, canonical(d[src]).encode()) for src, dst in pays if src in d]
        body.update({dst: {"payload": _sha(blob), "bytes": len(blob)} for dst, blob in blobs})
        payloads, taken = [blob for _, blob in blobs], taken | {src for src, _ in renames + pays}
        if "key" in d:
            body["key_sha256"] = _sha(str(d["key"]).encode())
        if d.get("op") == "session":
            body["event"] = d.get("phase") or "bounds not recorded"
        if key == "assert/":
            body.update({k: True for k, on in (("correction", d.get("kind") == "correction"),
                                                ("digest", d.get("writer") == "vessel:digest")) if on})
        if "supersedes" in d:
            ch += ["supersedes-linked"] if sup else []
            if not sup:
                taken.discard("supersedes")
        ninth = {k: v for k, v in d.items() if k not in taken}
        if ninth:
            body["ninth"] = ninth
        body["imported"] = {"row": r["row"], "id": r["old"], "sha256": r["sha256"]}
        text = " ".join(str(d.get(k) or "") for k in ("body", "note"))
        ch += [c for c, on in (
            ("ruling-as-answer", kind == "answer"), ("recommended-pick", kind == "answer" and "(Recommended)" in text),
            ("kind-mapped", kind not in ("answer", d.get("op"))), ("ratify-not-carried", d.get("op") == "ratify"),
            ("check-proves-nothing", d.get("op") == "check"), ("payload-beside", bool(payloads)),
            ("ink-dropped", "ink" in d), ("key-hashed", "key" in d),
            ("supersession-in-prose", bool(re.search(r"supersed", text, re.I))),
            ("author-approved", d.get("origin") == "human")) if on]
        prose += [r["row"]] if "supersession-in-prose" in ch else []
        if was:
            r.update(unit=unit, seq=was.get("seq"), kind=kind, prior=True, changes=["prior-imported"] + ch,
                     **{k: was[k] for k in ("about", "about_why", "ninth_unit") if k in was})
            continue
        seq[unit] += 1
        if kind == "run":
            open_run[name] = r["id"]
        elif kind == "close":
            open_run.pop(name, None)
        units.setdefault(unit, []).append({"kind": kind, "body": body, "by": _by(d), "t": d["ts"][:-1] + ".000Z",
                                           "id": r["id"], "lang": None, "valid_until": None, "payloads": payloads})
        r.update(unit=unit, seq=seq[unit], kind=kind, changes=ch, **({"ninth_unit": name} if unit != name else {}))
        words[r["id"]] = " ".join(str(d.get(k) or "") for k in ("body", "note", "subject"))
        if isinstance(d.get("receipt"), str):
            receipts.append({"claim": r["id"], "unit": unit, "row": r["row"], "pointer": d["receipt"], "written_at": d["ts"]})
    made = _things(units, {r["id"]: r for r in ledger if r.get("seq") and not r.get("prior")}, words, objects, named_at, mint) if objects else 0
    counts = collections.Counter(c for r in ledger for c in r["changes"])
    losses = [{"change": c, "count": counts.get(c, 0), "says": says, "filter": "changes contains " + c,
               "fields": fields, "reexport": how} for c, fields, how, says in LOSSES]
    path_map = []
    if os.path.exists(os.path.join(export_dir, "path-map.json")):
        with open(os.path.join(export_dir, "path-map.json")) as f:
            path_map = json.load(f)
    now, before = {ln["id"] for v in units.values() for ln in v}, {r["id"] for r in ledger if r.get("prior")}
    keep = [lk for lk in links if {lk["from"], lk["to"]} <= now | before and not {lk["from"], lk["to"]} <= before]
    here = {r["sha256"] for r in ledger}
    return Plan(source_path=os.path.abspath(path), source_sha256=_sha(data), ledger=ledger, losses=losses, units=units,
                links=keep, links_held=[lk for lk in links if lk not in keep], receipts=receipts, prose=prose, by_old=dict(by_old),
                path_map=path_map, prior_missing=[r for r in prior if r.get("sha256") not in here], objects=made, late=late)


def _ms_of(t):
    return _ms(t[:19] + "Z") + int(t[20:23])


def _things(units, rows, words, objects, named_at, mint):
    """Names each written unit's things in the same act: a thing's object line (and one alias fact per alias) just before the first line
    whose words name it, with that line's time, or after the unit's lines at named_at; a line naming exactly one thing of its unit, as a
    whole word, is about it, and every other line's ledger row says why not. Renumbers the ledger's seq; returns how many things."""
    hit = lambda o, w: any(re.search(r"(?<![\w.-])" + re.escape(m) + r"(?![\w-])", w) for m in o.get("match") or ())
    made = 0
    for unit, lines in units.items():
        mine, ids, out = [o for o in objects if o["unit"] == unit], {}, []

        def name(o, t):
            ids[o["name"]] = i = mint(_ms_of(t))
            out.append({"kind": "object", "by": dict(TOOL), "t": t, "id": i, "lang": None, "valid_until": None, "payloads": [], "body": {
                "type": o["type"], "name": o["name"], "ground": o.get("ground"), **({} if o["type"] == "secret" else {"named_at": named_at, "from": o.get("from")})}})  # a secret by its name only
            out.extend({"kind": "fact", "by": dict(TOOL), "t": t, "id": mint(_ms_of(t)), "about": i, "lang": None, "valid_until": None,
                        "payloads": [], "body": {"facet": "alias", "value": a, "basis": "I read it in", "source": o.get("from")}}
                       for a in o.get("aliases") or ())
        for ln in lines:
            r, w, looks = rows[ln["id"]], words.get(ln["id"], ""), ln["kind"] not in ("strike", "move")  # a strike and the genesis are never matched
            got = [o for o in mine if looks and hit(o, w)]
            for o in got:
                if o["name"] not in ids:
                    name(o, ln["t"])
            other = next((o for o in objects if looks and o["unit"] != unit and hit(o, w)), None)
            if len(got) == 1:
                ln["about"] = r["about"] = ids[got[0]["name"]]
            else:
                r["about_why"] = ("a strike acts on a line, not a thing" if ln["kind"] == "strike" else
                                  "names more than one thing of its unit: " + ", ".join(o["name"] for o in got) if got else
                                  f"names a thing of another unit: {other['name']} ({other['unit']})" if other else "names no thing of its unit")
            r["changes"].append("about-set" if len(got) == 1 else "about-unset")
            out.append(ln)
        for o in mine:
            if o["name"] not in ids:
                name(o, named_at)
        made += len(ids)
        for n, ln in enumerate(out, 1):
            if ln["id"] in rows:
                rows[ln["id"]]["seq"] = n
        units[unit] = out
    return made


def _form(p):
    if ".sandbox" in re.split(r"[/\\]", p):
        return "fenced"
    return next((f for pre, f in (("journal:", "journal"), ("sha256:", "sha256"), ("https://", "url"),
                                  ("http://", "url"), ("/", "path")) if p.startswith(pre)), "other")


def _under(p, root):
    root = root.rstrip("/")
    return p == root or p.startswith(root + "/")


def _resolve(path):
    """The path with every link followed, or None when a step would enter a .sandbox folder."""
    parts, cur, hops = [x for x in path.split("/") if x], "/", 0
    while parts:
        part = parts.pop(0)
        if part == ".sandbox" or hops > 40:
            return None
        if part in (".", ".."):
            cur = os.path.dirname(cur) if part == ".." else cur
            continue
        nxt = os.path.join(cur, part)
        if os.path.islink(nxt):
            hops, target = hops + 1, os.readlink(nxt)
            parts, cur = [x for x in target.split("/") if x] + parts, "/" if target.startswith("/") else cur
        else:
            cur = nxt
    return cur


def try_receipt(pointer, *, written_at, path_map=(), archive_root=ARCHIVE_ROOT, resolve_journal=None,
                seventh_root=SEVENTH_ROOT):
    """Tries one receipt, read-only: a path as written, then through the export's path map, then (written
    before CUTOFF under the seventh's root, by whole path segments) through the seventh's archive; a
    journal: pointer opens when its old id names imported lines; sha256:, URLs and anything else are
    read, never tried; a pointer through a .sandbox folder is never opened. Nothing is written."""
    form = _form(pointer)
    out = {"form": form, "pointer": pointer, "opened": None, "sha256": None, "opens_at": None, "via": None,
           "resolved": [], "why": "fenced: never opened" if form == "fenced" else f"a {form} pointer is read, never tried"}
    if form == "journal":
        ids = list(resolve_journal(pointer[len("journal:"):]) if resolve_journal else [])
        out.update(opened=bool(ids), resolved=ids, why="names imported lines" if ids else "names no imported line")
    if form != "path":
        return out
    tries = [(pointer, "as written")]
    tries += [(dst.rstrip("/") + pointer[len(src.rstrip("/")):], "through the path map")
              for src, dst in path_map if dst.startswith("/") and _under(pointer, src)]
    if written_at < CUTOFF and _under(pointer, seventh_root):
        tries.append((archive_root.rstrip("/") + pointer[len(seventh_root.rstrip("/")):], "through the archive"))
    fenced = False
    for place, via in tries:
        real = _resolve(place)
        fenced |= real is None
        if real and os.path.isfile(real):
            h = hashlib.sha256()
            with open(real, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            return dict(out, opened=True, sha256=h.hexdigest(), opens_at=place, via=via, why="opened " + via)
        if real and os.path.isdir(real):
            return dict(out, opened=True, opens_at=place, via=via, why=f"opened {via}; a folder, so no bytes to hash")
    return dict(out, opened=False, why="opens nowhere it was tried" + ("; a link led into a fenced folder" if fenced else ""))


def try_all(p, *, archive_root=ARCHIVE_ROOT, seventh_root=SEVENTH_ROOT):
    """Every receipt the plan lists, tried, each with its result in one word or three."""
    out = []
    for r in p.receipts:
        t = try_receipt(r["pointer"], written_at=r["written_at"], path_map=p.path_map, archive_root=archive_root,
                        resolve_journal=lambda old: p.by_old.get(old, []), seventh_root=seventh_root)
        result = {"path": t["via"] or "gone", "journal": "resolved" if t["opened"] else "dangling"}.get(t["form"], "not tried")
        out.append(dict(t, claim=r["claim"], unit=r["unit"], row=r["row"], result=result))
    return out


def _source(ln, old, sup, read):
    """One tenth line back in the ninth's shape."""
    b, k = ln["body"], ln["kind"]
    e = b.get("event")
    key = (("assert/" + e if e in ("make-summary", "project-state") else e or "assert/") if k == "note" else
           ("make/" if b.get("opened") == "not recorded" else "make/close") if k == "close" else
           ("halt" if b.get("exit") == 1 else "check") if k == "check" else "invalidate/" + b.get("form", "ref")
           if k == "strike" else {"move": "genesis", "session": "session", "run": "make/open",
                                  "answer": "assert/ruling", "accept": "ship"}[k])
    _, _, renames, pays = _spec(key)
    op, _, sub = key.partition("/")
    d = dict(b.get("ninth") or {}, op=op, ts=ln["t"][:19] + "Z")
    if b["imported"].get("id") is not None:
        d["id"] = b["imported"]["id"]
    d.update({src: b[dst] for src, dst in renames if dst in b})
    d.update({src: json.loads(read(b[dst]["payload"])) for src, dst in pays if dst in b})
    if sub and op in ("assert", "make"):
        d["cls" if op == "assert" else "phase"] = sub
    if op == "invalidate":
        d[sub] = old.get(b.get("target"))
    if op == "session" and e in ("open", "close"):
        d["phase"] = e
    if ln["id"] in sup:
        d["supersedes"] = old.get(sup[ln["id"]])
    return d


def reexport_rows(lines_by_ledger_row, payload_reader, links=()):
    """The tenth's lines given back as the ninth's rows, in ledger order; a dropped row gives nothing."""
    pairs = [(r, ln) for r, ln in lines_by_ledger_row if ln and ln.get("body")]
    old = {ln["id"]: ln["body"]["imported"]["id"] for _, ln in pairs}
    sup = {lk["from"]: lk["to"] for lk in links if lk.get("rel") == "supersedes"}
    for _, ln in pairs:
        yield _source(ln, old, sup, payload_reader)


def _grant_held(src, ln):
    """Whether a carried deletion under a grant had its authority in the source's own verified history (Astra's challenge of batch E,
    finding 13): the grant a grant line on the target's unit whose scope's services name delete, the maker's binding yes to its card
    written before the deletion, and no standing take-back, strike, deletion or end of the grant by the deletion's time."""
    b = ln.get("body") or {}
    g, t = b.get("grant"), ln.get("t") or ""
    gl = src.get(g) if isinstance(g, str) else None
    target = src.get(b.get("target")) if isinstance(b.get("target"), str) else None
    sc = ((gl or {}).get("body") or {}).get("scope") or {}
    if not (gl and gl["kind"] == "grant" and target and sc.get("unit") == target["unit"]
            and "delete" in (sc.get("services") if isinstance(sc.get("services"), list) else [])):
        return False
    if gl.get("mark") in ("erased", "deleted", "struck", "superseded") and (gl.get("mark_since") or "") <= t:
        return False
    until = (gl.get("body") or {}).get("until")
    if until and str(until) < t[:10]:
        return False
    if any((x.get("body") or {}).get("grant") == g and x["t"] <= t and x.get("mark") not in ("erased", "deleted", "struck")
           for x in src.lines(kinds=["grant_back"])):
        return False
    return any(a["t"] <= t and line.binds(a) and (a.get("body") or {}).get("answer") == "yes"
               and ((src.get((a.get("body") or {}).get("card")) or {}).get("body") or {}).get("about") == g
               for a in src.lines(kinds=["answer"]))


def rekey_lines(source_root, source_unit, into, *, taken, mint=None):
    """One unit's record from another workshop, read-only, planned for into with its ids kept: refused unless its chain verifies, its
    session files with it (Astra's challenge of batch E, finding 3); each line's id, time, kind, author (with the version it carried), body,
    language, validity and about, in chain order, flagged carried (a join or erase also internal); an id taken here (taken(id)) re-minted
    from its own time and every string equal to it in every carried body re-pointed; the payloads its bodies name, its session rows' too
    (finding 12), the unit's blocked rows and its head (batch E, Task 5; card 26); its per-session files, their record lines re-keyed the
    same way, a torn tail kept apart by its bytes and hash (finding 11), a file of another shape copied with its re-minted ids replaced,
    and what was left behind by kind (the review of batch E, finding 6); a partner's deletion under a grant carried only when the source's
    own history holds the grant (finding 13). The sitting re-points the references across its units and workshops (_sitting)."""
    from sandbox_os.store import Refused, open as open_store
    from sandbox_os.store.log import SESSION_RE, _read, _record_file, _rows
    src, mint = open_store(source_root, read_only=True), mint or line.mint_id
    v = src.verify(source_unit, sessions=True)
    sdir = os.path.join(src.unit_dir(source_unit), "sessions")
    tails = [f for f in v["failures"] if f["what"].startswith("torn tail") and os.path.dirname(os.path.join(src.root, f["file"])) == sdir]
    bad = [f for f in v["failures"] if f not in tails]
    if bad:
        f = bad[0]
        what = ", ".join(x["what"] for x in bad if (x["file"], x["row"]) == (f["file"], f["row"]))
        raise Refused(f"the source's chain does not verify ({what} at {f['file']} row {f['row']}); nothing was carried into {into}")
    got = [json.loads(b) for path in src._files(source_unit) for b in _rows(_read(path))]
    rec, sessions, files, torn = src.unit_dir(source_unit), {}, {}, []
    for name in sorted(os.listdir(sdir)) if os.path.isdir(sdir) and not os.path.islink(sdir) else []:
        path = os.path.join(sdir, name)
        if name.endswith(".jsonl") and os.path.isfile(path) and not os.path.islink(path):
            data = _read(path)
            if not (SESSION_RE.match(name[:-6]) and _record_file(data)):
                files["sessions/" + name] = data
                continue
            sessions[name[:-6]] = [json.loads(b) for b in _rows(data)]
            tail = data[data.rfind(b"\n") + 1:]
            torn += [{"file": "sessions/" + name, "bytes": len(tail), "sha256": hashlib.sha256(tail).hexdigest()}] if tail else []
    rows = [r for rs in sessions.values() for r in rs]
    for ln in got:
        if ln["kind"] == "delete" and (ln.get("body") or {}).get("grant") and ln["by"]["kind"] not in ("maker", "person") \
                and not _grant_held(src, ln):
            raise Refused(f"the source's deletion {ln['id']} names the grant {ln['body']['grant']}, and the source's own history does not "
                          f"hold it standing on the target's unit, with delete in its scope and the maker's yes before the deletion; nothing "
                          f"was carried into {into}")
    new = {ln["id"]: mint(line.id_time_ms(ln["id"])) for ln in got + rows if taken(ln["id"])}

    def swap(x):  # every string equal to a re-minted id, at any depth; an id inside prose stays as written
        return (new.get(x, x) if isinstance(x, str) else {k: swap(y) for k, y in x.items()} if isinstance(x, dict) else
                [swap(y) for y in x] if isinstance(x, list) else x)

    def carry(ln):  # the door keeps the author's version on a carried line (finding 7)
        return dict({k: swap(ln.get(k)) for k in ("id", "t", "kind", "body", "lang", "valid_until", "about")}, _carried=True, by=dict(ln["by"]),
                    **({"_internal": True} if ln["kind"] in ("join", "erase") else {}))
    payloads = {}
    for ln in got + rows:
        for sha in line.payload_refs(ln["body"]):
            payloads[sha] = src.payload_path(sha, unit=source_unit) or src.payload_path(sha)
            if not payloads[sha]:
                raise Refused(f"the source names a payload it does not keep ({sha[:12]}…); nothing was carried into {into}")
    for o, n in new.items():
        files = {k: data.replace(o.encode(), n.encode()) for k, data in files.items()}
    left = collections.Counter({"session torn tail, kept apart": len(torn)})
    for top, dirs, names in os.walk(rec):  # what stays behind, by kind; a link is never followed, a fenced folder never entered
        left["link, never followed"] += sum(1 for x in dirs if os.path.islink(os.path.join(top, x)))
        dirs[:] = [x for x in dirs if x != ".sandbox" and not os.path.islink(os.path.join(top, x))]
        for x in names:
            rel = os.path.relpath(os.path.join(top, x), rec)
            if os.path.islink(os.path.join(top, x)):
                left["link, never followed"] += 1
            elif not (re.fullmatch(r"\d{4}\.jsonl|blocked\.jsonl", rel) or rel in files or rel.startswith("sessions/") and rel[9:-6] in sessions
                      or rel.startswith("payloads/") and x in payloads):
                left["torn tail set aside" if rel.startswith("torn/") else "payload no line names" if rel.startswith("payloads/") else "other file"] += 1
    head = max(got, key=lambda ln: ln["seq"]) if got else {}
    return {"lines": [carry(ln) for ln in got], "payloads": payloads, "head": {k: head.get(k) for k in ("id", "hash", "seq")}, "rekeyed": new,
            "blocked": src.blocks(source_unit), "sessions": {k: [carry(r) for r in rs] for k, rs in sessions.items()}, "files": files,
            "left": {k: c for k, c in left.items() if c}, "torn": torn, "root": src.root, "was": {new.get(i, i): i for i in (x["id"] for x in got + rows)}}


def _ids_in(x):
    """Every string shaped as a line's id in a value, at any depth."""
    return ([x] if line.ID_RE.match(x) else []) if isinstance(x, str) else [i for y in (x.values() if isinstance(x, dict) else x) for i in _ids_in(y)] \
        if isinstance(x, (dict, list)) else []


def _sitting(store, carry, planned=()):
    """Every source a sitting carries, read and re-keyed before anything is checked, with one replacement map for the whole sitting scoped
    by source workshop (Astra's challenge of batch E, finding 2): an id re-minted in one unit is followed in every other unit carried from
    the same workshop, two workshops' equal ids stay two entries, and a carried reference that no map resolves and no line here holds is
    refused in words. Returns {into: [(root, unit, rekeyed)]}."""
    from sandbox_os.store import Refused
    ids, out, maps, seen = {ln["id"] for ln in planned if ln.get("id")}, {}, {}, set()
    for into, sources in carry.items():
        for root, unit in sources:
            if (os.path.realpath(root), unit) in seen:
                raise Refused(f"the sitting names {unit} of {root} twice; a unit's record is carried once, so nothing was written")
            seen.add((os.path.realpath(root), unit))
            g = rekey_lines(root, unit, into, taken=lambda i: i in ids or store.get(i) is not None)
            ids |= set(g["was"])
            maps.setdefault(g["root"], {}).update(g["rekeyed"])
            out.setdefault(into, []).append((root, unit, g))
    finals = collections.defaultdict(set)
    for gs in out.values():
        for _, _, g in gs:
            finals[g["root"]] |= set(g["was"])
    for into, gs in out.items():
        for root, unit, g in gs:
            more = {o: n for o, n in maps[g["root"]].items() if o not in g["rekeyed"]}  # the other units' re-mints, same workshop

            def swap(x):
                return (more.get(x, x) if isinstance(x, str) else {k: swap(y) for k, y in x.items()} if isinstance(x, dict) else
                        [swap(y) for y in x] if isinstance(x, list) else x)
            for ln in g["lines"] + [r for rs in g["sessions"].values() for r in rs] if more else ():
                ln["body"], ln["about"] = swap(ln["body"]), swap(ln.get("about"))
            for o, n in more.items():
                g["files"] = {k: data.replace(o.encode(), n.encode()) for k, data in g["files"].items()}
            for s, ln in [(None, ln) for ln in g["lines"]] + [(s, r) for s, rs in g["sessions"].items() for r in rs]:
                for x in [] if ln["kind"] in line.CHAIN_KINDS else _ids_in([ln.get("body"), ln.get("about")]):
                    if x not in finals[g["root"]] and x not in ids and store.get(x) is None:
                        raise Refused(f"nothing was written: the {ln['kind']} line for {into}" + (f" (session {s})" if s else "") +
                                      f", the source's line {ln['id']}, names {x}, and no line has the id {x!r} among this sitting's lines "
                                      f"from {root} or in this workshop; carry the unit that holds it in the same sitting")
    return out


def _carry(store, into, got, *, by, planned=()):
    """rekey's writes, planned and not yet made, from the sitting's re-keyed sources (_sitting): the payloads, the planned lines and every
    source's lines woven by (time, source, position) as the unit's part of the sitting's one sequence (_weave), the session lines file by
    file, the files copied, the sources' blocked rows, then the migration line."""
    from sandbox_os.store import Refused
    if store.lines(unit=into):
        raise Refused(f"the record is never rewritten: {into} already holds lines, so a line older than its newest would break the order "
                      "by time; carry into a unit before anything is written there")
    named = collections.Counter(k for _, _, g in got for k in list(g["files"]) + ["sessions/" + s + ".jsonl" for s in g["sessions"]])
    twice = [k for k, c in named.items() if c > 1]
    if twice:
        raise Refused(f"two sources carry {twice[0]} into {into}, and one would write over the other; nothing was written")
    ops = [("payload", into, path) for _, _, g in got for path in g["payloads"].values()]
    woven = sorted([(ln["t"], 0, k, ln, ln.get("id")) for k, ln in enumerate(planned)] +
                   [(ln["t"], n, k, ln, g["was"][ln["id"]]) for n, (_, _, g) in enumerate(got, 1) for k, ln in enumerate(g["lines"])],
                   key=lambda x: x[:3])
    ops.append(("weave", into, [w[3] for w in woven], [(w[0] or "", w[4] or "") for w in woven]))
    ops += [("lines", into, rows, name) for _, _, g in got for name, rows in g["sessions"].items()]
    ops += [("file", into, rel, data) for _, _, g in got for rel, data in g["files"].items()]
    rows = "".join(canonical(b) + "\n" for _, _, g in got for b in g["blocked"]).encode()
    ops += [("file", into, "blocked.jsonl", rows)] if rows else []
    rekeyed = {o: n for _, _, g in got for o, n in g["rekeyed"].items()}
    carried = {f"{root}:{unit}": len(g["lines"]) for root, unit, g in got}
    every = [ln for _, _, g in got for ln in g["lines"] + [r for rs in g["sessions"].values() for r in rs]]
    versions = sorted({ln["by"].get("version") for ln in every} - {None})
    sl, cf = sum(len(rs) for _, _, g in got for rs in g["sessions"].values()), [k for _, _, g in got for k in g["files"]]
    left = sum((collections.Counter(g["left"]) for _, _, g in got), collections.Counter())
    text = (f"{_n(sum(carried.values()), 'line')} of {_n(len(got), 'record')} re-keyed into {into}, woven by time with "
            f"{_n(len(planned), 'imported line')}, with {_n(sl, 'session line')} in their own files and {_n(len(cf), 'file')} of another shape "
            "copied beside; " + ("left behind: " + ", ".join(f"{c} {k}" for k, c in sorted(left.items())) if left else "nothing left behind") +
            "; ids inside prose are not re-pointed, and each carried line's author keeps the version it was written with"
            + (f" ({', '.join(versions)})" if versions else ""))
    ops.append(("lines", into, [{"kind": "migration", "by": dict(TOOL), "body": {
        "event": "rekeyed", "into": into, "asked_by": by, "rekeyed": rekeyed, "versions": versions, "carried_files": cf, "text": text,
        "from": [{"root": root, "unit": unit, "head": g["head"], "lines": len(g["lines"]), "session_lines": sum(map(len, g["sessions"].values())),
                  "left": g["left"], "rekeyed": g["rekeyed"], "torn": g["torn"]} for root, unit, g in got]}}], None))
    return ops, {"lines": len(woven), "carried": carried, "rekeyed": rekeyed}


def _bytes(x):
    if isinstance(x, (bytes, bytearray)):
        return bytes(x)
    with open(x, "rb") as f:
        return f.read()


def _weave(ops, now):
    """The sitting's units' lines as queues for one sequence (Astra's challenge of batch E, finding 1): the payloads first, then one merge
    of every unit's woven lines, the seed at the workshop's tail (it follows the workshop's own lines, at the time it runs), then the
    rest in their order. Units whose lines name one another's ids, or one same line, are judged and written interleaved by time; a unit
    whose lines share no id with another's can read no mark the others set, so its lines keep one place in the sequence (its first
    line's time) and go in one write."""
    weaves = [op for op in ops if op[0] == "weave"]
    owner, top = {ln["id"]: op[1] for op in weaves for ln in op[2] if ln.get("id")}, {op[1]: op[1] for op in weaves}

    def find(u):
        while top.setdefault(u, u) != u:
            u = top[u]
        return u
    for op in weaves:
        for ln in op[2]:
            for y in {owner.get(x, x) for x in _ids_in([ln.get("body"), ln.get("about")])} - {op[1]}:
                top[find(op[1])] = find(y)
    linked = collections.Counter(find(op[1]) for op in weaves)
    queues = [[(k if linked[find(op[1])] > 1 else op[3][0], op[1], ln) for ln, k in zip(op[2], op[3])] for op in weaves]
    if ("seed",) in ops:
        q = next((q for q in queues if q and q[0][1] == "workshop"), None)
        if q is None:
            queues.append(q := [])
        q.append(((now, ""), "workshop", None))
    return ([op for op in ops if op[0] == "payload"] + [("merge", queues)] +
            [op for op in ops if op[0] not in ("payload", "weave", "seed")])


def _dry(store, ops):
    """Every planned line and payload of a sitting through the door in one pass that writes nothing (the review of batch E, finding 5),
    each judged against those planned before it; the units' lines in one sequence by time across the units (Astra's challenge of batch E,
    finding 1), a line whose turn has come but which the door refuses waiting while the others go on (a census thing for the type a
    carried workshop brings), the seed simulated where it runs and counting only the types still absent there (finding 14). A refusal
    names the line and the store's reason, and nothing has been written. Returns the sitting's writes in the order judged."""
    from sandbox_os.store import Refused, seed
    from sandbox_os.store.line import find_secret
    ctx, out = {"batch": {}, "payloads": set(), "pending": []}, []

    def judge(unit, ln, session=None):
        n0, had = len(ctx["pending"]), ln.get("id") in ctx["batch"]
        try:
            store._append_many(unit, [ln], session=session, dry=ctx)
        except Refused as e:
            del ctx["pending"][n0:]
            None if had else ctx["batch"].pop(ln.get("id"), None)
            imp = (ln.get("body") or {}).get("imported") if isinstance(ln.get("body"), dict) else None
            what = (f"the old workshop's row {imp.get('row')} (id {imp.get('id')})" if isinstance(imp, dict) else
                    f"the source's line {ln.get('id')}" if ln.get("_carried") else "the import's own line")
            return Refused(f"nothing was written: the {ln.get('kind')} line for {unit}" + (f" (session {session})" if session else "") +
                           f", {what}, would be refused: {e}")
    for op in ops:
        if op[0] in ("payload", "file"):
            blob = _bytes(op[-1])
            hit = find_secret(blob.decode("utf-8", "replace"))
            if hit:
                raise Refused(f"nothing was written: a {'payload' if op[0] == 'payload' else 'file, ' + op[2] + ','} for {op[1]} matches the "
                              f"secret pattern '{hit}'")
            ctx["payloads"] |= {_sha(blob)} if op[0] == "payload" else set()
            out.append(op)
        elif op[0] == "lines":
            for ln in op[2]:
                e = judge(op[1], ln, op[3])
                if e:
                    raise e from None
            out.append(op)
        else:
            heads, run = [0] * len(op[1]), []
            while True:
                live, first = sorted((q[heads[n]][0], n) for n, q in enumerate(op[1]) if heads[n] < len(q)), None
                for _, n in live:
                    _, unit, ln = op[1][n][heads[n]]
                    if ln is None:  # the seed: the types it would add, only those the workshop has never recorded by now
                        have = seed.ever(store, "type") | {q["body"].get("name") for q in ctx["pending"] if q.get("kind") == "object"
                                                           and isinstance(q.get("body"), dict) and q["body"].get("type") == "type"}
                        ctx["pending"] += [{"kind": "object", "body": {"type": "type", "name": t["name"]}} for t in seed.TYPES if t["name"] not in have]
                        e = None
                    else:
                        e = judge(unit, ln)
                    if e:
                        first = first or e
                        continue
                    heads[n] += 1
                    if ln is None:
                        run.append(("seed",))
                    elif run and run[-1][0] == "lines" and run[-1][1] == unit:
                        run[-1][2].append(ln)
                    else:
                        run.append(("lines", unit, [ln], None))
                    break
                else:
                    if first:
                        raise first from None
                    break
            out += run
    return out


def _before(store, units):
    """What each unit a sitting may write holds before it writes: whether its folders were there, and each file of its record by size with
    the torn bytes after its last whole line (a write sets a torn tail aside)."""
    from sandbox_os.store.log import _tail
    snap = {}
    for u in units:
        rec, files = store.unit_dir(u), {}
        for top, dirs, names in os.walk(rec):
            dirs[:] = [x for x in dirs if not os.path.islink(os.path.join(top, x))]
            for x in names:
                p = os.path.join(top, x)
                if os.path.isfile(p) and not os.path.islink(p):
                    files[p] = (os.path.getsize(p), _tail(p)[1] if p.endswith(".jsonl") and os.path.getsize(p) else b"")
        snap[u] = (os.path.isdir(os.path.dirname(rec)), os.path.isdir(rec), files)
    return snap


def _put_back(store, snap):
    """Every unit a refused sitting wrote, as it was before: a unit that was not there removed with its folder and payloads, a file it
    added removed, a file it grew cut back to its old bytes (Astra's challenge of batch E, finding 1)."""
    import shutil
    from sandbox_os.store.log import _put
    for u, (proj, had, files) in snap.items():
        rec = store.unit_dir(u)
        if not proj or not had:
            shutil.rmtree(os.path.dirname(rec) if not proj else rec, ignore_errors=True)
            continue
        for top, dirs, names in os.walk(rec, topdown=False):
            for x in names:
                p = os.path.join(top, x)
                if p not in files and not os.path.islink(p):
                    os.remove(p)
            if top != rec and not os.listdir(top) and not any(f.startswith(top + os.sep) for f in files):
                os.rmdir(top)
        for p, (size, torn) in files.items():
            if os.path.getsize(p) != size:
                os.truncate(p, min(os.path.getsize(p), size - len(torn)))
                _put(p, torn, "ab") if torn else None
    store._known, store._fresh = {}, False


def _run(store, ops):
    """The sitting's writes, in the order the dry pass judged; the ids of each lines write. A refusal part way (a mark the dry pass does
    not derive) puts back every unit the sitting wrote, so the refusal's words, that nothing was written, are true (Astra's challenge of
    batch E, finding 1)."""
    from sandbox_os.store import Refused
    from sandbox_os.store.log import _put
    out, snap = [], _before(store, sorted({op[1] for op in ops if op[0] != "seed"} | ({"workshop"} if ("seed",) in ops else set())))
    pending, ids = os.path.join(store.root, *PENDING), sorted({ln["id"] for op in ops if op[0] == "lines" for ln in op[2] if ln.get("id")})
    end = ops[-1] if ops and ops[-1][0] == "lines" and ops[-1][2] else None  # its last line on the record says the sitting finished
    last = {"unit": end[1], "kind": end[2][-1]["kind"], "body": _sha(canonical(end[2][-1]["body"]).encode())} if end else None
    _put(pending + ".new", canonical({"ids": ids, "last": last, "units": {u: [proj, had, {p: [n, torn.hex()] for p, (n, torn) in files.items()}]
                                                                           for u, (proj, had, files) in snap.items()}}).encode(), "wb")
    os.replace(pending + ".new", pending)  # whole or absent: a kill while it is written leaves no half of it
    try:
        for op in ops:
            if op[0] == "seed":
                store.seed(by=dict(TOOL))
            elif op[0] == "payload":
                store.payload(_bytes(op[2]), unit=op[1])
            elif op[0] == "file":
                _put(os.path.join(store.unit_dir(op[1]), op[2]), op[3], "ab" if op[2] == "blocked.jsonl" else "wb")
            else:
                got = store._append_many(op[1], op[2], session=op[3])
                if all(ln.get("id") for ln in op[2]) and got != [ln["id"] for ln in op[2]]:
                    raise Refused(f"the store gave {op[1]}'s lines other ids than the ledger's; the ledger no longer pairs them")
                out.append(got)
    except BaseException as e:  # Ctrl-C and an exit too, each raised again as it came (R-READ-2); a kill or a power cut leaves PENDING (_resume)
        _put_back(store, snap)
        os.remove(pending)
        if isinstance(e, Refused):
            raise Refused(f"{e}; the sitting had begun to write, and every unit it wrote was put back as it was before, so nothing of it "
                          "stays") from None
        raise
    os.remove(pending)
    return out


def _resume(store):
    """A sitting stopped where nothing in its process runs (a kill, a closed terminal, a power cut) leaves PENDING: its snapshot of every unit
    it may write, as they were before, the ids it planned and its last line (card 34). The next import or re-keying reads it first. A
    sitting whose last line is on the record finished, so its snapshot is only dropped, never put back nor a reason to refuse. Else it
    puts those units back and removes the snapshot, so the stopped sitting runs again from the start; it is refused in words, and nothing
    put back, when what grew since holds a line the sitting would not have written (another id, and not the tool's own link, receipt,
    move, migration, thing or fact). Returns the units put back."""
    from sandbox_os.store import Refused
    path = os.path.join(store.root, *PENDING)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        got = json.load(f)
    snap = {u: (proj, had, {p: (n, bytes.fromhex(t)) for p, (n, t) in files.items()}) for u, (proj, had, files) in got["units"].items()}

    def grown(u):  # every whole line a unit's logs gained since the snapshot
        for top, _, names in os.walk(store.unit_dir(u)):
            for p in [os.path.join(top, x) for x in names if x.endswith(".jsonl") and x != "blocked.jsonl"]:
                n, torn = snap[u][2].get(p, (0, b""))
                with open(p, "rb") as f:
                    f.seek(n - len(torn))
                    yield from (json.loads(b) for b in f.read().split(b"\n") if b.startswith(b"{") and b.endswith(b"}"))
    last = got.get("last") or {}
    if last.get("unit") in snap and any(ln.get("kind") == last["kind"] and _sha(canonical(ln.get("body")).encode()) == last["body"]
                                        for ln in grown(last["unit"])):
        os.remove(path)  # the sitting wrote its last line: it finished, and only its snapshot outlived it
        return []
    for u in snap:
        other = next((ln for ln in grown(u) if ln.get("id") not in set(got["ids"]) and not ((ln.get("by") or {}).get("name") == TOOL["name"]
                      and ln.get("kind") in ("link", "receipt", "move", "migration", "object", "fact"))), None)
        if other:
            raise Refused(f"a sitting was stopped part way, and {u} holds a line written after it that is not the sitting's (the "
                          f"{other.get('kind')} line {other.get('id')}); putting the sitting back would take that line away, so nothing was "
                          f"put back or written, and no import runs until the maker says what becomes of the stopped sitting; its snapshot "
                          f"of each unit as it was before stays at {path}")
    _put_back(store, snap)
    os.remove(path)
    return sorted(snap)


def rekey(store, into, sources, *, by, planned=()):
    """Carries each source unit's record into a unit that holds no lines: the payloads first, then the planned lines (the import's, source
    0) and every source's lines woven by (time, source, position), the session files, the sources' blocked rows, then one migration line
    by the tool naming each old head, every id re-minted, the versions kept and what was left. Every write is judged in one dry pass
    first, and a refusal part way puts back what was written, so a refusal leaves nothing (Astra's challenge of batch E, finding 1). by
    names who asked. Returns the counts and the migration line's id."""
    from sandbox_os.store import gate
    with gate.replaying(), store.locked():
        _resume(store)
        got = _sitting(store, {into: sources}, planned)[into]
        ops, out = _carry(store, into, got, by=by, planned=planned)
        return dict(out, migration=_run(store, _dry(store, _weave(ops, line.iso(store.clock()))))[-1][0])


def import_export(store, export_dir, *, by, report_dir=None, archive_root=ARCHIVE_ROOT, seventh_root=SEVENTH_ROOT, units=None, prior=(),
                  objects=(), carry=None):
    """Writes the plan through the store, once into each unit, into units that hold no lines: payloads, each unit's lines,
    the links, the receipts tried, then one move line per unit closing its imported span. The import's own
    lines (links, receipts, move lines) are the tool's; `by` names who asked, on the move line. units and prior are plan's: one
    stream's sitting writes its units and holds the rest by name (batch E, Task 3); objects are the census's things, named in the same
    act after the seed, which follows the workshop's own lines when it is written now (Task 4); carry names, per eleventh unit, the
    other workshops' units re-keyed into it with its imported lines in one act (rekey, Task 5), every source read and re-keyed with one map
    for the sitting first (_sitting). Every write is planned first and judged in one dry pass, the units' lines in one sequence by time
    (_weave), so a refusal anywhere writes nothing (the review of batch E, finding 5), and a refusal the write meets part way puts back
    every unit it wrote (Astra's challenge of batch E, finding 1)."""
    from sandbox_os.store import gate
    with gate.replaying(), store.locked():
        asked_by, by, put_back = by, dict(TOOL), _resume(store)
        from sandbox_os.store.log import _put
        kw = dict(mint=line.mint_id, secret=line.find_secret, units=units, prior=prior, objects=objects, named_at=line.iso(store.clock()))
        p = plan(export_dir, **kw)
        blocks = [b for u in sorted(set(p.units) | set(store.units())) for b in store.blocks(u) or ()]
        p = plan(export_dir, blocks=blocks, **kw) if blocks else p
        carry = carry or {}
        _full(store, dict.fromkeys(list(p.units) + list(carry)))
        tries = try_all(p, archive_root=archive_root, seventh_root=seventh_root)
        order = sorted(dict.fromkeys(list(p.units) + list(carry)), key=lambda u: u != "workshop")  # the workshop first: the seed follows it
        seeding = bool(p.objects) and not store.lines(unit="workshop", kinds=["object"]) and any(u != "workshop" for u in order)
        ops, carried, rekeyed = [], {}, {}
        sitting = _sitting(store, carry, [ln for ls in p.units.values() for ln in ls])
        for unit in order:
            lines = p.units.get(unit, [])
            ops += [("seed",)] if seeding and unit != "workshop" and ("seed",) not in ops else []
            ops += [("payload", unit, b) for ln in lines for b in ln["payloads"]]
            planned = [{k: v for k, v in ln.items() if k != "payloads"} for ln in lines]
            if unit in carry:
                cops, r = _carry(store, unit, sitting[unit], by=asked_by, planned=planned)
                ops += cops
                carried[unit], rekeyed[unit] = sum(r["carried"].values()), r["rekeyed"]
            else:
                ops.append(("weave", unit, planned, [(ln.get("t") or "", ln.get("id") or "") for ln in planned]))
        where = {ln["id"]: u for u, ls in p.units.items() for ln in ls}
        ops += [("lines", where.get(lk["from"]) or (store.get(lk["from"]) or {}).get("unit"), [{"kind": "link", "by": by, "body": dict(lk)}], None)
                for lk in p.links]
        for unit in p.units:
            rs = [{"kind": "receipt", "by": by, "body": dict({k: t[k] for k in ("form", "pointer", "sha256", "opened", "opens_at", "why")},
                                                             claim=t["claim"], **({"ids": t["resolved"]} if t["resolved"] else {}))}
                  for t in tries if t["unit"] == unit]
            ops += [("lines", unit, rs, None)] if rs else []
        got = collections.Counter((t["form"], t["result"]) for t in tries)
        paths = dict({k: got[("path", k)] for k in ("as written", "through the archive", "gone")}, fenced=got[("fenced", "not tried")])
        receipts = {"expected": EXPECTED, "paths": paths, "differences": {k: paths[k] - v for k, v in EXPECTED.items()},
                    "folders": sum(1 for t in tries if t["opened"] and t["form"] == "path" and not t["sha256"]),
                    "by_form": {f"{f}: {r}": n for (f, r), n in sorted(got.items())},
                    "tries": [{k: t[k] for k in ("row", "claim", "form", "result", "sha256")} for t in tries]}
        ledger = "".join(canonical(r) + "\n" for r in p.ledger).encode()
        losses = json.dumps(p.losses, indent=1, ensure_ascii=False).encode()
        home = "workshop" if "workshop" in p.units or not p.units else next(iter(p.units))  # the report beside a unit this sitting writes
        refs = {k: {"payload": _sha(blob), "bytes": len(blob)} for k, blob in (("ledger", ledger), ("losses", losses))} if p.units else {}
        ops += [("payload", home, blob) for blob in (ledger, losses)] if p.units else []
        for unit, lines in p.units.items():  # the ninth's rows written, apart from the census's things and their alias facts (finding 10)
            mine = [ln for ln in lines if isinstance(ln["body"].get("imported"), dict)]
            things = sum(1 for ln in lines if ln["kind"] == "object")
            aliases = sum(1 for ln in lines if ln["kind"] == "fact" and ln["body"].get("facet") == "alias")
            counts = {"rows": len(p.ledger), "lines": len(mine), "things": things, "aliases": aliases,
                      "kinds": dict(collections.Counter(ln["kind"] for ln in mine))}
            text = f"{len(mine)} of the old workshop's rows written as lines" + (
                f"; {_n(things, 'thing')} named, with {_n(aliases, 'alias fact')}, from the census" if objects else "")
            late = {"late": p.late} if unit == home and p.late else {}
            text += f"; {_n(len(p.late), 'late row')} for units already moved, not written and listed apart" if late else ""
            ops.append(("lines", unit, [{"kind": "move", "by": by, "body": dict(refs, event="imported", counts=counts, asked_by=asked_by, **late,
                                                                                 source_sha256=p.source_sha256, source_path=p.source_path, text=text)}], None))
        _run(store, _dry(store, _weave(ops, line.iso(store.clock()))))
        held = sorted({r["unit"] for r in p.ledger if r.get("held")})
        if report_dir:
            for name, blob in (("ledger.jsonl", ledger), ("losses.json", losses),
                               ("receipts.json", json.dumps(receipts, indent=1, ensure_ascii=False).encode()),
                               ("held.json", json.dumps({"held": held, "late": p.late, "prior_missing": p.prior_missing, "links_held": p.links_held},
                                                        indent=1, ensure_ascii=False).encode())):
                _put(os.path.join(report_dir, name), blob, "wb")
        placed, before = sum(1 for r in p.ledger if r.get("seq") and not r.get("prior")), sum(1 for r in p.ledger if r.get("prior"))
        about = collections.Counter(c for r in p.ledger for c in r["changes"] if c.startswith("about-"))
        return {"rows": len(p.ledger), "lines": placed, "dropped": len(p.ledger) - placed - before, "units": len(p.units),
                "links": len(p.links), "receipts": paths, "source_sha256": p.source_sha256, "held": held, "late": p.late, "prior": before,
                "prior_missing": p.prior_missing, "links_held": len(p.links_held),
                **({"about": {"set": about["about-set"], "unset": about["about-unset"]}, "objects": p.objects} if objects else {}),
                **({"carried": carried, "rekeyed": rekeyed} if carry else {}), **({"put_back": put_back} if put_back else {})}


def reexport(store, dest, *, ledger):
    """Writes the record back as the ninth's journal.jsonl at dest, from the store's lines and payloads."""
    from sandbox_os.store import gate
    from sandbox_os.store.log import _put
    with gate.replaying():
        pairs = [(r, store.get(r["id"]) if r.get("id") else None) for r in ledger]
        links = [ln["body"] for ln in store.lines(kinds=["link"]) if ln.get("body")]

        def read(sha):
            with open(store.payload_path(sha), "rb") as f:
                return f.read()
        _put(dest, "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in reexport_rows(pairs, read, links=links)).encode(), "wb")
        return dest


CENSUS = ("seed.json", "streams.json", "objects.json")  # his own files for the move, in one folder outside the release (cards 30, 53, 57)
THING = ("unit", "type", "name", "ground", "aliases", "match", "from")  # what a thing of objects.json gives the import; its note stays there
BRAND = "@brand"  # the brand's unit in objects.json, named by his hand at the tool's sitting


def _full(store, units):
    """Refuses a sitting into a unit that already holds lines, since the import runs once into each unit."""
    from sandbox_os.store import Refused
    full = [u for u in units if store.lines(unit=u)]
    if full:
        raise Refused(f"the record is never rewritten: {', '.join(full)} already holds lines, so a line older than its newest would break "
                      "the order by time; carry into a unit before anything is written there, as the import runs once into each unit")


def prior(store):
    """Every earlier sitting's ledger on this record, as plan reads it: the newest row per source line (a row held at one sitting and
    written at a later one reads as written)."""
    rows = {}
    for ln in store.lines(kinds=["move"]):
        b = ln["body"] or {}
        if b.get("event") == "imported" and (b.get("ledger") or {}).get("payload"):
            with open(store.payload_path(b["ledger"]["payload"]), "rb") as f:
                rows.update((r["sha256"], r) for r in (json.loads(x) for x in f.read().decode("utf-8").splitlines() if x.strip()))
    return list(rows.values())


def things(doc, units, *, brand=None):
    """The census's things (objects.json's contents, as data) whose unit is in units, each with THING's keys only and @brand read as brand,
    in the file's order; a thing of the brand's unit selected while the brand has no name is refused, since the name is his."""
    from sandbox_os.store import Refused
    units, out = set(units), []
    for e in doc["objects"]:
        unit = brand if e["unit"] == BRAND else e["unit"]
        if e["unit"] not in units and unit not in units:
            continue
        if unit is None:
            raise Refused("the brand's unit has no name yet: it is the maker's, answered on the brand-name hand at the tool's sitting")
        out.append({k: (unit if k == "unit" else list(e[k]) if isinstance(e[k], list) else e[k]) for k in THING})
    return out


def read_census(folder):
    """His three files for the move, read from the folder the command is given: each name of CENSUS to its bytes, None for one not there."""
    out = {}
    for name in CENSUS:
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            with open(path, "rb") as f:
                out[name] = f.read()
        else:
            out[name] = None
    return out


def _stream(store, export_dir, stream, census):
    """What one stream's sitting reads (card 57): the export's journal.jsonl and his census folder's three files, census mapping each name
    of CENSUS to its bytes (None for a file that is not there). Returns the stream's units (a ninth project to its unit), the projects
    whose unit his word settles (waits), its quiet units (an old project to the dormant unit taking its lines), the census's
    things for them, every project a stream names and every one let go; or {"refuse": (a sentence's id in the table of words, its slots)}."""
    from sandbox_os.store import Refused
    if not os.path.isfile(os.path.join(export_dir, "journal.jsonl")):
        return {"refuse": ("move.refuse.export", {"export": export_dir})}
    if any(census.get(n) is None for n in CENSUS):
        return {"refuse": ("move.refuse.census", {"files": ", ".join(n for n in CENSUS if census.get(n) is None)})}
    docs = {}
    for n in CENSUS:
        try:
            docs[n] = json.loads(census[n])
        except ValueError:
            return {"refuse": ("move.refuse.unread", {"file": n})}
    named = docs["streams.json"].get("streams") or {}
    if stream not in named or not UNIT_RE.match(stream):
        return {"refuse": ("move.refuse.stream", {"stream": stream, "streams": ", ".join(docs["streams.json"].get("order") or named)})}
    mine = named[stream]
    units, quiet = {k: v for k, v in (mine.get("units") or {}).items() if v}, {d["lines_from"]: d["unit"] for d in mine.get("dormant") or ()
                                                                            if d.get("lines_from")}
    try:
        need = things(docs["objects.json"], set(units.values()) | set(quiet.values()))
    except Refused as e:
        return {"refuse": ("move.refuse.store", {"why": str(e)})}
    lack = sorted({o["type"] for o in need} - {t["body"].get("name") for t in store.types()})
    if lack:
        return {"refuse": ("move.refuse.types", {"types": ", ".join(lack)})}
    every = {k for s in named.values() for k in list(s.get("units") or {}) + [d.get("lines_from") for d in s.get("dormant") or ()]}
    return {"units": units, "waits": {k for k, v in (mine.get("units") or {}).items() if not v}, "quiet": quiet, "objects": need,
            "every": every, "gone": {e.get("project") for e in docs["streams.json"].get("let_go") or ()}}


def show(store, export_dir, stream, census):
    """What one stream's import would write into this record, planned from the export, his census folder's files (_stream) and the earlier
    sittings' ledgers, and never written (cards 34 and 52 to 57): (a sentence's id in the table of words, its slots) in three parts, what
    would come, what would not and why, what would change meaning, then what only changes shape in one row. A last row whose id begins
    move.refuse. says why none of it can be written: a file, the stream, his set's types, a unit already written, nothing to write, or
    quiet units, whose old lines the import cannot yet take in the act that writes their first lines. A sitting stopped part way is one
    row, move.show.stopped when it was this stream's (its writing puts it back first), else refused. The plan's ids are a count of its
    own, never the record's minter's, and no receipt is tried."""
    from sandbox_os.store import Refused
    got = _stream(store, export_dir, stream, census)
    if "refuse" in got:
        return [got["refuse"]]
    units, quiet, pending = got["units"], got["quiet"], os.path.join(store.root, *PENDING)
    if os.path.exists(pending):
        with open(pending, encoding="utf-8") as f:
            was = sorted(json.load(f)["units"])
        return [("move.show.stopped" if set(was) <= set(units.values()) | {"workshop"} else "move.refuse.stopped",
                 {"units": ", ".join(was), "path": pending})]
    try:
        _full(store, sorted(set(units.values()) | set(quiet.values())))
    except Refused as e:
        moved = [u for u in sorted(set(units.values())) if store.lines(unit=u, kinds=["move"])]
        return [("move.refuse.moved", {"stream": stream, "units": ", ".join(moved)}) if moved else ("move.refuse.store", {"why": str(e)})]
    count = iter(range(1, 1 << 62))
    p = plan(export_dir, mint=lambda ms=None: f"{next(count):026d}", secret=line.find_secret, units=dict(units, **quiet), prior=prior(store),
             blocks=[b for u in store.units() for b in store.blocks(u) or ()], objects=got["objects"], named_at=line.iso(store.clock()))
    rows = [r for r in p.ledger if r.get("seq") and not r.get("prior") and r["unit"] not in quiet.values()]
    held, c = collections.Counter(r["unit"] for r in p.ledger if r.get("held")), collections.Counter(x for r in rows for x in r["changes"])
    out = [("move.show.head", {"stream": stream, "rows": f"{len(p.ledger):,}", "export": export_dir}), ("move.show.come", {})]
    out += ([("move.show.unit", {"n": k, "unit": u}) for u, k in sorted(collections.Counter(r["unit"] for r in rows).items())]
            or [("move.show.none", {})])
    folded = collections.Counter((r["ninth_unit"], r["unit"]) for r in rows if r.get("ninth_unit"))
    out += [("move.show.folded", {"n": sum(folded.values()),
                                  "projects": ", ".join(f"{a} ({k:,}) into {b}" for (a, b), k in sorted(folded.items()))})] if folded else []
    out += [("move.show.things", {"k": f"{p.objects:,}"})] if p.objects and rows else []
    out.append(("move.show.not", {}))
    q = sum(1 for r in p.ledger if r.get("seq") and r["unit"] in quiet.values())
    out += [("move.show.quiet", {"n": q, "units": ", ".join(sorted(quiet.values()))})] if quiet else []
    for key, us in (("waits", [u for u in held if u in got["waits"]]), ("held", [u for u in held if u in got["every"] - got["waits"]]),
                    ("gone", [u for u in held if u in got["gone"]]), ("nostream", [u for u in held if u not in got["every"] | got["gone"]])):
        out += [("move.show." + key, {"n": sum(held[u] for u in us), "units": ", ".join(sorted(us))})] if us else []
    for key, k in (("before", sum(1 for r in p.ledger if r.get("prior"))), ("late", len(p.late)),
                   ("receipts", sum(1 for t in p.receipts if t["unit"] not in quiet.values())),
                   ("secret", sum(1 for r in p.ledger if r.get("drop") and not (r.get("held") or r.get("late"))))):
        out += [("move.show." + key, {"n": k})] if k else []
    if quiet or not rows:  # nothing of it can be written today
        return out + [("move.refuse.quiet", {"units": ", ".join(sorted(quiet.values()))}) if quiet else ("move.refuse.nothing", {"stream": stream})]
    by, approved = {ln["id"]: ln["by"]["kind"] for ls in p.units.values() for ln in ls}, [r["id"] for r in rows if "author-approved" in r["changes"]]
    out.append(("move.show.meaning", {}))
    for key, k in (("approved", sum(1 for i in approved if by.get(i) != "maker")), ("yours", sum(1 for i in approved if by.get(i) == "maker")),
                   ("rulings", c["ruling-as-answer"]), ("picked", c["recommended-pick"]), ("checks", c["check-proves-nothing"]),
                   ("ratify", c["ratify-not-carried"]), ("prose", c["supersession-in-prose"])):
        out += [("move.show." + key, {"n": k})] if k else []
    return out + [("move.show.shape", {"ids": f"{c['id-reminted'] + c['id-shared-split'] + c['id-given']:,}", "times": f"{c['ms-added']:,}",
                                       "kinds": f"{c['kind-mapped']:,}", "beside": f"{c['payload-beside']:,}",
                                       "units": f"{sum(c[k] for k in c if k.startswith('unit-from-')):,}"}), ("move.show.end", {})]


def keep(store, stream, text):
    """The showing's words as a plain file in the workshop's own folder, move/STREAM.txt, outside the record (card 56); returns its path."""
    from sandbox_os.store.log import _put
    path = os.path.join(store.root, "move", stream + ".txt")
    _put(path, text.encode("utf-8"), "wb")
    return path


def write(store, export_dir, stream, census, *, by):
    """Writes one stream's lines as show() planned them, once, through import_export: its units, the census's things for them and the
    earlier sittings' ledgers, read after a stopped sitting is put back (_resume); by names who asked. Refused, nothing written, wherever
    show() refuses before it plans, and for quiet units, whose old lines come only in the act that writes their own first lines, which the
    import cannot do yet; a stream already written is refused as never rewritten, but one whose stopped sitting turns out to have finished
    (a kill after its last write) is not written again and returns as written. Returns the ids of its units' move lines."""
    from sandbox_os.store import Refused, gate
    got = _stream(store, export_dir, stream, census)
    if "refuse" in got:
        raise Refused(f"nothing was written: the stream {stream} is refused before anything is planned ({got['refuse'][0]})")
    if got["quiet"]:
        raise Refused(f"nothing was written: {', '.join(sorted(got['quiet'].values()))} take their old lines only in the act that writes their "
                      "own first lines as quiet units, and the import cannot do that yet, so no part of this stream is written")
    units, pending, stopped = sorted(set(got["units"].values())), os.path.join(store.root, *PENDING), False
    with gate.replaying(), store.locked():
        if os.path.exists(pending):  # this stream's own stopped sitting, which _resume puts back, or finds finished
            with open(pending, encoding="utf-8") as f:
                stopped = set(json.load(f)["units"]) <= set(units) | {"workshop"}
        _resume(store)
        done = [ln["id"] for u in units for ln in store.lines(unit=u, kinds=["move"])]
        if done and not stopped:
            raise Refused(f"nothing was written: the record is never rewritten, and {', '.join(units)} took this stream's lines at an earlier sitting")
        if not done:  # else its stopped sitting had finished (a kill after its last write): every line is in, the note of the yes still to come
            import_export(store, export_dir, by=by, units=got["units"], prior=prior(store), objects=got["objects"])
        return [ln["id"] for u in units for ln in store.lines(unit=u, kinds=["move"])]
