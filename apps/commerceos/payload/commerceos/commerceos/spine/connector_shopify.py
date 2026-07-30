"""the Shopify read paths — the connector lands facts into the spine.

the spine is the sole facts writer; this module is part of the spine.
paged pulls from the Admin GraphQL API land idempotently keyed on
shopify id — a re-run updates, never duplicates. every row carries
source (`shopify:product/<id>@<iso-ts>`) + fetched_at. each order line
splits into take + payable AT LANDING (settlement.split, the
commission-marketplace ruling); the rate applied and the config row
that supplied it land on the line. money converts via Decimal, exactly
— never float. a failed sync lands status=error in sync_state and
re-raises: visible, never half-silent.

order totals convention: net_minor = merchandise net (subtotal after
discounts, before shipping/tax) — the base the settlement splits over;
gross_minor = net + discounts. shipping and tax are pass-throughs.

the product pull is wide (backlog A8): metafields (all namespaces —
the audit decides which bear spec claims), media count + first image
URL, seo title/description, collection titles, descriptionHtml. the
payload lands as-is in products.raw; queryable homes are product_media,
product_meta, and the seo/collections/description_len columns — the
audit scores all 7 dimensions from these landed facts. a THROTTLED
page sleeps and re-requests, bounded (_gql); any other error re-raises.

every landed product is also placed in the lifecycle (CL1c): each page,
after its own commit, calls catalog.lifecycle.set_initial per product so a
brand-new product carries its state the moment it lands — no manual
backfill step. placement is idempotent and never overwrites an operator's
recorded move; an unknown Shopify status fails the sync loudly (the same
never-half-silent law as above).
"""

from __future__ import annotations

import json
import time
from decimal import Decimal
from pathlib import Path

from commerceos import stores
from commerceos.spine.settlement import split
from commerceos.spine.shopify_client import ShopifyClient, ShopifyError

PAGE_SIZE = 50  # products/orders per page; nested connections capped below

# a THROTTLED page is pacing, not failure: sleep (exponential), re-request,
# give up bounded. worst case sleeps 2+4+8+16+32 = 62s, then the re-raise
# lands status=error through the run wrapper like any other failure.
THROTTLE_RETRIES = 5
THROTTLE_BASE_SLEEP = 2.0

# nested first: bounds stay modest for the platform's cost budget (the wide
# page measured 226 requested of a 2000 bucket on the dev store). every
# nested connection carries a fail-closed overflow check — v1 lands whole
# entities only; silent truncation would be a fact wearing a costume.
# the A8 widening: metafields (all namespaces; the audit decides which bear
# specs), media count + first image URL, seo, collections, descriptionHtml.
_PRODUCTS_QUERY = """
query($cursor: String) {
  products(first: 50, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id handle title status vendor productType tags
      descriptionHtml
      seo { title description }
      mediaCount { count }
      featuredMedia { preview { image { url } } }
      collections(first: 10) { pageInfo { hasNextPage } nodes { title } }
      metafields(first: 50) { pageInfo { hasNextPage } nodes { namespace key type value } }
      variants(first: 100) {
        pageInfo { hasNextPage }
        nodes { id sku barcode price inventoryQuantity }
      }
    }
  }
}
"""

_ORDERS_QUERY = """
query($cursor: String) {
  orders(first: 50, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id name createdAt
      customer { id }
      currencyCode
      subtotalPriceSet { shopMoney { amount } }
      totalDiscountsSet { shopMoney { amount } }
      totalShippingPriceSet { shopMoney { amount } }
      totalTaxSet { shopMoney { amount } }
      displayFinancialStatus displayFulfillmentStatus
      lineItems(first: 100) {
        pageInfo { hasNextPage }
        nodes {
          id quantity vendor
          variant { id }
          originalUnitPriceSet { shopMoney { amount } }
          totalDiscountSet { shopMoney { amount } }
          discountedTotalSet { shopMoney { amount } }
        }
      }
    }
  }
}
"""


