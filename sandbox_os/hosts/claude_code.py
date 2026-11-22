# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The Claude Code adapter: the partner's block in the workshop's CLAUDE.md, the fence and the hooks in its settings (deny rules first,
the sandbox on, then the hooks, then the five acts at ask, each step read back before the next), what overrides them read and never
changed, and the host's transcript read back as events and usage. It refuses nothing and records as the tool."""
import sys
import hashlib, json, os, re, shlex

from sandbox_os import VERSION
from sandbox_os.store import Refused, open as _open
from sandbox_os.store.line import canonical
from sandbox_os.store.log import TOOL
from sandbox_os.store.verbs import FLOOR, places
from sandbox_os.hosts.boundary import TREE, EVENTS, input_hash

NAME = "claude-code"
PROVEN = {
    "checked": "2026-10-31 by the builder (Opus): `claude --version` printed 2.1.316 (Claude Code); code.claude.com/docs/en/hooks and "
               "code.claude.com/docs/en/settings read once that night; `claude --help` read for the night's flags",
    "versions": {"2.1.316": "the installed command line: the hook events and input fields below, async and onFailure, the night's flags",
                 "2.1.309": "the transcript rows of sessions run in the desktop app's bundled host, scrubbed into "
                            "tests/fixtures/claude-code/session.jsonl; the row shapes events() and usage() read"},
    "events": {"common": ["session_id", "prompt_id", "transcript_path", "cwd", "scratchpad_dir", "permission_mode", "effort", "hook_event_name"],
               "SessionStart": ["source", "model"], "UserPromptSubmit": ["prompt"], "PreToolUse": ["tool_name", "tool_input", "tool_use_id"],
               "PermissionRequest": ["tool_name", "tool_input", "permission_suggestions"], "PermissionDenied": ["tool_name", "tool_input", "tool_use_id", "reason"],
               "PostToolUse": ["tool_name", "tool_input", "tool_response", "tool_use_id"], "PostToolUseFailure": ["tool_name", "tool_input", "tool_use_id", "error"],
               "Notification": ["message", "title", "notification_type (permission_prompt among them)"], "InstructionsLoaded": ["file_path", "memory_type", "load_reason"],
               "Stop": ["stop_hook_active", "last_assistant_message"], "SessionEnd": ["reason (clear, resume, logout, prompt_input_exit, other)"]},
    "hooks": "async: true is a field of command hooks, any event; an async hook cannot block, and under -p one still running at teardown is cancelled. "
             "onFailure is continue or block (2.1.295+), non-blocking by default; exit 2 blocks, other codes do not. PermissionDenied fires when auto "
             "mode denies a call; InstructionsLoaded fires when a CLAUDE.md or a rules file loads and cannot block. No hook receives the answer to a prompt.",
    "flags": "-p, --permission-mode dontAsk, --settings <file>, --session-id <uuid>, --disallowedTools <tools>",
    "settings": "an Edit(path) rule covers Write, MultiEdit and NotebookEdit, and a rule in those forms never matches (the host said so at a start of 10.0.0b5, 2026-11-05: one warning per fenced path); user ~/.claude/settings.json; project .claude/settings.json read from the session's primary working directory only; local "
                ".claude/settings.local.json; precedence managed, command line, local, project, user; lists merge; deny and ask apply at once, allow waits for trust",
    "unconfirmed": ["the sandbox keys and their path syntax (taken from the hosts appendix of 2026-10-30; the settings reference was not read tonight)",
                    "WebFetch(domain:[::1]) as a rule the host accepts",
                    "the desktop app's wrappers of another session's message (relayed, card 9): the forms the orchestrator named on 2026-11-02, not read in the host's documents",
                    "whether the SessionStart hook runs before CLAUDE.md's imports load, so that @read.md is this session's read and not the last one's"],
    "quoted": "an ask rule is a prefix of the command's words as written, so it cannot see inside a quoted word: git p\"us\"h, \"git\" \"push\" and "
              "git -C \"a b\" push are not Bash(git push*), and nothing asks for them; the hook reads the call as the shell does and records the act by "
              "its verb, not seen when no yes stands, and the brief says the host's own rule could not see this form (Astra's audit of batch C, finding "
              "9, measured on the fake host; how the installed host parses a quoted word is not read in its documents, so unconfirmed)",
    "turn_source": {"seen": "2.1.309, the desktop app (tests/fixtures/claude-code/session.jsonl): a person's turn has origin {kind: human}, turnOrigin human; a "
                            "peer's origin {kind: peer, from, name, handback, senderTaskId}, turnOrigin peer, isMeta true; any kind but human is read as not the maker's",
                    "unconfirmed": ["the row written before the async hook reads it (else the wrapper decides)", "any kind but human and peer", "2.1.316 writing origin"]}}
