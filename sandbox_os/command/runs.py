# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""Runs: opened on a sentence, about the thing they concern and serving the goal they work toward; checks named at close and run by the
tool then, each with when it was named. A pass is computed from a check line with exit 0 and its output kept; an older run's acceptance
list, written before its first act and never edited, still reads as before. A run closes only with what it taught and what it changed;
an abandoned one with a line saying so; it is accepted only on the maker's yes; and the four set moments at which the partner asks find
before it acts. A check runs only inside the machine's own sandbox (sandbox-exec on a Mac): no write to the record, the grants, cache/,
the hosts' settings, the tool or the credentials, and no network; where there is none, it is not run."""
import hashlib, os, re, stat, subprocess

from sandbox_os.store import Refused
from sandbox_os.store.acts import GUESS_PERSON
from sandbox_os.store.line import canonical, iso, one_space, UNIT_RE
from sandbox_os.command import MAKER, TOOL, DOWN, cards, say

SANDBOX = "/usr/bin/sandbox-exec"
TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the installed tool's own folder (sandbox_os)
CREDENTIALS = ("~/.ssh", "~/.aws", "~/.config/gh", "~/.gnupg", "~/.netrc")
TEMP = ("/private/tmp", "/private/var/folders", "/dev")  # where a check may write besides its project's folder, as real paths
NONE = "no sandbox on this machine"  # why a check, or a verb's dry run, was not run: no sandbox with its profile starts here (starts)


def _ends(store, run_id):
    return [l for l in store.lines(kinds=["close", "abandoned"]) if (l["body"] or {}).get("run") == run_id and l["mark"] not in DOWN]


def _list(store, run_id):
    acc = [l for l in store.lines(kinds=["acceptance"]) if (l["body"] or {}).get("run") == run_id]
    return acc[0]["body"]["checks"] if acc else []


def _old(store, run_id):
    """Whether a run is an older one, opened with an acceptance list."""
    return any((l["body"] or {}).get("run") == run_id for l in store.lines(kinds=["acceptance"]))


def open_(store, unit, sentence, *, by, about=None, serves=None, assumptions=()):
    """A run line on a sentence, about the thing it concerns and serving the goal it works toward; no acceptance list and no named
    check. Each assumption is written before its first act by knowing.assume, about the same thing, the run citing it (run, came_from,
    assumption), so the store's person rule reaches it; then the moment at its start. An assumption about a person is a guess written
    before work, refused before the run line is written, so nothing is half opened."""
    from sandbox_os.command import knowing
    with store.locked():
        t = store.get(about) if assumptions and isinstance(about, str) else None
        if t and t["kind"] == "object" and (t["body"] or {}).get("type") == "person":
            raise Refused(GUESS_PERSON)
        r = store.append(unit, "run", {"purpose": sentence}, by=by, about=about)
        serves and store.link(r, "serves", serves, by=by)
        for text in assumptions:
            knowing.assume(store, unit, text, by=by, about=about, run=r)
        moment(store, "run-start", unit, sentence, by=by)
    return r


def acceptance(store, run_id, checks, *, by):
    """Refused always: an older run's list was written once, before its first act, and never edited; a new run names its checks at close."""
    raise Refused(say("check.acceptance"))