def load_take_rates(path: Path | str | None = None) -> dict:
    """read the instance take-rate table (default_bps + per-vendor rows)."""
    p = Path(path) if path else stores.resolve(stores.active_store(), "take-rates.json")
    with open(p) as f:
        return json.load(f)


def rate_for(vendor: str | None, rates: dict) -> tuple[int, str]:
    """-> (take_rate_bps, rate_source): the vendor's row when named, else default."""
    vendors = rates.get("vendors") or {}
    if vendor and vendor in vendors:
        return int(vendors[vendor]), f"vendor:{vendor}"
    return int(rates["default_bps"]), "default"


def to_minor(amount) -> int:
    """'164.00' -> 16400. Decimal, exact; a fractional-fils amount raises."""
    minor = Decimal(str(amount)) * 100
    if minor != minor.to_integral_value():
        raise ValueError(f"not a whole minor-unit amount: {amount!r}")
    return int(minor)


def sync_products(conn, client=None) -> dict:
    """paged full pull of products + variants -> upsert keyed on shopify id.

    idempotent: a re-run updates in place, never duplicates. returns counts.
    """
    return _run(conn, "shopify:products", client, _land_products)


def sync_orders(conn, client=None, rates: dict | None = None) -> dict:
    """paged pull of orders -> orders + order_lines, settlement split at landing.

    an empty store lands zero rows and status=ok. returns counts.
    """
    rates = rates or load_take_rates()
    return _run(conn, "shopify:orders", client, lambda c, cl: _land_orders(c, cl, rates))


# ---------- the run wrapper: cursor + last_run + status, never half-silent ----------


def _gql(client, query: str, variables: dict) -> dict:
    """one GraphQL call with bounded backoff on THROTTLED.

    the client raises on every error (fail closed). THROTTLED is the one
    error that is a pacing signal, not a failure — it earns a sleep and a
    re-request, THROTTLE_RETRIES times at most; anything else re-raises at
    once, and an exhausted budget re-raises the last THROTTLED error.
    """
    for attempt in range(THROTTLE_RETRIES + 1):
        try:
            return client.graphql(query, variables)
        except ShopifyError as e:
            if "THROTTLED" not in str(e) or attempt == THROTTLE_RETRIES:
                raise
            time.sleep(THROTTLE_BASE_SLEEP * (2**attempt))
    raise AssertionError("unreachable")  # pragma: no cover


def _run(conn, connector: str, client, land) -> dict:
    client = client or ShopifyClient()
    try:
        counts, cursor = land(conn, client)
    except Exception as e:
        _mark_error(conn, connector, f"{type(e).__name__}: {e}")
        raise
    _mark_ok(conn, connector, cursor)
    return counts


def _mark_ok(conn, connector: str, cursor: str | None) -> None:
    conn.execute(
        "INSERT INTO sync_state (connector, cursor, last_run, status, error)"
        " VALUES (?, ?, ?, 'ok', NULL)"
        " ON CONFLICT(connector) DO UPDATE SET cursor = excluded.cursor,"
        "  last_run = excluded.last_run, status = 'ok', error = NULL",
        (connector, cursor, _utcnow()),
    )
    conn.commit()


def _mark_error(conn, connector: str, error: str) -> None:
    # keeps any prior cursor; records that this run failed, and when
    conn.execute(
        "INSERT INTO sync_state (connector, cursor, last_run, status, error)"
        " VALUES (?, NULL, ?, 'error', ?)"
        " ON CONFLICT(connector) DO UPDATE SET"
        "  last_run = excluded.last_run, status = 'error', error = excluded.error",
        (connector, _utcnow(), error),
    )
    conn.commit()


# ---------- products ----------


def _whole(node: dict, key: str, pid: str, bound: str) -> dict:
    """a nested connection, refused if truncated — whole entities only."""
    c = node.get(key) or {}
    if (c.get("pageInfo") or {}).get("hasNextPage"):
        raise ShopifyError(
            f"{key} overflow on {pid}: >{bound} {key}; v1 lands whole products only"
        )
    return c


