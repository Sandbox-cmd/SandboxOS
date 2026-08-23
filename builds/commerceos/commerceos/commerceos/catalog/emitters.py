"""per-channel emitters — C2's consistency, built in (spec/parts/catalog-loop.md).

three renderers — the store page's spec block (html fragment), a Google
Merchant feed entry (dict), a schema.org/Product JSON-LD (dict) — and
every one of them reads ONLY the canonical record (canonical.py's
table-set), never raw facts. one function (claim_set) extracts the claims
once; the renderers only format what it returns, so the same value
reaches every surface by construction — and the check below re-parses
the rendered outputs to prove it held.

the honesty rule, stated once and enforced on every surface:
  MACHINE SURFACES CARRY VERIFIED TRUTH ONLY. an unverified claim renders
  as "not yet verified" on the page — a human surface may show the gap,
  never the bare value — and is EXCLUDED from the feed's gtin and
  product_detail and from JSON-LD's gtin13 and additionalProperty. a
  guessed number that reaches Google or a crawler is an invented answer;
  silence over guesses (C2).

the part's ratified check, runnable:

  uv run python -m commerceos.catalog.emitters check --sample 50

rebuilds the canonical record from landed facts (through the write guard:
only the canonical tables are writable on that connection — the facts
stay untouched mechanically), emits page, feed, and JSON-LD for the N
products with the most spec claims, re-parses the rendered outputs, and
asserts per claim: identical values on every surface that carries it,
unverified claims marked on the page and absent from the machine
surfaces, fit-critical marks in place. writes
reports/emit-consistency-<date>.md (pass/fail per product + totals).
"""

from __future__ import annotations

import argparse
import html
import json
import sqlite3
import time
from html.parser import HTMLParser
from pathlib import Path

from commerceos.catalog.canonical import REPO, build_canonical, connect_guarded, default_db

DEFAULT_OUT = REPO / "reports"

NOT_YET_VERIFIED = "not yet verified"
FC_MARK = "fit-critical"
GTIN_FIELDS = ("gtin", "gtin13")


# ---------------------------------------------------------------- shared core

def claim_set(conn: sqlite3.Connection, product: str) -> dict:
    """the one extraction all three renderers format. identity + ordered
    claims for one product, from the canonical record and nowhere else."""
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row
    p = cur.execute(
        "SELECT shopify_id, handle, title, vendor, category"
        " FROM canonical_products WHERE shopify_id = ?", (product,)
    ).fetchone()
    if p is None:
        raise LookupError(f"no canonical record for {product!r} — run build_canonical first")
    claims = [dict(r) for r in cur.execute(
        "SELECT field, value, unit, source, verified, verified_on, fit_critical"
        " FROM spec_claims WHERE product = ? ORDER BY field", (product,))]
    return {"identity": dict(p), "claims": claims}


def label(field: str) -> str:
    """the one field->display-name mapping every surface uses."""
    return field.replace("_", " ")


def display_value(claim: dict) -> str:
    """the one value+unit rendering every surface uses."""
    return f'{claim["value"]} {claim["unit"]}' if claim["unit"] else claim["value"]


def verified_gtin(claims: list[dict]) -> str | None:
    """the gtin the machine surfaces may carry: a VERIFIED gtin claim only."""
    for c in claims:
        if c["field"] in GTIN_FIELDS and c["verified"]:
            return c["value"]
    return None


# ------------------------------------------------------------- the renderers

