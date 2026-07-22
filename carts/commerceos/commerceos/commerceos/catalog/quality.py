"""the catalog quality gate — delist flags, recomputed from landed facts (D5).

v0's doctrine, re-keyed to the current spine (the tombstone is read-only
reference: the tombstoned prior body's catalog module,
quality.py): detect noise SKUs and home-decor leakage, FLAG for the owner's
ruling, never delete. two flag classes:

  noise — dev-store demo data (Shopify seed snowboards, gift card), titles
          shaped like test/sample/placeholder, products whose every variant
          is zero-priced. junk wears its shape openly; one shape flags.
  decor — home-decor leakage into the outdoor catalog. CONSERVATIVE, the
          v0 law tightened: ONE SIGNAL ALONE NEVER FLAGS. a decor keyword
          needs a corroborating signal (a decor-leaf product_type, a decor
          marker in tags/collections, or a home brand); a home brand alone
          never flags — it only corroborates (a home/patio brand also makes
          legit outdoor gear: firepits, pizza ovens — verified 2026-06-30).
          single-signal products are HELD and reported, not flagged.

signals read only the landed facts: title, vendor, product_type, tags,
collections (+ variant prices for zero_price). v0's source_path signal
(the Standard Taxonomy path) is not landed by the current sync — raw
carries category: null — so the path's descendant here is the decor-leaf
product_type set, taken from the locked taxonomy's Home & Garden > Decor
and ambient-lighting leaves.

what leaves this module is a PROPOSAL through the gate, ONE per PRODUCT
(not per flag class, CW8), method mutate_product_state with args
{product_id, state:"delisted"} — mutate_product_state is consequential by
the shipped method class, so it PARKS on the owner's /approvals queue,
never auto-runs. one-per-product so each delist approves and records its
own lifecycle transition: on the owner's approve, the gated return leg
(delist.execute_and_record) flips the store status through the one write
door and records the lifecycle move on the verified read-back. stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from commerceos.gate import gate

REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO / "reports"

AGENT = "catalog-quality"
FUNCTION = "catalog-enrichment"
# the state-change executor (CW2, spine/writes.py:_mutate_product_state). a
# delist is args {product_id, state:"delisted"} — the executor flips the store
# status and reads it back; the gated return leg (delist.execute_and_record)
# records the lifecycle transition on that verified outcome. mutate_product_field
# was the pre-CW8 shape (args.state="delist"); it had no state executor — the bug
# CW8 fixes.
METHOD = "mutate_product_state"

# the prior body's run, for drift accounting in the report (backlog D5).
V0_BASELINE = {"noise": 15, "decor": 69,
               "label": "quality gate over the pre-push supplier catalog, 2026-06-30"}

# --- noise: dev-store demo data + placeholder shapes (config-ish) -------
# v0's sample-handle pattern, extended to the two Collection Snowboard
# siblings (-liquid, -oxygen) it missed; real catalog handles that start
# with "the-" (the-log-cabin-fire-pit, the-flusher-*) do NOT end in these
# suffixes — checked against the landed facts 2026-07-11.
DEMO_HANDLE = re.compile(r"^(gift-card|the-.*-(snowboard|collection)(-.*)?|.*-hydrogen)$", re.I)
# the Shopify dev-store seed vendors — no real supplier wears these names.
DEMO_VENDORS = {"commerceos dev", "snowboard vendor", "hydrogen vendor", "multi-managed vendor"}
# word-bounded on purpose: Bontrager's XXX line and "Contest ..." titles
# are real products; substring greed flags them, boundaries don't.
PLACEHOLDER_TITLE = re.compile(
    r"\b(test|testing|sample|placeholder|dummy|demo|tbd|tbc|do not use|delete me)\b", re.I)

# --- decor / off-catalog leakage (config-ish; store #1's outdoor catalog) --
# v0's title keywords + the shapes the landed catalog actually wears
# (wall signs, garden sculptures, artificial fence/turf — evidence, not guesses).
DECOR_TITLE = re.compile(
    r"\b(patio|decorative|ambient|candle|ornament|wall art|wall sign|sculpture|statue|"
    r"entrance|vase|tealight|fairy light|string light|centerpiece|figurine|wind ?chime|"
    r"door ?mat|trellis|artificial (fence|turf|grass|plant|shrub|flower|flora))\b", re.I)
# decor markers as EXACT tag/collection values (lowercased) — substring
# matching flags Signal Mirrors via "sign"; exact values don't.
DECOR_MARKERS = {"decor", "garden decor", "garden sculptures", "wall signs", "wall art",
                 "novelty signs", "home fragrances", "artificial flora", "ornaments"}
# the current-facts descendant of v0's _DECOR_PATH: product_type leaves that
# live under Home & Garden > Decor / ambient home lighting in the store's
# locked taxonomy (taxonomy.json leaf_category_map). work/camp
# lighting leaves (Work Lights, Flood & Spot Lights, Lanterns) stay out.
DECOR_TYPES = {"decor", "novelty signs", "garden sculptures", "sculptures & statues",
               "lawn ornaments & garden sculptures", "visual artwork", "artificial shrubs",
               "air fresheners", "home fragrances", "night lights & ambient lighting",
               "table lamps", "lamps", "lighting fixtures"}
# home/patio brands — CORROBORATING ONLY, never stands alone (v0's law).
HOME_BRANDS = {"la hacienda", "smart garden", "luxform"}


def noise_flags(handle, title, vendor, prices=None, has_sku=True) -> list[str]:
    """noise signals; any one flags (junk wears its shape openly).
    zero_price fires only when EVERY variant is zero/unpriced — a single
    free variant among priced ones is a freebie row, not junk. no_sku is
    corroborating-only: it rides as evidence beside another signal, never
    flags alone (plenty of legit supplier rows land SKU-less)."""
    f = []
    if DEMO_HANDLE.match(handle or ""):
        f.append("demo_handle")
    if (vendor or "").strip().lower() in DEMO_VENDORS:
        f.append("demo_vendor")
    if PLACEHOLDER_TITLE.search(title or ""):
        f.append("placeholder_title")
    if prices is not None and len(prices) > 0 and all(p is None or p <= 0 for p in prices):
        f.append("zero_price")
    if f and not has_sku:
        f.append("no_sku")  # corroborating only — never stands alone
    return f


def decor_signals(title, vendor, product_type, tags=(), collections=()) -> list[str]:
    """every decor signal that fires — the census, before the law.
    home_brand appends only beside a non-brand signal (corroborating-only,
    v0 verbatim); a home brand with a clean title/type/tags fires nothing."""
    t = title or ""
    p = (product_type or "").strip().lower()
    marks = {str(x).strip().lower() for x in (list(tags or []) + list(collections or []))}
    f = []
    if DECOR_TITLE.search(t):
        f.append("decor_keyword")
    if p in DECOR_TYPES:
        f.append("decor_type")
    if marks & DECOR_MARKERS:
        f.append("decor_tag")
    if (vendor or "").strip().lower() in HOME_BRANDS and f:
        f.append("home_brand")  # corroborating only — never stands alone
    return f


def decor_flags(title, vendor, product_type, tags=(), collections=()) -> list[str]:
    """the law: one signal alone never flags. returns the evidence when at
    least two distinct signals corroborate, else [] (clean or held)."""
    f = decor_signals(title, vendor, product_type, tags, collections)
    return f if len(f) >= 2 else []


def compute_delist_candidates(conn) -> dict:
    """recompute both flag classes from the landed facts. returns
    {"noise": [...], "decor": [...], "held": [...], "brand_only": [...],
    "total": n} — held is the single-signal decor near-misses the law kept
    back; brand_only is the home-brand products with no other signal
    (v0's poster-child leak, visible for the ruling, flagged nowhere)."""
    rows = conn.execute(
        "SELECT shopify_id, handle, title, status, vendor, product_type, tags, collections"
        " FROM products ORDER BY handle").fetchall()
    prices: dict[str, list] = {}
    skus: dict[str, bool] = {}
    for v in conn.execute("SELECT product_id, price_minor, sku FROM variants"):
        prices.setdefault(v["product_id"], []).append(v["price_minor"])
        skus[v["product_id"]] = skus.get(v["product_id"], False) or bool((v["sku"] or "").strip())

    noise, decor, held, brand_only = [], [], [], []
    for r in rows:
        tags = json.loads(r["tags"] or "[]")
        colls = json.loads(r["collections"] or "[]")
        base = {"product_id": r["shopify_id"], "handle": r["handle"], "title": r["title"],
                "vendor": r["vendor"], "product_type": r["product_type"], "status": r["status"]}
        nf = noise_flags(r["handle"], r["title"], r["vendor"],
                         prices=prices.get(r["shopify_id"]),
                         has_sku=skus.get(r["shopify_id"], False))
        if nf:
            noise.append({**base, "evidence": nf})
            continue  # noise wins; a demo snowboard is not also decor
        sig = decor_signals(r["title"], r["vendor"], r["product_type"], tags, colls)
        if len(sig) >= 2:
            decor.append({**base, "evidence": sig})
        elif sig:
            held.append({**base, "evidence": sig})
        elif (r["vendor"] or "").strip().lower() in HOME_BRANDS:
            brand_only.append({**base, "evidence": ["home_brand"]})
    return {"noise": noise, "decor": decor, "held": held,
            "brand_only": brand_only, "total": len(rows)}


def propose_delists(conn, candidates: dict, report_path: str | None = None,
                    table: dict | None = None) -> list[dict]:
    """park the candidates for the owner THROUGH THE GATE — ONE proposal per
    PRODUCT (not per flag class), so each delist approves and records its own
    lifecycle transition on a verified store write (CW8). the call is the exact
    one the executor runs: method mutate_product_state, args {product_id,
    state:"delisted"} — mutate_product_state is consequential by the shipped
    method class, so submit() parks it pending on the owner's /approvals queue.
    zero candidates = zero proposals (no empty spam). anything but a park is a
    policy surprise: fail loud, execute nothing."""
    labels = {
        "noise": ("noise SKU (dev-store demo data / placeholder shape)",
                  "dev-store seed products and placeholder shapes are not the store's "
                  "catalog; they leak into search, feeds, and counts. flag law: any "
                  "one noise shape flags; evidence attached."),
        "decor": ("home-decor leakage (off the outdoor catalog)",
                  "home-decor mis-filed into the outdoor catalog. conservative law "
                  "(v0, tightened): one signal alone never flags — this candidate "
                  "carries at least two corroborating signals; a home brand alone "
                  "never flags, it only corroborates. single-signal items were held, "
                  "not flagged (see the report)."),
    }
    out = []
    for klass in ("noise", "decor"):
        for c in candidates.get(klass) or []:
            res = gate.submit(conn, {
                "agent": AGENT, "function": FUNCTION, "method": METHOD,
                "args": {"product_id": c["product_id"], "state": "delisted"},
                "declared_type": "consequential",
                "intent": f"delist {c['handle']} — {labels[klass][0]}",
                "rationale": labels[klass][1],
                "impact": {"scope": "catalog", "flag_class": klass,
                           "product_id": c["product_id"], "handle": c["handle"],
                           "evidence": c["evidence"]},
                "provenance": [{"source": f"landed facts: products+variants tables; "
                                          f"report: {report_path or '(not written)'}"}],
            }, table=table)
            if res["decision"] != "parked":
                raise RuntimeError(
                    f"delist proposal for {c['handle']} did not park "
                    f"(got {res['decision']!r}) — mutate_product_state must classify "
                    "consequential; refusing to continue")
            out.append({"flag_class": klass, "record_id": res["record_id"],
                        "decision": res["decision"], "action_type": res["action_type"],
                        "product_id": c["product_id"], "handle": c["handle"],
                        "evidence": c["evidence"], "expires_at": res.get("expires_at")})
    return out


# ---------- the report (what the ruling reads) ---------------------------

def render_report(candidates: dict, parked: list[dict], date: str | None = None) -> str:
    date = date or time.strftime("%Y-%m-%d")
    noise, decor, held = candidates["noise"], candidates["decor"], candidates["held"]
    brand_only = candidates.get("brand_only", [])

    def table(rows, cols):
        head = "| " + " | ".join(c for c, _ in cols) + " |"
        sep = "|" + "|".join("---" for _ in cols) + "|"
        body = ["| " + " | ".join(str(f(r)) for _, f in cols) + " |" for r in rows]
        return "\n".join([head, sep] + body)

    ev = lambda r: ", ".join(r["evidence"])
    L = [
        f"# delist candidates — {date}",
        "",
        f"recomputed from the current landed facts ({candidates['total']} products; "
        f"signals: title, vendor, product_type, tags, collections, variant prices). "
        f"flags are PROPOSALS — the owner rules on /approvals; nothing delists "
        f"until the ruling lands and an executor for state changes exists (D5).",
        "",
        f"**totals: {len(noise)} noise + {len(decor)} decor** · prior body (v0 "
        f"{V0_BASELINE['label']}): ~{V0_BASELINE['noise']} noise + {V0_BASELINE['decor']} decor.",
        "",
        "## the law (conservative, v0's tightened)",
        "",
        "- noise: any one shape flags — demo handle, demo vendor, placeholder title "
        "(word-bounded), all-variants-zero price. no_sku rides as corroborating "
        "evidence only.",
        "- decor: **one signal alone never flags.** a candidate carries at least two "
        "of: decor keyword in title, decor-leaf product_type, decor marker in "
        "tags/collections. a home brand alone never flags — it only corroborates "
        "(home brands make legit outdoor gear: firepits, pizza ovens).",
        "- single-signal decor near-misses are HELD and listed below — visible, "
        "not proposed.",
        "",
        f"## noise SKUs ({len(noise)})",
        "",
        table(noise, [("handle", lambda r: f"`{r['handle']}`"),
                      ("title", lambda r: r["title"]),
                      ("vendor", lambda r: r["vendor"]),
                      ("status", lambda r: r["status"]),
                      ("evidence", ev)]) if noise else "_none._",
        "",
        f"## decor / off-catalog leakage ({len(decor)})",
        "",
        table(decor, [("handle", lambda r: f"`{r['handle']}`"),
                      ("title", lambda r: r["title"]),
                      ("vendor", lambda r: r["vendor"]),
                      ("product_type", lambda r: r["product_type"]),
                      ("evidence", ev)]) if decor else "_none._",
        "",
        f"## held by the law — single-signal near-misses ({len(held)}, not proposed)",
        "",
        table(held, [("handle", lambda r: f"`{r['handle']}`"),
                     ("title", lambda r: r["title"]),
                     ("vendor", lambda r: r["vendor"]),
                     ("product_type", lambda r: r["product_type"]),
                     ("signal", ev)]) if held else "_none._",
        "",
        f"## home-brand only — held by the corroborating-only law ({len(brand_only)}, not proposed)",
        "",
        ("the rest of the home-brand estate, wearing no decor signal at all — the "
         "brand also makes legit outdoor gear (firepits, pizza ovens, lanterns), so "
         "brand alone never flags. listed whole so the ruling sees the full estate: "
         + ", ".join(f"`{r['handle']}`" for r in brand_only)) if brand_only else "_none._",
        "",
        "## drift vs the prior body (v0: ~15 noise + 69 decor)",
        "",
        f"- **noise {len(noise)} vs ~15**: the same Shopify dev-store seed family, "
        "counted exactly. v0's handle regex missed the two Collection Snowboard "
        "siblings (`-liquid`, `-oxygen`) and Selling Plans Ski Wax (caught here by "
        "the demo-vendor signal). zero placeholder titles and zero all-zero-priced "
        "products in the landed facts.",
        f"- **decor {len(decor)} vs 69**: three reasons, in size order. (1) the corpus "
        "changed — v0 flagged over the pre-push supplier catalog; the dev store was "
        "pushed 2026-07-01 already curated, and the landed facts carry "
        f"{candidates['total']} products. (2) v0's strongest signal, the source "
        "Standard-Taxonomy path (`Home & Garden > Decor|Lighting|Outdoor Living`), "
        "is not landed by the current sync (raw carries `category: null`) — "
        "path-only candidates cannot corroborate today. (3) the law tightened: v0 "
        "flagged on one signal (path alone or keyword alone); this run requires two. "
        f"the {len(held)} held single-signal items and {len(brand_only)} brand-only "
        "items above are the visible remainder — citronella candles (pest control "
        "by design), patio-set titles, supplier Decor tags on work floodlights, and "
        "the La Hacienda lanterns/firepits/pizza-ovens wearing only their brand.",
        "",
        "## parked proposals (the gate record)",
        "",
    ]
    if parked:
        for p in parked:
            L.append(f"- `{p['record_id'][:8]}` — {p['flag_class']}: `{p['handle']}`, "
                     f"{p['action_type']}, {p['decision']} (expires {p['expires_at']}). "
                     f"approve/reject on /approvals; a lapsed proposal is re-proposed by "
                     f"re-running this module.")
    else:
        L.append("- none submitted (compute-only run, or zero candidates).")
    L += ["",
          "_each proposal is one product, method `mutate_product_state` (args "
          "state=`delisted`). on the owner's approve, the gated return leg "
          "(delist.execute_and_record) flips the store status and records the "
          "lifecycle transition on the verified read-back — state follows a "
          "rendered store change, never a staged one._",
          ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="recompute delist candidates from landed facts and park them through the gate")
    from commerceos.db import default_path

    ap.add_argument("--db", default=str(default_path()))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--no-submit", action="store_true",
                    help="compute and report only; park nothing")
    args = ap.parse_args(argv)

    from commerceos.db import connect
    from commerceos.gate import ledger
    conn = connect(args.db)
    ledger.ensure_schema(conn)
    try:
        cands = compute_delist_candidates(conn)
        date = time.strftime("%Y-%m-%d")
        report_path = Path(args.out) / f"delist-candidates-{date}.md"
        parked = [] if args.no_submit else propose_delists(conn, cands, report_path=str(report_path))
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_report(cands, parked, date))
    finally:
        conn.close()
    print(f"[quality] {len(cands['noise'])} noise + {len(cands['decor'])} decor candidates "
          f"(v0: ~{V0_BASELINE['noise']}+{V0_BASELINE['decor']}) · {len(cands['held'])} held "
          f"single-signal · {len(parked)} proposal(s) parked · report -> {report_path}")
    for p in parked:
        print(f"[quality]   {p['flag_class']}: {p['products']} products parked as "
              f"{p['action_type']} ({p['record_id'][:8]}, expires {p['expires_at']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
