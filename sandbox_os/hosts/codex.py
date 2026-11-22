# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The Codex adapter: the partner's block in the workshop's AGENTS.md (the charter and the book carried inline as their cut: Codex reads no imports), the fence
in the workshop's .codex/ (the forbidden short list and the profile's filesystem first, then the sandbox, the hooks, the five acts at prompt and
the partner's tools, each step read back by hash before the next), the user scope only on the maker's yes, what overrides the fence read and
never changed, and the rollout read back as events and usage. It refuses nothing, trusts nothing of its own, and records as the tool."""
import hashlib, json, os, re, shlex, sys, tomllib

from sandbox_os import VERSION
from sandbox_os.store import Refused, open as _open
from sandbox_os.store.line import canonical
from sandbox_os.store.log import TOOL
from sandbox_os.store.verbs import places
from sandbox_os.hosts.boundary import TREE, FIVE, input_hash, locate
from sandbox_os.hosts.claude_code import ASK, MORE, BEGIN, END, RULED, rows, relayed as _relayed
from sandbox_os.hosts import claude_code  # the cut and its switch, read at each call (card 31)

NAME = "codex"
PROVEN = {  # facts and dates; the receipt and the fixtures say the rest
    "checked": "2026-11-01, builder A (Opus): codex --version = codex-cli 0.164.0; the vendor's hooks, config, rules and AGENTS.md pages read by Fable that day (design section 2)",
    "versions": {"0.164.0": "installed; hook fields as documented, none captured from a live hook"},
    "events": {"common": ["session_id", "transcript_path", "cwd", "hook_event_name", "model", "turn_id"], "SessionStart": ["source"], "UserPromptSubmit": ["prompt"],
               "PreToolUse": ["tool_name", "tool_use_id", "tool_input.command"], "PermissionRequest": ["tool_name", "tool_use_id", "tool_input"], "PostToolUse":
               ["tool_name", "tool_use_id", "tool_input", "tool_response"], "Stop": ["stop_hook_active", "last_assistant_message"], "SessionEnd": ["reason"]},
    "normalise": "apply_patch an Edit naming every path, the strictest class the call's; beyond the design's 'only this', a list command read as its script",
    "rollout": "session_meta (cli_version), turn_context, response_item, event_msg (token_count): the builder's own knowledge; no real rollout read (fixtures.md)",
    "real_run": {"date": "2026-11-01", "receipt": "tests/fixtures/codex/real-run.json", "read_beats_workspace_write": "yes, seen once",
                 "seen": ["run 1 refused at start: a quoted path in a dotted -c key keeps its quotes; profile paths must be absolute, ~/ or :special",
                          "run 2, the filesystem table inline: an append into the record folder at read failed, Operation not permitted; its hash unchanged"],
                 "not_settled": "no control run; the header still printed sandbox: workspace-write; two hooks of the user config layer fired too, their writes unknown"},
    "unconfirmed": ["features.hooks set by the project layer", "async in hooks.json (none written)", "the hook payloads' shape", "the rollout's rows and exit "
                    "codes", "the global AGENTS.md counted", "prompt rules inside the workspace and under the profile, before ~ or * expand", "whether the prompt rules on bash -lc and the other wrappers match "
                    "Codex's own bash -lc around every shell call, so that every call asks", "approval_policy never refusing a five act", "the :workspace_roots glob form",
                    "a granted domain written as allowed (none is: a grant taken back would stay open until the next write)"],
    "read": "2026-11-07, the maker's ruling through the question tool: the block names read.md and carries none of "
            "its bytes, since a project's AGENTS.md is committed and pushed with it; before, the read was carried inline and trimmed to the room left",
    "quoted": "a prompt rule is a prefix of the command's tokens, so it cannot see inside a quoted word: git p\"us\"h, \"git\" \"push\" and git -C "
              "\"a b\" push are not the rule's git push, and nothing asks for them; the hook reads the call as the shell does and records the act by its "
              "verb, not seen when no yes stands, and the brief says the host's own rule could not see this form (Astra's audit of batch C, finding 9, "
              "measured on the fake host; how Codex tokenises a quoted word before its rules match is not confirmed)",
    "turn_source": "0.164.0: the fixture's user rows (event_msg user_message, response_item message role user) name no source of a turn; unconfirmed whether "
                   "any version marks a peer's turn, so the shared reader looks for one and the opening-text wrapper decides without it (card 9)"}
COVERAGE = ("the answer to a prompt: no hook receives it, so it is read from what ran", "hosted web search, which runs at the vendor", "every call while the "
            "workshop or its hooks are untrusted: calls come from the rollout, asks are not seen", "destruction inside the workspace", "a live safety or legal claim")
SYNC = ("SessionStart", "Stop", "SessionEnd")  # never async: the session line, the turn's answers and the end are written before the host goes on
HOOKED = ("SessionStart", "UserPromptSubmit", "PreToolUse", "PermissionRequest", "PostToolUse", "Stop", "SessionEnd")
EVENTS = HOOKED + ("PreCompact", "PostCompact", "SubagentStart", "SubagentStop", "Interrupt")  # the last five: session events, never failures
SETTINGS, LIMIT, CHAIN = (".codex", "config.toml"), 30 * 1024, 32 * 1024  # what the boundary reads at SessionStart; the contract's block (version 4, rulings rows 42 and 43 of 2026-11-08, was 24 KiB by card 12; a project keeps CHAIN - LIMIT, 2 KiB); Codex's chain
CREDS = ("~/.ssh", "~/.aws", "~/.config/gh", "~/.gnupg", "~/.netrc")
WRAPPED = (("bash", "-c"), ("bash", "-lc"), ("sh", "-c"), ("zsh", "-c"), ("zsh", "-lc"), ("env",), ("sudo",), ("nice",), ("time",), ("command",),
           ("xargs",))  # the first adapter's WRAPPED as token prefixes: a wrapped five act asks (Astra's audit)
SHORT = (("rm", "-rf", "/"), ("rm", "-rf", "/*"), ("rm", "-rf", "~"), ("rm", "-rf", "~/"), ("sudo", "rm"), ("mkfs",), ("chmod", "-R", "777", "/"), ("chmod", "-R", "777", "/*"))
NOT_COVERED = ("dd if=…: a prefix names whole words, and if= carries its path in the same word", "the fork bomb :(){ :|:& };:, not a command",
               "mkfs.<type>, another command's name", "rm -fr / and other spellings of the flags", "**/.env files: the profile takes paths, never patterns")
WHY = {"forbidden": "on the short list nobody wants from a partner: refused by the host, shown at the welcome, each line strikeable",
       "prompt": "one of the five acts (leaving this machine, moving money, destroying what the partner did not make, deploying or pushing): asked in Codex's own prompt"}
FILES = {"config": ("config.toml",), "hooks": ("hooks.json",), "rules": ("rules", "sandbox-os.rules")}
OVERRIDES = ((("approval_policy",), "never", "Codex asks nothing at this scope, so none of the five acts is asked"),
             (("sandbox_mode",), "danger-full-access", "the sandbox is off at this scope"), (("default_permissions",), ":danger-full-access",
             "the permissions at this scope leave the sandbox off"), (("features", "hooks"), False, "the hooks are off at this scope, so nothing is observed"))
CARD7 = "Codex's user settings are written only on the maker's binding yes to the welcome's fence card, at a path given; there is none"
PATCH, SHELL_TOOLS = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Move to: (.+)$", re.M), ("shell", "exec_command", "local_shell", "container.exec")
TREE_FENCE = ("sandbox_os", "tests", "seeds", "BUDGETS.md", "LICENSE", "README.md", "CLAUDE.md", "AGENTS.md")
OWN = ["You never edit the host's settings (.codex/, .claude/, .mcp.json, in the workshop or a project) or the instruction files (AGENTS.md, CLAUDE.md)."]
READ = ("Read read.md at the workshop's root first, before the charter and the book: it holds what the record knows about the things in hand, "
        "written by the tool at a session's start and its end, and this block carries none of it.")  # a pointer only: the maker's ruling of 2026-11-07
RULES_HEAD ="# placed by Sandbox OS: the short list refused, the five acts asked; never an allow. Yours go in another file.\n"

_sha = lambda b: hashlib.sha256(b.encode() if isinstance(b, str) else b).hexdigest()
_read = lambda path: open(path, "rb").read()
_tk = lambda k: k if re.fullmatch(r"[A-Za-z0-9_-]+", k) else json.dumps(k, ensure_ascii=False)
_tv = lambda v: ("true" if v else "false") if isinstance(v, bool) else "[" + ", ".join(map(_tv, v)) + "]" if isinstance(v, list) else json.dumps(v, ensure_ascii=False)
_units = lambda root: sorted({u for u in (os.listdir(os.path.join(root, "projects")) if os.path.isdir(os.path.join(root, "projects")) else [])
                             if os.path.isdir(os.path.join(root, "projects", u, "record"))} | {"workshop"})

def _note(root, body, once=None, clock=None):  # a note by the tool in the workshop unit; with once=(field, value), not again while one of that event carries it
    with (s := _open(root, clock=clock)).locked():
        if not (once and any((l["body"] or {}).get("event") == body["event"] and l["body"].get(once[0]) == once[1] for l in s.lines(unit="workshop", kinds=["note"]))):
            return s.append("workshop", "note", dict(body, host=NAME), by=TOOL)

def hook_command():  # the command's hook entry under the tool's own interpreter, never the PATH's python3; it calls the boundary, then binds a said line
    return f"{shlex.quote(sys.executable)} {shlex.quote(os.path.join(TREE, 'sandbox_os', 'command', 'hook.py'))} codex"

def block(workshop_root=None):
    """The block: the version, the pointer to read.md (never its bytes: a project's AGENTS.md is committed and pushed with the project, the
    maker's ruling of 2026-11-07), the charter and the book as the session is handed them (their cut while the switch stands,
    card 31, else whole; the workshop's own, else as shipped), the grants, the flow's step, the ruled lines, the projection hash over those."""
    own = lambda n: open(os.path.join(workshop_root, n), encoding="utf-8").read().rstrip("\n") if workshop_root and os.path.exists(os.path.join(workshop_root, n)) else None
    carried = [t for _, t in claude_code.pages(workshop_root)]
    carried += [t for t in (own("grants.md"), own("flow.md")) if t]
    parts = [BEGIN, f"Sandbox OS {VERSION}: the partner's standing instructions, placed by the tool. Codex reads no imports, so the " + (
             "partner's cut of the charter and the book is carried here, made by the tool from charter.md and book.md, which stay whole; "
             if claude_code.CUT else "charter and the book are carried here whole, as charter.md and book.md hold them; ") +
             "the maker edits those files, never this block.", READ, "",
             *[x for t in carried for x in (t, "")], "Each project's present page is projects/<unit>/where-it-stands.md; find asks the record "
             "through the partner's tools, never by reading the record's files.", *[f"- {r}" for r in RULED + [r for r in OWN if r not in RULED]],
             f"Projection: sha256 {_sha(chr(10).join(carried))} over the charter, the book and the grants as carried above.", END]
    return "\n".join(parts)

def _place(root, d, new, clock=None):
    """The block into <d>/AGENTS.md, text outside the markers kept byte for byte, an edited block never replaced: (its path, whether placed)."""
    path = os.path.join(d, "AGENTS.md")
    cache = os.path.join(root, "cache", "placed", "AGENTS.md.sha256" if d == root else f"AGENTS-{_sha(path)[:12]}.sha256")
    text, last = open(path, encoding="utf-8").read() if os.path.exists(path) else "", open(cache).read().strip() if os.path.exists(cache) else None
    cur = text[i:text.index(END, i) + len(END)] if (i := text.find(BEGIN)) >= 0 and END in text[i:] else None
    if cur is not None and _sha(cur) != _sha(new) and last and _sha(cur) != last:
        _note(root, {"event": "instruction-file-edited", "path": path, "placed_sha256": last, "found_sha256": _sha(cur),
                     "text": "the block in AGENTS.md was edited since the tool placed it; it is kept as edited, never replaced"}, once=("found_sha256", _sha(cur)), clock=clock)
        return path, False
    _put(path, (text.replace(cur, new) if cur is not None else text + ("\n" if text and not text.endswith("\n") else "") + new + "\n").encode(), "block")
    _put(cache, (_sha(new) + "\n").encode(), "block")
    return path, True

def instruction_file(workshop_root, home=None, clock=None):
    """The block in <workshop>/AGENTS.md and, where a project is its own git repository (Codex starts its walk there, R-HOSTS-14), in that
    project's AGENTS.md too; past 30 KiB (the contract's version 4, rulings rows 42 and 43; 24 KiB by card 12 before) placed whole with a block-over note (row 90). The chain is measured at the root and in each project."""
    root = os.path.realpath(workshop_root)
    new, projects = block(root), [os.path.join(root, "projects", u) for u in _units(root) if u != "workshop"]
    (path, placed), also = _place(root, root, new, clock), [_place(root, d, new, clock)[0] for d in projects if os.path.exists(os.path.join(d, ".git"))]
    out = {"path": path, "placed": placed, "sha256": _sha(new), "bytes": len(new.encode()), "also": also,
           "findings": [] if placed else ["the block was edited since it was placed; kept as it is, both hashes in a note"]}
    c = [chain(root, d, home, clock=clock) for d in [root] + projects][0]
    if placed and out["bytes"] > LIMIT:
        _note(root, {"event": "block-over", "path": path, "sha256": out["sha256"], "bytes": out["bytes"], "limit": LIMIT, "chain_limit": CHAIN, "room": (room := CHAIN - c["bytes"]),
                     "floor": CHAIN - LIMIT, "text": f"the block is {out['bytes']} bytes, past the contract's {LIMIT}, which leaves a project at least "
                     f"{CHAIN - LIMIT}; placed whole, {room} bytes of Codex's {CHAIN} left"},
              once=("sha256", out["sha256"]), clock=clock)
    return dict(out, chain=c)

def chain(workshop_root, cwd, home=None, *, top=None, record=True, clock=None):
    """The AGENTS.md files Codex reads for a session in cwd: the global one (home given), then from the nearest folder at or above cwd holding .git
    (no higher than top; else cwd alone) down to cwd; what fits whole in 32 KiB is read. A walk without the block, or dropping files, is a not_seen line."""
    root, cwd, top = os.path.realpath(workshop_root), os.path.realpath(cwd), os.path.realpath(top) if top else None
    ups = [cwd]
    while ups[-1] != os.path.dirname(ups[-1]) and ups[-1] != top:
        ups.append(os.path.dirname(ups[-1]))
    start = next((d for d in ups if os.path.exists(os.path.join(d, ".git"))), cwd)
    pick = lambda d: next((p for p in (os.path.join(d, "AGENTS.override.md"), os.path.join(d, "AGENTS.md")) if os.path.isfile(p)), None)
    files, total, read, dropped = [p for p in [pick(os.path.join(home, ".codex")) if home else None] + [pick(d) for d in ups[:ups.index(start) + 1][::-1]] if p], 0, [], []
    for p in files:
        (read if total + os.path.getsize(p) <= CHAIN and not dropped else dropped).append(p)
        total += os.path.getsize(p)
    has, where = any(BEGIN in open(p, encoding="utf-8", errors="replace").read() for p in read), locate(cwd)
    whats = ([f"Codex starts its walk at {start} for a session in {cwd}, and the workshop's block is not on it"] if not has else []) + \
        ([f"Codex dropped files nearest the work: the chain for a session in {cwd} is {total} bytes, past its {CHAIN}"] if dropped else [])
    if record and whats:
        s, unit = _open(root, clock=clock), where[1] if where and where[0] == root else "workshop"
        with s.locked():
            have = {(l["body"] or {}).get("what") for l in s.lines(unit=unit, kinds=["not_seen"])}
            [s.append(unit, "not_seen", {"host": NAME, "what": w, "start": start, "cwd": cwd, "dropped": dropped, "bytes": total}, by=TOOL) for w in whats if w not in have]
    return {"start": start, "files": files, "read": read, "dropped": dropped, "bytes": total, "block": has, "home": home}

_record = lambda root, read: read(_open(root)) if root and os.path.exists(os.path.join(root, "home.json")) else []  # the record, read only here

def _prompts(root=None):  # the five acts as token prefixes, every form of FIVE and of the first adapter's ASK once each (the floor), and the
    verbs = _record(root, lambda s: s.verbs())  # declared verbs' shapes when root is given
    return sorted({tuple(p) for p, _ in FIVE} | {tuple(e[5:-1].replace("*", " ").split()) for e in ASK + MORE} | set(WRAPPED) |
                  {tuple(sh) for v in verbs if v["declared"] for sh in v["shapes"] or []})

_rule = lambda p, d: ("rules", f"prefix_rule(pattern={json.dumps(list(p))}, decision={json.dumps(d)}, justification={json.dumps(WHY[d])})", [d, list(p)])
_j = lambda e: [e[0], list(e[1]) if isinstance(e[1], tuple) else e[1], e[2]]  # an entry as the cache and its hash hold it

def derived(root):  # the entries placed from the record rather than from code: the verbs' prompts beyond the floor, each maker's folder read-only
    floor = set(_prompts())
    return [_j(_rule(p, "prompt")) for p in _prompts(root) if p not in floor] + \
        [["config", ["permissions", "sandbox-os", "filesystem", p], "read"] for p in _owned(root)]


def _builtin(root):  # the profile's own filesystem entries, by path: the fence's files read-only, the rollouts read-only (card 9), the cache and the credentials denied
    j = os.path.join
    read = [j(root, "projects", u, x) for u in _units(root) for x in ("record", "grants.md", ".codex", ".claude")] + \
        [j(root, x) for x in ("grants.md", ".codex", ".claude", ".mcp.json", "charter.md", "book.md")] + [j(TREE, p) for p in TREE_FENCE]
    return dict([(p, "read") for p in read + ["~/.codex/sessions"]] + [(j(root, "cache"), "deny")] + [(c, "deny") for c in CREDS])


def _owned(root):  # each folder only the maker writes (verbs.places) that the built-in entries do not already hold: one TOML key per path (Astra's audit)
    have = {os.path.realpath(os.path.expanduser(p)) for p in _builtin(root)}
    return [p for p in dict.fromkeys(_record(root, places)) if os.path.realpath(p) not in have]

def entries(root, user_scope=False):
    """The steps in order, each a list of (file, key, value); the user scope's are the trust line and the hooks switch. Profile paths are absolute or ~/."""
    if user_scope:
        return [("trust", [("config", ("projects", root, "trust_level"), "trusted"), ("config", ("features", "hooks"), True)])]
    rule, prof, hook, j = _rule, ("permissions", "sandbox-os"), {"type": "command", "command": hook_command(), "timeout": 5}, os.path.join
    fs = list(_builtin(root).items()) + [(p, "read") for p in _owned(root)]  # a maker's folder the built-in entries hold keeps their stricter one
    return [("deny", [rule(p, "forbidden") for p in SHORT] + [("config", prof + ("filesystem", p), a) for p, a in fs]),
            ("sandbox", [("config", k, v) for k, v in ((("approval_policy",), "on-request"), (("default_permissions",), "sandbox-os"), (prof + ("extends",), ":workspace"),
                         (prof + ("network", "enabled"), True), (prof + ("network", "mode"), "limited"), (prof + ("network", "allow_local_binding"), False))] +
             [("config", prof + ("network", "domains", h), "deny") for h in ("localhost", "127.0.0.1", "[::1]")]),
            ("hooks", [("hooks", e, {"matcher": "*", "hooks": [hook]}) for e in HOOKED] + [("config", ("features", "hooks"), True)]),
            ("ask", [rule(p, "prompt") for p in _prompts(root)] + [("config", ("mcp_servers", "sandbox-os", k), v) for k, v in
                     (("command", sys.executable), ("args", ["-m", "sandbox_os", "mcp", "--workshop", root]), ("cwd", root))])]

