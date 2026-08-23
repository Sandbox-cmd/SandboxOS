"""A6 — the S1 proof, live against the dev store.

one reversible auto write + one consequential approve->execute->outcome,
every step on the record, both reverted, receipts printed. the approver
is labeled session:a6-proof — the record never claims the owner pressed.
run: uv run python scripts/a6_prove.py
"""

import json
import os

from fastapi.testclient import TestClient

from commerceos.db import connect
from commerceos.gate import gate, ledger
from commerceos.spine import writes
from commerceos.spine.shopify_client import ShopifyClient, credentials_available

DB = os.environ.get("COMMERCEOS_DB")
conn = connect(DB)
ledger.ensure_schema(conn)
assert credentials_available(), "no Keychain credentials — A6 live proof needs the dev store"
client = ShopifyClient()

# pick a real, cheap product with one variant from landed facts
row = conn.execute(
    "SELECT p.shopify_id pid, p.title, p.tags, v.shopify_id vid, v.price_minor"
    " FROM products p JOIN variants v ON v.product_id = p.shopify_id"
    " WHERE p.status='ACTIVE' ORDER BY v.price_minor ASC LIMIT 1").fetchone()
def _gid(val, kind):
    return val if str(val).startswith("gid://") else f"gid://shopify/{kind}/{val}"
pid = _gid(row["pid"], "Product")
vid = _gid(row["vid"], "ProductVariant")
tags0 = json.loads(row["tags"] or "[]")
price0 = f"{row['price_minor'] // 100}.{row['price_minor'] % 100:02d}"
print(f"subject: {row['title']} ({pid}) variant {vid} · tags={len(tags0)} · price={price0}")

receipts = {}

# ---- leg 1: reversible auto — tag append, then revert -----------------
def tag_cycle(tags, intent):
    res = gate.submit(conn, {
        "agent": "session:a6-proof", "function": "catalog-enrichment",
        "method": "mutate_product_field",
        "args": {"product_id": pid, "field": "tags", "value": tags},
        "declared_type": "reversible", "intent": intent,
        "rationale": "A6 S1 proof — reversible lane", "provenance": [{"source": f"facts:products/{row['pid']}"}],
    })
    assert res["decision"] == "allow", res
    out = writes.execute(conn, res["record_id"], client=client)
    assert out["ok"] and out["verified_rendered"], out
    return res["record_id"], out

rid1, out1 = tag_cycle(tags0 + ["commerceos-a6-proof"], "append the A6 proof tag")
rid1b, out1b = tag_cycle(tags0, "revert the A6 proof tag")
receipts["reversible"] = {"apply": rid1, "revert": rid1b,
                          "tags_after_revert": len(out1b["tags"])}
print(f"leg 1 ok: reversible applied {rid1[:8]} + reverted {rid1b[:8]}, rendered both times")

# ---- leg 2: consequential — price +1.00 via the web's only approve verb, then revert
app_client = TestClient(__import__("commerceos.web.app", fromlist=["app"]).app)
p_minor = row["price_minor"] + 100
price1 = f"{p_minor // 100}.{p_minor % 100:02d}"

def price_cycle(price, intent):
    res = gate.submit(conn, {
        "agent": "session:a6-proof", "function": "pricing", "method": "mutate_price",
        "args": {"product_id": pid, "variant_id": vid, "price": price},
        "declared_type": "consequential", "intent": intent,
        "rationale": "A6 S1 proof — consequential lane",
        "impact": {"money_minor": 100},
    })
    assert res["decision"] == "parked", res
    rid = res["record_id"]
    # visible in the queue before approval
    q = app_client.get("/approvals"); assert intent in q.text
    r = app_client.post(f"/api/approvals/{rid}",
                        json={"decision": "approved", "confirm": True, "by": "session:a6-proof"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["outcome"]["ok"] and body["record"]["status"] == "executed", body
    return rid, body

rid2, body2 = price_cycle(price1, f"reprice to {price1} (A6 proof)")
rid2b, body2b = price_cycle(price0, f"revert price to {price0} (A6 proof)")
receipts["consequential"] = {"apply": rid2, "revert": rid2b,
                             "price_after_revert": body2b["outcome"]["price"]}
print(f"leg 2 ok: parked, approved via the web verb, executed {rid2[:8]}, reverted {rid2b[:8]}")

# ---- receipts: the record + the surfaces ------------------------------
rec_page = app_client.get("/record").text
for rid in (rid1, rid1b, rid2, rid2b):
    assert ledger.get(conn, rid)["status"] == "executed"
assert "mutate_price" in rec_page and "mutate_product_field" in rec_page
parts_page = app_client.get("/parts").text
for part in ("data-spine", "gate-and-record", "web-surface"):
    assert part in parts_page, f"{part} missing from /parts"
track = ledger.track_record(conn, "pricing")
print("track record (pricing):", json.dumps(track))
print("A6 PROOF COMPLETE — four executed records on the ledger, store reverted, surfaces render.")
print(json.dumps(receipts, indent=1))