COVERAGE = ("the answer to a prompt: no hook receives it, so it is read from what ran", "what a subprocess, a hook or an MCP server did beyond its own call",
            "a session started below a project's root or outside the workshop, which reads none of the workshop's settings", "a live safety or legal claim")
NIGHT = ["claude", "-p", "{prompt}", "--permission-mode", "dontAsk", "--settings", "{settings}", "--session-id", "{session}", "--disallowedTools", "Agent"]
SYNC = ("SessionStart", "Stop", "SessionEnd")  # the session line, the turn's answers and the end are written before the host goes on
ASK = ["Bash(git push*)", "Bash(git push *)", "Bash(rm *)", "Bash(rm -r*)", "Bash(git reset --hard*)", "Bash(git clean*)", "Bash(git branch -D*)",
       "Bash(gh pr merge*)", "Bash(gh release*)", "Bash(curl -X POST*)", "Bash(curl -X PUT*)", "Bash(curl -X DELETE*)", "Bash(npm publish*)", "Bash(vercel*)",
       "Bash(fly deploy*)", "Bash(stripe *)", "Bash(shopify *)", "Bash(ssh *)", "Bash(scp *)", "Bash(rsync *)", "Bash(mail *)", "Bash(osascript *)"]
MORE = [f"Bash({' '.join(p)}{' *' if len(p) == 1 else '*'})" for p, _ in FLOOR if not any(e[5:-1].rstrip("* ") == " ".join(p) for e in ASK)]  # the
# floor's programs the twenty-two miss (the store's verbs.FLOOR: sendmail and mutt send mail, codex leaves, launchctl starts a job), beside the twenty-two the contract counts
WRAPPED = ["Bash(bash -c*)", "Bash(bash -lc*)", "Bash(sh -c*)", "Bash(zsh -*)", "Bash(env *)", "Bash(sudo *)", "Bash(nice *)", "Bash(time *)",
           "Bash(command *)", "Bash(xargs *)"]  # a shell or wrapper in front of a five act hides it from the prefixes, so each asks (Astra's audit)
CREDS = ["~/.ssh/**", "~/.aws/**", "~/.config/gh/**", "~/.gnupg/**", "~/.netrc", "**/.env", "**/.env.*"]
SHORT = ["Bash(rm -rf /*)", "Bash(rm -rf ~*)", "Bash(sudo rm *)", "Bash(mkfs*)", "Bash(dd if=*)", "Bash(:(){ :|:& };:*)", "Bash(chmod -R 777 /*)"]
LISTS = ("permissions.deny", "permissions.ask", "sandbox.filesystem.denyWrite", "sandbox.filesystem.denyRead")
BEGIN, END, LIMIT = "<!-- sandbox:begin -->", "<!-- sandbox:end -->", 12 * 1024
CARD7 = "the fence in the user's own settings is written only on the maker's yes to its card, and there is none"
RULED = ["Before one of the five acts (leaving this machine, moving money, destroying what you did not make, deploying or pushing, changing a live "
         "safety or legal claim), name which, in these words, and say that the yes is given in the host's own prompt. On a host that does not prompt, "
         "say that nothing will ask or stop it, raise a card and wait.",
         "Name a run's checks at its close, a failing one too, and what it taught and changed.",  # ruling row 11
         "The maker's words about the maker go on the maker's page with their source, strikeable; never write a guess about the maker; a rule "
         "the maker gives about how you behave is a card that waits for the maker's yes.",  # row 13; the last clause, the charter's promise 4 and
         # cards.make_rule; no pronoun for the maker, by the maker's ruling of 2026-11-16 for the public copy
         "You never write proved, accepted, or as the maker."]
OVERRIDES = (("disableAllHooks", True, "every hook is off at this scope, so nothing is observed"),
             ("permissions.defaultMode", "bypassPermissions", "the host asks nothing at this scope, and protected paths are then allowed"),
             ("sandbox.enabled", False, "the sandbox is off at this scope"), ("allowManagedHooksOnly", True, "only managed hooks run; this tool's do not"),
             ("remoteControlAtStartup", True, "remote control starts with each session, and the transcript leaves the machine while it is connected"))
CUT = True  # card 31, the maker's yes of 2026-11-11: a session is handed the cut of the charter and the book; False hands them whole, as before
HANDED = ("cache", "handed")  # where Claude Code's block imports the cut from; the fence keeps the partner's hand off cache/
DROPPED = {"charter.md": ("Why this page exists",),  # the sections a cut leaves out whole, by their "## " heading
           "book.md": ("Why this page exists", "Needs your eye", "The lines you kept", "Before and after", "What the words mean")}
