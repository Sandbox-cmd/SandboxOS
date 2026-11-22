# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The night: one card with its limits, armed only on the maker's yes, the host started in its no-prompt mode with the day's settings,
the machine kept awake for the span only, stopped by TERM then KILL; the worker's loop that reads the grants before each step; the
partner's own tools tonight, which record a refused step as a line; and the brief's rows that name each attempt."""
import datetime as _dt
import os, subprocess, time, uuid

from sandbox_os.store import Refused
from sandbox_os.store.line import iso
from sandbox_os.command import TOOL, cards, mcp, runs, say
from sandbox_os.hosts import boundary, claude_code

LIMITS = ("touch", "not", "stops", "awake_until", "aside", "acceptance")
AWAKE = ("caffeinate", "-i", "-w", "{pid}")


def card(store, unit, limits, *, by):
    """The night's card: what it may touch and may not, when it stops (a time, rounds, the lid), that it asks nothing until morning, that
    it keeps the machine awake until then, that a piece needing the maker is set aside, and the run's acceptance list. A gap is refused."""
    missing = [k for k in LIMITS if not limits.get(k)] + [f"stops.{k}" for k in ("time", "rounds", "lid") if not (limits.get("stops") or {}).get(k)]
    if missing:
        raise Refused(f"a night's card names every limit; this one lacks {', '.join(missing)}, so no night was proposed")
    s = limits["stops"]
    return cards.raise_(store, unit, dict(limits, asks="nothing until morning", about=unit, purpose=f"night:{unit}:{iso(store.clock())}", **cards.five(
        "card.night", unit=unit, touch=", ".join(limits["touch"]), never=", ".join(limits["not"]), time=s["time"], rounds=s["rounds"], lid=s["lid"])), by=by)


def prompt(c):
    """The card's limits as the night's prompt; the card's id rides in it so the worker names it."""
    b = c["body"]
    return say("night.prompt", id=c["id"], unit=c["unit"], touch="; ".join(b["touch"]), no="; ".join(b["not"]), time=str(b["stops"]["time"]), rounds=str(b["stops"]["rounds"]),
               checks="; ".join(x["name"] + ": " + x["command"] for x in b["acceptance"]))


class Night:
    def __init__(self, store, card_id, session, proc, awake, out):
        self.store, self.card, self.session, self.proc, self.awake, self.out = store, card_id, session, proc, awake, out

    def output(self):
        return open(self.out, errors="replace").read() if os.path.exists(self.out) else ""