def profile(root, unit=None):
    """The sandbox a check runs in: everything else allowed; no network; no write under any project's record, .claude or .codex, the grants
    files, the workshop's cache/, .claude, .codex and .mcp.json, the tool's own folder, the credential paths, or any .env file. With a unit
    (the check's fence, R-READ-4), every write is denied, then allowed in the temp folders, denied anywhere in the workshop (which may sit in
    one), allowed in projects/<unit>, and the list above denied last; in a profile the last rule that matches wins. A unit the store's pattern
    does not match is refused, and every path and pattern is quoted text with its backslashes and quotes escaped, so no name or path adds a rule."""
    if unit is not None and not (isinstance(unit, str) and UNIT_RE.match(unit)):
        raise Refused(say("check.unit", name=repr(str(unit)[:64])))
    root = os.path.realpath(root)
    r, q = re.sub(r"([.^$|?*+()\[\]{}\\])", r"\\\1", root), lambda t: '"' + t.replace("\\", "\\\\").replace('"', '\\"') + '"'
    paths = [*(f"(regex {q(x)})" for x in (f"^{r}/projects/[^/]+/(record|\\.claude|\\.codex)(/|$)", f"^{r}/(projects/[^/]+/)?grants\\.md$",
                                          f"^{r}/(cache|\\.claude|\\.codex)(/|$)", "/\\.env(\\.[^/]*)?$")),
             f"(literal {q(root + '/.mcp.json')})", *(f"(subpath {q(p)})" for p in (TOOL_DIR, *map(os.path.expanduser, CREDENTIALS)))]
    fence = "" if unit is None else ("(deny file-write*)\n(allow file-write* " + " ".join(f"(subpath {q(t)})" for t in TEMP) + ")\n"
                                     f"(deny file-write* (subpath {q(root)}))\n(allow file-write* (subpath {q(root + '/projects/' + unit)}))\n")
    return "(version 1)\n(allow default)\n(deny network*)\n" + fence + "(deny file-write*\n  " + "\n  ".join(paths) + ")\n"


PROJECTED = ("record", "pages", "cache", ".git", "where-it-stands.md", "grants.md")  # what the tool writes in a unit's folder, never the work
LEFT_OUT = PROJECTED + ("play",)  # and play/, which nothing reads (R-STORE-PLAY-1; the review of batch E, finding 11c)


BOUND = (2000, 32 << 20)  # the files and bytes whose contents a state reads; past either, a file counts by its size and mtime only


def _content(path, budget):
    """A file's part of a state: a regular file's contents' sha256 while the budget [files, bytes] lasts, else (and for a link or another
    kind) its size and mtime_ns; a regular file past the budget sets budget[0] to -1, so the state says bounded."""
    st = os.lstat(path)
    regular = stat.S_ISREG(st.st_mode)
    if regular and budget[0] > 0 and budget[1] >= st.st_size:
        budget[0], budget[1] = budget[0] - 1, budget[1] - st.st_size
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest().encode()
    budget[0] = -1 if regular else budget[0]
    return f"{st.st_size}\0{st.st_mtime_ns}".encode()


def state(folder):
    """The folder's state before a check runs (batch E, Task 15; the review of batch E, finding 4): where the folder is a git repository's own
    top, its commit (rev-parse HEAD) and a hash over the commit, the index's and the tree's changes as binary diffs (git diff --cached and
    git diff), and each untracked file's path and contents (past BOUND, its size and mtime_ns, and the state says bounded), so a second edit
    to a changed or untracked file is a new state; files git ignores are left out, unseen, as are what the tool projects and play/, which
    nothing reads (finding 11c). Elsewhere commit None and a hash over the sorted path and contents of its files, each past BOUND by its size
    and mtime_ns (the state then says bounded), leaving out the same."""
    git = lambda *a: subprocess.run(["git", "-C", folder, *a], capture_output=True, timeout=60, check=True).stdout
    spec = ["--", ".", *[f":(exclude){x}" for x in LEFT_OUT]]
    budget = list(BOUND)
    try:
        top = os.path.realpath(git("rev-parse", "--show-toplevel").decode().strip()) == os.path.realpath(folder)
        commit = git("rev-parse", "HEAD").decode().strip() if top else None
        rows = b"\0".join([commit.encode(), *(git("diff", *c, "--binary", "--no-ext-diff", "--no-textconv", "--no-color", *spec)
                                              for c in (["--cached"], [])),
                           *(p + b"\0" + _content(os.path.join(folder, p.decode()), budget) for p in sorted(
                               git("ls-files", "--others", "--exclude-standard", "-z", *spec).split(b"\0")) if p)]) if commit else None
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        commit = rows = None
    if rows is None:
        out, budget = [], list(BOUND)
        for d, dirs, files in os.walk(folder):
            top = os.path.samefile(d, folder)
            dirs[:] = sorted(x for x in dirs if x != ".git" and not (top and x in LEFT_OUT))
            for f in sorted(x for x in files if not (top and x in LEFT_OUT)):
                out.append(os.path.relpath(os.path.join(d, f), folder).encode() + b"\0" + _content(os.path.join(d, f), budget))
        rows = b"\n".join(sorted(out))
    return {"commit": commit, "files_sha256": hashlib.sha256(rows).hexdigest(), **({"bounded": True} if budget[0] < 0 else {})}


