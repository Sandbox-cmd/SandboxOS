# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""Where a thing fits in the world: its name, its type and what that type is out there, and its own ground when it differs, in one line
and in words from the strings table, never as the reference itself (03-design.md section 1 point 4); and the world graph, those things
and the links between them across units, drawn inline as they stand or as they stood on a day, by type and by unit (section 9 point 3)."""
import datetime as _dt

from sandbox_os.store.line import DATE_RE, canonical
from sandbox_os.pages.read import GONE
from sandbox_os.pages.words import H, esc, plain


def ref_of(g):
    return g if g is None or isinstance(g, str) else canonical(g)


def worded(c, ref):
    """Whether the strings table has words for a ground reference (its row ground.<reference>)."""
    return bool(ref) and ("ground." + ref, "") in c.w.tab


def ground_word(c, ref):
    """A ground reference as its word (the row ground.<reference>), else the table's words for a ground it has none for (ground.none),
    never the reference itself, which waits behind what I saw (unworded); None when there is none (Astra's finding 16 of batch D)."""
    ref = ref_of(ref)
    return None if not ref else c.w.t("ground." + ref) if worded(c, ref) else c.w.t("ground.none")


def types_of(c):
    """The standing types by name, read once per render."""
    if not hasattr(c, "types_by_name"):
        c.types_by_name = {t["body"]["name"]: t for t in c.s.types()}
    return c.types_by_name


def type_line(c, name):
    """The newest object line of type 'type' with this name, whatever its mark, or None."""
    return next((l for l in reversed(c.r.all()) if l["kind"] == "object" and (l["body"] or {}).get("type") == "type"
                 and (l["body"] or {}).get("name") == name), None)


def grounds(c, thing):
    """A thing's object line, type, own ground, its type's ground and whether its type is struck, from a Store.thing read or a graph node."""
    if "object" in thing:
        line = type_line(c, thing["type"])
        own = (thing["facets"].get("ground") or {}).get("value") or thing["ground"]
        return thing["object"], thing["type"], own, line and (line["body"] or {}).get("ground"), bool(line) and line.get("mark") in GONE
    return c.r.get(thing["id"]), thing["type"], thing["ground"], thing["type_ground"], thing["type_struck"]


def unworded(c, thing):
    """The ground references of a thing's line the table has no words for, to stand behind what I saw and never in its sentence."""
    _, _, own, tg, _ = grounds(c, thing)
    return [r for r in dict.fromkeys(map(ref_of, (tg, own))) if r and not worded(c, r)]


def ground_line(c, thing, link=False):
    """The name, a type, which is what its type is out there; then its own ground when that differs, then that its type is struck when it
    is; thing is a Store.thing read or a graph node, and link makes the name a link to its page. A ground the table has no words for reads
    as ground.none, once, and its reference waits behind what I saw (unworded)."""
    w = c.w
    o, typ, own, tg, struck = grounds(c, thing)
    name = c.words(o, "name") or w.ident("")
    name = H(f'<a href="{c.href("thing", id=o["id"])}">{name}</a>') if link else name
    standing = types_of(c).get(typ)
    tw = H(f'<a href="{c.href("type", name=typ)}">{c.words(standing, "name")}</a>') if standing else w.ident(typ or "")
    a = w.t("world.an" if plain(tw)[:1].lower() in "aeiou" else "world.a", type=tw)
    g = ground_word(c, tg)
    out = w.t("world.line", name=name, type=a, ground=g) if g else w.t("world.line.bare", name=name, type=a)
    if ref_of(own) and ref_of(own) != ref_of(tg) and (worded(c, ref_of(own)) or not tg or worded(c, ref_of(tg))):
        out = w.t("world.line.own", line=out, ground=ground_word(c, own))
    return w.t("world.struck", line=out) if struck else out


def read_in(c, source):
    """A fact read in a ground reference: that ground's word in the basis sentence; None when the source is not a ground the table knows."""
    return c.w.t("basis.from_ground", ground=c.w.t("ground." + source)) if isinstance(source, str) and ("ground." + source, "") in c.w.tab else None


# the world graph: things and their links across units, as they stand or stood on a day (03-design.md section 9 point 3)
def graph(s, as_of=None, types=None, units=None):
    """Store.graph, the one read of the world: its rule for a duplicate is the store's, the target of supersedes the superseded one and
    the original kept (design section 1 point 1); the pages keep no read of their own beside it."""
    return s.graph(as_of=as_of, types=types, units=units)


def day_of(day, first):
    """A day asked for: a date written YYYY-MM-DD, or the slider's whole number of days after the record's first day; else None."""
    try:
        return (_dt.date.fromisoformat(day) if DATE_RE.match(day) else first + _dt.timedelta(days=int(day)) if day.isdigit() and len(day) < 6
                else None)
    except (TypeError, ValueError, AttributeError):
        return None


def svg(c, nodes, edges, rels):
    """The picture: a column per type in the graph's order and a line per thing, its name beside it toward the middle (R-DESIGN-5); each
    node a link to its thing's page with its ground line on hover, each edge with its relation's gloss on hover; inline, nothing fetched."""
    cols, at = list(dict.fromkeys(n["type"] for n in nodes)), {}
    for k, n in enumerate(nodes):
        i = cols.index(n["type"])
        at[n["id"]] = (round(80 + 640 * i / max(1, len(cols) - 1)), 40 + 32 * k, len(cols) > 1 and i >= len(cols) / 2)
    h = 48 + 32 * len(nodes)
    out = [f'<svg class="world" viewBox="0 0 800 {h}" role="img" aria-labelledby="world-name"><title id="world-name">{esc(c.w.plain("title.world"))}</title>']
    for e in edges:
        (x1, y1, _), (x2, y2, _) = at[e["from"]], at[e["to"]]
        how = plain(c.words(rels.get(e["rel"]), "gloss") or e["rel"])
        out.append(f'<line class="edge" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"><title>{esc(how)}</title></line>')
    for n in nodes:
        x, y, last = at[n["id"]]
        name = c.words(c.r.get(n["id"]), "name", tag="tspan") or ""
        out.append(f'<a href="{c.href("thing", id=n["id"])}"><circle class="node" cx="{x}" cy="{y}" r="9"/>'
                   f'<text x="{x - 14 if last else x + 14}" y="{y + 5}" text-anchor="{"end" if last else "start"}">{name}</text>'
                   f'<title>{esc(plain(ground_line(c, n)))}</title></a>')
    return H("".join(out) + "</svg>")


def options(c, name, chosen, values):
    """A select over (value, words) pairs, its first option any value."""
    opts = [("", c.w.t("world.any"))] + values
    return H(f'<select name="{name}"{" disabled" if c.as_file else ""}>' + "".join(
        f'<option value="{esc(v)}"{" selected" if v == (chosen or "") else ""}>{words}</option>' for v, words in opts) + "</select>")


def world(c, day=None, type=None, unit=None):
    w, r = c.w, c.r
    every, names, units = r.all(), types_of(c), c.s.units()
    today = _dt.date.fromisoformat(r.today())
    first = _dt.date.fromisoformat(r.day(every[0]["t"])) if every else today
    d = day_of(day, first)
    d = d and min(max(d, first), today)
    # the type filter's choices as the vocabulary stood on the day drawn: today's standing types, or on a past day the types its things had
    # then, so a type struck since still filters the day it stood (Astra's finding 13 of batch D)
    then = list(dict.fromkeys(n["type"] for n in graph(c.s, as_of=d.isoformat())["nodes"])) if d and d < today else None
    known = names if then is None else then
    ignored = [k for k, v, ok in (("day", day, d), ("type", type, type in known), ("unit", unit, unit in units)) if v and not ok]
    type, unit = type if type in known else None, unit if unit in units else None
    g = graph(c.s, as_of=d and d.isoformat(), types=type and [type], units=unit and [unit])
    nodes, edges, rels = g["nodes"], g["edges"], {x["body"]["name"]: x for x in c.s.relations()}
    c.term("thing", "type", "ground")
    link = lambda id: H(f'<a href="{c.href("thing", id=id)}">{c.words(r.get(id), "name") or w.ident("")}</a>')
    off, shown = " disabled" if c.as_file else "", d or today
    choices = ([(n, c.words(x, "name")) for n, x in names.items()] if then is None
               else [(n, c.words(type_line(c, n), "name") or w.ident(n)) for n in then])
    form = (f'<form class="box" method="get" action="/graph"><label>{w.t("world.day", date=w.date(shown.isoformat()))}'
            f'<input type="range" name="day" min="0" max="{(today - first).days}" value="{(shown - first).days}"{off}></label>'
            f'<label>{w.t("world.types")}{options(c, "type", type, choices)}</label>'
            f'<label>{w.t("world.units")}{options(c, "unit", unit, [(u, c.project(u)) for u in units])}</label>'
            f'<button type="submit" class="quiet-btn"{off}>{w.t("world.go")}</button></form>')
    project = lambda u: w.t("top.project", project=H(f'<a href="{c.href("project", unit=u)}">{c.project(u)}</a>'))
    from sandbox_os.pages.views import saw  # a reference the table has no words for, behind what I saw (views imports this module)
    seen = lambda n: saw(c, [w.t("thing.saw.ground", ground=w.ident(g)) for g in unworded(c, n)])  # noqa: E731
    things = [c.row("", ground_line(c, n, link=True), H(project(n["unit"]) + seen(n))) for n in nodes] or [c.row("", w.t("world.none"))]
    links = [c.row("", w.t("world.edge", frm=link(e["from"]), to=link(e["to"]), how=c.words(rels.get(e["rel"]), "gloss") or w.ident(e["rel"])))
             for e in edges] or [c.row("", w.t("world.links.none"))]
    why = w.t("why.world.day" if d else "why.world", things=w.count("thing", len(nodes)), links=w.count("link", len(edges)),
              projects=w.count("project", len({n["unit"] for n in nodes})), date=w.date(shown.isoformat()))
    why = H(" ".join([why] + [w.t("world.ignored." + k) for k in ignored]))
    body = (c.part("part.world", len(nodes), "thing", w.t("sum.world"), [c.row("", svg(c, nodes, edges, rels)), c.row("", H(form))])
            + c.part("part.world.things", len(nodes), "thing", w.t("sum.world.things"), things)
            + c.part("part.world.links", len(edges), "link", w.t("sum.world.links"), links))
    return c.page(w.t("title.world"), why, H(""), H(body), view="world")
