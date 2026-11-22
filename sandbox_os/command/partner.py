# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""Places the partner's standing instructions in a workshop: the charter and the book copied in when absent and never overwritten (an
edit is the maker's, recorded with both wordings), the two skills placed the same way and linked, grants.md projected from the grant lines, and the host's instruction block."""
import hashlib, os, shutil

from sandbox_os.store import open as _open
from sandbox_os.command import TOOL, DOWN, cards, say
from sandbox_os.hosts import claude_code, codex
from sandbox_os.hosts.boundary import TREE, standing_grants
from sandbox_os.pages import read, write

TEMPLATES = os.path.join(TREE, "sandbox_os", "partner")
ADAPTERS = {a.NAME: a for a in (claude_code, codex)}  # each host's instruction file: CLAUDE.md, AGENTS.md
RULES_MAX = 20
SKILLS = ("product-pass", "challenger")  # the methods the partner loads at the pauses (design section 8 point 6), placed as the open format's pages


def _skills(s):
    """Each of SKILLS copied to .agents/skills/<name>/SKILL.md when absent (never over his edit) and linked, relative, from .claude/skills.
    A deletion is his edit too: a skill placed before and gone is a note by the tool, `event: skill removed` with its name, once, its own
    link taken with it; it is placed again only when the tool's own copy is a new version (its metadata's version, as cache/placed keeps it)."""
    from sandbox_os.command.skills import front
    for n in SKILLS:
        dest, at, src = os.path.join(s.root, ".agents", "skills", n, "SKILL.md"), os.path.join(s.root, ".claude", "skills", n), os.path.join(TEMPLATES, "skills", n, "SKILL.md")
        v, kept = ((front(src) or {}).get("metadata") or {}).get("version") or hashlib.sha256(open(src, "rb").read()).hexdigest(), os.path.join(s.root, "cache", "placed", "skills", n)
        was = open(kept, encoding="utf-8").read().strip() if os.path.exists(kept) else None
        said = any((l["body"] or {}).get("event") == "skill removed" and l["body"].get("skill") == n and l["body"].get("version") == v
                   for l in s.lines(unit="workshop", kinds=["note"]) if l["mark"] not in DOWN)  # the record's word stands when the cache is gone
        if not os.path.exists(dest) and (was == v or said):
            if not said:
                with s.locked():
                    s.append("workshop", "note", {"event": "skill removed", "skill": n, "version": v, "text": say("note.skill.removed", skill=n)}, by=TOOL)
            if os.path.islink(at) and not os.path.exists(at) and os.readlink(at) == os.path.join("..", "..", ".agents", "skills", n):
                os.remove(at)  # the tool's own link, which now points at nothing
            continue
        if not os.path.exists(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(src, dest)
            was = None
        if was is None:  # the version placed, kept so a deletion can be told from a skill never placed
            os.makedirs(os.path.dirname(kept), exist_ok=True)
            open(kept, "w", encoding="utf-8").write(v + "\n")
        if not os.path.lexists(at):
            os.makedirs(os.path.dirname(at), exist_ok=True)
            os.symlink(os.path.join("..", "..", ".agents", "skills", n), at)


def _said_yes(store, unit=None):
    """Each rule and each note about the maker that stands on the maker's yes, with its card: the lines of what you said yes to. The notes
    about him come from his page alone (read.you_lines, oldest first), so a note he struck or erased leaves grants.md (design section 6)."""
    cards = {(c["body"] or {}).get("about"): c["id"] for c in store.lines(unit=unit, kinds=["card"])}
    out = [(l["body"]["text"], l["body"].get("card")) for l in store.lines(unit=unit, kinds=["rule"]) if l["mark"] not in DOWN]
    out += [(l["body"]["text"], cards.get(l["id"])) for l in reversed(read.you_lines(store))
            if l["kind"] == "about_you" and (unit is None or l["unit"] == unit) and isinstance((l["body"] or {}).get("text"), str)]
    return out


def grants_text(store, unit=None):
    """grants.md as projected from the record, newest first; the same record always projects the same bytes."""
    gs = sorted({g["id"]: g for u in ([unit] if unit else store.units()) for g in standing_grants(store, u)}.values(), key=lambda g: g["t"], reverse=True)
    lines = ["# What the partner may do", "", say("grants.md.intro"), "", "## Grants that stand, newest first", ""]
    for g in gs:
        b = g["body"]
        sc = b.get("scope") or {}
        lines.append(say("grants.md.line", sentence=b["sentence"], day=g["t"][:10], reading=b["reading"], unit=str(sc.get("unit")), paths=", ".join(sc.get("paths") or []) or "none",
                         services=", ".join(sc.get("services") or []) or "none", until=b.get("until") or "you take it back", take_back=str(b.get("take_back")), id=g["id"]))
    yes = _said_yes(store, unit)
    lines += ["" if gs else "- none yet", "", "## What you said yes to", ""] + [f"- {t} (card {c})" for t, c in yes[-RULES_MAX:]] + ([] if yes else ["- nothing yet"])
    return "\n".join(lines) + "\n"


def _write(path, text):
    if not os.path.exists(path) or open(path, encoding="utf-8").read() != text:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".part", "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(path + ".part", path)


def gone(s):
    """Card 42: each placed file that is missing (the charter, the book, the block in CLAUDE.md), with the newest card that asked about it, his answer
    that binds, and where it stands: "ask" (never asked, or his yes was acted on and it is gone again), "wait", "yes" (place it) or "no" (his removal)."""
    p, out = os.path.join(s.root, "CLAUDE.md"), {}
    notes = [l["body"].get("yes") for l in s.lines(unit="workshop", kinds=["note"]) if (l["body"] or {}).get("event") == "placed-again"]
    block = claude_code.BEGIN in (open(p, encoding="utf-8").read() if os.path.exists(p) else "")
    for n in [n for n in ("charter.md", "book.md") if not os.path.exists(os.path.join(s.root, n))] + ["CLAUDE.md"] * (not block):
        c = max(map(s.get, cards._on(s, "workshop", f"placed:{n}")), key=lambda c: c["body"].get("version", 1), default=None)
        d = c and cards.decision(s, c["id"])
        a = d and d["body"].get("answer")
        out[n] = (c, d, "ask" if not c or (a == "yes" and d["id"] in notes) else a if a in ("yes", "no") else "wait")
    return out


def put(root, name):  # the tool's own copy of a placed file, and under cache/placed/ what was placed, so a later start reads no edit of his into it
    os.makedirs(os.path.join(root, "cache", "placed"), exist_ok=True)
    [shutil.copyfile(os.path.join(TEMPLATES, name), os.path.join(root, d, name)) for d in ("", os.path.join("cache", "placed"))]


def place(workshop_root, *, host="claude-code", home=None, clock=None):
    """At each start: the charter and the book into the workshop when absent, an edit since the last start recorded with both wordings and
    both hashes, the skills placed and linked when absent, grants.md projected at the root and per unit, and the host's instruction block placed (Codex's chain measured with the
    global file under `home` when one is given), every line on `clock` when one is given (the flow's), else the wall clock. Returns what it did."""
    s, out = _open(workshop_root, clock=clock), {"findings": []}
    for name in [n for n in ("charter.md", "book.md") if not gone(s).get(n, [None])[0]]:  # card 42: a missing one he was asked about is his to answer
        dest, seen = os.path.join(s.root, name), os.path.join(s.root, "cache", "placed", name)
        if not os.path.exists(dest):
            shutil.copyfile(os.path.join(TEMPLATES, name), dest)
        cur, old = open(dest, "rb").read(), open(seen, "rb").read() if os.path.exists(seen) else None
        if old is not None and cur != old:
            with s.locked():
                s.append("workshop", "note", {"event": f"{name[:-3]}-edited", "path": dest, "old": {"payload": s.payload(old, unit="workshop")},
                                              "new": {"payload": s.payload(cur, unit="workshop")}, "old_sha256": hashlib.sha256(old).hexdigest(),
                                              "new_sha256": hashlib.sha256(cur).hexdigest(), "text": f"{name} was edited by hand; both wordings are kept"}, by=TOOL)
            out["findings"].append(f"{name} was edited since the last start; both wordings are kept")
        os.makedirs(os.path.dirname(seen), exist_ok=True)
        shutil.copyfile(dest, seen)
    _skills(s)
    for u in s.units():
        _write(os.path.join(s.root, "projects", u, "grants.md"), grants_text(s, u))
    _write(os.path.join(s.root, "grants.md"), grants_text(s))
    if len(_said_yes(s)) > RULES_MAX and not [c for c in s.lines(kinds=["card"]) if (c["body"] or {}).get("purpose") == "rules-over-twenty"]:
        cards.raise_(s, "workshop", dict(cards.five("card.rules", lang=cards.language(s.root)), purpose="rules-over-twenty"), by=TOOL)
    if not os.path.exists(os.path.join(s.root, "read.md")):  # so the block's import never names a missing file; the hook writes it again at each start
        write.write_read(s, "workshop", clock=clock)
    out["instructions"] = codex.instruction_file(s.root, home, clock=clock) if host == codex.NAME else ADAPTERS[host].instruction_file(s.root, clock=clock)
    return out
