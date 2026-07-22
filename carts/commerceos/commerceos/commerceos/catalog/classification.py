"""classification / taxonomy cleanup — the SECOND catalog feature, pure config
over the one workflow engine (spec/parts/catalog-workflows.md).

the job: a product's locked taxonomy category should be persisted on the
`commerceos.category` metafield, resolved from its product_type against the
locked taxonomy. the QUEUE is the products that are not yet cleanly resolved —
either product_type maps to no locked category (unresolved) or it sits in a
"… — Other" fold bucket. for each, we compute a best-effort target category
from the taxonomy; a product_type that resolves to nothing after one
normalization retry is genuinely unresolvable and is LEFT OUT of the queue —
silence over guesses (the refuse-to-guess invariant).

this module owns none of the machine: it is config. it reuses the audit's
`resolve_category` + `_index_taxonomy` so the audit and this feature can never
disagree about what a product_type resolves to. the write it runs is the
EXISTING `mutate_product_field` metafield door (field `commerceos.category`);
the verified value routes back into the facts via the spine's product_meta
writer (one writer per table-set) so progress reads truth without a re-sync.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from commerceos import stores
from commerceos.catalog.audit import _index_taxonomy, resolve_category

NAMESPACE = "commerceos"
KEY = "category"
FIELD = f"{NAMESPACE}.{KEY}"


def load_taxonomy(path: Path | str | None = None) -> dict:
    """taxonomy.json -> the indexed lookup the resolver reads (audit's shape)."""
    return _index_taxonomy(
        json.loads(
            Path(path or stores.resolve(stores.active_store(), "taxonomy.json")).read_text()
        )
    )


_TAX: dict | None = None


def _tax(tax: dict | None = None) -> dict:
    """the indexed taxonomy — the caller's if given, else the store default
    loaded once. tests pass their own; production loads the active store's locked file."""
    global _TAX
    if tax is not None:
        return tax
    if _TAX is None:
        _TAX = load_taxonomy()
    return _TAX


def _normalize_ptype(ptype: str | None) -> str:
    """a one-step tidy so a product_type given as a full taxonomy PATH or with
    stray whitespace still finds its leaf: take the last '>' segment (the leaf
    name, exactly as _index_taxonomy keys the source leaf map) and collapse
    internal whitespace. normalization is not a guess, it is the same string
    wearing a cleaner shape — it is NOT where a synonym fallback lives (CW3b's
    ruled widening of CW3's "no synonyms, no fuzzy match" scope line: the spec
    already named the shape, spec/parts/catalog-workflows.md:158, "source-
    anchored leaf map first, keyword rules only as fallback"). the curated
    synonym map lives in resolve_category (audit.py), the one door every
    resolver consumer shares; order is law — exact wins, then this
    normalized retry (which inherits the same synonym fallback for free),
    and only on that second miss is the product genuinely unresolvable."""
    p = (ptype or "").strip()
    if ">" in p:
        p = p.rsplit(">", 1)[-1].strip()
    return " ".join(p.split())


def resolve_leaf(ptype: str | None, tax: dict | None = None) -> tuple[str | None, bool]:
    """best-effort target category for a product_type -> (category | None, is_fold).

    reuses audit.resolve_category first (curated subcategories, then the
    417-leaf source map, then — only on that exact miss, CW3b — the curated
    synonym map). when that resolves to a category — including a fold
    bucket, whose own category IS its target, or a synonym hop — that
    stands. only when it resolves to nothing do we retry ONCE on the
    normalized product_type (which inherits the same synonym fallback); if
    that still resolves to nothing, the product is genuinely unresolvable and
    we return None so the caller can leave it OUT of the queue (no guessing)."""
    t = _tax(tax)
    cat, is_fold = resolve_category(ptype, t)
    if cat is not None:
        return cat, is_fold
    norm = _normalize_ptype(ptype)
    if norm and norm.lower() != (ptype or "").strip().lower():
        cat2, fold2 = resolve_category(norm, t)
        if cat2 is not None:
            return cat2, fold2
    return None, is_fold


def _persisted_categories(conn: sqlite3.Connection) -> dict:
    """product_id -> the persisted commerceos.category value (stripped), for
    every product that already carries the metafield fact."""
    return {
        row[0]: (row[1] or "").strip()
        for row in conn.execute(
            "SELECT product_id, value FROM product_meta"
            " WHERE namespace = ? AND key = ?",
            (NAMESPACE, KEY),
        )
    }


def _is_resolved(pid: str, ptype: str | None, tax: dict, persisted: dict) -> bool:
    """a product counts as cleanly resolved when it carries a persisted locked
    category, OR its product_type already resolves to a locked NON-fold
    category. a fold bucket is NOT resolved — it is exactly the queue.

    CW3b: resolve_category runs with use_synonyms=False here — a synonym-
    resolvable product ("Torch") is QUEUEABLE, not resolved, until its
    metafield is actually persisted (mirrors the existing fold-bucket
    precedent above: the audit counts a synonym match classifiable the same
    way it already does folds, but the feature still queues it to persist
    the metafield through the normal gated batch)."""
    pv = persisted.get(pid, "")
    if pv in tax["cats"]:
        return True
    cat, is_fold = resolve_category(ptype, tax, use_synonyms=False)
    return cat is not None and not is_fold


def classification_queue(conn: sqlite3.Connection, tax: dict | None = None) -> list:
    """the products needing classification: unresolved OR fold-bucket, minus
    the genuinely unresolvable (left silent). each item carries the metafield
    write args + a display line + the resolved target leaf."""
    t = _tax(tax)
    persisted = _persisted_categories(conn)
    work = []
    for pid, ptype in conn.execute(
        "SELECT shopify_id, product_type FROM products ORDER BY shopify_id"
    ):
        if _is_resolved(pid, ptype, t, persisted):
            continue
        leaf, _ = resolve_leaf(ptype, t)
        if leaf is None:
            continue  # truly unresolvable -> silence over guesses, NOT queued
        pt = (ptype or "").strip() or "(none)"
        work.append({
            "product_id": pid,
            "product_type": pt,
            "leaf": leaf,
            "display": f"{pid}  {pt!r} -> {leaf}",
            "args": {"field": FIELD, "product_id": pid, "value": leaf},
        })
    return work


def classification_verify(outcome: dict, item: dict) -> bool:
    """counts only if the store rendered the category metafield back == the
    target leaf. a write the store did not render, or rendered to a different
    value, never counts (verify rendered, never files-exist)."""
    if not outcome.get("ok"):
        return False
    mf = outcome.get("metafield") or {}
    return mf.get("value") == str(item["leaf"])


def classification_progress(conn: sqlite3.Connection, tax: dict | None = None) -> dict:
    """the dashboard-card number: the share of products carrying a resolved,
    non-fold-bucket locked category — read live from the facts (persisted
    metafield first, else the product_type resolution)."""
    t = _tax(tax)
    persisted = _persisted_categories(conn)
    total = resolved = 0
    for pid, ptype in conn.execute("SELECT shopify_id, product_type FROM products"):
        total += 1
        if _is_resolved(pid, ptype, t, persisted):
            resolved += 1
    return {"resolved": resolved, "total": total,
            "queue_remaining": len(classification_queue(conn, t)),
            "rate": round(resolved / total, 4) if total else 0.0}


def classification_writeback(conn: sqlite3.Connection, item: dict, outcome: dict) -> None:
    """route the store-verified category back into the facts via the spine (the
    product_meta owner), so progress + audit read truth without waiting for the
    next full sync (one writer per table-set — the engine never writes here)."""
    from commerceos.spine import connector_shopify
    connector_shopify.writeback_product_metafield(
        conn, item["product_id"], NAMESPACE, KEY, str(item["leaf"]))