def _toml_add(text, adds):
    """New keys into a TOML text, nothing of it changed: top-level keys before the first table, else under its header, else a new table at the end."""
    lines = text.rstrip("\n").split("\n") if text.strip() else []
    for table in dict.fromkeys(k[:-1] for k, _ in adds):
        kv, head = [f"{_tk(k[-1])} = {_tv(v)}" for k, v in adds if k[:-1] == table], "[" + ".".join(map(_tk, table)) + "]"
        at = next((i for i, l in enumerate(lines) if (l.strip() == head if table else l.strip().startswith("["))), None)
        if not table or at is not None:
            at = len(lines) if at is None else at + 1 if table else at
            lines[at:at] = kv
        else:
            lines += ([""] if lines else []) + [head] + kv
    return "\n".join(lines) + "\n"

def _parse(kind, data):
    text = data.decode("utf-8")
    o = tomllib.loads(text) if kind == "config" else {l.strip() for l in text.splitlines()} if kind == "rules" else json.loads(text) if text.strip() else {}
    if kind == "hooks" and (not isinstance(o, dict) or not isinstance(o.setdefault("hooks", {}), dict)):
        raise ValueError("not an object of hooks")
    return o

def _render(kind, data, adds):
    text, o = data.decode("utf-8"), _parse(kind, data) if kind == "hooks" else None
    if kind == "hooks":
        return (json.dumps([o["hooks"].setdefault(k, []).append(v) for k, v in adds] and o, indent=2) + "\n").encode()
    return _toml_add(text, adds).encode() if kind == "config" else (("" if text.strip() else RULES_HEAD) + text + ("\n" if text and not text.endswith("\n") else "")
                                                                     + "".join(k + "\n" for k, _ in adds)).encode()

