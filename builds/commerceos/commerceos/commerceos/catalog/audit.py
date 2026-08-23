"""the catalog loop's audit phase — behavior 2 of spec/parts/catalog-loop.md.

READ-ONLY: scores every landed product per dimension against the locked
taxonomy, from the facts the spine landed (products + variants tables and
their raw payloads). it never opens a wire and never writes a fact; the
CLI opens the database with mode=ro so the guarantee is mechanical.

the honesty rule: a dimension is scored only when the sync actually landed
its raw signal. an absent key means the sync never asked — the dimension is
marked "not landed by the current sync — dimension not scorable yet", its
weight is withheld from the overall, and the report names it. a key present
with an empty value is a landed fact (requested, came back empty) and fails
the product. a sync limitation is named as such, never scored as measured.

dimensions, weights, signal requirements, and the prior-body baseline are
config (stores/<store>/audit-config.json); the taxonomy is instance data
(stores/<store>/taxonomy.json). the engine knows nothing about outdoor gear.

outputs (v0's shapes, rebuilt clean):
  reports/health-<date>.md    — the human report: dimensions, deltas, backlog, worst gaps
  reports/health-latest.json  — machine state for run-over-run delta tracking

usage:
  uv run python -m commerceos.catalog.audit                # real audit, read-only
  uv run python -m commerceos.catalog.audit --db PATH --out DIR
"""

from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import time
from pathlib import Path

from commerceos import stores

REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO / "reports"


def default_db() -> Path:
    return stores.resolve(stores.active_store(), stores.DB)


def default_taxonomy_path() -> Path:
    return stores.resolve(stores.active_store(), "taxonomy.json")


def default_config_path() -> Path:
    return stores.resolve(stores.active_store(), "audit-config.json")

NOT_LANDED = "not landed by the current sync — dimension not scorable yet"

# the checks this engine knows how to run; everything else about a
# dimension (weight, required signals, notes) lives in config.
KNOWN_DIMENSIONS = (
    "classification", "specs_structured", "provenance", "identity_gtin",
    "merchandising", "seo", "images",
)


def gtin_valid(s: str) -> bool:
    """GS1 mod-10 checksum over GTIN-8/12/13/14 — a barcode that scans,
    not an SKU in costume."""
    if not s or not s.isdigit() or len(s) not in (8, 12, 13, 14):
        return False
    digits = [int(c) for c in s]
    check = digits.pop()
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits)))
    return (10 - total % 10) % 10 == check


def classify_barcode(b: str) -> str:
    """where a landed barcode stands: valid as stored, a fixable artifact,
    or genuinely not a GTIN. the artifact buckets are findings, not passes."""
    b = (b or "").strip()
    if not b:
        return "empty"
    if gtin_valid(b):
        return "valid_gtin_as_stored"
    s = b.lstrip("'")
    if s != b and gtin_valid(s):
        return "apostrophe_wrapped_gtin"      # spreadsheet-export artifact
    if s.isdigit() and len(s) == 11 and gtin_valid("0" + s):
        return "upc_missing_leading_zero"     # spreadsheet dropped the zero
    if s.isdigit() and len(s) in (8, 12, 13, 14):
        return "right_length_bad_checksum"
    if s.isdigit():
        return "digits_wrong_length"
    return "sku_shaped"