def _land_products(conn, client) -> tuple[dict, str | None]:
    products = variants = metafields = 0
    cursor = None
    while True:
        page = _gql(client, _PRODUCTS_QUERY, {"cursor": cursor})["products"]
        fetched_at = _utcnow()
        page_statuses: list[tuple[str, str | None]] = []
        for node in page["nodes"]:
            pid = node["id"]
            page_statuses.append((pid, node.get("status")))
            vconn = _whole(node, "variants", pid, "100")
            mconn = _whole(node, "metafields", pid, "50")
            cconn = _whole(node, "collections", pid, "10")
            seo = node.get("seo") or {}
            desc = node.get("descriptionHtml")
            src = f"shopify:product/{_id_tail(pid)}@{fetched_at}"
            conn.execute(
                "INSERT INTO products (shopify_id, handle, title, status, vendor,"
                " product_type, tags, seo_title, seo_description, collections,"
                " description_len, raw, source, fetched_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(shopify_id) DO UPDATE SET"
                "  handle = excluded.handle, title = excluded.title,"
                "  status = excluded.status, vendor = excluded.vendor,"
                "  product_type = excluded.product_type, tags = excluded.tags,"
                "  seo_title = excluded.seo_title,"
                "  seo_description = excluded.seo_description,"
                "  collections = excluded.collections,"
                "  description_len = excluded.description_len,"
                "  raw = excluded.raw, source = excluded.source,"
                "  fetched_at = excluded.fetched_at",
                (
                    pid,
                    node.get("handle"),
                    node.get("title"),
                    node.get("status"),
                    node.get("vendor"),
                    node.get("productType"),
                    json.dumps(node.get("tags") or []),
                    seo.get("title"),
                    seo.get("description"),
                    json.dumps([c.get("title") for c in cconn.get("nodes") or []]),
                    len(desc) if desc is not None else None,
                    json.dumps(node),
                    src,
                    fetched_at,
                ),
            )
            products += 1
            # one media row per product, upserted: count + the first image URL
            conn.execute(
                "INSERT INTO product_media (product_id, media_count,"
                " first_image_url, source, fetched_at)"
                " VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(product_id) DO UPDATE SET"
                "  media_count = excluded.media_count,"
                "  first_image_url = excluded.first_image_url,"
                "  source = excluded.source, fetched_at = excluded.fetched_at",
                (
                    pid,
                    (node.get("mediaCount") or {}).get("count") or 0,
                    _first_image_url(node),
                    src,
                    fetched_at,
                ),
            )
            # metafields: replace the product's rows whole (the order_lines
            # pattern) — a metafield deleted on Shopify disappears here too.
            conn.execute("DELETE FROM product_meta WHERE product_id = ?", (pid,))
            for m in mconn.get("nodes") or []:
                conn.execute(
                    "INSERT INTO product_meta (product_id, namespace, key,"
                    " type, value, source, fetched_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (pid, m.get("namespace"), m.get("key"), m.get("type"),
                     m.get("value"), src, fetched_at),
                )
                metafields += 1
            for v in vconn.get("nodes") or []:
                vid = v["id"]
                conn.execute(
                    "INSERT INTO variants (shopify_id, product_id, sku, barcode,"
                    " price_minor, inventory, source, fetched_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                    " ON CONFLICT(shopify_id) DO UPDATE SET"
                    "  product_id = excluded.product_id, sku = excluded.sku,"
                    "  barcode = excluded.barcode, price_minor = excluded.price_minor,"
                    "  inventory = excluded.inventory, source = excluded.source,"
                    "  fetched_at = excluded.fetched_at",
                    (
                        vid,
                        pid,
                        v.get("sku"),
                        v.get("barcode"),
                        to_minor(v["price"]) if v.get("price") is not None else None,
                        v.get("inventoryQuantity"),
                        f"shopify:variant/{_id_tail(vid)}@{fetched_at}",
                        fetched_at,
                    ),
                )
                variants += 1
        conn.commit()  # a page landed whole; a later failure re-runs idempotently
        # a new product carries its lifecycle state the moment it exists — no
        # manual backfill step. set_initial short-circuits placed products, so
        # a re-sync never duplicates a row or stomps an operator's recorded
        # move (CL1c). the fallback mirrors backfill_from_products' own.
        from commerceos.catalog import lifecycle
        for pid, status in page_statuses:
            lifecycle.set_initial(conn, pid, status or "ACTIVE")
        cursor = page["pageInfo"].get("endCursor")
        if not page["pageInfo"]["hasNextPage"]:
            return {"products": products, "variants": variants, "metafields": metafields}, cursor


