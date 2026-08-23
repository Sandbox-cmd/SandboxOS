"""books file-drop import — the FTA VAT audit file lands as money_lines facts.

data-spine.md behavior 4: a dropped file is parsed, rows land as money
lines carrying the file hash as import_batch; re-importing the same file
lands zero new rows (the money_lines_dedupe unique index does the work).

the FTA file (Zoho's "FTA VAT Audit File" CSV) is one file with sections,
each opened by a bare marker line and closed by a "... Total" marker:

    Company Information Table          -> ignored
    Customer Supply Listing Table      -> sales line items   (account='sales')
    Supplier Purchase Listing Table    -> purchase line items (account='purchases')
    General Ledger Table               -> ignored (not a listing)

amount column: SupplyValueAED / PurchaseValueAED — the VAT-EXCLUSIVE value.
chosen by reconciling against the period's known GMV anchor: the exclusive
sum, with credit notes (negative rows) netted in, matches it exactly; the
VAT-inclusive sum does not. check this on your own file before trusting a
period — the column choice is the whole reconciliation.

external_ref: "<invoice no.>#<transaction id>/<line no.>" — the row's full
document identity. the dedupe index has no account column and the plain
invoice number repeats across lines (hundreds of same-date-same-amount
collisions in a real archive — e.g. purchase invoices all numbered
"Pending"), so the invoice number alone would silently drop real rows
inside one file.

money is INTEGER minor units (fils); amounts parse through Decimal, never
float. a row whose amount is not a whole number of fils is malformed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import NamedTuple

# section marker -> (account, amount column). only the two listings land.
LISTINGS = {
    "Customer Supply Listing Table": ("sales", "SupplyValueAED"),
    "Supplier Purchase Listing Table": ("purchases", "PurchaseValueAED"),
}

# every listing carries these; names come from the file's own header row.
DATE_COL = "InvoiceDate"
INVOICE_COL = "Invoice No."
TXN_COL = "TransactionID"
LINE_COL = "Line No."


class ImportCounts(NamedTuple):
    landed: int  # new money_lines rows written
    skipped: int  # rows the dedupe index already held (re-import)
    malformed: int  # rows that would not parse — counted, never fatal


def _fils(text: str) -> int:
    """AED text -> integer fils, exact. Raises ValueError if sub-fil."""
    amount = Decimal(text.strip()) * 100
    if amount != amount.to_integral_value():
        raise ValueError(f"not a whole number of fils: {text!r}")
    return int(amount)


def _iso_date(text: str) -> str:
    """FTA dates are DD-MM-YYYY -> ISO YYYY-MM-DD."""
    return datetime.strptime(text.strip(), "%d-%m-%Y").date().isoformat()


def import_fta_file(conn, path: Path | str) -> ImportCounts:
    """Parse an FTA VAT audit file and land its listings into money_lines.

    Every row lands with kind='books', the section's account, the file's
    sha256 as import_batch, and source='fta:<filename>'. Idempotent: the
    same file twice lands zero new rows.
    """
    path = Path(path)
    raw = path.read_bytes()
    batch = hashlib.sha256(raw).hexdigest()
    source = f"fta:{path.name}"
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    landed = skipped = malformed = 0
    account: str | None = None  # inside a listing section, or None
    amount_col: str | None = None
    header: dict[str, int] | None = None  # column name -> index

    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig")))
    for row in reader:
        cells = [c.strip() for c in row]
        filled = [c for c in cells if c]
        if not filled:
            continue

        # bare marker lines open and close sections
        if len(filled) == 1:
            marker = filled[0]
            if marker in LISTINGS:
                account, amount_col = LISTINGS[marker]
                header = None  # next row is this listing's header
                continue
            if marker.endswith(("Table", "Total")):
                account = None  # totals blocks, ledger, company info: not ours
                continue
            # a lone value inside a listing is not a parseable row
            if account is not None and header is not None:
                malformed += 1
            continue

        if account is None:
            continue  # rows of a section we don't import

        if header is None:
            header = {name.strip(): i for i, name in enumerate(row)}
            needed = (DATE_COL, INVOICE_COL, TXN_COL, LINE_COL, amount_col)
            missing = [c for c in needed if c not in header]
            if missing:
                raise ValueError(f"{path.name}: listing header missing {missing}")
            continue

        try:
            date = _iso_date(row[header[DATE_COL]])
            amount = _fils(row[header[amount_col]])
            ref = (
                f"{row[header[INVOICE_COL]].strip()}"
                f"#{row[header[TXN_COL]].strip()}"
                f"/{row[header[LINE_COL]].strip()}"
            )
        except (ValueError, InvalidOperation, IndexError):
            malformed += 1
            continue

        cur = conn.execute(
            "INSERT OR IGNORE INTO money_lines"
            " (date, kind, account, amount_minor, currency,"
            "  external_ref, import_batch, source, fetched_at)"
            " VALUES (?, 'books', ?, ?, 'AED', ?, ?, ?, ?)",
            (date, account, amount, ref, batch, source, fetched_at),
        )
        if cur.rowcount == 1:
            landed += 1
        else:
            skipped += 1  # the dedupe index already holds this row

    conn.commit()
    return ImportCounts(landed, skipped, malformed)


def _sales_by_year(conn, batch: str) -> list[tuple[str, int]]:
    return [
        (r["year"], r["total"])
        for r in conn.execute(
            "SELECT substr(date, 1, 4) AS year, SUM(amount_minor) AS total"
            " FROM money_lines"
            " WHERE import_batch = ? AND kind = 'books' AND account = 'sales'"
            " GROUP BY year ORDER BY year",
            (batch,),
        )
    ]


def main(argv: list[str] | None = None) -> int:
    from commerceos.spine.schema import ensure_schema

    parser = argparse.ArgumentParser(
        prog="python -m commerceos.spine.books_import",
        description="Land an FTA VAT audit file into the facts store.",
    )
    parser.add_argument("path", type=Path, help="the FTA CSV to import")
    args = parser.parse_args(argv)
    if not args.path.is_file():
        parser.error(f"no such file: {args.path}")

    conn = ensure_schema()
    counts = import_fta_file(conn, args.path)
    print(f"landed {counts.landed} · skipped {counts.skipped} · malformed {counts.malformed}")

    batch = hashlib.sha256(args.path.read_bytes()).hexdigest()
    print("sales per year (AED, VAT-exclusive):")
    for year, total in _sales_by_year(conn, batch):
        print(f"  {year}  {Decimal(total) / 100:>14,.2f}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