def _index_taxonomy(taxonomy: dict) -> dict:
    """taxonomy.json -> lookup maps (v0's shape: cats, leaf reverse map,
    per-category spec schema + fit-critical keys).

    the reverse map takes the curated subcategory lists first, then the
    source-anchored leaf_category_map (417 leaves; a leaf's name is the
    last path segment — the value product_type carries on the live store).
    v0 leaned on the persisted commerceos.category metafield instead; that
    signal is not landed by the current sync, so the taxonomy's own leaf
    set does the resolving — data drives, the engine stays gear-blind.

    CW3b: a curated synonym map (`classification.synonyms`, lowercased
    synonym -> canonical leaf name) is indexed here too — the one door every
    resolver consumer shares (audit, canonical, the classification feature) —
    so no two surfaces can ever disagree about a product's category. indexed
    fail-closed: a synonym must resolve, through this same leaf map, to a
    real locked category (a promised key must open a real door), and a
    synonym may never shadow a real leaf name (the fallback is a fallback,
    never a first resort)."""
    cats = {k: v for k, v in taxonomy["categories"].items() if not k.startswith("_")}
    subcat_to_cat, schema, fc = {}, {}, {}
    for cat, c in cats.items():
        for sub in c.get("subcategories", []):
            subcat_to_cat[str(sub).lower()] = cat
        ss = c.get("spec_schema", [])
        schema[cat] = [f["key"] for f in ss]
        fc[cat] = {f["key"] for f in ss if f.get("fc")}
    leaf_map = (taxonomy.get("classification") or {}).get("leaf_category_map") or {}
    for path, cat in leaf_map.items():
        subcat_to_cat.setdefault(str(path).split(">")[-1].strip().lower(), cat)

    raw_synonyms = (taxonomy.get("classification") or {}).get("synonyms") or {}
    synonyms: dict[str, str] = {}
    for syn, target in raw_synonyms.items():
        key = str(syn).strip().lower()
        leaf = str(target).strip()
        if key in subcat_to_cat:
            raise ValueError(
                f"synonym {syn!r} shadows a real leaf name — a synonym may"
                " never shadow an exact resolution"
            )
        if leaf.lower() not in subcat_to_cat:
            raise ValueError(
                f"synonym {syn!r} -> {target!r} names no locked category"
                " (a promised key must open a real door)"
            )
        synonyms[key] = leaf
    return {"cats": list(cats), "subcat_to_cat": subcat_to_cat, "schema": schema,
            "fc": fc, "synonyms": synonyms}


def resolve_category(
    ptype: str | None, tax: dict, use_synonyms: bool = True
) -> tuple[str | None, bool]:
    """landed product_type -> locked customer category (v0 semantics).
    '<Category> — Other' is a fold bucket; anything else reverse-maps via
    the subcategory list.

    CW3b: when that exact lookup misses (and only on this non-fold branch —
    a fold bucket's own name IS its target and never consults synonyms), a
    curated synonym may resolve it instead: a keyword fallback, never a
    first resort (spec/parts/catalog-workflows.md:158 — "source-anchored
    leaf map first, keyword rules only as fallback"). order is law: exact
    wins, the synonym only fires on a genuine miss. use_synonyms=False lets
    a caller ask "is this cleanly resolved without the fallback" —
    classification.py's `_is_resolved` uses it so a synonym-resolvable
    product is queueable, not resolved, until its metafield is persisted.

    returns (category | None, is_fold)."""
    p = (ptype or "").strip()
    if not p:
        return None, True
    if p.endswith("— Other") or p.endswith("- Other"):
        cat = p.rsplit("—", 1)[0].rsplit("-", 1)[0].strip()
        return (cat if cat in tax["cats"] else None), True
    cat = tax["subcat_to_cat"].get(p.lower())
    if cat is not None:
        return cat, False
    if use_synonyms:
        syn_leaf = tax.get("synonyms", {}).get(p.lower())
        if syn_leaf is not None:
            return tax["subcat_to_cat"].get(syn_leaf.lower()), False
    return None, False


def _specs_and_provenance(
    nodes: list[dict], blob_keys: set[str], spec_namespaces: set[str] | None = None
) -> tuple[dict, bool, list[str]]:
    """metafield nodes -> (specs, provenance_ok, verified_without_source keys).
    a spec is any spec-namespace metafield (config `spec_namespaces`, default
    commerceos) that is neither a _provenance companion nor a descriptive
    blob; the widened sync lands every namespace, and a foreign one
    (global.title_tag, app-owned keys) is not a spec claim and never counts
    against provenance. a node without a namespace key (legacy shape) is
    taken as spec-bearing. provenance holds when every spec has a parseable
    companion and none is flagged verified without a source (v0 semantics)."""
    specs, prov = {}, {}
    for m in nodes:
        ns = m.get("namespace")
        if spec_namespaces is not None and ns is not None and ns not in spec_namespaces:
            continue
        k = m.get("key", "")
        if k.endswith("_provenance"):
            try:
                prov[k[: -len("_provenance")]] = json.loads(m.get("value") or "")
            except Exception:
                prov[k[: -len("_provenance")]] = {"_unparseable": True}
        elif k in blob_keys:
            continue
        else:
            specs[k] = m.get("value")
    ok, vws = True, []
    for k in specs:
        pc = prov.get(k)
        if not pc or pc.get("_unparseable"):
            ok = False
        elif pc.get("verified") is True and not pc.get("source"):
            ok = False
            vws.append(k)
    return specs, ok, vws


