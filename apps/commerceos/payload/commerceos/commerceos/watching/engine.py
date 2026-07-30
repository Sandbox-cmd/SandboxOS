"""the watching engine — one evaluator, pointed both directions.

mechanism only (spec/parts/watching.md): the engine ships with zero
built-in metrics. every number it watches is a watch-list row (the
store's config file); every number a finding cites traces to landed
facts through an evaluation row. baselines form from prior evaluations
of actuals or read "forming" (NULL) — no invented defaults, ever. the
anti-pattern this is built against: the old simulator that hardcoded a
fictional store's numbers and never read actuals.

a metric row is a dict:

    name        the metric's name — also the findings dedup key
    formula     {op: sum|avg|count, table, column, date, where?, period,
                 freshness?} — or op: ratio with numerator/denominator
                 sides ({table, column, date, where?}), ratio of sums.
                 period: month|day. freshness: facts tables whose
                 max(fetched_at) must be younger than the cadence.
    dimensions  facts columns to slice by (e.g. ["vendor"]); [] = whole store
    cadence     hourly|daily|weekly|monthly — the staleness horizon
    baseline    {method: rolling|seasonal, window, curve?} over PRIOR
                evaluations only; seasonal deseasonalizes each prior value
                by its month's curve factor, then re-applies the current
                month's — a July trough is not a false alarm.
    bands       [{edge, side: above|below, direction}] — each edge names
                its own finding direction. bands fire even while forming.
    drift_pct   the warm-up drift line: |value - baseline| / baseline
                beyond this fires a finding while the metric's own history
                is still thin. once prior evaluations reach N for the
                row's period grain (DRIFT_WARMUP_N; overridable via the
                watch-list's top-level "drift_warmup_n"), the statistical
                band takes over — RULED 2026-07-18: mean ± band_k standard
                deviations over the metric's OWN prior evaluations. the
                same math both directions, one code path — a slump is
                a risk, a surge an opportunity (drift_up_direction can
                say insight instead). every evaluation records which mode
                governed it (drift_mode), and the self-report shows it
                per row.
    band_k      how many standard deviations wide the statistical band
                is (default 2.0)
    route       who the finding is suggested to (default: the owner)

the watch-list is owner-authored instance config, trusted the way
stores/<store>/policy-table.json is: formula fragments are interpolated
into read-only SELECTs over the facts tables. the watching writes no
facts — its own tables live in schema.py (table-set "watching").
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from commerceos import stores
from commerceos.watching import findings
from commerceos.watching.schema import ensure_schema
from commerceos.watching.status import report_status

CADENCE_SECONDS = {"hourly": 3600, "daily": 86400, "weekly": 604800, "monthly": 2678400}
_PERIOD_CHARS = {"month": 7, "day": 10}  # substr length of an ISO date

# how much history suffices, per period grain (the 2026-07-18 ruling: N is
# defined per grain). the week entry waits for a week grain to exist —
# today the engine speaks month|day only. overridable via the watch-list's
# top-level "drift_warmup_n".
DRIFT_WARMUP_N = {"day": 14, "week": 8, "month": 6}
DEFAULT_BAND_K = 2.0  # band width in standard deviations; per-row "band_k"


def load_watch_list(path: Path | str | None = None) -> dict:
    return json.loads(
        Path(path or stores.resolve(stores.active_store(), "watch-list.json")).read_text()
    )


def evaluate(conn: sqlite3.Connection, watch_list: dict, now: datetime | None = None) -> dict:
    """One pass: every metric row, every dimension slice, every period the
    facts cover — evaluations written (refreshed in place per period),
    findings minted or refreshed from the latest period, open findings
    aged. Returns a summary dict; ends by filling the part's own registry
    row. An empty watch-list evaluates nothing and says so."""
    now = now or datetime.now(timezone.utc)
    ensure_schema(conn)
    summary = {
        "metrics": 0, "evaluations": 0, "stale": [], "no_data": [],
        "findings_minted": 0, "findings_refreshed": 0, "aged_out": 0,
    }
    curves = watch_list.get("curves", {})
    warmup_n = {**DRIFT_WARMUP_N, **(watch_list.get("drift_warmup_n") or {})}
    for row in watch_list.get("metrics", []):
        summary["metrics"] += 1
        _evaluate_row(conn, row, curves, warmup_n, now, summary)
    summary["aged_out"] = findings.age_out(conn, watch_list.get("age_out_days"), now=now)
    conn.commit()
    report_status(conn, watch_list)
    return summary


# ---------- one metric row ----------

def _evaluate_row(conn, row: dict, curves: dict, warmup_n: dict, now: datetime, summary: dict) -> None:
    name = row["name"]
    formula = row["formula"]
    period_kind = formula.get("period", "month")
    if period_kind not in _PERIOD_CHARS:
        raise ValueError(f"{name}: unknown period {period_kind!r} (month|day)")
    cadence = row.get("cadence", "daily")
    if cadence not in CADENCE_SECONDS:
        raise ValueError(f"{name}: unknown cadence {cadence!r} ({'|'.join(CADENCE_SECONDS)})")
    dims = row.get("dimensions") or []
    ts = now.isoformat(timespec="seconds")

    # stale facts -> the evaluation says stale; no number is pretended.
    if _facts_stale(conn, formula.get("freshness", []), CADENCE_SECONDS[cadence], now):
        _upsert(conn, name, "", _period_of(now, period_kind),
                None, None, None, {"rows": 0, "stale_facts": True}, 1, ts)
        summary["evaluations"] += 1
        summary["stale"].append(name)
        return

    data, tables = _measure(conn, name, formula, dims, period_kind)
    if not data:
        # fresh facts, zero matching rows: no-data, honestly — never invented.
        _upsert(conn, name, "", _period_of(now, period_kind),
                None, None, None, {"rows": 0, "tables": tables}, 0, ts)
        summary["evaluations"] += 1
        summary["no_data"].append(name)
        return

    by_period: dict[str, dict] = {}
    for (period, slice_), measured in data.items():
        by_period.setdefault(period, {})[slice_] = measured
    # a whole-store sum/count month with zero rows is honestly zero, not a gap
    if not dims and formula.get("op") in ("sum", "count"):
        for period in _fill_periods(min(by_period), max(by_period), period_kind):
            by_period.setdefault(period, {"": (0, 0)})

    periods = sorted(by_period)
    latest = periods[-1]
    for period in periods:  # chronological: each evaluation is the next one's prior
        for slice_, (value, nrows) in sorted(by_period[period].items()):
            baseline = _baseline(conn, name, slice_, period, row.get("baseline") or {}, curves)
            drift_band = _drift_band(conn, name, slice_, period, row, warmup_n, period_kind)
            delta = None
            if value is not None and baseline is not None and baseline != 0:
                delta = (value - baseline) / baseline
            window = {"period": period, "rows": nrows, "tables": tables}
            eval_id = _upsert(conn, name, slice_, period, value, baseline, delta, window, 0, ts,
                              drift_mode=None if value is None else drift_band["mode"])
            summary["evaluations"] += 1
            if period == latest:  # the watching notices now, not history
                _notice(conn, row, slice_, period, value, baseline, delta, eval_id, window, drift_band, now, summary)


# ---------- measurement ----------

def _measure(conn, name: str, formula: dict, dims: list, period_kind: str):
    """-> ({(period, slice): (value, rows)}, [facts tables read])."""
    op = formula.get("op")
    if op in ("sum", "avg", "count"):
        return _aggregate(conn, formula, op, dims, period_kind), [formula["table"]]
    if op == "ratio":  # ratio of sums, both sides sliced the same way
        num = _aggregate(conn, formula["numerator"], "sum", dims, period_kind)
        den = _aggregate(conn, formula["denominator"], "sum", dims, period_kind)
        data = {}
        for key in set(num) | set(den):
            n, n_rows = num.get(key, (0, 0))
            d, d_rows = den.get(key, (None, 0))
            value = None if not d else (n or 0) / d  # no denominator -> no number
            data[key] = (value, n_rows + d_rows)
        return data, [formula["numerator"]["table"], formula["denominator"]["table"]]
    raise ValueError(f"{name}: unknown formula op {op!r} (sum|avg|count|ratio)")


def _aggregate(conn, side: dict, op: str, dims: list, period_kind: str) -> dict:
    column = side.get("column", "*")
    agg = {
        "sum": f"SUM({column})",
        "avg": f"AVG({column})",
        "count": "COUNT(*)" if column == "*" else f"COUNT({column})",
    }[op]
    period_expr = f"substr({side['date']}, 1, {_PERIOD_CHARS[period_kind]})"
    dim_select = "".join(f", {d} AS d{i}" for i, d in enumerate(dims))
    dim_group = "".join(f", d{i}" for i in range(len(dims)))
    where = f" WHERE {side['where']}" if side.get("where") else ""
    sql = (f"SELECT {period_expr} AS period{dim_select}, {agg} AS v, COUNT(*) AS n"
           f" FROM {side['table']}{where} GROUP BY {period_expr}{dim_group}")
    out = {}
    for r in conn.execute(sql):
        slice_ = "·".join(
            f"{d.split('.')[-1]}={r[f'd{i}']}" for i, d in enumerate(dims))
        out[(r["period"], slice_)] = (r["v"], r["n"])
    return out


def _facts_stale(conn, tables: list, horizon_seconds: int, now: datetime) -> bool:
    """Facts older than the row's cadence — or never landed — are stale."""
    for table in tables:
        newest = conn.execute(f"SELECT max(fetched_at) m FROM {table}").fetchone()["m"]
        if not newest:
            return True
        fetched = datetime.fromisoformat(newest.replace("Z", "+00:00"))
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        if (now - fetched).total_seconds() > horizon_seconds:
            return True
    return False