ASK_RULE = "When to ask"  # the one item a dropped section keeps: the rule that starts with these words, under a heading of its own
RELAYED = re.compile(r"\A\s*(?:[^\n<]*\b(?:session|agent)s?\b[^\n<]*\n\s*)?<(?:agent-message|cross-session-message)\b[^>]*?\sfrom=(?:\"([^\"]*)\"|'([^']*)')", re.I)


def _sha(text):
    return hashlib.sha256(text.encode() if isinstance(text, str) else text).hexdigest()


def _note(root, body, clock=None):
    s = _open(root, clock=clock)
    with s.locked():
        return s.append("workshop", "note", dict(body, host=NAME), by=TOOL)


def tail_rows(path, needle=b""):
    """A transcript's rows in its last MiB that hold needle, newest first; a torn or unreadable row is skipped, an unreadable file gives none."""
    try:
        with open(path, "rb") as f:
            f.seek(max(0, os.path.getsize(path) - (1 << 20)))
            raws = [r for r in reversed(f.read().split(b"\n")) if needle in r and r.strip()]
    except (OSError, TypeError):
        return
    for raw in raws:
        try:
            yield json.loads(raw)
        except ValueError:
            continue


def _said(o):  # the words of one of this host's user rows (a string, or its text parts joined), else None
    c = (o.get("message") or {}).get("content") if o.get("type") == "user" and isinstance(o.get("message"), dict) else None
    parts = [x["text"] for x in c if isinstance(x, dict) and x.get("type") == "text" and isinstance(x.get("text"), str)] if isinstance(c, list) else []
    return c if isinstance(c, str) else "".join(parts) if parts else None


def provenance(row):
    """Where a row says its turn came from (PROVEN's turn_source): None unmarked, "" a person, else who sent it; on the row and its payload."""
    for d in (row, row.get("payload")):
        o = d.get("origin") if isinstance(d, dict) and isinstance(d.get("origin"), dict) else {}
        kind = o.get("kind") or (d.get("turnOrigin") if isinstance(d, dict) else None)
        if isinstance(kind, str) and kind:
            return "" if kind == "human" else str(o.get("from") or o.get("name") or kind)


def relayed(prompt, transcript=None, said=_said):
    """Who sent a prompt that is another session's message (card 9), else None: the marking of the newest user row whose text is the prompt
    (said reads the host's row), else the desktop app's wrapper (a line naming a session or agent, then <agent-message from=…> or
    <cross-session-message from=…>, or the prompt opening with the tag) in the prompt's first 2 KiB, so a long prompt costs the hook nothing."""
    if not isinstance(prompt, str):
        return None
    row = next((o for o in tail_rows(transcript, b"user") if isinstance(o, dict) and isinstance(said(o), str) and said(o).strip() == prompt.strip()), None) if transcript else None
    if (mark := provenance(row) if row is not None else None) is not None:
        return mark or None
    m = RELAYED.match(prompt[:2048])
    return next(g for g in m.groups() if g is not None) if m else None


def hook_command():
    """The hook runs under the tool's own interpreter (uv's, or the one this process runs on), never whatever python3 the PATH gives; the
    command's entry, which hands the event to the boundary and binds a maker's answer after it."""
    return f"{shlex.quote(sys.executable)} {shlex.quote(os.path.join(TREE, 'sandbox_os', 'command', 'hook.py'))} claude-code"


def cut(text, name):
    """Card 31: the cut of a whole page (charter.md or book.md) that a session is handed, made from the page's own structure each time it
    is needed and kept nowhere as a second copy. A paragraph is text between blank lines; a list item starts at the margin and owns the
    indented paragraphs under it. Out go the comment lines, the sections DROPPED names, every "Old wording:" paragraph and what each
    "not yet:" mark waits on (the mark stays); of a dropped section only the item whose rule starts with ASK_RULE stays, its rule without
    the review's mark, under a heading of its own. Whatever the cut does not recognise stays whole. Its first line names the whole page,
    by its hash, as its source."""
    parts = re.split(r"\n(?:[ \t]*\n)+", text.strip("\n"))
    out = [f"Cut by the tool from the whole page {name} (sha256 {hashlib.sha256(text.encode()).hexdigest()}), its source, which stands "
           "wherever the two differ; the cut leaves out what the page keeps for the maker's own reading: its history, its old wordings, "
           "what each mark waits on, and its examples: the kept lines and the before-and-after pairs."]
    section, item, asked = None, None, False
    for i, para in enumerate(parts):
        head = para.lstrip()
        indent = para[:len(para) - len(head)]
        section = para[3:].strip() if para.startswith("## ") else section
        item = item if indent else i if re.match(r"(- |\d+\. )", para) else None
        if para.startswith("<!--") or head.startswith("Old wording:"):
            continue
        if section in DROPPED.get(name, ()):
            rule = head.split(": ", 1)[-1]
            if indent and item is not None and rule.startswith(ASK_RULE):
                out += ([] if asked else [f"## {ASK_RULE}"]) + [parts[item], indent + rule]
                asked = True
            continue
        out.append(indent + "not yet" if head.startswith("not yet:") else para)
    return "\n\n".join(out)


