"""the E3 gate, per lane (the fresh-start ruling, landed 2026-07-11).

    uv run python -m commerceos.economics.reconcile --period 2025 --tolerance-bps 50

--lane learnings (the default): engine proof against the old company's
books. opens the facts db READ-ONLY (mode=ro URI — a write attempt fails)
and compares, line by line:
- the period's learnings books sales vs the anchor in the instance config
  (learnings.anchors.fy<period>_sales_minor — the tax-authority-grade
  number the record landed for that period),
- the full-period gross spread (% of sales) vs
  learnings.anchors.full_period_spread_pct,
- and the round-trip selftest: a synthetic order + full return on a tmp db
  nets take and payable to exactly zero (spine settlement helpers).
passing proves the ENGINE computes right; it says nothing about the new
company's P&L, which starts at zero. the old numbers are reference and
lessons — they never enter company books.

--lane company: the new entity's books check. a stub today — exits 2 with
"no company books yet — first reconciliation lands with the new entity's
first period". honest, not passing.

writes reports/econ-reconcile-<lane>-<period>.md plus a .json sidecar (the
status row reads the sidecar — the facts db stays untouched). exit 0 =
every line within tolerance and the selftest nets to zero; 1 = out of
tolerance, a gap where a compared line should be, or a selftest failure;
2 = config or usage error, including the company-lane stub.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from commerceos import stores
from commerceos.db import connect, default_path
from commerceos.economics import engine
from commerceos.spine.schema import ensure_schema
from commerceos.spine.settlement import split, unwind

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = REPO_ROOT / "reports"


def default_config_path() -> Path:
    return stores.resolve(stores.active_store(), "economics.json")

LEARNINGS_PROOF = "learnings lane: engine proof against the old company's books"
COMPANY_STUB = ("no company books yet — first reconciliation lands with the"
                " new entity's first period")


class ConfigError(Exception):
    """the config cannot answer for this period — a usage error, not a delta."""


def connect_ro(path: Path | str) -> sqlite3.Connection:
    """the facts db, read-only. reconciliation reads; it never lands."""
    conn = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _sales_line(pnl: dict, period: str, anchors: dict, tolerance_bps: int) -> dict:
    key = f"fy{period}_sales_minor" if period.isdigit() else f"{period}_sales_minor"
    if key not in anchors:
        raise ConfigError(f"no sales anchor for period {period!r} —"
                          f" expected learnings.anchors.{key}")
    anchor = int(anchors[key])
    if anchor <= 0:
        raise ConfigError(f"learnings.anchors.{key} must be a positive minor-unit amount")
    label = f"{period} books sales"
    cell = pnl["cells"].get("books_sales")
    if cell is None:
        reason = next((g["reason"] for g in pnl["gaps"] if g["name"] == "books_sales"),
                      "books_sales is a gap")
        return {"line": label, "kind": "minor", "computed_minor": None,
                "anchor_minor": anchor, "delta_minor": None, "delta_bps": None,
                "ok": False, "note": reason, "provenance": None}
    computed = cell["value"]
    delta = computed - anchor
    delta_bps = abs(Decimal(delta) * 10_000 / Decimal(anchor))
    src = cell["sources"][0]
    return {"line": label, "kind": "minor", "computed_minor": computed,
            "anchor_minor": anchor, "delta_minor": delta,
            "delta_bps": float(round(delta_bps, 4)), "ok": delta_bps <= tolerance_bps,
            "provenance": f"{src['count']} {src['table']} rows — {src['query']}"}


def _spread_line(pnl_full: dict, anchors: dict, tolerance_bps: int) -> dict:
    if "full_period_spread_pct" not in anchors:
        raise ConfigError("no spread anchor — expected"
                          " learnings.anchors.full_period_spread_pct")
    anchor_pct = Decimal(str(anchors["full_period_spread_pct"]))
    label = f"full-period gross spread % ({pnl_full['start']} → {pnl_full['end']} excl.)"
    cells = pnl_full["cells"]
    if "gross_spread" not in cells or cells.get("books_sales", {}).get("value", 0) <= 0:
        return {"line": "full-period gross spread %", "kind": "pct", "computed_pct": None,
                "anchor_pct": float(anchor_pct), "delta_pp": None, "delta_bps": None,
                "ok": False, "note": "books facts missing — spread cannot be computed",
                "provenance": None}
    sales = cells["books_sales"]["value"]
    spread = cells["gross_spread"]["value"]
    computed_pct = Decimal(spread) * 100 / Decimal(sales)
    delta_pp = computed_pct - anchor_pct
    delta_bps = abs(delta_pp) * 100  # 1 bps = 0.01 percentage point
    s, p = cells["books_sales"]["sources"][0], cells["books_purchases"]["sources"][0]
    return {"line": label, "kind": "pct",
            "computed_pct": float(round(computed_pct, 4)), "anchor_pct": float(anchor_pct),
            "delta_pp": float(round(delta_pp, 4)), "delta_bps": float(round(delta_bps, 4)),
            "ok": delta_bps <= tolerance_bps,
            "provenance": (f"sales {s['count']} rows + purchases {p['count']} rows,"
                           f" money_lines books (learnings lane),"
                           f" [{pnl_full['start']}, {pnl_full['end']})")}


def selftest_roundtrip() -> dict:
    """spec check: a synthetic order + full return nets to exactly zero.

    lands a fixture order on a tmp db with the spine's own helpers (split,
    unwind, the real schema and CHECK constraints), then reads the result
    back through the engine's company-lane aggregates. nothing touches the
    real db.
    """
    net, bps = 61_500, 3_250  # an ordinary order value @ an ordinary take rate
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with tempfile.TemporaryDirectory(prefix="econ-selftest-") as td:
        conn = connect(Path(td) / "selftest.db")
        ensure_schema(conn)
        take, payable = split(net, bps)
        conn.execute(
            "INSERT INTO orders (shopify_id, number, placed_at, currency, gross_minor,"
            " net_minor, source, fetched_at) VALUES (?, ?, ?, 'AED', ?, ?, ?, ?)",
            ("selftest-1", "#ST1", "2026-01-10T12:00:00Z", net, net, "econ:selftest", now))
        cur = conn.execute(
            "INSERT INTO order_lines (order_id, vendor, qty, unit_price_minor, net_minor,"
            " take_rate_bps, take_minor, payable_minor, rate_source)"
            " VALUES ('selftest-1', 'selftest-vendor', 1, ?, ?, ?, ?, ?, 'selftest')",
            (net, net, bps, take, payable))
        line_id = cur.lastrowid
        take_rev, payable_rev = unwind(net, net, take)
        conn.execute(
            "INSERT INTO returns (shopify_id, order_id, refunded_at, amount_minor,"
            " source, fetched_at) VALUES (?, 'selftest-1', ?, ?, 'econ:selftest', ?)",
            ("selftest-ret-1", "2026-01-20T09:00:00Z", net, now))
        conn.execute(
            "INSERT INTO return_lines (return_id, order_line_id, qty, amount_minor,"
            " take_reversed_minor, payable_reversed_minor)"
            " VALUES ('selftest-ret-1', ?, 1, ?, ?, ?)",
            (line_id, net, take_rev, payable_rev))
        conn.commit()
        cells = engine.assemble(conn, "2026-01", lane="company")["cells"]
        conn.close()
    take_net = cells["take_earned"]["value"]
    payable_net = cells["payable_outstanding"]["value"]
    unwound = cells["unwinds"]["value"]
    ok = (take_net == 0 and payable_net == 0 and unwound == net
          and take + payable == net and (take_rev, payable_rev) == (take, payable))
    return {"line": "round-trip selftest (synthetic order + full return)", "kind": "selftest",
            "ok": ok, "take_net": take_net, "payable_net": payable_net,
            "detail": (f"order {net} fils @ {bps} bps -> take {take} + payable {payable};"
                       f" full return reverses {take_rev} + {payable_rev}; both sides net 0")}


def _fmt_aed(minor: int) -> str:
    return f"{Decimal(minor) / 100:,.2f}"


def write_report(result: dict, report_dir: Path | str) -> tuple[Path, Path]:
    """econ-reconcile-<lane>-<period>.md + .json — computed vs anchor vs delta."""
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = f"econ-reconcile-{result['lane']}-{result['period']}"
    md_path = report_dir / f"{stem}.md"
    json_path = report_dir / f"{stem}.json"
    json_path.write_text(json.dumps(result, indent=1) + "\n")

    st = result["selftest"]
    out = [f"# econ reconcile — {result['lane']} lane, period {result['period']}", ""]
    if result["lane"] == "learnings":
        out += [
            f"{LEARNINGS_PROOF}. the numbers below are the OLD company's —"
            " reference and lessons, never the new company's P&L. the company"
            " lane's first reconciliation lands with the new entity's first period.",
            "",
        ]
    out += [
        f"- run: {result['run_at']}",
        f"- db: {result['db']} (read-only)",
        f"- config: {result['config']}",
        f"- tolerance: {result['tolerance_bps']} bps per line",
        "",
        "| line | computed | anchor | delta | delta (bps) | verdict |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for ln in result["lines"]:
        verdict = "ok" if ln["ok"] else "OUT"
        if ln.get("computed_minor") is None and ln.get("computed_pct") is None:
            out.append(f"| {ln['line']} | — | — | — | — | {verdict}: {ln.get('note', '')} |")
        elif ln["kind"] == "minor":
            out.append(
                f"| {ln['line']} (AED) | {_fmt_aed(ln['computed_minor'])}"
                f" | {_fmt_aed(ln['anchor_minor'])} | {Decimal(ln['delta_minor']) / 100:+,.2f}"
                f" | {ln['delta_bps']:.4f} | {verdict} |")
        else:
            out.append(
                f"| {ln['line']} | {ln['computed_pct']:.4f}% | {ln['anchor_pct']:.4f}%"
                f" | {ln['delta_pp']:+.4f} pp | {ln['delta_bps']:.4f} | {verdict} |")
    out.append(
        f"| {st['line']} | take net {st['take_net']} · payable net {st['payable_net']}"
        f" | 0 · 0 | 0 | — | {'ok' if st['ok'] else 'FAIL'} |")
    out += ["", f"verdict: {'RECONCILED' if result['ok'] else 'NOT RECONCILED'}"
                f" ({result['lane']} lane) — exit {0 if result['ok'] else 1}", ""]

    out.append("## provenance")
    for ln in result["lines"]:
        if ln.get("provenance"):
            out.append(f"- {ln['line']}: {ln['provenance']}")
    out.append(f"- selftest: {st['detail']}")
    out.append("")

    if result.get("gaps"):
        out.append(f"## named gaps in period {result['period']},"
                   f" {result['lane']} lane (not defaults, not zeros)")
        for g in result["gaps"]:
            out.append(f"- {g['name']}: {g['reason']}")
        out.append("")

    md_path.write_text("\n".join(out))
    return md_path, json_path


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m commerceos.economics.reconcile",
        description="the E3 gate, per lane: learnings (default) proves the engine"
                    " against the old company's books; company is the new entity's"
                    " check, a stub until its first period. the exit code is the"
                    " verdict.")
    parser.add_argument("--lane", choices=("learnings", "company"), default="learnings",
                        help="learnings (default): engine proof against the old company's"
                             " books. company: the new entity's books check — exits 2"
                             " until its first period lands")
    parser.add_argument("--period", default="2025",
                        help="YYYY, YYYY-MM, or YYYY-Qn (default 2025, the learnings"
                             " gold period)")
    parser.add_argument("--tolerance-bps", type=int, default=None,
                        help="per-line tolerance in basis points (default: config, else 50)")
    parser.add_argument("--db", default=None, help="facts db path (default: the repo db)")
    parser.add_argument("--config", default=str(default_config_path()),
                        help="instance economics config (learnings anchors, company"
                             " block, tolerance)")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR),
                        help="where econ-reconcile-<lane>-<period>.md/.json land")
    args = parser.parse_args(argv)

    try:
        config = json.loads(Path(args.config).read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"unreadable config {args.config}: {e}", file=sys.stderr)
        return 2

    if args.lane == "company":
        # the company lane's future check — a stub that stays honest.
        company = config.get("company") or {}
        if company.get("books_source"):
            print("company books_source is configured but the company reconcile is"
                  " not built yet — build the check before trusting this lane",
                  file=sys.stderr)
        else:
            print(COMPANY_STUB, file=sys.stderr)
        return 2

    db_path = Path(args.db) if args.db else default_path()
    if not db_path.is_file():
        print(f"no facts db at {db_path}", file=sys.stderr)
        return 2
    tolerance = (args.tolerance_bps if args.tolerance_bps is not None
                 else int(config.get("tolerance_bps", 50)))
    anchors = (config.get("learnings") or {}).get("anchors") or {}

    conn = connect_ro(db_path)
    try:
        pnl = engine.assemble(conn, args.period, lane="learnings")
        pnl_full = engine.assemble(conn, "full", lane="learnings")
        lines = [_sales_line(pnl, args.period, anchors, tolerance),
                 _spread_line(pnl_full, anchors, tolerance)]
    except (ValueError, ConfigError) as e:
        print(str(e), file=sys.stderr)
        return 2
    finally:
        conn.close()

    st = selftest_roundtrip()
    ok = all(ln["ok"] for ln in lines) and st["ok"]
    result = {"period": args.period, "lane": "learnings", "meaning": LEARNINGS_PROOF,
              "run_at": _utcnow(), "db": str(db_path), "config": str(args.config),
              "tolerance_bps": tolerance, "ok": ok, "lines": lines, "selftest": st,
              "gaps": pnl["gaps"]}
    md_path, _ = write_report(result, args.report_dir)

    print(LEARNINGS_PROOF)
    for ln in lines:
        mark = "ok " if ln["ok"] else "OUT"
        if ln["kind"] == "minor" and ln["computed_minor"] is not None:
            print(f"{mark} {ln['line']}: computed {_fmt_aed(ln['computed_minor'])} vs"
                  f" anchor {_fmt_aed(ln['anchor_minor'])} AED"
                  f" (delta {ln['delta_minor']:+} fils, {ln['delta_bps']:.4f} bps)")
        elif ln["kind"] == "pct" and ln["computed_pct"] is not None:
            print(f"{mark} {ln['line']}: computed {ln['computed_pct']:.4f}% vs"
                  f" anchor {ln['anchor_pct']:.4f}% (delta {ln['delta_bps']:.4f} bps)")
        else:
            print(f"{mark} {ln['line']}: {ln.get('note', 'no computed value')}")
    print(f"{'ok ' if st['ok'] else 'FAIL'} round-trip selftest:"
          f" take net {st['take_net']} · payable net {st['payable_net']}")
    print(f"{'reconciled' if ok else 'NOT reconciled'} (learnings lane,"
          f" tolerance {tolerance} bps) · report: {md_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