# ---------- baselines: from PRIOR evaluations only ----------

def _baseline(conn, metric: str, slice_: str, period: str, cfg: dict, curves: dict):
    method = cfg.get("method")
    if not method:
        return None  # no baseline configured: forming forever, bands only
    window = int(cfg.get("window", 0))
    if window < 1:
        raise ValueError(f"{metric}: baseline window must be >= 1")
    prior = conn.execute(
        "SELECT period, value FROM evaluations WHERE metric = ? AND slice = ?"
        " AND period < ? AND stale = 0 AND value IS NOT NULL"
        " ORDER BY period DESC LIMIT ?",
        (metric, slice_, period, window),
    ).fetchall()
    if len(prior) < window:
        return None  # forming — the window fills from actuals, or it isn't a baseline
    if method == "rolling":
        return sum(r["value"] for r in prior) / window
    if method == "seasonal":
        curve = curves.get(cfg.get("curve") or "")
        if not curve:
            raise ValueError(
                f"{metric}: seasonal baseline names curve {cfg.get('curve')!r},"
                " which the watch-list does not define")
        deseasonalized = [r["value"] / _factor(curve, r["period"]) for r in prior]
        return (sum(deseasonalized) / window) * _factor(curve, period)
    raise ValueError(f"{metric}: unknown baseline method {method!r} (rolling|seasonal)")