def _has(kind, cur, key, val):  # whether a file's parsed state holds an entry: (present, someone else's differing value or None)
    if kind != "config":
        return (key in cur if kind == "rules" else any(isinstance(g, dict) and any(isinstance(h, dict) and h.get("command") == hook_command()
                                                                                   for h in g.get("hooks") or []) for g in cur["hooks"].get(key) or [])), None
    d = cur
    for k in key[:-1]:
        d = d.get(k) if isinstance(d, dict) else None
    return (False, None) if not isinstance(d, dict) or key[-1] not in d else (d[key[-1]] == val, None if d[key[-1]] == val else d[key[-1]])

def _put(path, data, step):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path + ".part", "wb").write(data)
    os.replace(path + ".part", path)

def _apply(step, items, base, placed, out, files=FILES, added=None):
    """One step: the entries each file lacks added (never someone else's changed, a removed one put back, or an unparsed file touched), read back."""
    for kind in dict.fromkeys(f for f, _, _ in items):
        p = os.path.join(base, *files[kind])
        data = _read(p) if os.path.exists(p) else b""
        try:
            cur = _parse(kind, data)
        except (ValueError, UnicodeDecodeError) as e:
            raise ValueError(f"{p} does not parse ({type(e).__name__}); it is left as it is") from None
        adds = []
        for _, key, val in (x for x in items if x[0] == kind):
            h, (present, theirs), name = _sha(canonical([kind, list(key) if isinstance(key, tuple) else key, val])), _has(kind, cur, key, val), \
                ".".join(key) if isinstance(key, tuple) else key
            out["entries"].append(h)
            if not present:
                out["findings"].append(f"{name} is {theirs!r} in {p}, set by someone else; kept, and the fence reads weaker for it") if theirs is not None else \
                    out["findings"].append(f"the maker removed {name} from {p}; it was not put back") if h in placed else adds.append((key, val))
        new = _render(kind, data, adds) if adds else None
        if adds and [k for k, v in adds if not _has(kind, _parse(kind, new), k, v)[0]]:
            raise ValueError(f"{p} would not hold the entries added to it; nothing was written")
        adds and _put(p, new, step)
        if adds and _sha(_read(p)) != _sha(new):
            raise ValueError(f"{p} read back by hash differs from what was written")
        added is not None and added.extend(_j((kind, k, v)) for k, v in adds)  # what the tool itself added, the only entries it takes out

