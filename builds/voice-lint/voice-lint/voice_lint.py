#!/usr/bin/env python3
"""voice-lint — the plain-language law, enforced by mechanism not memory.

Reads the banned-word list straight from soul/voice.md (one source of truth,
never a hardcoded copy that drifts) and scans a target path for it. A hit
names its file and line — the wall comes with a door.

  python3 voice_lint.py [PATH] [--dict soul/voice.md]

PATH defaults to the current directory. Exits 1 if anything trips the law,
0 if the copy is clean. Point it at a channel, a docs folder, a built site.

what it scans:
  .py                       -> string literals only (never code identifiers)
  .md .html .txt .json      -> the whole text
  .js .ts .jsx .tsx         -> the whole text (human copy lives inline there)

what it reads from voice.md:
  the "- cut:" list — single words (leverage, delve) and quoted phrases
  ("it's worth noting"). Multi-word style notes (adjective pile-ups,
  warm-up intros) are left out on purpose: a regex can't enforce them.
  Plus the programmer plural — "user(s)", "file(s)" — which voice.md bans
  by stance ("never 'users can create artifacts'").
"""
import argparse
import ast
import os
import re
import sys

TEXT_EXT = {".md", ".html", ".htm", ".txt", ".json", ".js", ".ts", ".jsx",
            ".tsx", ".css", ".yml", ".yaml"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist",
             "build", ".next", ".sandbox", "site-packages"}
PROGRAMMER_PLURAL = re.compile(r"\b[a-z]+\(s\)", re.I)


def load_banned(dict_path):
    """Pull the enforceable banned tokens from voice.md's '- cut:' block."""
    text = open(dict_path, encoding="utf-8").read()
    # the cut block runs from "cut:" to the end of that bullet (next "- keep"
    # / blank-line-then-heading). grab from 'cut:' to the first line that
    # starts a new bullet at column 0-2 beginning with "- keep" or a heading.
    m = re.search(r"cut:(.*?)(?:\n\s*-\s+keep|\n#{1,6}\s|\n\n)", text,
                  re.S | re.I)
    if not m:
        raise SystemExit("voice-lint: no '- cut:' list found in %s" % dict_path)
    body = m.group(1)
    banned = []
    for raw in body.split(","):
        entry = raw.strip().strip(".").strip()
        if not entry:
            continue
        q = re.match(r'^"(.+)"$', entry) or re.match(r"^'(.+)'$", entry)
        if q:                       # quoted phrase — keep verbatim
            banned.append(q.group(1))
        elif " " not in entry and re.match(r"^[a-z][a-z\-']*$", entry, re.I):
            banned.append(entry)    # single lexical word — keep
        # else: multi-word style note (adjective pile-ups) — not lintable
    if not banned:
        raise SystemExit("voice-lint: parsed an empty banned list from %s"
                         % dict_path)
    pattern = r"\b(" + "|".join(re.escape(w) for w in sorted(set(banned),
                                                             key=len,
                                                             reverse=True)) + r")\b"
    return re.compile(pattern, re.I), banned


def scan_text(rel, text, banned_re, out):
    for i, line in enumerate(text.splitlines(), 1):
        for mo in banned_re.finditer(line):
            out.append("%s:%d: banned word %r" % (rel, i, mo.group(0)))
        if PROGRAMMER_PLURAL.search(line):
            out.append("%s:%d: programmer plural in %r" % (rel, i, line.strip()[:60]))


def scan_py(rel, src, banned_re, out):
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        out.append("%s: does not parse (%s)" % (rel, e))
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value
            for mo in banned_re.finditer(s):
                out.append("%s:%d: banned word %r in string" % (rel, node.lineno, mo.group(0)))
            if PROGRAMMER_PLURAL.search(s):
                out.append("%s:%d: programmer plural in %r" % (rel, node.lineno, s[:60]))


def run(target, dict_path):
    banned_re, banned = load_banned(dict_path)
    dict_abs = os.path.abspath(dict_path)
    self_abs = os.path.abspath(__file__)
    out = []
    if os.path.isfile(target):
        files = [target]
        base = os.path.dirname(target) or "."
    else:
        files = []
        base = target
        for root, dirs, names in os.walk(target):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for n in names:
                files.append(os.path.join(root, n))
    for p in files:
        ap = os.path.abspath(p)
        if ap in (dict_abs, self_abs):   # never lint the law or the linter
            continue
        ext = os.path.splitext(p)[1].lower()
        rel = os.path.relpath(p, base) if not os.path.isfile(target) else p
        try:
            if ext == ".py":
                scan_py(rel, open(p, encoding="utf-8").read(), banned_re, out)
            elif ext in TEXT_EXT:
                scan_text(rel, open(p, encoding="utf-8").read(), banned_re, out)
        except (UnicodeDecodeError, IsADirectoryError, PermissionError):
            continue
    return out, banned


def main():
    ap = argparse.ArgumentParser(description="the plain-language voice lint")
    ap.add_argument("path", nargs="?", default=".", help="file or dir to scan")
    default_dict = os.environ.get(
        "VOICE_DICT",
        os.path.expanduser("~/Desktop/SandboxOS_workshop/soul/voice.md"))
    ap.add_argument("--dict", default=default_dict,
                    help="voice.md to read the banned list from")
    args = ap.parse_args()
    if not os.path.exists(args.dict):
        raise SystemExit("voice-lint: dict not found: %s "
                         "(set --dict or $VOICE_DICT)" % args.dict)
    out, banned = run(args.path, args.dict)
    if out:
        print("voice-lint: the law holds by mechanism — fix or reword:\n")
        print("\n".join(out))
        print("\n%d violation(s) · %d banned words in force" % (len(out), len(banned)))
        sys.exit(1)
    print("voice-lint: clean — %d banned words checked, nothing tripped." % len(banned))


if __name__ == "__main__":
    main()
