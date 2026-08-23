"""the gated write path — the only door to the world.

execute(conn, record_id) runs an APPROVED ledger record's exact stored
proposal: the one-use handle is validated and consumed BEFORE any network
call (no valid handle, no write — fail closed); the mutation runs; the
world is read back; the outcome lands on that same record. idempotent by
construction: the handle consumes exactly once, so a replay is refused at
the wall, not by convention.

V1 methods: mutate_product_field (tags | title | a commerceos metafield),
mutate_price. both verify rendered: the read-back value is the receipt.
"""

from __future__ import annotations

import json

from commerceos.gate import handles, ledger
from commerceos.spine.shopify_client import ShopifyClient

_PRODUCT_FIELD_MUTATION = """
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id tags title }
    userErrors { field message }
  }
}
"""

_METAFIELD_MUTATION = """
mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { id namespace key value }
    userErrors { field message }
  }
}
"""

_PRICE_MUTATION = """
mutation variantUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants { id price }
    userErrors { field message }
  }
}
"""

_READBACK_PRODUCT = """
query product($id: ID!) { product(id: $id) { id tags title } }
"""

_READBACK_VARIANT = """
query variant($id: ID!) { node(id: $id) { ... on ProductVariant { id price } } }
"""


class WriteRefused(RuntimeError):
    """the wall spoke: no valid handle, no write."""


def execute(conn, record_id: str, client: ShopifyClient | None = None) -> dict:
    """run an approved record's stored proposal. returns the outcome dict."""
    rec = ledger.get(conn, record_id)
    if rec is None:
        raise KeyError(f"no ledger record {record_id}")
    prop = rec["proposal"]
    method, args = prop["method"], prop["args"]

    # the wall, two lanes, one law — no valid ceremony, no write:
    # auto lane: submit() minted AND consumed the handle in one motion; the
    # record arrives "executing" with a consumed handle as the proof.
    # approved lane: resolve() minted the handle; consume it here, which
    # also moves the record approved -> executing in the same transaction.
    status = rec["status"]
    if status == "executing":
        h = handles.get(conn, record_id)
        if not h or not h.get("consumed_at"):
            raise WriteRefused("executing without a consumed handle — refused")
    elif status == "approved":
        took = handles.validate_and_consume(conn, record_id, method, args)
        if not took["ok"]:
            raise WriteRefused(took["reason"])
    else:
        raise WriteRefused(f"record is {status} — only approved or executing may execute")

    try:
        if method == "mutate_spec_verification":
            # CW7 (ruled 2026-07-12/18): a LOCAL provenance flip — no store
            # client is ever constructed on this branch, by design.
            outcome = _mutate_spec_verification(args)
        elif method == "record_supplier":
            # SP1: supplier + purchase-order facts land LOCALLY — the store
            # is never touched; no client on this branch either.
            outcome = _record_supplier(conn, args)
        else:
            client = client or ShopifyClient()
            if method == "mutate_product_field":
                outcome = _mutate_product_field(client, args)
            elif method == "mutate_variant_field":
                outcome = _mutate_variant_field(client, args)
            elif method == "mutate_price":
                outcome = _mutate_price(client, args)
            elif method == "mutate_product_state":
                outcome = _mutate_product_state(client, args)
            elif method == "mutate_seo":
                outcome = _mutate_seo(client, args)
            elif method == "create_collection":
                outcome = _create_collection(client, args)
            elif method == "mutate_menu":
                outcome = _mutate_menu(client, args)
            else:
                raise WriteRefused(f"no executor for method {method}")
    except Exception as e:
        out = {"ok": False, "error": str(e)[:500]}
        ledger.fill_outcome(conn, record_id, out, status="failed")
        raise
    ledger.fill_outcome(conn, record_id, outcome, status="executed")
    ledger.emit_event(conn, "write.executed", actor=rec["agent"], subject=record_id,
                      payload={"method": method, "ok": outcome.get("ok", True)})
    return outcome


def _errs(payload: dict, key: str) -> list:
    return (payload.get(key) or {}).get("userErrors") or []