def settings_plan(workshop_root, user_scope=False):
    """The fence card's lines, one per entry, written nowhere: the user scope's trust line and hooks switch only, or every project entry."""
    root = os.path.realpath(workshop_root)
    if user_scope:
        return [f"Codex, in ~/.codex/config.toml: [projects.\"{root}\"] trust_level = \"trusted\", so Codex loads this workshop's .codex/ layer (its rules, "
                "its profile and its hooks); trusting each hook by hash stays yours, in Codex's /hooks",
                "Codex, in ~/.codex/config.toml: [features] hooks = true, in case the workshop's own layer cannot turn the hooks on (unconfirmed)"]
    say = lambda f, k, v: (f"Codex {'refuses' if v[0] == 'forbidden' else 'asks first'}: {' '.join(v[1])}" if f == "rules" else
                           f"Codex observes every {k} event, by {hook_command()}" if f == "hooks" else f"Codex setting {'.'.join(k)} = {_tv(v)}")
    return [say(f, k, v) for _, items in entries(root) for f, k, v in items]

def _binding(root, yes, clock=None):  # the maker's standing yes to the welcome's fence card, read back from the record, else None
    s = _open(root, clock=clock)
    a = s.get(yes) if isinstance(yes, str) else None
    b = (a or {}).get("body") or {}
    c = s.get(b["card"]) if a and a["kind"] == "answer" and isinstance(b.get("card"), str) else None
    return a if (c and a["by"]["kind"] == "maker" and b.get("answer") == "yes" and a["mark"] not in ("struck", "deleted", "erased", "superseded")
                 and b.get("presence") != "none" and b.get("stale") is not True and b.get("person") != "not established"
                 and (c["body"] or {}).get("purpose") == "fence-user-settings") else None

