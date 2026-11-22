# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The skills tree (R-CMD-40): each .agents/skills/<name>/SKILL.md, at the workshop's root and in each project, holds the six fields
only, is named as its folder, is linked (never copied) into .claude/skills/<name> beside it, and is pinned to a full commit when it
comes from outside; check() names each that is not, in the strings table's words, for doctor and the release check."""
import os, re

FIELDS = ("name", "description", "license", "compatibility", "metadata", "allowed-tools")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")


KEY = re.compile(r"""(\s*)(?:"([^"]+)"|'([^']+)'|([A-Za-z][\w-]*))\s*:(?:\s+(.*))?$""")


def _value(v):
    """A scalar with its quotes off, or an inline mapping {k: v, ...} as a dict; None for a form not read here."""
    v = v.strip()
    if not v.startswith("{"):
        return v.strip("\"'")
    if not v.endswith("}"):
        return None
    pairs = [x.partition(":") for x in v[1:-1].split(",") if x.strip()]
    return None if any(not k.strip() or not sep for k, sep, _ in pairs) else {k.strip().strip("\"'"): x.strip().strip("\"'") for k, _, x in pairs}


def front(path):
    """The front matter's top-level keys (quoted or bare), metadata's keys as a dict (indented or inline); every line it cannot read is
    kept under "_unread", so the check names it instead of passing it. None when there is no front matter."""
    text = open(path, encoding="utf-8").read()
    end = text.find("\n---", 3)
    if not text.startswith("---\n") or end < 0:
        return None
    out, cur, unread = {}, None, []
    for line in text[4:end].splitlines():
        m, item = KEY.match(line), re.match(r"\s+-(?:\s+(.*))?$", line)
        key = m and (m.group(2) or m.group(3) or m.group(4))
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if item and cur and (out.get(cur) == {} or isinstance(out.get(cur), list)):
            out[cur] = (out[cur] or []) + [(item.group(1) or "").strip()]  # an item of a list under its key
        elif cur and line[:1].isspace() and isinstance(out.get(cur), str) and not m:
            continue  # a block scalar's continuation
        elif m and not m.group(1):
            cur, v = key, _value(m.group(5) or "")
            out[cur] = {} if v == "" else v if v is not None else unread.append(line)
        elif m and isinstance(out.get(cur), dict) and _value(m.group(5) or "") is not None:
            out[cur][key] = _value(m.group(5) or "")
        else:
            unread.append(line)
    return dict(out, _unread=unread) if unread else out


def check(workshop):
    from sandbox_os.pages.words import Words
    say, out = Words("en").plain, []
    projects = os.path.join(workshop, "projects")
    for base in [workshop] + [os.path.join(projects, u) for u in (sorted(os.listdir(projects)) if os.path.isdir(projects) else [])]:
        src, dst = os.path.join(base, ".agents", "skills"), os.path.join(base, ".claude", "skills")
        names = sorted(n for n in os.listdir(src) if os.path.isdir(os.path.join(src, n))) if os.path.isdir(src) else []
        for n in names:
            f, at = os.path.join(src, n, "SKILL.md"), os.path.join(dst, n)
            fm = front(f) if os.path.exists(f) else False
            out += ([say("cli.skill.nofile", name=n)] if fm is False else [say("cli.skill.nofront", name=n)] if fm is None else
                    [say("cli.skill.unread", name=n, line=x) for x in fm.get("_unread", [])]
                    + [say("cli.skill.field", name=n, field=k) for k in fm if k not in FIELDS + ("_unread",)]
                    + ([say("cli.skill.name", name=n, other=fm.get("name") or "")] if fm.get("name") != n else []))
            meta = (fm or {}).get("metadata") if isinstance((fm or {}).get("metadata"), dict) else {}
            if (meta.get("source") or meta.get("pinned")) and not COMMIT.match(meta.get("pinned") or ""):
                out.append(say("cli.skill.pin", name=n, pin=meta.get("pinned") or ""))
            if fm is False:
                continue
            if os.path.islink(at):
                if not os.path.exists(at):
                    out.append(say("cli.skill.dangling", path=at))
                elif os.path.realpath(at) != os.path.realpath(os.path.join(src, n)):
                    out.append(say("cli.skill.elsewhere", path=at, target=os.path.realpath(at), name=n))
            else:
                out.append(say("cli.skill.copy", name=n, path=at) if os.path.exists(at) else say("cli.skill.unlinked", name=n, path=dst))
        for n in sorted(os.listdir(dst)) if os.path.isdir(dst) else []:
            at = os.path.join(dst, n)
            if n not in names and os.path.islink(at) and not os.path.exists(at):
                out.append(say("cli.skill.dangling", path=at))
    return out
