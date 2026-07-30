"""E1's checks: the FTA file lands as money_lines facts — right accounts,
exact minor units, idempotent on re-import, malformed rows counted never
fatal. the anchor check against a real archive is a template at the foot of
this file — fill it in with your own books."""

import hashlib
from pathlib import Path

import pytest

import commerceos.db
from commerceos.db import connect
from commerceos.spine.books_import import import_fta_file, main
from commerceos.spine.schema import ensure_schema

FIXTURE = Path(__file__).parent / "fixtures" / "fta_mini.csv"
REAL_FILE = Path("data/books/FTAVATAuditFile.csv")  # your books export; absent by default

# the fixture's good rows: 10 sales + 5 purchases; 3 rows are deliberately
# malformed (bad date, bad amount, short row).
FIXTURE_LANDED = 15
FIXTURE_MALFORMED = 3


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "test.db")
    ensure_schema(c)
    yield c
    c.close()


def _rows(conn, **where):
    clause = " AND ".join(f"{k} = ?" for k in where) or "1=1"
    return conn.execute(
        f"SELECT * FROM money_lines WHERE {clause}", tuple(where.values())
    ).fetchall()


def test_import_lands_the_right_rows_accounts_and_amounts(conn):
    counts = import_fta_file(conn, FIXTURE)
    assert counts == (FIXTURE_LANDED, 0, FIXTURE_MALFORMED)

    sales = _rows(conn, account="sales")
    purchases = _rows(conn, account="purchases")
    assert len(sales) == 10
    assert len(purchases) == 5
    # nothing else landed: the general ledger and totals blocks are not ours
    assert len(_rows(conn)) == FIXTURE_LANDED

    batch = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    for row in sales + purchases:
        assert row["kind"] == "books"
        assert row["currency"] == "AED"
        assert row["import_batch"] == batch
        assert row["source"] == "fta:fta_mini.csv"
        assert row["fetched_at"]

    # exact minor units (fils) and ISO dates, by document identity
    by_ref = {r["external_ref"]: r for r in sales + purchases}
    expect = {
        "GDINV-000100#9000000000000000001/1": ("2024-01-05", 100_000),
        "GDINV-000100#9000000000000000001/2": ("2024-01-05", 25_050),
        # the multi-line quoted description row parses as one row
        "GDINV-000101#9000000000000000002/1": ("2024-03-20", 7_525),
        "GDINV-000101#9000000000000000002/2": ("2024-03-20", 3_000),
        # a credit note lands negative
        "GDCN-00010#9000000000000000004/1": ("2025-03-01", -10_000),
        # an empty invoice number still has a document identity
        "#9000000000000000005/1": ("2025-04-10", 54_000),
        "INV2-2024010001#9100000000000000001/1": ("2024-01-08", 60_000),
        "GDCN-00066#9100000000000000003/1": ("2025-03-05", -45_600),
    }
    for ref, (date, fils) in expect.items():
        assert (by_ref[ref]["date"], by_ref[ref]["amount_minor"]) == (date, fils), ref


def test_same_invoice_same_amount_lines_both_land(conn):
    """The dedupe index must not eat distinct lines of one document —
    external_ref carries invoice#transaction/line, so both survive."""
    import_fta_file(conn, FIXTURE)
    dry_bags = _rows(conn, account="sales", amount_minor=5_500, date="2025-02-14")
    assert len(dry_bags) == 2
    pending = _rows(conn, account="purchases", amount_minor=3_905, date="2025-02-12")
    assert len(pending) == 2


def test_reimport_of_the_same_file_lands_zero_new_rows(conn):
    first = import_fta_file(conn, FIXTURE)
    again = import_fta_file(conn, FIXTURE)
    assert first.landed == FIXTURE_LANDED
    assert again == (0, FIXTURE_LANDED, FIXTURE_MALFORMED)
    assert len(_rows(conn)) == FIXTURE_LANDED


def test_malformed_rows_are_counted_and_skipped_never_fatal(conn):
    counts = import_fta_file(conn, FIXTURE)
    assert counts.malformed == FIXTURE_MALFORMED
    # the ghost rows (bad date, bad amount) never landed
    assert not [r for r in _rows(conn) if "Ghost" in (r["external_ref"] or "")]
    assert not _rows(conn, external_ref="GDINV-000300#9000000000000000006/1")
    assert not _rows(conn, external_ref="GDINV-000301#9000000000000000007/1")


def test_per_year_sales_totals_from_landed_rows(conn):
    import_fta_file(conn, FIXTURE)
    totals = dict(
        conn.execute(
            "SELECT substr(date, 1, 4), SUM(amount_minor) FROM money_lines"
            " WHERE account = 'sales' GROUP BY 1"
        )
    )
    assert totals == {"2024": 135_575, "2025": 92_000}


def test_cli_prints_counts_and_per_year_sales(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("COMMERCEOS_DB", str(tmp_path / "cli.db"))
    assert main([str(FIXTURE)]) == 0
    out = capsys.readouterr().out
    assert f"landed {FIXTURE_LANDED} · skipped 0 · malformed {FIXTURE_MALFORMED}" in out
    assert "2024" in out and "1,355.75" in out
    assert "2025" in out and "920.00" in out


# --- your own archive: the anchor check ---
#
# this is the check that proves the importer against YOUR books, and it is
# the one worth writing before you trust a single number the engine shows.
#
# drop your export at the path above, put your period's known-good sales
# total (in minor units) and row counts below, and delete the skip. the
# assertions are the shape; the values are yours.
#
#   ANCHOR_SALES_MINOR = ...   # the period total your accountant agrees with
#   ANCHOR_SALES_ROWS  = ...   # the file's own totals block
#   ANCHOR_PURCHASE_ROWS = ...
#
# @pytest.mark.skipif(not REAL_FILE.is_file(), reason="no archive on this machine")
# def test_real_archive_reproduces_the_anchor(conn):
#     counts = import_fta_file(conn, REAL_FILE)
#     assert counts.malformed == 0
#     assert counts.skipped == 0
#     assert len(_rows(conn, account="sales")) == ANCHOR_SALES_ROWS
#     assert len(_rows(conn, account="purchases")) == ANCHOR_PURCHASE_ROWS
#
#     total = conn.execute(
#         "SELECT SUM(amount_minor) FROM money_lines"
#         " WHERE account = 'sales' AND date LIKE '<year>-%'"
#     ).fetchone()[0]
#     assert total == ANCHOR_SALES_MINOR
#
# the column choice is the whole reconciliation: the VAT-EXCLUSIVE value,
# with credit notes netted in, is what matches a tax-authority-grade total.