def write_settings(workshop_root, user_scope=False, *, path=None, yes=None, clock=None):
    """The fence into <workshop>/.codex/ in four steps, deny, sandbox, hooks, ask, each read back by hash before the next, a failed step stopping
    the rest; the user scope only at a path given, on the maker's binding yes to the fence card, else refused (card 07). A note names each entry by hash."""
    root = os.path.realpath(workshop_root)
    if user_scope and not (path and _binding(root, yes, clock)):
        raise Refused(CARD7)
    base, files = (os.path.dirname(path), {"config": (os.path.basename(path),)}) if user_scope else (os.path.join(root, ".codex"), FILES)
    cache = os.path.join(root, "cache", "placed", f"codex-{_sha(os.path.realpath(path or base))[:12]}.json")
    was = json.load(open(cache)) if os.path.exists(cache) else {}
    placed, now = set(was.get("entries", [])), [] if user_scope else derived(root)
    out = {"path": path if user_scope else os.path.join(base, "config.toml"), "files": [os.path.join(base, *f) for f in files.values()], "written": False,
           "steps": [], "findings": [], "entries": [], "not_covered": [] if user_scope else list(NOT_COVERED)}
    mine = [e for e in was.get("added", []) if e in was.get("derived", [])]
    for kind, key, val in (e for e in mine if e not in now):  # the tool's own, which the record no longer gives (Task 9); never one the maker wrote
        if kind == "config":
            out["findings"].append(f"Codex keeps {key[-1]} read-only until you remove it from config.toml; the tool adds there and never removes")
        p = os.path.join(base, *files[kind]) if kind in files else None
        lines = _read(p).decode("utf-8").splitlines(keepends=True) if kind == "rules" and p and os.path.exists(p) else []
        if any(l.strip() == key for l in lines):
            _put(p, "".join(l for l in lines if l.strip() != key).encode(), "derived")
            placed.discard(_sha(canonical([kind, key, val])))
            out["findings"].append(f"{' '.join(val[1])} asked for a verb that is struck or changed; the tool's own entry was taken out")
    for step, items in entries(root, user_scope):
        try:
            _apply(step, items, base, placed, out, files, mine)
            out["steps"].append({"step": step, "entries": len(items), "read_back": True})
        except Exception as e:
            out["findings"].append(f"step {step} failed ({type(e).__name__}: {e}); the steps after it were not written")
            break
    else:
        out["written"] = True
        _put(cache, json.dumps({"entries": sorted(set(out["entries"]) | placed), "derived": now, "added": [e for e in now if e in mine]}).encode(), "placed")  # by hash, so an entry the maker removes stays out
    _note(root, {"event": "settings-written", "path": out["path"], "files": out["files"], "written": out["written"], "steps": [s["step"] for s in out["steps"]],
                 "entries": out["entries"], "findings": out["findings"], "not_covered": out["not_covered"], **({"yes": yes} if user_scope else {})}, clock=clock)
    return out

