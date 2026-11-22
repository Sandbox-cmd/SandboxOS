# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The weekly measure lines and the kill rule's card (R-MEASURE-01, 11, 12): the eight measures of a week that has ended, kept once as
`measure` lines by the tool from the pages' functions over lines; the baseline's lines over the four weeks before the import, once, with
the export's hash; after two zero weeks of M7 in a row over the host projects, one card asking whether to pause, which pauses nothing;
and the hook `sandbox` and the doctor call, with the tool's own units read from home.json's tool_units. Calibration and his corrections
by basis are the pages' own functions, imported here, since the pages may not import the command."""
import datetime as _dt

from sandbox_os import store as _store
from sandbox_os.store import Refused
from sandbox_os.store.line import iso
from sandbox_os.command import TOOL, DOWN, cards
from sandbox_os.pages.measures import calibration, corrections  # noqa: F401

KEYS = ("value", "unit", "counts", "kinds", "formula", "how")
PURPOSE = "kill-rule"


def _monday(week):
    y, w = week.split("-W")
    return _dt.date.fromisocalendar(int(y), int(w), 1)


def _today(store):
    return _dt.date.fromisoformat(cards.local_day(iso(store.clock())))


def ended(store):
    """The ISO weeks of the maker's local days from the workshop's first day to the last week that has ended, oldest first."""
    from sandbox_os.pages import measures as M
    since = (store.home or {}).get("since")
    day, today, out = _dt.date.fromisoformat(cards.local_day(since)) if since else None, _today(store), []
    while day and day + _dt.timedelta(days=6 - day.weekday()) < today:
        out.append(M.iso_week(day))
        day += _dt.timedelta(days=7 - day.weekday())
    return out


def record_week(store, week, *, by=TOOL, tool=None):
    """One measure line per measure for a week that has ended, written once: a measure the week already holds is never written again; a
    week still running is refused, since its count would still move. Returns the ids written."""
    from sandbox_os.pages import measures as M
    if _monday(week) + _dt.timedelta(days=6) >= _today(store):
        raise Refused(f"{week} has not ended on your local days; its measures are recorded once it has")
    with store.locked():
        have = {(l["body"] or {}).get("measure") for l in store.lines(kinds=["measure"]) if (l["body"] or {}).get("week") == week
                and not l["body"].get("export_sha256")}
        table = M.week_table(store, week, tool=tool) if tool else M.week_table(store, week)
        return [store.append("workshop", "measure", dict({"measure": name, "week": week}, **{k: m.get(k) for k in KEYS}), by=by)
                for name, m in sorted(table.items()) if name not in have]


def record_baseline(store, *, by=TOOL):
    """The baseline (R-MEASURE-11): one measure line per measure per week of the four complete weeks before the import, from the pages'
    baseline over the move line that carries the export's hash, each with that hash and its how naming the proxy read; written once."""
    from sandbox_os.pages import measures as M
    b = M.baseline(store)
    if not b:
        return []
    with store.locked():
        have = {(l["body"]["week"], l["body"]["measure"]) for l in store.lines(kinds=["measure"]) if (l["body"] or {}).get("export_sha256") == b["export_sha256"]}
        named = lambda n, m: m["how"] if b["proxies"][n] in m["how"] else f"{m['how']}; proxy: {b['proxies'][n]}"  # noqa: E731
        return [store.append("workshop", "measure", {"measure": name, "week": week, **{k: m.get(k) for k in KEYS}, "how": named(name, m),
                                                     "export_sha256": b["export_sha256"]}, by=by)
                for week in b["weeks"] for name, m in sorted(b["table"][week].items()) if (week, name) not in have]


def _zero(m7):
    """Whether a week's M7, as the kill rule reads it (the host projects only), counted nothing taken live."""
    v = ((m7 or {}).get("counts") or {}).get("kill_rule", (m7 or {}).get("value"))
    return not (isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0)


def kill_rule(store, *, by=TOOL, tool=None):
    """After the last two ended weeks both read zero on M7 over the host projects, one card by the tool asking whether to pause; it pauses
    nothing. Not raised while one stands unanswered; after a ruling older than those weeks, asked again naming it. Returns the card or None."""
    weeks = ended(store)[-2:]
    if len(weeks) < 2:
        return None
    for w in weeks:
        record_week(store, w, by=by, tool=tool)
    m7 = {l["body"]["week"]: l for l in store.lines(kinds=["measure"]) if (l["body"] or {}).get("measure") == "m7" and l["body"].get("week") in weeks}
    if not all(_zero(m7[w]["body"]) for w in weeks):
        return None
    mine = [c["id"] for c in store.lines(unit="workshop", kinds=["card"]) if (c["body"] or {}).get("purpose") == PURPOSE and c["mark"] not in DOWN]
    if any((cards.decision(store, c) or {"body": {"answer": "later"}})["body"].get("answer") == "later" for c in mine):
        return None  # one stands: unanswered, or answered later
    r = cards.ruling(store, "workshop", PURPOSE)
    changed = {"ruling": r["id"], "line": m7[weeks[-1]]["id"]} if r and cards.local_day(r["t"]) < _monday(weeks[0]).isoformat() else None
    return cards.raise_(store, "workshop", dict(
        cards.five("card.pause", lang=cards.language(store.root), first=weeks[0], second=weeks[1], a=m7[weeks[0]]["id"], b=m7[weeks[1]]["id"]), about="workshop", purpose=PURPOSE,
        **({"changed": changed} if changed else {})), by=by)


def catch_up(workshop, *, by=TOOL):
    """The hook `sandbox` (before it serves the pages) and the doctor call: the baseline when a move carries an export's hash and no baseline
    line is there, every ended week since the workshop began that lacks its lines, then the kill rule; the tool's own units from home.json."""
    s = workshop if hasattr(workshop, "lines") else _store.open(workshop)
    tool = (s.home or {}).get("tool_units") or None
    out = [] if any((l["body"] or {}).get("export_sha256") for l in s.lines(kinds=["measure"])) else record_baseline(s, by=by)
    out += [i for w in ended(s) for i in record_week(s, w, by=by, tool=tool)]
    k = kill_rule(s, by=by, tool=tool)
    from sandbox_os.command import growth  # the week's card after the kill rule (batch D, Task 7): his answers settled, then proposals, then the card
    g = growth.catch_up(s, by=by)
    return out + ([k] if k else []) + g["settled"] + g["queued"] + ([g["card"]] if g["card"] else [])
