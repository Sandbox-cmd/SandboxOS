"""carry-over seeds — the fresh-start ruling's operational data.

the ruling carries over product, vendor, customer and other operational
data. products carry via the sync; suppliers carry from the purchase
listing here. customers carry only when the real
store exists (PII goes to Shopify, never here). take rates stay NULL —
they arrive with real contracts (F6), never from history.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from pathlib import Path


def seed_suppliers_from_fta(conn, path: Path | str) -> dict:
    """land supplier names + purchase history shape from the FTA file.

    idempotent: INSERT OR IGNORE on the name; a re-run lands zero new rows.
    """
    path = Path(path)
    raw = path.read_bytes()
    source = f"fta:{path.name}"
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    totals: dict[str, tuple[int, int]] = {}  # name -> (lines, fils)
    in_purchases = False
    header: dict[str, int] | None = None
    for row in csv.reader(io.StringIO(raw.decode("utf-8-sig"))):
        filled = [c.strip() for c in row if c.strip()]
        if not filled:
            continue
        if len(filled) == 1:
            marker = filled[0]
            if "Supplier Purchase Listing" in marker:
                in_purchases, header = True, None
            elif marker.endswith(("Table", "Total")):
                in_purchases = False
            continue
        if not in_purchases:
            continue
        if header is None:
            header = {name.strip(): i for i, name in enumerate(row)}
            continue
        try:
            name = row[header["SupplierName"]].strip()
            fils = int(round(float(row[header["PurchaseValueAED"]].replace(",", "")) * 100))
        except (KeyError, ValueError, IndexError):
            continue
        if not name:
            continue
        lines, total = totals.get(name, (0, 0))
        totals[name] = (lines + 1, total + fils)

    landed = 0
    for name in sorted(totals):
        cur = conn.execute(
            "INSERT OR IGNORE INTO suppliers (name, default_take_rate_bps,"
            " payment_terms, source, fetched_at) VALUES (?, NULL, NULL, ?, ?)",
            (name, source, fetched_at),
        )
        landed += cur.rowcount
    conn.commit()
    return {"suppliers_seen": len(totals), "landed": landed,
            "top": sorted(totals.items(), key=lambda kv: -kv[1][1])[:5]}