def scope_paths(home, workshop_root):  # where overrides() reads: the maker's Codex config and rules under a home, and the workshop's own config
    return {"user": os.path.join(home, ".codex", "config.toml"), "project": os.path.join(workshop_root, ".codex", "config.toml"), "rules": os.path.join(home, ".codex", "rules", "default.rules")}

def read_back(workshop_root, scopes=None):
    """Each scope read, none changed, nothing recorded: approval never, sandbox or hooks off, the workshop untrusted, an allow rule over a five act."""
    root, found = os.path.realpath(workshop_root), []
    covers = lambda p, f: all(f[i] == p[i] for i in range(min(len(p), len(f))))
    gap = lambda scope, path, at, field, what: {"event": "not-seen", "scope": scope, "path": path, "key": field, "field": field, "at": at, "differs": "not read",
                                                "what": f"{what}; read past, never changed"}  # no value of the maker's ever: the key and the kind of difference (Astra's audit)
    for scope, path in (scopes or scope_paths(os.path.expanduser("~"), root)).items():
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            text = None
        except ValueError as e:  # a file of the maker's that is not text at all
            found.append(gap(scope, path, f"byte {getattr(e, 'start', '?')}", "file", "a file of yours that is not text"))
            continue
        if scope == "rules":
            for n, c in enumerate((text or "").split("prefix_rule(")[1:], 1):  # each rule read alone; one this reader cannot read is a named gap
                m, d = re.search(r"pattern\s*=\s*(\[[^\[\]]*\])", c), re.search(r'decision\s*=\s*"(\w+)"', c)
                try:
                    pat = json.loads(m.group(1).replace("'", '"'))
                except (AttributeError, ValueError):
                    found.append(gap(scope, path, f"rule {n}", "pattern", "a prefix_rule of yours whose pattern this reader cannot read"))
                    continue
                (d.group(1) if d else "allow") == "allow" and any(covers(pat, f) for f in _prompts()) and found.append(
                    {"event": "override", "scope": scope, "path": path, "key": "prefix_rule", "differs": "an allow rule where the fence asks", "at": f"rule {n}",
                     "what": "an allow rule of yours covers one of the five acts, so Codex runs it unasked; listed, never edited"})
            continue
        try:
            cfg = tomllib.loads(text) if text is not None else {} if scope == "user" else None
        except ValueError as e:
            found.append(gap(scope, path, (re.search(r"line \d+, column \d+", str(e)) or [str(e)[:60]])[0], "file", "a config of yours that does not parse"))
            continue
        get = lambda key: [d := cfg] and [d := d.get(k) if isinstance(d, dict) else None for k in key][-1]
        found += [{"event": "override", "scope": scope, "path": path, "key": ".".join(k), "value": v, "differs": "set where the fence says unset", "what": w}
                  for k, v, w in OVERRIDES if cfg is not None and get(k) == v]  # value: the adapter's own constant the key matched, never a word of the maker's
        trust = get(("projects", root, "trust_level")) if scope == "user" else "trusted"
        trust != "trusted" and found.append({"event": "override", "scope": scope, "path": path, "key": f"projects.{root}.trust_level",
                                             "differs": "unset where the fence says trusted" if trust is None else "another level than the fence's trusted",
                                             "what": "Codex does not trust this workshop, so it loads none of its .codex/ layer: no rules, no profile, no hooks; "
                                                     "calls come from the rollout where one is read, and asks are not seen"})
    return found

