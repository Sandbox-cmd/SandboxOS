"""the analyst — the fleet's pattern-hunter over landed facts.

findings only, no store writes (.claude/agents/analyst.md): every claim
leaves this module through findings.mint, watching's one door, carrying
the fact rows it was computed from — no provenance, no finding. the
analyst never acts on what it finds; anything a finding suggests goes
to whoever it is routed to, and anything consequential goes through
the gate.

the analyst hunts PATTERNS the watch-list doesn't declare. declared
metrics already have the W1 statistical bands (engine.py) judging them
both directions; the six ruled hunts here (RULED 2026-07-18) look
across slices and joins no single metric row covers — category and
vendor sales shifts week-over-week, what sells together, AOV and
return-rate drift by category, and whether healthier listings sell
more. no statistics theater: each hunt is a plain SQL comparison with
an honest threshold, and thin data mints nothing — a hunt that cannot
support its claim reports not_enough_data and stays silent. a slump is
a risk and a surge is an opportunity by construction: only the sign of
the move picks the direction, one code path.

weeks run Monday to Sunday; "the week of <date>" names the Monday. the
latest week compared is the newest week any order landed in, against
the week immediately before it — no prior week, no week-over-week
claim.

run_hunts(conn, jcfg) runs the configured subset (jcfg["hunts"],
default all six) and returns a tally per hunt:
{found, minted, refreshed, skipped_no_evidence, not_enough_data}.
a repeated pattern refreshes its open finding instead of flooding
(watching behavior 7); a candidate naming no evidence is dropped and
counted, never minted.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from commerceos.watching import findings
from commerceos.watching.schema import ensure_schema

AGENT = "analyst"

# the week key: the Monday of the week the timestamp falls in.
_WEEK = "date({col}, 'weekday 0', '-6 days')"

# the joins that resolve an order line's category (products.product_type).
_CATEGORY_JOIN = (" JOIN variants v ON v.shopify_id = ol.variant_id"
                  " JOIN products p ON p.shopify_id = v.product_id")


# ---------- shared measurement ----------

def _latest_weeks(conn) -> tuple[str | None, str | None]:
    """(latest week with orders, the week before it) — or (None, None)."""
    week = _WEEK.format(col="o.placed_at")
    row = conn.execute(
        f"SELECT max({week}) w FROM orders o WHERE o.placed_at IS NOT NULL"
    ).fetchone()
    if not row or not row["w"]:
        return None, None
    prior = conn.execute("SELECT date(?, '-7 days') p", (row["w"],)).fetchone()["p"]
    return row["w"], prior


def _week_slices(conn, slice_expr: str, extra_join: str,
                 this_week: str, prior_week: str) -> dict:
    """{slice: {week: {net, orders, lines}}} over order_lines, two weeks.
    lines are the actual order_lines row refs the sums were computed from."""
    week = _WEEK.format(col="o.placed_at")
    sql = (f"SELECT {slice_expr} AS s, {week} AS week, SUM(ol.net_minor) AS net,"
           f" COUNT(DISTINCT ol.order_id) AS orders, group_concat(ol.id) AS line_ids"
           f" FROM order_lines ol JOIN orders o ON o.shopify_id = ol.order_id{extra_join}"
           f" WHERE {week} IN (?, ?) AND {slice_expr} IS NOT NULL AND {slice_expr} <> ''"
           f" GROUP BY s, week")
    out: dict = {}
    for r in conn.execute(sql, (this_week, prior_week)):
        out.setdefault(r["s"], {})[r["week"]] = {
            "net": r["net"] or 0, "orders": r["orders"],
            "lines": [f"order_lines:{i}" for i in str(r["line_ids"]).split(",")],
        }
    return out


def _aed(minor) -> str:
    v = (minor or 0) / 100
    return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:g}"


def _shift_over_weeks(conn, jcfg: dict, slice_expr: str, extra_join: str,
                      metric: str, slice_prefix: str, noun: str,
                      shift_pct: float, min_orders: int) -> dict:
    """the shared week-over-week net-sales comparison behind hunts 1 and 2.
    a slice must appear in both weeks; a claimable move on too few orders
    is counted not_enough_data, never minted."""
    this_week, prior_week = _latest_weeks(conn)
    if not this_week:
        return {"candidates": [], "not_enough_data": 1}
    slices = _week_slices(conn, slice_expr, extra_join, this_week, prior_week)
    candidates, thin = [], 0
    for key in sorted(slices):
        cur, prev = slices[key].get(this_week), slices[key].get(prior_week)
        if not cur or not prev or not prev["net"]:
            continue  # no baseline week -> no week-over-week claim
        pct = (cur["net"] - prev["net"]) / prev["net"] * 100
        if abs(pct) < shift_pct:
            continue
        if cur["orders"] < min_orders or prev["orders"] < min_orders:
            thin += 1  # the move is there, the data is too thin to claim it
            continue
        direction = "risk" if pct < 0 else "opportunity"
        candidates.append({
            "metric": metric, "slice": f"{slice_prefix}={key}", "direction": direction,
            "route": "owner",
            "sentence": (f"{noun} {key} net sales for the week of {this_week} are"
                         f" {_aed(cur['net'])} AED, {pct:+.0f}% vs {_aed(prev['net'])} AED"
                         f" the week before ({cur['orders']} vs {prev['orders']} orders)"),
            "evidence": {"evaluations": [], "facts": prev["lines"] + cur["lines"]},
        })
    return {"candidates": candidates, "not_enough_data": thin}


# ---------- the six ruled hunts ----------

def hunt_category_sales_shift(conn: sqlite3.Connection, jcfg: dict) -> dict:
    """1 — category net sales, latest week vs the week before. knobs:
    shift_pct (default 30 — the move, either direction, that makes a
    claim) · min_orders (default 5 — each week must carry at least this
    many orders in the category, or the move is not_enough_data)."""
    return _shift_over_weeks(
        conn, jcfg, "p.product_type", _CATEGORY_JOIN,
        "analyst.category_sales_shift", "category", "category",
        float(jcfg.get("shift_pct", 30)), int(jcfg.get("min_orders", 5)))


def hunt_vendor_sales_shift(conn: sqlite3.Connection, jcfg: dict) -> dict:
    """2 — vendor net sales, latest week vs the week before. same knobs
    as the category hunt: shift_pct (default 30) · min_orders (default 5)."""
    return _shift_over_weeks(
        conn, jcfg, "ol.vendor", "",
        "analyst.vendor_sales_shift", "vendor", "vendor",
        float(jcfg.get("shift_pct", 30)), int(jcfg.get("min_orders", 5)))


def hunt_basket_pairings(conn: sqlite3.Connection, jcfg: dict) -> dict:
    """3 — what sells together: pairs of products landing in the same
    order, over all landed orders. knobs: min_pair_orders (default 3 —
    a pair seen in fewer orders makes no claim) · max_pairs (default 3 —
    only the strongest pairs are reported, most orders first). routed to
    catalog: a cross-sell or collection could answer it."""
    min_pair = int(jcfg.get("min_pair_orders", 3))
    max_pairs = int(jcfg.get("max_pairs", 3))
    rows = conn.execute(
        "SELECT pa.shopify_id a_id, pa.title a_title, pb.shopify_id b_id,"
        " pb.title b_title, COUNT(DISTINCT la.order_id) n,"
        " group_concat(DISTINCT la.id) a_lines, group_concat(DISTINCT lb.id) b_lines"
        " FROM order_lines la JOIN order_lines lb ON la.order_id = lb.order_id"
        " JOIN variants va ON va.shopify_id = la.variant_id"
        " JOIN products pa ON pa.shopify_id = va.product_id"
        " JOIN variants vb ON vb.shopify_id = lb.variant_id"
        " JOIN products pb ON pb.shopify_id = vb.product_id"
        " WHERE pa.shopify_id < pb.shopify_id"
        " GROUP BY pa.shopify_id, pb.shopify_id"
        " ORDER BY n DESC, a_id, b_id",
    ).fetchall()
    if not rows:
        return {"candidates": [], "not_enough_data": 1}  # nothing sells together yet
    candidates = []
    for r in rows:
        if r["n"] < min_pair or len(candidates) >= max_pairs:
            continue
        lines = [f"order_lines:{i}"
                 for i in (str(r["a_lines"]) + "," + str(r["b_lines"])).split(",")]
        candidates.append({
            "metric": "analyst.basket_pairings",
            "slice": f"pair={r['a_id']}+{r['b_id']}",
            "direction": "insight", "route": "catalog",
            "sentence": (f"{r['a_title']} and {r['b_title']} sold together in"
                         f" {r['n']} orders — a pairing a cross-sell or a shared"
                         f" collection could use"),
            "evidence": {"evaluations": [], "facts": lines},
        })
    return {"candidates": candidates, "not_enough_data": 0}


def hunt_aov_drift(conn: sqlite3.Connection, jcfg: dict) -> dict:
    """4 — average order value by category, latest week vs the week
    before (category line net / orders touching the category). knobs:
    aov_drift_pct (default 20) · min_orders (default 5 per week per
    category, or the move is not_enough_data)."""
    drift_pct = float(jcfg.get("aov_drift_pct", 20))
    min_orders = int(jcfg.get("min_orders", 5))
    this_week, prior_week = _latest_weeks(conn)
    if not this_week:
        return {"candidates": [], "not_enough_data": 1}
    slices = _week_slices(conn, "p.product_type", _CATEGORY_JOIN, this_week, prior_week)
    candidates, thin = [], 0
    for key in sorted(slices):
        cur, prev = slices[key].get(this_week), slices[key].get(prior_week)
        if not cur or not prev or not prev["orders"] or not cur["orders"]:
            continue
        aov_cur = cur["net"] / cur["orders"]
        aov_prev = prev["net"] / prev["orders"]
        if not aov_prev:
            continue
        pct = (aov_cur - aov_prev) / aov_prev * 100
        if abs(pct) < drift_pct:
            continue
        if cur["orders"] < min_orders or prev["orders"] < min_orders:
            thin += 1
            continue
        direction = "risk" if pct < 0 else "opportunity"
        candidates.append({
            "metric": "analyst.aov_drift", "slice": f"category={key}",
            "direction": direction, "route": "owner",
            "sentence": (f"category {key} average order value for the week of"
                         f" {this_week} is {_aed(aov_cur)} AED, {pct:+.0f}% vs"
                         f" {_aed(aov_prev)} AED the week before"
                         f" ({cur['orders']} vs {prev['orders']} orders)"),
            "evidence": {"evaluations": [], "facts": prev["lines"] + cur["lines"]},
        })
    return {"candidates": candidates, "not_enough_data": thin}


def hunt_return_rate_drift(conn: sqlite3.Connection, jcfg: dict) -> dict:
    """5 — return rate by category: refunds landed in a week (by
    refunded_at) over that week's sales (by placed_at), latest week vs
    the week before. knobs: rate_delta_pp (default 5 — the move in
    percentage points that makes a claim) · min_orders (default 5 sales
    orders per week per category, or the move is not_enough_data)."""
    delta_pp = float(jcfg.get("rate_delta_pp", 5))
    min_orders = int(jcfg.get("min_orders", 5))
    this_week, prior_week = _latest_weeks(conn)
    if not this_week:
        return {"candidates": [], "not_enough_data": 1}
    sales = _week_slices(conn, "p.product_type", _CATEGORY_JOIN, this_week, prior_week)
    week = _WEEK.format(col="r.refunded_at")
    refunds: dict = {}
    for r in conn.execute(
        f"SELECT p.product_type AS s, {week} AS week, SUM(rl.amount_minor) AS refunded,"
        f" group_concat(rl.id) AS rl_ids"
        f" FROM return_lines rl JOIN returns r ON r.shopify_id = rl.return_id"
        f" JOIN order_lines ol ON ol.id = rl.order_line_id{_CATEGORY_JOIN}"
        f" WHERE {week} IN (?, ?) GROUP BY s, week",
        (this_week, prior_week),
    ):
        refunds.setdefault(r["s"], {})[r["week"]] = {
            "refunded": r["refunded"] or 0,
            "lines": [f"return_lines:{i}" for i in str(r["rl_ids"]).split(",")],
        }
    candidates, thin = [], 0
    for key in sorted(sales):
        cur, prev = sales[key].get(this_week), sales[key].get(prior_week)
        if not cur or not prev or not cur["net"] or not prev["net"]:
            continue
        ref_cur = refunds.get(key, {}).get(this_week, {"refunded": 0, "lines": []})
        ref_prev = refunds.get(key, {}).get(prior_week, {"refunded": 0, "lines": []})
        rate_cur = ref_cur["refunded"] / cur["net"] * 100
        rate_prev = ref_prev["refunded"] / prev["net"] * 100
        move = rate_cur - rate_prev
        if abs(move) < delta_pp:
            continue
        if cur["orders"] < min_orders or prev["orders"] < min_orders:
            thin += 1
            continue
        direction = "risk" if move > 0 else "opportunity"
        candidates.append({
            "metric": "analyst.return_rate_drift", "slice": f"category={key}",
            "direction": direction, "route": "owner",
            "sentence": (f"category {key} return rate for the week of {this_week} is"
                         f" {rate_cur:.0f}% of that week's sales, vs {rate_prev:.0f}%"
                         f" the week before — refunds landed in the week, against the"
                         f" week's own sales"),
            "evidence": {"evaluations": [],
                         "facts": prev["lines"] + cur["lines"]
                         + ref_prev["lines"] + ref_cur["lines"]},
        })
    return {"candidates": candidates, "not_enough_data": thin}


def hunt_catalog_health_vs_sales(conn: sqlite3.Connection, jcfg: dict) -> dict:
    """6 — do healthier listings sell more? three landed listing signals
    per product — media present, description at least min_description
    chars (default 200), an seo title — split products into healthier
    (healthy_min signals or more, default 2) and thinner groups; compare
    average units sold per product over all landed order lines. claims
    only when the signals actually landed AND both groups carry at least
    min_group products (default 10) — otherwise not_enough_data, nothing
    minted, never a provenance-free finding. knob gap_pct (default 30 —
    the gap between group averages that makes a claim). an insight both
    ways — a correlation over landed facts, not a cause — routed to
    catalog, where listing work could answer it."""
    min_desc = int(jcfg.get("min_description", 200))
    healthy_min = int(jcfg.get("healthy_min", 2))
    min_group = int(jcfg.get("min_group", 10))
    gap_pct = float(jcfg.get("gap_pct", 30))
    landed = conn.execute(
        "SELECT (SELECT count(*) FROM product_media) +"
        " (SELECT count(*) FROM products WHERE description_len IS NOT NULL) +"
        " (SELECT count(*) FROM products WHERE seo_title IS NOT NULL AND seo_title <> '')"
        " AS n"
    ).fetchone()["n"]
    if not landed:
        return {"candidates": [], "not_enough_data": 1}  # the widened sync never landed
    healthy, thin = [], []  # [(product_ref, units)]
    for r in conn.execute(
        "SELECT p.shopify_id pid,"
        " (CASE WHEN COALESCE(pm.media_count, 0) > 0 THEN 1 ELSE 0 END"
        "  + CASE WHEN COALESCE(p.description_len, 0) >= ? THEN 1 ELSE 0 END"
        "  + CASE WHEN p.seo_title IS NOT NULL AND p.seo_title <> '' THEN 1 ELSE 0 END)"
        " AS health, COALESCE(s.units, 0) AS units"
        " FROM products p"
        " LEFT JOIN product_media pm ON pm.product_id = p.shopify_id"
        " LEFT JOIN (SELECT v.product_id pid2, SUM(ol.qty) units FROM order_lines ol"
        "            JOIN variants v ON v.shopify_id = ol.variant_id"
        "            GROUP BY v.product_id) s ON s.pid2 = p.shopify_id",
        (min_desc,),
    ):
        (healthy if r["health"] >= healthy_min else thin).append(
            (f"products:{r['pid']}", r["units"]))
    if len(healthy) < min_group or len(thin) < min_group:
        return {"candidates": [], "not_enough_data": 1}
    avg_h = sum(u for _, u in healthy) / len(healthy)
    avg_t = sum(u for _, u in thin) / len(thin)
    hi, lo = max(avg_h, avg_t), min(avg_h, avg_t)
    if hi == 0 or (lo > 0 and (hi - lo) / lo * 100 < gap_pct):
        return {"candidates": [], "not_enough_data": 0}  # honest: no pattern
    lead = "healthier" if avg_h > avg_t else "thinner"
    sentence = (f"products with {lead} listings sold more: healthier listings"
                f" ({healthy_min}+ of media, description, seo title;"
                f" {len(healthy)} products) average {avg_h:.1f} units sold each,"
                f" thinner listings ({len(thin)} products) average {avg_t:.1f} —"
                f" a correlation over landed facts, not a cause")
    return {"candidates": [{
        "metric": "analyst.catalog_health_vs_sales", "slice": "",
        "direction": "insight", "route": "catalog", "sentence": sentence,
        "evidence": {"evaluations": [],
                     "facts": [ref for ref, _ in healthy] + [ref for ref, _ in thin]},
    }], "not_enough_data": 0}


# the pluggable registry: adding a hunt is an entry here, run by name.
HUNTS = {
    "category_sales_shift": hunt_category_sales_shift,
    "vendor_sales_shift": hunt_vendor_sales_shift,
    "basket_pairings": hunt_basket_pairings,
    "aov_drift": hunt_aov_drift,
    "return_rate_drift": hunt_return_rate_drift,
    "catalog_health_vs_sales": hunt_catalog_health_vs_sales,
}


# ---------- the run: every candidate through the one door ----------

def run_hunts(conn: sqlite3.Connection, jcfg: dict | None = None,
              now: datetime | None = None) -> dict:
    """run the configured hunts (jcfg["hunts"], default all six) and mint
    every evidenced candidate through findings.mint — the only door. a
    candidate naming no evidence is dropped and counted, never minted; a
    pattern already open as a finding is refreshed, not flooded (watching
    behavior 7). returns {hunt: {found, minted, refreshed,
    skipped_no_evidence, not_enough_data}}."""
    jcfg = jcfg or {}
    ensure_schema(conn)
    names = list(jcfg.get("hunts") or HUNTS)
    unknown = [n for n in names if n not in HUNTS]
    if unknown:
        raise ValueError(f"unknown hunt(s) {unknown} — this analyst runs {list(HUNTS)}")
    tally: dict = {}
    for name in names:
        out = HUNTS[name](conn, jcfg)
        t = {"found": len(out["candidates"]), "minted": 0, "refreshed": 0,
             "skipped_no_evidence": 0,
             "not_enough_data": out.get("not_enough_data", 0)}
        for cand in out["candidates"]:
            evidence = cand.get("evidence") or {}
            if not (evidence.get("evaluations") or evidence.get("facts")):
                t["skipped_no_evidence"] += 1  # the mint law, honored before the door
                continue
            open_row = findings.open_finding_for(
                conn, cand["metric"], cand["slice"], cand["direction"])
            if open_row:
                findings.refresh(conn, open_row["id"], evidence,
                                 sentence=cand["sentence"], now=now)
                t["refreshed"] += 1
            else:
                findings.mint(conn, cand["sentence"], cand["direction"], evidence,
                              route=cand.get("route", "owner"), metric=cand["metric"],
                              slice_=cand["slice"], now=now)
                t["minted"] += 1
        tally[name] = t
    return tally
