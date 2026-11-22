# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The licence's checks: LICENSE's identifier line and Required Notice with no drafting mark left; the two SPDX lines at the top of every
shipped file that can carry a comment, in that file's own form (added with fix); no shipped file carrying another grant, the fonts and
the shelf's builds exempt by name; the first page's words; and the public shelf's scaffolding under the same LICENSE, byte for byte.
Each returns the list of what is wrong, empty when nothing is."""
import json, os, re

HEADER = ("SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name", "SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0")
FIRST = ("Winktank Person Licence 1.0 (LicenseRef-Winktank-Person-1.0), not an SPDX-listed licence; the full terms follow.",
         "Required Notice: Copyright 2026 Hameed, under the Winktank name.")
FORMS = {".py": ("# ", ""), ".css": ("/* ", " */"), ".js": ("/* ", " */"), ".md": ("<!-- ", " -->"), ".html": ("<!-- ", " -->")}
MARKS = ("[changed", "[new", "[choice", "[kept", "Poly" + "Form")
GRANTS = ("MIT" + " License", "Apache" + " License", "G" + "NU", "B" + "SD", "Mozilla" + " Public")  # spelled apart, so this file names none
EXEMPT = ("sandbox_os/pages/fonts/", "shelf/builds/", "shelf/apps/")
WORDS, LINES = 800, 40


def licence_file(root):
    """LICENSE opens with the identifier line and the Required Notice, and carries no drafting mark."""
    p = os.path.join(root, "LICENSE")
    if not os.path.exists(p):
        return ["no LICENSE at the root"]
    text = open(p, encoding="utf-8").read()
    out = [f"LICENSE line {i + 1} is not: {want}" for i, (want, got) in enumerate(zip(FIRST, text.splitlines()[:2] + ["", ""])) if got != want]
    return out + [f"LICENSE still carries the drafting mark {m!r}" for m in MARKS if m in text]


def _walk(tree):
    for d, dirs, fs in os.walk(tree):
        dirs[:] = sorted(x for x in dirs if x != "__pycache__" and not x.startswith("."))
        for f in sorted(fs):
            yield os.path.relpath(os.path.join(d, f), tree).replace(os.sep, "/")


def headers(tree, fix=False):
    """The files under tree that can carry a comment and do not open with the two lines; with fix, the lines are added (after a
    shebang, or as comments just inside a SKILL.md's front matter). The fonts folder is exempt by name; a file with no comment form (tables, JSON, keys) is left alone."""
    out = []
    for rel in _walk(tree):
        ext = os.path.splitext(rel)[1]
        if ext not in FORMS or "fonts" in rel.split("/")[:-1]:
            continue
        p, (a, b) = os.path.join(tree, rel), FORMS[ext]
        text = open(p, encoding="utf-8").read()
        lines = text.split("\n")
        at = 1 if lines[0].startswith("#!") else 0
        if rel.split("/")[-1] == "SKILL.md" and lines[0] == "---":  # a skill opens with its front matter (the open format), so the lines are its comments
            at, a, b = 1, "# ", ""
        want = [f"{a}{h}{b}" for h in HEADER]
        if lines[at:at + 2] == want:
            continue
        out.append(rel)
        if fix:
            with open(p, "w", encoding="utf-8") as f:
                f.write("\n".join(lines[:at] + want + lines[at:]))
    return out


def no_other_grant(root):
    """(path, phrase) for each shipped file (the package, the shelf, the root's own files) that names another licence's grant."""
    out = []
    for base in ("sandbox_os", "shelf"):
        for rel in _walk(os.path.join(root, base)) if os.path.isdir(os.path.join(root, base)) else []:
            out += _grant(root, f"{base}/{rel}")
    for name in ("LICENSE", "README.md", "BUDGETS.md", "CHANGES.md"):
        out += _grant(root, name) if os.path.exists(os.path.join(root, name)) else []
    return out


def _grant(root, rel):
    if rel.startswith(EXEMPT):
        return []
    text = open(os.path.join(root, rel), "rb").read().decode("utf-8", "replace")
    return [(rel, g) for g in GRANTS if re.search(rf"\b{re.escape(g)}\b", text)][:1]


def first_screen(text):
    """The source lines above the page's second heading, the title being its first."""
    lines = text.splitlines()
    heads = [i for i, line in enumerate(lines) if line.startswith("#")]
    return lines[:heads[1]] if len(heads) > 1 else lines


def first_page(root):
    """The first page stays under its 800 words (wc -w) with its first screen at most 40 source lines."""
    p = os.path.join(root, "README.md")
    text = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    out = [f"README.md is {len(text.split())} words, over its {WORDS}"] if len(text.split()) > WORDS else []
    return out + ([f"README.md's first screen is {len(first_screen(text))} source lines, over {LINES}"] if len(first_screen(text)) > LINES else [])


SHELF_README = """# The shelf

What the maker built with the tool and chose to share. The scaffolding (this page, `index.json`, the folder) is under the same terms as
the tool, in `LICENSE` beside this file; each build under `builds/` names its own terms in `index.json` and in its own folder.
"""


def shelf(root, make=False):
    """The public shelf's scaffolding: shelf/LICENSE the same bytes as LICENSE, a short README.md, index.json listing builds (each naming
    its own terms) and builds/; with make, whatever is absent is written."""
    s = os.path.join(root, "shelf")
    want = {"LICENSE": open(os.path.join(root, "LICENSE"), "rb").read(),
            "README.md": ("".join(f"<!-- {h} -->\n" for h in HEADER) + SHELF_README).encode(),
            "index.json": json.dumps({"builds": [], "note": "each build names its own terms in its terms field; the scaffolding is under the "
                                                            "shelf's LICENSE"}, indent=1).encode() + b"\n", "builds/.gitkeep": b""}
    for rel, data in want.items():
        if make and not os.path.exists(os.path.join(s, rel)):
            os.makedirs(os.path.dirname(os.path.join(s, rel)), exist_ok=True)
            open(os.path.join(s, rel), "wb").write(data)
    out = [f"shelf/{rel} is missing" for rel in want if not os.path.exists(os.path.join(s, rel))]
    if not out:
        out += [] if open(os.path.join(s, "LICENSE"), "rb").read() == want["LICENSE"] else ["shelf/LICENSE is not LICENSE byte for byte"]
        try:
            idx = json.load(open(os.path.join(s, "index.json")))
            out += [f"shelf/index.json: build {b.get('name', i)} names no terms" for i, b in enumerate(idx["builds"]) if not b.get("terms")]
        except (ValueError, KeyError, TypeError) as e:
            out.append(f"shelf/index.json does not read as a list of builds: {e}")
        out += [f"shelf/{rel} lacks the two header lines" for rel in headers(s) if not rel.startswith(("builds/", "apps/"))]
    return out
