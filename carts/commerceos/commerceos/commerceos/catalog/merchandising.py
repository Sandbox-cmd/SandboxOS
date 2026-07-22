"""merchandising / smart collections — the V1 keystone catalog feature, pure
config over the one workflow engine (spec/parts/catalog-workflows.md:159).

the job (the v0 keystone: ~20 creates, not 3,000 writes): one smart collection
per major category, so a shopper meets the catalog as shelves. the ~20
definitions are DATA — the active store's collections.json, derived from the
locked taxonomy's category classifier — not code constants; store #2 rewrites
that file. this module is the config that wires those definitions into the
engine: the queue (collections not yet on the store), the write (the existing
CW4 create_collection door), verify (the executor's read-back receipt), and
progress (collection-coverage — the share of products in at least one smart
collection, RULED the card's headline 2026-07-12).

placement is BOTH (owner ruled both-now 2026-07-19): the collections above
(reversible creates, held for one glance-approve), AND the main navigation —
a SEPARATE consequential flow (nav_proposal / mutate_menu) that parks per item
because a menu write replaces the whole tree wholesale (CW4).

the rule basis is product_type, not the commerceos.category metafield — see
collections.json _rule_basis_doc: the metafield rule the schema enum offers
(PRODUCT_METAFIELD_DEFINITION) needs a metafield DEFINITION with
useAsCollectionCondition set and a conditionObjectId the shipped executor does
not send, so product_type CONTAINS (the same signal the taxonomy classifier
keys on) is the honest, working basis today.

coverage reads products.collections — the titles the connector syncs per
product (connector_shopify.py). that column refreshes ONLY on a full product
sync, so a freshly-created collection's membership LAGS until the next sync;
the surface says "as of the last sync" so the number is never a lie.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from commerceos import stores
from commerceos.gate import ledger

# the write the create batch runs (CW4, spine/writes.py) and the nav write the
# placement flow runs (CW4, consequential). the agent identifier that lands on
# each ledger row — the merchandising writer-class. NOTE (flagged): no agent
# manifest in .claude/agents/ owns a collections/merchandising writer-class
# today (catalog-proposer owns product fields + publish state; content owns
# pages/meta/feed) — collection STRUCTURE is neither. this follows the existing
# feature precedent (gtin -> "catalog-gtin", classification ->
# "catalog-classification": bare identifiers, no manifest) and earns its own
# manifest when the domain does.
AGENT = "catalog-merchandising"
FUNCTION = "catalog-enrichment"
METHOD = "create_collection"
NAV_METHOD = "mutate_menu"


def load_config(path: Path | str | None = None) -> dict:
    """the store's merchandising config — the ~20 definitions + the main-menu
    target. the resolver honors the env store override; tests pass their own."""
    p = Path(path or stores.resolve(stores.active_store(), "collections.json"))
    return json.loads(p.read_text())


_CFG: dict | None = None


def _cfg(config: dict | None = None) -> dict:
    """the config — the caller's if given, else the active store's loaded once."""
    global _CFG
    if config is not None:
        return config
    if _CFG is None:
        _CFG = load_config()
    return _CFG


def definitions(config: dict | None = None) -> list[dict]:
    """the ~20 collection definitions (title, handle, rules, applied_disjunctively)."""
    return _cfg(config).get("collections", [])


def _product_collection_titles(conn: sqlite3.Connection) -> list[list[str]]:
    """each product's synced collection titles — products.collections is a JSON
    array of titles the connector lands on a full sync. a null/blank/bad value
    reads as no memberships, never an error."""
    out = []
    try:
        rows = conn.execute("SELECT collections FROM products")
    except sqlite3.OperationalError:
        return out
    for (raw,) in rows:
        try:
            titles = json.loads(raw) if raw else []
        except (ValueError, TypeError):
            titles = []
        out.append([t for t in titles if isinstance(t, str)])
    return out


def existing_titles(conn: sqlite3.Connection) -> set:
    """the collection titles that already exist on the store, read from the
    local facts: a title is 'existing' when it shows on at least one product's
    synced membership. imperfect by construction — a live collection with zero
    members never appears in any product's list — but it is the honest
    local-facts read, and re-proposing a zero-member collection is harmless
    (the create receipt catches a taken handle). refreshes on the next sync."""
    seen: set = set()
    for titles in _product_collection_titles(conn):
        seen.update(titles)
    return seen


def _rule_phrase(defn: dict) -> str:
    """the membership rule in plain words for a person's screen — never the
    column/relation codes. 'products whose type mentions torch, lantern or …'."""
    terms = defn.get("match_terms") or [r.get("condition") for r in defn.get("rules", [])]
    terms = [str(t) for t in terms if t]
    if not terms:
        return "products in this category"
    if len(terms) == 1:
        shown = terms[0]
    elif len(terms) <= 4:
        shown = ", ".join(terms[:-1]) + " or " + terms[-1]
    else:
        shown = ", ".join(terms[:3]) + f" or {len(terms) - 3} more"
    return f"products whose type mentions {shown}"


def merch_queue(conn: sqlite3.Connection, config: dict | None = None) -> list:
    """the collections not yet on the store: every definition whose title is not
    already a synced membership. each item carries the create_collection args
    (title, handle, rules, applied_disjunctively) + a plain display sentence."""
    have = existing_titles(conn)
    work = []
    for d in definitions(config):
        if d["title"] in have:
            continue
        work.append({
            "title": d["title"],
            "handle": d["handle"],
            "rules": d["rules"],
            "display": f"new collection: {d['title']} — {_rule_phrase(d)}",
            "args": {
                "title": d["title"],
                "handle": d["handle"],
                "rules": d["rules"],
                "applied_disjunctively": bool(d.get("applied_disjunctively", True)),
            },
        })
    return work


def merch_verify(outcome: dict, item: dict) -> bool:
    """counts only when the store created the collection and read it back with
    OUR handle and every rule we sent — the CW4 receipt's own truth (title +
    exact rules echoed live). membership is NOT verified here: Shopify settles a
    smart collection asynchronously after the create, so coverage moves on the
    next sync, not on this receipt (create verified != membership settled)."""
    return (bool(outcome.get("ok"))
            and bool(outcome.get("verified_rendered"))
            and outcome.get("handle") == item["handle"]
            and outcome.get("rule_count") == len(item["rules"]))


def merch_progress(conn: sqlite3.Connection, config: dict | None = None) -> dict:
    """the card's headline number: collection-coverage — the share of products
    in at least one of OUR smart collections, read live from products.collections
    (the synced memberships). honest at 0 before any collection lands, and moving
    as collections are created and the next sync lands their members. also: how
    many of the ~20 are live, and how many are still to create."""
    defined = {d["title"] for d in definitions(config)}
    memberships = _product_collection_titles(conn)
    total = len(memberships)
    covered = sum(1 for titles in memberships if defined.intersection(titles))
    have = existing_titles(conn)
    collections_live = len(defined & have)
    collections_total = len(defined)
    to_create = collections_total - collections_live
    return {
        "covered": covered,
        "total": total,
        "collections_live": collections_live,
        "collections_total": collections_total,
        "to_create": to_create,
        "rate": round(covered / total, 4) if total else 0.0,
    }


# ---------- the SEPARATE nav-placement flow (consequential, parks per item) ----------
# a menu write is NOT part of the reversible create batch: menuUpdate replaces
# the whole item tree wholesale and the main menu is default + un-deletable, so
# a nav rewrite parks for the owner's per-item call (CW4). the items are built
# from LOCAL FACTS only — each LIVE collection becomes a top-level link to its
# storefront collection page (an HTTP item at /collections/<handle>); we store
# no collection gid locally, so a native COLLECTION item with a resourceId is a
# later refinement, once creates capture their ids. the main-menu gid is store
# config (collections.json main_menu), confirmed by the owner before the live
# land — it is not in the facts.
NAV_WHY = ("changes your store's navigation — a menu write replaces the whole "
           "menu tree, so it waits on you.")


def nav_menu_items(conn: sqlite3.Connection, config: dict | None = None) -> list[dict]:
    """the live collections as top-level menu items, in the config's order —
    each a link to its storefront collection page. only collections that
    actually exist on the store (synced membership) are placed; nothing is
    linked to a shelf that isn't there yet."""
    have = existing_titles(conn)
    items = []
    for d in definitions(config):
        if d["title"] not in have:
            continue
        items.append({"title": d["title"], "type": "HTTP",
                      "url": f"/collections/{d['handle']}"})
    return items