def overrides(workshop_root, scopes=None, clock=None):  # read_back, and a note by the tool for each thing it found
    found = read_back(workshop_root, scopes)
    [_note(os.path.realpath(workshop_root), f, clock=clock) for f in found]
    return found

def _script(c):  # a shell call's command as the hook carries it: the script of bash -lc (or zsh, sh), else the words joined
    w = [str(x) for x in c] if isinstance(c, list) else None
    return c if w is None else w[2] if len(w) == 3 and os.path.basename(w[0]) in ("bash", "zsh", "sh") and w[1] in ("-lc", "-c") else shlex.join(w)

def normalise(ev):
    """Codex's shapes into the boundary's (PROVEN's normalise), the host's own input hashed in _sha256; MCP names and all else as they are."""
    inp = ev.get("tool_input") if isinstance(ev, dict) else None
    if isinstance(inp, dict) and ev.get("tool_name") == "apply_patch":
        cwd, text = ev.get("cwd") if isinstance(ev.get("cwd"), str) else "", next((x for x in (inp.get("command"), inp.get("input")) if isinstance(x, str)), "")
        paths = [os.path.join(cwd, (a or b).strip()) for a, b in PATCH.findall(text)]
        return dict(ev, tool_name="Edit", tool_input={"file_path": paths[0] if paths else None, "paths": paths[1:]}, _sha256=input_hash(inp))
    if isinstance(inp, dict) and ev.get("tool_name") == "Bash" and isinstance(inp.get("command"), list):
        return dict(ev, tool_input=dict(inp, command=_script(inp["command"])), _sha256=input_hash(inp))
    return ev

def _said(o):  # a rollout row's user words: an event_msg user_message, or a user message item's text; else None
    p = o.get("payload") if isinstance(o.get("payload"), dict) else {}
    return p.get("message") if p.get("type") == "user_message" else "".join(x.get("text") or "" for x in p.get("content") or [] if isinstance(x, dict)) if p.get("role") == "user" else None
relayed = lambda prompt, transcript=None: _relayed(prompt, transcript, _said)  # card 9 through Codex: its rollout's row for the prompt, else the wrapper

def _call(p):  # (tool, the input as the hook would carry it) for one call row of a rollout
    name = "shell" if p.get("type") == "local_shell_call" else p.get("name")
    args = p.get("action") if p.get("type") == "local_shell_call" else {"input": p.get("input")} if p.get("type") == "custom_tool_call" else p.get("arguments")
    args = json.loads(args) if isinstance(args, str) else args  # arguments that do not parse make the row a named gap (events' guard)
    args = args if isinstance(args, dict) else {}
    return ("Bash", {"command": _script(args.get("command") or args.get("cmd"))}) if name in SHELL_TOOLS else \
        (name, {"command": args.get("input")}) if name == "apply_patch" else (name, args)

class _Drift(ValueError): pass  # a rollout field whose shape changed, by its name

def _want(v, kind, field):  # a row's field: its value when absent or of its kind, else the row is a named gap
    if v is None or isinstance(v, kind):
        return v
    raise _Drift(field)

