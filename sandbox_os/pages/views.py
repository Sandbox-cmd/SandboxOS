# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""Each view's content, built from the reader's lines in the frame's blocks: the brief and a project's brief, a run, a card
(a grant's read-back, tonight, take it live and a note about you included), the present page and its file, find, what
was learned, the charter and the book, the tool's page, the graph, the morning after a move, the welcome, a thing's page, and a note
about you, every line about the maker with a strike on each."""
import datetime as _dt
import os
import re

from sandbox_os.store import verbs as declared
from sandbox_os.store.line import BASES, CLAIM_KINDS, ID_RE, canonical, iso, strip_arabic_marks
from sandbox_os.pages import measures, world
from sandbox_os.pages.frame import Ctx, HERE
from sandbox_os.pages.read import (words_of, standing, touched, maker_id, you_lines, question_state, expired_unread, sentences, ticked,
                                   FAILED, DOWN, GONE, VOCAB, PORTRAITS, PROPOSED, skill_uses, from_seed)
from sandbox_os.pages.read import portraits as read_portraits, proposals as read_proposals, chosen
from sandbox_os.pages.read import DOORS  # noqa: F401  the one map the page, the read and the tools (command.mcp) read
from sandbox_os.pages.words import H, esc, plain

TREE = os.path.dirname(os.path.dirname(HERE))
LIMITS = measures.LIMITS
ACTS = ("leaves", "money", "destroys", "deploys", "claim")
OUTCOMES = {"ran": "ask.ran", "did not run": "ask.notran", "refused by the host": "ask.refused"}
IMPORT = ("receipt", "move", "link")  # the import's own lines: activity of the move, not of the work; a verb's receipt is the work's
HOW = {".env path": "secret.env", "keychain by name": "secret.keychain", "a secret's name": "secret.named"}  # a secret read's how (Task 10)
STAYED = ("did not run", "refused by the host")  # an unknown act with one of these outcomes never left the machine
SANDBOX_OFF = (("sandbox.enabled", False), ("sandbox_mode", "danger-full-access"), ("default_permissions", ":danger-full-access"))  # Claude Code's, then Codex's


def setting(c):
    s = (c.welcome.get("ask") or "").strip().lower()
    return s if s in LIMITS else "some"


def named(w, prefix, key):
    """A record's value named from the table when the table has it (a step, a cause), else shown as it is."""
    return w.t(prefix + key) if isinstance(key, str) and (prefix + key, "") in w.tab else w.ident(key or "")


def listed(v):
    """The ids a moment line lists; its recall line carries the same as a count, so only the moment's list is counted."""
    return len(v) if isinstance(v, list) else 0


def ul(items):
    items = [i for i in items if i]
    return H('<ul class="list">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>") if items else H("")


# a card, in a list of cards and on its own page
def card_row(c, card, i, n, opened):
    w, r, card = c.w, c.r, tilde(card)  # opened, the card is the row and its question is said once, in it (C1)
    c.cards.append(card)
    c.term("card")
    later = [a for a in r.answers(card["id"]) if standing(a) and (a["body"] or {}).get("answer") == "later"]
    state = "card.state.open" if opened else "card.state.later" if later else "card.state.waiting"
    title = c.words(card, "decides") or w.t("card.missing")
    head = ("" if opened else f'<button class="open-card" aria-expanded="false" aria-controls="card-{card["id"]}">{title}</button>') + w.t(state, cls="state")
    return H(f'<div class="row" tabindex="-1" data-card="{card["id"]}"><span class="mark num">{w.ident(i)}</span>'
             f'<span class="text">{head}</span><span class="why">{c.meta(card, project=True)}</span>{card_block(c, card, i, n, not opened)}</div>')


def tilde(card):
    """A card as shown: each path under the home folder in its words said from ~ (C1); the record keeps them as written."""
    home = re.compile(r"(?<![\w.~-])/*" + re.escape(os.path.expanduser("~")) + r"(?=/|\s|$)")
    return dict(card, body={k: home.sub("~", v) if isinstance(v, str) else v for k, v in card["body"].items()}) if card.get("body") else card


def pairs(c, line, fields):
    """Labelled fields of a line as a definition list; a field the partner left out says so."""
    out = []
    for f, sid in fields:
        v = (line["body"] or {}).get(f) if line else None
        if isinstance(v, list):
            val = ul(c.w.ident(x) if not isinstance(x, str) or "/" in x else f'<span data-l="{line["id"]}" dir="auto">{esc(x)}</span>' for x in v)
        elif isinstance(v, dict):
            val = ul(c.w.ident(x) for vs in v.values() for x in (vs if isinstance(vs, list) else [vs]) if x)
        elif f in ("until", "awake_until", "said_at") and isinstance(v, str) and re.match(r"\d{4}-\d\d-\d\d", v):
            val = c.w.date(v if "T" in v else v + "T12:00:00+00:00")
        else:
            val = c.words(line, f) if isinstance(v, str) and v.strip() else None
        out.append(f"<dt>{c.w.t(sid)}</dt><dd>{val or c.w.t('card.missing')}</dd>")
    return "".join(out)


def card_block(c, card, i, n, hidden=False):
    w, r = c.w, c.r
    b, cid = card["body"] or {}, card["id"]
    about = r.get(b["about"]) if isinstance(b.get("about"), str) else None
    kind = about["kind"] if about else None
    lead = ""
    if kind == "grant":
        c.term("grant")
        until = pairs(c, about, (("until", "grant.until"),)) if (about["body"] or {}).get("until") else f"<dt>{w.t('grant.until')}</dt><dd>{w.t('grant.until.none')}</dd>"
        lead = (pairs(c, about, (("sentence", "grant.sentence"), ("reading", "grant.reading"), ("scope", "grant.covers"))) + until
                + pairs(c, about, (("take_back", "grant.takeback"),)))
    elif kind == "night":
        c.term("night")
        lead = pairs(c, about, (("touch", "night.touch"), ("not", "night.not"), ("stops", "night.stops"), ("asks", "night.asks"),
                                ("awake_until", "night.awake"), ("aside", "night.aside"), ("acceptance", "night.acceptance")))
    elif kind == "live":
        host = (about["body"] or {}).get("host")
        lead = pairs(c, about, (("thing", "live.thing"), ("stays", "live.stays"), ("until", "live.until")))
        lead += f"<dt>{w.t('live.host')}</dt><dd>{w.ident(host) + w.t('live.underhost', tag='p') if host else w.t('live.nohost')}</dd>"
    elif kind == "about_you":
        q = c.words(about, "quote") or c.words(about)
        lead = f"<dt>{w.t('about.quote', date=w.date((about['body'] or {}).get('said_at', about['t'])[:10] + 'T12:00:00+00:00'))}</dt><dd>{q}</dd>"
    dl = pairs(c, card, (("stand", "card.stand"), ("other", "card.other"), ("wrong", "card.wrong")))
    again = ""
    if (b.get("version") or 1) > 1:
        again = (f"<dt>{w.t('card.changed')}</dt><dd>{c.words(card, 'changed')}</dd>" if words_of(card, "changed")
                 else f"<dt></dt><dd>{w.t('card.nochange')}</dd>")
    seen = [l for l in (words_of(card, "saw") or "").split("\n") if l.strip()]
    show = lambda ls: c.words(dict(card, body={"saw": "\n".join(ls)}), "saw", cls="mono")  # noqa: E731
    saw = (H(w.t("saw.count", items=w.count("item", len(seen)), tag="p") + show(seen[:10]) + fold(  # past ten, counted, the rest folded (C1)
        w.t("saw.rest", items=w.count("item", len(seen) - 10)), [show(seen[10:])])) if len(seen) > 10
           else c.words(card, "saw", cls="mono") or w.t("card.missing", cls="mono"))
    tail = H(about and kind == "grant" and w.t("grant.onyes", tag="p", cls="answered") or "")
    if kind == "about_you":
        tail = w.t("about.waits", tag="p", cls="answered")
    return H(f'<div class="card" id="card-{cid}"{" hidden" if hidden else ""}>'
             f'{c.words(card, "decides", tag="p", cls="decides") or w.t("card.missing", tag="p", cls="decides")}'
             f'{f"<dl>{lead}</dl>" if lead else ""}<dl>{dl}{again}</dl>{tail}'
             f'<details class="saw"><summary>{w.t("card.saw")}</summary>{saw}</details>{answers_of(c, card)}{form(c, card)}</div>')


def answers_of(c, card):
    w, r, out = c.w, c.r, []
    for a in r.answers(card["id"]):
        ab = a["body"] or {}
        if a["body"] is None:
            out.append(w.t("mark.gone", tag="p", cls="answered"))
            continue
        said = (H('“' + c.words(a, "words") + '”') if ab.get("answer") == "words" and words_of(a, "words")
                else w.t("answer." + ab.get("answer", "later")) if ab.get("answer") in ("yes", "no", "later", "words") else c.words(a))
        frm = w.t("from." + ab["from"]) if ab.get("from") in ("page", "conversation") else w.ident(ab.get("from") or "")
        if ab.get("stale"):
            out.append(w.t("card.stale.page", tag="p", cls="answered", answer=said, when=w.when(a["t"]), **{"from": frm}))
            continue
        if ab.get("presence") == "none" or a["by"]["kind"] != "maker":
            out.append(w.t("card.nobody", tag="p", cls="answered", **{"from": frm}, when=w.when(a["t"])))
            continue
        if a.get("mark") == "superseded":
            later = r.into(a["id"], "supersedes")
            out.append(w.t("card.superseded", tag="p", cls="answered", when=w.when(later[-1]["t"] if later else a["t"])))
        on = c.words(card, "on_" + ab.get("answer", "")) or ""
        out.append(f'<p class="answered">{w.t("card.kept", answer=said)} {on} {w.t("card.answered", when=w.when(a["t"]), **{"from": frm})}</p>')
        if r.into(a["id"], "follows") and any(x["kind"] == "needless" for x in r.into(a["id"], "follows")):
            c.term("needless")
            out.append(w.t("card.needless", tag="p", cls="answered"))
    return "".join(out)


def form(c, card):
    w, b = c.w, card["body"] or {}
    dis = " disabled" if c.as_file else ""
    labels = b.get("answers") if isinstance(b.get("answers"), list) and len(b.get("answers")) == 3 else None

    def button(k, a, idx):
        lab = (f'<span data-l="{card["id"]}" dir="auto">{esc(labels[idx])}</span>' if labels and isinstance(labels[idx], str)
               else w.t("answer." + a))
        return f'<button{" class=\"primary\"" if a == "yes" else ""} name="answer" value="{a}"{dis}>{w.key(k)} {lab}</button>'
    return H(f'<form class="answers" method="post" action="/answer" aria-label="{esc(w.plain("aria.answers"))}">'
             f'<input type="hidden" name="card" value="{card["id"]}"><input type="hidden" name="head" value="{c.r.head(card["unit"])}">'
             f'<button class="hidden" name="answer" value="words" tabindex="-1" aria-hidden="true"{dis}></button>'
             + "".join(button(k, a, i) for i, (k, a) in enumerate((("y", "yes"), ("n", "no"), ("l", "later"))))
             + f'<input name="words" type="text" placeholder="{esc(w.plain("card.box"))}" aria-label="{esc(w.plain("card.box.label"))}"{dis}></form>')


def card_rows(c, cards):
    return [card_row(c, x, i, len(cards), i == 1) for i, x in enumerate(cards, 1)]


def needs(c, cards, rows, sid="sum.needs"):  # what needs his answer, only when a card waits: no empty part (C5); the brief keeps its line
    return c.part("part.needs", len(cards), "card", c.w.t(sid), rows, hot=True) if cards else H("")


# the brief, for the workshop or for one project, as a note across the desk (03-design.md section 5 point 9, section 9 point 5; the pages
# sitting): one line of context, the first card whole and the rest counted, then a paragraph per project that moved, the rest in one line
def brief(c, unit=None):
    r, w = c.r, c.w
    mk = r.maker_newest()
    since = mk["t"] if mk else None
    pool = [unit] if unit else r.units()
    new = [l for l in r.all() if l["unit"] in pool and (mk is None or (l["t"], l["id"]) > (mk["t"], mk["id"])) and not from_seed(l)]  # the seed is not news
    cards = [x for x in r.open_cards(pool) if not outside_budget(x)]  # the move's cards and the week's wait under good to know (card 23)
    needs = one_card(c, cards)
    real = [l for l in new if work(l)]
    held = None if unit else []  # what came in line by line: on each project's own page, and here the rare and promised rows, the rest counted
    rows = debrief_rows(c, pool, since, new, held, real[-20:] if unit else ())
    went_on = sum(c.assumed_n.values())  # each is its project's last sentence; good to know counts them, the top does not (the sweep)
    fs = faults(c, unit)
    good = (fs + held_rows(c, held or []) + ([c.row("", w.t("good.assumed", went_on, assumptions=w.count("assumption", went_on)))] if went_on else [])
            + good_rows(c, pool, since) + world_rows(c, pool))
    moved = {l["unit"] for l in new}
    live = [l for l in r.kind("live", units=pool, since=since) if standing(l) and (l["body"] or {}).get("address")]
    went = w.t("why.debrief.live", things=w.count("thing", len(live))) if live else w.t("why.debrief.live.none")
    went = H(went + (w.t("why.debrief.faults", len(c.found), faults=w.count("fault", len(c.found))) if fs else ""))  # a fault, counted (F1)
    if mk:
        said = dict(day=w.date(c.now), lines=w.count("line", len(real)), projects=w.count("project", len(moved)), live=went)
        why = w.t(("why.debrief" if cards else "why.debrief.none") + ("" if real else ".still"), len(cards) if cards else None, cards=w.count("card", len(cards)), **said)
    else:
        why = w.t("why.brief.first")
    body = (c.part("part.needs", len(cards), "card", w.t("sum.needs") if cards else w.t("sum.needs.none"), needs, hot=True)
            + c.part("part.since", len(rows), "item", w.t("sum.debrief.project" if unit else "sum.debrief"), rows)
            + c.part("part.good", len(good), "item", w.t("sum.good.fault" if fs else "sum.good"), good))
    title = w.t("title.project", project=c.project(unit)) if unit else w.t("title.brief")
    where = w.t("top.project", project=c.project(unit)) if unit else None
    return c.page(title, why, H(""), body, where=where, view="project" if unit else "brief")


def faults(c, unit, most=5):
    """Every fault the read-back of the record finds, a row each and kept in c.found, which the brief's first sentence counts (F1): a torn
    tail by its project and size, a line or a file not as written, the read-back's own failure; past most, counted; paths in what I saw."""
    w = c.w
    try:
        v = c.s.verify(unit)
        found = c.found = v["failures"]
        c.heads = v.get("heads") or {}
    except Exception as e:  # the read-back itself failed: one row, one fault, and the page still opens
        c.found = [e]
        return [c.row("", w.t("index.fault.read"), saw(c, [w.ident(str(e))]))]
    rec = lambda u: w.t("index.record.own") if u == "workshop" else w.t("index.record", project=w.ident(u))
    torn = lambda f: w.t("index.torn", record=rec(f["file"].split("/")[1]), bytes=w.count("byte", int((re.findall(r"\d+", f["what"]) or [0])[0])))
    rows = [c.row("", torn(f) if f["what"].startswith("torn tail") else
                  w.t("index.fault", record=rec(f["file"].split("/")[1]), row=w.num(f["row"])) if f["row"] else w.t("index.fault.file"),
                  saw(c, [w.ident(f["file"]), w.ident(f["what"])])) for f in found[:most]]
    return rows + ([c.row("", w.t("index.faults.more", lines=w.count("line", len(found) - most)))] if len(found) > most else [])


def debrief_rows(c, pool, since, new, held=None, tail=()):
    """The since part in section 5's order: a paragraph per project that moved (note_row), the quiet projects in one line, on a project's
    own page what came in line by line (since_rows, then its newest lines no row above names; on the brief, held to be counted), the
    proposals, the open questions, this month's score and corrections, and the week's cost with each host's."""
    r, w, rows = c.r, c.w, []
    c.assumed_n = {}
    last, pending = {}, {}
    for l in new:
        last[l["unit"]] = (l["t"], l["id"])
    for p in declared.waiting(c.s, units=pool):  # a yes with no receipt yet, listed by the verb's name until one exists (section 3 point 3)
        pending.setdefault(p["unit"], []).append(p)
    for u in sorted(last, key=lambda u: last[u], reverse=True):
        rows.append(note_row(c, u, [l for l in new if l["unit"] == u], since, pending.get(u, ())))
    quiet = [u for u in pool if u not in last]
    quiet and rows.append(c.row("", w.t("debrief.quiet", projects=joined(c, [project_link(c, u) for u in quiet]))))
    rows += [c.row("", yes_said(c, pending[u], "debrief.verb.yes.quiet", project=project_link(c, u))) for u in quiet if pending.get(u)]
    rows += since_rows(c, pool, since, new, held)
    named_ = "".join(rows)
    rows += [c.line_row(l) for l in tail if f'data-line="{l["id"]}"' not in named_] + [x for x in [proposals_row(c, pool)] if x]
    state = {q["id"]: question_state(r, q) for q in r.kind("question", units=pool)}
    open_ = [q for q in r.kind("question", units=pool) if state[q["id"]] == "open"]
    block = [q for q in open_ if (q["body"] or {}).get("blocks") is True]
    rows.append(c.row("", w.t("debrief.questions" if block else "debrief.questions.none")))
    rows += question_rows(c, block)
    rest = len(open_) - len(block)
    rest and rows.append(c.row("", w.t("debrief.questions.rest", questions=w.count("moreopen", rest))))
    gone = expired_unread(r, pool)
    gone and rows.append(c.row("", H(w.t("debrief.questions.expired", len(gone), questions=w.count("question", len(gone))) + ul(c.words(q) for q in gone))))
    month = measures.month_start(c.now)
    cal, said = measures.calibration(c.s, since=month), []
    for conf, sid in (("likely", "debrief.calibration"), ("unsure", "debrief.calibration.unsure")):
        k = cal[conf]
        (k["held"] or k["fell"]) and said.append(w.t(sid, beliefs=w.count("belief", k["marked"]), held=w.count("held", k["held"]), fell=w.count("fell", k["fell"])))
    said and c.term("likely", "belief")
    rows += [c.row("", H(" ".join(said)) if said else w.t("debrief.calibration.none"))] if said or not any(cal[k]["marked"] for k in ("likely", "unsure")) else []
    fixed = [(b, n) for b, n in measures.corrections(c.s, since=month).items() if n]
    fixed and rows.append(c.row("", H(w.t("debrief.corrections") + ul(w.t("debrief.corrections.item", basis=w.t("debrief.basis." + b),
                                                                         beliefs=w.count("belief", n)) for b, n in fixed))))
    m8 = measures.m8(measures.Week(r.all(), measures.iso_week(c.now)), measures.prices(c.root))
    if isinstance(m8["value"], int):
        rows.append(c.row("", w.t("debrief.cost", tokens=w.count("token", m8["value"]), money=money(c, m8["counts"]))))
    else:
        c.term("notseen")
    costs, silent = host_cost_rows(c, pool, since)  # the hosts that reported nothing: one sentence, the week's when none reported (R-READ-19)
    rows += [] if isinstance(m8["value"], int) else [c.row("", w.t("debrief.cost.none"))]
    return rows + costs + ([c.row("", w.t("good.cost.none", hosts=silent))] if silent and isinstance(m8["value"], int) else [])


def proposals_row(c, pool):
    """The proposals waiting in one sentence of the morning note (03-design.md section 9 point 5; the pages sitting: its proposals line):
    the types, relations and verbs proposed, each kind counted and a kind with none left out, the first proposal whole in its own words and
    the rest counted, on the week's card as a link when it is open, else for it; None when nothing waits or the workshop is not read."""
    w = c.w
    waiting = [p for p in read_proposals(c.r.all()) if p["state"] == "waiting"] if "workshop" in pool else []
    if not waiting:
        return None
    kinds = [w.t("good.proposals.kind", count=w.count(noun, n)) for noun, n in
             ((noun, sum(p["event"] == ev for p in waiting)) for ev, noun in zip(PROPOSED, ("type", "relation", "verb"))) if n]
    card = next((x for x in c.r.open_cards(pool) if (x["body"] or {}).get("week_card")), None)
    on = H(f'<a href="{c.href("card", id=card["id"])}">{w.t("good.proposals.card")}</a>') if card else w.t("good.proposals.wait")
    c.term("proposal", "card")
    return c.row("", w.t("good.proposals", len(waiting), kinds=joined(c, kinds), card=on, first=c.words(waiting[0]["line"]),
                         rest=w.count("proposal", len(waiting) - 1)))


def world_rows(c, pool):
    """Good to know about the vocabulary, the brief's alarm (06-stream.md adjustment 8): the types and relations with no new line in ninety
    days, counted, the types each a link and the relations' names in what I saw, any of them struck on the week's card; and the skills
    unused as long, counted, their names in what I saw. Only where the workshop is read, since the vocabulary lives there."""
    if "workshop" not in pool:
        return []
    w, u = c.w, c.s.unused(days=UNUSED_DAYS)
    days = w.count("day", UNUSED_DAYS)
    c.term("type")
    if u["types"] or u["relations"]:
        rels, more = [w.ident(x["name"]) for x in u["relations"]], len(u["types"]) - 8  # past eight, the rest counted as types
        names = [type_words(c, x["name"]) for x in u["types"][:8]] + ([w.t("debrief.more", things=w.count("type", more))] if more > 0 else [])
        rows = [c.row("", w.t("good.unused", types=w.count("type", len(u["types"])), relations=w.count("relation", len(u["relations"])), days=days),
                      H(joined(c, names) + saw(c, rels)))]
    else:
        rows = [c.row("", w.t("good.unused.none", days=days))]
    skills = [x for x in skill_uses(c.root, c.r.all(), now=c.now, days=UNUSED_DAYS) if x["unused"]]
    skills and c.term("skill")
    return rows + ([c.row("", w.t("good.skills.unused", len(skills), skills=w.count("skill", len(skills)), days=days),
                          saw(c, [w.ident(x["name"]) for x in skills]))] if skills else [])


def project_link(c, u):
    return H(f'<a href="{c.href("project", unit=u)}">{c.project(u)}</a>')


def joined(c, items, cap=None):
    """Items in one sentence, the table's comma between them; past cap, the rest counted as things."""
    items = [i for i in items if i]
    more = [c.w.t("debrief.more", things=c.w.count("thing", len(items) - cap))] if cap and len(items) > cap else []
    return H(esc(c.w.raw("read.sep")).join(items[:cap] + more))


def work(l):
    """A line of the work, not of the import: every kind but the import's own, and a verb's receipt, which the hook writes."""
    return l["kind"] not in IMPORT or bool((l["body"] or {}).get("verb"))


def note_row(c, u, ls, since, pending=()):
    """One project's paragraph in my voice, in section 5's order, what I assumed always its last sentence; the acts by their verb inside
    it (what ran and what failed after what was made, what the hook saw after the checks, what waits on a verb after what waits for
    you); a project that moved by the import's own lines alone says only that."""
    w = c.w
    mine = [l for l in ls if work(l)]
    if not mine:
        return c.row(c.stamp(ls[-1]["t"]), w.t("row.project.import", project=project_link(c, u), lines=w.count("line", len(ls))))
    cards = [x for x in c.r.open_cards([u]) if not outside_budget(x)]
    cards and c.term("card")
    said = [w.t("debrief.on", project=project_link(c, u), lines=w.count("line", len(mine))), made(c, mine), *ran(c, mine), picked(c, u),
            checked(c, u), *seen(c, mine), w.t("debrief.waits", len(cards), cards=w.count("card", len(cards))) if cards else w.t("debrief.waits.none"),
            *waiting_on(c, cards, pending), assumed(c, u, since)]
    return c.row(c.stamp(ls[-1]["t"]), H(" ".join(said)), seen_saw(c, mine) or None, attrs=f' data-project="{esc(u)}"')


def verb_link(c, b):
    """A verb by its name, a link to its own page; the name the line carries when the verb's object is not here."""
    v = b.get("verb")
    return thing_link(c, {"id": v}) if isinstance(v, str) and c.r.get(v) else c.w.ident(b.get("verb_name") or "")


def tally(pairs):
    """Each key once, in the order first seen, with the first value given for it and how many times it came."""
    out = {}
    for k, v in pairs:
        out[k] = (out[k][0], out[k][1] + 1) if k in out else (v, 1)
    return list(out.values())


def of_verb(ls, kind, event=None):
    return [l for l in ls if l["kind"] == kind and standing(l) and isinstance((l["body"] or {}).get("verb"), str)
            and (event is None or l["body"].get("event") == event)]


def ran(c, ls):
    """What ran by its verb since he left, a sentence each: the acts with the outside's receipt (on his yes, or under a grant named by its
    sentence), then the ones that failed outside, in the outside's first words."""
    w, out = c.w, []
    got = of_verb(ls, "receipt")
    if got:
        c.term("verb", "verb receipt")
        items = []
        for l in got:
            b = l["body"]
            r = b.get("receipt") if isinstance(b.get("receipt"), dict) else {}
            g = c.r.get(b["grant"]) if isinstance(b.get("grant"), str) else None
            g and c.term("grant")
            back = receipt_words(c, {"kind": r.get("kind"), "value": r.get("value")})
            items.append(w.t("debrief.verb.ran.grant", verb=verb_link(c, b), grant=c.words(g, "sentence") or w.ident(""), receipt=back) if g
                         else w.t("debrief.verb.ran.item", verb=verb_link(c, b), receipt=back))
        out.append(w.t("debrief.verb.ran", len(got), acts=w.count("act", len(got)), items=joined(c, items, 5)))
    bad = of_verb(ls, "note", "failed")
    if bad:
        c.term("verb")
        out.append(w.t("debrief.verb.failed", len(bad), acts=w.count("act", len(bad)), items=joined(
            c, [w.t("debrief.verb.failed.item", verb=verb_link(c, l["body"]), words=first_words(c, l, "words")) for l in bad], 5)))
    return out


def first_words(c, l, field, most=12):
    """A line's words in a sentence, twelve at most, cut at a word and marked; words kept beside the record say so."""
    ws = (words_of(l, field) or "").split()
    return c.words(dict(l, body={"text": " ".join(ws[:most]) + ("…" if len(ws) > most else "")})) if ws else c.w.t("debrief.verb.words.kept")


def host_words(w, h):
    """A host in a sentence by its words from the table, never by its id; a host the table has no words for is another host."""
    return w.t("host." + h) if isinstance(h, str) and ("host." + h, "") in w.tab else w.t("host.other")


def seen(c, ls):
    """What the hook saw leave without a yes, a sentence each: the acts of a verb with no proposal answered yes (not seen), by the verb's
    name, host and what followed; the acts that left the machine that no verb names, counted (their shape goes inside the paragraph's "What I saw"); a shell read of a secret, by how."""
    w, out = c.w, []
    host = lambda l: (l["body"] or {}).get("host") or l["by"].get("host") or ""  # noqa: E731
    blind = [l for l in of_verb(ls, "not_seen") if not l["body"].get("proposal")]  # one under a proposal waits on its receipt instead
    if blind:
        c.term("verb")
        items = [w.t("debrief.verb.notseen.quoted" if b.get("quoted") is True else "debrief.verb.notseen.item", verb=verb_link(c, b),
                     host=host_words(w, host(l)), times=w.count("time", n), outcome=w.t(OUTCOMES.get(b.get("outcome"), "ask.notseen")))
                 for (l, b), n in tally(((l["body"]["verb"], host(l), l["body"].get("outcome"), l["body"].get("quoted") is True), (l, l["body"])) for l in blind)]
        out.append(w.t("debrief.verb.notseen", len(blind), items=joined(c, items, 5)))
    gone = unknown_acts(ls)
    if gone:
        c.term("verb")
        out.append(w.t("debrief.verb.unknown", len(gone), acts=w.count("act", len(gone)),
                       hosts=joined(c, [host_words(w, h) for h, _ in tally((host(l), host(l)) for l in gone)])))
    reads = [l for l in ls if l["kind"] == "finding" and standing(l) and l["body"].get("event") == "secret read"]
    if reads:
        def how(b):
            sec = c.r.get(b["secret"]) if isinstance(b.get("secret"), str) else None
            return w.t(HOW.get(b.get("how"), "secret.named"), name=thing_link(c, sec) if sec else w.ident(""))
        out.append(w.t("debrief.verb.secret", len(reads), hosts=joined(c, [host_words(w, h) for h, _ in tally((host(l), host(l)) for l in reads)]),
                       hows=joined(c, [h for h, _ in tally(((b.get("how"), b.get("secret")), how(b)) for b in (l["body"] for l in reads))]),
                       times=w.count("time", len(reads))))
    return out


def unknown_acts(ls):
    """The acts that left the machine that no verb names (the hook's unknown act notes, but those that stayed)."""
    return [l for l in ls if l["kind"] == "note" and standing(l) and l["body"].get("event") == "unknown act" and l["body"].get("outcome") not in STAYED]


def shape_of(b):
    return b.get("command") or " ".join(x for x in b.get("shape") or [] if isinstance(x, str))


def seen_saw(c, ls):
    """The paragraph's "What I saw": each receipt's value, then the shapes of the acts that left the machine that no verb names, code names
    kept out of its sentences."""
    gone = unknown_acts(ls)
    got = [receipt_saw(c, verb_link(c, l["body"]), l["body"].get("receipt")) for l in of_verb(ls, "receipt")]
    return saw(c, got + ([c.w.t("debrief.verb.unknown.saw", commands=joined(
        c, [c.w.ident(x) for x, _ in tally((shape_of(l["body"]),) * 2 for l in gone)], 5))] if gone else []))


def waiting_on(c, cards, pending):
    """What waits on a verb, a sentence each: the proposals among the open cards (the first by its verb with its card, the rest counted),
    then the proposals answered yes with an act still without its receipt, by the verb's name, never written as done."""
    w, out = c.w, []
    asked = [x for x in cards if isinstance((x["body"] or {}).get("verb"), str)]
    if asked:
        c.term("verb")
        card = H(f'<a href="{c.href("card", id=asked[0]["id"])}">{w.t("debrief.verb.card")}</a>')
        out.append(w.t("debrief.verb.proposed", len(asked), proposals=w.count("proposal", len(asked)), verb=verb_link(c, asked[0]["body"]),
                       card=card, rest=w.count("proposal", len(asked) - 1)))
    if pending:
        out.append(yes_said(c, pending, "debrief.verb.yes"))
    return out


def yes_said(c, pending, sid, **more):
    c.term("verb", "verb receipt")
    names = [verb_link(c, p) for p, _ in tally((p["verb"], p) for p in pending)]
    return c.w.t(sid, len(pending), verbs=joined(c, names), proposals=c.w.count("proposal", len(pending)), **more)


def made(c, ls):
    """What was made since he left: the things named as links, the closes in my words, and where the project now stands (its newest
    present line), which is what the story paragraph said before the note took its place. Things of real types only: the vocabulary's
    own type and relation objects are not things made, and when the seed recorded them in the span the sentence says so in one clause."""
    objects = [x for x in ls if x["kind"] == "object" and standing(x)]
    kind = lambda x: (x["body"] or {}).get("type")
    things = [thing_link(c, x) for x in objects if kind(x) != "decision" and kind(x) not in VOCAB]
    said = [x for x in ls if x["kind"] in ("close", "present") and standing(x) and words_of(x) and x["by"]["kind"] == "partner"]
    said = sorted([x for x in said if x["kind"] == "close"] + [x for x in said if x["kind"] == "present"][-1:], key=lambda x: (x["t"], x["id"]))
    more = [c.w.t("debrief.said.more", lines=c.w.count("line", len(said) - 3))] if len(said) > 3 else []
    items = ([joined(c, things, 5)] if things else []) + [opening(c, x) for x in said[:3]] + more
    n = {v: sum(1 for x in objects if kind(x) == v) for v in VOCAB}
    seeded = c.w.t("debrief.seeded", types=c.w.count("type", n["type"]), relations=c.w.count("relation", n["relation"])) if any(n.values()) else H("")
    return c.w.t("debrief.made", things=joined(c, items), seeded=seeded) if items else c.w.t("debrief.made.none", seeded=seeded)


def opening(c, x, most=12):
    """A close or a present line named by its first words, twelve at most cut at a word and marked, as a link to its run's page (a
    present line, or a close of no run, to its project's): its whole words live there, never on the brief."""
    ws = (words_of(x) or "").split()
    run = (x["body"] or {}).get("run")
    href = c.href("run", id=run) if isinstance(run, str) and c.r.get(run) else c.href("project", unit=x["unit"])
    return H(f'<a href="{href}">{c.words(dict(x, body={"text": " ".join(ws[:most]).rstrip(".") + ("…" if len(ws) > most else "")}))}</a>')


def picked(c, u):
    """The standing decisions picked for now, newest first, each with its pick and how many picks it replaced: the decisions it
    supersedes and the pick facts it had before its present one."""
    w, items = c.w, []
    for d in reversed(c.s.things(type="decision", unit=u)):
        t = c.s.thing(d["id"])
        if (t["facets"].get("provisional") or {}).get("value") is not True:
            continue
        c.term(PICKED)
        now = t["facets"].get("pick")
        item = w.t("debrief.picked.item", thing=thing_link(c, d), pick=value_of(c, c.r.get(now["line"]))) if now else thing_link(c, d)
        had = [l for l in c.s.lines(about=d["id"], kinds=["fact"]) if (l["body"] or {}).get("facet") == "pick" and l.get("mark") not in DOWN
               and l["id"] != (now or {}).get("line")]
        n = len([x for x in c.r.out_of(d["id"], "supersedes") if x["kind"] == "object"]) + len(had)
        items.append(w.t("debrief.picked.replaced", pick=item, picks=w.count("pick", n)) if n else item)
    return w.t("debrief.picked", picks=joined(c, items, 5)) if items else w.t("debrief.picked.none")


def checked(c, u):
    """The tool's checks this ISO week, counted: those named at a close (passed, failed, not run, named after they passed), then those no
    close named; then each as its run's page says it, a red one once, its name a link to its run (C7), the first five."""
    week, w = measures.iso_week(c.now), c.w
    mine = [l for l in c.r.kind("check", units=[u]) if standing(l) and l["by"]["kind"] == "tool"]
    named_ = [l for l in mine if isinstance(l["body"].get("named_at"), str) and measures.iso_week(l["body"]["named_at"]) == week]
    ran = [l for l in mine if not isinstance(l["body"].get("named_at"), str) and measures.iso_week(l["t"]) == week]
    if not named_ and not ran:
        return w.t("debrief.checks.none")
    late = sum(1 for l in named_ if l.get("named_late"))
    late and c.term("named late")
    said = []
    for sid, ls in (("debrief.checks", named_), ("debrief.checks.ran", ran)):
        passed, failed = [l for l in ls if l["body"].get("exit") == 0], [l for l in ls if red(l)]
        notrun = len(ls) - len(passed) - len(failed)
        ls and said.append(w.t(sid, len(ls), checks=w.count("check", len(ls)), passed=w.count("passed", len(passed)), failed=w.count("failed", len(failed)),
                               late=w.t("checks.late", late=w.count("afterpassed", late)) if late else H(""),  # a failed one: said once, below (C7)
                               notrun=w.t("debrief.checks.notrun", checks=w.count("notrun", notrun)) if notrun else H("")))
    to = lambda l: c.href("run", id=l["body"]["run"]) if isinstance(l["body"].get("run"), str) and c.r.get(l["body"]["run"]) else c.href("project", unit=u)
    each = [check_said(c, l, red(l) and to(l)) for l in named_ + ran]  # by name and command in full, a red one linked to its run (R-READ-16, 17)
    return H(" ".join(said) + ul(each[:5] + [w.t("debrief.more", things=w.count("check", len(each) - 5))] * (len(each) > 5)))


def red(l):
    """A red check: a check line by the tool whose exit is a number other than 0."""
    e = (l.get("body") or {}).get("exit")
    return l["kind"] == "check" and l["by"]["kind"] == "tool" and isinstance(e, int) and not isinstance(e, bool) and e != 0


def check_said(c, l, to=None):
    """A check as the run's page and the brief say it: its name (a link to `to` when given), passed or not with its exit, its command in
    full; one the tool did not run says so, with the command it would have run and its line's reason, and never that it ran."""
    w, b = c.w, l["body"] or {}
    name = c.words(l, "name") or w.ident("")
    say = dict(name=H(f'<a href="{to}">{name}</a>') if to else name, command=H(f'<code>{w.ident(b.get("command") or "")}</code>'))
    if not red(l) and not (l["by"]["kind"] == "tool" and b.get("exit") == 0 and b.get("exit") is not False):
        return w.t("run.check.notrun", why=w.t("run.check.notrun.why", why=c.words(l, "text")) if c.words(l, "text") else H(""), **say)
    return w.t("run.check", result=w.t("run.check.failed", exit=w.num(b["exit"])) if red(l) else w.t("run.check.passed"), **say)


def assumed(c, u, since):
    """What I read and took as true without asking: the standing goals and assumptions written since his last line, or since a run of
    the project still open began, each linked to the thing it is about; always the paragraph's last sentence."""
    r, w = c.r, c.w
    ended = {(l["body"] or {}).get("run") for l in r.kind("close", "abandoned", units=[u])}
    first = min((x["t"] for x in r.kind("run", units=[u]) if standing(x) and x["id"] not in ended), default=None)
    ls = [l for l in r.kind("assumption", "goal", units=[u]) if standing(l) and (since is None or l["t"] > since or (first and l["t"] >= first))]
    c.assumed_n[u] = sum(1 for l in ls if l["kind"] == "assumption")
    items = []
    for l in ls:
        c.term(l["kind"])
        text = c.words(l) or named(w, "kind.", l["kind"])
        text = H(f'<a href="{c.href("thing", id=l["about"])}">{text}</a>') if l.get("about") and r.get(l["about"]) else text
        items.append(w.t("debrief.assumed.goal", goal=text) if l["kind"] == "goal" else text)
    return w.t("debrief.assumed", items=joined(c, items)) if items else w.t("debrief.assumed.none")


def held_rows(c, held):
    """What came in line by line, on the brief: deletions, a failed hook and a refusal row by row (rulings 7 and 8, promise 5); the rest
    counted in one sentence each (acts outside a grant, asks, days not seen, other lines), with the projects whose page shows them."""
    rows = [row for _, kind, _, row in held if kind == "shown"]
    for what, sid, terms in (("outside", "debrief.outside", ("grant",)), ("ask", "debrief.asks", ("host",)),
                             ("notseen", "debrief.notseen", ("host", "notseen")), ("line", "debrief.lines", ())):
        mine = [(us, n) for us, kind, n, _ in held if kind == what]
        if mine:
            c.term(*terms)
            units, n = sorted({u for us, _ in mine for u in us}), sum(n for _, n in mine)
            rows.append(c.row("", c.w.t(sid, n, lines=c.w.count("line", n), projects=joined(c, [project_link(c, u) for u in units]))))
    return rows


def since_rows(c, pool, since, new, held=None):
    """What came in, line by line; with held, every row goes there instead, as its projects, what it is (shown on the brief row by row,
    an act outside a grant, an ask, a day not seen, or another line), how many lines it names and the row, and none is returned."""
    r, w, rows = c.r, c.w, []
    term = c.term if held is None else (lambda *names: None)  # a word the page does not show is not glossed on it
    host = lambda l: w.ident((l["body"] or {}).get("host") or l["by"].get("host") or "")
    hd = lambda l: ((l["body"] or {}).get("host") or l["by"].get("host"), r.day(l["t"]))
    blind = lambda l: l["kind"] == "host_ask" and (l["body"] or {}).get("asked") is None and (l["body"] or {}).get("answer") == "not seen"
    about = {(x["body"] or {}).get("about") for x in r.cards()}

    def first(l):  # a said line's first eight words, so a line the maker did not type shows (card 9), read from its payload when kept beside
        ws, kept = (words_of(l) or r.opening(l) or "").split(), words_of(l) is None
        return ws and c.words(dict(l, body={"text": " ".join(ws[:8]) + ("…" if len(ws) > 8 or kept else "")})) or w.t("kind.said.row")

    def act(l):  # the act as the host's line names it: a day-one key from the table, else the line's own words
        a = (l["body"] or {}).get("act")
        return w.t("act." + a) if a in ACTS else (c.words(l, "act") or w.ident((l["body"] or {}).get("tool") or ""))

    def keep(units, row, what="line", n=1):
        held.append((units, what, n, row)) if held is not None else rows.append(row)

    def add(l, text, what="line"):
        keep({l["unit"]}, c.row(c.stamp(l["t"]), text, c.meta(l, project=True), attrs=f' data-line="{l["id"]}"'), what)
    calls = []
    for l in new:
        b, k = l["body"] or {}, l["kind"]
        outcome = w.t(OUTCOMES.get(b.get("answer") if k == "host_ask" else b.get("outcome"), "ask.notseen"))
        if k == "host_ask":
            sid = "row.asknotseen" if blind(l) else "row.unasked" if b.get("asked") is False else "row.ask"  # seen only at catch-up: no ask
            add(l, w.t(sid, host=host(l), act=act(l), answer=outcome), "ask")
            term("notseen" if blind(l) else "host")
        elif k == "host_ran" and b.get("grant") in (None, "", "none"):
            add(l, w.t("row.outside", host=host(l), act=act(l), outcome=outcome), "outside")
            term("grant")
        elif k in ("hook", "note") and not b.get("verb") and (b.get("failed") is True or b.get("event") in FAILED or b.get("outcome") == "failed"):
            add(l, w.t("row.hookfail", host=host(l)), "shown")
        elif k == "delete" and l["by"]["kind"] == "partner":
            hold = next((h for h in c.s.holds() if h["delete"] == l["id"]), None)
            word = w.t("word.undelete")
            text = (w.t("row.deleted", project=c.project(l["unit"]), date=w.date(hold["end"]), word=word) if hold and hold.get("end")
                    else w.t("row.deleted.waiting", project=c.project(l["unit"]), word=word))
            add(l, text + ul([c.words(l, "why")]), "shown")
            c.term("deleted", "hold")
        elif k in ("moment", "recall") and (b.get("applied") or b.get("may_apply")):
            add(l, w.t("row.applied" if b.get("applied") else "row.mayapply", project=c.project(l["unit"])) + ul([c.words(l, "query")]))
            term("ruling")
        elif b.get("event") == "memory-read":
            add(l, H(w.t("row.memory", host=host(l)) + saw(c, [w.ident(b.get("path") or "")])))
        elif b.get("event") == "refused" and b.get("via") == "mcp":  # a refused call of the partner's to the tool (command.mcp), not a page
            calls.append(l)  # request, which carries its status and path: counted in one sentence after the loop
        elif k == "release" and b.get("event") == "refused":  # a release the tool refused (command.update.offer), its reason behind what I saw
            add(l, H(w.t("row.refused.release") + saw(c, [w.ident(b.get("reason") or "")])), "shown")
        elif b.get("event") == "refused":
            add(l, w.t("row.refused") + ul([c.words(l)]), "shown")
        elif k == "flow" and b.get("event") == "stalled":
            add(l, w.t("row.stall", step=named(w, "cli.step.", b.get("step")), cause=named(w, "stall.", b.get("cause"))) + ul([c.words(l, "words")]))
        elif k == "answer" and b.get("stale"):
            add(l, w.t("row.stale") + ul([c.words(l, "words") or w.t("answer." + b.get("answer", "later"))]))
        elif k == "answer" and (b.get("presence") == "none" or b.get("person") == "not established" or l["by"]["kind"] != "maker"):
            add(l, w.t("row.nobody"))
        elif k == "grant" and l["by"]["kind"] == "partner" and l["id"] not in about and c.s.grant_state(l["id"]) == "read_back":
            add(l, w.t("row.grantwaits") + ul([c.words(l, "sentence")]))
            term("grant")
        elif k == "said" and b.get("surface") == "relayed":
            add(l, w.t("row.relayed", host=host(l), sender=w.ident(b.get("from") or "")) + ul([first(l)]))
    calls and keep({l["unit"] for l in calls}, c.row("", w.t("row.refused.calls", len(calls), times=w.count("time", len(calls))), saw(c, [w.ident(
        f'{(l["body"] or {}).get("verb") or ""}: {(l["body"] or {}).get("why") or ""}') for l in calls])), "shown", len(calls))
    eve = since and (_dt.datetime.fromisoformat(since) - _dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    mine = [l for l in r.kind("said", units=pool, since=eve) if since and l["by"]["kind"] == "maker" and l["t"] <= since and standing(l)]
    mine and keep({l["unit"] for l in mine}, c.row("", w.t("row.yours") + ul([H(first(l) + c.meta(l, project=True)) for l in mine])), n=len(mine))
    seen, asked = r.hosts(since, pool)
    asked -= {hd(l) for l in new if blind(l)} - {hd(l) for l in new if l["kind"] == "host_ask" and not blind(l)}
    told = {hd(l) for l in new if l["kind"] == "not_seen" or blind(l)}
    for h in sorted(seen):
        for day in sorted(seen[h] | {d for x, d in told if x == h}):
            if (h, day) not in asked:
                row = c.row("", w.t("row.notseen", host=w.ident(h), date=w.date(day + "T12:00:00")))
                keep({l["unit"] for l in new if r.day(l["t"]) == day and h in ((l["body"] or {}).get("host"), l["by"].get("host"))}, row, "notseen")
                term("notseen")
    return rows


def outside_budget(card):
    """A card counted outside the asking budget and kept out of what needs him: one of the move's (card 23), or the week's card of proposals."""
    return bool((card["body"] or {}).get("move") or (card["body"] or {}).get("week_card"))


def good_rows(c, pool, since):
    r, w, rows = c.r, c.w, []
    s, today = setting(c), r.today()
    week = (c.now - _dt.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    todays = [x for x in r.kind("card", units=pool) if r.day(x["t"]) == today and not (x["body"] or {}).get("act") and not outside_budget(x)]
    limit = LIMITS[s]
    if limit is None:
        rows.append(c.row("", w.t("good.cards.often", cards=w.count("card", len(todays)))))
    else:
        rows.append(c.row("", w.t("good.cards", cards=w.count("card", len(todays)), setting=w.t("setting." + s), limit=w.count("card", limit))))
        if len(todays) > limit:
            rows.append(c.row("", w.t("good.over", cards=w.count("card", len(todays) - limit))))
    weekly = [x for x in r.open_cards(pool) if (x["body"] or {}).get("week_card")]  # outside the budget, as the move's (design section 2 point 4)
    if weekly:
        c.term("card")
        rows.append(c.row("", w.t("good.week", len(weekly), cards=joined(c, [H(f'<a href="{c.href("card", id=x["id"])}">'
                                                                            f'{c.words(x, "decides") or w.t("card.missing")}</a>') for x in weekly]))))
    moved = [x for x in r.open_cards(pool) if (x["body"] or {}).get("move")]  # card 23: outside the budget, opened as the maker likes
    if moved:
        c.term("card")
        more = [H(f'<a href="{c.href("cards")}">{w.t("good.move.more", n=w.num(len(moved) - 5))}</a>')] if len(moved) > 5 else []
        rows.append(c.row("", w.t("good.move", cards=w.count("card", len(moved))) + ul(
            [H(f'<a href="{c.href("card", id=x["id"])}">{c.words(x, "decides") or w.t("card.missing")}</a>') for x in moved[:5]] + more)))
    weeks = r.kind("card", units=pool, since=week)
    needless = len(r.kind("needless", units=pool, since=week))
    if needless:  # none called needless is not news (C7)
        c.term("needless")
        rows.append(c.row("", w.t("good.needless", n=w.num(needless), cards=w.count("card", len(weeks)))))
    again = [x for x in r.cards(pool) if ((x["body"] or {}).get("version") or 1) > 1 and not words_of(x, "changed")]
    if again:
        rows.append(c.row("", w.t("good.nochange", cards=w.count("card", len(again)))))
    nxt = ([l for l in r.kind("close", units=pool) if standing(l) and words_of(l, "next")]
           or [l for l in r.kind("present", units=pool) if standing(l) and words_of(l, "next")])
    if nxt:
        rows.append(c.row("", w.t("good.nextup") + ul([c.words(nxt[-1], "next")]), c.meta(nxt[-1], project=True)))
    for bet in [x for x in r.kind("bet", units=pool) if standing(x)]:
        c.term("bet")
        items = [H(w.t(sid) + " " + (c.words(bet, f) or w.t("card.missing"))) for f, sid in
                 (("direction", "bet.direction"), ("would_show", "bet.show"), ("by", "bet.by"))]
        rows.append(c.row("", w.t("good.bet") + ul(items), c.meta(bet, project=True)))
    scoped = {(x["body"] or {}).get("host"): x["body"] for x in r.kind("note", units=pool) if (x["body"] or {}).get("event") == "scope read back"}
    for h, b in sorted((h, b) for h, b in scoped.items() if isinstance(h, str)):  # each host's newest read back of its user scope (batch C, task 12)
        found = [f for f in b.get("found") or [] if isinstance(f, dict)]
        off = [f for f in found if f.get("scope") == "user" and (f.get("key"), f.get("value")) in SANDBOX_OFF]
        rows += [c.row("", w.t("good.sandboxoff", host=H(esc(h))))] if off else []
        rows += [c.row("", w.t("good.scope", host=H(esc(h)), key=w.ident(str(f.get("key") or ""))),  # the adapter's English only in what I saw
                       saw(c, [w.ident(str(f["what"]))] if f.get("what") else [])) for f in found if f not in off]
    newest = r.kind("run", units=pool, since=week)  # the newest run of the last seven days, its cost and its model (batch D, task 14)
    cost = measures.run_cost(r.all(), newest[-1], measures.prices(c.root)) if newest else None
    if cost and cost["tokens"]:
        c.term("run", "host")
        hits = [h for h in c.s.resolve(cost["model"]) if h["type"] == "model"] if cost["model"] else []
        model = (thing_link(c, hits[0]) if len(hits) == 1 else w.t("good.run.model.none")) if cost["model"] else w.t("good.run.model")
        seen = saw(c, [w.ident(cost["model"])]) if cost["model"] and len(hits) != 1 else None  # an id no one thing holds: behind what I saw
        if len(cost["models"]) > 1:  # several models: counted in the sentence, each with its tokens behind what I saw (Astra's finding 11)
            model = w.t("good.run.models", models=w.count("model", len(cost["models"])))
            seen = saw(c, [w.t("good.run.model.tokens", model=w.ident(m), tokens=w.count("token", n)) for m, n in cost["models"].items()])
        run = H(f'<a href="{c.href("run", id=newest[-1]["id"])}">{c.words(newest[-1], "purpose") or w.t("run.nopurpose")}</a>')
        if cost["money"] is None:
            c.term("notseen")
            rows.append(c.row("", w.t("good.run.cost", run=run, tokens=w.count("token", cost["tokens"]), model=model), seen))
        else:
            money = w.t("good.run.priced" if cost["priced"] else "measure.m8.reported", money=w.count("usd", cost["money"]))
            part = {"lines": w.count("line", cost["unpriced"])} if cost["unpriced"] else {}  # some usage had no price: at least, and how many
            rows.append(c.row("", w.t("good.run.cost.part" if part else "good.run.cost.money", run=run, tokens=w.count("token", cost["tokens"]),
                                      money=money, model=model, **part), seen))
    unsettled = [l for l in r.kind("close", units=pool, since=week) if standing(l) and (l["body"] or {}).get("rests_on") == "nothing settled"]
    if unsettled:  # the state test as a rule of runs (batch E, Task 13): counted, never refused
        c.term("run")
        rows.append(c.row("", w.t("good.unsettled", len(unsettled), runs=w.count("run", len(unsettled)))))
    for l in [l for l in r.kind("check", units=pool, since=week) if standing(l) and l.get("world_moved")]:  # batch E, Task 15
        b = l["body"] or {}
        to = c.href("run", id=b["run"]) if isinstance(b.get("run"), str) and r.get(b["run"]) else c.href("project", unit=l["unit"])
        rows.append(c.row("", w.t("good.worldmoved", check=H(f'<a href="{to}">{c.words(l, "name") or w.ident("")}</a>')),
                          saw(c, [w.ident(str(b.get("command") or ""))])))
    rows += verb_rows(c, pool, week)
    if c.welcome_text is None and r.kind("move"):
        rows.append(c.row("", w.t("good.welcome")))
    return rows


def verb_rows(c, pool, week):
    """Good to know about the verbs, a sentence each: the acts not seen this week, by verb; on the workshop's brief the declared verbs no
    command shape fences, whose card is all that asks; the verbs I proposed that wait for the week's card."""
    w, rows = c.w, []
    blind = [l for l in of_verb(c.r.kind("not_seen", units=pool, since=week), "not_seen") if not l["body"].get("proposal")]
    if blind:
        c.term("verb")
        by = tally((l["body"]["verb"], l["body"]) for l in blind)  # each verb with its own count only when more than one is named
        items = [w.t("good.verb.notseen.item", verb=verb_link(c, b), acts=w.count("act", n)) if len(by) > 1 else verb_link(c, b) for b, n in by]
        rows.append(c.row("", w.t("good.verb.notseen", acts=w.count("act", len(blind)), verbs=joined(c, items))))
    bare = declared.unfenced(c.s) if "workshop" in pool else []
    if bare:
        c.term("verb", "card")
        rows.append(c.row("", w.t("good.verb.unfenced", len(bare), verbs=w.count("verb", len(bare)),
                                  names=joined(c, [thing_link(c, {"id": v["id"]}) for v in bare]))))
    mine = [x for x in declared.queued(c.s) if x["unit"] in pool]
    if mine:
        c.term("verb", "card")
        rows.append(c.row("", w.t("good.verbs.proposed", len(mine), verbs=w.count("verb", len(mine)),
                                  names=joined(c, [c.words(x, "name") or w.ident("") for x in mine], 5))))
    return rows


def host_cost_rows(c, pool, since):
    """Each host's tokens since his last line and this ISO week, the window the week's cost reads (measures.m8), and the money it reports;
    and the hosts that reported none, joined."""
    r, w, rows, silent = c.r, c.w, [], []
    week = measures.midnight(measures.bounds(measures.iso_week(c.now))[0])
    use = r.kind("usage", units=pool, since=week)
    seen, _ = r.hosts(week, pool)
    for h in sorted(set(seen) | {(u["body"] or {}).get("host") for u in use} - {None}):
        mine = [u["body"] or {} for u in use if (u["body"] or {}).get("host") == h]
        night = [u["body"] or {} for u in use if (u["body"] or {}).get("host") == h and (since is None or u["t"] > since)]
        if not mine:
            silent.append(w.ident(h))
            c.term("notseen")
            continue
        tok = lambda bs: sum((b.get("tokens_in") or 0) + (b.get("tokens_out") or 0) for b in bs)
        rows.append(c.row("", w.t("good.cost", host=w.ident(h), night=w.count("token", tok(night)), week=w.count("token", tok(mine)))))
        if any(b.get("cost") is not None for b in mine):
            usd = lambda bs: round(sum(b.get("cost") or 0 for b in bs), 2)
            rows.append(c.row("", w.t("good.cost.money", host=w.ident(h), night=w.count("usd", usd(night)), week=w.count("usd", usd(mine)))))
    return rows, joined(c, silent) if silent else None


def project(c, unit):
    return brief(c, unit)


def move_cards(c):
    """Every open card of the move (card 23), oldest first, each its decides line linking to its card page: what the brief's and-more opens."""
    r, w = c.r, c.w
    moved = [x for x in r.open_cards() if (x["body"] or {}).get("move")]
    c.term("card")
    rows = [c.row(w.ident(i), H(f'<a href="{c.href("card", id=x["id"])}">{c.words(x, "decides") or w.t("card.missing")}</a>'), c.meta(x, project=True))
            for i, x in enumerate(moved, 1)]
    body = (c.part("part.move", len(moved), "card", w.t("sum.move"), rows or [c.row("", w.t("move.none"))])
            + c.part("part.good", 1, "item", w.t("sum.good"), [c.row("", w.t("good.move.budget"))]))
    return c.page(w.t("title.cards"), w.t("why.cards", cards=w.count("card", len(moved))), H(""), body, view="cards")


def card(c, id):
    r, w = c.r, c.w
    x = r.get(id)
    others = r.open_cards([x["unit"]])
    n = max(len(others), 1)
    i = next((k for k, o in enumerate(others, 1) if o["id"] == id), 1)
    row = card_row(c, x, i, n, True)
    lines = [r.get(x["body"]["about"])] if isinstance((x["body"] or {}).get("about"), str) else []
    open_ = x in others
    rows = ([] if open_ else [row]) + [c.line_row(l, project=True) for l in lines + r.answers(id) if l]  # answered, the card heads its part
    body = needs(c, [x] if open_ else [], [row]) + c.part("part.card.about", len(rows), "line", w.t("sum.card.since"), rows)
    if not open_:
        c.cards = []
    return c.page(w.t("title.card.open" if open_ else "title.card.done"), w.t("why.card" if open_ else "why.card.done"), H(""), body,
                  where=w.t("top.project", project=c.project(x["unit"])), view="card")


# a run
def run(c, id):
    r, w = c.r, c.w
    d = r.run(id)
    u, span = d["run"]["unit"], d["lines"]
    c.term("run")
    rows = []
    for l in span:
        if l["kind"] in ("acceptance",):
            continue
        cls = "said you" if l["by"]["kind"] == "maker" else "said" if l["by"]["kind"] == "partner" else ""
        said = (check_said(c, l) if l["kind"] == "check" else w.t("run.began") if l["id"] == id  # its purpose is the title's, said once
                else c.words(l) or w.t("kind." + l["kind"] + ".row"))
        about = "".join(w.t("line.about", cls="meta", project=c.project(t["unit"])) for t in r.out_of(l["id"], "part_of") if t["unit"] != l["unit"])
        rows.append(c.row(c.stamp(l["t"]), H(f'<span class="{cls}"><span class="who">{c.who(l)}</span> {said}</span>'),
                          H(c.mark(l.get("mark")) + c.meta(l) + about), cls="row said" if cls else "row"))
    about = c.s.thing(d["run"]["about"]) if isinstance(d["run"].get("about"), str) else None
    asked = [q for q in (about or {}).get("questions") or [] if question_state(r, q) == "open"]
    notes = [l for l in r.into(id, "part_of") if l["kind"] == "note" and (l["body"] or {}).get("event") == "pre-mortem"]
    good = (goal_rows(c, [g for g in r.out_of(id, "serves") if g["kind"] == "goal"])
            + assumption_rows(c, [a for a in r.out_of(id, "came_from") if a["kind"] == "assumption"])
            + question_rows(c, asked) + premortem_rows(c, notes) + (acceptance_rows(c, d) or named_rows(c, d)))
    taught = [l for l in span if l["kind"] == "learned"] or [l for l in span if words_of(l, "learned")]
    changed = [l for l in span if l["kind"] == "changed"] or [l for l in span if words_of(l, "changed")]
    if d["end"]:
        good.append(c.row("", w.t("run.taught") + ul([c.words(l, None if l["kind"] == "learned" else "learned") for l in taught])
                          if taught else w.t("run.no-taught")))
        good.append(c.row("", w.t("run.changed") + ul([c.words(l, None if l["kind"] == "changed" else "changed") for l in changed])
                          if changed else w.t("run.no-changed")))
    if d["state"] == "abandoned":
        good.append(c.row("", w.t("run.abandoned") + ul([c.words(d["end"])])))
    for bet in (x for x in r.out_of(id, "serves") if x["kind"] != "goal"):
        c.term("bet")
        good.append(c.row("", w.t("run.bet") + ul([c.words(bet, "direction")])))
    end_t = d["end"]["t"] if d["end"] else "9999"
    use = [l["body"] or {} for l in r.kind("usage", units=[u]) if d["run"]["t"] <= l["t"] <= end_t]
    good.append(c.row("", w.t("run.cost", tokens=w.count("token", sum((b.get("tokens_in") or 0) + (b.get("tokens_out") or 0) for b in use)))
                      if use else w.t("run.cost.none")))
    cards = [x for x in r.open_cards([u]) if (x["body"] or {}).get("about") == id]
    state = w.t("run.state." + d["state"])
    end = d["end"] if d["end"] and words_of(d["end"]) else None  # the story box holds this run's own closing line, else no box (C4)
    body = (needs(c, cards, card_rows(c, cards))
            + c.part("part.started", len(rows), "line", w.t("sum.run.since"), rows)
            + c.part("part.good", len(good), "item", w.t("sum.run.good"), good))
    return c.page(c.words(d["run"]) or w.t("title.run"), w.t("why.run", project=c.project(u), state=state, lines=w.count("line", len(span))),  # L4
                  c.story(end) if end else H(""), body, where=w.t("top.run", project=c.project(u)), view="run")


def acceptance_rows(c, d):
    r, w, rows = c.r, c.w, []
    lists = [l for l in r.kind("acceptance", units=[d["run"]["unit"]]) if (l["body"] or {}).get("run") == d["run"]["id"]]
    if not lists:
        return rows
    checks = [l for l in d["lines"] + r.into(d["run"]["id"], "part_of") if l["kind"] == "check" and standing(l)]
    items = []
    for item in (lists[0]["body"] or {}).get("checks") or []:
        ran = [x for x in checks if (x["body"] or {}).get("name") == item.get("name") and (x["body"] or {}).get("exit") == 0
               and c.s.payload_path(((x["body"] or {}).get("output") or {}).get("payload") or "")]
        ok = [x for x in ran if (x["body"] or {}).get("command") == item.get("command")]  # only the command named before the run proves it
        other = w.t("run.check.command") if ran and not ok else ""
        items.append(H(c.mark("proved" if ok else "not yet") + f'<span data-l="{lists[0]["id"]}" dir="auto">{esc(item.get("name", ""))}</span> {other}'))
    rows.append(c.row("", w.t("run.acceptance") + ul(items), c.meta(lists[0])))
    for extra in lists[1:]:
        rows.append(c.row(c.stamp(extra["t"]), w.t("run.check.edit"), c.meta(extra)))
    return rows


# what the partner knows, where he looks: the goal read back, the assumptions, the open questions, the pre-mortems and the checks named
# at close (03-design.md section 4 points 2 to 4 and 9, section 5 point 2); the run page and a thing's page show them in their own parts
def goal_rows(c, goals):
    """Each goal read back in my words, beside it the words of yours it came from with who and when, what would show it reached, and
    your words since this reading (your "no, I mean"), until a newer goal replaces it."""
    r, w, rows = c.r, c.w, []
    for g in goals:
        c.term("goal")
        frags = [r.get(f) for f in (g["body"] or {}).get("fragments") or [] if isinstance(f, str)]
        items = [H(w.t("goal.from") + ul(H((c.words(f) or named(w, "kind.", f["kind"] + ".row")) + c.meta(f)) for f in frags if f))]
        shows = c.words(g, "shows")
        shows and items.append(H(w.t("goal.shows") + " " + shows))
        end = min(((x["t"], x["seq"]) for x in r.into(g["id"], "supersedes") if x["kind"] == "goal"), default=("9999", 0))
        since = [l for l in r.kind("said", units=[g["unit"]]) if l["by"]["kind"] == "maker" and standing(l) and l not in frags
                 and (g["t"], g["seq"]) < (l["t"], l["seq"]) < end]
        since and items.append(H(w.t("goal.since") + ul(H(c.words(l) + c.meta(l)) for l in since if c.words(l))))
        rows.append(c.row("", H(w.t("goal.read") + " " + (c.words(g) or w.t("card.missing")) + ul(items)), H(note_mark(c, g) + c.meta(g))))
    return rows


def assumption_rows(c, lines):
    """What I took as true without asking, each written before the work and strikeable."""
    lines and c.term("assumption")
    return [c.row("", c.w.t("thing.assumed", text=c.words(a) or c.w.t("card.missing")), H(note_mark(c, a) + c.meta(a))) for a in lines]


def question_rows(c, qs):
    """Each open question in its words, with who could settle it, what leaving it open costs, the day it lapses, and where it stands."""
    w, rows = c.w, []
    for q in qs:
        c.term("question")
        missing = w.t("card.missing")
        until = w.date(q["valid_until"] + "T12:00:00+00:00") if q.get("valid_until") else missing
        who = w.t("thing.question.who", settles=w.t("question.settles", who=c.words(q, "settles") or missing),
                  cost=w.t("question.cost", cost=c.words(q, "cost") or missing), asked=w.date(q["t"]), until=w.t("question.until", date=until))
        rows.append(c.row("", c.words(q) or named(w, "kind.", q["kind"] + ".row"), H(who + " " + w.t("question.state." + question_state(c.r, q), cls="state"))))
    return rows


def premortem_rows(c, notes):
    """The one line written before anything costly: if this fails in a week, it will be because."""
    notes and c.term("premortem")
    return [c.row("", H(c.w.t("premortem.row") + " " + (c.words(n) or c.w.t("card.missing"))), H(note_mark(c, n) + c.meta(n))) for n in notes]


def proves(c, line):
    """A check that proves, as the index reads one (store/index.py, proving): standing, by the tool, exit 0, its output kept, and not
    followed by a newer check, whether linked by follows or the newer standing check of the same run and name (as runs.passes reads)."""
    b = (line or {}).get("body") or {}
    out = b.get("output") if isinstance(b.get("output"), dict) else {}
    if not (line and standing(line) and line["by"]["kind"] == "tool" and b.get("exit") == 0 and c.s.payload_path(out.get("payload") or "")):
        return False
    same = lambda x: x["kind"] == "check" and standing(x) and ((x["body"] or {}).get("run"), (x["body"] or {}).get("name")) == (b.get("run"), b.get("name"))
    return not any(x["kind"] == "check" and standing(x) for x in c.r.into(line["id"], "follows")) and not any(
        same(x) and (x["t"], x["id"]) > (line["t"], line["id"]) for x in c.r.kind("check", units=[line["unit"]]))


def named_rows(c, d):
    """A run whose close names its checks: how many, how many were named after they had passed, and each with its mark (proved when it
    proves as the index reads a check, see proves) and named after it passed when the index says so; each command and receipt in what I saw."""
    r, w = c.r, c.w
    end = d["end"] if d["end"] and d["end"]["kind"] == "close" else None
    named_ = [x for x in ((end or {}).get("body") or {}).get("checks") or [] if isinstance(x, dict)]
    if not named_:
        return [c.row("", w.t("run.named.none.ran" if any(l["kind"] == "check" for l in d["lines"]) else "run.named.none"))] if end else []
    items, seen, late = [], [], 0
    for x in named_:
        line = r.get(x["check"]) if isinstance(x.get("check"), str) else None
        ok = proves(c, line)
        name = (c.words(line, "name") if line else None) or w.ident(x.get("name") or "")
        tail = ""
        if line and line.get("named_late"):
            late += 1
            c.term("named late")
            tail = " " + w.t("run.named.late", cls="state")
        items.append(H(c.mark("proved" if ok else "not yet") + name + tail))
        seen.append(w.t("run.named.saw", name=w.ident(x.get("name") or ""), command=w.ident(x.get("command") or ""), line=w.ident(x.get("check") or "")))
    head = w.t("run.named", len(named_), checks=w.count("check", len(named_)), late=w.t("checks.late", late=w.count("late", late)) if late else H(""))
    return [c.row("", H(head + ul(items) + saw(c, seen)), c.meta(end))]


# the present page, as a view and as its file; it opens on the unit's things (03-design.md section 9 point 6)


def present_things(c, unit):
    """The unit's standing things by type, in the order first recorded, never a type, a relation or a verb; and its standing picks, each
    decision of the unit with its newest pick fact and whether its provisional facet is true."""
    by, picks = {}, []
    for x in c.s.things(unit=unit):
        if x["type"] not in ("type", "relation", "verb"):
            by.setdefault(x["type"], []).append(x)
    for x in by.get("decision", []):
        t = c.s.thing(x["id"])
        now = t["facets"].get("pick")  # a decision's pick is one facet, pick, as batch A's thing page writes it
        now and picks.append((x, c.r.get(now["line"]), (t["facets"].get("provisional") or {}).get("value") is True))
    return by, picks


def present(c, unit):
    r, w = c.r, c.w
    p = r.present(unit)
    c.term("present")
    by, picks = present_things(c, unit)
    things = [c.row("", H(w.t("present.type", type=type_words(c, k), count=w.count("thing", len(v))) + ul(thing_link(c, x) for x in v)))
              for k, v in by.items()]
    for x, line, fornow in picks:
        fornow and c.term(PICKED)
        things.append(c.row("", H(w.t("present.pick", thing=thing_link(c, x), pick=value_of(c, line))
                                  + (w.t("read.sep") + w.t("present.pick.fornow") if fornow else "")), basis_of(c, line)))
    by and c.term("thing", "type")
    closes = []
    for cl in p["closes"]:
        checked = [H(c.mark(x.get("mark")) + (c.words(x, "name") or c.words(x) or w.t(f"kind.{x['kind']}.row")) + c.meta(x)) for x in p["checks"][cl["id"]]]
        closes.append(c.line_row(cl, why=ul([H(w.t("present.checks") + ul(checked))]) if checked else None))
    last = [l for l in r.unit(unit) if l["by"]["kind"] == "maker" and l["kind"] == "said"][-1:]  # his newest struck: said so, not an older one
    maker = [c.row("", w.t("present.maker.struck"))] if last and last[0].get("mark") == "struck" else [c.line_row(p["maker"])] if p["maker"] else []
    good = [c.line_row(l, why=None) for l in r.unit(unit) if l["kind"] == "note" and (l["body"] or {}).get("event") == "file edit"][-3:]
    if p["stale"]:
        c.term("stale")
        good.append(c.row("", w.t("present.stale", date=w.date(p["stale"]["t"])) + ul([c.words(p["stale"])])))
    body = (c.part("present.things", sum(map(len, by.values())), "thing", w.t("sum.present.things"), things or [c.row("", w.t("present.none.things"))])
            + c.part("present.closes", len(closes), "line", w.t("sum.present.closes"), closes or [c.row("", w.t("present.none.close"))])
            + c.part("present.maker", len(maker), "line", w.t("sum.present.maker"), maker or [c.row("", w.t("present.none.maker"))])
            + c.part("part.good", len(good), "item", w.t("sum.good"), good))
    return c.page(w.t("title.present"), w.t("why.present", project=c.project(unit)), c.story(r.story([unit])), body,
                  where=w.t("top.project", project=c.project(unit)), head=p["head"], view="present")


def present_md(c, unit):
    """where-it-stands.md: the same projection as plain markdown; two projections of one record are byte-identical."""
    r, w = c.r, c.w
    p = r.present(unit)
    line = lambda l: [f"- {plain(w.t('md.line', when=w.when(l['t']), who=c.who(l), mark=w.t('mark.' + (l.get('mark') or 'recorded'))))}",
                      "  " + (words_of(l) or w.plain("mark.gone" if l["body"] is None else "kind." + l["kind"] + ".row")).replace("\n", "\n  ")]
    out = [f"# {w.plain('md.title', project=unit)}", "", w.plain("md.projected", id=p["head"] or "-"), "", f"## {w.plain('present.things')}", ""]
    by, picks = present_things(c, unit)
    for k, v in by.items():
        out += [f"- {w.plain('present.type', type=type_words(c, k), count=w.count('thing', len(v)))}"]
        out += [f"  - {words_of(c.r.get(x['id']), 'name') or x['name']}" for x in v]
    for x, got, fornow in picks:
        out += [f"- {w.plain('present.pick', thing=words_of(c.r.get(x['id']), 'name') or x['name'], pick=plain(value_of(c, got)))}"
                + (w.raw("read.sep") + w.plain("present.pick.fornow") if fornow else "")]
    out += ([] if by else [w.plain("present.none.things")]) + ["", f"## {w.plain('present.closes')}", ""]
    for cl in p["closes"]:
        out += line(cl)
        for x in p["checks"][cl["id"]]:
            out += ["  " + s for s in line(x)]
    out += [] if p["closes"] else [w.plain("present.none.close")]
    out += ["", f"## {w.plain('present.maker')}", ""] + (line(p["maker"]) if p["maker"] else [w.plain("present.none.maker")])
    if p["stale"]:
        out += ["", w.plain("present.stale", date=w.date(p["stale"]["t"]))]
    return "\n".join(out) + "\n"


def grants_md(c, unit):
    w, r = c.w, c.r
    out = [f"# {w.plain('md.grants', project=unit)}", ""]
    gs = r.kind("grant", units=[unit])
    for g in gs:
        st = c.s.grant_state(g["id"]) or "read_back"
        out += [f"- {plain(w.t('md.line', when=w.when(g['t']), who=c.who(g), mark=w.t('mark.' + (g.get('mark') or 'recorded'))))}"]
        out += [f"  {plain(w.t(sid))}: {(g['body'] or {}).get(f)}" for f, sid in (("sentence", "grant.sentence"), ("reading", "grant.reading"),
                                                                                  ("until", "grant.until"), ("take_back", "grant.takeback")) if g["body"]]
        out += [f"  {w.plain('md.grant.state', state=w.plain('grant.state.' + st))}", ""]
    return "\n".join(out + ([] if gs else [w.plain("md.grants.none")])) + "\n"


# find, and its three questions (03-design.md section 9 point 4): about a thing, by a basis, what rests on a strike, each asked by its
# first word and a colon, in English or in the table's Arabic; every hit names the thing it is about
QUESTIONS = ("find.about", "find.basis", "find.restson")


def bare(s):
    return " ".join(strip_arabic_marks(str(s)).split()).lower()


def asked(c, q):
    """The question a query opens with (its word and a colon, in either language) and the rest of the query; else None and the query."""
    b = bare(q)
    for sid in QUESTIONS:
        for word in {bare(c.w.tab[(sid, "")][col]) for col in ("en", "ar")}:
            if b.startswith(word) and b[len(word):].lstrip().startswith(":"):
                return sid, b[len(word):].lstrip()[1:].strip()
    return None, q


def basis_asked(c, rest):
    """The basis rest opens with, as the record writes it or as a page says it in either language, and what follows; else None and rest."""
    said = {bare(b): b for b in BASES}
    said.update({bare(re.sub(r"\{[^}]*\}", " ", c.w.tab[("basis." + b, "")][col])): b for b in BASES for col in ("en", "ar")})
    word = next((x for x in sorted(said, key=len, reverse=True) if x and (rest == x or rest.startswith(x + " "))), None)
    return (said[word], rest[len(word):].strip()) if word else (None, rest)


def newest(c, lines, most=20):
    """Lines read, not searched, as hits, newest first, each naming its thing as the store's find does; past most, the rest counted."""
    lines = sorted(lines, key=lambda l: (l["t"], l["id"]), reverse=True)
    things = {i: c.s.thing(i) for i in {l["about"] for l in lines[:most] if l.get("about")}}
    hits = [{"id": l["id"], "about": (t := things.get(l.get("about"))) and {"id": t["object"]["id"], "name": t["name"], "type": t["type"]}}
            for l in lines[:most]]
    return [c.w.t("find.more", lines=c.w.count("line", len(lines) - most))] if len(lines) > most else [], hits


def taught_or(s, words, got):
    """The one of several things his answer taught these words mean (read.chosen, Astra's finding 6), alone, before several; else all."""
    pick = chosen(s, words, got) if len(got) > 1 else None
    return [pick] if pick else got


def question(c, sid, rest):
    """One of the three questions answered through the store: what I say about it, and the hits."""
    w, s = c.w, c.s
    unknown = ([w.t("find.question.unknown", words=rest)], [])
    if sid == "find.about":  # the longest run of first words that names a thing; the words after it searched among its lines
        words = rest.split()
        k = next((k for k in range(len(words), 0, -1) if s.resolve(" ".join(words[:k]))), 0)
        got, tail = s.resolve(" ".join(words[:k])) if k else [], " ".join(words[k:])
        got = taught_or(s, " ".join(words[:k]), got)
        if len(got) > 1:
            return [w.t("find.about.several", name=" ".join(words[:k]), things=w.count("thing", len(got)),
                        names=joined(c, [named_thing(c, x, "find.thing.name") for x in got]))], []
        return unknown if not got else ([], s.find(tail, about=got[0]["id"])["hits"]) if tail else newest(c, s.lines(about=got[0]["id"]))
    if sid == "find.basis":
        b, tail = basis_asked(c, rest)
        return unknown if b is None else ([], s.find(tail, basis=b)["hits"]) if tail else newest(c, s.lines(kinds=["fact"], basis=b))
    return newest(c, s.rests_on(rest.upper())) if ID_RE.match(rest.upper()) and c.r.get(rest.upper()) else unknown


def opening_words(line, most=8):
    """A line's first words as a sentence names it: a fact as its facet and value, else its own words, cut after most words; None for none."""
    b = line.get("body") or {}
    text = f"{b['facet']}: {b.get('value')}" if line["kind"] == "fact" and isinstance(b.get("facet"), str) else words_of(line)
    words = (text or "").split()
    return " ".join(words[:most]) + ("…" if len(words) > most else "") if words else None


def query_words(c, q):
    """The question as a sentence says it, and the line a real rests-on question names: that struck line by its kind and its first words,
    never its id, which stays in the form's value and behind what I saw (Astra's finding 16 of batch D); any other question as he asked it."""
    sid, rest = asked(c, q)
    line = c.r.get(rest.upper()) if sid == "find.restson" and ID_RE.match(rest.upper()) else None
    if not line:
        return q, None
    words = opening_words(line)
    kind = named(c.w, "kind.", line["kind"])
    said_ = (c.w.t("find.restson.line", rests=c.w.t("find.restson"), kind=kind, words=words) if words
             else c.w.t("find.restson.line.bare", rests=c.w.t("find.restson"), kind=kind))
    return said_, line


def find(c, q=None):
    r, w = c.r, c.w
    once = lambda hs: [h for h in hs if h["kind"] != "moment" or (r.get(h["id"])["body"] or {}).get("run") not in [x["id"] for x in hs]]  # noqa: E731
    shown, struck = query_words(c, q) if q else (q, None)
    dis = " disabled" if c.as_file else ""
    box = (f'<form class="box" method="get" action="/find" role="search"><input name="q" type="search" value="{esc(q or "")}" '
           f'aria-label="{esc(w.plain("find.label"))}" placeholder="{esc(w.plain("find.label"))}"{dis}>'
           f'<button class="quiet-btn" type="submit"{dis}>{w.t("find.go")}</button></form>')
    rows = [c.row("", H(box))]
    if q:
        sid, rest = asked(c, q)
        if sid:
            said, got = question(c, sid, rest)
            hits = [hit_item(c, h) for h in got]
            said += [] if got or said else [w.t("find.none", query=shown)]
        else:
            res, mine = c.s.find(q, limit=20), c.s.resolve(q)  # a thing's name leads to its page
            mine = taught_or(c.s, q, mine)
            hits = [hit_item(c, h) for h in once(res["hits"])]  # each hit once: a lookup at a set moment can repeat its run's words
            said = ([w.t("find.pages", len(mine), things=joined(c, [named_thing(c, x, "find.thing.name") for x in mine]))] if mine else []) + (
                [] if res["hits"] else [w.t("find.none", query=q)])
            if res.get("some"):
                said.append(w.t("find.some"))
                hits = [hit_item(c, h) for h in once(res["some"])]
            if res.get("present"):
                said.append(H(f'<a href="{c.href("present", unit=res["present"]["unit"])}">{w.t("find.present", project=c.project(res["present"]["unit"]))}</a>'))
        asked_ = shown if isinstance(shown, H) else H(f'<bdi data-f="slot">{esc(q)}</bdi>')
        seen = saw(c, [w.t("find.saw.restson", id=w.ident(struck["id"]))]) if struck else H("")  # its id behind what I saw
        rows.append(c.row("", H(f'<span class="q">{w.t("find.asked", cls="k")}{asked_}</span>' + "".join(said) + ul(hits) + seen)))
    applied, may = (w.count("ruling", sum(listed((m["body"] or {}).get(k)) for m in r.kind("moment"))) for k in ("applied", "may_apply"))
    good = [c.row("", w.t("find.moments", applied=applied, may=may))] * any(r.kind("moment")) + [c.row("", w.t("find.reads"))]
    q or c.term("basis")
    tries = [w.t(k) if c.as_file else H(f'<a href="{c.href("find", q=w.plain(k))}">{w.t(k)}</a>') for k in map("find.try.{}".format, "123")]  # to click (C11)
    good += [] if q else [c.row("", H(w.t("find.try") + ul(tries)))]
    c.term("ruling")
    body = (c.part("part.find", len(rows) - 1, "item",
            w.t("sum.find") if q else w.t("sum.find.empty"), rows) + c.part("part.good", len(good), "item", w.t("sum.good"), good))
    return c.page(w.t("title.find"), w.t("why.find", query=shown) if q else w.t("why.find.empty"), H(""), body, view="find")


def named_thing(c, x, sid="find.thing"):
    """The thing a hit is about: about her name, a link to her page, and her type; in a list of things (find.thing.name), without about."""
    tw = type_words(c, x.get("type"))
    name = H(f'<a href="{c.href("thing", id=x["id"])}">{c.words(c.r.get(x["id"]), "name") or c.w.ident(x.get("name") or "")}</a>')
    c.term("thing")
    return c.w.t(sid, name=name, type=c.w.t("world.an" if plain(tw)[:1].lower() in "aeiou" else "world.a", type=tw))


def hit_item(c, h):
    w, r = c.w, c.r
    line = r.get(h["id"])
    rep = h.get("replaced")
    replaced = H(w.t("find.replaced", date=w.date(rep["t"])) + c.words(r.get(rep["id"]))) if rep else ""  # nothing replaced: nothing said
    by = h.get("replaced_by")
    thing = H(named_thing(c, h["about"]) + " ") if h.get("about") else ""
    return H(f'{w.t("row.meta.project", cls="meta", who=c.who(line), when=w.date(line["t"]), project=c.project(line["unit"]))}'
             f'{said(c, line)} {c.mark(line.get("mark"))}'
             f'<span class="meta">{thing}{replaced}{w.t("find.replacedby", date=w.date(by["t"])) if by else ""}</span>')


# what was learned
def learned(c):
    r, w = c.r, c.w
    rows, own = {"learned": [], "changed": []}, lambda l, f: words_of(l, f) and not ID_RE.match(words_of(l, f))  # an id names its own row
    for l in reversed([l for l in r.all() if standing(l) and (l["kind"] in rows or own(l, "learned") or own(l, "changed"))]):
        for f in rows:  # what was taught and what changed, each in its own group (C10)
            if l["kind"] == f or l["kind"] not in rows and own(l, f):
                rows[f].append(c.line_row(l, project=True, field=None if l["kind"] == f else f))
    said = {}
    for l in r.all():
        if l["by"]["kind"] == "maker" and standing(l) and words_of(l):
            said.setdefault((l["unit"], " ".join(words_of(l).lower().split())), []).append(l)
    again = [c.row("", w.t("learned.repeat", times=w.count("time", len(ls)), project=c.project(ls[0]["unit"]))
                   + ul([H(c.words(x) + c.meta(x)) for x in ls])) for ls in said.values() if len(ls) > 1]
    moments = r.kind("moment", "recall")
    struck = [s for s in r.kind("strike") if (r.get((s["body"] or {}).get("target")) or {}).get("kind") in ("moment", "recall")]
    counts = w.t("learned.counts", applied=w.count("ruling", sum(listed((m["body"] or {}).get("applied")) for m in moments if m["kind"] == "moment")),
                 back=w.count("ruling", len(r.kind("recall"))), struck=w.count("ruling", len(struck)))
    c.term("run", "ruling")
    body = (c.part("part.repeat", len(again), "item", w.t("sum.learned.repeat"), again or [c.row("", w.t("learned.repeat.none"))])
            + "".join(c.part("part." + f, len(ls), "line", w.t("sum.learned." + f), ls) for f, ls in rows.items()) + c.part("part.good", 1, "item", w.t("sum.good"), [c.row("", counts)]))
    return c.page(w.t("title.learned"), w.t("why.learned", projects=w.count("project", len(r.units()))), H(""), body, view="learned")


# the manual: the charter, the book, the tool's page
LABEL = re.compile(r"^(\[[^\]]{1,30}\]|[A-Za-z][\w ,]{0,29}):\s*(.*)$", re.S)


def inline(text, src):
    t = esc(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return H(f'<span data-m="{src}" dir="auto">{t}</span>')


def parse_md(text):
    """Headings, paragraphs and list items with their following indented paragraphs, each with its line number."""
    doc, sec, item, para = {"title": None, "lead": [], "sections": []}, None, None, None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if line.startswith("<!--") or not line.strip():
            para = None
            continue
        m = re.match(r"^(#{1,2}) (.*)", line)
        if m:
            if m.group(1) == "#":
                doc["title"] = (n, m.group(2))
            else:
                sec, item = {"h": (n, m.group(2)), "paras": [], "items": [], "after": []}, None
                doc["sections"].append(sec)
            para = None
            continue
        m = re.match(r"^(\d+)\. (.*)|^- (.*)", line)
        if m and sec is not None:
            item = {"n": m.group(1), "paras": [[n, m.group(2) or m.group(3)]]}
            sec["items"].append(item)
            para = item["paras"][-1]
            continue
        indented = raw.startswith("  ")
        if para is not None:
            para[1] += ("\n" if raw.endswith("  ") or para[1].endswith("  ") else " ") + line.strip()
            continue
        target = item["paras"] if (item and indented) else (sec["after"] if sec and sec["items"] else sec["paras"]) if sec else doc["lead"]
        target.append([n, line.strip()])
        para = target[-1]
    return doc


def promise_mark(c, n):
    lines = [l for l in c.r.kind("check", "receipt") if standing(l) and (l["body"] or {}).get("promise") == f"P{n}"]
    if not lines:
        return "not yet"
    b = lines[-1]["body"]
    out = (b.get("output") or {}).get("payload")
    kept = c.s.payload_path(out) if out else (lines[-1]["kind"] == "receipt")
    ok = (b.get("exit") == 0 and out) if lines[-1]["kind"] == "check" else b.get("opened") is True
    return "proved" if ok and kept else "not yet"


def manual(c, name, view):
    r, w = c.r, c.w
    path, demo = os.path.join(c.root, name), [w.t("manual.first")]
    if not os.path.exists(path):
        path = os.path.join(TREE, "sandbox_os", "partner", name)
        demo.append(w.t("manual.missing", file=w.ident(name)))
    doc = parse_md(open(path, encoding="utf-8").read())
    src = lambda n: f"{name}:{n}"
    c.term("manual")
    parts, story, marks, kept, new = [], None, [], 0, 0
    for k, sec in enumerate(doc["sections"]):
        paras = [inline(t, src(n)) for n, t in sec["paras"]]
        if k == 0 and not sec["items"]:
            story = H(f'<div class="story"><div class="lbl">{inline(sec["h"][1], src(sec["h"][0]))}</div>' + "".join(f"<p>{p}</p>" for p in paras) + "</div>")
            continue
        rows, promises = [], any(LABEL.match(t) and LABEL.match(t).group(1) == "Catch" for i in sec["items"] for _, t in i["paras"])
        for i in sec["items"]:
            (n0, first), rest = i["paras"][0], i["paras"][1:]
            subs = []
            for n, t in rest:
                m = LABEL.match(t)
                lab = m.group(1) if m else None
                if promises and lab in ("not yet", "proved"):
                    mk = promise_mark(c, i["n"])
                    marks.append(mk)
                    subs.append(H(f'<span class="sub">{c.mark(mk)}{inline(m.group(2), src(n))}</span>'))
                elif m:
                    kept, new = kept + lab.startswith("kept"), new + (lab == "new")
                    subs.append(H(f'<span class="sub"><span class="k" data-m="{src(n)}">{esc(lab)}</span>{inline(m.group(2), src(n))}</span>'))
                else:
                    subs.append(H(f'<span class="sub">{inline(t, src(n))}</span>'))
            m = LABEL.match(first)
            head = (H(f'<span class="k" data-m="{src(n0)}">{esc(m.group(1).strip("[]"))}</span>{inline(m.group(2), src(n0))}')
                    if m and not i["n"] else inline(first, src(n0)))
            rows.append(H(f'<div class="row" tabindex="-1"><span class="mark">{w.ident(i["n"]) if i["n"] else ""}</span>'
                          f'<span class="text">{head}</span>{"".join(subs)}</div>'))
        rows += [c.row("", inline(t, src(n))) for n, t in sec["after"]]
        noun = "promise" if promises else "item"
        parts.append(H(f'<section class="part"><div class="label"><h2>{inline(sec["h"][1], src(sec["h"][0]))}</h2> '
                       f'<span class="n" aria-label="{esc(plain(w.count(noun, len(sec["items"]))))}">{w.num(len(sec["items"]))}</span>'
                       f'<span class="sum">{paras[0] if paras else ""}</span></div><div class="rows">{"".join(rows)}</div></section>'))
    changes = [l for l in r.kind("changed") if (l["body"] or {}).get("file") == name]
    if changes:
        parts.append(c.part("manual.changes", len(changes), "line", w.t("sum.good"), [c.line_row(l, why=ul([
            H(w.t("manual.old") + " " + (c.words(l, "old") or "")), H(w.t("manual.new") + " " + (c.words(l, "new") or ""))])) for l in changes]))
    if marks:
        demo.append(w.t("manual.promises", promises=w.count("promise", len(marks)), proved=w.num(marks.count("proved")), notyet=w.num(marks.count("not yet"))))
    if kept or new:
        demo.append(w.t("manual.counts", lines=w.count("line", kept + new), kept=w.num(kept), new=w.num(new)))
    t, lead = doc["title"] or (0, name), doc["lead"]
    why = inline(lead[0][1], src(lead[0][0])) if lead else H("")
    return c.page(inline(t[1], src(t[0])), why, story or H(""), H("".join(parts)), demo=demo, title_text=t[1], view=view)


def charter(c):
    return manual(c, "charter.md", "charter")


def book(c):
    return manual(c, "book.md", "book")


def budgets():
    """BUDGETS.md's table: part, job, paths, limit, unit, with each row's line number; and the paths measured apart."""
    path = os.path.join(TREE, "BUDGETS.md")
    if not os.path.exists(path):
        return None, []
    text = open(path, encoding="utf-8").read()
    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        cells = [x.strip() for x in line.strip().strip("|").split("|")] if line.startswith("| ") else []
        if len(cells) >= 7 and cells[0] not in ("part",) and not cells[0].startswith("---"):
            rows.append({"n": n, "part": cells[0], "job": cells[1], "paths": [p.strip("` ") for p in cells[2].split(",")],
                         "limit": int(cells[3].replace(",", "")) if cells[3].replace(",", "").isdigit() else None, "unit": cells[4]})
    m = re.search(r"by name: (.*?)\.\s", text, re.S)
    return rows, [p.strip("` ") for p in m.group(1).split(",")] if m else []


def glob_match(path, pattern):
    rx = re.escape(pattern).replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
    return re.fullmatch(rx, path) is not None


def tool(c):
    w = c.w
    rows, apart = budgets()
    files = sorted(os.path.relpath(os.path.join(d, f), TREE) for base in ("sandbox_os", "tests")
                   for d, ds, fs in os.walk(os.path.join(TREE, base)) if "__pycache__" not in d for f in fs if not f.endswith(".pyc"))
    measure = lambda fs, unit: sum(len(t.split()) if unit.startswith("word") else t.count("\n")
                                   for t in (open(os.path.join(TREE, f), encoding="utf-8", errors="replace").read() for f in fs))
    out, gone = [], []
    c.term("part")
    for i, p in enumerate(rows or [], 1):
        mine = [f for f in files if any(glob_match(f, x) for x in p["paths"]) and not any(glob_match(f, e) for e in apart)]
        noun = "word" if p["unit"].startswith("word") else "line"
        each = p["unit"].endswith("each") and mine  # a limit for each file: its largest file against it (R-READ-23)
        size, code = max(measure([f], p["unit"]) for f in mine) if each else measure(mine, p["unit"]), measure([f for f in mine if f.endswith(".py")], p["unit"])
        sub = (w.t("tool.size.each" if each else "tool.size", size=w.count(noun, size), limit=w.count(noun, p["limit"])) if p["limit"]
               else w.t("tool.size.all", size=w.count(noun, size), code=w.count(noun, code)) if code != size else w.count(noun, size))
        verdict = (w.t("tool.over", over=w.count(noun, size - p["limit"])) if p["limit"] and size > p["limit"] else w.t("tool.within") if p["limit"] else H(""))
        out.append(H(f'<div class="row" tabindex="-1"><span class="mark">{w.ident(i)}</span><span class="text"><b data-m="BUDGETS.md:{p["n"]}">'
                     f'{esc(p["part"])}</b> <span data-m="BUDGETS.md:{p["n"]}" dir="auto">{esc(p["job"])}</span></span>'
                     f'<span class="sub">{sub} {verdict}</span></div>'))
    for e in apart:
        mine = [f for f in files if glob_match(f, e)]
        gone.append(c.row("", w.ident(e), w.t("tool.apart", size=w.count("file", len(mine)) if "*" in e else w.count("line", measure(mine, "lines")))))
    for f in ("BUDGETS.md", "LICENSE", "README.md", "CLAUDE.md", "AGENTS.md", ".gitignore", ".gitattributes"):
        if os.path.exists(os.path.join(TREE, f)):
            gone.append(c.row("", w.ident(f), w.t("tool.tree")))
    good = [c.row("", c.link("week", "link.week"))]
    good += [] if rows else [c.row("", w.t("tool.nobudgets"))]
    body = (c.part("part.parts", len(out), "part", w.t("sum.tool.parts"), out) + c.part("part.notpart", len(gone), "item", w.t("sum.tool.notpart"), gone)
            + c.part("part.good", len(good), "item", w.t("sum.good"), good))
    return c.page(w.t("title.tool"), w.t("why.tool", parts=w.count("part", len(rows or []))), H(""), body, demo=[w.t("manual.first")], view="tool")


# the graph and the morning after a move
def graph(c, unit):
    r, w = c.r, c.w
    rows, bare = [], 0
    cards = {}
    for x in r.cards([unit]):
        cards.setdefault((x["body"] or {}).get("about"), []).append(x)
    for cl in reversed([l for l in r.unit(unit) if l["kind"] in CLAIM_KINDS]):
        proofs = [p for p in r.into(cl["id"], "proves") if p["kind"] in ("receipt", "check")]
        decided = [a for x in cards.get(cl["id"], []) for a in [x] + r.answers(x["id"])]
        runs = [x for x in r.into(cl["id"], "follows") if x["kind"] == "run"]
        lessons = [x for x in r.into(cl["id"], "came_from") if x["kind"] == "learned"]
        if not (proofs or decided or runs or lessons):
            bare += 1
            continue
        item = lambda x: H(c.mark(x.get("mark")) + (c.words(x) or (w.ident(p) if (p := (x["body"] or {}).get("pointer")) else w.t("kind." + x["kind"] + ".row"))) + c.meta(x))
        groups = [H(w.t(sid) + ul([item(x) for x in xs])) for sid, xs in (("graph.proofs", proofs), ("graph.cards", decided),
                                                                         ("graph.runs", runs), ("graph.lessons", lessons)) if xs]
        rows.append(c.line_row(cl, why=ul(groups)))
    c.term("claim", "receipt")
    good = [c.row("", w.t("graph.unlinked", claims=w.count("claim", bare))),
            c.row("", w.t("graph.world", world=H(f'<a href="{c.href("world", unit=unit)}">{w.t("graph.world.link")}</a>')))]
    body = c.part("part.claims", len(rows), "claim", w.t("sum.graph"), rows) + c.part("part.good", len(good), "item", w.t("sum.good"), good)
    return c.page(w.t("title.graph"), w.t("why.graph", project=c.project(unit)), c.story(r.story([unit])), body,
                  where=w.t("top.project", project=c.project(unit)), view="graph")


def moved(c, unit):
    r, w = c.r, c.w
    moves = [l for l in r.unit(unit) if l["kind"] == "move" and standing(l) and isinstance((l["body"] or {}).get("counts"), dict)]
    c.term("move")
    came, lost, cards = [], [], []
    if moves:
        m = moves[-1]
        counts = m["body"]["counts"]
        came.append(c.row(w.date(m["t"]), w.t("moved.came", lines=w.count("line", counts.get("lines") or 0)), c.meta(m)))
        for k, n in sorted((counts.get("kinds") or {}).items(), key=lambda kv: -kv[1]):
            came.append(c.row("", w.t("moved.kind", lines=w.count("line", n), kind=w.t("kind." + k) if ("kind." + k, "") in w.tab else w.ident(k))))
        ls = r.unit(unit)
        checks = [l for l in ls if l["kind"] == "check" and l["by"]["kind"] == "tool" and l["t"] > m["t"]]
        came.append(c.row("", w.t("moved.checked", checks=w.count("check", len(checks)))))
        came.append(c.row("", w.t("moved.notyet", claims=w.count("claim", len([l for l in ls if l.get("mark") == "not yet"])))))
        came.append(c.row("", w.t("moved.gone", receipts=w.count("receipt", len([l for l in ls if l["kind"] == "receipt" and (l["body"] or {}).get("opened") is False])))))
        for x in r.payload_json(((m["body"].get("losses") or {}).get("payload")) or "") or []:
            if isinstance(x, dict) and x.get("count"):
                lost.append(c.row("", H(w.ident(x.get("change", "")) + f' <span data-l="{m["id"]}" dir="auto">{esc(x.get("says", ""))}</span>'),
                                  w.t("moved.loss", lines=w.count("line", x["count"]))))
        cards = [x for x in r.open_cards([unit]) if (x["body"] or {}).get("about") in [mm["id"] for mm in moves]]
        c.term("not yet", "receipt")
    else:
        came.append(c.row("", w.t("moved.none", project=project_link(c, unit))))
    body = (needs(c, cards, card_rows(c, cards))
            + c.part("part.came", len(came), "item", w.t("sum.came"), came) + c.part("part.lost", len(lost), "item", w.t("sum.lost"), lost))
    return c.page(w.t("title.moved"), w.t("why.moved", project=c.project(unit)), H(""), body,
                  where=w.t("top.project", project=c.project(unit)), view="moved")


# the week: the eight measures against the week before, what the week taught, its cost, and the baseline before the move
WEEK_PURPOSES = ("kill-rule", "behaviour-check")
shows = lambda name, m: m["value"] != measures.NONE and (m["value"] != measures.NOT_SEEN or name in ("m1", "m2", "m3", "m4", "m6", "m7"))  # noqa: E731


def measure_value(c, name, m):
    """A measure's value for one week in the table's words, every number counted with its noun: nothing to count, or its template."""
    w, v, k = c.w, m["value"], m["counts"]
    n = lambda noun, x: w.count(noun, x if isinstance(x, (int, float)) else 0)
    proxy = m["how"].startswith("proxy: ")
    if not shows(name, m):  # nothing to show, said once: how it was got says why (R-DESIGN-17)
        return w.t("week.value.nothing")
    if name in ("m1", "m7") and proxy:
        return w.t("measure.m1.proxyvalue", ships=n("ship", k["ships"]), places=n("place", k["places"]), naming=n("line", k["naming_an_address"]))
    if name == "m1":
        return w.t("measure.m1.value", hours=w.duration(v), ideas=n("idea", k["opened"]), unopened=n("idea", k["unopened"]))
    if name == "m2":
        return (w.t("measure.m2.proxyvalue", candidates=n("line", k["candidates"]), closes=n("run", k["closes"])) if proxy else
                w.t("measure.m2.value", runs=n("run", k["accepted"]), worded=n("run", k["with_words"]), closed=n("run", k["closes"])))
    if name == "m3":
        return (w.t("measure.m3.proxyvalue", rulings=n("ruling", k["rulings"]), keys=n("line", k["keys"])) if proxy else
                w.t("measure.m3.value" if k["asks"] else "measure.m3.value.unasked", cards=n("card", k["cards"]), answered=n("card", k["answered"]),
                    needless=n("card", k["needless"]), over=n("card", k["over_by"]), asks=n("ask", k["asks"])))  # no asks clause at zero
    if name == "m4":
        if v == measures.UNPLACED:
            return w.t("measure.m4.unplaced", sessions=n("session", k["sessions"]), unplaced=n("session", k["unplaced"]))
        return w.t("measure.m4.value", tool=n("session", k["tool"]), rest=n("session", k["rest"]), toolhours=w.duration(k["hours_tool"]),
                   resthours=w.duration(k["hours_rest"]), unplaced=n("session", k["unplaced"]))
    if name == "m5":
        return w.t("measure.m5.value", minutes=w.duration(v / 60), stalls=n("stall", k["stalls"]),
                   finished=w.t("measure.m5.done" if k["completed"] else "measure.m5.notdone"))
    if name == "m6":
        return (w.t("measure.m6.proxyvalue", back=n("line", k["brought_back"]), struck=n("line", k["struck"])) if proxy else
                w.t("measure.m6.value", applied=n("ruling", k["applied"]), back=n("card", k["brought_back"]), same=n("card", k["unchanged"]),
                    struck=n("line", k["struck"])))
    if name == "m7":
        opens = w.t("measure.m7.opens.notseen") if k["opens"] == measures.NOT_SEEN else w.t("measure.m7.opens", opens=n("open", k["opens"]))
        return w.t("measure.m7.unplaced" if k["tool"] == measures.UNPLACED else "measure.m7.value", things=n("thing", k["live"]), opens=opens,
                   kill=n("thing", k["kill_rule"]))
    if name == "m9":
        return w.t("measure.m9.value", likely=n("belief", k["likely"]), held=n("belief", k["held"]), fell=n("belief", k["fell"]), open=n("belief", k["open"]))
    if name == "m10":
        return w.t("measure.m10.value", expired=n("question", k["expired"]), unread=n("question", k["unread"]))
    if name == "m11":
        return w.t("measure.m11.value", types=n("type", k["types"]), relations=n("relation", k["relations"]))
    if name == "m12":
        verbs = [w.t("measure.m12.verb", verb=w.ident(x), acts=n("act", y)) if x != "no verb" else w.t("measure.m12.noverb", acts=n("act", y))
                 for x, y in k["by_verb"].items()]
        return w.t("measure.m12.value", acts=n("act", k["acts"]), verbs=joined(c, verbs))
    if name == "m13":
        return w.t("measure.m13.value", late=n("check", k["named_late"]), checks=n("check", k["checks"]))
    if name == "m14":
        views = [w.t("measure.m14.view", view=w.ident(x), pages=n("page", y)) for x, y in k["by_view"].items()]
        return w.t("measure.m14.value", pages=n("page", k["opens"]), days=n("day", len(k["days"])), views=joined(c, views))
    if name == "m15":
        return w.t("measure.m15.value", needless=n("card", k["needless"]), cards=n("card", k["cards"]))
    if name == "m16":
        return w.t("measure.m16.value", days=n("day", k["days_over"]), over=n("card", k["over_by"]), cap=n("card", k["cap"]))  # no cap: none over
    return w.t("measure.m8.value", tokens=n("token", v), money=money(c, k))


def money(c, k):
    w = c.w
    if k.get("money") is None:
        return w.t("measure.m8.nomoney")
    if k.get("money_priced"):
        return w.t("measure.m8.priced", money=w.count("usd", k["money"]), priced=w.count("usd", k["money_priced"]),
                   date=w.date(k["price_table_date"] + "T12:00:00+00:00"))
    return w.t("measure.m8.reported", money=w.count("usd", k["money"]))


def how_got(c, name, m):
    w = c.w
    if m["how"].startswith("proxy: "):
        c.term("proxy")
        said = w.t("week.how.proxy", proxy=w.t(f"measure.{name}.proxy"))
    elif m["how"].startswith(measures.NOT_SEEN):
        c.term("notseen")
        said = w.t("week.how.notseen")
    else:
        said = w.t("week.how.computed")
    gone, untold = m["counts"].get("erased"), name == "m7" and m["counts"].get("tool") == measures.UNPLACED  # every unit counted, said so
    said += (" " + w.t("measure.erased", lines=w.count("line", gone))) if gone else ""
    return H(said + (" " + w.t("measure.m7.untold") if untold else ""))


def measure_items(c, name, m):
    """What a measure lists beside its number: the ideas not opened yet, your accept words verbatim, the welcome's stalls with their words."""
    w, r = c.w, c.r
    if name == "m1" and not m["how"].startswith("proxy: "):
        return [w.t("week.unopened", project=c.project(i["unit"]), date=w.date(i["since"]), hours=w.duration(i["hours"])) for i in m.get("items", [])]
    if name == "m2":
        return [c.words(r.get(i["id"]), "words" if "run" in i else None) for i in m.get("items", [])]
    if name == "m5":
        return [H(w.t("week.stall", step=named(w, "cli.step.", i["step"]), cause=named(w, "stall.", i["cause"])) + " "
                  + (c.words(r.get(i["id"]), "words") or "")) for i in m.get("items", [])]
    return []


def week(c, week=None):
    r, w = c.r, c.w
    lines = r.all()
    week = week or measures.last_week(c.now)
    mon, sun = measures.bounds(week)
    this = measures.week_table(c.s, week, lines=lines)
    before = measures.week_table(c.s, measures.iso_week(mon - _dt.timedelta(days=7)), lines=lines) if any(r.day(l["t"]) < str(mon) for l in lines) else None
    inside = lambda l: mon <= measures.day_of(l["t"]) <= sun
    c.term("measure")
    since = []
    for name in measures.NAMES:
        shown = [shows(name, this[name]), bool(before) and shows(name, before[name])]  # no week before the first week counted (R-DESIGN-17)
        items = [w.t("week.this", value=measure_value(c, name, this[name])) if shown[0] else w.t("week.nothing")]
        items += [w.t("week.before", value=measure_value(c, name, before[name])) if before else w.t("week.before.none")] * any(shown)
        why = H(how_got(c, name, this[name]) + " " + w.t(f"measure.{name}.formula") + " " + w.t("week.unit", unit=w.t(f"measure.{name}.unit")))
        since.append(c.row("", H(w.t("measure." + name) + ul(items + measure_items(c, name, this[name]))), H(why + saw(c, [w.ident(name.upper())])),
                           attrs=f' data-measure="{name}"'))  # its code behind what I saw, not in the mark column (R-DESIGN-17)
    since += [c.line_row(l, project=True) for l in lines if l["kind"] in ("learned", "changed") and standing(l) and inside(l)]
    k3 = this["m3"]["counts"]
    c.term("needless")
    since.append(c.row("", w.t("week.needless", needless=w.count("card", k3.get("needless", 0)),
                               cards=w.count("card", k3.get("cards", 0) + k3.get("before_act", 0)))))
    for bet in [x for x in r.kind("bet") if standing(x)]:
        c.term("bet")
        fields = [H(w.t(sid) + " " + (c.words(bet, f) or w.t("card.missing"))) for f, sid in
                  (("direction", "bet.direction"), ("would_show", "bet.show"), ("by", "bet.by"))]
        since.append(c.row("", w.t("good.bet") + ul(fields), c.meta(bet, project=True)))
    good, k8 = [], this["m8"]["counts"]
    if isinstance(this["m8"]["value"], int):
        good.append(c.row("", w.t("week.cost.week", tokens=w.count("token", this["m8"]["value"]), money=money(c, k8))))
        good += [c.row("", w.t("week.cost.run", tokens=w.count("token", n)) + ul([c.words(r.get(i)) or w.t("kind.run.row")])) for i, n in k8["runs"].items()]
        good += [c.row("", w.t("week.cost.night", tokens=w.count("token", n), session=w.ident(s))) for s, n in k8["nights"].items()]
    else:
        good.append(c.row("", measure_value(c, "m8", this["m8"])))
    for host, n in sorted((this["m3"]["counts"].get("not_seen") or {}).items()):  # M3's own figure, so the week and the brief count alike
        c.term("notseen")
        good.append(c.row("", w.t("week.notseen", host=w.ident(host), lines=w.count("line", n))))
    found = [l for l in lines if l["kind"] == "finding" and (l["body"] or {}).get("event") == "behaviour-check" and l["body"].get("week") == week]
    if found:
        good += [c.line_row(f, project=True) for f in found]
    else:
        sample = [r.get(i) for i in measures.behaviour_sample(lines, week)]
        listed = "".join(f'<li data-sample="{x["id"]}">{c.words(x, "decides") or c.words(x) or w.t("kind." + x["kind"] + ".row")}</li>' for x in sample)
        good.append(c.row("", H(w.t("week.behaviour.notrun", items=w.count("item", len(sample))) + (f'<ul class="list">{listed}</ul>' if listed else ""))))
    base = measures.baseline(c.s, lines=lines)
    if base:
        good.append(c.row("", w.t("week.baseline.head", sha=w.ident(base["export_sha256"]), date=w.date(base["imported_at"]))))
        for name in measures.NAMES:
            items = [w.t("week.baseline.item", week=w.ident(wk), value=measure_value(c, name, base["table"][wk][name])) for wk in base["weeks"]]
            good.append(c.row("", H(w.t("measure." + name) + ul(items)), H(how_got(c, name, base["table"][base["weeks"][0]][name])
                                                                           + saw(c, [w.ident(name.upper())])), attrs=f' data-baseline="{name}"'))
    cards = [x for x in r.open_cards() if (x["body"] or {}).get("purpose") in WEEK_PURPOSES and (x["body"] or {}).get("week") in (None, week)]
    done = sun < measures.day_of(c.now)
    why = w.t("why.week" if done else "why.week.open", week=w.ident(week), start=w.date(f"{mon}T12:00:00+00:00"), end=w.date(f"{sun}T12:00:00+00:00"))
    body = (needs(c, cards, card_rows(c, cards), "sum.week.needs")
            + c.part("part.week", len(since), "item", w.t("sum.week.since", measures=w.count("measure", len(measures.NAMES))), since)
            + c.part("part.good", len(good), "item", w.t("sum.week.good"), good))
    return c.page(w.t("title.week"), why, H(""), body, where=w.t("top.week", week=w.ident(week)), view="week")


# the welcome
def welcome(c, gated=False):
    """gated: served before a first run, when every route serves this page again, so it offers no link (R-READ-26)."""
    w = c.w
    c.links = () if gated else c.links
    done = c.welcome_text is not None
    dis = " disabled" if c.as_file else ""
    fields = []
    for i, (k, kind) in enumerate((("name", "text"), ("making", "text"), ("ask", "select")), 1):
        val, tie = c.welcome.get(k, ""), f' aria-describedby="h-{k}"{dis}'  # a box names its hint (L5)
        if kind == "select":
            pick = val if val in LIMITS else "some"
            ctrl = (f'<select id="f-{k}" name="{k}"{tie}>' + "".join(f'<option value="{o}" data-s="ask.{o}"{" selected" if o == pick else ""}>{esc(w.plain("ask." + o))}</option>'
                                                                       for o in LIMITS) + "</select>")
        else:
            ctrl = f'<input id="f-{k}" name="{k}" type="text" value="{esc(val)}" placeholder="{esc(w.plain("welcome." + k + ".ph"))}"{tie}>'
        fields.append(c.row(w.ident(i), H(f'<span class="form"><span class="field"><label for="f-{k}">{w.t("welcome." + k)}</label>{ctrl}'
                                          f'<button class="skip" type="button" data-skip="f-{k}" aria-label="{esc(w.plain("welcome.skip." + k))}"{dis}>'
                                          f'{w.t("welcome.skip")}</button><span class="hint" id="h-{k}">{w.t("welcome." + k + ".hint")}</span></span></span>')))
    form = H(f'<form id="welcome" method="post" action="/welcome">{"".join(fields)}</form>')
    first = next((o for o in c.s.lines(kinds=["object"]) if (o["body"] or {}).get("first") and o["by"]["kind"] == "tool"
                  and o.get("mark") not in ("erased", "deleted", "struck", "superseded")), None) if done else None
    since = ([c.row("", w.t("welcome.first.later", name=c.words(first, "name")))] if first and gated else  # its page opens after a first run
             [c.row("", H(f'<a href="{c.href("thing", id=first["id"])}">{w.t("welcome.first", name=c.words(first, "name"))}</a>')),
              c.row("", H(f'<a href="{c.href("brief")}">{w.t("welcome.first.brief")}</a>'))]  # one thing, its page and the brief (section 9 point 10)
             if first else [c.row("", w.t("welcome.since"))])
    if done:  # answered: the three answers once, as sentences, and no form drawn again (R-READ-27)
        md = lambda k: H(f'<span data-m="welcome.md" dir="auto">{esc(c.welcome.get(k, ""))}</span>')
        since = [c.row("", w.t("welcome.said." + k, **{k: md(k)}) if (c.welcome.get(k) or "").strip() else w.t("welcome.said." + k + ".none"))
                 for k in ("name", "making")] + [c.row("", w.t("welcome.said.ask." + setting(c)))] + since
    good = [c.row("", w.t(k)) for k in ("welcome.start", "welcome.brief", "welcome.opens")]
    story = H(f'<div class="story"><div class="lbl">{w.t("welcome.what")}</div><p>{w.t("welcome.p1")}</p><p>{w.t("welcome.p2")}</p>'
              f'<p>{w.t("acts.list")}</p><p>{w.t("acts.leaves")} {w.t("acts.where-yes")}</p></div>')
    # the cards waiting, as the brief counts them: the terminal's figure (R-READ-28); gated, every card is shown whole and counted, the
    # week's too, since the gate serves this page for each card's own: the ones answered later after the rest (R-READ-26)
    cards = [x for x in c.r.open_cards() if gated or not outside_budget(x)]
    gated and cards.sort(key=lambda x: any(standing(a) and (a["body"] or {}).get("answer") == "later" for a in c.r.answers(x["id"])))
    after = [c.row("", w.t("welcome.cards.after", cards=w.count("card", len(cards))))] if cards else []  # counted after the questions
    asks = (needs(c, cards, one_card(c, cards, gated)) if done else c.part("part.needs", 3, "question", w.t("sum.welcome"), [form] + after, hot=True,
             aria=cards and w.t("welcome.needs.aria", questions=w.count("question", 3), cards=w.count("card", len(cards)))))
    body = (asks + c.part("part.welcome.since", len(since), "item", w.t("welcome.sum.answered" if done else "sum.welcome.first" if first else "sum.welcome.since"), since)
            + c.part("part.good", len(good), "item", w.t("sum.welcome.good"), good))
    c.term("partner", "run", "card")
    extra = H(f'<button class="primary-btn" form="welcome" name="go" value="save"{dis}>{w.t("welcome.save")}</button>'
              f'<button class="quiet-btn" form="welcome" name="go" value="skip"{dis}>{w.t("welcome.skipall")}</button>')
    return c.page(w.t("title.welcome"), w.t("welcome.why.done" if done else "why.welcome"), story, body, view="welcome",
                  bar=None if done else H(f'<span class="what">{w.t("actions.welcome")}</span>{extra}'))


# a thing's page: a short note across the desk, then what I believe about it and on what (03-design.md section 9 point 1; the pages sitting)
PICKED = "picked for now"  # the legend's key for a provisional pick, an id whose words are the table's; listed by name in LEGEND_KEYS of
# tests/pages/test_strings_table.py, the one place a renderer may hold such a key


def value_of(c, line):
    """A facet's value: its own words when it is a string, else the identifier's formatter over its canonical form."""
    v = (line["body"] or {}).get("value")
    return c.words(line, "value") if isinstance(v, str) and v.strip() else c.w.ident(canonical(v))


def age_of(c, t):
    w = c.w
    n = (w.local(w.now).date() - w.local(t).date()).days
    return w.t("age.today") if n <= 0 else w.t("age.days", days=w.count("day", n))


def basis_of(c, line):
    """What a belief rests on, as a word (read in names the file, its path left for what I saw), then how sure, then how old."""
    w, b = c.w, line["body"] or {}
    src = b.get("source") if isinstance(b.get("source"), str) else ""
    basis = ((b.get("basis") == BASES[2] and world.read_in(c, src)) or w.t("basis." + b["basis"], source=w.ident(re.split(r"[/\\]", src.rstrip("/"))[-1]))
             if b.get("basis") in BASES else w.ident(b.get("basis") or ""))
    ran = c.r.get(src) if b.get("basis") == BASES[1] and ID_RE.match(src) else None  # a check showed: its command beside it (R-READ-17)
    if ran and ran["kind"] == "check" and ran["by"]["kind"] == "tool" and (ran["body"] or {}).get("command"):
        basis = H(basis + " " + w.t("basis.command", command=H(f'<code>{w.ident(ran["body"]["command"])}</code>')))
    if b.get("confidence"):
        return w.t("thing.facet.why.confidence", basis=basis, confidence=named(w, "confidence.", b["confidence"]), age=age_of(c, line["t"]))
    return w.t("thing.facet.why", basis=basis, age=age_of(c, line["t"]))


def said(c, line):
    """A line about a thing in its own words; a fact as its facet and its value, a decision's provisional facet in the believe part's words."""
    b = line["body"] or {}
    if line["kind"] == "fact" and b.get("facet") == "provisional" and isinstance(b.get("value"), bool):
        b["value"] and c.term(PICKED)
        return c.w.t(f"thing.provisional.{str(b['value']).lower()}")
    if line["kind"] == "fact" and isinstance(b.get("facet"), str):
        return c.w.t("thing.facet.line", facet=c.words(line, "facet"), value=value_of(c, line))
    return c.words(line, "decides" if line["kind"] == "card" else None) or named(c.w, "kind.", line["kind"] + ".row")  # a card by its question


def note_mark(c, line):
    """A line's mark on a thing's page, which reads as a note: said only when it is not the ground state, recorded."""
    return H("") if line.get("mark") == "recorded" else c.mark(line.get("mark"))


def about_row(c, line):
    return c.row(c.stamp(line["t"]), said(c, line), H(note_mark(c, line) + c.meta(line, project=True)))


def saw(c, items):
    """The one fold where a code name, a path or a reference may stand on a page."""
    items = [i for i in items if i]
    return H(f'<details class="saw"><summary>{c.w.t("saw")}</summary>{ul(items)}</details>') if items else H("")


def fold(summary, rows):
    return H(f'<details><summary>{summary}</summary><div class="rows">{"".join(rows)}</div></details>')


def one_card(c, cards, every=False):
    """The first card whole with its answers, and one line counting the rest: a page asks for one thing at a time. every: each card
    whole, for the welcome behind the gate, which is served for each card's own page too (R-READ-26)."""
    if not cards:
        return []
    c.waiting = len(cards)  # the bar counts them all, not only the one shown whole
    rows = [card_row(c, x, i, len(cards), True) for i, x in enumerate(cards[:None if every else 1], 1)]
    return rows + ([c.row("", c.w.t("cards.after", cards=c.w.count("card", len(cards) - 1)))] if len(cards) > len(rows) else [])


def cards_about(c, id):
    return [x for x in c.r.open_cards() if (x["body"] or {}).get("about") == id or x.get("about") == id]


def type_words(c, name):
    if name in VOCAB:
        return c.w.ident(name)
    line = next((x for x in c.s.types() if (x["body"] or {}).get("name") == name), None)
    return H(f'<a href="{c.href("type", name=name)}">{c.words(line, "name")}</a>') if line else c.w.ident(name or "")


def picks(c, t):
    """Each decision made for this thing, with its present pick and the pick facts it has had, oldest first; read once per thing."""
    if "picks" in t:
        return t["picks"]
    out = t["picks"] = []
    for x in t["related"]:
        d = c.s.thing(x["id"]) if (x["rel"], x["direction"], x["type"]) == ("for", "in", "decision") else None
        now = d and d["facets"].get("pick")
        if now:
            had = [l for l in c.s.lines(about=x["id"], kinds=["fact"]) if (l["body"] or {}).get("facet") == "pick"]
            out.append((d, c.r.get(now["line"]), had))
    return out


def pick_rows(c, t):
    w, rows = c.w, []
    for d, line, had in picks(c, t):
        fornow = (d["facets"].get("provisional") or {}).get("value") is True
        fornow and c.term(PICKED)
        text = w.t("thing.pick.fornow" if fornow else "thing.pick", pick=value_of(c, line))
        before = [l for l in had if l.get("mark") not in DOWN and (l["t"], l["id"]) < (line["t"], line["id"])]
        if before:
            text = H(text + " " + w.t("thing.pick.replaced", pick=value_of(c, before[-1]), date=w.date(before[-1]["t"])))
        name = H(f'<a href="{c.href("thing", id=d["object"]["id"])}">{c.words(d["object"], "name")}</a>')
        rows.append(c.row(name, text, basis_of(c, line)))
    return rows


def receipt_words(c, got):
    """A verb's last receipt in a sentence: none yet, its output when the outside gave no value, else its kind in words (its value is a
    code name, inside "What I saw" only)."""
    if not got:
        return c.w.t("thing.verb.noreceipt")
    if got["value"] is None:
        return c.w.t("receipt.output")
    return named(c.w, "receipt.kind.", got["kind"] if ("receipt.kind." + str(got["kind"]), "") in c.w.tab else "other")


def receipt_saw(c, verb, got):
    """A receipt's value inside "What I saw", by its verb: its kind with the value; none when the outside gave no value."""
    got = got if isinstance(got, dict) else {}
    if got.get("value") is None:
        return None
    v = c.w.ident(got["value"])
    return c.w.t("receipt.saw", verb=verb, receipt=c.w.t("receipt." + got["kind"], value=v) if ("receipt." + str(got.get("kind")), "") in c.w.tab else v)


def thing_verbs(c, id, verbs=None):
    """What can be done to a thing (Store.thing(id)["verbs"]): one sentence glossing door and receipt, then each verb by its name, a link to
    its own page, with its door, its last receipt and the service it reaches; a failure newer than that receipt under it; the command shapes
    behind what I saw."""
    w, vs = c.w, c.s.thing(id)["verbs"] if verbs is None else verbs
    c.term("verb", "door", "verb receipt")
    rows, shapes = [c.row("", w.t("thing.verbs.lead", verbs=w.count("verb", len(vs))))], []
    for v in vs:
        line, full = c.r.get(v["verb"]), c.s.verb(v["verb"]) or {}
        name = c.words(line, "name") or w.ident("")
        svc = c.r.get(full.get("service")) if isinstance(full.get("service"), str) else None
        service = H(f'<a href="{c.href("thing", id=svc["id"])}">{c.words(svc, "name") or w.ident("")}</a>') if svc else w.ident("")
        got, failed = v["last_receipt"], v["last_failure"]
        rows.append(c.row("", w.t("thing.verb.row", verb=H(f'<a href="{c.href("thing", id=v["verb"])}">{name}</a>'),
                                  door=named(w, "door.", DOORS.get(v["door"], v["door"])), receipt=receipt_words(c, got), service=service)))
        if failed and (not got or (failed["t"], failed["id"]) > (got["t"], got["id"])):
            rows.append(c.row("", w.t("thing.verb.failed", date=w.date(failed["t"]), words=c.words(c.r.get(failed["id"]), "words") or w.ident(""))))
        if full.get("shapes"):
            shapes.append(w.t("thing.verb.saw", verb=name, shapes=joined(c, [w.ident(" ".join(s)) for s in full["shapes"]])))
        shapes.append(receipt_saw(c, name, got))
    return rows + ([c.row("", saw(c, shapes))] if any(shapes) else [])


def believed(c, t):
    return bool(t["facets"] or t["assumptions"] or picks(c, t))


def thing_note(c, t):
    """The head's note in the partner's voice: what it is and where it fits (world.ground_line), where, since when, how many lines, and whether a card about it waits."""
    w, o = c.w, t["object"]
    project = project_link(c, o["unit"])
    n = len(c.s.lines(about=o["id"]))
    note = w.t("thing.note" if believed(c, t) else "thing.note.none", n or None, line=world.ground_line(c, t), project=project, date=w.date(o["t"]),
               lines=w.count("line", n))
    cards = cards_about(c, o["id"])
    return H(note + " " + w.t("thing.note.needs", len(cards), cards=w.count("card", len(cards)))) if cards else note


def thing(c, id):
    r, w = c.r, c.w
    t = c.s.thing(id)
    o, lines = t["object"], c.s.lines(about=id)
    c.term("thing", "facet", "ground", "basis")  # the words its page shows, glossed at its foot; a check's reading is a shadow
    any(f["basis"] == BASES[1] for f in t["facets"].values()) and c.term("shadow")
    ordered = sorted(((k, f) for k, f in t["facets"].items() if k != "alias"), key=lambda kf: (kf[1]["t"], kf[1]["line"]))
    believe = []
    for k, f in ordered:
        line, v = r.get(f["line"]), f.get("value")
        if k == "provisional" and isinstance(v, bool):  # a decision's own page: picked for now, or settled, in words
            v and c.term(PICKED)
            believe.append(c.row("", w.t(f"thing.provisional.{str(v).lower()}"), H(basis_of(c, line) + note_mark(c, line))))
            continue
        believe.append(c.row(c.words(line, "facet"), value_of(c, line), H(basis_of(c, line) + note_mark(c, line))))
    aliases = [l for l in lines if l["kind"] == "fact" and (l["body"] or {}).get("facet") == "alias" and standing(l)]
    believe += [c.row(w.t("thing.alias"), ul(value_of(c, l) for l in aliases))] if aliases else []
    believe += pick_rows(c, t)
    believe += assumption_rows(c, t["assumptions"])
    n = len(believe)
    g = t["ground"] if t["ground"] is None or isinstance(t["ground"], str) else canonical(t["ground"])
    items = [w.t("thing.saw.ground", ground=w.ident(x)) for x in dict.fromkeys(([g] if g else []) + world.unworded(c, t))]  # Astra's finding 16
    items += [w.t("thing.saw.source", facet=c.words(r.get(f["line"]), "facet"), source=w.ident(f["source"] or "")) for _, f in ordered if f["basis"] == BASES[2]]
    believe += [c.row("", saw(c, items))] if any(items) else []
    cards = cards_about(c, id)
    asked = question_rows(c, t["questions"])
    rels, decided = {(x["body"] or {}).get("name"): x for x in c.s.relations()}, {d["object"]["id"] for d, _, _ in picks(c, t)}
    linked = goal_rows(c, t["goals"])
    for x in [x for x in t["related"] if x["id"] not in decided]:
        other, how = r.get(x["id"]), rels.get(x["rel"])
        link = H(f'<a href="{c.href("thing", id=x["id"])}">{c.words(other, "name") or w.ident("")}</a>')
        typ = c.words(other, "type") or w.ident("")
        linked.append(c.row("", w.t("thing.link", thing=link, type=typ, how=c.words(how, "gloss")) if words_of(how, "gloss")
                            else w.t("thing.link.bare", thing=link, type=typ)))
    now = lambda l: t["facets"].get((l["body"] or {}).get("facet")) or {"t": "", "line": ""}
    old = [l for l in lines if l["kind"] == "fact" and l.get("mark") not in DOWN and (l["t"], l["id"]) < (now(l)["t"], now(l)["line"])]
    old += [l for _, now, had in picks(c, t) for l in had if l["id"] != now["id"]] + [l for l in lines if l.get("mark") in GONE]
    old = sorted({l["id"]: l for l in old}.values(), key=lambda l: (l["t"], l["id"]), reverse=True)
    earlier = [c.row("", fold(w.t("thing.earlier", lines=w.count("line", len(old))), [about_row(c, l) for l in old]))] if old else []
    every = [about_row(c, l) for l in reversed(lines)]
    every = every[:20] + ([c.row("", fold(w.t("thing.lines.more", lines=w.count("line", len(every) - 20)), every[20:]))] if len(every) > 20 else [])
    body, empty = [], []  # each section with nothing in it is a clause of one sentence in one part, the view's three parts kept (R-READ-22)
    for k, count, noun, rows in (("believe", n, "belief", believe if n else []), ("needs", len(cards), "card", one_card(c, cards)),
                                 ("open", len(t["questions"]), "question", asked), ("linked", len(linked), "item", linked),
                                 ("do", len(t["verbs"]), "verb", t["verbs"] and thing_verbs(c, id, t["verbs"])), ("earlier", len(old), "line", earlier),
                                 ("lines", len(lines), "line", every)):
        if rows:
            body.append(c.part("part." + k, count, noun, w.t("sum." + k), rows, hot=k == "needs"))
        elif k != "needs":
            empty.append(w.t("thing.empty." + k))
    body = "".join(body + ([c.part("part.empty", len(empty), "item", w.t("sum.empty"), [c.row("", w.t("thing.more" if body else "thing.empty",
                                   items=joined(c, empty)))] + (believe if not n else []))] if empty else []))  # all empty: nothing said yet
    name = c.words(o, "name") or w.ident("")
    why = H(thing_note(c, t) + (c.mark(o.get("mark")) if o.get("mark") in ("struck", "superseded") else ""))
    return c.page(name, why, H(""), H(body), where=w.t("top.project", project=c.project(o["unit"])), title_text=plain(name), view="thing")


# the explorer and a type's page: the things by type, every count taken from the lines at this render (03-design.md section 9 point 2)
UNUSED_DAYS = 90


def held(c, line):
    """A type's standing things, newest touched first, each with when it was touched; and the newest of those times, or None."""
    ts = sorted((dict(x, touched=touched(c.s, x["id"])) for x in c.s.things(type=line["body"]["name"])),
                key=lambda x: (x["touched"], x["id"]), reverse=True)
    return line, ts, ts[0]["touched"] if ts else None


def lately(c, last):
    return bool(last) and last >= iso(c.now - _dt.timedelta(days=UNUSED_DAYS))


def in_use(c):
    """The standing types split by whether a thing of theirs was touched in the last UNUSED_DAYS days, each newest touched first."""
    every = sorted((held(c, t) for t in c.s.types()), key=lambda h: h[2] or "", reverse=True)
    return [h for h in every if lately(c, h[2])], [h for h in every if not lately(c, h[2])]


def type_link(c, line):
    return H(f'<a href="{c.href("type", name=line["body"]["name"])}">{c.words(line, "name")}</a>')


def thing_link(c, x):
    return H(f'<a href="{c.href("thing", id=x["id"])}">{c.words(c.r.get(x["id"]), "name") or c.w.ident("")}</a>')


def things(c):
    w = c.w
    c.term("thing", "type")
    used, unused = in_use(c)
    days = w.count("day", UNUSED_DAYS)
    rows = [c.row(w.date(last), H(w.t("things.type", type=type_link(c, line), things=w.count("thing", len(ts))) + ul(thing_link(c, x) for x in ts)))
            for line, ts, last in used]
    later = [c.row("", type_link(c, line), w.t("things.unused.since", date=w.date(last)) if last else w.t("things.unused.never", date=w.date(line["t"])))
             for line, _, last in unused]
    why = w.t("why.things", len(unused), things=w.count("thing", sum(len(ts) for _, ts, _ in used)), types=w.count("type", len(used)),
              unused=w.count("type", len(unused)), days=days)
    body = (c.part("part.types", len(used), "type", w.t("sum.types"), rows or [c.row("", w.t("things.none"))])
            + c.part("part.unused", len(unused), "type", w.t("sum.unused", days=days),
                     [c.row("", fold(w.t("things.unused", types=w.count("type", len(unused))), later))]))
    return c.page(w.t("title.things"), why, H(""), H(body), view="things")


def type_view(c, name):
    w = c.w
    c.term("type", "facet", "ground")
    line, ts, last = held(c, next(t for t in c.s.types() if t["body"]["name"] == name))
    carried = {}
    for x in ts:
        for k in c.s.thing(x["id"])["facets"]:
            carried[k] = carried.get(k, 0) + (k != "alias")
    carried = sorted(((k, n) for k, n in carried.items() if n), key=lambda kn: -kn[1])
    mine = [c.row(w.date(x["touched"]), thing_link(c, x)) for x in ts] or [c.row("", w.t("type.thing.none"))]
    facets = [c.row("", w.t("type.facet", facet=w.ident(k), things=w.count("thing", n))) for k, n in carried] or [c.row("", w.t("type.facet.none"))]
    g = line["body"].get("ground")
    g = g if g is None or isinstance(g, str) else canonical(g)
    about = [c.row("", w.t("type.gloss", gloss=c.words(line, "gloss") or w.t("card.missing"))),
             c.row("", w.t("type.group", group=c.words(line, "group") or w.t("card.missing"))),
             c.row("", saw(c, [w.t("thing.saw.ground", ground=w.ident(g))])) if g else c.row("", w.t("type.ground.none")),
             c.line_row(line, say=w.t("type.line", type=c.words(line, "name")))]  # its own line as a sentence, never its bare name (C3)
    about += [c.line_row(x) for x in c.s.lines(about=line["id"])] or [c.row("", w.t("type.made.none"))]
    why = w.t("why.type", things=w.count("thing", len(ts)), facets=w.count("facet", len(carried)))
    why = why if lately(c, last) else H(why + " " + w.t("type.unused", days=w.count("day", UNUSED_DAYS)))
    body = (c.part("part.type.things", len(ts), "thing", w.t("sum.type.things"), mine)
            + c.part("part.type.facets", len(carried), "facet", w.t("sum.type.facets"), facets)
            + c.part("part.type.about", len(about), "item", w.t("sum.type.about"), about))
    title = c.words(line, "name")
    return c.page(title, why, H(""), H(body), title_text=plain(title), view="type")


# a note about you: every line about the maker, newest first, with its basis, its source and a strike (03-design.md section 6 point 2)
PAGED = {"run": "run", "card": "card", "object": "thing"}  # a source line's kind, and the view that is its page


def source_of(c, line):
    """Where a line about him came from, on any line that names a source (a fact, a tick, which names its portrait's page) or the said
    line it rests on: the source line's page as a link, or its own words; its id or path kept for what I saw."""
    b = line["body"] or {}
    src = b.get("source") if isinstance(b.get("source"), str) and b.get("source") else b.get("said")
    if not isinstance(src, str) or not src:
        return None, None
    item = c.w.t("you.saw.source", line=said(c, line), source=c.w.ident(src))
    got = c.r.get(src) if ID_RE.match(src) else None
    text = got and c.words(got)
    if got and got["kind"] in PAGED:
        text = H(f'<a href="{c.href(PAGED[got["kind"]], id=src)}">{text or named(c.w, "kind.", got["kind"])}</a>')
    return (c.w.t("you.source", source=text) if text else None), item


def strike_form(c, line):
    """One click that strikes the line, the maker's only at the desk; a file cannot send it, as it cannot send an answer."""
    dis = " disabled" if c.as_file else ""
    return H(f'<form class="strike" method="post" action="/strike"><input type="hidden" name="line" value="{line["id"]}">'
             f'<button name="go" value="strike"{dis}>{c.w.t("you.strike")}</button></form>')


def you(c):
    w = c.w
    lines, me = you_lines(c.s, every=True), maker_id(c.s)
    basis = lambda l: (l["body"] or {}).get("basis")
    any(basis(l) in BASES for l in lines) and c.term("basis")  # the words its page shows, glossed at its foot
    any(standing(l) for l in lines) and c.term("struck")
    up = [l for l in lines if standing(l) and l.get("mark") != "waiting"]  # the count: the standing lines, in three kinds that add up to it
    counted, readin = (sum(1 for l in up if basis(l) == b) for b in BASES[1:3])
    own = len(up) - counted - readin  # his word (he said), his own lines, and what he kept on his yes (a guess about him is never written)
    rows, items = [], []
    for l in lines:
        src, item = source_of(c, l)
        items.append(item)
        tail = (basis_of(c, l) if basis(l) in BASES else None, src, note_mark(c, l), c.meta(l, project=True), strike_form(c, l) if standing(l) else None)
        rows.append(c.row(c.stamp(l["t"]), said(c, l), H(" ".join(x for x in tail if x)), attrs=f' data-line="{l["id"]}"'))
    rows = (rows or [c.row("", w.t("you.none"))]) + ([c.row("", saw(c, items))] if any(items) else [])
    about = {l["id"] for l in lines} | ({me} if me else set())
    cards = [x for x in c.r.open_cards() if (x["body"] or {}).get("about") in about]
    down = len(lines) - len(up)
    count = w.t("you.count", lines=w.count("line", len(up)), own=w.count("own", own), counts=w.count("counted", counted), read=w.count("read", readin),
                down=w.t("you.count.down", down, lines=w.count("line", down)) if down else H("")) if lines else w.t("you.none")
    body = (needs(c, cards, one_card(c, cards))
            + c.part("part.you", len(lines), "line", w.t("sum.you.since"), rows)
            + c.part("part.good", len(out := [c.row("", w.t("you.outside"))] * bool(c.r.kind("move"))), "item", w.t("sum.you.good"), out
                     + ([] if c.as_file else [c.row("", c.link("portraits", "link.portraits"))])))  # copies outside only after a move; portraits served only
    return c.page(w.t("title.you"), H(w.t("why.you") + " " + count), H(""), H(body), view="you")


# the portraits: sentences others wrote about him, to tick; served only, never a file (03-design.md section 6 point 6; consistency item 5)
def tick_form(c, n, sha):
    """One click that makes the sentence his line, at the desk only; a file cannot send it, as it cannot send a strike."""
    dis = " disabled" if c.as_file else ""
    return H(f'<form class="tick" method="post" action="/tick"><input type="hidden" name="n" value="{n}"><input type="hidden" name="sha" '
             f'value="{sha}"><button name="go" value="tick"{dis}>{c.w.t("portraits.tick")}</button></form>')


def portrait_rows(c, p, done):
    """A named page as a row (its label, or that it was not found), then each of its sentences with a tick, or the day it was ticked."""
    w = c.w
    label = (H(f'<span data-m="{PORTRAITS}:{p["n"] + 1}" dir="auto">{esc(p["label"])}</span>') if p["label"]
             else w.ident(os.path.basename(p["path"])))
    if not p["found"]:
        return [c.row("", label, w.t("portraits.missing", path=w.ident(p["path"])))], 0
    got = [(f, sha, x) for f in p["files"] for sha, x in sentences(f, p["section"] or None)]
    rows = [c.row("", label, w.count("sentence", len(got)))]
    for f, sha, x in got:
        line = done.get((f, sha))
        text = H(f'<span data-sentence="{sha}" data-m="{esc(f)}" dir="auto">{esc(x)}</span>')
        rows.append(c.row("", text, w.t("portraits.ticked", date=w.date(line["t"])) if line else tick_form(c, p["n"], sha)))
    return rows, len(got)


def portraits(c):
    w, named, done = c.w, read_portraits(c.root), ticked(c.s)
    rows, n = [], 0
    for p in named:
        got, k = portrait_rows(c, p, done)
        rows, n = rows + got, n + k
    n and c.term("tick")
    rows = (rows or [c.row("", w.t("portraits.none"))]) + ([c.row("", saw(c, [w.ident(f) for p in named for f in p["files"] or [p["path"]]]))]
                                                         if named else [])
    body = c.part("part.portraits", n, "sentence", w.t("sum.portraits"), rows)
    return c.page(w.t("title.portraits"), H(w.t("why.portraits") + " " + w.t("portraits.file")), H(""), H(body), view="portraits")


VIEWS = {"brief": brief, "project": project, "run": run, "card": card, "present": present, "find": find, "learned": learned,
         "charter": charter, "book": book, "tool": tool, "graph": graph, "moved": moved, "welcome": welcome, "week": week, "cards": move_cards,
         "thing": thing, "things": things, "type": type_view, "you": you, "portraits": portraits, "world": world.world}


def render(view, workshop, *, lang=None, clock=None, as_file=False, here=None, reader=None, **ids):
    c = Ctx(workshop, lang=lang, clock=clock, as_file=as_file, here=here, reader=reader)
    try:
        c.r.all()
    except Exception as e:  # the index could not be caught up or rebuilt: one sentence, its error in what I saw, then each fault the
        w, c.heads = c.w, {}  # read-back finds, built from the files alone (R-READ-20)
        rows = faults(c, None)
        newest = max((i for ids in c.heads.values() for i in ids), default="-")
        title = w.t("title." + view) if ("title." + view, "") in w.tab else w.t("title.brief")
        return c.page(title, w.t("index.failed", id=w.ident(newest)), saw(c, [w.ident(str(e))]),
                      c.part("part.good", len(rows), "item", w.t("sum.good"), rows) if rows else H(""), head=newest, view=view)
    return VIEWS[view](c, **ids)
