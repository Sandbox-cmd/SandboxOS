# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The frame every view is built in: the context of one render (the store, the words, served or a file), the blocks
(top bar, title with its why and the story so far, part, row, card, run line, the foot of links, and the action bar while a
card waits), the example line, the legend, a line's own words with their language, and where each view lives as a route and a file."""
import os
import urllib.parse

from sandbox_os import VERSION
from sandbox_os import store as _store
from sandbox_os.pages.read import Reader, words_of, seeded, RESTS
from sandbox_os.pages.words import Words, H, esc, plain, direction

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
CSP = ("default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; font-src 'self'; img-src 'self' data:; "
       "form-action 'self'; base-uri 'none'")
FACES = (("BricolageGrotesque", "Bricolage Grotesque"), ("IBMPlexSansArabic", "IBM Plex Sans Arabic"), ("IBMPlexMono", "IBM Plex Mono"))
WEIGHTS = (("ExtraBold", "800"), ("SemiBold", "600"), ("Bold", "700"), ("Medium", "500"), ("Regular", "400"), ("Variable", "100 900"))
PAGES = ("brief", "find", "learned", "charter", "book", "tool", "welcome", "things", "you", "world")
UNIT_PAGES = ("project", "present", "graph", "moved")
SERVED = {"portraits": "/you/tick"}  # a view served only, never written as a file, at its route (consistency item 5)
MARKS = ("proved", "not yet", "recorded", "struck", "deleted", "erased", "superseded", "past", "waiting", RESTS)
LINKS = (("brief", "link.brief"), ("find", "link.find"), ("learned", "link.learned"), ("charter", "link.charter"),
         ("book", "link.book"), ("tool", "link.tool"), ("things", "link.things"), ("you", "link.you"))


def welcome_answers(text, w):
    """welcome.md's lines by their English keys, each value verbatim after the key's one space."""
    keys = {k: w.tab[("md.welcome." + k, "")]["en"] for k in ("name", "making", "ask", "language", "locale")}
    out = {}
    for line in (text or "").splitlines():
        for k, key in keys.items():
            if line.startswith(key):
                v = line[len(key):]
                out[k] = v[1:] if v.startswith(" ") else v
    return out