def pages(workshop_root=None):
    """What a session is handed of the charter and the book, in that order, as (name, text): the workshop's own page (the maker edits it),
    else the one the tool ships; cut while CUT stands (card 31), whole when it is off, as before."""
    out = []
    for n in ("charter.md", "book.md"):
        p = os.path.join(workshop_root or "", n)
        t = open(p, encoding="utf-8").read() if workshop_root and os.path.exists(p) else ""
        t = t if t.rstrip("\n") else open(os.path.join(TREE, "sandbox_os", "partner", n), encoding="utf-8").read()
        out.append((n, cut(t, n) if CUT else t.rstrip("\n")))
    return out


def handed(workshop_root):
    """Card 31: the cut Claude Code's block imports, written under cache/handed/ from the workshop's own pages at each placing and at each
    session's start and end (command/hook.py), so an edit of his reaches the next session; nothing is written while CUT is off. A page
    he removed is not cut from the tool's own copy, and its cut goes (card 42). The paths written, each only when its bytes change."""
    out = []
    for n, text in pages(workshop_root) if CUT else []:
        p = os.path.join(workshop_root, *HANDED, n)
        if not os.path.exists(os.path.join(workshop_root, n)):
            if os.path.exists(p):
                os.remove(p)
            continue
        if not os.path.exists(p) or open(p, encoding="utf-8").read() != text + "\n":
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p + ".part", "w", encoding="utf-8") as f:
                f.write(text + "\n")
            os.replace(p + ".part", p)
        out.append(p)
    return out


def block(workshop_root=None, cut=None):
    """The tenth's block: the tool and its version, the read, the charter, the book and the grants by Claude Code's own import, the flow's
    open step while the onboarding is unfinished, where the present page is, and the ruled standing instructions. The charter and the book
    are imported as their cut under cache/handed/ while CUT stands (card 31) and both cut files exist (none, with no workshop), else whole,
    so no import names a missing file: an update runs this from the old version, which writes no cut. It writes nothing. cut=True or
    False makes the one form or the other, for refresh to know the tool's own block in either."""
    flow = ["@flow.md"] if workshop_root and os.path.exists(os.path.join(workshop_root, "flow.md")) else []
    cut_ = CUT and (all(os.path.exists(os.path.join(workshop_root, *HANDED, n)) for n in ("charter.md", "book.md") if workshop_root) if cut is None else cut)
    pages_ = [f"@{'/'.join(HANDED)}/{n}" if cut_ else f"@{n}" for n in ("charter.md", "book.md")]
    return "\n".join([BEGIN, f"Sandbox OS {VERSION}: the partner's standing instructions, placed by the tool. The read of the things in hand comes "
                      + ("first; the charter and the book are imported as the partner's cut, made by the tool from charter.md and book.md, which "
                         "stay whole; the maker edits those, never this block." if cut_ else
                         "first; the charter and the book are imported whole; the maker edits them, never this block."),
                      "@read.md", *pages_, "@grants.md", *flow,
                      "Each project's present page is projects/<unit>/where-it-stands.md; find asks the record through the partner's tools, never by "
                      "reading the record's files.", *[f"- {r}" for r in RULED], END])