def _factor(curve: dict, period: str) -> float:
    month = str(int(period[5:7]))
    if month not in curve:
        raise ValueError(f"the seasonal curve has no factor for month {month}")
    factor = float(curve[month])
    if factor <= 0:
        raise ValueError(f"seasonal factor for month {month} must be positive")
    return factor


# ---------- drift bands: from the metric's OWN prior evaluations ----------

def _drift_band(conn, metric: str, slice_: str, period: str, row: dict,
                warmup_n: dict, period_kind: str) -> dict:
    """RULED 2026-07-18: the drift threshold is a statistical band per
    metric — mean ± band_k standard deviations over ALL of that metric's
    own prior evaluations (this slice, earlier periods, real numbers
    only). until the history reaches N for the row's period grain, the
    plain-percentage drift_pct carries the warm-up, and the mode says so
    in plain words."""
    needed = int(warmup_n.get(period_kind, DRIFT_WARMUP_N[period_kind]))
    prior = conn.execute(
        "SELECT id, value FROM evaluations WHERE metric = ? AND slice = ?"
        " AND period < ? AND stale = 0 AND value IS NOT NULL ORDER BY period",
        (metric, slice_, period),
    ).fetchall()
    if len(prior) < needed:
        return {"mode": f"warming up ({len(prior)} of {needed})", "banded": False}
    k = float(row.get("band_k", DEFAULT_BAND_K))
    if k <= 0:
        raise ValueError(f"{metric}: band_k must be positive")
    values = [r["value"] for r in prior]
    mean = sum(values) / len(values)
    sd = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
    return {"mode": "banded", "banded": True, "mean": mean, "sd": sd, "k": k,
            "low": mean - k * sd, "high": mean + k * sd,
            "history_ids": [r["id"] for r in prior]}


# ---------- noticing: bands + drift, both directions, one code path ----------

def _plain_label(name: str, slice_: str) -> str:
    """the watched number in plain words for a finding's sentence — the same
    shape the findings surface renders ('vendor return rate · vendor Acme'),
    so a raw metric key or key=value slice is never minted into a sentence."""
    label = name.replace("-", " ").replace("_", " ")
    if slice_ and not slice_.startswith("pair="):
        bits = []
        for tok in slice_.split("·"):
            key, _, val = tok.partition("=")
            bits.append(f"{key.replace('_', ' ')} {val}".strip())
        sliced = " · ".join(b for b in bits if b)
        if sliced:
            label = f"{label} · {sliced}"
    return label


