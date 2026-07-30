"""the spec-verification pilot — D4's first slice: parsed claims become
VERIFIED claims with citable manufacturer sources, fit-critical first.

the provenance rule (spec/parts/catalog-loop.md): a value parsed from a
supplier blob stays verified:false until a real source resolves it. this
module is the resolving loop's first pass, pilot-scale:

  1. pick   — query the canonical claim set for products carrying parsed
              values on fit-critical fields (the taxonomy's fc flags,
              already stamped on spec_claims by canonical.py). emit a
              findings skeleton: every claim with source_url/quote/
              found_value left null.
  2. (human/agent legwork, outside this module) — fetch each product's
              MANUFACTURER spec page, one fetch per product, public pages
              only. record the stated value, the quote, the URL. a page
              that won't load or doesn't state the spec stays null —
              never guess, never substitute a retailer's claim.
  3. run    — compute verdicts mechanically (agree | disagree |
              not_found), submit ONE proposal PER PRODUCT through the
              gate declared fit_critical (ALWAYS human-gated — it parks,
              never autos), and write the pilot report. conflicting
              values are stated as conflicts, never silently resolved.

the proposal shape: method mutate_product_field, args {product_id,
field: "spec_verification", value: {claims: [{field, value, found_value,
source_url, quote, verdict}]}}, declared_type fit_critical. the policy
table's stricter-of-two honors the declared class, and fit_critical never
auto-approves — the park is mechanical, not a convention.

usage:
  uv run python -m commerceos.catalog.verify_sources pick \
      --brands "Ledlenser,Leatherman" --limit 20 --out findings.json
  uv run python -m commerceos.catalog.verify_sources run \
      --findings findings.json [--submit] [--out-dir reports]
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from commerceos.db import connect, default_path
from commerceos.gate import gate, ledger, policy

AGENT = "spec-verifier"
FUNCTION = "catalog-enrichment"
# CW7 built 2026-07-18: the method has its own local executor now. pilot
# proposals parked under the old method name (mutate_product_field) were
# never executable; expire or re-propose them — a re-run re-proposes with
# current numbers under this method.
METHOD = "mutate_spec_verification"
FIELD = "spec_verification"

VERDICTS = ("agree", "disagree", "not_found")

REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO / "reports"

# numeric agreement tolerance: manufacturers round (3.0 in = 7.62 cm may be
# stated 7.6); 2% relative keeps rounding honest without blessing drift.
REL_TOL = 0.02

# unit families for honest cross-unit comparison — factors to a family base.
# units from different families (or unknown units) never convert: a failed
# conversion falls back to comparing bare numbers WITH a conflict note,
# never a silent pass (the never-collapse rule).
_FAMILIES: list[dict[str, float]] = [
    {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4},
    {"g": 1.0, "kg": 1000.0, "oz": 28.349523125, "lb": 453.59237},
    {"ml": 1.0, "l": 1000.0},
]

_IP_RE = re.compile(r"^IP[X0-9][0-9X]?$")


# ---- 1. pick the pilot set ---------------------------------------------

def pick_pilot_set(conn, brands: list[str] | None = None, limit: int = 20) -> list[dict]:
    """products from the canonical record that carry PARSED (verified=0)
    values on fit-critical fields — the only products this pilot admits.
    a product with no unverified fit-critical claim never enters, whatever
    its brand. brands filter (exact vendor match) and interleave: the
    limit is spread round-robin across brands so one deep catalog cannot
    crowd the others out. deterministic order throughout."""
    where = "sc.fit_critical = 1 AND sc.verified = 0"
    params: list = []
    if brands:
        where += f" AND cp.vendor IN ({','.join('?' * len(brands))})"
        params.extend(brands)
    rows = conn.execute(
        f"""SELECT cp.shopify_id, cp.handle, cp.title, cp.vendor, cp.category,
                   sc.field, sc.value, sc.unit
            FROM spec_claims sc
            JOIN canonical_products cp ON cp.shopify_id = sc.product
            WHERE {where}
            ORDER BY cp.vendor, cp.title, sc.field""",
        params,
    ).fetchall()

    by_product: dict[str, dict] = {}
    for r in rows:
        p = by_product.setdefault(r["shopify_id"], {
            "product_id": r["shopify_id"], "handle": r["handle"],
            "title": r["title"], "vendor": r["vendor"],
            "category": r["category"], "claims": [],
        })
        p["claims"].append({"field": r["field"], "value": r["value"], "unit": r["unit"]})

    # round-robin across vendors (brand order as given, else alphabetical)
    order = brands or sorted({p["vendor"] for p in by_product.values()})
    lanes = {b: [p for p in by_product.values() if p["vendor"] == b] for b in order}
    picked: list[dict] = []
    i = 0
    while len(picked) < limit and any(lanes.values()):
        lane = lanes[order[i % len(order)]]
        if lane:
            picked.append(lane.pop(0))
        i += 1
        if i > limit * max(1, len(order)) * 2:  # all lanes drained
            break
    return picked


def skeleton(products: list[dict]) -> dict:
    """the findings file the legwork fills in: every claim gets null
    evidence slots. found_value left null = not found — never guess."""
    out = {
        "date": time.strftime("%Y-%m-%d"),
        "picked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method_note": ("manufacturer public spec pages only, one fetch per "
                        "product. a page that won't load or doesn't state the "
                        "spec stays null (not_found) — never a retailer's claim."),
        "products": [],
    }
    for p in products:
        out["products"].append({
            **{k: p[k] for k in ("product_id", "handle", "title", "vendor", "category")},
            "claims": [{**c, "source_url": None, "quote": None,
                        "found_value": None, "found_unit": None, "note": None}
                       for c in p["claims"]],
        })
    return out


# ---- 3a. verdicts, computed mechanically --------------------------------

def _num(v) -> float | None:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _convert(value: float, from_unit: str, to_unit: str) -> float | None:
    """cross-unit only within one family; anything else refuses (None)."""
    fu, tu = from_unit.strip().lower(), to_unit.strip().lower()
    if fu == tu:
        return value
    for fam in _FAMILIES:
        if fu in fam and tu in fam:
            return value * fam[fu] / fam[tu]
    return None


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= REL_TOL * max(abs(a), abs(b), 1e-9)


def _ip_code(v) -> str | None:
    s = re.sub(r"[\s\-]", "", str(v or "")).upper()
    return s if _IP_RE.match(s) else None


def verdict_for(parsed_value, unit, found_value, found_unit=None) -> tuple[str, str | None]:
    """(verdict, note). agree | disagree | not_found — nothing else.

    IP codes compare exactly after normalization (IPX4 is not IP54 — never
    collapse non-comparable ratings). numbers compare in the claim's stored
    unit, converting the found unit within its family; when the bare
    numbers match but the units don't, the verdict stays disagree and the
    note names the likely unit slip — a conflict stated, never resolved
    silently. everything else falls back to case-insensitive equality."""
    if found_value is None or str(found_value).strip() == "":
        return "not_found", None

    p_ip, f_ip = _ip_code(parsed_value), _ip_code(found_value)
    if p_ip or f_ip:
        if p_ip and f_ip and p_ip == f_ip:
            return "agree", None
        return "disagree", None

    pn, fn = _num(parsed_value), _num(found_value)
    if pn is not None and fn is not None:
        pu, fu = (unit or "").strip(), (found_unit or unit or "").strip()
        converted = _convert(fn, fu, pu) if pu and fu else fn
        if converted is not None and _close(pn, converted):
            return "agree", None
        note = None
        if pu and fu and pu.lower() != fu.lower() and _close(pn, fn):
            note = (f"bare number matches the manufacturer's {fn:g} {fu}; "
                    f"the stored unit ({pu}) looks wrong")
        return "disagree", note

    if str(parsed_value).strip().casefold() == str(found_value).strip().casefold():
        return "agree", None
    return "disagree", None


def judge(findings: dict) -> dict:
    """stamp a verdict on every claim (in place) and tally per product and
    overall. found evidence must carry a source_url — evidence with no
    citation is refused (no source, no claim)."""
    totals = {"products": 0, "claims": 0, "agree": 0, "disagree": 0, "not_found": 0}
    for p in findings["products"]:
        tally = {"agree": 0, "disagree": 0, "not_found": 0}
        for c in p["claims"]:
            if c.get("found_value") is not None and not c.get("source_url"):
                raise ValueError(
                    f"{p['handle']}/{c['field']}: a found value with no source_url "
                    "— no source, no claim")
            v, note = verdict_for(c["value"], c.get("unit"),
                                  c.get("found_value"), c.get("found_unit"))
            c["verdict"] = v
            if note and not c.get("note"):
                c["note"] = note
            tally[v] += 1
            totals["claims"] += 1
            totals[v] += 1
        p["tally"] = tally
        totals["products"] += 1
    findings["totals"] = totals
    return findings


# ---- 3b. one proposal per product, through the gate ----------------------

def _gid(product_id: str) -> str:
    return product_id if str(product_id).startswith("gid://") \
        else f"gid://shopify/Product/{product_id}"


def build_proposal(product: dict) -> dict:
    """ONE proposal per product: all its checked claims batched, so the
    owner's queue stays humane. declared fit_critical — the gate honors
    declaring higher and fit_critical never auto-approves: it MUST park."""
    claims = [{
        "field": c["field"], "value": c["value"], "unit": c.get("unit"),
        "found_value": c.get("found_value"), "source_url": c.get("source_url"),
        "quote": c.get("quote"), "verdict": c["verdict"],
        **({"note": c["note"]} if c.get("note") else {}),
    } for c in product["claims"]]
    n = len(claims)
    agree = sum(1 for c in claims if c["verdict"] == "agree")
    conflict = sum(1 for c in claims if c["verdict"] == "disagree")
    cites = sorted({c["source_url"] for c in claims if c["source_url"]})
    return {
        "agent": AGENT, "function": FUNCTION, "method": METHOD,
        "args": {"product_id": _gid(product["product_id"]), "field": FIELD,
                 "value": {"claims": claims}},
        "declared_type": policy.FIT_CRITICAL,
        # rendered on home's record card and the approvals queue — plain words.
        "intent": (f"check {n} safety-bearing details for {product['title']} "
                   f"({agree} agree, {conflict} conflict)"),
        "rationale": ("manufacturer spec page checked against the parsed claim. "
                      "approval flips agreeing claims to verified with the cite; "
                      "conflicts are stated for ruling, never silently resolved "
                      "(a wrong spec is a safety claim, not content)."),
        "impact": {"scope": "spec-provenance", "product": product["handle"],
                   "risk": "safety-bearing spec claims"},
        "provenance": [{"source": u} for u in cites] or {"unverified": True},
    }


def _already_pending(conn, args_hash: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM ledger WHERE status = 'pending'"
        " AND json_extract(proposal, '$.args_hash') = ? LIMIT 1",
        (args_hash,),
    ).fetchone()
    return row is not None


def submit_pilot(conn, findings: dict) -> dict:
    """submit one gate proposal per product that has at least one FOUND
    claim (agree or disagree). all-not_found products have nothing to put
    before the owner — they stay report-only. an identical proposal already
    pending is skipped, so re-runs never stack the queue. every submit must
    come back parked: fit_critical never autos — anything else is a
    construction failure and raises."""
    ledger.ensure_schema(conn)
    receipts = {"submitted": 0, "parked": 0, "skipped_already_pending": 0,
                "skipped_nothing_found": 0, "records": []}
    for p in findings["products"]:
        if all(c["verdict"] == "not_found" for c in p["claims"]):
            receipts["skipped_nothing_found"] += 1
            continue
        prop = build_proposal(p)
        ahash = policy.args_hash(prop["method"], prop["args"])
        if _already_pending(conn, ahash):
            receipts["skipped_already_pending"] += 1
            continue
        res = gate.submit(conn, prop)
        receipts["submitted"] += 1
        if res["decision"] != "parked" or res["action_type"] != policy.FIT_CRITICAL:
            raise RuntimeError(
                f"fit-critical proposal did not park ({res['decision']}, "
                f"{res['action_type']}) — the wall failed; stop and investigate")
        receipts["parked"] += 1
        receipts["records"].append({"id": res["record_id"], "handle": p["handle"],
                                    "expires_at": res["expires_at"]})
    return receipts


def execute_and_record(conn, record_id: str) -> dict:
    """the approved verification's return leg (CW7, ruled division):
    1. the spine executor runs the approved record — LOCAL, no store
       client, returns the instruction receipt (the flips it validated);
    2. catalog-loop's own writer records each flip
       (canonical.record_verification — verified, dated, cited);
    3. the render check re-reads page, feed, and JSON-LD
       (emitters.check_product) — verified_rendered only when all three
       agree; a failed check compensates every flip exactly and reports
       failed. commits on success and after compensation — never a blind
       rollback (the consumed handle must stay consumed either way)."""
    from commerceos.catalog import canonical, emitters
    from commerceos.spine import writes

    out = writes.execute(conn, record_id, client=None)
    if not out.get("ok"):
        return {"ok": False, "verified_rendered": False, "outcome": out}
    flips = out.get("flips") or []
    if not flips:
        conn.commit()
        return {"ok": True, "verified_rendered": True, "flipped": 0,
                "conflicts_stated": out.get("conflicts_stated", 0),
                "not_found": out.get("not_found", 0), "failures": []}

    product = flips[0]["product"]
    priors: list[tuple[str, dict]] = []
    for f in flips:
        row = conn.execute(
            "SELECT verified, verified_on, source FROM spec_claims"
            " WHERE product=? AND field=?", (product, f["field"])).fetchone()
        priors.append((f["field"], {
            "verified": row[0] if row else 0,
            "verified_on": row[1] if row else None,
            "source": row[2] if row else "parsed:unknown"}))
        canonical.record_verification(conn, product, f["field"], f["value"], f["source"])

    check = emitters.check_product(conn, product)
    if check["failures"]:
        for field, prior in priors:
            canonical.revert_verification(conn, product, field, prior)
        conn.commit()
        return {"ok": False, "verified_rendered": False, "flipped": 0,
                "failures": check["failures"],
                "error": "render check failed — flips compensated exactly"}
    conn.commit()
    return {"ok": True, "verified_rendered": True, "flipped": len(flips),
            "conflicts_stated": out.get("conflicts_stated", 0),
            "not_found": out.get("not_found", 0), "failures": []}


# ---- 4. the pilot report -------------------------------------------------

def _host(url: str | None) -> str:
    return re.sub(r"^https?://(www\.)?", "", url or "").split("/")[0]


def render_report(findings: dict, receipts: dict | None = None) -> str:
    t = findings["totals"]
    L = [
        f"# spec-verification pilot — {findings['date']}",
        "",
        f"**{t['products']} products · {t['claims']} fit-critical claims checked · "
        f"{t['agree']} agree · {t['disagree']} disagree · {t['not_found']} not found**",
        "",
        "> parsed-from-blob claims checked against MANUFACTURER spec pages — one",
        "> fetch per product, public pages only. a spec the page does not state is",
        "> not_found, never guessed and never a retailer's claim. verdicts are",
        "> computed, conflicts are stated for the owner's ruling, and every",
        "> proposal is declared fit_critical: it parks, it never auto-approves.",
        "",
        "## the pilot table",
        "",
        "| product | brand | claims | agree | disagree | not found | source |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for p in findings["products"]:
        ty = p["tally"]
        hosts = sorted({_host(c["source_url"]) for c in p["claims"] if c.get("source_url")})
        L.append(f"| {p['title']} | {p['vendor']} | {len(p['claims'])} "
                 f"| {ty['agree']} | {ty['disagree']} | {ty['not_found']} "
                 f"| {', '.join(hosts) or '—'} |")
    L.append(f"| **total** | | **{t['claims']}** | **{t['agree']}** "
             f"| **{t['disagree']}** | **{t['not_found']}** | |")

    conflicts = [(p, c) for p in findings["products"]
                 for c in p["claims"] if c["verdict"] == "disagree"]
    if conflicts:
        L += ["", "## conflicts — stated, not resolved", ""]
        for p, c in conflicts:
            L.append(f"- **{p['title']}** `{c['field']}`: catalog says "
                     f"{c['value']}{' ' + c['unit'] if c.get('unit') else ''}, "
                     f"manufacturer says {c['found_value']}"
                     f"{' ' + c['found_unit'] if c.get('found_unit') else ''} "
                     f"— \"{c.get('quote') or ''}\" ({c.get('source_url')})"
                     + (f" · note: {c['note']}" if c.get("note") else ""))

    not_found = [(p, c) for p in findings["products"]
                 for c in p["claims"] if c["verdict"] == "not_found"]
    if not_found:
        L += ["", "## not found — recorded, never guessed", ""]
        for p, c in not_found:
            L.append(f"- **{p['title']}** `{c['field']}` = {c['value']}: "
                     f"{c.get('note') or 'the manufacturer page does not state this spec'}"
                     + (f" ({c['source_url']})" if c.get("source_url") else ""))

    agrees = [(p, c) for p in findings["products"]
              for c in p["claims"] if c["verdict"] == "agree"]
    if agrees:
        L += ["", "## verified with cite", ""]
        for p, c in agrees:
            L.append(f"- **{p['title']}** `{c['field']}` = {c['value']}"
                     f"{' ' + c['unit'] if c.get('unit') else ''} — "
                     f"\"{c.get('quote') or ''}\" ({c['source_url']})")

    if receipts is not None:
        L += ["", "## gate receipts", "",
              f"- proposals submitted: {receipts['submitted']} · parked pending the "
              f"owner: {receipts['parked']} (fit_critical never auto-approves)",
              f"- skipped — identical proposal already pending: "
              f"{receipts['skipped_already_pending']} · nothing found to propose: "
              f"{receipts['skipped_nothing_found']}"]
        for r in receipts["records"]:
            L.append(f"  - `{r['id'][:8]}` {r['handle']} — expires {r['expires_at']}")
        if receipts["records"]:
            L += ["", "pending approvals lapse per policy (default one hour). a lapsed "
                  "proposal still wanted is re-run from the findings file — re-runs "
                  "skip anything still pending, so the queue never stacks."]
    else:
        L += ["", "## gate receipts", "", "- dry run: nothing submitted."]

    L += ["", f"_findings file: verify-pilot-{findings['date']}-findings.json — the "
          "evidence (URLs, quotes) behind every verdict above._", ""]
    return "\n".join(L)


def write_report(findings: dict, receipts: dict | None = None,
                 out_dir: Path | str = DEFAULT_OUT) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"verify-pilot-{findings['date']}.md"
    path.write_text(render_report(findings, receipts))
    return path


# ---- guardrails between findings file and the live claim set -------------

def check_against_claims(conn, findings: dict) -> None:
    """a findings file gone stale must not park proposals about claims that
    changed under it: every (product, field, value) must still match the
    canonical claim set exactly. raises on drift."""
    for p in findings["products"]:
        for c in p["claims"]:
            row = conn.execute(
                "SELECT value FROM spec_claims WHERE product = ? AND field = ?",
                (p["product_id"], c["field"])).fetchone()
            if row is None:
                raise ValueError(f"{p['handle']}/{c['field']}: no such claim in the "
                                 "canonical record — findings file is stale")
            if str(row["value"]) != str(c["value"]):
                raise ValueError(f"{p['handle']}/{c['field']}: claim value drifted "
                                 f"({row['value']!r} landed vs {c['value']!r} in findings)")


# ---- CLI ------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="spec-verification pilot (D4 first slice)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("pick", help="emit the findings skeleton for the pilot set")
    p1.add_argument("--db", default=str(default_path()))
    p1.add_argument("--brands", default="", help="comma-separated vendor names")
    p1.add_argument("--limit", type=int, default=20)
    p1.add_argument("--out", default="", help="write skeleton here (else stdout)")

    p2 = sub.add_parser("run", help="judge findings, submit gated proposals, write report")
    p2.add_argument("--db", default=str(default_path()))
    p2.add_argument("--findings", required=True)
    p2.add_argument("--submit", action="store_true",
                    help="actually submit to the gate (else dry run)")
    p2.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)

    conn = connect(args.db)
    try:
        if args.cmd == "pick":
            brands = [b.strip() for b in args.brands.split(",") if b.strip()]
            sk = skeleton(pick_pilot_set(conn, brands or None, args.limit))
            text = json.dumps(sk, indent=2, ensure_ascii=False) + "\n"
            if args.out:
                Path(args.out).write_text(text)
                print(f"[pick] {len(sk['products'])} products -> {args.out}")
            else:
                print(text)
            return 0

        findings = json.loads(Path(args.findings).read_text())
        check_against_claims(conn, findings)
        judge(findings)
        receipts = submit_pilot(conn, findings) if args.submit else None
        path = write_report(findings, receipts, args.out_dir)
        t = findings["totals"]
        print(f"[verify-pilot] {t['products']} products · {t['claims']} claims · "
              f"{t['agree']} agree / {t['disagree']} disagree / {t['not_found']} not found"
              + (f" · {receipts['parked']} parked" if receipts else " · dry run")
              + f" · report -> {path}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
