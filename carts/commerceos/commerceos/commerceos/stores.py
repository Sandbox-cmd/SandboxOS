"""the store registry and the resolver — the one door from a store name
to that store's config files and database (spec/parts/multi-store.md).

resolve order (behavior 1): an explicit env override wins first
(COMMERCEOS_DB for the database, COMMERCEOS_POLICY_TABLE for
policy-table.json); else the store name resolves against the registry.
an unknown store fails loudly, before any read. resolution is CALL-TIME
— nothing here is frozen at import.

stores/registry.json names the stores; this module and the onboarding
ceremony are its sole writers. every store's database is data/<name>.db
and its audit mirror data/<name>.ledger.jsonl — one database, one
ledger, one mirror per store, no exceptions (M3 renamed store #1's
legacy files to conform and retired the registry's bridge field).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DB = "db"  # the sentinel filename that names a store's database

# filename -> the env override that wins over any resolution
_ENV_OVERRIDES = {
    DB: "COMMERCEOS_DB",
    "policy-table.json": "COMMERCEOS_POLICY_TABLE",
}


def registry_path(root: Path | None = None) -> Path:
    return (root or REPO_ROOT) / "stores" / "registry.json"


def load_registry(root: Path | None = None) -> dict:
    """Read and validate the registry. Malformed fails loudly, never guesses."""
    path = registry_path(root)
    if not path.exists():
        raise FileNotFoundError(f"no store registry at {path} — the workshop names its stores there")
    reg = json.loads(path.read_text())
    rows = reg.get("stores")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path} has no 'stores' list — a registry names at least one store")
    names = [row.get("name") for row in rows]
    if any(not n for n in names):
        raise ValueError(f"{path} has a store row without a name")
    if len(names) != len(set(names)):
        raise ValueError(f"{path} names a store twice")
    defaults = [n for row, n in zip(rows, names) if row.get("default")]
    if len(defaults) != 1:
        raise ValueError(
            f"{path} marks {len(defaults)} stores as default — exactly one carries the flag"
        )
    return reg


def default_store(root: Path | None = None) -> str:
    rows = load_registry(root)["stores"]
    return next(row["name"] for row in rows if row.get("default"))


def active_store(root: Path | None = None) -> str:
    """The store this process speaks for: COMMERCEOS_STORE, else the default."""
    named = os.environ.get("COMMERCEOS_STORE")
    if not named:
        return default_store(root)
    known = [row["name"] for row in load_registry(root)["stores"]]
    if named not in known:
        raise ValueError(
            f"COMMERCEOS_STORE names '{named}' but the registry knows {known} — refusing to guess"
        )
    return named


def resolve(store: str, filename: str, root: Path | None = None) -> Path:
    """The only way mechanism code turns a store name into a path.

    resolve(store, "policy-table.json") -> stores/<store>/policy-table.json
    resolve(store, stores.DB)           -> that store's database under data/
    """
    override = _ENV_OVERRIDES.get(filename)
    if override and os.environ.get(override):
        return Path(os.environ[override])
    base = root or REPO_ROOT
    rows = load_registry(root)["stores"]
    row = next((r for r in rows if r["name"] == store), None)
    if row is None:
        raise ValueError(
            f"unknown store '{store}' — the registry knows {[r['name'] for r in rows]}"
        )
    if filename == DB:
        return base / "data" / f"{store}.db"
    return base / "stores" / store / filename


# ---------- the registry's sole writer: onboarding ----------

def register_store(name: str, label: str, root: Path | None = None) -> None:
    """add a store to the registry (never the default — the first store
    keeps that). registering a known name refuses loudly."""
    reg = load_registry(root)
    if any(r["name"] == name for r in reg["stores"]):
        raise ValueError(f"store '{name}' is already registered")
    reg["stores"].append({"name": name, "label": label})
    registry_path(root).write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")


def stamp_step(store: str, step: str, ts: str, root: Path | None = None) -> None:
    """record an onboarding ceremony step on the store's registry row —
    the ceremony's five steps live here, this module their sole writer."""
    if step not in CEREMONY_STEPS:
        raise ValueError(f"unknown ceremony step '{step}' — the ceremony is {CEREMONY_STEPS}")
    reg = load_registry(root)
    row = next((r for r in reg["stores"] if r["name"] == store), None)
    if row is None:
        raise ValueError(f"unknown store '{store}' — register it first")
    row.setdefault("onboarding", {})[step] = ts
    registry_path(root).write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")


CEREMONY_STEPS = ("config", "register", "migrate", "first_tick", "first_render")


def _main(argv: list[str] | None = None) -> int:
    import argparse
    from datetime import datetime, timezone

    ap = argparse.ArgumentParser(
        prog="python -m commerceos.stores",
        description="the store registry: list stores, register one, stamp a ceremony step")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="every registered store and its onboarding stamps")
    reg_p = sub.add_parser("register", help="name a new store in the registry")
    reg_p.add_argument("name")
    reg_p.add_argument("label")
    st = sub.add_parser("stamp", help="record a ceremony step: " + ", ".join(CEREMONY_STEPS))
    st.add_argument("store")
    st.add_argument("step", choices=CEREMONY_STEPS)
    args = ap.parse_args(argv)
    if args.cmd == "register":
        register_store(args.name, args.label)
        print(f"registered '{args.name}' — its config lives at stores/{args.name}/,"
              f" its database at data/{args.name}.db")
    elif args.cmd == "stamp":
        stamp_step(args.store, args.step, datetime.now(timezone.utc).isoformat(timespec="seconds"))
        print(f"stamped {args.step} on '{args.store}'")
    else:
        for row in load_registry()["stores"]:
            stamps = row.get("onboarding", {})
            done = [s for s in CEREMONY_STEPS if s in stamps]
            print(f"{row['name']}{' (default)' if row.get('default') else ''}"
                  f" — {row.get('label', '')} — ceremony: "
                  + (", ".join(done) if done else "no stamps"))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