def emit_page(conn: sqlite3.Connection, product: str) -> str:
    """the spec block as an html fragment (dl/dt/dd). fit-critical claims
    carry a visible mark; an unverified claim renders "not yet verified" —
    the gap is shown, the unvouched value is not, never a bare value."""
    cs = claim_set(conn, product)
    e = html.escape
    L = [f'<dl class="spec-claims" data-product="{e(cs["identity"]["shopify_id"])}">']
    for c in cs["claims"]:
        fc_attr = ' class="fit-critical"' if c["fit_critical"] else ""
        mark = f' <span class="fc-mark">{FC_MARK}</span>' if c["fit_critical"] else ""
        L.append(f'  <dt data-field="{e(c["field"])}"{fc_attr}>{e(label(c["field"]))}{mark}</dt>')
        if c["verified"]:
            unit_attr = f' data-unit="{e(c["unit"])}"' if c["unit"] else ""
            L.append(
                f'  <dd data-field="{e(c["field"])}" data-verified="1"'
                f' data-value="{e(c["value"])}"{unit_attr}>{e(display_value(c))}</dd>')
        else:
            L.append(
                f'  <dd data-field="{e(c["field"])}" data-verified="0"'
                f' class="not-yet-verified">{NOT_YET_VERIFIED}</dd>')
    L.append("</dl>")
    return "\n".join(L)


def emit_feed(conn: sqlite3.Connection, product: str) -> dict:
    """a Google Merchant-shaped entry. product_detail carries one entry per
    VERIFIED spec claim (section_name/attribute_name/attribute_value per
    Google's product_detail shape); gtin only when a verified gtin claim
    exists. machine surfaces carry verified truth only."""
    cs = claim_set(conn, product)
    ident = cs["identity"]
    verified = [c for c in cs["claims"] if c["verified"]]
    entry = {
        "id": ident["shopify_id"],
        "title": ident["title"],
        "brand": ident["vendor"],
        "product_detail": [
            {
                "section_name": ident["category"] or "Specifications",
                "attribute_name": label(c["field"]),
                "attribute_value": display_value(c),
            }
            for c in verified
        ],
    }
    g = verified_gtin(verified)
    if g:
        entry["gtin"] = g
    return entry


def emit_jsonld(conn: sqlite3.Connection, product: str) -> dict:
    """a schema.org/Product dict. additionalProperty carries one
    PropertyValue per VERIFIED spec claim; gtin13 only when a verified
    13-digit gtin claim exists. machine surfaces carry verified truth only."""
    cs = claim_set(conn, product)
    ident = cs["identity"]
    verified = [c for c in cs["claims"] if c["verified"]]
    props = []
    for c in verified:
        pv = {"@type": "PropertyValue", "name": label(c["field"]), "value": c["value"]}
        if c["unit"]:
            pv["unitText"] = c["unit"]
        props.append(pv)
    ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": ident["title"],
        "brand": {"@type": "Brand", "name": ident["vendor"]},
        "productID": ident["shopify_id"],
        "additionalProperty": props,
    }
    g = verified_gtin(verified)
    if g and g.isdigit() and len(g) == 13:
        ld["gtin13"] = g
    return ld


# ------------------------------------------------- the consistency check (C2)

class _PageParser(HTMLParser):
    """read the page fragment back the way a checker must: from the
    rendered output, not from the code that wrote it."""

    def __init__(self):
        super().__init__()
        self.product: str | None = None
        self.rows: dict[str, dict] = {}   # field -> dd record
        self.fc_fields: set[str] = set()
        self._dd: dict | None = None
        self._dt_field: str | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "dl":
            self.product = a.get("data-product")
        elif tag == "dt":
            self._dt_field = a.get("data-field")
        elif tag == "span" and "fc-mark" in (a.get("class") or "") and self._dt_field:
            self.fc_fields.add(self._dt_field)
        elif tag == "dd":
            self._dd = {"field": a.get("data-field"), "verified": a.get("data-verified"),
                        "value": a.get("data-value"), "unit": a.get("data-unit"), "text": ""}

    def handle_data(self, data):
        if self._dd is not None:
            self._dd["text"] += data

    def handle_endtag(self, tag):
        if tag == "dd" and self._dd is not None:
            self._dd["text"] = " ".join(self._dd["text"].split())
            self.rows[self._dd["field"]] = self._dd
            self._dd = None
        elif tag == "dt":
            self._dt_field = None


def parse_page(fragment: str) -> _PageParser:
    p = _PageParser()
    p.feed(fragment)
    p.close()
    return p