def _mutate_product_field(client: ShopifyClient, args: dict) -> dict:
    pid = args["product_id"]
    field = args["field"]
    value = args["value"]
    if field == "tags":
        data = client.graphql(_PRODUCT_FIELD_MUTATION,
                              {"input": {"id": pid, "tags": value}})
        if _errs(data, "productUpdate"):
            return {"ok": False, "error": json.dumps(_errs(data, "productUpdate"))}
        back = client.graphql(_READBACK_PRODUCT, {"id": pid})["product"]
        rendered = sorted(back["tags"]) == sorted(value if isinstance(value, list) else [value])
        return {"ok": rendered, "verified_rendered": rendered, "tags": back["tags"]}
    if field == "title":
        data = client.graphql(_PRODUCT_FIELD_MUTATION,
                              {"input": {"id": pid, "title": value}})
        if _errs(data, "productUpdate"):
            return {"ok": False, "error": json.dumps(_errs(data, "productUpdate"))}
        back = client.graphql(_READBACK_PRODUCT, {"id": pid})["product"]
        rendered = back["title"] == value
        return {"ok": rendered, "verified_rendered": rendered, "title": back["title"]}
    if field.startswith("commerceos."):
        key = field.split(".", 1)[1]
        data = client.graphql(_METAFIELD_MUTATION, {"metafields": [{
            "ownerId": pid, "namespace": "commerceos", "key": key,
            "type": "single_line_text_field", "value": str(value)}]})
        if _errs(data, "metafieldsSet"):
            return {"ok": False, "error": json.dumps(_errs(data, "metafieldsSet"))}
        got = (data.get("metafieldsSet") or {}).get("metafields") or []
        rendered = bool(got) and got[0]["value"] == str(value)
        return {"ok": rendered, "verified_rendered": rendered, "metafield": got[0] if got else None}
    return {"ok": False, "error": f"unsupported field {field} (fit-critical fields arrive with the catalog loop)"}


# listing text (S1, built 2026-07-18) — the executor CW6's content feature
# rides. writes the product's search listing (title/description shown to
# search engines and the feed), reads it back as the receipt. the facts
# write-through (products.seo_title/seo_description) belongs to the spine's
# writeback lane, recorded by the caller on this receipt — same division
# as every other executor.
_SEO_MUTATION = """
mutation productSeo($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id seo { title description } }
    userErrors { field message }
  }
}
"""

_READBACK_SEO = """
query productSeo($id: ID!) { product(id: $id) { id seo { title description } } }
"""


def _mutate_seo(client: ShopifyClient, args: dict) -> dict:
    pid = args["product_id"]
    seo = {}
    if args.get("title") is not None:
        seo["title"] = args["title"]
    if args.get("description") is not None:
        seo["description"] = args["description"]
    if not seo:
        return {"ok": False, "error": "mutate_seo needs a title or a description"}
    data = client.graphql(_SEO_MUTATION, {"input": {"id": pid, "seo": seo}})
    if _errs(data, "productUpdate"):
        return {"ok": False, "error": json.dumps(_errs(data, "productUpdate"))}
    back = (client.graphql(_READBACK_SEO, {"id": pid})["product"] or {}).get("seo") or {}
    rendered = all(back.get(k) == v for k, v in seo.items())
    return {"ok": rendered, "verified_rendered": rendered, "seo": back}


def _mutate_price(client: ShopifyClient, args: dict) -> dict:
    data = client.graphql(_PRICE_MUTATION, {
        "productId": args["product_id"],
        "variants": [{"id": args["variant_id"], "price": args["price"]}],
    })
    if _errs(data, "productVariantsBulkUpdate"):
        return {"ok": False, "error": json.dumps(_errs(data, "productVariantsBulkUpdate"))}
    back = client.graphql(_READBACK_VARIANT, {"id": args["variant_id"]})["node"]
    rendered = back and str(back["price"]) == str(args["price"])
    return {"ok": bool(rendered), "verified_rendered": bool(rendered),
            "price": back["price"] if back else None}


_VARIANT_FIELD_MUTATION = """
mutation variantField($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants { id barcode }
    userErrors { field message }
  }
}
"""

_READBACK_VARIANT_BARCODE = """
query variant($id: ID!) { node(id: $id) { ... on ProductVariant { id barcode } } }
"""


def _mutate_variant_field(client: ShopifyClient, args: dict) -> dict:
    field = args["field"]
    if field != "barcode":
        return {"ok": False, "error": f"unsupported variant field {field}"}
    data = client.graphql(_VARIANT_FIELD_MUTATION, {
        "productId": args["product_id"],
        "variants": [{"id": args["variant_id"], "barcode": args["value"]}],
    })
    if _errs(data, "productVariantsBulkUpdate"):
        return {"ok": False, "error": json.dumps(_errs(data, "productVariantsBulkUpdate"))}
    back = client.graphql(_READBACK_VARIANT_BARCODE, {"id": args["variant_id"]})["node"]
    rendered = back and back.get("barcode") == args["value"]
    return {"ok": bool(rendered), "verified_rendered": bool(rendered),
            "barcode": back.get("barcode") if back else None}