def _has_media(raw: dict, media_keys: list[str]) -> bool:
    for k in media_keys:
        v = raw.get(k)
        if isinstance(v, dict) and "nodes" in v:
            if v["nodes"]:
                return True
        elif v:
            return True
    return False


def _signal_present(raw: dict, path: str) -> bool:
    """key PRESENCE, not truthiness: `"barcode": null` is landed-and-empty
    (a real gap); an absent key was never requested (unknowable)."""
    if path.startswith("variants[]."):
        key = path.split(".", 1)[1]
        nodes = (raw.get("variants") or {}).get("nodes") or []
        return any(key in n for n in nodes)
    return path in raw


def audit(conn: sqlite3.Connection, taxonomy: dict, config: dict) -> dict:
    """score every landed product per configured dimension. returns the
    machine state dict (what health-latest.json carries). read-only."""
    dims_cfg = config["dimensions"]
    unknown = [d for d in dims_cfg if d not in KNOWN_DIMENSIONS]
    if unknown:
        raise ValueError(f"unknown dimension(s) {unknown}; this engine scores {list(KNOWN_DIMENSIONS)}")
    wsum = sum(v["weight"] for v in dims_cfg.values())
    if abs(wsum - 1.0) > 1e-6:
        raise ValueError(f"dimension weights must sum to 1.0, got {wsum}")

    tax = _index_taxonomy(taxonomy)
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row
    prows = cur.execute(
        "SELECT shopify_id, handle, title, status, product_type, tags, raw"
        " FROM products ORDER BY shopify_id"
    ).fetchall()
    if not prows:
        raise RuntimeError("no landed products — nothing to audit (fail closed; run the spine's sync first)")
    variants_by_product: dict[str, list] = collections.defaultdict(list)
    for v in cur.execute("SELECT product_id, sku, barcode FROM variants"):
        variants_by_product[v["product_id"]].append(v)

    raws = {r["shopify_id"]: json.loads(r["raw"] or "{}") for r in prows}

    # which raw signals did the sync actually land?
    signals = {k: v for k, v in config["signals"].items() if not k.startswith("_")}
    landed = {
        sig: any(_signal_present(raw, p) for raw in raws.values() for p in paths)
        for sig, paths in signals.items()
    }
    scorable, reasons = {}, {}
    for d, c in dims_cfg.items():
        missing = [s for s in c.get("requires", []) if not landed.get(s)]
        scorable[d] = not missing
        if missing:
            reasons[d] = f"raw signal `{', '.join(missing)}` {NOT_LANDED}"

    blob_keys = set(config.get("spec_blob_keys", []))
    spec_ns = set(config.get("spec_namespaces", ["commerceos"]))
    media_keys = signals.get("media", [])
    min_tags = int(dims_cfg.get("merchandising", {}).get("min_tags", 1))

    results = []
    barcode_kinds: collections.Counter = collections.Counter()
    n_variants = 0
    for r in prows:
        raw = raws[r["shopify_id"]]
        cat, is_fold = resolve_category(r["product_type"], tax)
        tags = json.loads(r["tags"] or "[]")
        vs = variants_by_product.get(r["shopify_id"], [])
        barcodes = [(v["barcode"] or "").strip() for v in vs]
        for b in barcodes:
            barcode_kinds[classify_barcode(b)] += 1
        n_variants += len(vs)
        nodes = (raw.get("metafields") or {}).get("nodes") or []
        specs, prov_ok, vws = _specs_and_provenance(nodes, blob_keys, spec_ns)
        seo = raw.get("seo") or {}

        checks = {
            "classification": cat is not None and cat != "Uncategorized",
            "specs_structured": len(specs) > 0,
            "provenance": prov_ok,
            "identity_gtin": any(gtin_valid(b) for b in barcodes),
            "merchandising": len(tags) >= min_tags,
            "seo": bool(seo.get("title")) and bool(seo.get("description")),
            "images": _has_media(raw, media_keys),
        }
        schema = tax["schema"].get(cat, [])
        results.append({
            "handle": r["handle"], "title": r["title"], "status": r["status"],
            "category": cat, "is_fold": is_fold, "tags_n": len(tags),
            "dims": {d: checks[d] for d in dims_cfg if scorable[d]},
            "coverage": (len([k for k in schema if k in specs]) / len(schema)) if schema else None,
            "verified_without_source": vws,
        })

    total = len(results)
    dim_results = {}
    for d, c in dims_cfg.items():
        if not scorable[d]:
            dim_results[d] = {"weight": c["weight"], "scorable": False, "rate": None,
                              "passed": None, "reason": reasons[d], "note": c.get("note")}
        else:
            passed = sum(1 for r in results if r["dims"][d])
            dim_results[d] = {"weight": c["weight"], "scorable": True,
                              "rate": round(100 * passed / total, 1), "passed": passed,
                              "note": c.get("note")}
    scored_weight = sum(c["weight"] for d, c in dims_cfg.items() if scorable[d])
    overall = round(
        100 * sum(dim_results[d]["passed"] / total * dims_cfg[d]["weight"]
                  for d in dims_cfg if scorable[d]) / scored_weight, 1) if scored_weight else None

    # prioritized backlog: failing count x moat weight, scorable dimensions only
    moat = config.get("moat_weights", {})
    backlog = sorted(
        ({"dimension": d, "failing": total - dim_results[d]["passed"],
          "priority": round((total - dim_results[d]["passed"]) * moat.get(d, 1.0), 1)}
         for d in dims_cfg if scorable[d] and total - dim_results[d]["passed"] > 0),
        key=lambda g: -g["priority"])

    # per-product worst gaps: heaviest failed weight first
    gaps = []
    for r in results:
        fails = [d for d, ok in r["dims"].items() if not ok]
        if fails:
            gaps.append({"handle": r["handle"], "title": r["title"],
                         "failing": sorted(fails, key=lambda d: -dims_cfg[d]["weight"]),
                         "weight": round(sum(dims_cfg[d]["weight"] for d in fails), 2)})
    gaps.sort(key=lambda g: (-g["weight"], g["handle"]))
    worst_gaps = gaps[: int(config.get("worst_gaps", 15))]

    by_cat = collections.defaultdict(list)
    for r in results:
        by_cat[r["category"] or "(unresolved)"].append(r)
    per_category = {}
    for cat, rs in sorted(by_cat.items()):
        row = {"n": len(rs), "fold_rate": round(100 * sum(1 for r in rs if r["is_fold"]) / len(rs), 1)}
        if scorable.get("specs_structured"):
            with_schema = [r for r in rs if r["coverage"] is not None]
            row["spec_coverage"] = round(
                100 * sum(r["coverage"] for r in with_schema) / len(with_schema), 1) if with_schema else None
        per_category[cat] = row

    facts = {
        "identity_barcodes": {"variants": n_variants, **{k: barcode_kinds.get(k, 0) for k in (
            "valid_gtin_as_stored", "apostrophe_wrapped_gtin", "upc_missing_leading_zero",
            "right_length_bad_checksum", "digits_wrong_length", "sku_shaped", "empty")}},
        "folds": sum(1 for r in results if r["is_fold"] and r["category"]),
        "unresolved": sum(1 for r in results if r["category"] is None),
        "no_tags": sum(1 for r in results if r["tags_n"] == 0),
        "status": dict(collections.Counter(r["status"] for r in results)),
    }
    if scorable.get("provenance"):
        facts["verified_without_source"] = sum(len(r["verified_without_source"]) for r in results)

    prior_block = None
    pb = config.get("prior_body")
    if pb:
        pdims = {}
        for d in dims_cfg:
            old = pb.get("dimensions", {}).get(d)
            new = dim_results[d]["rate"]
            pdims[d] = {"prior": old, "now": new,
                        "delta": round(new - old, 1) if (old is not None and new is not None) else None}
        prior_block = {"label": pb.get("label"), "arc": pb.get("arc"), "source": pb.get("source"),
                       "overall_prior": pb.get("overall"), "total_prior": pb.get("total"),
                       "dimensions": pdims}

    prod_keys = sorted(set().union(*(set(r) for r in raws.values()))) if raws else []
    var_keys = sorted({k for r in raws.values()
                       for n in (r.get("variants") or {}).get("nodes") or [] for k in n})

    return {
        "date": time.strftime("%Y-%m-%d"),
        "store": config.get("store"),
        "taxonomy": {"version": taxonomy.get("version"), "status": taxonomy.get("status")},
        "total": total,
        "overall_score": overall,
        "scored_weight": round(scored_weight, 2),
        "scored_dimensions": sum(1 for d in dims_cfg if scorable[d]),
        "configured_dimensions": len(dims_cfg),
        "dimensions": dim_results,
        "landed_raw_keys": {"product": prod_keys, "variant": var_keys},
        "facts": facts,
        "backlog": backlog,
        "worst_gaps": worst_gaps,
        "per_category": per_category,
        "prior_body": prior_block,
    }


