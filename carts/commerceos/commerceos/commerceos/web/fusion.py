"""fusion.py — the fusion register's render helpers and plain-word string
sets (CS0, PACK.md "the ruled contracts").

no import of fastapi, no import of web/app.py (context.md "the seam map" —
fusion.py must not import app.py, that would drag fastapi into a pure
module and create the collision CS0 exists to avoid).

escaping law (the record's own: record-born strings escape before markup —
web/app.py:13,856 convention copied here): title, meta, and the group-label
text are record-born short text and are html.escape'd at the interpolation
site. inner_html (page()) and body (ticket()'s receipt-in-place block) are
already-composed HTML handed in by the caller (assembled from other escaped
fusion calls, e.g. this module's own tests) and are NOT re-escaped here —
escaping them again would double-escape valid nested markup. since_line is
record-born (it rides through aged(), itself built from audit-derived
values) and is escaped at the page() interpolation site.
"""

from __future__ import annotations

from html import escape as html_escape

# NOTE (CS2 cleanup, ruled): the FUSION_EDGE_PLAIN / FUSION_GROUP_PLAIN sets
# once lived here but were never rendered anywhere — the edge meaning is a CSS
# class and the group labels are written inline at their call sites. they were
# deleted (one carried "you approved it and it landed", the exact machine-
# subject 'landed' pattern M4 retired). the SF1 lints discover the plain-word
# roster dynamically (any FUSION_*_PLAIN dict), so an empty roster is honest;
# the lints keep real subjects to walk — the triage sentences and the
# rendered-surface land-guard.


def aged(value: str, asof: str) -> str:
    """the only place fusion.py concatenates the age onto a mirror-derived
    number (PACK.md — mirror-lint depends on this being the one formatter,
    one law): "78.5" + "last night" -> "78.5 as of last night"."""
    return f"{value} as of {asof}"


# the four edge meanings a ticket may wear — anything else is a design
# change, not a parameter (PACK.md "the ruled contracts").
_EDGES = {"waiting", "running", "stopped", "done"}


def ticket(title, meta, edge, action_label=None, action_href=None, body=None) -> str:
    """the desk's unit: a card with a title, one meta line, a colored edge
    that means one thing, and an optional action + an optional receipt-in-
    place block that opens on the ticket (spec/parts/collab-surface.md "the
    desk contributes the unit"). title/meta are html.escape'd; body is
    already-composed HTML from the caller (see module docstring) and rides
    through unescaped, the same way page()'s inner_html does."""
    if edge not in _EDGES:
        raise ValueError(
            f"ticket(edge={edge!r}) — the four meanings are {sorted(_EDGES)}, "
            "a fifth color is a design change, not a parameter"
        )

    action_html = ""
    if action_label is not None and action_href is not None:
        action_html = (
            f'<a href="{html_escape(action_href)}">{html_escape(action_label)} →</a>'
        )

    card = (
        f'<div class="ticket {edge}">'
        f'<div><span class="t">{html_escape(title)}</span>'
        f'<span class="m">{html_escape(meta)}</span></div>'
        f"{action_html}"
        f"</div>"
    )
    if body:
        card += f'<div class="receipt">{body}</div>'
    return card


def group_label(text) -> str:
    """the desk's small-caps, letterspaced group heading (spec/parts/
    collab-surface.md "under load" — eyes-first / routine / stopped)."""
    return f'<div class="group-label">{html_escape(text)}</div>'


def page(inner_html, since_line=None) -> str:
    """wraps composed inner_html (sentence + groups + tickets + doors,
    assembled by the caller — CS1's route handlers, CS0's own render
    fixtures) in the fusion shell. the <link> to /static/fusion.css is
    CS1's business to serve; page() only references the path (PACK.md "the
    ruled contracts") — it inlines nothing and opens no file. since_line,
    when given, is the page's own freshness stamp (typically aged()'s
    output) rendered once near the top, escaped like any record-born
    string."""
    since_html = f"<span>{html_escape(since_line)}</span>" if since_line else ""
    return (
        '<link rel="stylesheet" href="/static/fusion.css">'
        '<div class="wrap"><div class="inner">'
        f'<div class="tiny"><span>commerceos</span>{since_html}</div>'
        f"{inner_html}"
        "</div></div>"
    )