def arm(store, card_id, *, argv=None, cwd=None, awake=AWAKE):
    """Arms the night only after the maker's standing yes to its card: a night line (armed, the card, the stop time, the session), the
    host started as NIGHT with the day's settings and a session id of the night's own, and caffeinate for the host's span only."""
    c, d = store.get(card_id), cards.decision(store, card_id)
    if not c or not d or d["body"].get("answer") != "yes":
        raise Refused("a night starts only on the maker's yes to its card, and there is none; nothing was started")
    session, unit = str(uuid.uuid4()), c["unit"]
    with store.locked():
        store.append(unit, "night", {"event": "armed", "card": card_id, "session": session, "stop": c["body"]["stops"]["time"], "yes": d["id"]}, by=TOOL)
    out = os.path.join(store.root, "cache", "night", session + ".out")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    args = [a.format(prompt=prompt(c), settings=os.path.join(store.root, ".claude", "settings.json"), session=session) for a in argv or claude_code.NIGHT]
    with open(out, "w") as f:
        proc = subprocess.Popen(args, cwd=cwd or os.path.join(store.root, "projects", unit), stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT,
                                start_new_session=True)
    keep = subprocess.Popen([a.format(pid=proc.pid) for a in awake], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return Night(store, card_id, session, proc, keep, out)


def wait(n, timeout):
    """Waits for the night's host to finish, or for the time to run out."""
    end = time.monotonic() + timeout
    while n.proc.poll() is None and time.monotonic() < end:
        time.sleep(0.2)


def run(store, card_id, *, argv=None, cwd=None, awake=AWAKE, until=None, grace=60, transcript=None):
    """The runner: arms the night, waits for its host to finish or for the card's stop time (until, a datetime, for tests), then stops it."""
    n, c = arm(store, card_id, argv=argv, cwd=cwd, awake=awake), store.get(card_id)
    hh, mm = (int(x) for x in c["body"]["stops"]["time"].split(":"))
    now = _dt.datetime.now().astimezone()
    until = until or now.replace(hour=hh, minute=mm, second=0, microsecond=0) + _dt.timedelta(days=1 if (hh, mm) <= (now.hour, now.minute) else 0)
    wait(n, max(0.0, (until - now).total_seconds()))
    return n, stop(n, "done" if n.proc.poll() is not None else "time", grace=grace, transcript=transcript)


def stop(n, reason, grace=60, transcript=None):
    """Stops the night: TERM, then KILL after the grace; the keep-awake ended; a night line with the reason; the run still open closed as
    abandoned; and what the hooks missed filled in from the transcript, with the night's tokens."""
    killed = False
    if n.proc.poll() is None:
        n.proc.terminate()
        try:
            n.proc.wait(grace)
        except subprocess.TimeoutExpired:
            n.proc.kill()
            n.proc.wait()
            killed = True
    n.awake.poll() is None and n.awake.terminate()
    s, c = n.store, n.store.get(n.card)
    with s.locked():
        s.append(c["unit"], "night", {"event": "stopped", "reason": reason, "card": n.card, "session": n.session, "exit": n.proc.returncode, "killed": killed}, by=TOOL)
    armed = [l["t"] for l in s.lines(unit=c["unit"], kinds=["night"]) if l["body"].get("session") == n.session]
    runs.close_orphans(s, c["unit"], by={k: c["by"][k] for k in ("kind", "name", "model", "host")}, since=min(armed + [c["t"]]))
    if transcript:
        boundary.catch_up("claude-code", transcript, store=s, unit=c["unit"], session=n.session, missing="did not run")
        with s.locked():
            [s.append(c["unit"], "usage", u, by=TOOL) for u in claude_code.usage(None, [transcript])]
    return killed


class Tools:
    """The partner's own tools tonight, a caller of the MCP server's dispatch (the one path): each call records as the partner, and a
    refused call is a note by the tool saying what was refused and why, written before the refusal comes back here as Refused."""
    def __init__(self, store, unit, session, *, by):
        self.store, self.who = store, {"unit": unit, "session": session, "host": by.get("host"), "model": by.get("model")}

    def _do(self, name, args):
        r = mcp.dispatch(self.store.root, name, dict(args, **self.who))
        if not r["ok"]:
            raise Refused(r["refused"])
        return r["result"]

    def append(self, kind, body):
        return self._do(kind, body)

    def answer(self, card_id, answer, words=None):
        return self._do("answer_report", {"card": card_id, "answer": answer, "words": words})


def work(store, unit, pieces, *, by):
    """The worker's loop: before each step of each piece it reads the standing grants; a piece whose grant was taken back stops at its
    next step and comes back as a card, while the rest go on (row 46). Returns each piece's end: finished or stopped."""
    state = {p["name"]: "running" for p in pieces}
    for i in range(max(len(p["steps"]) for p in pieces)):
        for p in (p for p in pieces if state[p["name"]] == "running" and i < len(p["steps"])):
            if p.get("needs") and p["needs"] not in {g["id"] for g in boundary.standing_grants(store, unit)}:
                state[p["name"]] = "stopped"
                cards.raise_(store, unit, dict(cards.five("card.piece", name=p["name"], step=i + 1, grant=p["needs"]), about=unit, purpose="piece-stopped"), by=by)
                continue
            p["steps"][i]()
    return {k: "finished" if v == "running" else v for k, v in state.items()}


def trailer(run_id, by):
    """The trailer each night commit carries: the run and the partner, never the maker's name alone."""
    return f"Sandbox-Run: {run_id}\nSandbox-Partner: {by['name']} ({by.get('model')}, {by.get('host')})"


def attempts(store, unit, since):
    """The brief's rows for a night: each attempt the record holds since it was armed, what it was, and the lines that show it."""
    rows = []
    for l in store.lines(unit=unit, since=since):
        b, k = l["body"] or {}, l["kind"]
        what = (f"{b.get('act')} ({b.get('tool')}), outside any grant: {b.get('outcome')}" if k == "host_ran" and b.get("grant") == "none" else
                f"a hook failed: {b.get('cause')}" if k == "hook" and b.get("failed") else
                f"{b.get('act')} with no ask from the host ({b.get('answer')})" if k == "host_ask" and b.get("asked") is False else
                f"{b.get('act')} ({b.get('tool')}) was not seen: no hook ran in that session" if k == "host_ask" and b.get("asked") is None
                and b.get("answer") == "not seen" else
                "a grant written outside the read-back: it waits and covers nothing" if k == "grant" and store.grant_state(l["id"]) == "read_back"
                and not any((c["body"] or {}).get("about") == l["id"] for c in store.lines(kinds=["card"])) else
                "an answer not established as the maker's: it binds nothing" if k == "answer" and b.get("person") == "not established" else
                f"refused: {b.get('why')}" if k == "note" and b.get("event") == "refused" else
                f"the pages' address reached: {b.get('address')}" if k == "note" and b.get("event") == "reached-pages" else
                f"a card: {b.get('decides')}" if k == "card" and str(b.get("purpose")).startswith(("outside-grant", "piece-stopped")) else None)
        if what:
            rows.append({"t": l["t"], "what": what, "ids": [l["id"]], "kind": k})
    return rows


def not_seen_day(store, unit, host, day):
    """One line per host and day: what the host never shows (its COVERAGE) and the day's calls no hook saw, counted from the record."""
    if any((l["body"] or {}).get("day") == day and l["body"].get("host") == host for l in store.lines(unit=unit, kinds=["not_seen"])):
        return None
    gaps = sum(len(l["body"].get("calls") or []) for l in store.lines(unit=unit, kinds=["hook"]) if l["t"][:10] == day and l["body"].get("event") == "catch-up")
    with store.locked():
        return store.append(unit, "not_seen", {"host": host, "day": day, "always": list(claude_code.COVERAGE), "calls_without_hooks": gaps,
                                               "what": f"what {host} did not show on {day}"}, by=TOOL)