def starts(prof):
    """Whether a sandbox with this profile starts here, tried on /usr/bin/true before a check or a verb's dry run is run in it."""
    try:
        return subprocess.run([SANDBOX, "-p", prof, "/usr/bin/true"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def check(store, run_id, name, command, *, named_at=None):
    """The tool runs a check in the unit's folder inside the machine's sandbox, fenced to that folder and the temp folders, and keeps its
    output beside the record, the receipt naming the profile by its hash; with no sandbox that starts here it is not run, and says so. A check
    named at close carries when it was named (named_at), from which the index tells whether it went green before; on an older run, a name
    not on its list carries its time."""
    run = store.get(run_id)
    prof = profile(store.root, run["unit"])
    body = {"run": run_id, "name": name, "command": command, "exit": None, "text": "not run: " + NONE}
    if starts(prof):
        folder = os.path.join(store.root, "projects", run["unit"])
        before = state(folder)  # taken before the command runs, so a red check can be read for its cause
        p = subprocess.run([SANDBOX, "-p", prof, "/bin/sh", "-c", command], cwd=folder, capture_output=True, timeout=600)
        sha, out = store.payload(prof.encode(), unit=run["unit"]), p.stdout + p.stderr or b"(no output)"
        if p.returncode and b"Operation not permitted" in out:  # a refusal, as the system words it (R-READ-5): said once, last, as the tool's
            out = out.rstrip(b"\n") + b"\n" + say("check.fence").encode() + b"\n"
        body = {"run": run_id, "name": name, "command": command, "exit": p.returncode, "output": {"payload": store.payload(out, unit=run["unit"])},
                "sandbox": {"ran": "sandboxed by sandbox-exec", "profile_sha256": sha, "profile": {"payload": sha}}, "state": before}
    if named_at is not None:
        body["named_at"] = named_at
    if _old(store, run_id) and name not in {c["name"] for c in _list(store, run_id)}:
        body["added_at"] = store.clock().isoformat()
    with store.locked():
        return store.append(run["unit"], "check", body, by=TOOL)


def passes(store, run_id, named=None):
    """Each check's pass, computed at read from the tool's check lines. An older run: each listed check, exit 0, output kept, the same
    command as listed. A closed run (or one closing, its checks given as named): each check named at close, true when the newest standing
    check line of that name and that command (whitespace made single) exited 0 with its output kept, so a name run again with another
    command stands for nothing. An open run: each name it checked, by its newest standing check line."""
    mine = [l for l in store.lines(kinds=["check"]) if (l["body"] or {}).get("run") == run_id and l["mark"] not in DOWN]
    green = lambda b: b.get("exit") == 0 and isinstance(b.get("output"), dict)
    if _old(store, run_id):
        ok = {(l["body"]["name"], l["body"]["command"]) for l in mine if green(l["body"])}
        return {c["name"]: (c["name"], c["command"]) in ok for c in _list(store, run_id)}
    end = next((l for l in reversed(store.lines(kinds=["close"])) if (l["body"] or {}).get("run") == run_id and l["mark"] not in DOWN), None)
    named = named if named is not None else ((end or {}).get("body") or {}).get("checks") if end else None
    newest = {}
    for l in mine:
        newest[(l["body"].get("name"), one_space(l["body"].get("command"))) if named is not None else l["body"].get("name")] = l
    if named is None:
        return {n: green(l["body"]) for n, l in newest.items()}
    return {c["name"]: (c["name"], one_space(c["command"])) in newest and green(newest[(c["name"], one_space(c["command"]))]["body"]) for c in named}


def settled(store, run_id):
    """What the run's thing rests on, settled by the maker, each yes read by the rule a card's own decision uses (cards.decision, his newest
    binding answer to the card; the review of batch E, finding 8): the run's own body.settled_by when it names his binding yes that is still
    his card's decision, or his standing accept; else the newest such yes about the run's thing (the answer's own about, or its card's), or
    his standing accept of a run about that thing; else None, so his later no on the same card un-settles it. A settled_by naming anything
    else (a partner's line, a no) is ignored. A run about no thing has nothing to rest on, so None."""
    run = store.get(run_id) or {}
    yes = lambda a: bool(a and a["kind"] == "answer" and cards.binds(a) and (a["body"] or {}).get("answer") == "yes"
                         and (cards.decision(store, a["body"].get("card")) or {}).get("id") == a["id"])
    his = lambda a: bool(a and a["kind"] == "accept" and a["by"]["kind"] == "maker" and a["mark"] not in DOWN)
    own = (run.get("body") or {}).get("settled_by")
    own = store.get(own) if isinstance(own, str) else None
    if yes(own) or his(own):
        return own["id"]
    thing = run.get("about")
    if not isinstance(thing, str):
        return None
    about = lambda c: c and (c.get("about") == thing or (c.get("body") or {}).get("about") == thing)
    found = [l for l in store.lines(kinds=["answer", "accept"]) if l["id"] != run_id and (
        yes(l) and (l.get("about") == thing or about(store.get(l["body"].get("card") or ""))) if l["kind"] == "answer"
        else his(l) and (l.get("about") == thing or about(store.get((l["body"] or {}).get("run") or ""))))]
    return found[-1]["id"] if found else None


def _part_of(store, ids, run_id, by):
    for i in ids:
        store.link(i, "part_of", run_id, by=by)


def close(store, run_id, *, by, outcome, text, learned, changed, checks=(), ruling=None):
    """Closes a run with its two learning lines, what this taught and what it changed (a ruling links to the maker's answer); a close
    without both is refused. The checks that stand for what it claims are named here, each run by the tool now with one time of naming,
    and the close names each with its command and its receipt; one with no check stays not yet. Closing is not accepting: only the
    maker accepts. A run about a thing that nothing of his settled (settled) says so in its close, rests_on "nothing settled"."""
    if not (learned and changed):
        raise Refused("a run closes with what it taught and what it changed, both; one of them is missing, so it stays open")
    run, named_at = store.get(run_id), iso(store.clock())
    named = [{"name": x["name"], "command": x["command"], "check": check(store, run_id, x["name"], x["command"], named_at=named_at)}
             for x in checks]
    with store.locked():  # the two learning lines first, so the close names them (the store refuses a close that does not)
        l = store.append(run["unit"], "learned", {"run": run_id, "text": learned}, by=by)
        ch = store.append(run["unit"], "changed", dict({"run": run_id, "text": changed}, **({"ruling": ruling} if ruling else {})), by=by)
        body = {"run": run_id, "outcome": outcome, "text": text, "learned": l, "changed": ch, "named_at": named_at, "checks": named,
                "passes": passes(store, run_id, named)}
        if isinstance(run.get("about"), str) and settled(store, run_id) is None:  # the state test (batch E, Task 13): said, never refused
            body["rests_on"] = "nothing settled"
        if _old(store, run_id):
            body["checks_sha256"] = hashlib.sha256(canonical(_list(store, run_id)).encode()).hexdigest()
        c = store.append(run["unit"], "close", body, by=by)
        _part_of(store, (c, l, ch), run_id, by)
        ruling and store.link(ch, "came_from", ruling, by=by)
    return c


def abandon(store, run_id, *, by, tried, learned, changed):
    """An abandoned run closes with a line saying so and what it tried, with its two learning lines."""
    if not (learned and changed):
        raise Refused("an abandoned run still says what it taught and what it changed")
    run = store.get(run_id)
    with store.locked():
        l = store.append(run["unit"], "learned", {"run": run_id, "text": learned}, by=by)
        ch = store.append(run["unit"], "changed", {"run": run_id, "text": changed}, by=by)
        a = store.append(run["unit"], "abandoned", {"run": run_id, "tried": tried, "text": f"abandoned: {run['body'].get('purpose')}", "learned": l, "changed": ch}, by=by)
        _part_of(store, (a, l, ch), run_id, by)
    return a


def close_orphans(store, unit, *, by, since=None):
    """Every run of a unit opened since a session (or a night) began and still open when it ended is closed so, at the next start or the
    night's stop; runs older than that (an imported history among them) are not this session's to close."""
    return [abandon(store, r["id"], by=by, tried=say("run.orphan.tried"), changed=say("run.orphan.changed"), learned=say("run.orphan.learned"))
            for r in store.lines(unit=unit, kinds=["run"], since=since) if r["mark"] not in DOWN and not _ends(store, r["id"])]


def accepted(store, run_id):
    return any(l["by"]["kind"] == "maker" and l["mark"] not in DOWN for l in store.lines(kinds=["accept"]) if (l["body"] or {}).get("run") == run_id)


def accept(store, run_id, *, by, answer):
    """Accepts a run, only from the maker's own yes to a card about it (or a grant of his that says so): never on the partner's word."""
    a = store.get(answer) if isinstance(answer, str) else None
    card = store.get((a or {}).get("body", {}).get("card") or "")
    if not (a and a["kind"] == "answer" and a["by"]["kind"] == "maker" and a["body"].get("answer") == "yes" and card and card["body"].get("about") == run_id):
        raise Refused("a run is accepted only by the maker's yes on a card about it; the partner closes, it never accepts")
    with store.locked():
        return store.append(store.get(run_id)["unit"], "accept", {"run": run_id, "answer": answer}, by=MAKER)


def moment(store, at, unit, purpose, *, by):
    """A set moment (run-start, before-card, before-act, before-ruling): find asked with the purpose; the maker's own rulings on this unit
    and purpose applied, any other shown as may apply with because, each by the rule a card's own decision uses (cards.binds: the maker's,
    standing, someone at the desk, not stale, a person established); a moment line naming the query, and a recall line counting it."""
    applied, may, struck = [], [], 0
    for h in store.find(purpose, kinds=["card"], limit=50)["hits"]:
        card = store.get(h["id"])
        if (card["body"] or {}).get("purpose") != purpose:
            continue
        for a in (a for a in store.lines(unit=card["unit"], kinds=["answer"]) if a["body"].get("card") == card["id"] and a["by"]["kind"] == "maker"):
            if a["body"].get("answer") == "later" or a["mark"] in ("superseded", "deleted", "erased"):
                continue
            if a["mark"] == "struck":
                struck += 1
            elif not cards.binds(a):
                continue
            elif card["unit"] == unit:
                applied.append(a["id"])
            else:
                may.append({"id": a["id"], "because": f"your ruling on {card['unit']} about the same purpose: {purpose}"})
    with store.locked():
        m = store.append(unit, "moment", {"at": at, "unit": unit, "purpose": purpose, "query": purpose, "applied": applied, "may_apply": may}, by=by)
        store.append(unit, "recall", {"moment": m, "applied": len(applied), "may_apply": len(may), "struck_matches": struck,
                                      "counts": "your rulings applied, others brought back as may apply, and struck matches, at this moment"}, by=TOOL)
    return m
