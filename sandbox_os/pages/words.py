# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The words: the strings table and a workshop's local overrides, plurals by language, locales with their digits and months,
isolation of every slot, and the formatters every numeral passes through (a count with its noun, a length of time, a time, a date, an identifier)."""
import csv
import datetime as _dt
import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RTL = ("ar", "he", "fa", "ur")
EASTERN = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
SLOT = re.compile(r"\{(\w+)\}")


class H(str):
    """Text already safe as HTML: a formatter's output or a rendered fragment; anything else is escaped on the way in."""


def esc(s):
    return s if isinstance(s, H) else H(html.escape("" if s is None else str(s), quote=True))


def plain(s):
    """The text a reader sees, without the markup: for attributes, titles and the markdown files."""
    return html.unescape(re.sub(r"<[^>]*>", "", str(s)))


def read_tsv(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)]
    head = rows[0]
    return [dict(zip(head, r + [""] * (len(head) - len(r)))) for r in rows[1:] if any(c.strip() for c in r)]


def table(root=None):
    """(id, form) to its row; `<workshop>/strings.local.tsv` replaces every row of an id it names."""
    rows = read_tsv(os.path.join(HERE, "strings.tsv"))
    local = os.path.join(root, "strings.local.tsv") if root else None
    if local and os.path.exists(local):
        over = read_tsv(local)
        mine = {r["id"] for r in over}
        rows = [r for r in rows if r["id"] not in mine] + over
    return {(r["id"], r["form"]): r for r in rows}


def locales():
    return {r["locale"]: r for r in read_tsv(os.path.join(HERE, "locales.tsv"))}


def plural(lang, n):
    """The plural form of n: Arabic's six (zero, one, two, few, many, other), English's three (zero, one, other); a fraction is other."""
    if not isinstance(n, int) or isinstance(n, bool):
        return "other"
    if lang == "ar":
        m = n % 100
        return ("zero" if n == 0 else "one" if n == 1 else "two" if n == 2 else "few" if 3 <= m <= 10
                else "many" if 11 <= m <= 99 else "other")
    return "zero" if n == 0 else "one" if n == 1 else "other"


def digits(s, system):
    return s.translate(EASTERN) if system == "arab" else s


def direction(lang):
    return "rtl" if (lang or "").split("-")[0] in RTL else "ltr"


class Words:
    """The pages' own words in one language and locale; every method returns safe HTML whose text a test can trace to the table."""

    def __init__(self, lang="en", locale=None, *, root=None, now=None, zone=None):
        self.tab, self.locs = table(root), locales()
        self.lang = lang if any(r["language"] == lang for r in self.locs.values()) else "en"
        mine = [k for k, r in self.locs.items() if r["language"] == self.lang]
        self.locale = locale if locale in mine else mine[0]
        self.system, self.months = self.locs[self.locale]["digits"], self.locs[self.locale]["months"]
        self.dir, self.zone = direction(self.lang), zone
        self.now = now or _dt.datetime.now(_dt.timezone.utc)

    def raw(self, id, form=""):
        """A table cell in this language; a missing form falls back to other, a missing language to English."""
        rows = [self.tab.get((id, form)), self.tab.get((id, "other")), self.tab.get((id, ""))]
        for col in (self.lang, "en"):
            cell = next((r[col] for r in rows if r and r.get(col)), None)
            if cell is not None:
                return cell
        raise KeyError(id)

    def fill(self, template, slots):
        parts = SLOT.split(template)
        return "".join(esc(p) if i % 2 == 0 else slots[p] if isinstance(slots.get(p), H)
                       else f'<bdi data-f="slot">{esc(slots.get(p, "{" + p + "}"))}</bdi>' for i, p in enumerate(parts))

    def t(self, id, n=None, /, *, tag="span", cls=None, **slots):
        """A table entry as an element carrying its id; slots are isolated, and {n} goes through the count's number."""
        form = plural(self.lang, n) if n is not None else ""
        if n is not None:
            slots.setdefault("n", self.num(n))
        c = f' class="{cls}"' if cls else ""
        return H(f'<{tag}{c} data-s="{esc(id)}">{self.fill(self.raw(id, form), slots)}</{tag}>')

    def plain(self, id, n=None, /, **slots):
        return plain(self.t(id, n, **slots))

    def num(self, n):
        s = f"{n:,}" if isinstance(n, int) else f"{n:,.2f}"
        return H(f'<bdi data-f="n">{digits(s, self.system).replace(",", "٬" if self.system == "arab" else ",")}</bdi>')

    def count(self, noun, n):
        """A count with its noun: the only way a number of things reaches a page."""
        return self.t("count." + noun, n)

    def duration(self, hours):
        """A length of time as a person says it (R-DESIGN-17): seconds under ninety, hours and minutes under two days, else days and hours."""
        s, m, h = round(hours * 3600), round(hours * 60), round(hours)
        if s < 90:
            return self.count("second", s)
        two = (("hour", m // 60), ("minute", m % 60)) if m < 2880 else (("day", h // 24), ("hour", h % 24))
        return H(esc(self.raw("duration.and")).join(self.count(unit, n) for unit, n in two if n))

    def local(self, t):
        t = _dt.datetime.fromisoformat(t) if isinstance(t, str) else t
        return t.astimezone(self.zone) if self.zone else t.astimezone()

    def time(self, t):
        return H(f'<bdi data-f="time">{digits(self.local(t).strftime("%H:%M"), self.system)}</bdi>')

    def date(self, t):
        d, now = self.local(t), self.local(self.now)
        slots = {"weekday": self.raw(f"weekday.{d.weekday()}"), "day": str(d.day), "year": str(d.year),
                 "month": self.raw(f"month.{self.months}.{d.month}")}
        text = SLOT.sub(lambda m: slots[m.group(1)], self.raw("fmt.date" if d.year == now.year else "fmt.date.year"))
        return H(f'<bdi data-f="date">{esc(digits(text, self.system))}</bdi>')

    def when(self, t):
        return self.t("fmt.when", date=self.date(t), time=self.time(t))

    def ident(self, s):
        return H(f'<bdi data-f="id">{esc(s)}</bdi>')

    def key(self, k):
        return H(f'<kbd><bdi data-f="key">{esc(k)}</bdi></kbd>')
