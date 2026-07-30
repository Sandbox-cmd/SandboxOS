"""the fleet's first working member — a deterministic proposer.

it reads facts, computes work, and submits every act through the gate:
reversible acts run through the gated write path with verify-rendered
receipts; anything consequential parks for the owner. it holds no API of
its own — the gated connector is its only hands, the same wall as every
future agent. work kinds are pluggable; gtin_normalize is the first.
"""

from __future__ import annotations

from commerceos.gate import gate
from commerceos.spine import writes

AGENT = "catalog-proposer"
FUNCTION = "catalog-enrichment"


# ---- gtin normalization: the first delegated work ----------------------

def gtin_checksum_ok(code: str) -> bool:
    """GTIN-8/12/13/14 mod-10 check."""
    if not code.isdigit() or len(code) not in (8, 12, 13, 14):
        return False
    digits = [int(c) for c in code]
    check = digits.pop()
    # weight pattern: rightmost payload digit always weighs 3
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits)))
    return (10 - total % 10) % 10 == check


def normalize_barcode(raw: str | None) -> str | None:
    """strip spreadsheet artifacts; return a checksum-valid GTIN or None.

    the audit's discovery (2026-07-11): most invalid barcodes wear a
    leading apostrophe, and the rest are UPC-A with the leading zero
    dropped. we repair exactly those two artifacts and accept only what
    then passes the checksum — no invention, ever.
    """
    if not raw:
        return None
    c = raw.strip().lstrip("'").lstrip("’").strip()
    if not c.isdigit():
        return None
    if len(c) == 11:  # UPC-A with dropped leading zero
        c = "0" + c
    if not gtin_checksum_ok(c):
        return None
    return c


def compute_gtin_proposals(conn, limit: int = 50) -> list[dict]:
    """variants whose barcode repairs to a valid GTIN and differs as stored."""
    rows = conn.execute(
        "SELECT v.shopify_id vid, v.product_id pid, v.barcode, v.source"
        " FROM variants v WHERE v.barcode IS NOT NULL AND v.barcode != ''"
        " ORDER BY v.shopify_id").fetchall()
    out = []
    for r in rows:
        fixed = normalize_barcode(r["barcode"])
        if fixed and fixed != r["barcode"]:
            out.append({
                "product_id": r["pid"] if str(r["pid"]).startswith("gid://")
                              else f"gid://shopify/Product/{r['pid']}",
                "variant_id": r["vid"] if str(r["vid"]).startswith("gid://")
                              else f"gid://shopify/ProductVariant/{r['vid']}",
                "field": "barcode", "value": fixed,
                "was": r["barcode"], "provenance": [{"source": r["source"]}],
            })
        if len(out) >= limit:
            break
    return out


WORK_KINDS = {"gtin_normalize": compute_gtin_proposals}


def propose_and_run(conn, kind: str, limit: int = 50, client=None) -> dict:
    """compute -> gate -> (auto) execute with receipts. bounded, honest."""
    compute = WORK_KINDS[kind]
    proposals = compute(conn, limit=limit)
    receipts = {"kind": kind, "computed": len(proposals), "executed": 0,
                "parked": 0, "failed": 0, "records": []}
    for p in proposals:
        res = gate.submit(conn, {
            "agent": AGENT, "function": FUNCTION, "method": "mutate_variant_field",
            "args": {k: p[k] for k in ("product_id", "variant_id", "field", "value")},
            "declared_type": "reversible",
            "intent": f"normalize barcode {p['was']!r} -> {p['value']}",
            "rationale": "spreadsheet-artifact repair; checksum-valid GTIN unlocks machine-surface product matching (C2)",
            "provenance": p["provenance"],
        })
        if res["decision"] == "parked":
            receipts["parked"] += 1
            continue
        try:
            out = writes.execute(conn, res["record_id"], client=client)
            ok = bool(out.get("ok") and out.get("verified_rendered"))
            receipts["executed"] += 1 if ok else 0
            receipts["failed"] += 0 if ok else 1
            receipts["records"].append({"id": res["record_id"][:8], "ok": ok})
        except Exception as e:
            receipts["failed"] += 1
            receipts["records"].append({"id": res["record_id"][:8], "error": str(e)[:120]})
    return receipts