# spec verification (CW7) — the LOCAL provenance flip. this executor makes
# no network call and constructs no client: it validates the approved
# claims payload and returns the instruction receipt. the flip itself is
# recorded by catalog-loop's own writer (canonical.record_verification) on
# this receipt, and the render check runs after — the one-writer division
# ruled 2026-07-12 (catalog-workflows.md behavior 3): this executor never
# writes catalog-loop's tables itself.
def _mutate_spec_verification(args: dict) -> dict:
    claims = ((args.get("value") or {}).get("claims")) or []
    if not claims:
        return {"ok": False, "error": "no claims in the approved proposal"}
    flips, conflicts, not_found = [], 0, 0
    for c in claims:
        verdict = c.get("verdict")
        if verdict == "agree":
            src = (c.get("source_url") or "").strip()
            if not src:
                # no source on an approved claim is a construction failure
                raise WriteRefused(
                    f"claim {c.get('field')}: agree without a source — refused"
                    " (no source, no claim)")
            flips.append({"product": args["product_id"], "field": c["field"],
                          "value": c["value"], "source": src})
        elif verdict == "disagree":
            conflicts += 1   # stated for the ruling, never resolved
        else:
            not_found += 1   # nothing found is nothing flipped
    return {"ok": True, "local": True, "flips": flips,
            "conflicts_stated": conflicts, "not_found": not_found}


# product state (delist / relist / archive) — the lifecycle store write.
# the local state field + history row are written by catalog-lifecycle (the
# one-writer-per-table-set rule); THIS executor only flips the store status
# and returns the verified receipt for lifecycle to commit on. the target
# lifecycle state maps onto Shopify's product status (catalog-lifecycle.md):
# active -> ACTIVE, delisted -> DRAFT, archived -> ARCHIVED. relist is just
# state="active" on a delisted product — the executor is state-agnostic.
_STATE_TO_STATUS = {"active": "ACTIVE", "delisted": "DRAFT", "archived": "ARCHIVED"}

_PRODUCT_STATE_MUTATION = """
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id status }
    userErrors { field message }
  }
}
"""

_READBACK_PRODUCT_STATUS = """
query productStatus($id: ID!) { product(id: $id) { id status } }
"""


def _mutate_product_state(client: ShopifyClient, args: dict) -> dict:
    pid = args["product_id"]
    state = args["state"]
    target = _STATE_TO_STATUS.get(state)
    if target is None:
        return {"ok": False,
                "error": f"unsupported state {state} (want one of {sorted(_STATE_TO_STATUS)})"}
    data = client.graphql(_PRODUCT_STATE_MUTATION,
                          {"input": {"id": pid, "status": target}})
    if _errs(data, "productUpdate"):
        return {"ok": False, "error": json.dumps(_errs(data, "productUpdate"))}
    back = client.graphql(_READBACK_PRODUCT_STATUS, {"id": pid})["product"]
    status = back.get("status") if back else None
    rendered = status == target
    return {"ok": rendered, "verified_rendered": rendered, "status": status}


