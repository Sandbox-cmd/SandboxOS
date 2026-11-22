# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The hook boundary every host shares: one event in, lines out, never a refusal. The host runs this file (`/usr/bin/env python3 <tree>/sandbox_os/hosts/boundary.py
claude-code`): one JSON event on standard input; the calls into the session's own file, the asks, acts outside a grant, five-act candidates, failures and gaps into the log."""
import hashlib, importlib, json, os, re, shlex, subprocess, sys
from urllib.parse import urlparse

TREE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if __package__ in (None, ""):  # run by the host as a script: the tree onto the path
    sys.path.insert(0, TREE)

from sandbox_os.store import Busy, open as _open  # noqa: E402
from sandbox_os.store.line import canonical, find_secret, local_date, UNIT_RE, TEXT_MAX  # noqa: E402
from sandbox_os.store.verbs import WRAP, SHELLS, GIT_VALUED, FLOOR, simple as _simple, words, fits, parse_receipt, five_act as _five, act_sha256, places, ACTS  # noqa: E402
from sandbox_os.store.log import TOOL  # noqa: E402

MAKER = {"kind": "maker", "name": "maker", "model": None, "host": None}
EVENTS = ("SessionStart", "UserPromptSubmit", "PreToolUse", "PermissionRequest", "Notification", "PermissionDenied", "PostToolUse", "PostToolUseFailure",
          "InstructionsLoaded", "Stop", "SessionEnd")
PHASE = {"PreToolUse": "pre", "PermissionRequest": "ask", "PostToolUse": "post", "PostToolUseFailure": "failed", "PermissionDenied": "denied"}
OUTCOME = {"post": "ran", "failed": "failed", "denied": "denied by host"}
RAN = {"post": "ran", "failed": "did not run", "denied": "refused by the host"}  # what an act outside a grant came to, read from its call's end
LEAVES, MONEY, DESTROYS, DEPLOYS = "leaving this machine", "moving money", "destroying what the partner did not make", "deploying or pushing"
UNRESOLVED, STRICT = "unresolved: names an address or an outside path", ("a write to the fence", "a write to the settings", "a write outside the project")
FIVE, TEXTS = FLOOR, ("stdout", "stderr", "output", "content", "result")  # the floor is the store's (verbs.FLOOR, row 34)
EDITS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
OUT_SECRET, WORDS_SECRET = "the output matched a secret pattern and was not kept", "the outside's words matched a secret pattern and were not kept"
HOSTS, FORGERS = {"claude", "codex", "node"}, {"script", "expect", "unbuffer", "socat"}
TERMINALS = {"ghostty", "Terminal", "iTerm2", "kitty", "alacritty", "wezterm", "wezterm-gui", "Hyper", "Claude", "Code", "Cursor", "sshd", "sshd-session", "tmux"}
LOOPBACK, URL = re.compile(r"\b(?:127\.0\.0\.1|localhost|0\.0\.0\.0)(?::\d+)?|\[::1\](?::\d+)?"), re.compile(r"https?://[^\s'\"<>]+")
ADDRESS = re.compile(r"\b(?:https?|s3|ftp|sftp|ssh|rsync)://(?!(?:127\.0\.0\.1|localhost|\[::1\])[:/])[^\s'\"]+|(?:^|\s)[\w.-]+@[\w-]+(?:\.[\w-]+)*:")
REDIRECT, QUOTED = re.compile(r"(?:^|[^<>&\d])>>?\|?\s*([^\s;&|<>()'\"]+)"), re.compile(r"['\"]((?:/|~/|\.\.?/)[^'\"]*)['\"]")
SCRIPT = re.compile(r"\b(?:python3?|perl|ruby|node)\b[^;&|]*\s-[ce]\b")
OPENS = re.compile(r"open\([^)]*,\s*['\"][wax]|write_text\(|write_bytes\(|\.write\(|writeFileSync|appendFileSync")
UNSHIPPED = ("work/", "morning/")  # the tree's own scratch and the morning's pages; the rest of the tree is the tool's, fenced
NAMED = re.compile(r"\b[0-9A-HJKMNP-TV-Z]{26}\b")  # a line's id, as a Stop's last message names a card
CARD = ("whether the partner may go on with {kind} on {unit}: it did so twice in one session with no grant of yours covering it", "Give it a grant in "
        "your own words if it should go on; until then each one is a line in the brief.", "Leave it: each act stays listed.", "a card you did not need")


class Failure(Exception):  # a named cause the hook records when it cannot read an event: malformed input, an unknown event or tool, a missing field
    pass


def input_hash(obj):
    """SHA-256 of a tool's input in canonical JSON: all of a tool's input that ever enters a line."""
    return hashlib.sha256(canonical(obj).encode()).hexdigest()



def five_act(tool, tool_input):
    """Which of the five acts a call is, in the day-one words, or None: the first of its simple commands the store's five_act classes
    (verbs.five_act: the floor's words behind any wrapper or option, data sent by curl or wget, gh api writes, aws s3 and rsync out)."""
    cmds = _simple(str(tool_input.get("command", ""))) if tool == "Bash" and isinstance(tool_input, dict) else []
    return next((x for x in map(_five, cmds) if x), None)


def fenced(root, path):
    """Whether a path is inside the fence: the record folders, cache/, the settings, the grant files, the charter and the book, the tool's tree."""
    p = os.path.realpath(path)
    return bool(re.fullmatch(r"projects/[^/]+/(record(/.*)?|grants\.md)|(cache|\.claude)(/.*)?|grants\.md|charter\.md|book\.md", os.path.relpath(p, root))) or \
        p.startswith(TREE + "/") and not p.startswith(tuple(os.path.join(TREE, u) for u in UNSHIPPED))


def _writes(cmd):
    """The paths a shell command writes: its redirections, tee, the destination of cp, mv and install, the files of sed -i, dd of=, and
    the quoted paths of an inline script (python -c, perl -e, node -e ...) that opens a file to write."""
    out = [p for p in REDIRECT.findall(cmd) if not p.startswith(("&", "/dev/"))]
    for a in _simple(cmd):
        args = []
        for x in a[1:]:
            if re.match(r"\d*[<>]", x):
                break
            args += [] if x.startswith("-") else [x]
        out += (args if a[0] == "tee" else args[-1:] if a[0] in ("cp", "mv", "install") and len(args) > 1 else
                args[1:] if a[0] in ("sed", "gsed") and any(x.startswith(("-i", "--in-place")) for x in a[1:]) else
                [x[3:] for x in a[1:] if x.startswith("of=")] if a[0] == "dd" else [])
    return out + (QUOTED.findall(cmd) if SCRIPT.search(cmd) and OPENS.search(cmd) else [])


def _place(root, home, path, owned=()):
    """What a write to this path is: to the settings, to the fence (owned, the folders only the maker writes, verbs.places, among it: with the
    sandbox off, row 30, a shell write there is refused by nothing, so it is recorded), outside the project (the unit's folder), or nothing."""
    p, claude = os.path.realpath(os.path.join(home, os.path.expanduser(path))), os.path.realpath(os.path.expanduser("~/.claude"))
    if re.fullmatch(r"\.claude(/.*)?", os.path.relpath(p, root)) or p.startswith(os.path.join(claude, "settings")):
        return "a write to the settings"
    mine = any(p == o or p.startswith(o + "/") for o in (os.path.realpath(x) for x in owned))
    return "a write to the fence" if mine or fenced(root, p) else None if p == home or p.startswith(home + "/") else "a write outside the project"


def service(tool, inp):
    """The domain a call reaches outside this machine by a fetch (WebFetch, WebSearch, curl or wget reading), or None; loopback is the pages'."""
    cmd = _simple(str(inp.get("command", ""))) if tool == "Bash" else []
    urls = [inp.get("url", "")] if tool == "WebFetch" else [u for a in cmd if a[0] in ("curl", "wget", "http", "xh") for u in URL.findall(" ".join(a))]
    hosts = ["search"] if tool == "WebSearch" else [urlparse(u).hostname or "" for u in urls]
    return next((h for h in hosts if h and not LOOPBACK.fullmatch(h) and h != "::1"), None)


def needs(root, unit, tool, inp, owned=()):
    """The kind of act a call is when it needs more than the working copy (R-PARTNER-15), or None: spawning a helper; a write to the settings,
    to the fence (owned, the folders only the maker writes, among it) or outside the project, by an edit tool or a shell form; one of the five
    acts; reaching a service; else, for a command that names an address or a path outside the workshop and matches no rule, an unresolved act."""
    inp = inp if isinstance(inp, dict) else {}
    path, home = inp.get("file_path") or inp.get("notebook_path"), root if unit == "workshop" else os.path.join(root, "projects", unit)
    if tool in ("Agent", "Task"):
        return "spawning a helper"
    if tool in EDITS and isinstance(path, str):  # every path a call names (a patch's), the strictest class the call's
        return next((k for k in STRICT if k in {_place(root, home, p, owned) for p in [path] + [p for p in inp.get("paths") or [] if isinstance(p, str)]}), None)
    cmd = str(inp.get("command", "")) if tool == "Bash" else ""
    outside = [x for a in _simple(cmd) for x in a[1:] if x.startswith(("/", "~")) and not x.startswith("/dev/")
               and not (os.path.realpath(os.path.expanduser(x)) + "/").startswith(root + "/")]
    return (next((k for k in (_place(root, home, t, owned) for t in _writes(cmd)) if k), None) or five_act(tool, inp)
            or ("reaching a service" if service(tool, inp) else None) or (UNRESOLVED if cmd and (ADDRESS.search(cmd) or outside) else None))


def covering(standing, unit, tool, tool_input):
    """The id of the standing grant whose scope covers the unit, the paths and the service a call names, else None; never a five act."""
    inp = tool_input if isinstance(tool_input, dict) else {}
    paths, dom = [os.path.realpath(p) for p in (inp.get("file_path"), inp.get("notebook_path"), *(inp.get("paths") or [])) if isinstance(p, str)], service(tool, inp)
    glob = lambda pat, p: re.fullmatch(("" if pat.startswith("/") else "(?:.*/)?") + re.escape(pat).replace(r"\*\*/", "(?:.*/)?")
                                       .replace(r"\*\*", ".*").replace(r"\*", "[^/]*"), p) is not None
    for g in [] if five_act(tool, inp) or not (paths or dom) else standing:
        sc = (g.get("body") or {}).get("scope") or {}
        if sc.get("unit") in (unit, "*") and (not dom or any(s == "*" or dom == s or dom.endswith("." + s) for s in sc.get("services") or [])) \
                and all(any(glob(pat, p) for pat in sc.get("paths") or []) for p in paths):
            return g["id"]

def _text(resp):
    """The words a call's response holds: a dict's string values under TEXTS (a list there read as parts), a list's text parts, else str."""
    parts = [resp.get(k) for k in TEXTS] if isinstance(resp, dict) else [p.get("text") if isinstance(p, dict) else p for p in resp] if isinstance(resp, list) else []
    return "\n".join(v if isinstance(v, str) else _text(v) for v in parts if isinstance(v, (str, list))) if isinstance(resp, (dict, list)) else "" if resp is None else str(resp)

OTHER, SPENT = "other words than the yes covered", "the yes is spent: an act ran with other words than it covered"


def _act_words(cmd, shape):
    """The act's text parameters: the plain words after a verb's program and subcommand in the first simple command they begin, its
    options and the shape's own words dropped, or []."""
    front = [w for w in shape or [] if not w.startswith("-")]
    a = next((a for a in map(words, _simple(cmd)) if front and a[:len(front)] == front), [])
    return [w for w in a[len(front):] if not w.startswith("-") and w not in (shape or [])]


def words_hash(cmd, shape):
    """The hash of an act's words, kept on the pre line in place of the words: sha256 of the distinct words, sorted, in canonical JSON. The hosts'
    own copy until the store's retry-hash check lands (batch C's review)."""
    return input_hash(sorted(set(_act_words(cmd, shape))))


def _covered(store, v, p, shape):
    """The hash of the words a yes covered: its act's text and number parameters (the proposal's params at p's index), read as an act of
    the same shape would be, each value one word as the shell would quote it (shlex.join), as the act's own words are read (batch D's sweep)."""
    acts = ((store.get(p["proposal"]) or {}).get("body") or {}).get("params") or []
    act = acts[p["index"] - 1] if 0 < p["index"] <= len(acts) and isinstance(acts[p["index"] - 1], dict) else {}
    types = v.get("params") if isinstance(v.get("params"), dict) else {}
    return words_hash(shlex.join(list(shape or []) + [str(x) for k, x in act.items() if types.get(k) in ("text", "number")]), shape)


def _unknown(store, a):
    """An unknown act's shape: its program alone, and its next word only when a standing verb's shape names that word as the program's
    subcommand; never a host's name, an argument, a value, an address or a path (batch C's review)."""
    w = words(a)
    known = {sh[1] for x in store.verbs() for sh in x["shapes"] or [] if len(sh) > 1 and sh[0] == w[0]}
    return w[:2] if len(w) > 1 and w[1] in known else w[:1]


ASKED = {"bash", "sh", "zsh", "env", "sudo", "nice", "time", "command", "xargs"}  # the programs the adapters' WRAPPED asks name, whatever follows


def _hidden(cmd, shape):
    """Whether the host's own prefix rule could not see a verb's shape in a command (Astra's audit, finding 9): the command holds a quote,
    and no piece of it, read word by word as written with its quotes kept (as a prefix rule reads it), is of the shape or opens with a
    wrapper the adapters' asks name. The hook still reads it as the shell does (simple); the brief says the host could not see it."""
    pieces = [p.split() for p in re.split(r"&&|\|\||[;|&\n()`]|\$\(", cmd)] if re.search(r"[\"']", cmd) else None
    return pieces is not None and not any(w and (os.path.basename(w[0]) in ASKED or fits(shape, w)) for w in pieces)


def _matched(store, tool, inp, act, kind):
    """A Bash call's acts, one per simple command (Astra's audit: the store's acts_in, read a command at a time through Store.verb_for): a
    command of a verb is that verb, its shape and its two hashes; one no verb names that leaves the machine is an unknown act by its shape
    (_unknown), and with none, a call that names an address or an outside path is one by its first such command. The first act stands at the
    top of the pre line, as before; acts lists them all when there are more. A verb's act says quoted when the host's own rule could not see
    its form (_hidden)."""
    if tool != "Bash" or not isinstance(inp, dict):
        return {}
    raw = str(inp.get("command", ""))
    cmds, acts = _simple(raw), []
    for a in cmds:
        v = store.verb_for([a])
        acts += [{"verb": v["id"], "shape": v["shape"], "words_sha256": words_hash(shlex.join(a), v["shape"]), "act_sha256": act_sha256([v["argv"]]),
                  "quoted": _hidden(raw, v["shape"])}] if v else \
            [{"verb": None, "shape": _unknown(store, a)}] if _five(a) in (LEAVES, MONEY, DEPLOYS) else []
    if not acts and cmds and (act in (LEAVES, MONEY, DEPLOYS) or kind == UNRESOLVED):
        a = next((a for a in cmds if _five(a)), None) or next((a for a in cmds if ADDRESS.search(" ".join(a)) or any(x.startswith(("/", "~")) for x in a[1:])), cmds[0])
        acts = [{"verb": None, "shape": _unknown(store, a)}]
    first = next((x for x in acts if x["verb"]), acts[0]) if acts else {"verb": None, "shape": None}
    return dict(first, **({"acts": acts} if len(acts) > 1 else {}))

def standing_grants(store, unit):
    """The grants that stand for a unit now: the maker's yes to their read-back, not taken back, not past, not superseded."""
    return [g for g in store.lines(kinds=["grant"]) if ((g["body"] or {}).get("scope") or {}).get("unit") in (unit, "*")
            and g["mark"] != "superseded" and store.grant_state(g["id"]) == "standing"]

def surface_of(pid, table=None):
    """The whole chain above the host is read: nested when a host (or script, expect) is anywhere above it, whatever terminal sits between;
    terminal only when a terminal application is above and no host is; unknown otherwise (an orphan, a terminal the list does not name)."""
    if table is None:
        out = subprocess.run(["ps", "-axo", "pid=,ppid=,comm="], capture_output=True, text=True, timeout=5).stdout
        table = {int(b[0]): (int(b[1]), b[2]) for b in (l.strip().split(None, 2) for l in out.splitlines()) if len(b) == 3 and b[0].isdigit()}
    name = lambda p: os.path.basename(table[p][1]) if p in table else ""
    while pid in table and name(pid) in SHELLS:  # from the hook up to the host
        pid = table[pid][0]
    p, seen, terminal = table.get(pid, (0, ""))[0], set(), False
    while p in table and p > 1 and p not in seen:
        seen.add(p)
        if name(p) in HOSTS | FORGERS:
            return "nested"
        terminal = terminal or name(p) in TERMINALS or name(p).startswith(("Code Helper", "Cursor Helper", "tmux"))
        p = table[p][0]
    return "terminal" if terminal else "unknown"

def locate(cwd):
    """(workshop root, unit) for a folder inside a workshop: projects/<unit>/... is that unit, the root is "workshop"; else None."""
    d = os.path.realpath(cwd) if isinstance(cwd, str) and cwd else None
    while d and d != os.path.dirname(d):
        if os.path.isfile(os.path.join(d, "home.json")) and os.path.isdir(os.path.join(d, "projects")):
            parts = os.path.relpath(os.path.realpath(cwd), d).split(os.sep)
            unit = parts[1] if parts[0] == "projects" and len(parts) > 1 else "workshop"
            return (d, unit) if UNIT_RE.match(unit) else None
        d = os.path.dirname(d)
    return None

def session_lines(store, unit, session):
    """The whole lines of one session's own file, at the place contract section 1 names; a torn tail is not a line."""
    p = os.path.join(store.unit_dir(unit), "sessions", f"{session}.jsonl")
    data = open(p, "rb").read() if session and os.path.exists(p) else b""
    return [json.loads(r) for r in data[:data.rfind(b"\n") + 1].splitlines() if r.strip()]

class Ctx:
    """One session in one unit: its own file's lines, its surface and model, and the writes the hook makes for it."""
    def __init__(self, host, store, unit, sid):
        self.host, self.store, self.unit, self.sid, self.rows = host, store, unit, sid, session_lines(store, unit, sid)
        state = next((r["body"] for r in self.rows if "surface" in r["body"]), {})
        self.surface, self.model = state.get("surface"), state.get("model")
    def actor(self, **kind):
        return dict({"name": "partner", "model": self.model or "not reported", "host": self.host}, **kind)
    def sess(self, body, kind="hook", refresh=True):
        self.store.session_append(self.unit, self.sid, kind, dict({"host": self.host, "session": self.sid, "via": "hook", "actor": self.actor()}, **body), by=TOOL)
        self.rows = session_lines(self.store, self.unit, self.sid) if refresh else self.rows
    def log(self, kind, body, by=TOOL, about=None):
        return self.store.append(self.unit, kind, dict({"host": self.host, "session": self.sid}, **body), by=by, about=about)
    def mine(self, kinds):
        return [l for l in self.store.lines(unit=self.unit, kinds=kinds) if (l["body"] or {}).get("session") == self.sid]
    def named(self):  # the calls a line of this session already says the act of: a receipt, a failed or not-run note, not seen, unknown
        return {l["body"].get("call_id") for l in self.mine(["receipt", "note", "not_seen"]) if "verb" in l["body"] or l["body"].get("event") == "unknown act"}
    def fail(self, name, cause, err):
        self.log("hook", {"failed": True, "event": name, "cause": cause, "error": f"{type(err).__name__}: {str(err)[:200]}", "exit": 0})

def _acts(ctx, pre, end, output):
    """One line per act of the call (Astra's audit): each of the pre line's acts, else the call's one, as _act writes it; the last line's id."""
    return [_act(ctx, dict(pre, **a), end, output) for a in pre.get("acts") or [pre]][-1]


def _act(ctx, pre, end, output):
    """What an act came to, once per call, by the tool (design section 3 point 3, section 10 point 3), output the outside's words or None: with an
    answered proposal, its receipt linked came_from to it and to the answer or grant, its failure with the one retry said (row 36), or its refusal;
    with a verb and none, an act not seen by the verb's name; with no verb, an unknown act by its shape. It refuses nothing."""
    s, cid, vid, out = ctx.store, pre.get("call_id"), pre.get("verb"), RAN.get(end, "not seen")
    if not vid:
        return ctx.log("note", {"event": "unknown act", "call_id": cid, "tool": pre.get("tool"), "shape": pre.get("shape"), "command": " ".join(pre.get("shape") or []),
                                "act": pre.get("act"), "needs": pre.get("needs"), "input_sha256": pre.get("input_sha256"), "outcome": out})
    v, p = s.verb(vid) or {}, s.proposal_for(vid, ctx.unit, act_sha256=pre.get("act_sha256"))  # a retry only for the failed act's command
    inside = not p and s.door(vid, ctx.unit)["door"] == "inside"  # the inside door asks nothing: its act is a receipt with no proposal, never not seen
    p = dict(proposal=None, answer=None, grant=None, index=1, of=1, undoes=None, failures=0) if inside else p
    base = {"verb": vid, "verb_name": v.get("name"), "call_id": cid, **({"proposal": p["proposal"]} if p else {}), **({"door": "inside"} if inside else {}),
            **({"quoted": True} if pre.get("quoted") else {})}  # the host's own rule could not see this form (_hidden)
    if p and not inside and "answer" in pre and (pre.get("proposal"), pre.get("answer")) != (p["proposal"], p["answer"] or p["grant"]):
        return ctx.log("not_seen", dict(base, proposal=None, act=pre.get("act"), outcome=out, what="ran before your answer"))  # bound at the pre line; spends nothing
    if not p or end == "post" and output is None and not inside:  # no proposal answered yes: an act not seen by the verb's name; no output seen: not written as done
        return ctx.log("not_seen", dict(base, act=pre.get("act"), outcome=out, what=f"the verb '{v.get('name')}' was tried with no proposal answered yes on the record"
                                        if not p else f"'{v.get('name')}' ran under proposal {p['proposal']}; its receipt was not seen, so it is not written as done"))
    if end == "post" and not inside and not output.strip() and parse_receipt(v, output)["value"] is None:  # an empty output is no receipt (Astra's audit)
        return ctx.log("not_seen", dict(base, act=pre.get("act"), outcome=out, what="ran, receipt not seen"))  # with its proposal, so the store spends the act
    got = pre.get("words_sha256")  # the yes covers its own words only (batch C's review); row 36's retry is the store's (retry_allowed)
    other = not inside and end in ("post", "failed") and (got is None or got != _covered(s, v, p, pre.get("shape")))
    words_of = dict(words_sha256=got, **({"other_words": OTHER} if other else {}))
    spend = lambda: [ctx.log("note", dict(base, event="not run", why=SPENT), about=vid) for _ in range(p["of"] - p["index"])] if other else None  # noqa: E731
    if end == "post":
        r = parse_receipt(v, output, folder=s.root)  # an output receipt keeps 80 characters inline and its whole output beside (Astra's audit, finding 8)
        keep, hid = (r["value"] is None or r["kind"] == "output") and output, find_secret(output or "")  # kept beside, never over a secret
        body = dict(base, answer=p["answer"], grant=p["grant"], act=p["index"], of=p["of"], form="other", receipt=r, **words_of, **({"why": OUT_SECRET} if hid else {}),
                    output={"payload": s.payload(output.encode(), unit=ctx.unit)} if keep and not hid else None)
        if find_secret(canonical(body)):  # check_body's own scan: the value itself matched a secret pattern, so it is not kept either
            body.update(receipt=dict(r, value=None), output=None, why=OUT_SECRET)
        rid = ctx.log("receipt", body, about=vid)  # then its links: came_from the proposal, and the answer or the grant
        [s.link(rid, "came_from", x, by=TOOL) for x in (p["proposal"], p["answer"] or p["grant"]) if x]
        p["undoes"] and s.link(rid, "supersedes", p["undoes"], by=TOOL)  # an undo is a new act: its receipt, once written, supersedes the one it takes back
        spend()  # other words spend the yes: each act it had left, a note that it did not run
        return rid
    if end == "failed":
        hid, line = output is not None and find_secret(output), (str(output or "").strip().splitlines() or [""])[0][:80]  # Astra's audit, finding 8:
        w = None if output is None else WORDS_SECRET if hid else line  # 80 characters of the first line inline, the command's text already its shape
        beside = {"payload": s.payload(output.encode(), unit=ctx.unit)} if output is not None and not hid and output.strip() != line else None
        n = ctx.log("note", dict(base, event="failed", answer=p["answer"], grant=p["grant"], words=w, output=beside, retry=p["failures"] + 1 if not other else None,
                                 act_sha256=pre.get("act_sha256"), **words_of), about=vid)
        spend()
        return n
    return ctx.log("note", dict(base, event="not run", why="refused in the host's prompt"), about=vid)

def resolve(ctx, missing=None):
    """Reads what each call came to from its own lines, by its call id: each ask's answer (ran, did not run, else the missing word), each
    five-act call no ask came before, and each act outside any grant; the second act of a kind in one session raises a card; each act no line names, unseen (_act)."""
    rows = [r for r in ctx.rows if r["kind"] == "hook"]
    calls = {}
    for i, r in enumerate(rows):
        b = r["body"]
        if b.get("call_id") and b.get("phase") in ("pre", "post", "failed", "denied"):
            c = calls.setdefault(b["call_id"], {})
            c.update({"pre": b, "at": i} if b["phase"] == "pre" else {} if "end" in c else {"end": b["phase"], "end_at": i})
    told = {(l["body"].get("asked"), l["body"].get("ask") or l["body"].get("call_id")) for l in ctx.mine(["host_ask"])}
    taken = {r["body"]["call_id"] for r in rows if r["body"].get("phase") == "ask" and r["body"].get("call_id")} | \
            {l["body"].get("call_id") for l in ctx.mine(["host_ask"]) if l["body"].get("asked") is True}
    for i, a in ((i, r) for i, r in enumerate(rows) if r["body"].get("phase") == "ask" and (True, r["id"]) not in told):
        b, cid = a["body"], a["body"].get("call_id")
        if not cid:  # no call id: the first call of the same input whose end came after the ask, never an earlier one; else one still open
            later = sorted((c["end_at"], k) for k, c in calls.items() if k not in taken and c.get("pre", {}).get("input_sha256") == b["input_sha256"] and c.get("end_at", -1) > i)
            cid = later[0][1] if later else next((k for k, c in calls.items() if k not in taken and "end" not in c and c.get("pre", {}).get("input_sha256") == b["input_sha256"]), None)
            taken.add(cid)
        end = calls.get(cid, {}).get("end")
        answer = "ran" if end == "post" else "did not run" if end else missing
        answer and ctx.log("host_ask", {"event": b.get("event"), "tool": b.get("tool"), "input_sha256": b["input_sha256"], "act": b.get("act"), "asked": True,
                                        "answer": answer, "call_id": cid, "ask": a["id"]})
    hooked = any(r["kind"] == "held" or r["body"].get("via") == "hook" for r in ctx.rows)  # with no hook line at all, an ask could not be seen
    for cid, c in calls.items():
        pre, end = c.get("pre") or {}, c.get("end")
        if pre.get("act") and cid not in taken and not told & {(False, cid), (None, cid)} and (end or missing):
            ctx.log("host_ask", {"asked": False if hooked else None, "act": pre["act"], "tool": pre.get("tool"), "input_sha256": pre.get("input_sha256"), "call_id": cid,
                                 "answer": ("ran" if end == "post" else "did not run" if end else missing) if hooked else "not seen",
                                 "event": "no ask before the call" if hooked else "not seen: no hook ran in this session"})
    done = {l["body"].get("call_id") for l in ctx.mine(["host_ran"])}
    for cid, c in calls.items():
        pre, end = c.get("pre") or {}, c.get("end")
        if pre.get("needs") and not pre.get("act") and pre.get("grant") == "none" and cid not in done and (end or missing):
            ctx.log("host_ran", {"tool": pre.get("tool"), "input_sha256": pre.get("input_sha256"), "grant": "none", "act": pre["needs"], "call_id": cid,
                                 "outcome": RAN.get(end, missing), "unit": ctx.unit})
            same = [l["id"] for l in ctx.mine(["host_ran"]) if l["body"].get("act") == pre["needs"] and l["body"].get("grant") == "none"]
            if len(same) == 2:  # the second act of a kind outside any grant in one session comes back as a card, by the tool (it saw both), about the session
                ctx.log("card", dict(zip(("decides", "stand", "other", "wrong"), (CARD[0].format(kind=pre["needs"], unit=ctx.unit),) + CARD[1:]), about=ctx.sid,
                                     version=1, saw=f"two lines in session {ctx.sid}: {', '.join(same)}", answers=["yes", "no", "later"],
                                     purpose=f"outside-grant:{pre['needs']}"), by=TOOL)
    named = ctx.named()
    [_acts(ctx, c["pre"], c["end"], None) for k, c in calls.items() if c.get("end") and k not in named and ((c.get("pre") or {}).get("verb") or (c.get("pre") or {}).get("shape"))]


def _verb_act(store, seen):
    """Which of the five acts the call's first verb of one is, by the verb's own act facet, or None."""
    return next((x for a in seen.get("acts") or [seen] if a.get("verb") for x in [(store.verb(a["verb"]) or {}).get("act")] if x in ACTS), None)


def _bound(ctx, seen):
    """The pre line's binding (Astra's audit): the proposal and the answer (or grant) that stand for the verb when the act starts, so an
    answer given after it is never its consent; with no yes yet, both None."""
    def one(x):
        p = x.get("verb") and ctx.store.proposal_for(x["verb"], ctx.unit, act_sha256=x.get("act_sha256"))
        return dict(x, proposal=p and p["proposal"], answer=p and (p["answer"] or p["grant"])) if x.get("verb") else x
    return dict(one(seen), **({"acts": [one(x) for x in seen["acts"]]} if seen.get("acts") else {}))


def _pending(ctx, h=None):
    """The newest call still waiting (no end, no ask yet), of this input when h is given."""
    ended = {r["body"].get("call_id") for r in ctx.rows if r["body"].get("phase") in ("post", "failed", "denied", "ask")}
    return ([r["body"] for r in ctx.rows if r["body"].get("phase") == "pre" and r["body"].get("call_id") not in ended
             and (h is None or r["body"].get("input_sha256") == h)] or [None])[-1]


def _call(ctx, ev, name, state):
    tool, inp = ev["tool_name"], ev.get("tool_input") if isinstance(ev.get("tool_input"), dict) else {}
    h, phase, cid, act = ev.get("_sha256") or input_hash(inp), PHASE[name], ev.get("tool_use_id"), five_act(tool, inp)
    if name == "PermissionRequest":  # the ask, named by the call it waits on; its answer is read from that call's own end
        p = _pending(ctx, h)
        return ctx.sess(dict(state, event=name, tool=tool, input_sha256=h, act=act, phase="ask", call_id=cid or (p and p["call_id"])))
    if cid and any(r["body"].get("call_id") == cid and r["body"].get("phase") == phase for r in ctx.rows):
        return None  # seen twice, one line: host, session, call and phase
    kind, grant = needs(ctx.store.root, ctx.unit, tool, inp, places(ctx.store)), covering(standing_grants(ctx.store, ctx.unit), ctx.unit, tool, inp) or "none"
    seen = _bound(ctx, _matched(ctx.store, tool, inp, act, kind)) if phase == "pre" else {}
    act = act or _verb_act(ctx.store, seen)  # a verb's five act that the floor's table misses (Astra's audit); a five act has no grant
    grant = "none" if act else grant
    ctx.sess(dict(state, event=name, tool=tool, input_sha256=h, call_id=cid, phase=phase, grant=grant, outcome=OUTCOME.get(phase), act=act, needs=kind, **seen))
    if phase != "pre":  # the act's end, with the outside's words, before resolve reads what every call came to
        pre = next((r["body"] for r in ctx.rows if cid and r["body"].get("call_id") == cid and r["body"].get("phase") == "pre"), {})
        out = _text(ev.get("error") or ev.get("tool_response")) if phase == "failed" else _text(ev["tool_response"]) if phase == "post" and "tool_response" in ev else None
        cmd = str(inp.get("command") or "").strip() if phase == "failed" else ""  # a host that echoes the command: its span is the shape (Astra's audit)
        out = out.replace(cmd, " ".join(pre.get("shape") or [tool])) if cmd and out else out
        (pre.get("verb") or pre.get("shape")) and cid not in ctx.named() and _acts(ctx, pre, phase, out)
        return resolve(ctx)
    m = LOOPBACK.search(canonical(inp))
    m and ctx.log("note", {"event": "reached-pages", "tool": tool, "input_sha256": h, "address": m.group(0), "call_id": cid})
    tool == "AskUserQuestion" and ctx.log("host_ask", {"event": tool, "card": True, "tool": tool, "input_sha256": h, "call_id": cid})
    if act and ev.get("permission_mode") == "bypassPermissions":
        ctx.log("not_seen", {"what": f"the host does not prompt in this mode, so {act} was not asked by it", "call_id": cid})


def scope_read_back(ctx, adapter):
    """The user scope read back, never changed (design section 10 point 6): what it says that differs from the fence, a note by the tool in the
    session's unit once per host and day while its hash is the same (batch D's doctor reads it); a read that raises is one not_seen instead."""
    try:
        found = [{k: f[k] for k in ("scope", "key", "value", "differs", "what") if k in f} for f in adapter.read_back(ctx.store.root)]  # no value of the maker's
    except Exception as e:
        return ctx.log("not_seen", {"what": f"the user scope of {ctx.host} was not read back at this session's start ({type(e).__name__})"})
    day, h = local_date(ctx.store.clock()).isoformat(), input_hash(found)
    last = next((l["body"] for l in reversed(ctx.store.lines(kinds=["note"])) if (l["body"] or {}).get("event") == "scope read back"
                 and l["body"].get("host") == ctx.host), None)
    if not (last and last.get("day") == day and last.get("sha256") == h):
        ctx.log("note", {"event": "scope read back", "found": found, "differs": bool(found), "day": day, "sha256": h})

def _event(host, store, unit, ev, pid, table):
    adapter = importlib.import_module("sandbox_os.hosts." + host.replace("-", "_"))
    ev = adapter.normalise(ev) if hasattr(adapter, "normalise") else ev  # the host's own shapes into these (Codex's apply_patch an edit), hashed before
    name, sid = ev.get("hook_event_name"), ev.get("session_id")
    for bad, why in ((name not in getattr(adapter, "EVENTS", EVENTS), f"an unknown event: {str(name)[:60]}"), (not isinstance(sid, str) or not sid, "a missing field: session_id"),
                     (name in PHASE and not isinstance(ev.get("tool_name"), str), "an unknown tool: tool_name is not a name"),
                     (name == "UserPromptSubmit" and not isinstance(ev.get("prompt"), str), "a missing field: prompt")):
        if bad:
            raise Failure(why)
    ctx, state = Ctx(host, store, unit, sid), {}
    if ctx.surface is None:  # the first line of a session: its surface (ps once) and model, kept in the session's own file
        armed = {(l["body"] or {}).get("session") for l in store.lines(kinds=["night"]) if (l["body"] or {}).get("event") == "armed"}
        night = sid in armed or getattr(adapter, "night_of", lambda *a: None)(store, unit, ev)  # a host with no session id of the night's: the adapter binds it
        ctx.surface, ctx.model = "night" if night else surface_of(pid or os.getpid(), table), ev.get("model") if isinstance(ev.get("model"), str) else None
        state = dict({"surface": ctx.surface, "model": ctx.model}, **({"night": night} if isinstance(night, str) else {}))
    if name in PHASE:
        return _call(ctx, ev, name, state)
    ctx.sess(dict(state, event=name, phase="event", **({"notification_type": ev.get("notification_type")} if name == "Notification" else
                                                       {"cards_named": NAMED.findall(str(ev.get("last_assistant_message") or ""))} if name == "Stop" else {})))
    if name == "SessionStart":
        try:
            p = os.path.join(store.root, *getattr(adapter, "SETTINGS", (".claude", "settings.json")))
            open(p).close() if os.path.exists(p) else ctx.log("not_seen", {"what": "this session runs with no settings of this tool's"})
        except OSError as e:
            ctx.fail(name, "an unreadable config", e)
        ctx.log("session", {"event": "start", "host_version": adapter.version(ev.get("transcript_path")), "transcript": ev.get("transcript_path"),
                            "surface": ctx.surface, "source": ev.get("source"), "model": ctx.model, **{k: v for k, v in state.items() if k == "night"}})
        scope_read_back(ctx, adapter)
    elif name == "UserPromptSubmit":
        body = {"words": {"payload": store.payload(ev["prompt"].encode(), unit=unit)} if len(ev["prompt"].encode()) > TEXT_MAX else ev["prompt"], "surface": ctx.surface, "prompt_id": ev.get("prompt_id")}
        sender = getattr(adapter, "relayed", lambda p, t: None)(ev["prompt"], ev.get("transcript_path"))  # another session's message as a user turn (card 9)
        if ctx.surface == "terminal" and sender is None:  # what the command's binder needs (command/hook.py): the said line and the ids the last Stop named
            named = next((r["body"].get("cards_named") or [] for r in reversed(ctx.rows) if r["body"].get("event") == "Stop"), [])
            return {"root": store.root, "unit": unit, "host": host, "session": sid, "said": ctx.log("said", body, by=MAKER), "named": named}
        ctx.log("said", dict(body, event="prompt", **({"surface": "relayed", "from": sender} if sender is not None else {})), by=ctx.actor(kind="partner"))
    elif name == "Notification" and ev.get("notification_type") == "permission_prompt":
        p = _pending(ctx)  # a notification alone is the ask of the call still waiting, unless a request already asked it
        p and ctx.sess({"event": name, "tool": p["tool"], "input_sha256": p["input_sha256"], "act": p.get("act"), "phase": "ask", "call_id": p["call_id"]})
    elif name == "InstructionsLoaded":
        path = ev.get("file_path") if isinstance(ev.get("file_path"), str) else ""
        if re.search(r"/(agent-)?memory/", path) and os.path.isfile(path):  # the host's memory is material: path and hash, never a fact
            ctx.log("note", {"event": "memory-read", "path": path, "memory_type": ev.get("memory_type"), "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()})
    elif name in ("Stop", "SessionEnd"):
        if name == "SessionEnd":
            ctx.log("session", {"event": "end", "reason": ev.get("reason"), "surface": ctx.surface, "transcript": ev.get("transcript_path")})
        catch_up(host, ev.get("transcript_path"), store=store, missing="did not run", unit=unit, session=sid)

def handle(host, raw, cwd=None, pid=None, table=None):
    """One event in, lines out; never raises and never prints. pid is the hook's parent (the host); table a process table for tests."""
    store = unit = ev = None
    try:
        ev = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        where = locate(ev.get("cwd") if isinstance(ev.get("cwd"), str) else cwd or os.getcwd())
        if not where:
            return None  # a session outside any workshop: nothing is recorded
        store, unit = _open(where[0]), where[1]
        try:
            with store.locked(timeout=0.2):
                return _event(host, store, unit, ev, pid, table)
        except Busy:  # the record's lock held past 200 ms: a held line in the session's own file, and the hook goes on
            held = dict({k: v for k, v in ev.items() if k not in ("tool_input", "tool_response", "last_assistant_message")},
                        **({"input_sha256": input_hash(ev["tool_input"])} if isinstance(ev.get("tool_input"), dict) else {}))
            store.session_append(unit, ev.get("session_id"), "held", {"held": "the record's lock was busy past 200 ms", "event": held}, by=TOOL)
    except Exception as e:
        cause, ev = str(e) if isinstance(e, Failure) else "the hook crashed" if isinstance(ev, dict) else "malformed input", ev if isinstance(ev, dict) else {}
        try:
            where = (store.root, unit) if store and unit else locate(ev.get("cwd") if isinstance(ev.get("cwd"), str) else cwd or os.getcwd())
            s = where and (store or _open(where[0]))
            with s.locked(timeout=0.2):
                Ctx(host, s, where[1], None).fail(ev.get("hook_event_name"), cause, e)
        except Exception:
            pass  # a hook that cannot write shows at catch-up as calls with no hook line

def catch_up(host, transcript_path, *, store=None, missing="not seen", unit=None, session=None):
    """Fills in from the transcript every call no hook saw (via: transcript), names them, and reads every open ask's answer (else the missing word)."""
    adapter, path = importlib.import_module("sandbox_os.hosts." + host.replace("-", "_")), transcript_path if isinstance(transcript_path, str) else ""
    evs = adapter.events(None, [path] if path else [])
    sid = session or next((b["session"] for _, b in evs if b.get("session")), None) or os.path.basename(path)[:-6]
    where = locate(next((b.get("cwd") for _, b in evs if b.get("cwd")), None) or os.path.dirname(path)) or (store and unit and (store.root, unit))
    if not where:
        return {}
    s, added = store or _open(where[0]), {}
    units = {where[1]} | ({unit} - {None}) | {u for u in s.units() if sid and os.path.exists(os.path.join(s.unit_dir(u), "sessions", sid + ".jsonl"))}
    with s.locked(timeout=2.0):
        for u in sorted(units):
            ctx, standing, new = Ctx(host, s, u, sid), standing_grants(s, u), []
            seen, pres = {(r["body"].get("call_id"), r["body"].get("phase")) for r in ctx.rows}, {r["body"].get("call_id"): r["body"] for r in ctx.rows if r["body"].get("phase") == "pre"}
            for kind, b in ((k, dict(b)) for k, b in evs if (b.get("session") or sid) == sid):
                inp, pre = b.pop("_input", None), pres.get(b.get("call_id"), {})
                if kind == "hook" and b.get("call_id") and (b["call_id"], b["phase"]) not in seen:
                    b.update(act=five_act(b.get("tool"), inp), needs=needs(s.root, u, b.get("tool"), inp, places(s)), outcome=None, grant=covering(standing, u, b.get("tool"), inp)
                             or "none") or b.update(_matched(s, b.get("tool"), inp, b["act"], b["needs"])) or b.update(act=b["act"] or _verb_act(s, b)) if b["phase"] == "pre" else \
                        b.update(tool=pre.get("tool"), input_sha256=pre.get("input_sha256"), grant=pre.get("grant", "none"), act=pre.get("act"), outcome=OUTCOME[b["phase"]])
                    ctx.sess({k: v for k, v in b.items() if k not in ("cwd", "transcript")}, refresh=False)
                    seen.add((b["call_id"], b["phase"])), pres.update({b["call_id"]: b} if b["phase"] == "pre" else {})
                    new += [b["call_id"]] if b["phase"] == "pre" else []
                elif kind == "not_seen" and not any(l["body"].get("what") == b["what"] for l in ctx.mine(["not_seen"])):
                    ctx.log("not_seen", {k: v for k, v in b.items() if k not in ("cwd", "session")})
            for r in (r for r in ctx.rows if r["kind"] == "held" and not any(l["body"].get("held") == r["id"] for l in ctx.mine(["not_seen"]))):
                ctx.log("not_seen", {"what": f"a {r['body']['event'].get('hook_event_name')} the hook held while the record was busy; its line is in "
                                     "the session's own file", "held": r["id"]})
            new and ctx.log("hook", {"event": "catch-up", "failed": True, "cause": "calls the hooks did not see", "calls": new, "via": "transcript"})
            ctx.rows = session_lines(s, u, sid)
            resolve(ctx, missing)
            added[u] = new
    return added

def hook_main(host):
    """One event on standard input, lines out; returns handle's said line for command/hook.py to bind. As a file, it exits 0 and prints nothing."""
    try:
        return handle(host, sys.stdin.buffer.read(), os.getcwd(), os.getppid())
    except BaseException:
        return None

if __name__ == "__main__":
    try:
        hook_main(sys.argv[1] if len(sys.argv) > 1 else "claude-code")
    finally:
        os._exit(0)
