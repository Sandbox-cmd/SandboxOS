"""period P&L assembled from landed facts — every cell cites its facts.

two lanes, explicit everywhere (the fresh-start ruling, landed 2026-07-11:
this is a fresh start company; the old numbers are for learnings, the new
company earns its own):

- lane="company" (the default): the fresh company's own facts — settlement
  aggregates over orders / order_lines / returns (the spine lands the split
  per line, spine/settlement.py; this module only aggregates), payout and
  fee lines from Shopify, books imports tagged for the new entity, and
  ad-spend facts. TODAY this lane is honestly empty: zero orders, every
  missing input a named gap — empty but real.
- lane="learnings": the old company's FTA/Zoho history — money_lines whose
  source starts with 'fta:' or 'zoho:'. read-only reference: baselines,
  lessons, and the engine-correctness proof. it NEVER enters company P&L.

a fact row's lane is decided by its source prefix (LEARNINGS_SOURCE_PREFIXES).
the only combined view is overlay(), and it carries the label
"learnings overlay" — two lanes side by side, cells never merged.

the contract: a number that cannot cite its source facts does not render.
every cell carries provenance — the fact ids when few (<= IDS_CAP), and a
count + query descriptor always. an input with zero facts becomes a named
gap, never a zero pretending to be measured. derived cells (spread,
margin) name the cells they derive from; the chain ends in facts.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

IDS_CAP = 100  # a cell lists its fact ids up to here; past it, count + query stand

LANES = ("company", "learnings")
LEARNINGS_SOURCE_PREFIXES = ("fta:", "zoho:")  # the old company's systems
OVERLAY_LABEL = "learnings overlay"  # the only label a combined view may wear

_YEAR = re.compile(r"^(\d{4})$")
_MONTH = re.compile(r"^(\d{4})-(\d{2})$")
_QUARTER = re.compile(r"^(\d{4})-?[Qq]([1-4])$")


def lane_sql(lane: str, column: str = "source") -> str:
    """the SQL predicate that decides a fact row's lane, by source prefix.

    learnings = source starts with an old-company prefix; company = the rest.
    prefixes are module constants, never user input.
    """
    likes = " OR ".join(f"{column} LIKE '{p}%'" for p in LEARNINGS_SOURCE_PREFIXES)
    return f"({likes})" if lane == "learnings" else f"NOT ({likes})"


def _check_lane(lane: str) -> None:
    if lane not in LANES:
        raise ValueError(
            f"unknown lane {lane!r} — use 'company' or 'learnings'; the only combined"
            f" view is overlay(), and it carries the {OVERLAY_LABEL!r} label")


def parse_period(period: str) -> tuple[str, str]:
    """'2025' | '2025-07' | '2025-Q3' -> (start, end) ISO dates, end exclusive."""
    if m := _YEAR.match(period):
        y = int(m.group(1))
        return f"{y:04d}-01-01", f"{y + 1:04d}-01-01"
    if m := _MONTH.match(period):
        y, mo = int(m.group(1)), int(m.group(2))
        if not 1 <= mo <= 12:
            raise ValueError(f"no such month: {period!r}")
        ny, nm = (y + 1, 1) if mo == 12 else (y, mo + 1)
        return f"{y:04d}-{mo:02d}-01", f"{ny:04d}-{nm:02d}-01"
    if m := _QUARTER.match(period):
        y, q = int(m.group(1)), int(m.group(2))
        sm = 3 * q - 2
        ny, em = (y + 1, 1) if q == 4 else (y, sm + 3)
        return f"{y:04d}-{sm:02d}-01", f"{ny:04d}-{em:02d}-01"
    raise ValueError(f"unreadable period {period!r} — use YYYY, YYYY-MM, YYYY-Qn, or 'full'")


def period_range(conn, period: str, lane: str = "company") -> tuple[str, str] | None:
    """like parse_period, plus 'full' = the span of the LANE's books facts.

    'full' with no books facts in the lane returns None — there is no range
    to invent.
    """
    _check_lane(lane)
    if period != "full":
        return parse_period(period)
    try:
        row = conn.execute(
            "SELECT MIN(date) lo, MAX(date) hi FROM money_lines"
            f" WHERE kind = 'books' AND {lane_sql(lane)}").fetchone()
    except sqlite3.OperationalError:
        return None
    if row is None or row["lo"] is None:
        return None
    end = (date.fromisoformat(row["hi"]) + timedelta(days=1)).isoformat()
    return row["lo"], end


def _measure(conn, table: str, sums: dict[str, str], where: str, params: tuple,
             query: str, join: str = "", id_col: str = "id") -> dict:
    """count + sums + fact ids (when few) for the rows behind one cell.

    a table that does not exist yet measures as zero facts and says so in
    the query descriptor — it never raises, never invents.
    """
    sums_sql = ", ".join(f"COALESCE(SUM({expr}), 0) AS {name}" for name, expr in sums.items())
    tail = f"FROM {table} {join} WHERE {where}"
    try:
        row = conn.execute(f"SELECT COUNT(*) AS n, {sums_sql} {tail}", params).fetchone()
    except sqlite3.OperationalError:
        return {"table": table, "query": query + " (table not created)",
                "count": 0, "ids": None, "sums": dict.fromkeys(sums, 0)}
    n = row["n"]
    ids = None
    if 0 < n <= IDS_CAP:
        ids = [r[0] for r in conn.execute(f"SELECT {table}.{id_col} {tail} ORDER BY 1", params)]
    return {"table": table, "query": query, "count": n, "ids": ids,
            "sums": {k: row[k] for k in sums}}


def _prov(m: dict) -> dict:
    return {"table": m["table"], "query": m["query"], "count": m["count"], "ids": m["ids"]}


def assemble(conn, period: str, lane: str = "company") -> dict:
    """the period P&L for ONE lane: {period, lane, start, end, cells, gaps}.

    cells: name -> {name, value, unit, sources | derived_from [, formula]}.
    gaps: [{name, reason, table, query}] — a missing input is named, never
    rendered as a zero.

    lane="company" (default) reads only the fresh company's facts; today it
    renders empty but real. lane="learnings" reads only the old company's
    fta:/zoho: books history — reference, never company P&L. an unknown
    lane raises; merging lanes is not a lane (see overlay()).
    """
    _check_lane(lane)
    lane_pred = lane_sql(lane)
    rng = period_range(conn, period, lane)
    if rng is None:
        return {"period": period, "lane": lane, "start": None, "end": None, "cells": {},
                "gaps": [{"name": "books", "table": "money_lines",
                          "query": f"kind='books' AND {lane_pred}",
                          "reason": f"no {lane} books facts landed —"
                                    " the 'full' range is undefined"}]}
    start, end = rng
    cells: dict[str, dict] = {}
    gaps: list[dict] = []

    def cell(name: str, value: int, unit: str, sources: list | None = None,
             derived_from: list[str] | None = None, formula: str | None = None) -> None:
        c: dict = {"name": name, "value": value, "unit": unit}
        if sources:
            c["sources"] = sources
        if derived_from:
            c["derived_from"] = derived_from
        if formula:
            c["formula"] = formula
        cells[name] = c

    def gap(name: str, reason: str, table: str | None = None, query: str | None = None) -> None:
        gaps.append({"name": name, "reason": reason, "table": table, "query": query})

    # ---- books facts, lane-filtered by source prefix ----
    for name, account in (("books_sales", "sales"), ("books_purchases", "purchases")):
        q = (f"kind='books' AND account='{account}' AND date>='{start}'"
             f" AND date<'{end}' AND {lane_pred}")
        m = _measure(conn, "money_lines", {"total": "amount_minor"},
                     f"kind='books' AND account=? AND date>=? AND date<? AND {lane_pred}",
                     (account, start, end), q)
        if m["count"]:
            cell(name, m["sums"]["total"], "fils", sources=[_prov(m)])
        else:
            gap(name, f"no {lane} books facts (account='{account}') in [{start}, {end})",
                "money_lines", m["query"])

    if "books_sales" in cells and "books_purchases" in cells:
        sales_v = cells["books_sales"]["value"]
        spread = sales_v - cells["books_purchases"]["value"]
        cell("gross_spread", spread, "fils",
             derived_from=["books_sales", "books_purchases"],
             formula="books_sales - books_purchases")
        if sales_v > 0:
            bps = int((Decimal(spread) * 10_000 / Decimal(sales_v))
                      .quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            cell("gross_margin_bps", bps, "bps",
                 derived_from=["gross_spread", "books_sales"],
                 formula="gross_spread / books_sales, in basis points")
        else:
            gap("gross_margin_bps",
                f"books sales total is {sales_v} — margin undefined", "money_lines")
    else:
        gap("gross_spread", "needs both books_sales and books_purchases — one is a gap")

    # ---- purchase-order costs (SP1): the COGS side of the supplier form.
    # hand-entered POs land through the gate with operator: provenance; this
    # cell reads them so an approved entry becomes a number the P&L can cite.
    if lane == "company":
        po_q = (f"purchase_orders.created_at>='{start}' AND"
                f" purchase_orders.created_at<'{end}' AND"
                f" {lane_sql(lane, 'purchase_orders.source')}")
        pm = _measure(
            conn, "po_lines", {"total": "po_lines.qty * po_lines.unit_cost_minor"},
            f"purchase_orders.created_at>=? AND purchase_orders.created_at<?"
            f" AND {lane_sql(lane, 'purchase_orders.source')}",
            (start, end), po_q,
            join="JOIN purchase_orders ON po_lines.po_id = purchase_orders.id",
            id_col="id")
        if pm["count"]:
            cell("po_purchases", pm["sums"]["total"], "fils", sources=[_prov(pm)])
        else:
            gap("po_purchases",
                f"no purchase-order facts in [{start}, {end}) — the supplier "
                f"form lands them, each approved by hand",
                "po_lines", pm["query"])

    if lane == "learnings":
        # the learnings lane is the books history and nothing else — the old
        # company never landed operational facts here. no settlement, no
        # payouts, no ad spend: those belong to the company lane.
        return {"period": period, "lane": lane, "start": start, "end": end,
                "cells": cells, "gaps": gaps}

    # ---- company lane only, from here down ----

    # settlement aggregates (the spine landed the split per order line)
    try:
        orders_landed = conn.execute(
            f"SELECT COUNT(*) FROM orders WHERE {lane_pred}").fetchone()[0]
    except sqlite3.OperationalError:
        orders_landed = 0
    if orders_landed == 0:
        gap("settlement", "no orders landed yet — take, payable, unwinds have no facts",
            "orders", f"COUNT(*) = 0 WHERE {lane_pred}")
    else:
        o_pred = lane_sql(lane, "orders.source")
        r_pred = lane_sql(lane, "returns.source")
        ol = _measure(conn, "order_lines",
                      {"take": "order_lines.take_minor", "payable": "order_lines.payable_minor"},
                      "substr(orders.placed_at, 1, 10) >= ? AND substr(orders.placed_at, 1, 10) < ?"
                      f" AND {o_pred}",
                      (start, end), f"orders.placed_at date in [{start}, {end}) AND {o_pred}",
                      join="JOIN orders ON orders.shopify_id = order_lines.order_id")
        rl = _measure(conn, "return_lines",
                      {"amount": "return_lines.amount_minor",
                       "take_rev": "return_lines.take_reversed_minor",
                       "payable_rev": "return_lines.payable_reversed_minor"},
                      "substr(returns.refunded_at, 1, 10) >= ? AND substr(returns.refunded_at, 1, 10) < ?"
                      f" AND {r_pred}",
                      (start, end), f"returns.refunded_at date in [{start}, {end}) AND {r_pred}",
                      join="JOIN returns ON returns.shopify_id = return_lines.return_id")
        if ol["count"] == 0 and rl["count"] == 0:
            gap("settlement", f"no orders placed and no returns in [{start}, {end})",
                "order_lines", ol["query"])
        else:
            sources = [_prov(m) for m in (ol, rl) if m["count"]]
            cell("take_earned", ol["sums"]["take"] - rl["sums"]["take_rev"], "fils",
                 sources=sources,
                 formula="SUM(order_lines.take_minor) - SUM(return_lines.take_reversed_minor)")
            cell("payable_outstanding", ol["sums"]["payable"] - rl["sums"]["payable_rev"], "fils",
                 sources=sources,
                 formula="SUM(order_lines.payable_minor) - SUM(return_lines.payable_reversed_minor)")
            if rl["count"]:
                cell("unwinds", rl["sums"]["amount"], "fils", sources=[_prov(rl)])
            else:
                gap("unwinds", f"no return facts in [{start}, {end})",
                    "return_lines", rl["query"])

    # payout and fee lines (Shopify money lines, when they start landing)
    pq = f"kind='payout' AND date>='{start}' AND date<'{end}' AND {lane_pred}"
    pm = _measure(conn, "money_lines", {"total": "amount_minor"},
                  f"kind='payout' AND date>=? AND date<? AND {lane_pred}", (start, end), pq)
    if pm["count"]:
        cell("payouts", pm["sums"]["total"], "fils", sources=[_prov(pm)])
    else:
        gap("payouts", f"no payout lines in [{start}, {end}) — the new company's"
                       " Shopify payouts have not landed yet", "money_lines", pq)
    fq = (f"kind IN ('gateway_fee','platform_bill') AND date>='{start}'"
          f" AND date<'{end}' AND {lane_pred}")
    fm = _measure(conn, "money_lines", {"total": "amount_minor"},
                  f"kind IN ('gateway_fee','platform_bill') AND date>=? AND date<?"
                  f" AND {lane_pred}", (start, end), fq)
    if fm["count"]:
        cell("fees", fm["sums"]["total"], "fils", sources=[_prov(fm)])
    else:
        gap("fees", f"no gateway/platform fee lines in [{start}, {end}) — fee facts"
                    " have not landed yet", "money_lines", fq)

    # ---- ad spend ----
    aq = f"date>='{start}' AND date<'{end}' AND {lane_pred}"
    ads = _measure(conn, "ad_spend", {"spend": "spend_minor"},
                   f"date >= ? AND date < ? AND {lane_pred}", (start, end), aq)
    if ads["count"]:
        cell("ad_spend", ads["sums"]["spend"], "fils", sources=[_prov(ads)])
    else:
        gap("ad_spend", f"no ad-spend facts in [{start}, {end})", "ad_spend", aq)

    return {"period": period, "lane": lane, "start": start, "end": end,
            "cells": cells, "gaps": gaps}


def overlay(conn, period: str) -> dict:
    """the ONLY combined view — both lanes side by side, wearing the label.

    the learnings lane is never merged into company P&L; this returns the
    two assembled lanes intact under the 'learnings overlay' label, cells
    never summed across lanes. a consumer that shows both must show the label.
    """
    return {"label": OVERLAY_LABEL, "period": period,
            "company": assemble(conn, period, lane="company"),
            "learnings": assemble(conn, period, lane="learnings")}


def audit_provenance(pnl: dict) -> list[str]:
    """names of rendered cells that cannot cite facts — must come back empty.

    a cell is grounded when a source counts >= 1 fact, or when everything
    it derives from is grounded. the spec check: zero orphan numbers.
    """
    cells = pnl["cells"]

    def grounded(name: str, seen: tuple = ()) -> bool:
        c = cells.get(name)
        if c is None or name in seen:
            return False
        if any(s["count"] >= 1 for s in c.get("sources", [])):
            return True
        derived = c.get("derived_from")
        return bool(derived) and all(grounded(d, (*seen, name)) for d in derived)

    return [name for name in cells if not grounded(name)]
