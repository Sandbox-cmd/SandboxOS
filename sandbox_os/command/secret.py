# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""Secrets (R-CMD-41 to 44; design.md section 7): set reads the value with echo off or from a pipe, never from the command line, keeps
it in the macOS Keychain through `security -i` on standard input (service sandbox-os, account <workshop>/<project>/<NAME>), reads it
back, and names any workshop file the value already appears in; list names, never values; erase deletes at once; use gives the value
to one child's environment. With no secret service it can use, it refuses, says why, records the refusal and writes no file. The
value is never printed, never in a line, never in an argument; `security` is the one program this part runs."""
import getpass, os, re, subprocess, sys

from sandbox_os.command import TOOL, options, say

SECURITY, SERVICE = "/usr/bin/security", "sandbox-os"
NEED = {"set": 1, "list": 0, "erase": 1, "use": 1}


def _security(args, stdin=None):
    return subprocess.run([SECURITY, *args], input=stdin, capture_output=True, text=True, timeout=60)


def _q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _record(workshop, event, name, text, **extra):
    from sandbox_os import store as _store
    s = _store.open(workshop)
    with s.locked():
        return s.append("workshop", "note", dict({"event": event, "name": name, "text": text}, **extra), by=TOOL)


def _appears(workshop, value):
    """Every workshop file holding the value's bytes, the rebuildable cache and git's own folder aside."""
    hits, v = [], value.encode()
    for d, dirs, fs in os.walk(workshop):
        dirs[:] = sorted(x for x in dirs if not (x == ".git" or os.path.join(d, x) == os.path.join(workshop, "cache")))
        for f in sorted(fs):
            p = os.path.join(d, f)
            if os.path.isfile(p) and not os.path.islink(p) and os.path.getsize(p) < 8 << 20 and v in open(p, "rb").read():
                hits.append(p)
    return hits


def main(argv, *, workshop=None, out=print):
    sub, rest = (argv[0], list(argv[1:])) if argv else (None, [])
    cmd = rest[rest.index("--") + 1:] if "--" in rest else []
    rest = rest[:rest.index("--")] if "--" in rest else rest
    opts, args = options(rest, {"--project": "workshop", "--keychain": None})
    if sub == "set" and len(args) > 1:
        out(say("cli.secret.argv"))
        return 2
    if sub not in NEED or len(args) != NEED[sub] or (sub == "use") != bool(cmd) or any(a.startswith("-") for a in args):
        out(say("cli.secret.usage") if argv else say("cli.secret.what") + "\n" + say("cli.secret.usage"))
        return 2
    if not workshop:
        out(say("cli.noworkshop"))
        return 1
    kc, name = [opts["--keychain"]] if opts["--keychain"] else [], args[0] if args else None
    account = f"{workshop}/{opts['--project']}/{name}"
    p = _security(["show-keychain-info", *kc]) if os.path.exists(SECURITY) else None
    if p is None or p.returncode:
        why = (p.stderr.strip() or f"exit {p.returncode}") if p else "the macOS security command is not on this machine"
        out(say("cli.secret.none", why=why))
        _record(workshop, "secret-refused", name, say("cli.secret.line.refused", name=name or "", why=why), why=why)
        return 1
    if sub == "list":
        found = [m.group(1) for b in _security(["dump-keychain", *kc]).stdout.split("keychain: ")
                 if f'"svce"<blob>="{SERVICE}"' in b for m in [re.search(r'"acct"<blob>="(.*)"', b)] if m]
        mine = [a for a in found if a.startswith(workshop + "/")]
        for a in mine:
            out(say("cli.secret.item", name=a.rsplit("/", 1)[1], account=a))
        out(say("cli.secret.empty")) if not mine else None
        return 0
    if sub == "set":
        value = getpass.getpass(say("cli.secret.ask", name=name)) if sys.stdin.isatty() else sys.stdin.readline().rstrip("\n")
        if not value or "\n" in value or "\r" in value:
            out(say("cli.secret.oneline"))
            return 1
        _security(["-i"], f"add-generic-password -U -s {SERVICE} -a {_q(account)} -w {_q(value)} {' '.join(_q(k) for k in kc)}\n")
        back = _security(["find-generic-password", "-s", SERVICE, "-a", account, *kc])
        if back.returncode:
            why = back.stderr.strip() or "the Keychain did not read it back"
            out(say("cli.secret.none", why=why))
            _record(workshop, "secret-refused", name, say("cli.secret.line.refused", name=name, why=why), why=why)
            return 1
        out(say("cli.secret.kept", name=name, account=account))
        files = _appears(workshop, value)
        for f in files:
            out(say("cli.secret.found", name=name, path=f))
        _record(workshop, "secret-set", name, say("cli.secret.line.set", name=name), account=account, also_in=files)
        return 0
    if sub == "erase":
        p = _security(["delete-generic-password", "-s", SERVICE, "-a", account, *kc])
        if p.returncode:
            out(say("cli.secret.missing", name=name, why=p.stderr.strip()))
            return 1
        out(say("cli.secret.erased", name=name))
        _record(workshop, "secret-erased", name, say("cli.secret.line.erased", name=name), account=account)
        return 0
    p = _security(["find-generic-password", "-s", SERVICE, "-a", account, "-w", *kc])
    if p.returncode:
        out(say("cli.secret.missing", name=name, why=p.stderr.strip()))
        return 1
    return subprocess.run(cmd, env=dict(os.environ, **{name: p.stdout.rstrip("\n")})).returncode