# ---------- orders ----------


def _land_orders(conn, client, rates: dict) -> tuple[dict, str | None]:
    orders = lines = 0
    cursor = None
    while True:
        page = _gql(client, _ORDERS_QUERY, {"cursor": cursor})["orders"]
        fetched_at = _utcnow()
        for node in page["nodes"]:
            oid = node["id"]
            liconn = node.get("lineItems") or {}
            if (liconn.get("pageInfo") or {}).get("hasNextPage"):
                raise ShopifyError(
                    f"line-item overflow on {oid}: >100 lines; v1 lands whole orders only"
                )
            net = _money(node.get("subtotalPriceSet"))
            discount = _money(node.get("totalDiscountsSet"))
            conn.execute(
                "INSERT INTO orders (shopify_id, number, placed_at, customer_ref,"
                " currency, gross_minor, discount_minor, shipping_minor, tax_minor,"
                " net_minor, financial_status, fulfillment_status, source, fetched_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(shopify_id) DO UPDATE SET"
                "  number = excluded.number, placed_at = excluded.placed_at,"
                "  customer_ref = excluded.customer_ref, currency = excluded.currency,"
                "  gross_minor = excluded.gross_minor,"
                "  discount_minor = excluded.discount_minor,"
                "  shipping_minor = excluded.shipping_minor,"
                "  tax_minor = excluded.tax_minor, net_minor = excluded.net_minor,"
                "  financial_status = excluded.financial_status,"
                "  fulfillment_status = excluded.fulfillment_status,"
                "  source = excluded.source, fetched_at = excluded.fetched_at",
                (
                    oid,
                    node.get("name"),
                    node.get("createdAt"),
                    (node.get("customer") or {}).get("id"),  # reference only; PII stays in Shopify
                    node.get("currencyCode") or "AED",
                    net + discount,
                    discount,
                    _money(node.get("totalShippingPriceSet")),
                    _money(node.get("totalTaxSet")),
                    net,
                    node.get("displayFinancialStatus"),
                    node.get("displayFulfillmentStatus"),
                    f"shopify:order/{_id_tail(oid)}@{fetched_at}",
                    fetched_at,
                ),
            )
            # lines have no natural key -> replace the order's lines whole.
            # safe while nothing references them (returns land in a later item).
            conn.execute("DELETE FROM order_lines WHERE order_id = ?", (oid,))
            for li in liconn.get("nodes") or []:
                line_net = _money(li.get("discountedTotalSet"))
                bps, rate_source = rate_for(li.get("vendor"), rates)
                take, payable = split(line_net, bps)
                conn.execute(
                    "INSERT INTO order_lines (order_id, variant_id, vendor, qty,"
                    " unit_price_minor, discount_minor, net_minor,"
                    " take_rate_bps, take_minor, payable_minor, rate_source)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        oid,
                        (li.get("variant") or {}).get("id"),
                        li.get("vendor"),
                        li["quantity"],
                        _money(li.get("originalUnitPriceSet")),
                        _money(li.get("totalDiscountSet")),
                        line_net,
                        bps,
                        take,
                        payable,
                        rate_source,
                    ),
                )
                lines += 1
            orders += 1
        conn.commit()
        cursor = page["pageInfo"].get("endCursor")
        if not page["pageInfo"]["hasNextPage"]:
            return {"orders": orders, "lines": lines}, cursor


