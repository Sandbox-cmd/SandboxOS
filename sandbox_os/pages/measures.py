# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The sixteen measures (part 06, R-MEASURE-01 to 12; m9 to m16 from design section 12, R-WORLD-MEASURE-1 to 3), each one function over lines and never typed, naming the kinds it reads, its
formula, its unit and how it was got: "computed" over the tenth's own lines, "not seen" where nothing in the record could show it, or
"proxy: ..." over the ninth's imported lines (part 06's last column). A day is the maker's local day, a week an ISO week of those days;
an empty week reads "none this week"; an erased body may move a count and the measure says so in how. Beside them: the weeks a record
holds, the baseline over the last four complete weeks before the import (R-MEASURE-11), and the weekly behaviour check's sample and its
recording by a reader who wrote none of it (R-PARTNER-43). And calibration (design section 4 point 10): how often a belief marked likely or
unsure held, and his corrections counted by the basis of the line they corrected, over a window from month_start. The eight beside the
eight (batch D): likely held, questions expired unread, types and relations unused ninety days, acts not seen by verb, checks named after
their green, pages opened (from the pages server's own log, OPENED: a time and a view name a line, on this machine), needless, the budget.

    week_table(store, week, *, zone=None, tool=None) -> {"m1": {value, unit, counts, kinds, formula, how[, items]}, ..., "m16": ...}
    iso_week(day_or_t, zone=None) -> "yyyy-Www"     weeks(lines, *, now=None, zone=None) -> [{"week", "complete"}]
    last_week(now, zone=None)     baseline(store, *, zone=None)     behaviour_sample(lines, week)     behaviour_check(store, week, reader, *, by)
    calibration(store, *, since) -> {"likely": {"marked", "held", "fell"}, "unsure": {...}}     corrections(store, *, since) -> {basis: n}
    month_start(now, zone=None) -> the line time of the maker's local month's first midnight     midnight(day, zone=None) -> the same for one day
    pages_opened(root, mon, sun, zone=None) -> {"opens", "by_view", "days"}, or None when the pages have kept no log"""
import collections
import datetime as _dt
import functools
import json
import os
import re
import statistics

from sandbox_os.store import Refused
from sandbox_os.store.index import DOWN, OUT
from sandbox_os.store.line import BASES, canonical, iso, links_of, local_date
from sandbox_os.pages.frame import welcome_answers
from sandbox_os.pages.read import words_of
from sandbox_os.pages.words import Words, read_tsv

EN = Words("en")
NAMES = tuple(f"m{n}" for n in range(1, 17))
NONE, NOT_SEEN, UNPLACED = EN.raw("week.none"), "not seen", "unplaced"
LIMITS = {"little": 2, "some": 5, "often": None}
WEEK_RE = re.compile(r"\d{4}-W\d\d")
ADDRESS = re.compile(r"https?://[^\s\"'<>]+")
STARTS, ENDS, CLOSING = ("start", "open"), ("end", "close"), ("yes", "no", "words")
CONFIDENCE, SCORES = ("likely", "unsure"), BASES[:2]  # the two words a belief may carry; his word and a check, which score it
OPENED = os.path.join("cache", "pages-opened.jsonl")  # the pages server's log of opened views: a time and a view name, never leaving the machine
STAYED = ("did not run", "refused by the host")  # an act with one of these outcomes never left the machine (the views' own words)


@functools.lru_cache(maxsize=1 << 16)
def _ts(t):
    return _dt.datetime.fromisoformat(t)


@functools.lru_cache(maxsize=1 << 16)
def _day(t, zone):
    return local_date(_ts(t), zone)


def day_of(x, zone=None):
    """The maker's local day of a line's time (an ISO string or a datetime), or a date as it is."""
    if isinstance(x, _dt.datetime):
        return local_date(x, zone)
    if isinstance(x, _dt.date):
        return x
    return _day(x, zone) if "T" in x else _dt.date.fromisoformat(x)


def iso_week(day_or_t, zone=None):
    y, w, _ = day_of(day_or_t, zone).isocalendar()
    return f"{y}-W{w:02d}"


def bounds(week):
    """The Monday and the Sunday of an ISO week; a week that does not exist raises ValueError."""
    if not WEEK_RE.fullmatch(str(week)):
        raise ValueError(week)
    monday = _dt.date.fromisocalendar(int(week[:4]), int(week[6:]), 1)
    return monday, monday + _dt.timedelta(days=6)


def valid(week):
    try:
        return bool(bounds(week))
    except ValueError:
        return False


def last_week(now, zone=None):
    """The last complete week: the one before the week of today, the maker's local day."""
    return iso_week(day_of(now, zone) - _dt.timedelta(days=7))


def weeks(lines, *, now=None, zone=None):
    today = day_of(now or _dt.datetime.now(_dt.timezone.utc), zone)
    return [{"week": w, "complete": bounds(w)[1] < today} for w in sorted({iso_week(l["t"], zone) for l in lines})]


def imported(l):
    return isinstance((l.get("body") or {}).get("imported"), dict)


class Week:
    """One week's lines, split into the tenth's own and the ninth's imported, with what the measures share."""

    def __init__(self, lines, week, zone=None, tool=None, ninth=None, now=None):
        self.all, self.week, self.zone = lines, week, zone
        self.today = day_of(now or _dt.datetime.now(_dt.timezone.utc), zone)
        self.mon, self.sun = bounds(week)
        self.inn = [l for l in lines if self.mon <= _day(l["t"], zone) <= self.sun]
        self.tenth = [l for l in self.inn if not imported(l)]
        self.old = [l for l in self.inn if imported(l)]
        self.tool, self.forced = (sorted(tool) if tool else None), ninth
        midnight = _dt.datetime.combine(self.sun + _dt.timedelta(days=1), _dt.time())
        self.end = midnight.replace(tzinfo=zone) if zone else midnight.astimezone()

    def proxy(self, kinds):
        """True when the week is read through the ninth's lines: asked so, or none of the tenth's lines of these kinds and some imported."""
        if self.forced is not None:
            return self.forced
        return bool(self.old) and not any(l["kind"] in kinds for l in self.tenth)

    def of(self, kinds, pool):
        return [l for l in pool if l["kind"] in kinds]

    def day(self, l):
        return _day(l["t"], self.zone)

    def by_unit(self):
        out = collections.defaultdict(list)
        for l in self.all:
            out[l["unit"]].append(l)
        return out


def hours(a, b):
    return round((_ts(b) - _ts(a)).total_seconds() / 3600, 2)


def result(name, value, counts, kinds, how="computed", items=None, erased=0):
    if erased:
        counts["erased"] = erased
        how += "; " + EN.plain("measure.erased", lines=EN.count("line", erased))
    out = {"value": value, "unit": EN.raw(f"measure.{name}.unit"), "counts": counts, "kinds": list(kinds),
           "formula": EN.raw(f"measure.{name}.formula"), "how": how}
    if items is not None:
        out["items"] = items
    return out


def proxied(name):
    return "proxy: " + EN.raw(f"measure.{name}.proxy")


def gone(lines):
    return sum(1 for l in lines if l.get("body") is None)


def m1(W):
    """An idea (a unit's first line, or a bet) to its first preview or thing taken live; the ninth's ship or place naming an address."""
    proxy = W.proxy(("bet", "preview", "live"))
    if proxy:
        kinds = ("accept", "note")
        opens = [l for l in W.all if imported(l) and (l["kind"] == "accept" or (l["body"] or {}).get("event") == "place")]
        opens = [l for l in opens if ADDRESS.search(words_of(l) or "")]
    else:
        kinds = ("bet", "preview", "live")
        opens = [l for l in W.all if not imported(l) and ((l["kind"] == "preview" and (l["body"] or {}).get("event") in ("up", "opened"))
                                                        or (l["kind"] == "live" and (l["body"] or {}).get("address")))]
    firsts = {}
    for l in W.all:
        if l["unit"] != "workshop":
            firsts.setdefault(l["unit"], l)
    ideas = sorted(list(firsts.values()) + [l for l in W.all if l["kind"] == "bet"], key=lambda l: l["t"])
    per_unit = collections.defaultdict(list)
    for o in opens:
        per_unit[o["unit"]].append(o)
    took, unopened = [], []
    for i in ideas:
        if W.day(i) > W.sun:
            continue
        o = next((o for o in per_unit[i["unit"]] if o["t"] >= i["t"]), None)
        if o and W.mon <= W.day(o) <= W.sun:
            took.append(hours(i["t"], o["t"]))
        elif not o or W.day(o) > W.sun:
            unopened.append({"id": i["id"], "unit": i["unit"], "kind": i["kind"], "since": i["t"],
                             "hours": round((W.end - _ts(i["t"])).total_seconds() / 3600, 2)})
    counts = {"opened": len(took), "unopened": len(unopened), "ideas": len(took) + len(unopened)}
    if proxy:
        week_old = W.of(("accept", "note"), W.old)
        counts.update(ships=sum(1 for l in week_old if l["kind"] == "accept"), naming_an_address=sum(1 for o in opens if W.mon <= W.day(o) <= W.sun),
                      places=sum(1 for l in week_old if (l["body"] or {}).get("event") == "place"))
    value = round(statistics.median(took), 2) if took else NONE
    return result("m1", value, counts, kinds, proxied("m1") if proxy else "computed", unopened, gone(W.of(kinds, W.tenth)))


def m2(W):
    """Runs accepted, with your words kept exactly; the ninth's: your lines within a day after a make's close, as candidates."""
    if W.proxy(("accept",)):
        closes, near = [l for l in W.all if imported(l) and (l["kind"] == "close" or (l["body"] or {}).get("event") == "make-summary")], {}
        for c in closes:
            near.setdefault(c["unit"], []).append(c["t"])
        cands = [l for l in W.old if l["by"]["kind"] == "maker" and words_of(l) and any(0 < hours(t, l["t"]) <= 24 for t in near.get(l["unit"], ()))]
        items = [{"id": l["id"], "unit": l["unit"], "words": words_of(l), "lang": l.get("lang")} for l in cands]
        n_closes = sum(1 for c in closes if W.mon <= W.day(c) <= W.sun)
        return result("m2", len(cands) or NONE, {"candidates": len(cands), "closes": n_closes}, ("note", "close", "answer"), proxied("m2"), items)
    acc, closes = W.of(("accept",), W.tenth), W.of(("close",), W.tenth)
    items = [{"id": l["id"], "unit": l["unit"], "run": (l["body"] or {}).get("run"), "words": l["body"]["words"], "lang": l.get("lang")}
             for l in acc if isinstance((l["body"] or {}).get("words"), str) and l["body"]["words"]]
    value = len(acc) if acc or closes else NONE
    return result("m2", value, {"accepted": len(acc), "with_words": len(items), "closes": len(closes)}, ("accept", "close"),
                  items=items, erased=gone(acc + closes))


def m3(W, setting):
    """Cards per local day against the setting (none raised before a five act counted), answered, needless; asks per host; not seen."""
    kinds = ("card", "answer", "needless", "host_ask", "not_seen")
    if W.proxy(("card", "answer", "needless", "host_ask")):
        rulings = W.of(("answer",), W.old)
        keys = [l for l in W.old if "key_sha256" in (l["body"] or {})]
        return result("m3", len(rulings) or NONE, {"rulings": len(rulings), "keys": len(keys)}, ("answer", "session", "note"), proxied("m3"))
    cards = W.of(("card",), W.tenth)
    weekly = [c for c in cards if (c["body"] or {}).get("week_card")]  # the week's card of proposals, outside the budget (design section 2 point 4)
    counted = [c for c in cards if not (c["body"] or {}).get("before_act") and c not in weekly]
    per_day = collections.Counter(W.day(c).isoformat() for c in counted)
    cap = LIMITS.get(setting, 5)
    over = {d: n - cap for d, n in per_day.items() if cap is not None and n > cap}
    answers = collections.defaultdict(list)
    for a in W.all:
        if a["kind"] == "answer" and a.get("body"):
            answers[a["body"].get("card")].append(a)
    answered = [c for c in cards if any(a["by"]["kind"] == "maker" and a["body"].get("answer") in CLOSING and a["body"].get("presence") != "none"
                                        and not a["body"].get("stale") and a.get("mark") not in ("deleted", "erased", "struck") for a in answers[c["id"]])]
    calls, by_host = W.of(("host_ask",), W.tenth), collections.defaultdict(collections.Counter)
    asks = [a for a in calls if (a["body"] or {}).get("asked") in (True, False)]  # the host's line says it asked, or did not
    blind = [a for a in calls if (a["body"] or {}).get("asked") is None and (a["body"] or {}).get("answer") == NOT_SEEN]  # found at catch-up
    for a in asks:
        b = a["body"] or {}
        by_host[b.get("host") or a["by"].get("host") or UNPLACED][b.get("act") or "other"] += 1
    not_seen = collections.Counter((l["body"] or {}).get("host") or l["by"].get("host") or UNPLACED for l in W.of(("not_seen",), W.tenth) + blind)
    needless = W.of(("needless",), W.tenth)
    counts = {"cards": len(counted), "before_act": len(cards) - len(counted) - len(weekly), "week_card": len(weekly), "answered": len(answered),
              "needless": len(needless), "days_over": len(over), "over_by": sum(over.values()), "setting": setting, "cap": cap, "per_day": dict(sorted(per_day.items())),
              "asks": len(asks), "asks_by_host": {h: dict(sorted(c.items())) for h, c in sorted(by_host.items())}, "not_seen": dict(sorted(not_seen.items()))}
    value = len(counted) if cards or asks or needless else NONE
    return result("m3", value, counts, kinds, erased=gone(W.of(kinds, W.tenth)))


def m4(W, tool):
    """Sessions and their hours on the tool's own unit against the rest; sessions in no project (the workshop's own) unplaced."""
    proxy = W.proxy(("session",))
    pool = W.old if proxy else W.tenth
    began = lambda l: (l["body"] or {}).get("event") in STARTS or (imported(l) and (l["body"] or {}).get("event") not in ENDS)  # the import's
    starts = [l for l in W.of(("session",), pool) if began(l)]  # sessions whose bounds the ninth did not record count, with no hours
    units = W.by_unit()
    tally = collections.Counter()
    hours_of = collections.Counter()
    for s in starts:
        b, mine = s["body"], [l for l in units[s["unit"]] if l["kind"] == "session" and l["t"] >= s["t"] and l is not s]
        sid = b.get("session")
        end = next((l for l in mine if (l["body"] or {}).get("event") in ENDS and (sid is None or (l["body"] or {}).get("session") == sid)), None)
        nxt = next((l for l in mine if began(l)), None)
        if sid is None and end and nxt and nxt["t"] < end["t"]:
            end = None
        side = "unplaced" if s["unit"] == "workshop" else "tool" if tool and s["unit"] in tool else "rest"
        tally[side] += 1
        hours_of[side] += hours(s["t"], end["t"]) if end and b.get("event") in STARTS else 0
    placed = tally["tool"] + tally["rest"]
    counts = {"sessions": len(starts), "tool": tally["tool"] if tool else None, "rest": tally["rest"] if tool else None,
              "unplaced": tally["unplaced"], "hours_tool": round(hours_of["tool"], 2), "hours_rest": round(hours_of["rest"], 2),
              "hours_unplaced": round(hours_of["unplaced"], 2), "by_unit": dict(sorted(collections.Counter(s["unit"] for s in starts).items())),
              "tool_units": W.tool or UNPLACED}
    if not tool:
        counts["placed"] = placed
    value = NONE if not starts else UNPLACED if not tool or not placed else round(tally["tool"] / placed, 2)
    return result("m4", value, counts, ("session",), proxied("m4") if proxy else "computed", erased=0 if proxy else gone(W.of(("session",), W.tenth)))


def m5(W):
    """The welcome's minutes, whether it finished, and its stalls with their step and words."""
    flows = W.of(("flow",), W.tenth)
    if not flows and (W.forced or (W.forced is None and W.old)):
        return result("m5", NOT_SEEN, {}, ("flow",), NOT_SEEN)
    if not flows:
        return result("m5", NONE, {"flows": 0, "completed": 0, "stalls": 0}, ("flow",))
    read = [l for l in flows if l.get("body")]
    done = [l for l in read if l["body"].get("step") == "flow" and l["body"].get("event") == "done"]
    stalls = [l for l in read if l["body"].get("event") == "stalled"]
    minutes = (round(done[-1]["body"]["seconds"] / 60, 2) if done and isinstance(done[-1]["body"].get("seconds"), (int, float))
               else round(hours(flows[0]["t"], flows[-1]["t"]) * 60, 2))
    items = [{"id": l["id"], "step": l["body"].get("step"), "cause": l["body"].get("cause"), "words": l["body"].get("words"),
              "seconds": l["body"].get("seconds"), "lang": l.get("lang")} for l in stalls]
    counts = {"flows": max(len(done), 1), "completed": len(done), "stalls": len(stalls), "minutes": minutes}
    return result("m5", minutes, counts, ("flow",), items=items, erased=gone(flows))


def m6(W):
    """Rulings applied at the set moments, cards asked again after an answer (and with nothing changed), and strikes."""
    if W.proxy(("recall", "card", "strike")):
        back = [l for l in W.old if "supersede" in (words_of(l) or "").lower()]
        links = [l for l in W.inn if l["kind"] == "link" and (l["body"] or {}).get("rel") == "supersedes"]
        struck = W.of(("strike",), W.old)
        forms = collections.Counter((l["body"] or {}).get("form") or "other" for l in struck)
        return result("m6", NOT_SEEN, {"applied": NOT_SEEN, "brought_back": len(back) + len(links), "struck": len(struck),
                                       "struck_by_form": dict(sorted(forms.items()))}, ("note", "link", "strike"), proxied("m6"))
    recalls = W.of(("recall",), W.tenth)
    applied = sum((lambda v: v if isinstance(v, int) else len(v) if isinstance(v, list) else 0)((l["body"] or {}).get("applied")) for l in recalls)
    by_id = {l["id"]: l for l in W.all}
    follows = collections.defaultdict(list)
    for l in W.all:
        for frm, rel, to in links_of(l) if l.get("body") else []:
            if rel == "follows":
                follows[frm].append(to)
    answered = {a["body"].get("card") for a in W.all if a["kind"] == "answer" and a.get("body") and a["by"]["kind"] == "maker"
                and a["body"].get("answer") in CLOSING}
    back = [c for c in W.of(("card",), W.tenth) if any((by_id.get(t) or {}).get("kind") == "card" and t in answered for t in follows[c["id"]])]
    same = [c for c in back if not (c["body"] or {}).get("changed")]
    struck = W.of(("strike",), W.tenth)
    value = applied if applied or back or struck else NONE
    counts = {"applied": applied, "brought_back": len(back), "unchanged": len(same), "struck": len(struck)}
    return result("m6", value, counts, ("recall", "card", "link", "strike"), erased=gone(recalls + back + struck))


def m7(W, tool):
    """Things taken live with an address and the preview's logged opens; the kill rule reads the same without the tool's unit."""
    out, untold = {"tool": W.tool or UNPLACED}, "" if tool else "; " + EN.raw("measure.m7.untold")  # no list: every unit, said so
    if W.proxy(("live", "preview")):
        week_old = W.of(("accept", "note"), W.old)
        ships = [l for l in week_old if l["kind"] == "accept"]
        places = [l for l in week_old if (l["body"] or {}).get("event") == "place"]
        naming = [l for l in ships + places if ADDRESS.search(words_of(l) or "")]
        out.update(ships=len(ships), places=len(places), naming_an_address=len(naming), kill_rule=len(naming))
        return result("m7", len(naming) or NONE, out, ("accept", "note"), proxied("m7") + untold)
    live = [l for l in W.of(("live",), W.tenth) if (l["body"] or {}).get("address")]
    logged = any(l["kind"] == "preview" and (l["body"] or {}).get("event") == "opened" for l in W.all if not imported(l))
    opens = sum(1 for l in W.of(("preview",), W.tenth) if (l["body"] or {}).get("event") == "opened") if logged else NOT_SEEN
    out.update(live=len(live), by_unit=dict(sorted(collections.Counter(l["unit"] for l in live).items())), opens=opens,
               kill_rule=sum(1 for l in live if not tool or l["unit"] not in tool), play="not yet")
    value = len(live) if live or opens not in (0, NOT_SEEN) else NONE
    return result("m7", value, out, ("live", "preview"), "computed" + untold, erased=gone(W.of(("live", "preview"), W.tenth)))


def prices(root):
    """The dated price table the maker edits (price-table.tsv at the workshop root: date, model, input and output money per million
    tokens), newest first; absent, none."""
    p = os.path.join(root or "", "price-table.tsv")
    rows = []
    for r in read_tsv(p) if root and os.path.exists(p) else []:
        try:
            rows.append((r["date"], r["model"], float(r["input"]), float(r["output"])))
        except (KeyError, ValueError):
            continue
    return sorted(rows, reverse=True)


def _tok(b):
    return (b.get("tokens_in") or 0) + (b.get("tokens_out") or 0)


def _price(b, day, table):
    """A usage body's money from the newest row of the dated table for its model on or before its day, with the row; no row, (None, None)."""
    row = next((r for r in table if r[1] == b.get("model") and r[0] <= day), None)
    return (((b.get("tokens_in") or 0) * row[2] + (b.get("tokens_out") or 0) * row[3]) / 1e6, row) if row else (None, None)


def _money(read, table, zone):
    """Usage lines' money, as m8 and run_cost read it: as the host reported it, else priced from the dated table (dated: the date of the
    table's row last used), and how many lines had neither; the money None when no line gave any."""
    told = [l["body"]["cost"] for l in read if l["body"].get("cost") is not None]
    got = [_price(l["body"], _day(l["t"], zone).isoformat(), table) for l in read if l["body"].get("cost") is None]
    priced = [(m, row[0]) for m, row in got if row]
    return {"reported": sum(told, 0.0), "priced": sum((m for m, _ in priced), 0.0), "dated": priced[-1][1] if priced else None,
            "unpriced": len(got) - len(priced), "money": round(sum(told, 0.0) + sum(m for m, _ in priced), 6) if told or priced else None}


def run_cost(lines, run, table, *, zone=None):
    """One run's cost from its unit's usage lines, from the run to its close or the next run (as m8 reads them): its tokens; its money as
    the host reported it, else priced from the dated table (priced true), else None; unpriced, how many of its usage lines had neither, so
    a money beside them is at least that much; models, each model id's tokens; and model, the one model id they name, or None when they
    name none or several. A struck, deleted, erased or superseded usage line counts for nothing (Astra's finding 11 of batch D)."""
    mine = [l for l in lines if l["unit"] == run["unit"]]
    end = next((l["t"] for l in mine if l["t"] > run["t"] and (l["kind"] == "run" or (l["kind"] in ("close", "abandoned")
                                                                                      and (l["body"] or {}).get("run") == run["id"]))), "9999")
    read = [l for l in mine if l["kind"] == "usage" and l.get("body") and l.get("mark") not in OUT and not imported(l) and run["t"] <= l["t"] <= end]
    use = [l["body"] for l in read]
    money = _money(read, table, zone)
    models = collections.Counter()
    for b in (b for b in use if isinstance(b.get("model"), str)):
        models[b["model"]] += _tok(b)
    return {"tokens": sum(_tok(b) for b in use), "money": money["money"], "priced": money["dated"] is not None, "unpriced": money["unpriced"],
            "models": dict(models), "model": next(iter(models)) if len(models) == 1 else None}


def m8(W, table):
    """Tokens per run, night and week from the usage lines; money as the host reports it, else from the dated price table, marked so;
    each run's tokens and money through run_cost."""
    if W.forced or not any(l["kind"] == "usage" for l in W.all if not imported(l)):
        return result("m8", NOT_SEEN, {}, ("usage",), NOT_SEEN)
    use = [l for l in W.of(("usage",), W.tenth) if l.get("mark") not in ("struck", "deleted", "superseded")]  # not the week's (Astra, batch D); an erased line stays to be counted as erased
    read = [l for l in use if l.get("body")]
    money = _money(read, table, W.zone)
    runs, nights, run_money = collections.Counter(), collections.Counter(), {}
    units, keep = W.by_unit(), {l["id"] for l in read}
    for r in (l for l in W.all if l["kind"] == "run"):
        cost = run_cost([l for l in units[r["unit"]] if l["kind"] != "usage" or l["id"] in keep], r, table, zone=W.zone)
        if cost["tokens"]:
            runs[r["id"]], run_money[r["id"]] = cost["tokens"], cost["money"]
    armed = {(l["body"] or {}).get("session") for l in W.all if l["kind"] == "night" and (l["body"] or {}).get("event") == "armed"}
    for l in read:
        if l["body"].get("session") in armed:
            nights[l["body"]["session"]] += _tok(l["body"])
    hosts = collections.Counter()
    for l in read:
        hosts[l["body"].get("host") or UNPLACED] += _tok(l["body"])
    total = sum(_tok(l["body"]) for l in read)
    counts = {"usage": len(use), "tokens": total, "by_host": dict(sorted(hosts.items())), "runs": dict(runs), "nights": dict(nights),
              "money_reported": round(money["reported"], 6), "money_priced": round(money["priced"], 6) if money["dated"] else None,
              "money": money["money"], "price_table_date": money["dated"], "unpriced": money["unpriced"], "run_money": run_money}
    return result("m8", total if use else NONE, counts, ("usage", "run", "night"), erased=gone(use))


def unseen(name, kinds):
    """A measure the record holds nothing for (the ninth's weeks, or no log): not seen, never zero."""
    return result(name, NOT_SEEN, {}, kinds, NOT_SEEN)


def m9(W, store):
    """How often "likely" held: batch B's calibration over the week, the beliefs marked from Monday's midnight less those from the next
    Monday's; the share held of those marked, and those not shown either way yet as open."""
    if W.forced:
        return unseen("m9", ("fact", "strike"))
    a, b = (calibration(store, since=midnight(d, W.zone))["likely"] for d in (W.mon, W.sun + _dt.timedelta(days=1)))
    k = {x: a[x] - b[x] for x in a}
    counts = {"likely": k["marked"], "held": k["held"], "fell": k["fell"], "open": k["marked"] - k["held"] - k["fell"]}
    return result("m9", round(k["held"] / k["marked"], 2) if k["marked"] else NONE, counts, ("fact", "strike"))


def m10(W):
    """Questions whose valid_until fell in the week and has passed, with no standing line linked answers to them and no strike, deletion,
    erasure or replacement (superseded) by that day, each by the mark's own time (Astra's finding 12 of batch D)."""
    if W.forced:
        return unseen("m10", ("question", "link", "strike"))
    by_id, answered = {l["id"]: l for l in W.all}, collections.defaultdict(list)
    for l in W.all:
        for frm, rel, to in links_of(l) if l.get("body") else []:
            if rel == "answers" and (by_id.get(frm) or {}).get("mark") not in OUT and l.get("mark") not in OUT:
                answered[to].append(max(l["t"], (by_id.get(frm) or l)["t"]))
    until = lambda q: _dt.date.fromisoformat(q["valid_until"])  # noqa: E731
    expired = [q for q in W.all if q["kind"] == "question" and not imported(q) and q.get("valid_until") and W.mon <= until(q) <= W.sun
               and until(q) < W.today]
    read = lambda q: (any(W.day({"t": t}) <= until(q) for t in answered[q["id"]])  # noqa: E731
                      or (q.get("mark") in OUT and day_of(q.get("mark_since") or q["t"], W.zone) <= until(q)))  # by the mark's own time
    unread = [q for q in expired if not read(q)]
    return result("m10", len(unread) or NONE, {"expired": len(expired), "unread": len(unread)}, ("question", "link", "strike"), erased=gone(expired))


def _unused(lines, store, as_of, days=90):
    """Store.unused's rule over the lines in hand, for a store without it: a standing type or relation older than the cut with no standing
    line about its things (the object lines included), or no link of its name, from the cut to the end of as_of."""
    cut, end = midnight(as_of - _dt.timedelta(days=days)), midnight(as_of + _dt.timedelta(days=1))
    ls = [l for l in lines if l["t"] < end and l.get("mark") not in OUT]
    typed = {l["id"]: (l["body"] or {}).get("type") for l in ls if l["kind"] == "object"}
    last = collections.defaultdict(str)
    for l in ls:
        ty = typed.get(l["id"]) or typed.get(l.get("about"))
        if ty:
            last[ty] = max(last[ty], l["t"])
        for _, rel, _ in links_of(l) if l.get("body") else []:
            last["rel:" + rel] = max(last["rel:" + rel], l["t"])
    old = lambda x, key: x["t"] < cut and last[key] < cut  # noqa: E731
    return {"types": [t for t in store.types() if old(t, t["body"]["name"])],
            "relations": [r for r in store.relations() if old(r, "rel:" + r["body"]["name"])]}


def m11(W, store):
    """Types and relations unused ninety days as of the week's Sunday (Store.unused, or its rule over the lines where the store lacks it)."""
    if W.forced:
        return unseen("m11", ("object", "link"))
    u = store.unused(as_of=W.sun.isoformat()) if hasattr(store, "unused") else _unused(W.all, store, W.sun)
    counts = {"types": len(u["types"]), "relations": len(u["relations"])}
    return result("m11", counts["types"] + counts["relations"] or NONE, counts, ("object", "link"))


def m12(W):
    """Acts the hook saw that no answered proposal covered, by verb: an act not seen by its verb's name, an unknown act as no verb; an act
    that never left the machine is not counted."""
    if W.forced:
        return unseen("m12", ("note", "not_seen"))
    acts = [l for l in W.tenth if l.get("mark") not in OUT and l.get("body") and l["body"].get("outcome") not in STAYED and (
        (l["kind"] == "note" and l["body"].get("event") == "unknown act") or (l["kind"] == "not_seen" and l["body"].get("verb")))]
    by_verb = collections.Counter((l["body"].get("verb_name") or l["body"]["verb"]) if l["kind"] == "not_seen" else "no verb" for l in acts)
    return result("m12", len(acts) or NONE, {"by_verb": dict(sorted(by_verb.items())), "acts": len(acts)}, ("note", "not_seen"))


def m13(W):
    """The week's checks that were named, and those named after one of the same run, name and command had gone green (the index's flag)."""
    if W.forced:
        return unseen("m13", ("check",))
    checks = W.of(("check",), W.tenth)
    named = [l for l in checks if isinstance((l.get("body") or {}).get("named_at"), str) or l.get("named_late")]
    late = sum(1 for l in named if l.get("named_late"))
    return result("m13", late or NONE, {"checks": len(named), "named_late": late}, ("check",), erased=gone(checks))


def pages_opened(root, mon, sun, zone=None):
    """The views the pages server answered with a page, Monday to Sunday of the maker's local days, from its own log; None with no log."""
    p = os.path.join(root or "", OPENED)
    if not root or not os.path.exists(p):
        return None
    views, days = collections.Counter(), collections.Counter()
    with open(p, encoding="utf-8") as f:
        for row in f:
            try:
                r = json.loads(row)
                d, v = day_of(r["t"], zone), r["view"]
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
            if mon <= d <= sun and isinstance(v, str):
                views[v] += 1
                days[d.isoformat()] += 1
    return {"opens": sum(views.values()), "by_view": dict(sorted(views.items())), "days": dict(sorted(days.items()))}


def m14(W, root):
    """Pages opened in the week, from the server's log of opened views; not seen, never zero, when the pages have kept no log."""
    got = None if W.forced else pages_opened(root, W.mon, W.sun, W.zone)
    return unseen("m14", (OPENED,)) if got is None else result("m14", got["opens"] or NONE, got, (OPENED,))


def m15(W, k3):
    """Cards called needless, from M3's own count, so the week page and the brief count alike, of every card raised that could be called
    needless: those against the budget (the move's among them), those before a five act and the week's (Astra's finding 15 of batch D);
    which of them count against the asking budget is M3's and M16's measure, not this one's."""
    k = k3["counts"]
    if W.forced or "needless" not in k:
        return unseen("m15", ("needless", "card"))
    raised = k["cards"] + k["before_act"] + k["week_card"]
    return result("m15", k["needless"] or NONE, {"needless": k["needless"], "cards": raised}, ("needless", "card"))


def m16(W, k3):
    """The asking budget, from M3's own count: the days over the daily limit and the cards over it, against the limit your setting gives."""
    k = k3["counts"]
    if W.forced or "days_over" not in k:
        return unseen("m16", ("card",))
    return result("m16", k["days_over"] or NONE, {x: k[x] for x in ("days_over", "over_by", "cap", "setting")}, ("card",))


def setting(root):
    p, ask = os.path.join(root or "", "welcome.md"), ""
    if root and os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            ask = welcome_answers(f.read(), EN).get("ask", "").strip().lower()
    return ask if ask in LIMITS else "some"


def week_table(store, week, *, zone=None, tool=None, ninth=None, lines=None):
    """M1 to M16 for one ISO week of the maker's local days, read from the store's lines now; M3 first, since M15 and M16 read its count."""
    tool = set(tool or (store.home or {}).get("tool_units") or ()) or None  # the caller's list, else the one home.json names: page and recorder agree
    W = Week(store.lines() if lines is None else lines, week, zone, tool, ninth, now=store.clock())
    k3 = m3(W, setting(store.root))
    return {"m1": m1(W), "m2": m2(W), "m3": k3, "m4": m4(W, tool), "m5": m5(W), "m6": m6(W), "m7": m7(W, tool),
            "m8": m8(W, prices(store.root)), "m9": m9(W, store), "m10": m10(W), "m11": m11(W, store), "m12": m12(W), "m13": m13(W),
            "m14": m14(W, store.root), "m15": m15(W, k3), "m16": m16(W, k3)}


def baseline(store, *, zone=None, lines=None):
    """The measures over the last four complete weeks before the import's date, from the move line that carries the export's hash."""
    lines = store.lines() if lines is None else lines
    moves = [l for l in lines if l["kind"] == "move" and isinstance((l.get("body") or {}).get("source_sha256"), str)]
    if not moves:
        return None
    first = min(moves, key=lambda l: (l["t"], l["id"]))
    day = day_of(first["t"], zone)
    monday = bounds(iso_week(day))[0]
    names = [iso_week(monday - _dt.timedelta(days=7 * k)) for k in (4, 3, 2, 1)]
    table = {w: week_table(store, w, zone=zone, ninth=True, lines=lines) for w in names}
    return {"export_sha256": first["body"]["source_sha256"], "move": first["id"], "imported_at": first["t"], "import_day": day.isoformat(),
            "weeks": names, "table": table, "proxies": {n: EN.raw(f"measure.{n}.proxy") for n in NAMES},
            "kinds": sorted({k for t in table.values() for m in t.values() for k in m["kinds"]})}


def behaviour_sample(lines, week, zone=None):
    """Ten of the week's briefs and cards at most, spread evenly over the week, oldest first: what the behaviour check would read."""
    items = [l["id"] for l in lines if l["kind"] in ("brief", "card") and iso_week(l["t"], zone) == week]
    return items if len(items) <= 10 else [items[round(i * (len(items) - 1) / 9)] for i in range(10)]


def behaviour_check(store, week, reader, *, by, zone=None):
    """The weekly behaviour check, by a reader that wrote none of the sample: a finding per failure the reader names, and at most one
    card for the week gathering them (purpose behaviour-check). `reader(line) -> [{"position", "text"}]`; nothing here judges words."""
    lines = store.lines()
    by_id = {l["id"]: l for l in lines}
    sample = [by_id[i] for i in behaviour_sample(lines, week, zone)]
    me = (by.get("kind"), by.get("name"), by.get("model"))
    if any((l["by"]["kind"], l["by"]["name"], l["by"].get("model")) == me for l in sample):
        raise Refused(EN.plain("behaviour.self"))
    found = []
    for l in sample:
        for f in reader(l) or []:
            found.append(store.append(l["unit"], "finding", {"event": "behaviour-check", "week": week, "about": l["id"],
                                                             "position": f.get("position"), "text": f.get("text")}, by=by))
    card = None
    stands = any(c["kind"] == "card" and (c.get("body") or {}).get("purpose") == "behaviour-check" and c["body"].get("week") == week for c in lines)
    if found and not stands:
        saw = "\n".join(f"{i}" for i in found)
        card = store.append("workshop", "card", {"decides": EN.plain("behaviour.decides", week=week, findings=EN.count("item", len(found))),
                                                 "stand": EN.raw("behaviour.stand"), "other": EN.raw("behaviour.other"),
                                                 "wrong": EN.raw("behaviour.wrong"), "saw": saw, "answers": ["yes", "no", "later"],
                                                 "purpose": "behaviour-check", "week": week, "about": "workshop", "version": 1}, by=by)
    return {"sample": [l["id"] for l in sample], "findings": found, "card": card}


def month_start(now, zone=None):
    """The first midnight of the maker's local month holding now (a datetime or a line's time), as a line's time in UTC, so a window
    `since` it compares with every line's t."""
    return midnight(day_of(now, zone).replace(day=1), zone)


def midnight(day, zone=None):
    """The first midnight of one of the maker's local days, as a line's time in UTC."""
    m = _dt.datetime.combine(day_of(day, zone), _dt.time())
    return iso(m.replace(tzinfo=zone) if zone else m.astimezone())


def _beliefs(store):
    """The facts about things whose words are kept, grouped by (thing, facet), each group in time order; and the strikes. A deleted or
    erased fact has no words in the index; calibration reads its shape from store.beliefs instead."""
    groups, strikes = collections.defaultdict(list), []
    for l in store.lines(kinds=["fact", "strike"]):
        b = l.get("body")
        if l["kind"] == "strike":
            strikes.append(l)
        elif l.get("about") and isinstance(b, dict) and isinstance(b.get("facet"), str):
            groups[(l["about"], b["facet"])].append(l)
    return groups, strikes


def _shown(later, value, bases):
    """The first later standing fact of the group whose basis is one of bases: whether it says the same value, or None when none does."""
    x = next((x for x in later if x.get("mark") not in OUT and x["body"].get("basis") in bases), None)
    return None if x is None else canonical(x["body"].get("value")) == value


def _scores(store, belief, x):
    """Whether a later standing fact x can score a belief: it rests on a check the tool ran that exited 0 after the belief, or on a said
    line of his written after it; a later fact by the partner on anything else scores nothing."""
    b = x.get("body") or {}
    src = store.get(b.get("source")) if isinstance(b.get("source"), str) else None
    if not src or x.get("mark") in OUT or (src["t"], src["id"]) <= (belief["t"], belief["id"]):
        return False
    if b.get("basis") == BASES[0]:
        return src["kind"] == "said" and src["by"]["kind"] == "maker"
    return b.get("basis") == BASES[1] and src["kind"] == "check" and src["by"]["kind"] == "tool" and (src.get("body") or {}).get("exit") == 0


def calibration(store, *, since):
    """Beliefs about things marked likely or unsure with t >= since, each counted once as marked; held when the first later fact about the
    same thing and facet that rests on a green check by the tool or on his said line, both after the belief, says the same value; fell
    when the belief is struck, deleted or erased (a deleted or erased one read by its shape alone, from store.beliefs, never its words),
    or that fact says another value; otherwise marked and not scored. A strike taken back is no strike; a belief written before since is
    not in the window, whenever it fell. Counts of beliefs, never a percent: the brief says "of 40 marked likely, 31 held"."""
    out = {c: {"marked": 0, "held": 0, "fell": 0} for c in CONFIDENCE}
    for group in _beliefs(store)[0].values():
        for i, l in enumerate(group):
            n = out.get(l["body"].get("confidence"))
            if n is None or l["t"] < since:
                continue
            n["marked"] += 1
            x = None if l.get("mark") in DOWN else next((x for x in group[i + 1:] if _scores(store, l, x)), None)
            if l.get("mark") in DOWN or x is not None:
                n["fell" if x is None or canonical(x["body"].get("value")) != canonical(l["body"].get("value")) else "held"] += 1
    for b in store.beliefs():  # taken away: its words are gone, its shape is kept
        n = out.get(b["confidence"])
        if n is not None and b["mark"] in ("deleted", "erased") and b["t"] >= since:
            n["marked"] += 1
            n["fell"] += 1
    return out


def corrections(store, *, since):
    """Facts about things, of any confidence, that fell by his hand in the window, counted once each under the basis of the line corrected
    (the four bases, each counted even at 0): struck by a strike of his that stands, with t >= since, or followed by a standing fact in his
    words (basis he said) with t >= since saying another value. Counts of facts corrected."""
    groups, strikes = _beliefs(store)
    struck = {(l["body"] or {}).get("target") for l in strikes if l["by"]["kind"] == "maker" and l["t"] >= since and l.get("mark") not in OUT}
    out = dict.fromkeys(BASES, 0)
    for group in groups.values():
        for i, l in enumerate(group):
            if l["body"].get("basis") in out and (l["id"] in struck or _shown([x for x in group[i + 1:] if x["t"] >= since],
                                                                                canonical(l["body"].get("value")), BASES[:1]) is False):
                out[l["body"]["basis"]] += 1
    return out
