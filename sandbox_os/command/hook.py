# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The host's hook entry, `<python> <tree>/sandbox_os/command/hook.py <host>` and `sandbox hook <host>`: the shared boundary records the
event (boundary.handle, as hook_main does); when it wrote a terminal said line it hands back {"root", "unit", "session", "said", "named"},
and the conversation's answer binding runs here (cards.answer_from_said), since the hosts part may not import the command. At every event
of a session, the binds a busy lock held are tried again first; at a session's start and at its end the read is written (handed), and at
a start the maker's flagged object is recorded first when the workshop has its welcome and not yet the object. Never
raises, never prints, exits 0."""
import json, os, re, sys

if __package__ in (None, ""):  # run by the host as a file: the tree in place of this folder at the head of the path
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def bind(host, root, unit, session, new=None):
    """The session's held binds that no answer or unbound note has settled yet, then the new one, under the record's lock waited for 200 ms;
    past that the new one is held in the session's own file (once), and the held ones stay held for the next event."""
    from sandbox_os import store as _store
    from sandbox_os.command import TOOL, cards
    from sandbox_os.hosts.boundary import session_lines
    held = [r["body"]["bind"] for r in session_lines(_store.open(root, read_only=True, machine="hook"), unit, session)
            if r["kind"] == "held" and isinstance((r["body"] or {}).get("bind"), dict)]
    if not held and not new:
        return
    s = _store.open(root)
    try:
        with s.locked(timeout=0.2):
            done = {(l["body"] or {}).get("said") for l in s.lines(kinds=["answer", "note"]) if l["kind"] == "answer" or (l["body"] or {}).get("event") == "answer-unbound"}
            for b in held + ([new] if new else []):
                if b.get("said") and b["said"] not in done:
                    cards.answer_from_said(s, b["said"], host=host, session=session, named=list(b.get("named") or []))
                    done.add(b["said"])
    except _store.Busy:
        if new:
            s.session_append(unit, session, "held", {"held": "the record's lock was busy past 200 ms", "bind": {"said": new["said"], "named": new.get("named")}}, by=TOOL)
    finally:
        s.close()


def handed(host, root, unit, event="SessionStart"):
    """The read of the session's things written for its unit and at the workshop's root (on Codex, the block placed again to carry it; on Claude
    Code, the cut of the charter and the book, and the block refreshed to import it, card 31), at a session's start and at its end
    (ruling row 32); a read that cannot be written, or a hand edit to it the store refused (the read written again all the same), is a
    failed hook line carrying the sentence, never the edit's words, the lock waited for 200 ms, else dropped."""
    from sandbox_os import store as _store
    from sandbox_os.command import TOOL, say
    from sandbox_os.pages import write
    refused, failed = [], None
    try:
        if event == "SessionStart" and os.path.exists(os.path.join(root, "welcome.md")):  # his object on first need, by the tool, once
            s = _store.open(root)
            try:
                write.maker_object(s)
            finally:
                s.close()
        write.write_read(root, unit, refused=refused)
        from sandbox_os.hosts import claude_code, codex
        codex.instruction_file(root) if host == "codex" else claude_code.refresh(root)
    except Exception as e:
        failed = ("the read could not be written", f"{type(e).__name__}: {str(e)[:200]}")
    if refused and not failed:
        failed = (say("hook.read.refused"), " ".join(f"{file}: {why}" for _, file, why in refused)[:400])
    if failed:
        s = _store.open(root)
        try:
            with s.locked(timeout=0.2):
                s.append(unit, "hook", {"failed": True, "event": event, "cause": failed[0], "error": failed[1], "exit": 0, "host": host}, by=TOOL)
        except _store.Busy:
            pass
        finally:
            s.close()


KEYCHAIN = ("find-generic-password", "find-internet-password")


def _how(cmd, secrets):
    """How a shell command reads a secret and which one: a word whose basename is .env or starts .env. ("a .env path"), security
    find-generic-password or find-internet-password ("keychain by name", the secret its -s or -a value names), a word equal to a secret's
    lives_at ("a secret's name"); the first that holds, else (None, None)."""
    from sandbox_os.store.verbs import simple
    cmds, lives = simple(cmd), {x["lives_at"]: x["id"] for x in secrets if isinstance(x["lives_at"], str)}
    ws = [w for c in cmds for w in c]
    env = next((w for w in ws if os.path.basename(w) == ".env" or os.path.basename(w).startswith(".env.")), None)
    kc = next((c for c in cmds if c[:1] == ["security"] and c[1:2] and c[1] in KEYCHAIN), None)
    if env:
        return ".env path", lives.get(env)
    if kc:
        return "keychain by name", next((lives[v] for o, v in zip(kc, kc[1:]) if o in ("-s", "-a") and v in lives), None)
    w = next((w for w in ws if w in lives), None)
    return ("a secret's name", lives[w]) if w else (None, None)


def secret_read(host, ev):
    """A shell read of a secret (design section 10 point 4), at a Bash call's PreToolUse once the boundary has recorded the call: a finding
    by the tool, about the secret when one matches, saying how it was read and never the command's words; nothing is refused, and the
    record's lock is waited for 200 ms, else the finding is dropped. The plan names it the boundary's _secret_read; the boundary was
    another builder's that night, so it runs from the hook's entry, which every host's hook runs (hook_command)."""
    import importlib
    from sandbox_os import store as _store
    from sandbox_os.command import TOOL
    from sandbox_os.hosts import boundary
    from sandbox_os.store.verbs import secrets
    adapter = importlib.import_module("sandbox_os.hosts." + host.replace("-", "_"))
    ev = adapter.normalise(ev) if hasattr(adapter, "normalise") else ev
    inp = ev.get("tool_input") if isinstance(ev.get("tool_input"), dict) else {}
    where = boundary.locate(ev.get("cwd") if isinstance(ev.get("cwd"), str) else os.getcwd())
    if not where or ev.get("hook_event_name") != "PreToolUse" or ev.get("tool_name") != "Bash" or not isinstance(inp.get("command"), str):
        return None
    s = _store.open(where[0])
    try:
        how, sid = _how(inp["command"], secrets(s))
        if how:
            with s.locked(timeout=0.2):
                return s.append(where[1], "finding", {"event": "secret read", "how": how, "secret": sid, "call_id": ev.get("tool_use_id"),
                                                      "input_sha256": ev.get("_sha256") or boundary.input_hash(inp), "host": host,
                                                      "session": ev.get("session_id")}, by=TOOL, about=sid)
    except _store.Busy:
        return None
    finally:
        s.close()


def main(host):
    try:
        from sandbox_os.hosts import boundary
        raw = sys.stdin.buffer.read()
        said = boundary.handle(host, raw, os.getcwd(), os.getppid())
        ev = json.loads(raw)
        where = boundary.locate(ev.get("cwd") if isinstance(ev.get("cwd"), str) else os.getcwd())
        if where and ev.get("hook_event_name") == "PreToolUse":
            secret_read(host, ev)
        if where and ev.get("hook_event_name") in ("SessionStart", "SessionEnd"):
            handed(host, *where, event=ev["hook_event_name"])
        if where and isinstance(ev.get("session_id"), str) and re.fullmatch(r"[\w.-]{1,128}", ev["session_id"], re.A):
            bind(host, *where, ev["session_id"], said if isinstance(said, dict) else None)
    except BaseException:
        pass  # a hook that cannot bind leaves the said line as it is; the brief shows it unanswered
    finally:
        os._exit(0)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "claude-code")