# ---------- SP1: supplier + purchase-order facts, landed locally ----------
# the spine is the facts tables' sole writer; this executor is the one door
# hand-entered supplier facts come through — always via an approved gate
# record, never a direct write from the web. read-back is the receipt: the
# rows are re-selected after the write and returned.
def _record_supplier(conn, args: dict) -> dict:
    from datetime import datetime, timezone

    sup = args.get("supplier") or {}
    name = (sup.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "a supplier fact carries a name"}
    source = args.get("source") or "operator:web-form"
    if not source.startswith("operator:"):
        return {"ok": False, "error": "hand-entered facts carry operator: provenance"}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # an existing name updates terms; a missing value never nulls what an
    # earlier approval landed (the producer's cold read, finding 5).
    conn.execute(
        "INSERT INTO suppliers (name, default_take_rate_bps, payment_terms,"
        " source, fetched_at) VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(name) DO UPDATE SET"
        " default_take_rate_bps = COALESCE(excluded.default_take_rate_bps,"
        "                                  suppliers.default_take_rate_bps),"
        " payment_terms = COALESCE(excluded.payment_terms, suppliers.payment_terms),"
        " source = excluded.source, fetched_at = excluded.fetched_at",
        (name, sup.get("default_take_rate_bps"), sup.get("payment_terms"),
         source, now))
    po = args.get("purchase_order") or {}
    po_landed = None
    if po:
        po_id = (po.get("id") or "").strip()
        lines = po.get("lines") or []
        if not po_id:
            return {"ok": False, "error": "a purchase order carries an id"}
        if not lines:
            return {"ok": False, "error": "a purchase order carries at least one line"}
        for ln in lines:
            qty, cost = ln.get("qty"), ln.get("unit_cost_minor")
            if not (isinstance(qty, int) and qty > 0
                    and isinstance(cost, int) and cost >= 0):
                return {"ok": False,
                        "error": "each line carries qty (> 0) and unit cost in fils (>= 0)"}
        existing = conn.execute("SELECT supplier FROM purchase_orders WHERE id = ?",
                                (po_id,)).fetchone()
        if existing and existing["supplier"] != name:
            return {"ok": False,
                    "error": f"purchase order {po_id} belongs to {existing['supplier']}"
                             f" — one po, one supplier"}
        # a repeat id APPENDS its line — approved money facts are never
        # deleted by a later entry (the cold read's finding 2).
        conn.execute(
            "INSERT INTO purchase_orders (id, supplier, status, created_at,"
            " source, fetched_at) VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " status = excluded.status, fetched_at = excluded.fetched_at",
            (po_id, name, po.get("status") or "open",
             po.get("created_at") or now[:10], source, now))
        for ln in lines:
            conn.execute(
                "INSERT INTO po_lines (po_id, variant_id, qty, unit_cost_minor)"
                " VALUES (?, ?, ?, ?)",
                (po_id, ln.get("variant_id"), ln["qty"], ln["unit_cost_minor"]))
        po_landed = po_id
    conn.commit()
    # the read-back receipt — what the tables now actually hold.
    srow = conn.execute("SELECT * FROM suppliers WHERE name = ?", (name,)).fetchone()
    receipt = {"ok": True, "supplier": dict(srow), "verified_rendered": True}
    if po_landed:
        receipt["purchase_order"] = dict(conn.execute(
            "SELECT * FROM purchase_orders WHERE id = ?", (po_landed,)).fetchone())
        receipt["po_lines"] = [dict(r) for r in conn.execute(
            "SELECT * FROM po_lines WHERE po_id = ?", (po_landed,))]
    return receipt


# ---------- CW4: the smart-collection create (the write CW5 merchandising needs) ----------
# a new gated method on the ONE door — mutation + read-back + verified_rendered
# in the one body, the same discipline as _mutate_seo. gate class REVERSIBLE
# (a collection deletes cleanly), REGISTERED deliberately in the policy floor
# and the store's table so the fail-safe never silently parks it fit-critical.
#
# the async-membership trap (scout finding): Shopify computes smart-collection
# membership asynchronously AFTER a ruleSet create — the member count is not
# settled at the create receipt. so the receipt verifies what IS true at write
# time: the collection exists and reads back with our title and our exact
# rules. membership settling is a SEPARATE live check, CW5's concern, not this
# executor's receipt (create verified != membership settled).
_COLLECTION_CREATE_MUTATION = """
mutation collectionCreate($input: CollectionInput!) {
  collectionCreate(input: $input) {
    collection {
      id handle title
      ruleSet { appliedDisjunctively rules { column relation condition } }
    }
    userErrors { field message }
  }
}
"""

_READBACK_COLLECTION = """
query collection($id: ID!) {
  collection(id: $id) {
    id handle title
    ruleSet { appliedDisjunctively rules { column relation condition } }
  }
}
"""


def _norm_rules(rules: list) -> list:
    """the rules we sent, normalized for an order-independent compare with the
    live read-back. each rule is (column, relation, condition)."""
    out = []
    for r in rules or []:
        out.append((str(r.get("column")), str(r.get("relation")), str(r.get("condition"))))
    return sorted(out)


def _create_collection(client: ShopifyClient, args: dict) -> dict:
    title = (args.get("title") or "").strip()
    if not title:
        return {"ok": False, "error": "a collection carries a title"}
    rules = args.get("rules") or []
    if not rules:
        return {"ok": False,
                "error": "a smart collection carries at least one membership rule"}
    for r in rules:
        if not (r.get("column") and r.get("relation") and r.get("condition") is not None):
            return {"ok": False,
                    "error": "each rule carries a column, a relation, and a condition"}
    ci: dict = {"title": title, "ruleSet": {
        "appliedDisjunctively": bool(args.get("applied_disjunctively", False)),
        "rules": [{"column": r["column"], "relation": r["relation"],
                   "condition": r["condition"]} for r in rules],
    }}
    if args.get("handle"):
        ci["handle"] = args["handle"]
    if args.get("description_html") is not None:
        ci["descriptionHtml"] = args["description_html"]
    data = client.graphql(_COLLECTION_CREATE_MUTATION, {"input": ci})
    if _errs(data, "collectionCreate"):
        return {"ok": False, "error": json.dumps(_errs(data, "collectionCreate"))}
    made = (data.get("collectionCreate") or {}).get("collection")
    if not made:
        return {"ok": False, "error": "collectionCreate returned no collection"}
    back = client.graphql(_READBACK_COLLECTION, {"id": made["id"]}).get("collection")
    sent = _norm_rules(ci["ruleSet"]["rules"])
    got = _norm_rules(((back or {}).get("ruleSet") or {}).get("rules"))
    rendered = bool(back) and back.get("title") == title and got == sent
    return {"ok": rendered, "verified_rendered": rendered,
            "collection_id": (back or {}).get("id"),
            "handle": (back or {}).get("handle"),
            "rule_count": len(got)}


