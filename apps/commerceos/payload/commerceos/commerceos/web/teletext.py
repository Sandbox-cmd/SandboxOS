"""the teletext broadcast frame — small plain functions that return HTML
strings, one per repeated component. the whole operator surface is dressed
by these so it reads as one tuned channel, not a log.

no templating engine, no build step, no JS: strings, matching the app's
existing style. every colour lives in tokens.css / teletext.css; nothing
here reaches for a raw hex. the block-mosaic meter and the P-blocks are the
material; the discipline (one amber call, one slap, supercolor only on
parts) lives in the routes that call these.
"""

from __future__ import annotations

# the operator interface is organized by intent, not by table name (RULED
# 2026-07-12). each job-area is a teletext channel number — the P-page the
# masthead announces. "system" (/parts) is the O4 self-report, reachable from
# the masthead corner rather than the job strip.
PAGE_NO = {
    "home": "100",
    "operations": "200",
    "decisions": "300",
    "record": "400",
    "system": "500",
    "fleet": "510",
    "money": "600",
    "growth": "700",
}

# the job-based top nav (RULED 2026-07-12): home · decisions · operations ·
# record · money · growth. each maps onto a route that already works; this is
# a relabel + reorganize of the shell, not a data change. operations lands on
# the catalog overview (catalog is the first operation).
NAV = (("/", "home"), ("/approvals", "decisions"), ("/catalog", "operations"),
       ("/record", "record"), ("/economics", "money"), ("/findings", "growth"))

_BLOCKS = "░▒▓█"  # teletext block-mosaic ramp (empty → full)


def meter(rate, cells: int = 18) -> str:
    """the block-mosaic coverage meter — pure teletext material. a rate in
    0..1 becomes a run of full blocks over light-shade empties, then its
    percent. rate None / non-numeric renders an honest em-dash, never a
    faked bar."""
    if not isinstance(rate, (int, float)):
        return "<span class='meter'><span class='pct'>—</span></span>"
    r = max(0.0, min(1.0, float(rate)))
    fill = round(r * cells)
    empty = cells - fill
    pct = f"{round(r * 100, 1)}%"
    return (f"<span class='meter'>"
            f"<span class='fill'>{'█' * fill}</span>"
            f"<span class='empty'>{'░' * empty}</span> "
            f"<span class='pct'>{pct}</span></span>")


def teletext_bar(left: str, right: str = "") -> str:
    return (f"<div class='teletext-bar'><span>{left}</span>"
            f"<span>{right}</span></div>")


def block(bar_left: str, rows_html: str, bar_right: str = "",
          block_id: str = "", style: str = "") -> str:
    """a titled P-block: the bell-blue bar over its rows. the reusable
    broadcast container every page fills."""
    idattr = f" id='{block_id}'" if block_id else ""
    styleattr = f" style='{style}'" if style else ""
    return (f"<div class='teletext'{idattr}{styleattr}>"
            f"{teletext_bar(bar_left, bar_right)}{rows_html}</div>")


def idx_row(no: str, name: str, stat_html: str, action_html: str = "",
            row_id: str = "") -> str:
    """a numbered index row: num · NAME · stat · action."""
    idattr = f" id='{row_id}'" if row_id else ""
    return (f"<div class='teletext-row idx-row'{idattr}>"
            f"<span class='no'>{no}</span>"
            f"<span class='name'>{name}</span>"
            f"<span class='stat'>{stat_html}</span>"
            f"{action_html}</div>")


def state_row(k: str, v_html: str, total: bool = False) -> str:
    cls = "teletext-row state-row total" if total else "teletext-row state-row"
    return (f"<div class='{cls}'><span class='k'>{k}</span>"
            f"<span class='v'>{v_html}</span></div>")


def masthead(section: str, big_html: str, sub: str, split_html: str = "",
             as_of: str = "") -> str:
    """the station identifier bar + marquee: commerceos · store · section
    on the left (the store the surface speaks for, always — behavior 4,
    RULED), the P-page + as-of on the right, then the big count and its
    split. big_html carries the one large number (or the section name);
    split_html the active/draft/archived breakdown when a page has one."""
    from commerceos import stores

    page = PAGE_NO.get(section, "000")
    right = f"p{page}" + (f" · as of {as_of}" if as_of else "")
    return (f"<div class='masthead'>"
            f"{teletext_bar(f'commerceos · {stores.active_store()} · {section}', right)}"
            f"<div class='marquee'>"
            f"<div class='count'>{big_html}<small>{sub}</small></div>"
            f"{split_html}</div></div>")