def render_report(state: dict, prev: dict | None = None) -> str:
    """the human report. `prev` is the previous run's machine state, for
    run-over-run deltas; the prior-body baseline rides in `state` itself."""
    dims = state["dimensions"]
    scored = {d: v for d, v in dims.items() if v["scorable"]}
    skipped = {d: v for d, v in dims.items() if not v["scorable"]}

    def dlt(cur, key):
        if not prev or cur is None:
            return ""
        old = prev.get("overall_score") if key == "_overall" else (
            (prev.get("dimensions", {}).get(key) or {}).get("rate"))
        if old is None:
            return ""
        d = round(cur - old, 1)
        return f" ({'+' if d >= 0 else ''}{d} vs {prev['date']})" if d else " (no change vs last run)"

    tx = state.get("taxonomy") or {}
    L = [
        f"# catalog health — {state['date']}",
        "",
        f"**overall: {state['overall_score']}/100**{dlt(state['overall_score'], '_overall')} · "
        f"{state['total']} landed products · scored on {len(scored)} of {len(dims)} configured "
        f"dimensions ({round(100 * state['scored_weight'])}% of configured weight; the overall is "
        f"renormalized over what the sync landed) · taxonomy v{tx.get('version')} "
        f"({(tx.get('status') or 'unversioned').split(' — ')[0]})",
        "",
        "> read-only audit of landed facts (the data spine). a dimension whose raw signal the",
        "> sync never requested is listed under \"not scorable yet\" with its weight withheld —",
        "> a sync limitation named as such, never scored zero as if measured.",
        "",
        "## dimensions (pass rate, weighted)",
        "",
    ]
    for d, v in sorted(scored.items(), key=lambda kv: -kv[1]["rate"]):
        L.append(f"- **{d}** — {v['rate']}% ({v['passed']}/{state['total']}, weight {v['weight']})"
                 f"{dlt(v['rate'], d)}")

    if skipped:
        lk = state.get("landed_raw_keys", {})
        L += ["", "## not scorable yet — signal not landed by the current sync", "",
              f"the sync's product payload carries: {', '.join(lk.get('product', []))} · "
              f"variants: {', '.join(lk.get('variant', []))}. these dimensions wait on a wider sync:",
              ""]
        for d, v in sorted(skipped.items(), key=lambda kv: -kv[1]["weight"]):
            L.append(f"- **{d}** (weight {v['weight']} withheld) — {v['reason']}")

    pb = state.get("prior_body")
    if pb:
        L += ["", f"## delta vs the prior body — {pb['label']}", ""]
        if pb.get("arc"):
            L.append(f"{pb['arc']} (source: {pb.get('source')}).")
        L += ["", "| dimension | prior body | this audit | note |", "|---|---:|---:|---|"]
        for d, v in pb["dimensions"].items():
            now = f"{v['now']}%" if v["now"] is not None else "not scorable yet"
            delta = f" ({'+' if v['delta'] >= 0 else ''}{v['delta']})" if v["delta"] is not None else ""
            note = (dims[d].get("note") or "").split(". ")[0].rstrip(".")
            L.append(f"| {d} | {v['prior']}% | {now}{delta} | {note} |")
        L += ["", f"overall: prior body {pb['overall_prior']}/100 across {len(pb['dimensions'])} "
              f"dimensions on {pb['total_prior']} products · this audit {state['overall_score']}/100 "
              f"across {len(scored)} — a narrower basis, shown for the record, not a like-for-like delta."]

    if state["backlog"]:
        L += ["", "## prioritized backlog (failing count × moat weight, scorable dimensions)", ""]
        for g in state["backlog"]:
            L.append(f"- **{g['dimension']}** — {g['failing']} products failing · priority {g['priority']}")

    if state["worst_gaps"]:
        L += ["", f"## worst gaps (top {len(state['worst_gaps'])} products by failed weight)", ""]
        for g in state["worst_gaps"]:
            L.append(f"- `{g['handle']}` — fails {', '.join(g['failing'])} (weight {g['weight']})")

    f = state["facts"]
    ib = f["identity_barcodes"]
    fixable = ib["apostrophe_wrapped_gtin"] + ib["upc_missing_leading_zero"]
    L += ["", "## standing findings", ""]
    gtin_line = (f"- **GTIN**: {ib['valid_gtin_as_stored']}/{ib['variants']} variant barcodes are "
                 f"checksum-valid GTINs as stored.")
    if fixable:
        gtin_line += (f" but {ib['apostrophe_wrapped_gtin']} become valid after stripping a leading "
                      f"apostrophe (a spreadsheet-export artifact) and {ib['upc_missing_leading_zero']} "
                      f"are 11-digit UPCs missing their leading zero — {fixable} of {ib['variants']} "
                      f"({round(100 * fixable / ib['variants'])}%) are one normalization away, not a "
                      f"sourcing project. the prior body read this field as \"barcode = SKU\"; the "
                      f"landed facts say most barcodes are GTINs wearing an artifact.")
    L.append(gtin_line)
    if f["unresolved"]:
        L.append(f"- **unresolved category**: {f['unresolved']} products' product_type maps to no "
                 f"locked category or subcategory — classification drift or new arrivals.")
    L.append(f"- **fold buckets**: {f['folds']} products sit in a \"… — Other\" subcategory "
             f"(under-curated navigation, not a defect).")
    if f["no_tags"]:
        L.append(f"- **untagged**: {f['no_tags']} products carry zero tags — invisible to "
                 f"tag-ruled collections.")
    if "verified_without_source" in f:
        if f["verified_without_source"]:
            L.append(f"- **refuse-to-guess BREACH**: {f['verified_without_source']} spec(s) flagged "
                     f"verified without a source — the provenance invariant must hold; investigate.")
        else:
            L.append(f"- **provenance invariant holds**: 0 specs verified-without-source.")
    L.append("- **status**: " + " · ".join(f"{k.lower()} {v}" for k, v in sorted(f["status"].items()))
             + " (all landed products scored).")

    L += ["", "## per category", ""]
    has_cov = any("spec_coverage" in v for v in state["per_category"].values())
    L.append("| category | n | fold rate |" + (" spec coverage |" if has_cov else ""))
    L.append("|---|---:|---:|" + ("---:|" if has_cov else ""))
    for cat, v in sorted(state["per_category"].items(), key=lambda kv: -kv[1]["n"]):
        row = f"| {cat} | {v['n']} | {v['fold_rate']}% |"
        if has_cov:
            row += f" {v.get('spec_coverage', '-')}% |"
        L.append(row)

    L += ["", "_machine state → reports/health-latest.json (delta-tracked). "
          "read-only audit; no writes._", ""]
    return "\n".join(L)