def instruction_file(workshop_root, clock=None):
    """Places the block between the markers in <workshop>/CLAUDE.md, keeping text outside them byte for byte; a block someone edited
    since it was placed is never replaced: the difference is a note with both hashes. Returns what was placed and every finding."""
    path, cache = os.path.join(workshop_root, "CLAUDE.md"), os.path.join(workshop_root, "cache", "placed", "CLAUDE.md.sha256")
    handed(workshop_root)  # the cut first, so the block's imports never name a missing file (card 31)
    text, new = open(path, encoding="utf-8").read() if os.path.exists(path) else "", block(workshop_root)
    if len(new.encode()) > LIMIT:
        raise Refused(f"the block is {len(new.encode())} bytes, past Claude Code's 12 KiB; nothing was placed")
    last = open(cache).read().strip() if os.path.exists(cache) else None
    cur = text[text.index(BEGIN):text.index(END, text.index(BEGIN)) + len(END)] if BEGIN in text and END in text[text.find(BEGIN):] else None
    out = {"path": path, "placed": True, "sha256": _sha(new), "bytes": len(new.encode()), "findings": []}
    if cur is not None and _sha(cur) != _sha(new) and last and _sha(cur) != last:
        s = _open(workshop_root, clock=clock)
        if not any((l["body"] or {}).get("found_sha256") == _sha(cur) for l in s.lines(unit="workshop", kinds=["note"])):
            _note(workshop_root, {"event": "instruction-file-edited", "path": path, "placed_sha256": last, "found_sha256": _sha(cur),
                                  "text": "the block in CLAUDE.md was edited since the tool placed it; it is kept as edited, never replaced"}, clock=clock)
        return dict(out, placed=False, findings=["the block was edited since it was placed; kept as it is, both hashes in a note"])
    text = text.replace(cur, new) if cur is not None else text + ("\n" if text and not text.endswith("\n") else "") + new + "\n"
    with open(path + ".part", "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(path + ".part", path)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    open(cache, "w").write(_sha(new) + "\n")
    lines = text.count("\n")
    return dict(out, lines=lines, findings=[f"CLAUDE.md is {lines} lines, past the 200 lines target; nothing was cut"] if lines > 200 else [])


def refresh(workshop_root):
    """Card 31, at each session's start and end (command/hook.py): the cut written (handed), then the tool's block already in CLAUDE.md
    refreshed through instruction_file when it is the tool's own block of this version in its other form (the whole pages or the cut),
    so it imports the cut from then on. It places nothing: with no CLAUDE.md, or none holding the block, it is left as it is (card 42:
    his no to a missing block holds); a block an earlier version placed waits for an update, as the doctor's fix says; a block he
    edited is held with instruction_file's note; nothing is written when the bytes would not change. Whether the block was written."""
    handed(workshop_root)
    path, cache = os.path.join(workshop_root, "CLAUDE.md"), os.path.join(workshop_root, "cache", "placed", "CLAUDE.md.sha256")
    text = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    i = text.find(BEGIN)
    cur = text[i:text.index(END, i) + len(END)] if i >= 0 and END in text[i:] else None
    if cur is None or cur == block(workshop_root):
        return False
    if cur in (block(workshop_root, cut=True), block(workshop_root, cut=False)):
        return instruction_file(workshop_root)["placed"]
    if os.path.exists(cache) and _sha(cur) != open(cache).read().strip():
        instruction_file(workshop_root)  # his edit: held, with the note naming both hashes, once
    return False


def _record(root, read):  # read(store) on the workshop's record, read only here (Store.verbs, verbs.places), when it has one; else none
    return read(_open(root)) if os.path.exists(os.path.join(root, "home.json")) else []


def _owned(root):  # each folder only the maker writes (verbs.places, Task 10), in the fence's path form
    return [f"//{p.lstrip('/')}/**" for p in _record(root, places)]


def _fence(root):
    r, t = "//" + root.lstrip("/"), "//" + TREE.lstrip("/")
    return [f"{r}/projects/*/record/**", f"{r}/cache/**", f"{r}/.claude/**", f"{r}/grants.md", f"{r}/projects/*/grants.md", f"{r}/charter.md", f"{r}/book.md",
            f"{r}/.mcp.json", f"{r}/.codex/**", f"{r}/projects/*/.claude/settings.json", f"{r}/projects/*/.codex/**"] + \
        [f"{t}/{p}" for p in ("sandbox_os/**", "tests/**", "seeds/**", "BUDGETS.md", "LICENSE", "README.md", "CLAUDE.md", "AGENTS.md")] + _owned(root)


def ask_rules(root):
    """The asks: ASK, MORE and WRAPPED, the floor in code (ruling row 34: a struck verb narrows nothing below it), then Bash(<shape>*) for each shape of
    each declared standing verb, so a verb asks from the day it is declared and stops when struck; no entry twice."""
    out = ASK + MORE + WRAPPED
    for shape in (sh for v in _record(root, lambda s: s.verbs()) if v["declared"] for sh in v["shapes"] or []):
        e = f"Bash({' '.join(shape)}*)"
        e in out or out.append(e)
    return out


def derived(root):
    """The [key, value] pairs placed from the record rather than from code: the verbs' asks beyond the floor, each folder only the maker writes."""
    return [["permissions.ask", e] for e in ask_rules(root) if e not in ASK + MORE + WRAPPED] + \
        [x for p in _owned(root) for x in (["permissions.deny", f"Edit({p})"], ["sandbox.filesystem.denyWrite", p])]


def entries(root):
    """The four steps in their order, each a list of (dotted key, value): a list item for the list keys and hooks, else a setting."""
    fence = _fence(root)
    deny = [f"Edit({p})" for p in fence] + [f"WebFetch(domain:{h})" for h in ("127.0.0.1", "localhost", "[::1]")] + \
        [f"Read({c})" for c in CREDS] + ["Edit(~/.claude/projects/**/*.jsonl)"] + SHORT  # Edit covers Write, MultiEdit and NotebookEdit (PROVEN)
    hook = lambda e: {"matcher": "*", "hooks": [dict({"type": "command", "command": hook_command(), "timeout": 5, "onFailure": "continue"},
                                                     **({} if e in SYNC else {"async": True}))]}
    return [("deny", [("permissions.deny", e) for e in deny]),
            ("sandbox", [("sandbox.enabled", True), ("sandbox.failIfUnavailable", True), ("sandbox.allowUnsandboxedCommands", False),
                         *[("sandbox.filesystem.denyWrite", p) for p in fence + ["~/.claude/projects/**"]], *[("sandbox.filesystem.denyRead", c) for c in CREDS],
                         ("sandbox.network.allowLocalBinding", False), ("sandbox.network.allowedDomains", [])]),
            ("hooks", [(f"hooks.{e}", hook(e)) for e in EVENTS]), ("ask", [("permissions.ask", e) for e in ask_rules(root)])]


def _put_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".part", "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(path + ".part", path)


def _has(cur, key, val):
    """Whether a settings object holds an entry; (present, someone else's differing value or None)."""
    *path, last = key.split(".")
    d = cur
    for k in path:
        d = d.get(k) if isinstance(d, dict) else None
    if not isinstance(d, dict) or last not in d:
        return False, None
    if key in LISTS or key.startswith("hooks."):
        lst = d[last] if isinstance(d[last], list) else []
        return (any(h.get("command") == hook_command() for g in lst if isinstance(g, dict) for h in g.get("hooks", [])) if key.startswith("hooks.")
                else val in lst), None
    return d[last] == val, None if d[last] == val else d[last]


def _take(cur, key, val):  # one of the tool's own list entries out of a settings object; whether it was there
    d = cur
    for k in key.split(".")[:-1]:
        d = d.get(k) if isinstance(d, dict) else None
    lst = d.get(key.split(".")[-1]) if isinstance(d, dict) else None
    return isinstance(lst, list) and val in lst and lst.remove(val) is None


def _put(cur, key, val):
    *path, last = key.split(".")
    d = cur
    for k in path:
        d = d.setdefault(k, {})
    d.setdefault(last, []).append(val) if key in LISTS or key.startswith("hooks.") else d.__setitem__(last, val)


def mcp_entry(root):
    """The partner's tools as Claude Code starts them: the tool's own interpreter, the server, this workshop and no other."""
    return {"command": sys.executable, "args": ["-m", "sandbox_os", "mcp", "--workshop", root]}


def _mcp_json(root, placed, out):
    """The hooks step's last entry: sandbox-os in <workshop>/.mcp.json beside the maker's own servers, read back by hash; a file that does not
    parse, a sandbox-os entry of someone else's and one the maker removed are each a finding, and nothing is changed."""
    path, val = os.path.join(root, ".mcp.json"), mcp_entry(root)
    h = _sha(canonical(["mcpServers.sandbox-os", val]))
    out["entries"].append(h)
    try:
        cur = json.load(open(path)) if os.path.exists(path) else {}
        assert isinstance(cur, dict) and isinstance(cur.setdefault("mcpServers", {}), dict)
    except (ValueError, AssertionError):
        return out["findings"].append(f"{path} does not parse as an object of mcpServers; it is left as it is, and the partner's tools are not registered")
    have = cur["mcpServers"].get("sandbox-os")
    if have is not None:
        return have == val or out["findings"].append(f"sandbox-os in .mcp.json is {have!r}, set by someone else; kept as it is")
    if h in placed:
        return out["findings"].append("the maker removed sandbox-os from .mcp.json; it was not put back")
    cur["mcpServers"]["sandbox-os"] = val
    with open(path + ".part", "w") as f:
        json.dump(cur, f, indent=2)
    os.replace(path + ".part", path)
    if json.load(open(path)).get("mcpServers", {}).get("sandbox-os") != val:
        raise ValueError("read back without mcpServers.sandbox-os")


def settings_plan(workshop_root, user_scope=False):
    """The entries write_settings would add, in its four steps' order, one plain line each, written nowhere: the lines the welcome's
    fence card shows. They are the same at either scope; user_scope only says which file the card asks about."""
    plain = lambda k, v: (f"refused: {v}" if k == "permissions.deny" else f"asked first: {v}" if k == "permissions.ask" else
                          f"observed: every {k[6:]} event, by {hook_command()}" if k.startswith("hooks.") else f"sandbox {k[8:]}: {json.dumps(v)}")
    root = os.path.realpath(workshop_root)
    return [plain(k, v) for _, items in entries(root) for k, v in items] + \
        ([] if user_scope else [f"the partner's tools: sandbox-os in .mcp.json, {' '.join(mcp_entry(root)['args'])} under {sys.executable}"])


def write_settings(workshop_root, user_scope=False, *, path=None, yes=None, clock=None):
    """Writes the fence in four steps, deny, sandbox, hooks, ask, each read back before the next; a failed step stops the rest. It never
    removes or changes an entry of anyone else's, never puts back one the maker removed, and never writes a file that does not parse.
    The user scope is written only on the maker's yes to the welcome's fence card (`yes` names that answer, read back here) at a path
    given, or into a file a test names inside this tree; otherwise refused (card 07). A note line names every entry by hash."""
    root = os.path.realpath(workshop_root)
    a = _open(root, clock=clock).get(yes) if user_scope and yes else None
    said = bool(a and a["kind"] == "answer" and a["by"]["kind"] == "maker" and (a["body"] or {}).get("answer") == "yes")
    if user_scope and not (path and (said or os.path.realpath(path).startswith(TREE + os.sep))):
        raise Refused(f"the user settings were not written: {CARD7}")
    path = path or os.path.join(root, ".claude", "settings.json")
    cache = os.path.join(root, "cache", "placed", f"settings-{_sha(os.path.realpath(path))[:12]}.json")
    was = json.load(open(cache)) if os.path.exists(cache) else {}
    placed, ents, now = set(was.get("entries", [])), entries(root), derived(root)
    out = {"path": path, "written": False, "steps": [], "findings": [], "entries": []}
    try:
        cur = json.load(open(path)) if os.path.exists(path) else {}
        assert isinstance(cur, dict), "not a JSON object"
    except (ValueError, AssertionError, OSError) as e:
        out["findings"].append(f"the settings file does not parse ({type(e).__name__}); nothing was written, and it is left as it is")
        _note(root, {"event": "settings-written", "path": path, "written": False, "findings": out["findings"], "entries": []}, clock=clock)
        return out
    every, mine = [[k, v] for _, items in ents for k, v in items], [p for p in was.get("added", []) if p in was.get("derived", [])]
    for key, val in (p for p in mine if p not in now and p not in every):  # the tool's own, which the record no longer gives; never one the maker wrote
        if _take(cur, key, val):
            placed.discard(_sha(canonical([key, val])))
            out["findings"].append(f"{val} asked for a verb that is struck or changed; the tool's own entry was taken out" if key == "permissions.ask"
                                   else f"{val} fenced a folder no longer the maker's alone; the tool's own entry was taken out")
    for step, items in ents:
        try:
            for key, val in items:
                h, (present, theirs) = _sha(canonical([key, val])), _has(cur, key, val)
                out["entries"].append(h)
                if present:
                    continue
                if theirs is not None:
                    out["findings"].append(f"{key} is {theirs!r} in this file, set by someone else; kept, and the fence reads weaker for it")
                elif h in placed:
                    out["findings"].append(f"the maker removed {key} {val!r}; it was not put back")
                else:
                    _put(cur, key, val)
                    mine.append([key, val])  # the derived entries the tool itself added, the only ones it ever takes out
            _put_json(path, cur)
            back = json.load(open(path))
            missing = [k for k, v in items if not _has(back, k, v)[0] and _sha(canonical([k, v])) not in placed and _has(back, k, v)[1] is None]
            if missing:
                raise ValueError(f"read back without {missing[:3]}")
            step == "hooks" and not user_scope and _mcp_json(root, placed, out)
            out["steps"].append({"step": step, "entries": len(items), "read_back": True})
        except Exception as e:
            out["findings"].append(f"step {step} failed ({type(e).__name__}: {e}); the steps after it were not written")
            break
    else:
        out["written"] = True
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "w") as f:  # what the tool placed, by hash, so an entry the maker removes is never put back
            json.dump({"entries": sorted(set(out["entries"]) | placed), "derived": now, "added": [p for p in now if p in mine]}, f)
    _note(root, {"event": "settings-written", "path": path, "written": out["written"], "steps": [s["step"] for s in out["steps"]],
                 "entries": out["entries"], "findings": out["findings"], **({"yes": yes} if said else {})}, clock=clock)
    return out