def check_product(conn: sqlite3.Connection, product: str) -> dict:
    """emit all three surfaces for one product and hold them against the
    canonical record and against each other. returns claims/verified counts
    plus every failure found; an empty failure list is the pass."""
    cs = claim_set(conn, product)
    ident = cs["identity"]
    page = parse_page(emit_page(conn, product))
    feed = emit_feed(conn, product)
    ld = emit_jsonld(conn, product)
    f: list[str] = []

    # identity travels identically
    if page.product != ident["shopify_id"]:
        f.append("page: data-product differs from canonical shopify_id")
    if feed["id"] != ident["shopify_id"] or ld["productID"] != ident["shopify_id"]:
        f.append("id: feed.id / jsonld.productID / canonical.shopify_id disagree")
    if not (feed["title"] == ld["name"] == ident["title"]):
        f.append("title: feed.title / jsonld.name / canonical.title disagree")
    if not (feed["brand"] == ld["brand"]["name"] == ident["vendor"]):
        f.append("brand: feed.brand / jsonld.brand.name / canonical.vendor disagree")

    verified_labels = {label(c["field"]) for c in cs["claims"] if c["verified"]}
    feed_detail = {d["attribute_name"]: d for d in feed["product_detail"]}
    ld_props = {p["name"]: p for p in ld["additionalProperty"]}

    # coverage: the page carries every claim; the machine surfaces carry
    # exactly the verified subset — no leak, no drop.
    if set(page.rows) != {c["field"] for c in cs["claims"]}:
        f.append("page: claim set differs from canonical")
    if set(feed_detail) != verified_labels:
        f.append("feed: product_detail must carry exactly the verified claims")
    if set(ld_props) != verified_labels:
        f.append("jsonld: additionalProperty must carry exactly the verified claims")

    for c in cs["claims"]:
        row = page.rows.get(c["field"])
        if row is None:
            continue  # already counted under coverage
        lab = label(c["field"])
        if c["verified"]:
            fd, lp = feed_detail.get(lab), ld_props.get(lab)
            if row["value"] != c["value"] or row["text"] != display_value(c):
                f.append(f'{c["field"]}: page value differs from canonical')
            if fd is not None and fd["attribute_value"] != display_value(c):
                f.append(f'{c["field"]}: feed value differs from canonical')
            if lp is not None and (lp["value"] != c["value"] or lp.get("unitText") != c["unit"]):
                f.append(f'{c["field"]}: jsonld value differs from canonical')
            # and pairwise, surface against surface
            if fd is not None and lp is not None and not (
                row["value"] == lp["value"] and fd["attribute_value"] == row["text"]
            ):
                f.append(f'{c["field"]}: surfaces disagree with each other')
        else:
            if row["text"] != NOT_YET_VERIFIED or row["value"] is not None:
                f.append(f'{c["field"]}: unverified claim must render "{NOT_YET_VERIFIED}", never a bare value')
            if lab in feed_detail:
                f.append(f'{c["field"]}: unverified claim leaked into the feed')
            if lab in ld_props:
                f.append(f'{c["field"]}: unverified claim leaked into the JSON-LD')
        if bool(c["fit_critical"]) != (c["field"] in page.fc_fields):
            f.append(f'{c["field"]}: fit-critical mark wrong on the page')

    g = verified_gtin([c for c in cs["claims"] if c["verified"]])
    if ("gtin" in feed) != bool(g):
        f.append("feed: gtin must appear exactly when a verified gtin claim exists")
    if "gtin13" in ld and not g:
        f.append("jsonld: gtin13 without a verified gtin claim")

    return {
        "product": product, "handle": ident["handle"],
        "claims": len(cs["claims"]),
        "verified": sum(1 for c in cs["claims"] if c["verified"]),
        "failures": f,
    }