class Ctx:
    """One render: the record read once, the words in the chosen language, and whether it is served or written to a file."""

    def __init__(self, workshop, *, lang=None, clock=None, as_file=False, here=None, reader=None, machine="pages"):
        self.s = workshop if hasattr(workshop, "lines") else _store.open(workshop, read_only=True, clock=clock, machine=machine)
        self.r = reader or Reader(self.s)
        self.now = self.s.clock()
        self.root, self.as_file, self.here, self.lang_asked = self.s.root, as_file, here, lang
        base = Words("en", root=self.root, now=self.now)
        self.welcome_text = self.r.welcome()
        self.welcome = welcome_answers(self.welcome_text, base)
        lang = lang or self.welcome.get("language") or "en"
        self.w = Words(lang, self.welcome.get("locale"), root=self.root, now=self.now)
        self.terms, self.cards, self.extra, self.links, self.made = [], [], [], LINKS, {}  # the menu; the welcome before a first run offers none
        self.waiting = 0  # every open card the page knows of, shown whole or counted (the first whole, the rest counted)
        self.example = bool((self.s.home or {}).get("example"))

    def term(self, *names):
        for n in names:
            if n not in self.terms:
                self.terms.append(n)

    # where a view lives
    def path_of(self, view, unit=None, id=None, week=None, name=None, **_):
        """A view's file, relative to the workshop root; the week's names its ISO week, the last complete one when none is given."""
        if view == "week":
            from sandbox_os.pages import measures  # measures reads the frame's welcome; this call comes after both are loaded
            return f"pages/week-{week or measures.last_week(self.now)}.html"
        if view in PAGES or view == "cards":  # the move's cards (card 23) at pages/cards-move.html
            return "pages/cards-move.html" if view == "cards" else f"pages/{view}.html"
        if view == "type":
            return f"pages/types/{name}.html"
        if view in UNIT_PAGES:
            return f"projects/{unit}/pages/{'brief' if view == 'project' else view}.html"
        line = self.r.get(id)
        return f"projects/{line['unit']}/pages/{view}s/{self.r.day(line['t'])}-{id}.html"

    def href(self, view, **ids):
        if self.as_file:
            return esc(urllib.parse.quote(os.path.relpath(self.path_of(view, **ids), os.path.dirname(self.here or "pages/x.html"))))
        if view == "world":  # the world graph at /graph, its day, type and unit in the query
            q = [(k, ids[k]) for k in ("day", "type", "unit") if ids.get(k)] + ([("lang", self.lang_asked)] if self.lang_asked else [])
            return esc("/graph" + ("?" + urllib.parse.urlencode(q) if q else ""))
        key = ids.get("unit") or ids.get("id") or ids.get("week") or ("move" if view == "cards" else None) or ids.get("name")
        q = urllib.parse.urlencode([(k, v) for k, v in (("q", ids.get("q")), ("lang", self.lang_asked)) if v])  # an example search, the language asked
        return esc((SERVED.get(view) or ("/" if view == "brief" else f"/{view}" + (f"/{urllib.parse.quote(key)}" if key else ""))) + (q and "?" + q))

    def link(self, view, sid, **ids):
        return H(f'<a href="{self.href(view, **ids)}">{self.w.t(sid)}</a>')

    # a line's own words
    def words(self, line, field=None, tag="span", cls=None, quote=False):
        """A line's own words as an element carrying its id, its language and its direction; a gone line shows its mark's sentence."""
        c = f' class="{cls}"' if cls else ""
        if line is None:
            return H("")
        if line.get("body") is None:
            return self.w.t("mark.gone", tag=tag, cls=cls)
        if field == "name" and seeded(self.w, line):  # a seeded verb's or service's name in both languages
            return self.w.t(seeded(self.w, line), tag=tag, cls=cls)
        text = words_of(line, field)
        if text is None:
            return None
        lang = line.get("lang")
        la = f' lang="{esc(lang)}" dir="{direction(lang)}"' if lang else ' dir="auto"'
        return H(f'<{tag}{c} data-l="{line["id"]}"{la}>{esc(text)}</{tag}>')

    def project(self, unit):  # by its own words, as the terminal's receipt prints them; its folder name when the record holds none (R-DESIGN-10)
        return self.made.get(unit) or self.made.setdefault(unit, next((self.words(l, "words") for l in self.r.kind("note", units=[unit])
                                                    if (l["body"] or {}).get("event") == "project-made" and words_of(l, "words")), None) or self.w.ident(unit))

    def who(self, line):
        by = line["by"]
        k, name = by["kind"], by.get("name") or ""
        if k == "partner" and name in ("", "partner"):  # the partner's tools record its kind as its name: said once (R-DESIGN-4)
            return self.w.t("row.meta.partner")
        return self.w.t("who.maker") if k == "maker" else self.w.t(f"who.{k}", name=self.w.ident(name))

    def meta(self, line, project=False):
        sid = "row.meta.project" if project else "row.meta"
        return self.w.t(sid, cls="meta", who=self.who(line), when=self.w.when(line["t"]), project=self.project(line["unit"]))

    def mark(self, m):
        if not m:
            return H("")
        self.term(m)
        return self.w.t("mark." + m, cls="mk p" if m == "proved" else "mk")

    # the blocks
    def row(self, mark, text, why=None, attrs="", cls="row"):
        return H(f'<div class="{cls}" tabindex="-1"{attrs}><span class="mark">{mark or ""}</span><span class="text">{text}</span>'
                 + (f'<span class="why">{why}</span>' if why else "") + "</div>")

    def stamp(self, t):
        """A row's mark column: the time when the line is from today, else its date."""
        return self.w.time(t) if self.r.day(t) == self.r.today() else self.w.date(t)

    def line_row(self, line, project=False, why=None, field=None, mark=True, say=None):
        """A line as a row: its time, its words (or what say gives), who and when, and its mark."""
        said = say or self.words(line, field)
        tail = H((self.mark(line.get("mark")) if mark else "") + self.meta(line, project) + (why or ""))
        return self.row(self.stamp(line["t"]), said or self.w.t("kind." + line["kind"] + ".row"), tail)  # what the line is, never a bare kind word (C3)

    def part(self, label, n, noun, summary, rows, hot=False, aria=None):
        aria = esc(plain(aria or self.w.count(noun, n)))  # what the number counts, said whole to a screen reader
        cls = "n hot" if hot and n else "n"
        body = "".join(rows)
        return H(f'<section class="part"><div class="label">{self.w.t(label, tag="h2")} <span class="{cls}" aria-label="{aria}">{self.w.num(n)}</span>'
                 f'<span class="sum">{summary}</span></div><div class="rows">{body}</div></section>')

    def story(self, line):
        if line is None:
            body = f"<p>{self.w.t('story.none')}</p>"
        else:
            self.term("story")
            body = self.words(line, tag="p") + self.w.t("story.by", cls="by", who=self.who(line), when=self.w.when(line["t"]))
        return H(f'<div class="story"><div class="lbl">{self.w.t("story.label")}</div>{body}</div>')

    def actions(self, what=None):
        """The bar, only while this page has something to answer: a card's keys and the count of cards left, or the view's own (what)."""
        w = self.w
        if not (what or self.cards):
            return ""
        keys, left = what, ""
        if not what:
            n = len(self.cards)
            keys = (f'<span class="what">{w.t("actions.answer", i=w.ident(1))}</span>'
                    + "".join(f"<span>{w.key(k)}{w.t('actions.' + a)}</span>" for k, a in (("y", "yes"), ("n", "no"), ("l", "later")))
                    + (f"<span>{w.key(2)}{w.t('actions.open', i=w.ident(2))}</span>" if n > 1 else "")
                    + f"<span>{w.key('Esc')}{w.t('actions.esc')}</span>")
            left = w.t("actions.left", cls="state count", n=w.num(1), cards=w.count("card", max(n, self.waiting)))
        return H(f'<div class="actions{"" if what else " keys"}" aria-label="{esc(w.plain("aria.actions"))}"><div class="in">{keys}{left}</div></div>')

    def foot(self):
        """The column's last block: what else can be said and where, the other pages, and on a file that answering needs it served."""
        w = self.w
        links = " ".join(f'<a href="{self.href(v)}">{w.t(s)}</a>' for v, s in self.links)
        return H(f'<nav class="foot" aria-label="{esc(w.plain("aria.foot"))}">{w.t("actions.else", tag="p")}' + (f"<p>{links}</p>" if links else "")
                 + (w.t("actions.file", tag="p") if self.as_file else "") + "</nav>")

    def legend(self):
        w = self.w
        items = "".join(f'<dt class="{"mono proved" if t == "proved" else "mono" if t in MARKS else ""}" data-s="legend.{t}">'
                        f'{esc(w.raw("legend." + t))}</dt>{w.t("legend." + t + ".d", tag="dd")}' for t in self.terms)
        return H(f'<div class="legend" aria-label="{esc(w.plain("aria.legend"))}">{w.t("legend.label", tag="h2", cls="lbl")}<dl>{items}</dl></div>')

    def page(self, title, why, story, body, *, where=None, demo=(), title_text=None, head=None, view="", bar=None):
        """The whole document: the head with its policy and stamp, the blocks, the legend, the foot, the script."""
        w = self.w
        where = where or w.t("top.all")
        self.stamp_head = head or (self.r.head(self.here.split("/")[1]) if (self.here or "").startswith("projects/") else self.r.head()) if self.as_file else None
        you = (f'<span data-m="welcome.md">{esc(self.welcome["name"])}</span>' if self.welcome.get("name") else w.t("who.you"))
        lang = "" if self.as_file else (f'<span class="lang"><a href="?lang=en" lang="en">{w.t("lang.en")}</a>'
                                        f'<a href="?lang=ar" lang="ar">{w.t("lang.ar")}</a></span>')
        ws = w.t("top.workshop", name=w.ident(os.path.basename(self.root)))
        top = (f'<nav class="top" aria-label="{esc(w.plain("aria.top"))}"><span class="ws">'
               + (f'<a href="{self.href("brief")}">{ws}</a>' if self.links else ws) + f'</span><span class="where">{where}</span>'
               f'<span class="you">{you}</span><span class="time">{w.when(self.now)}</span>{lang}</nav>')
        stamp_line = [w.t("file.stamp", when=w.when(self.now), id=w.ident(self.stamp_head or "-"))] if self.as_file else []
        demo = "".join([w.t("example.walk" if self.example else "example.real"), *demo, *self.extra, *stamp_line])
        actions = self.actions(what=bar)
        stamp = (f'<meta name="tenth-written" content="{esc(self.now.strftime("%Y-%m-%dT%H:%M:%SZ"))} head={self.stamp_head} '
                 f'tool={VERSION} example={"yes" if self.example else "no"}">' if self.as_file else "")
        return H(f'<!doctype html>\n<html lang="{w.lang}" dir="{w.dir}">\n<head>\n<meta charset="utf-8">\n'
                 f'<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                 f'<meta http-equiv="Content-Security-Policy" content="{CSP}">\n{stamp}\n<title>{esc(title_text or plain(title))}</title>\n'
                 f'<style>{self.faces()}{open(os.path.join(HERE, "tenth.css"), encoding="utf-8").read()}</style>\n</head>\n'
                 f'<body data-view="{view}"{" data-file" if self.as_file else ""}>\n<div class="col">\n{top}\n<p class="demo">{demo}</p>\n'
                 f'<main>\n<header class="head"><h1>{title}</h1><p class="why">{why}</p>{story}</header>\n<div class="parts">\n{body}\n</div>\n'
                 f'{self.legend()}\n</main>\n{self.foot()}\n</div>\n{actions}\n<script>{open(os.path.join(HERE, "tenth.js"), encoding="utf-8").read()}</script>\n'
                 f'</body>\n</html>\n')

    def faces(self):
        """@font-face for each face present in pages/fonts/; with none there, the stacks fall back to system faces."""
        files = sorted(f for f in (os.listdir(FONTS) if os.path.isdir(FONTS) else []) if f.endswith(".woff2"))
        here = self.here or "pages/x.html"
        mine = "/".join(here.split("/")[:3]) if here.startswith("projects/") else "pages"
        base = os.path.relpath(mine + "/fonts", os.path.dirname(here)) if self.as_file else "/fonts"
        out = []
        for f in files:
            fam = next((name for pre, name in FACES if f.startswith(pre)), None)
            wt = next((v for k, v in WEIGHTS if k in f), "400")
            if fam:
                out.append(f"@font-face{{font-family:'{fam}';src:url('{base}/{f}') format('woff2');font-weight:{wt};font-display:swap}}")
        return "".join(out)