def nav_pending(conn: sqlite3.Connection) -> str | None:
    """the id of a nav-placement proposal already waiting on the owner, or None.
    a menu write parks per item, so at most ONE should wait at a time — the
    control steps aside for it and a re-press never stages a duplicate (mirrors
    the reversible batch's one-waits-at-a-time step-aside)."""
    try:
        rows = conn.execute(
            "SELECT id, expires_at FROM ledger WHERE status = 'pending'"
            " AND json_extract(proposal, '$.method') = ?", (NAV_METHOD,)).fetchall()
    except sqlite3.OperationalError:
        return None
    for r in rows:
        if not ledger.expired(r["expires_at"]):
            return r["id"]
    return None


def nav_proposal(conn: sqlite3.Connection, config: dict | None = None) -> dict | None:
    """the ONE mutate_menu proposal that places the live collections into the
    store's main menu — consequential, so it parks per item with a plain WHY.
    returns None when no collection is live yet (nothing to place). the args
    carry the main-menu target (menu_id from store config) + the items; the
    executor's read-back checks the top-level titles landed."""
    items = nav_menu_items(conn, config)
    if not items:
        return None
    main = _cfg(config).get("main_menu") or {}
    return {
        "agent": AGENT,
        "function": FUNCTION,
        "method": NAV_METHOD,
        "args": {
            "menu_id": main.get("id"),
            "title": main.get("title") or "Main menu",
            "items": items,
        },
        "declared_type": "consequential",
        "intent": (f"place {len(items)} smart collection"
                   f"{'s' if len(items) != 1 else ''} into your store's main menu"),
        "rationale": NAV_WHY,
        "provenance": [{"source": "merchandising config (collections.json)"},
                       {"source": "owner:cw4-placement-ruling-both-now"}],
    }
