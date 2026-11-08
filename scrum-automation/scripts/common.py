"""Shared helpers: load the backlog workbook into pandas DataFrames."""
import argparse
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BOOK = ROOT / "backlog_template.xlsx"
OUTPUT = ROOT / "output"

SHEETS = ["Projects", "Backlog", "Standup Log", "Impediments", "Risks", "Sprint Snapshots", "Calendar"]


def parse_args(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--book", type=Path, default=DEFAULT_BOOK, help="Backlog workbook (.xlsx export)")
    p.add_argument("--sprint", default="S5", help="Current sprint name")
    p.add_argument("--today", default="2026-11-06", help="Date to evaluate against (YYYY-MM-DD); use 'now' for today")
    p.add_argument("--out", type=Path, default=OUTPUT, help="Output folder")
    a = p.parse_args()
    a.today = pd.Timestamp(date.today() if a.today == "now" else a.today)
    a.out.mkdir(parents=True, exist_ok=True)
    return a


def load(book):
    data = pd.read_excel(book, sheet_name=SHEETS)
    for df in data.values():
        for c in df.columns:
            if any(k in c for k in ("Date", "Created", "Started", "Updated", "Raised", "Resolved", "Start")):
                df[c] = pd.to_datetime(df[c], errors="coerce")
    data["Backlog"]["Sprint"] = data["Backlog"]["Sprint"].fillna("")
    return data