def run_check(conn: sqlite3.Connection, sample: int = 50) -> dict:
    """the ratified check: pick the `sample` products with the most spec
    claims, emit all three surfaces each, assert value-identity per claim.
    read-only against the canonical record; fails closed on an empty one."""
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row
    picked = [r["product"] for r in cur.execute(
        "SELECT product, COUNT(*) AS n FROM spec_claims"
        " GROUP BY product ORDER BY n DESC, product LIMIT ?", (sample,))]
    results = [check_product(conn, pid) for pid in picked]
    totals = {
        "sample": sample,
        "products": len(results),
        "passed": sum(1 for r in results if not r["failures"]),
        "failed": sum(1 for r in results if r["failures"]),
        "claims": sum(r["claims"] for r in results),
        "verified": sum(r["verified"] for r in results),
        "unverified": sum(r["claims"] - r["verified"] for r in results),
        "failures": sum(len(r["failures"]) for r in results),
    }
    return {
        "date": time.strftime("%Y-%m-%d"),
        "totals": totals,
        "results": results,
        "pass": totals["products"] > 0 and totals["failed"] == 0,
    }


def render_report(result: dict, build: dict | None = None, db: str | None = None) -> str:
    t = result["totals"]
    L = [
        f"# emit consistency — {result['date']}",
        "",
        f"**{'PASS' if result['pass'] else 'FAIL'}** — {t['passed']}/{t['products']} products clean "
        f"(sample: the {t['sample']} products with the most spec claims) · {t['claims']} claims "
        f"compared · {t['verified']} verified (carried on page, feed, and JSON-LD — values "
        f"identical) · {t['unverified']} unverified (page renders \"not yet verified\"; excluded "
        f"from feed and JSON-LD — machine surfaces carry verified truth only) · "
        f"{t['failures']} failures",
        "",
        "> one extraction (claim_set) feeds all three renderers; this check re-parses the",
        "> rendered outputs — the page's dl fragment, the feed dict, the JSON-LD dict — and",
        "> asserts per claim: identical values on every surface that carries it, unverified",
        "> claims marked on the page and absent from the machine surfaces, fit-critical",
        "> marks in place, and identity (id, title, brand) equal across surfaces.",
        "",
    ]
    if build:
        L += [
            f"canonical build: {build['products']} products · {build['claims']} claims · "
            f"{build['verified']} verified · {build['unverified']} unverified"
            + (f" · built from landed facts in {db}" if db else ""),
            "",
        ]
    L += ["## per product", "", "| product | handle | claims | verified | result |",
          "|---|---|---:|---:|---|"]
    for r in result["results"]:
        verdict = "pass" if not r["failures"] else "FAIL — " + "; ".join(r["failures"])
        L.append(f"| {r['product']} | {r['handle']} | {r['claims']} | {r['verified']} | {verdict} |")
    L += ["", "_the emitters read only the canonical record (table-set: canonical); the facts",
          "tables stay untouched — the connection's write guard denies anything else._", ""]
    return "\n".join(L)


def write_report(result: dict, out_dir: Path | str, build: dict | None = None,
                 db: str | None = None) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"emit-consistency-{result['date']}.md"
    path.write_text(render_report(result, build, db))
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="emit page/feed/JSON-LD from the canonical record and prove they agree")
    sub = ap.add_subparsers(dest="cmd", required=True)
    chk = sub.add_parser("check", help="build the canonical record, emit a sample, assert value identity")
    chk.add_argument("--sample", type=int, default=50)
    chk.add_argument("--db", default=str(default_db()))
    chk.add_argument("--taxonomy", default=None, help="taxonomy json (default: the store's)")
    chk.add_argument("--config", default=None, help="audit config json (default: the store's)")
    chk.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)

    conn = connect_guarded(args.db)
    try:
        taxonomy = json.loads(Path(args.taxonomy).read_text()) if args.taxonomy else None
        config = json.loads(Path(args.config).read_text()) if args.config else None
        build = build_canonical(conn, taxonomy, config)
        result = run_check(conn, args.sample)
    finally:
        conn.close()
    path = write_report(result, args.out, build, db=str(Path(args.db).resolve()))
    t = result["totals"]
    print(f"[emit] {'PASS' if result['pass'] else 'FAIL'} — {t['passed']}/{t['products']} products · "
          f"{t['claims']} claims ({t['verified']} verified, {t['unverified']} unverified) · "
          f"canonical: {build['products']} products, {build['claims']} claims · report -> {path}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