# ---------- small helpers ----------


def _money(money_set: dict | None) -> int:
    """a Shopify MoneyBag -> integer minor units; an absent bag is 0."""
    if not money_set:
        return 0
    return to_minor(money_set["shopMoney"]["amount"])


def _first_image_url(node: dict) -> str | None:
    """featuredMedia's preview image URL — None when the product has no media."""
    return ((((node.get("featuredMedia") or {}).get("preview")) or {}).get("image") or {}).get("url")


def _id_tail(gid: str) -> str:
    """'gid://shopify/Product/1001' -> '1001' (source-ref shape per the spec)."""
    return gid.rsplit("/", 1)[-1]


def _utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def writeback_variant_barcode(conn, variant_id: str, barcode: str) -> int:
    """update the local barcode fact after a VERIFIED store write.

    the spine owns the variants facts table (one writer per table-set), so a
    workflow that fixed a barcode on the store routes the store-verified value
    back through here — the audit, the progress card, and the feed read truth
    without waiting for the next full sync. only a value the store already read
    back should reach this; the source marks it as a verified write-back, not a
    fresh sync. returns the row count updated (0 if the variant is unknown)."""
    fetched_at = _utcnow()
    cur = conn.execute(
        "UPDATE variants SET barcode = ?, source = ?, fetched_at = ?"
        " WHERE shopify_id = ?",
        (barcode, f"writeback:verified@{fetched_at}", fetched_at, variant_id),
    )
    conn.commit()
    return cur.rowcount


def writeback_product_seo(conn, product_id: str, title: str | None,
                          description: str | None) -> int:
    """update the local listing facts after a VERIFIED store write.

    the spine owns the products facts table (one writer per table-set), so the
    listing-text workflow that wrote a product's search listing on the store
    routes the store-verified title/description back through here — the weak-
    listing rule, the progress card, and the feed read truth without waiting for
    the next full sync. only values the store already read back should reach
    this; the source marks it a verified write-back, not a fresh sync. a None
    value leaves that column as it stands (never nulls what an earlier fact
    landed). returns the row count updated (0 if the product is unknown)."""
    fetched_at = _utcnow()
    cur = conn.execute(
        "UPDATE products SET"
        "  seo_title = COALESCE(?, seo_title),"
        "  seo_description = COALESCE(?, seo_description),"
        "  source = ?, fetched_at = ?"
        " WHERE shopify_id = ?",
        (title, description, f"writeback:verified@{fetched_at}", fetched_at,
         product_id),
    )
    conn.commit()
    return cur.rowcount


def writeback_product_metafield(
    conn, product_id: str, namespace: str, key: str, value: str,
    type_: str = "single_line_text_field",
) -> int:
    """upsert a product metafield fact after a VERIFIED store write.

    the spine owns the product_meta facts table (one writer per table-set), so a
    workflow that set a metafield on the store (e.g. classification writing
    commerceos.category) routes the store-verified value back through here — the
    audit, the progress card, and the feed read truth without waiting for the
    next full sync. only a value the store already read back should reach this;
    the source marks it a verified write-back, not a fresh sync. mirrors the
    sync's own INSERT ... ON CONFLICT on (product_id, namespace, key). returns
    the row count written."""
    fetched_at = _utcnow()
    cur = conn.execute(
        "INSERT INTO product_meta (product_id, namespace, key, type, value,"
        " source, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(product_id, namespace, key) DO UPDATE SET"
        "  type = excluded.type, value = excluded.value,"
        "  source = excluded.source, fetched_at = excluded.fetched_at",
        (product_id, namespace, key, type_, value,
         f"writeback:verified@{fetched_at}", fetched_at),
    )
    conn.commit()
    return cur.rowcount