# ---------- CW4: main-navigation placement (the store's nav spine) ----------
# gate class CONSEQUENTIAL, RULED so deliberately: the Admin API has no
# per-item diff — menuUpdate REPLACES the whole item tree wholesale, so a write
# silently drops anything the payload omits, and the main menu is a DEFAULT
# menu (isDefault, un-deletable) whose prior tree we do not snapshot here. a
# nav rewrite is therefore not reversible-in-practice; the owner should rule
# each one. it parks per item (the batch-approve loop makes that cheap).
# menu_id present -> menuUpdate (place into the existing main menu); absent with
# a handle -> menuCreate (a fresh secondary menu). read-back is the receipt:
# the live menu's top-level item titles, in order, must match what we sent.
_MENU_UPDATE_MUTATION = """
mutation menuUpdate($id: ID!, $title: String!, $items: [MenuItemUpdateInput!]!) {
  menuUpdate(id: $id, title: $title, items: $items) {
    menu { id handle title isDefault items { id title type url } }
    userErrors { code field message }
  }
}
"""

_MENU_CREATE_MUTATION = """
mutation menuCreate($handle: String!, $title: String!, $items: [MenuItemCreateInput!]!) {
  menuCreate(handle: $handle, title: $title, items: $items) {
    menu { id handle title isDefault items { id title type url } }
    userErrors { code field message }
  }
}
"""

_READBACK_MENU = """
query menu($id: ID!) {
  menu(id: $id) { id handle title isDefault items { id title type url } }
}
"""


def _menu_items_in(items: list) -> list:
    """our item dicts -> the GraphQL MenuItem*Input shape. title is required;
    type defaults to COLLECTION (the placement CW5 makes); resource_id points
    a COLLECTION/PRODUCT item at its resource, url carries an HTTP item; nested
    items recurse (Shopify allows three levels)."""
    out = []
    for it in items or []:
        node: dict = {"title": it["title"], "type": it.get("type", "COLLECTION")}
        if it.get("resource_id"):
            node["resourceId"] = it["resource_id"]
        if it.get("url"):
            node["url"] = it["url"]
        if it.get("items"):
            node["items"] = _menu_items_in(it["items"])
        out.append(node)
    return out


def _top_titles(items: list) -> list:
    return [it.get("title") for it in (items or [])]


def _mutate_menu(client: ShopifyClient, args: dict) -> dict:
    title = (args.get("title") or "").strip()
    if not title:
        return {"ok": False, "error": "a menu carries a title"}
    items = args.get("items")
    if not items:
        return {"ok": False, "error": "a menu write carries at least one item"}
    gql_items = _menu_items_in(items)
    menu_id = args.get("menu_id")
    if menu_id:
        data = client.graphql(_MENU_UPDATE_MUTATION,
                              {"id": menu_id, "title": title, "items": gql_items})
        if _errs(data, "menuUpdate"):
            return {"ok": False, "error": json.dumps(_errs(data, "menuUpdate"))}
        made = (data.get("menuUpdate") or {}).get("menu")
    else:
        handle = (args.get("handle") or "").strip()
        if not handle:
            return {"ok": False,
                    "error": "a new menu carries a handle (or a menu_id to update)"}
        data = client.graphql(_MENU_CREATE_MUTATION,
                              {"handle": handle, "title": title, "items": gql_items})
        if _errs(data, "menuCreate"):
            return {"ok": False, "error": json.dumps(_errs(data, "menuCreate"))}
        made = (data.get("menuCreate") or {}).get("menu")
    if not made:
        return {"ok": False, "error": "the menu mutation returned no menu"}
    back = client.graphql(_READBACK_MENU, {"id": made["id"]}).get("menu")
    sent = _top_titles(items)
    got = _top_titles((back or {}).get("items"))
    rendered = bool(back) and got == sent
    return {"ok": rendered, "verified_rendered": rendered,
            "menu_id": (back or {}).get("id"),
            "handle": (back or {}).get("handle"),
            "item_titles": got}