def read_back(workshop_root, scopes=None):
    """Reads every scope, changing none and recording nothing, and returns what overrides the fence: the boundary's read at a session's start."""
    scopes = scopes or {"user": os.path.expanduser("~/.claude/settings.json"), "local": os.path.join(workshop_root, ".claude", "settings.local.json")}
    found = []
    for scope, path in scopes.items():
        try:
            s = json.load(open(path))
        except (OSError, ValueError):
            continue
        for key, val, what in OVERRIDES:
            d = s
            for k in key.split("."):
                d = d.get(k) if isinstance(d, dict) else None
            if d == val:
                found.append({"event": "override", "scope": scope, "path": path, "key": key, "value": val, "differs": "set where the fence says unset",
                              "what": what})  # value: the adapter's own constant the key matched, never a word of the maker's (Astra's audit)
    return found


def overrides(workshop_root, scopes=None, clock=None):
    """read_back, and one note line per override it found, for good to know."""
    found = read_back(workshop_root, scopes)
    for f in found:
        _note(workshop_root, f, clock=clock)
    return found


def rows(path):
    """(byte offset, row) for each line of a transcript; a row that does not parse comes back as None, never an exception."""
    try:
        data = open(path, "rb").read()
    except (OSError, TypeError):
        return
    off = 0
    for raw in data.split(b"\n"):
        if raw.strip():
            try:
                o = json.loads(raw)
                yield off, o if isinstance(o, dict) else None
            except ValueError:
                yield off, None
        off += len(raw) + 1


