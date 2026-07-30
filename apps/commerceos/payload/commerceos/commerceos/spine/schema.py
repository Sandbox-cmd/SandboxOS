"""the facts tables — the spine is their sole writer.

every fact carries source + fetched_at (NOT NULL, enforced here, checked
in tests). money is INTEGER minor units (fils); rates are INTEGER basis
points — settlement identities stay exact, no float drift.
"""

from commerceos.db import connect, migrate

TABLE_SET = "facts"

MIGRATIONS = [
    """
    CREATE TABLE products (
        shopify_id   TEXT PRIMARY KEY,
        handle       TEXT,
        title        TEXT,
        status       TEXT,
        vendor       TEXT,
        product_type TEXT,
        tags         TEXT,               -- JSON array
        raw          TEXT,               -- JSON, the landed payload
        source       TEXT NOT NULL,
        fetched_at   TEXT NOT NULL
    );
    CREATE TABLE variants (
        shopify_id   TEXT PRIMARY KEY,
        product_id   TEXT NOT NULL REFERENCES products(shopify_id),
        sku          TEXT,
        barcode      TEXT,
        price_minor  INTEGER,
        inventory    INTEGER,
        source       TEXT NOT NULL,
        fetched_at   TEXT NOT NULL
    );
    CREATE TABLE orders (
        shopify_id         TEXT PRIMARY KEY,
        number             TEXT,
        placed_at          TEXT,
        customer_ref       TEXT,          -- shopify customer id only; PII stays in Shopify
        currency           TEXT NOT NULL DEFAULT 'AED',
        gross_minor        INTEGER NOT NULL,
        discount_minor     INTEGER NOT NULL DEFAULT 0,
        shipping_minor     INTEGER NOT NULL DEFAULT 0,
        tax_minor          INTEGER NOT NULL DEFAULT 0,
        net_minor          INTEGER NOT NULL,
        financial_status   TEXT,
        fulfillment_status TEXT,
        source             TEXT NOT NULL,
        fetched_at         TEXT NOT NULL
    );
    CREATE TABLE order_lines (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id       TEXT NOT NULL REFERENCES orders(shopify_id),
        variant_id     TEXT,
        vendor         TEXT,
        qty            INTEGER NOT NULL,
        unit_price_minor INTEGER NOT NULL,
        discount_minor INTEGER NOT NULL DEFAULT 0,
        net_minor      INTEGER NOT NULL,
        -- settlement at landing (commission-marketplace ruling):
        take_rate_bps  INTEGER NOT NULL,
        take_minor     INTEGER NOT NULL,
        payable_minor  INTEGER NOT NULL,
        rate_source    TEXT NOT NULL,     -- which config row supplied the rate
        CHECK (take_minor + payable_minor = net_minor)
    );
    CREATE TABLE returns (
        shopify_id   TEXT PRIMARY KEY,
        order_id     TEXT NOT NULL REFERENCES orders(shopify_id),
        refunded_at  TEXT,
        amount_minor INTEGER NOT NULL,
        source       TEXT NOT NULL,
        fetched_at   TEXT NOT NULL
    );
    CREATE TABLE return_lines (
        id                     INTEGER PRIMARY KEY AUTOINCREMENT,
        return_id              TEXT NOT NULL REFERENCES returns(shopify_id),
        order_line_id          INTEGER NOT NULL REFERENCES order_lines(id),
        qty                    INTEGER NOT NULL,
        amount_minor           INTEGER NOT NULL,
        take_reversed_minor    INTEGER NOT NULL,
        payable_reversed_minor INTEGER NOT NULL,
        CHECK (take_reversed_minor + payable_reversed_minor = amount_minor)
    );
    CREATE TABLE ad_spend (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        platform      TEXT NOT NULL,
        campaign_id   TEXT,
        campaign_name TEXT,
        date          TEXT NOT NULL,
        spend_minor   INTEGER NOT NULL,
        currency      TEXT NOT NULL DEFAULT 'AED',
        clicks        INTEGER,
        impressions   INTEGER,
        source        TEXT NOT NULL,
        fetched_at    TEXT NOT NULL
    );
    CREATE TABLE suppliers (
        name                  TEXT PRIMARY KEY,
        default_take_rate_bps INTEGER,
        payment_terms         TEXT,
        source                TEXT NOT NULL,
        fetched_at            TEXT NOT NULL
    );
    CREATE TABLE purchase_orders (
        id         TEXT PRIMARY KEY,
        supplier   TEXT,
        status     TEXT,
        created_at TEXT,
        source     TEXT NOT NULL,
        fetched_at TEXT NOT NULL
    );
    CREATE TABLE po_lines (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        po_id           TEXT NOT NULL REFERENCES purchase_orders(id),
        variant_id      TEXT,
        qty             INTEGER NOT NULL,
        unit_cost_minor INTEGER NOT NULL
    );
    CREATE TABLE money_lines (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        date         TEXT NOT NULL,
        kind         TEXT NOT NULL,      -- payout | gateway_fee | platform_bill | books
        account      TEXT,               -- books account name when kind = books
        amount_minor INTEGER NOT NULL,
        currency     TEXT NOT NULL DEFAULT 'AED',
        external_ref TEXT,
        import_batch TEXT NOT NULL,      -- file hash; same file twice lands zero new rows
        source       TEXT NOT NULL,
        fetched_at   TEXT NOT NULL
    );
    CREATE UNIQUE INDEX money_lines_dedupe
        ON money_lines (import_batch, date, kind, amount_minor, COALESCE(external_ref, ''));
    CREATE TABLE sync_state (
        connector TEXT PRIMARY KEY,
        cursor    TEXT,
        last_run  TEXT,
        status    TEXT,
        error     TEXT
    );
    """,
    # migration 1 (backlog A8): the widened product sync — metafields, media,
    # seo, collections, description length — so the audit scores all 7
    # dimensions from landed facts. the as-fetched payload rides products.raw;
    # these are the queryable homes. one row per shopify id, upserted.
    """
    ALTER TABLE products ADD COLUMN seo_title TEXT;
    ALTER TABLE products ADD COLUMN seo_description TEXT;
    ALTER TABLE products ADD COLUMN collections TEXT;        -- JSON array of collection titles (first 10)
    ALTER TABLE products ADD COLUMN description_len INTEGER; -- length of descriptionHtml as fetched
    CREATE TABLE product_media (
        product_id      TEXT PRIMARY KEY REFERENCES products(shopify_id),
        media_count     INTEGER NOT NULL DEFAULT 0,
        first_image_url TEXT,
        source          TEXT NOT NULL,
        fetched_at      TEXT NOT NULL
    );
    CREATE TABLE product_meta (
        product_id TEXT NOT NULL REFERENCES products(shopify_id),
        namespace  TEXT NOT NULL,
        key        TEXT NOT NULL,
        type       TEXT,
        value      TEXT,
        source     TEXT NOT NULL,
        fetched_at TEXT NOT NULL,
        PRIMARY KEY (product_id, namespace, key)
    );
    """,
    # migration 2 (CL1): the product lifecycle — the small ruled state model
    # the operator runs the catalog from. catalog/lifecycle.py is the SOLE
    # writer of both tables (the current-state field AND the append-only
    # history); schema only creates them. no FK to products: lifecycle state
    # is placed by set_initial from the synced status and stands on its own,
    # so a product id need not already sit in the facts table to carry state.
    # product_lifecycle holds one current state per product (the invariant:
    # exactly one, never two). lifecycle_history is append-only — one row per
    # move, with who/when/why and the ledger id of the store write when one
    # backed the move (the delist-feature seam commits state only on a
    # verified store outcome and records that outcome's ledger id here).
    """
    CREATE TABLE product_lifecycle (
        product_id TEXT PRIMARY KEY,
        state      TEXT NOT NULL,
        reason     TEXT,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE lifecycle_history (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL,
        from_state TEXT,                     -- NULL on the first (sync placement) row
        to_state   TEXT NOT NULL,
        reason     TEXT,
        "by"       TEXT NOT NULL,            -- operator id, 'detector', or 'sync'
        ts         TEXT NOT NULL,
        ledger_id  TEXT                      -- the store write's record, when one backed the move
    );
    CREATE INDEX lifecycle_history_product ON lifecycle_history (product_id);
    """,
]


def ensure_schema(conn=None):
    """Create the facts tables if they don't exist. Returns the connection."""
    conn = conn or connect()
    migrate(conn, TABLE_SET, MIGRATIONS)
    return conn
