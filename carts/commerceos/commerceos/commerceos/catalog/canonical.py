"""the canonical product record — the catalog loop's own table-set (C2).

one row per product, one row per spec claim, built only from landed facts
(the spine's products + product_meta tables — read here, never written).
every claim carries provenance: source, verified 0|1, verified_on, unit,
fit-critical. the emitters (emitters.py) read this record and nothing
else, so page, feed, and structured data cannot disagree — C2's
consistency is built in, not checked after.

the provenance rule (spec/parts/catalog-loop.md): a claim with no source
of its own lands verified=0. the landed meta carries provenance as a
`<field>_provenance` json companion per spec field — that is the pattern
actually found in product_meta (v0's notes said `*_source`; the landed
rows say `_provenance`), shaped {"source", "verified", "verified_on",
"unit", "std", "fc"}. verified in the canonical record means the
companion itself says verified:true AND names a source — a companion's
existence alone verifies nothing (today every landed companion says
verified:false with source "parsed:supplier-spec-blob": a parsed value
waiting for a real source). never invent a value: only a landed,
non-empty metafield value becomes a claim; an orphan companion with no
bare value becomes nothing.

what counts as a spec vs a descriptive blob is the store's audit config
(spec_namespaces, spec_blob_keys) — one definition shared with the audit,
so the two phases can never disagree about what a spec is. the taxonomy
(locked instance data) supplies category resolution, units, and
fit-critical flags; the engine knows nothing about outdoor gear.

one writer per table-set, mechanically: connect_guarded() attaches a
sqlite authorizer that denies this connection any write outside the
canonical tables — the facts stay untouched by construction, not by
promise.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from commerceos import stores
from commerceos.catalog.audit import _index_taxonomy, resolve_category
from commerceos.db import connect, migrate

TABLE_SET = "canonical"
PROVENANCE_SUFFIX = "_provenance"

REPO = Path(__file__).resolve().parents[2]


def default_db() -> Path:
    return stores.resolve(stores.active_store(), stores.DB)


def default_taxonomy_path() -> Path:
    return stores.resolve(stores.active_store(), "taxonomy.json")


def default_config_path() -> Path:
    return stores.resolve(stores.active_store(), "audit-config.json")

MIGRATIONS = [
    """
    CREATE TABLE canonical_products (
        shopify_id TEXT PRIMARY KEY,
        handle     TEXT,
        title      TEXT,
        vendor     TEXT,
        category   TEXT,               -- resolved against the locked taxonomy; NULL = unresolved
        built_at   TEXT NOT NULL
    );
    CREATE TABLE spec_claims (
        id           INTEGER PRIMARY KEY,
        product      TEXT NOT NULL REFERENCES canonical_products(shopify_id),
        field        TEXT NOT NULL,
        value        TEXT NOT NULL,    -- never invented: only a landed, non-empty value lands here
        unit         TEXT,
        source       TEXT NOT NULL,    -- no source, no claim
        verified     INTEGER NOT NULL DEFAULT 0 CHECK (verified IN (0, 1)),
        verified_on  TEXT,
        fit_critical INTEGER NOT NULL DEFAULT 0 CHECK (fit_critical IN (0, 1)),
        UNIQUE (product, field),
        CHECK (verified = 0 OR source <> '')   -- never verified-without-source, mechanically
    );
    """,
    # CW7 (ruled 2026-07-12/18): verifications survive the full rebuild.
    # a verification binds to the exact (product, field, VALUE) it checked;
    # build_canonical re-applies it only while the landed value still
    # matches — a drifted value honestly loses its verified mark.
    """
    CREATE TABLE claim_verifications (
        product     TEXT NOT NULL,
        field       TEXT NOT NULL,
        value       TEXT NOT NULL,
        source      TEXT NOT NULL CHECK (source <> ''),
        verified_on TEXT NOT NULL,
        PRIMARY KEY (product, field)
    );
    """,
]

# tables this part may write: its own table-set plus migration bookkeeping.
_WRITABLE = {"canonical_products", "spec_claims", "claim_verifications", "_migrations"}
_WRITE_ACTIONS = (
    sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
    sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE,
    sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_DROP_INDEX,
    sqlite3.SQLITE_ALTER_TABLE,
)


def _guard(action, arg1, arg2, dbname, trigger):
    """one writer per table-set, enforced below the code: any statement that
    would touch a table outside the canonical set is denied at prepare time."""
    if action not in _WRITE_ACTIONS:
        return sqlite3.SQLITE_OK
    # for ALTER TABLE and index DDL the table name rides in arg2
    table = arg2 if action in (
        sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_DROP_INDEX
    ) else arg1
    if table is None or table.startswith("sqlite_") or table in _WRITABLE:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def connect_guarded(path: Path | str | None = None) -> sqlite3.Connection:
    """open the shared database with the catalog's write guard attached:
    the facts tables (and every other part's tables) are read-only on this
    connection — mechanically, the way audit.py's mode=ro is mechanical."""
    conn = connect(path)
    conn.set_authorizer(_guard)
    return conn


def ensure_schema(conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
    """create the canonical tables if they don't exist. returns the connection."""
    conn = conn or connect_guarded()
    migrate(conn, TABLE_SET, MIGRATIONS)
    return conn


def record_verification(conn: sqlite3.Connection, product: str, field: str,
                        value: str, source: str,
                        verified_on: str | None = None) -> dict:
    """the provenance flip — this module's own hand (CW7, the one-writer
    division ruled 2026-07-12). records the verification in
    claim_verifications and flips the live spec_claims row when its value
    matches the value that was checked. no source, no claim — refused.
    does not commit; the caller owns the transaction."""
    if not source or not str(source).strip():
        raise ValueError("no source, no claim — a verification names where it looked")
    verified_on = verified_on or time.strftime("%Y-%m-%d", time.gmtime())
    conn.execute(
        "INSERT INTO claim_verifications (product, field, value, source, verified_on)"
        " VALUES (?,?,?,?,?)"
        " ON CONFLICT(product, field) DO UPDATE SET"
        " value=excluded.value, source=excluded.source, verified_on=excluded.verified_on",
        (product, field, str(value), source, verified_on))
    cur = conn.execute(
        "UPDATE spec_claims SET verified=1, verified_on=?, source=?"
        " WHERE product=? AND field=? AND value=?",
        (verified_on, source, product, field, str(value)))
    return {"product": product, "field": field, "flipped": cur.rowcount == 1,
            "verified_on": verified_on, "source": source}


def revert_verification(conn: sqlite3.Connection, product: str, field: str,
                        prior: dict) -> None:
    """exact compensation for one record_verification call — used when a
    flip fails its render check. restores the claim's prior provenance
    columns verbatim and removes the overlay row. does not commit."""
    conn.execute("DELETE FROM claim_verifications WHERE product=? AND field=?",
                 (product, field))
    conn.execute(
        "UPDATE spec_claims SET verified=?, verified_on=?, source=?"
        " WHERE product=? AND field=?",
        (prior["verified"], prior["verified_on"], prior["source"], product, field))


def _units_by_category(taxonomy: dict) -> dict[str, dict[str, str | None]]:
    """taxonomy spec_schema -> {category: {field: unit}} (instance data drives)."""
    return {
        cat: {f["key"]: f.get("unit") for f in c.get("spec_schema", [])}
        for cat, c in taxonomy["categories"].items()
        if not cat.startswith("_")
    }


def build_canonical(conn: sqlite3.Connection, taxonomy: dict | None = None,
                    config: dict | None = None) -> dict:
    """construct/refresh the canonical record from landed facts. full
    rebuild, idempotent. reads products + product_meta; writes only the
    canonical tables. returns the build counts.

    per claim:
      value       — the landed metafield value, verbatim. empty/NULL never
                    becomes a claim (never invent a value).
      source      — the provenance companion's source when one parses;
                    else the metafield's landed source ref (which fetch of
                    the live store carried it — the only provenance left).
      verified    — 1 only when the companion says verified:true AND names
                    a source; anything less lands 0.
      verified_on — the companion's date, kept only when verified.
      unit        — the companion's unit, else the taxonomy schema's unit
                    for the product's category, else NULL.
      fit_critical— the locked taxonomy rules for fields it knows; for a
                    field outside the category schema, the companion's fc.
    """
    taxonomy = taxonomy if taxonomy is not None else json.loads(default_taxonomy_path().read_text())
    config = config if config is not None else json.loads(default_config_path().read_text())
    ensure_schema(conn)

    tax = _index_taxonomy(taxonomy)
    units = _units_by_category(taxonomy)
    spec_ns = sorted(set(config.get("spec_namespaces", ["commerceos"])))
    blob_keys = set(config.get("spec_blob_keys", []))

    cur = conn.cursor()
    cur.row_factory = sqlite3.Row

    meta: dict[str, list[sqlite3.Row]] = {}
    q = ",".join("?" * len(spec_ns))
    for m in cur.execute(
        f"SELECT product_id, key, value, source FROM product_meta WHERE namespace IN ({q})",
        spec_ns,
    ):
        meta.setdefault(m["product_id"], []).append(m)

    built_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    prod_rows: list[tuple] = []
    claim_rows: list[tuple] = []
    verified_n = 0
    for p in cur.execute(
        "SELECT shopify_id, handle, title, vendor, product_type FROM products ORDER BY shopify_id"
    ):
        rows = meta.get(p["shopify_id"], [])
        bare = {m["key"]: m for m in rows if not m["key"].endswith(PROVENANCE_SUFFIX)}
        comps: dict[str, dict] = {}
        for m in rows:
            if m["key"].endswith(PROVENANCE_SUFFIX):
                try:
                    c = json.loads(m["value"] or "")
                    if isinstance(c, dict):
                        comps[m["key"][: -len(PROVENANCE_SUFFIX)]] = c
                except Exception:
                    pass  # an unparseable companion is no provenance; the claim lands verified=0

        # identity: the persisted customer category first (v0's keystone lesson),
        # the taxonomy's reverse map over product_type second.
        cat_meta = bare["category"]["value"] if "category" in bare else None
        category = cat_meta if cat_meta in tax["cats"] else resolve_category(p["product_type"], tax)[0]
        prod_rows.append((p["shopify_id"], p["handle"], p["title"], p["vendor"], category, built_at))

        cat_units = units.get(category, {})
        cat_fc = tax["fc"].get(category, set())
        cat_schema = set(tax["schema"].get(category, []))
        for field in sorted(bare):
            if field in blob_keys:
                continue  # descriptive blobs (and the identity category field) are not spec claims
            value = bare[field]["value"]
            if value is None or str(value).strip() == "":
                continue  # a landed-empty value is a gap, not a claim — never invent a value
            comp = comps.get(field)
            comp_source = (comp or {}).get("source") or None
            verified = 1 if (comp is not None and comp.get("verified") is True and comp_source) else 0
            verified_n += verified
            if field in cat_schema:
                fit = 1 if field in cat_fc else 0  # the locked taxonomy rules fields it knows
            else:
                fit = 1 if (comp or {}).get("fc") is True else 0
            claim_rows.append((
                p["shopify_id"], field, str(value),
                (comp or {}).get("unit") or cat_units.get(field),
                comp_source or bare[field]["source"],
                verified,
                (comp or {}).get("verified_on") if verified else None,
                fit,
            ))

    # re-apply recorded verifications (CW7): a verification survives the
    # rebuild only while the landed value still matches the value it
    # checked — value drift honestly drops the verified mark.
    overlay = {
        (p, f): (val, src, on)
        for p, f, val, src, on in conn.execute(
            "SELECT product, field, value, source, verified_on FROM claim_verifications")
    }
    if overlay:
        merged: list[tuple] = []
        for row in claim_rows:
            product, field, value, unit, source, verified, verified_on, fit = row
            v = overlay.get((product, field))
            if verified == 0 and v is not None and v[0] == value:
                row = (product, field, value, unit, v[1], 1, v[2], fit)
                verified_n += 1
            merged.append(row)
        claim_rows = merged

    conn.execute("DELETE FROM spec_claims")
    conn.execute("DELETE FROM canonical_products")
    conn.executemany(
        "INSERT INTO canonical_products (shopify_id, handle, title, vendor, category, built_at)"
        " VALUES (?,?,?,?,?,?)", prod_rows)
    conn.executemany(
        "INSERT INTO spec_claims (product, field, value, unit, source, verified, verified_on, fit_critical)"
        " VALUES (?,?,?,?,?,?,?,?)", claim_rows)
    conn.commit()
    return {
        "products": len(prod_rows),
        "claims": len(claim_rows),
        "verified": verified_n,
        "unverified": len(claim_rows) - verified_n,
        "built_at": built_at,
    }