def version(path):
    """The host's version as the newest row of its transcript says, or None."""
    try:
        with open(path, "rb") as f:
            f.seek(max(0, os.path.getsize(path) - 65536))
            found = re.findall(rb'"version":\s*"([^"]+)"', f.read())
    except (OSError, TypeError):
        return None
    return found[-1].decode() if found else None


def events(since, transcripts):
    """The transcripts' calls and gaps as (kind, body): a hook line for each call and each result, a not_seen line for each row that does
    not parse, each unproven version and each renamed field. The tool's input is carried only as its hash (and, in memory, as _input)."""
    out = []
    for path in transcripts:
        sid, seen = os.path.basename(path)[:-6], set()
        for off, o in rows(path):
            if o is None:
                out.append(("not_seen", {"host": NAME, "session": sid, "what": f"a torn or unreadable row at byte {off} of the transcript", "offset": off}))
                continue
            if since and (o.get("timestamp") or "") < since:
                continue
            sid, v, m = o.get("sessionId") or sid, o.get("version"), o.get("message")
            c = {"host": NAME, "session": sid, "cwd": o.get("cwd"), "via": "transcript"}
            if v and v not in PROVEN["versions"] and v not in seen:
                seen.add(v)
                out.append(("not_seen", dict(c, what=f"Claude Code {v} is not a proven version; its rows were read as {max(PROVEN['versions'])}'s", version=v)))
            if o.get("type") not in ("user", "assistant"):
                continue
            if not isinstance(m, dict) or "content" not in m:
                out.append(("not_seen", dict(c, what=f"a {o.get('type')} row with no message.content (a renamed field?)", field="message.content")))
                continue
            for x in (x for x in (m["content"] if isinstance(m["content"], list) else []) if isinstance(x, dict)):
                if x.get("type") == "tool_use":
                    inp = x.get("input") if isinstance(x.get("input"), dict) else {}
                    out.append(("hook", dict(c, event="PreToolUse", phase="pre", tool=x.get("name"), call_id=x.get("id"), input_sha256=input_hash(inp), _input=inp)))
                elif x.get("type") == "tool_result":
                    ph = "denied" if (o.get("permissionDecision") or {}).get("decision") == "reject" else "failed" if x.get("is_error") else "post"
                    out.append(("hook", dict(c, event="PostToolUse", phase=ph, call_id=x.get("tool_use_id"))))
    return out


def usage(since, transcripts):
    """Tokens per session from the transcripts' usage fields, each message counted once; money is null unless the host reports it."""
    per = {}
    for path in transcripts:
        seen = set()
        for _, o in rows(path):
            m = (o or {}).get("message")
            if not o or o.get("type") != "assistant" or not isinstance(m, dict) or m.get("id") in seen or (since and (o.get("timestamp") or "") < since):
                continue
            seen.add(m.get("id"))
            u, s = m.get("usage") or {}, per.setdefault(o.get("sessionId"), {"host": NAME, "session": o.get("sessionId"), "model": m.get("model"),
                                                                             "tokens_in": 0, "tokens_out": 0, "cost": None, "price_table_date": None})
            s["tokens_in"] += sum(u.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
            s["tokens_out"] += u.get("output_tokens") or 0
    return list(per.values())