def write_reports(state: dict, out_dir: Path | str) -> tuple[Path, Path]:
    """write health-<date>.md + health-latest.json; the previous latest (if
    any) feeds the run-over-run deltas before it is replaced."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    latest = out / "health-latest.json"
    prev = None
    if latest.exists():
        try:
            prev = json.loads(latest.read_text())
        except Exception:
            prev = None
    md_path = out / f"health-{state['date']}.md"
    md_path.write_text(render_report(state, prev))
    latest.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    return md_path, latest


def connect_readonly(path: Path | str) -> sqlite3.Connection:
    """open the landed facts read-only — mode=ro makes 'never writes' mechanical."""
    conn = sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="score catalog health from landed facts (read-only)")
    ap.add_argument("--db", default=str(default_db()))
    ap.add_argument("--taxonomy", default=str(default_taxonomy_path()))
    ap.add_argument("--config", default=str(default_config_path()))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)

    conn = connect_readonly(args.db)
    try:
        state = audit(conn, json.loads(Path(args.taxonomy).read_text()),
                      json.loads(Path(args.config).read_text()))
    finally:
        conn.close()
    state["db"] = str(Path(args.db).resolve())
    md_path, json_path = write_reports(state, args.out)
    print(md_path.read_text())
    scored = state["scored_dimensions"]
    print(f"[audit] overall {state['overall_score']}/100 · {state['total']} products · "
          f"{scored}/{state['configured_dimensions']} dimensions scorable · "
          f"report -> {md_path} + {json_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