def nav_bar(here: str) -> str:
    """the job-based nav rendered as a teletext-bar strip — the one masthead
    every route wears. 'system' (/parts) rides the right corner so the O4
    self-report stays reachable from every page without crowding the jobs."""
    links = " ".join(
        f"<a href='{h}' class='here'>{t}</a>" if t == here else f"<a href='{h}'>{t}</a>"
        for h, t in NAV)
    sys_here = " class='here'" if here == "system" else ""
    return (f"<div class='channel-nav'>"
            f"<div class='teletext-bar'><span class='links'>{links}</span>"
            f"<span class='links'><a href='/parts'{sys_here}>system</a></span>"
            f"</div></div>")


def catalog_subnav(here: str) -> str:
    """the catalog channel's own index — the sub-nav under _operations_. the
    top nav is the one masthead; this is the catalog's five-view index. only
    the built views are live links; a view still to come wears a plain 'soon'
    so the tab reads as the nav, never as a dead number."""
    tabs = [("/catalog", "overview", True),
            ("/catalog/products", "products", True),
            ("/catalog/workflows", "workflows", True),
            ("/catalog/flags", "flags", True)]
    parts = []
    for href, label, live in tabs:
        if not live:
            parts.append(f"<span class='soon'>{label} <span class='soon-tag'>soon</span></span>")
        elif label == here:
            parts.append(f"<a href='{href}' class='here'>{label}</a>")
        else:
            parts.append(f"<a href='{href}'>{label}</a>")
    return (f"<div class='sub-nav'><div class='teletext-bar'>"
            f"<span class='links'>catalog · {' · '.join(parts)}</span>"
            f"<span></span></div></div>")


def chip(label: str, href: str | None = None, active: bool = False,
         tone: str = "") -> str:
    """a teletext filter chip — a small selectable token. `active` wears the
    'on' highlight; `tone` (e.g. 'gap', 'flag') colours it. a chip with an
    href is a link (a filter or a tab); without one it is a plain marker (a
    gap a card carries), never clickable."""
    cls = "chip" + (" on" if active else "") + (f" chip--{tone}" if tone else "")
    if href:
        return f"<a class='{cls}' href='{href}'>{label}</a>"
    return f"<span class='{cls}'>{label}</span>"


def pcard(href: str, title: str, sub: str, chips_html: str = "") -> str:
    """a compact product card in a board lane: the title (a cyan link to the
    drill) over its identity line, then the plain gap chips it carries."""
    chips = f"<span class='chips'>{chips_html}</span>" if chips_html else ""
    return (f"<a class='pcard' href='{href}'>"
            f"<span class='pcard-title'>{title}</span>"
            f"<span class='pcard-sub'>{sub}</span>{chips}</a>")


def board_lane(page_no: str, label: str, count: int, cards_html: str,
               more_html: str = "") -> str:
    """one stage lane of the combined board — a P-block column. the plain
    stage label LEADS with its live count on the bell-blue bar (the
    'active · 1,204' shape); the cards fill the body below. an empty lane
    says so plainly rather than rendering a bare frame."""
    body = cards_html or "<p class='lane-empty muted'>none here</p>"
    return (f"<div class='lane'>"
            f"{teletext_bar(f'{label} · {count:,}', page_no)}"
            f"<div class='lane-body'>{body}{more_html}</div></div>")


def board(lanes_html: str) -> str:
    """the combined board — the stage lanes laid side by side over one
    surface, so the pipeline and the filtered table are one thing."""
    return f"<div class='board'>{lanes_html}</div>"


def receipt(verdict: str, text: str, tone: str = "") -> str:
    """one run-log ledger line — a code-written receipt. the plain verdict
    ('showed up live? yes' / 'still to check') leads; the item it belongs to
    follows. tone 'ok' marks a verified-live line, 'warn' one still open."""
    cls = "receipt" + (f" receipt--{tone}" if tone else "")
    return (f"<div class='{cls}'><span class='verdict'>{verdict}</span>"
            f"<span class='what'>{text}</span></div>")


def timeline_row(when: str, move: str, who: str, why: str = "") -> str:
    """one move in a product's life — when · what moved · who · why, as a plain
    teletext row (the history timeline block)."""
    why_html = f"<span class='why'>{why}</span>" if why else ""
    return (f"<div class='teletext-row tl-row'>"
            f"<span class='when'>{when}</span>"
            f"<span class='move'>{move}</span>"
            f"<span class='who'>{who}</span>{why_html}</div>")


def signoff(section: str, line: str) -> str:
    return (f"<p class='signoff' style='margin-top:var(--sp-6)'>"
            f"commerceos · {section} · {line}</p>")