def _notice(conn, row, slice_, period, value, baseline, delta, eval_id, window, drift_band, now, summary):
    if value is None:
        return  # no number, nothing to claim
    name = row["name"]
    label = _plain_label(name, slice_)
    evidence = {
        "evaluations": [eval_id],
        "facts": [f"{t}@{period} rows={window['rows']}" for t in window["tables"]],
    }

    for band in row.get("bands") or []:
        side, edge, direction = band.get("side"), band["edge"], band["direction"]
        if side not in ("above", "below"):
            raise ValueError(f"{name}: band side must be above|below, not {side!r}")
        if direction not in findings.DIRECTIONS:
            raise ValueError(f"{name}: band direction must be one of {findings.DIRECTIONS}")
        if (value > edge) if side == "above" else (value < edge):
            sentence = f"{label} at {_fmt(value)} is {side} the {_fmt(edge)} edge for {period}"
            _mint_or_refresh(conn, row, slice_, direction, sentence, evidence, now, summary)

    if drift_band["banded"]:
        # history suffices: the metric's own band judges it, both directions
        low, high = drift_band["low"], drift_band["high"]
        if value < low or value > high:
            direction = "risk" if value < low else row.get("drift_up_direction", "opportunity")
            if direction not in findings.DIRECTIONS:
                raise ValueError(f"{name}: drift_up_direction must be one of {findings.DIRECTIONS}")
            sentence = (f"{label} at {_fmt(value)} for {period} is outside its usual"
                        f" range {_fmt(low)} to {_fmt(high)}, learned from"
                        f" {len(drift_band['history_ids'])} past readings")
            band_evidence = {**evidence,
                             "evaluations": [eval_id, *drift_band["history_ids"]]}
            _mint_or_refresh(conn, row, slice_, direction, sentence, band_evidence, now, summary)
        return

    # warming up: the plain-percentage line carries it until history suffices
    drift_pct = row.get("drift_pct")
    if drift_pct and delta is not None and abs(delta) >= drift_pct / 100.0:
        # one code path, both directions: only the sign picks the direction
        direction = "risk" if delta < 0 else row.get("drift_up_direction", "opportunity")
        if direction not in findings.DIRECTIONS:
            raise ValueError(f"{name}: drift_up_direction must be one of {findings.DIRECTIONS}")
        sentence = (f"{label} at {_fmt(value)} for {period} is {delta:+.0%}"
                    f" vs baseline {_fmt(baseline)} — past the {drift_pct:g}% drift line")
        _mint_or_refresh(conn, row, slice_, direction, sentence, evidence, now, summary)


def _mint_or_refresh(conn, row, slice_, direction, sentence, evidence, now, summary):
    """behavior 7: a persisting breach refreshes the open finding, never floods."""
    open_row = findings.open_finding_for(conn, row["name"], slice_, direction)
    if open_row:
        findings.refresh(conn, open_row["id"], evidence, sentence=sentence, now=now)
        summary["findings_refreshed"] += 1
    else:
        findings.mint(conn, sentence, direction, evidence, route=row.get("route", "owner"),
                      metric=row["name"], slice_=slice_, now=now)
        summary["findings_minted"] += 1


# ---------- small helpers ----------

def _upsert(conn, metric, slice_, period, value, baseline, delta, window, stale, ts,
            drift_mode=None) -> int:
    conn.execute(
        "INSERT INTO evaluations (metric, slice, period, value, baseline, delta,"
        " facts_window, stale, ts, drift_mode) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(metric, slice, period) DO UPDATE SET value=excluded.value,"
        " baseline=excluded.baseline, delta=excluded.delta,"
        " facts_window=excluded.facts_window, stale=excluded.stale, ts=excluded.ts,"
        " drift_mode=excluded.drift_mode",
        (metric, slice_, period, value, baseline, delta, json.dumps(window), stale, ts,
         drift_mode),
    )
    return conn.execute(
        "SELECT id FROM evaluations WHERE metric = ? AND slice = ? AND period = ?",
        (metric, slice_, period),
    ).fetchone()["id"]


def _period_of(now: datetime, kind: str) -> str:
    return now.strftime("%Y-%m" if kind == "month" else "%Y-%m-%d")


def _fill_periods(first: str, last: str, kind: str) -> list[str]:
    if kind == "day":
        start, end = date.fromisoformat(first), date.fromisoformat(last)
        return [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
    year, month = int(first[:4]), int(first[5:7])
    out = []
    while True:
        period = f"{year:04d}-{month:02d}"
        out.append(period)
        if period >= last:
            return out
        month += 1
        if month == 13:
            month, year = 1, year + 1


def _fmt(value) -> str:
    if value is None:
        return "—"
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:g}"
