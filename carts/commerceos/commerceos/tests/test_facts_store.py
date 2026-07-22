"""A2's checks: schema creates clean; every fact carries source+fetched_at;
the settlement identity is exact; migrations are idempotent."""

import sqlite3

import pytest

from commerceos.db import connect, migrate
from commerceos.spine.schema import MIGRATIONS, TABLE_SET, ensure_schema
from commerceos.spine.settlement import split, unwind


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "test.db")
    ensure_schema(c)
    yield c
    c.close()


def test_schema_creates_clean_and_is_idempotent(tmp_path):
    c = connect(tmp_path / "fresh.db")
    assert migrate(c, TABLE_SET, MIGRATIONS) == len(MIGRATIONS)
    assert migrate(c, TABLE_SET, MIGRATIONS) == 0  # re-run: no-op
    tables = {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"products", "orders", "order_lines", "returns", "money_lines"} <= tables


def test_a_fact_without_source_is_refused(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO products (shopify_id, title, source, fetched_at)"
            " VALUES ('p1', 'x', NULL, '2026-07-11T00:00:00Z')"
        )


def test_a_seeded_fact_carries_source_and_fetched_at(conn):
    conn.execute(
        "INSERT INTO products (shopify_id, title, source, fetched_at)"
        " VALUES ('p1', 'Tent', 'shopify:product/p1@t0', '2026-07-11T00:00:00Z')"
    )
    row = conn.execute("SELECT source, fetched_at FROM products").fetchone()
    assert row["source"] and row["fetched_at"]


def test_settlement_identity_is_exact_across_the_range():
    for net in (0, 1, 99, 100, 605_00, 781_00, 1_540_815_00):
        for bps in (0, 1, 3000, 3250, 3500, 9999, 10000):
            take, payable = split(net, bps)
            assert take + payable == net
            assert take >= 0 and payable >= 0


def test_db_check_constraint_holds_the_identity(conn):
    conn.execute(
        "INSERT INTO orders (shopify_id, gross_minor, net_minor, source, fetched_at)"
        " VALUES ('o1', 10000, 10000, 's', 't')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO order_lines (order_id, qty, unit_price_minor, net_minor,"
            " take_rate_bps, take_minor, payable_minor, rate_source)"
            " VALUES ('o1', 1, 10000, 10000, 3000, 3000, 6999, 'test')"  # 3000+6999 != 10000
        )


def test_full_return_nets_both_sides_to_zero():
    net = 60_500  # AED 605.00
    take, payable = split(net, 3250)
    t1, p1 = unwind(20_000, net, take)
    t2, p2 = unwind(net - 20_000, net, take, already_reversed_take=t1, already_reversed_payable=p1)
    assert t1 + t2 == take
    assert p1 + p2 == payable
    assert (t1 + t2) + (p1 + p2) == net