def _ended(o):  # a call's end from its output: failed on an exit code other than 0, denied when it says the user refused, else post
    try:
        out = json.loads(o) if isinstance(o, str) else o
    except ValueError:
        out = o
    meta, text = _want(out.get("metadata"), dict, "metadata") if isinstance(out, dict) else None, str(out.get("output", "")) if isinstance(out, dict) else str(out or "")
    m, code = re.match(r"\s*(?:Exit code|Process exited with code):?\s*(-?\d+)", text), _want((meta or {}).get("exit_code"), int, "exit_code")
    code = int(m.group(1)) if m and code is None else code
    return "denied" if re.search(r"(?:rejected|aborted|declined) by (?:the )?user", text[:300], re.I) else "failed" if code not in (None, 0) else "post"

def version(path):  # the host's version as the rollout's session row says (a string, else none), or None
    return next((v for _, o in (rows(path) if path else ()) if o and o.get("type") == "session_meta" and isinstance(o.get("payload"), dict)
                 for v in [o["payload"].get("cli_version")] if isinstance(v, str)), None)

def events(since, transcripts):
    """The rollouts' calls as hook lines, each row under its own guard: a torn row, an unproven version or a changed field is a named gap; never an exception."""
    out = []
    for path in transcripts:
        m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$", path or "")
        sid, cwd, seen = m.group(1) if m else os.path.basename(path or "")[:-6], None, set()
        for off, o in rows(path):
            c, t, p = {"host": NAME, "session": sid, "cwd": cwd, "via": "transcript"}, (o or {}).get("type"), (o or {}).get("payload")
            try:
                if o is None:
                    out.append(("not_seen", dict(c, offset=off, what=f"a torn or unreadable row at byte {off} of the rollout")))
                elif not isinstance(p, dict):
                    raise _Drift("payload")
                elif since and (o.get("timestamp") or "") < since:
                    continue
                elif t == "session_meta":
                    sid, cwd, v = _want(p.get("id"), str, "id") or sid, _want(p.get("cwd"), str, "cwd") or cwd, _want(p.get("cli_version"), str, "cli_version")
                    if v not in PROVEN["versions"] and v not in seen:
                        seen.add(v)
                        out.append(("not_seen", dict(c, session=sid, cwd=cwd, version=v, what=f"Codex {v} is not a proven version; its rows were read as 0.164.0's")))
                elif t == "turn_context":
                    cwd = _want(p.get("cwd"), str, "cwd") or cwd
                elif t == "response_item" and p.get("type") in ("function_call", "custom_tool_call", "local_shell_call"):
                    if not _want(p.get("call_id"), str, "call_id") or not (_want(p.get("name"), str, "name") or p.get("type") == "local_shell_call"):
                        raise _Drift("call_id")
                    tool, inp = _call(p)
                    ev = normalise({"tool_name": tool, "tool_input": inp, "cwd": cwd or ""})
                    out.append(("hook", dict(c, event="PreToolUse", phase="pre", tool=ev["tool_name"], call_id=p["call_id"],
                                             input_sha256=ev.get("_sha256") or input_hash(inp), _input=ev["tool_input"])))
                elif t == "response_item" and p.get("type") in ("function_call_output", "custom_tool_call_output") and p.get("call_id"):
                    out.append(("hook", dict(c, event="PostToolUse", phase=_ended(p.get("output")), call_id=_want(p["call_id"], str, "call_id"))))
            except Exception as e:  # the row is a gap with its offset and field; the reading goes on
                out.append(("not_seen", dict(c, offset=off, field=(f := str(e) if isinstance(e, _Drift) else None),
                                             what=f"a {t if isinstance(t, str) else 'changed'} row at byte {off} whose {f or type(e).__name__} changed shape; read past")))
    return out

def usage(since, transcripts):
    """Tokens per session from the rollout's cumulative counts (the last, less the last before since), each row under its own guard; money null."""
    per = []
    for path in transcripts:
        sid, model, before, last = None, None, {}, None
        for _, o in rows(path):
            p = (o or {}).get("payload")
            try:
                sid = _want(p.get("id"), str, "id") or sid if o.get("type") == "session_meta" else sid
                model = _want(p.get("model"), str, "model") or model if o.get("type") == "turn_context" else model
                if o.get("type") == "event_msg" and p.get("type") == "token_count" and isinstance(p.get("info"), dict):
                    tot = {k: _want(v, int, k) for k, v in (_want(p["info"].get("total_token_usage"), dict, "total_token_usage") or {}).items() if k.endswith("tokens")}
                    before, last = (tot, last) if since and (o.get("timestamp") or "") < since else (before, tot)
            except (AttributeError, ValueError, TypeError):
                continue  # a changed or torn row counts nothing; events() names it
        n = lambda k: (last.get(k) or 0) - (before.get(k) or 0)
        last and per.append({"host": NAME, "session": sid, "model": model, "tokens_in": n("input_tokens"), "tokens_out": n("output_tokens"), "cost": None, "price_table_date": None})
    return per
