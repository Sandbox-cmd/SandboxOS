"""policy — the one classifier the gate and every connector share.

part: the gate + the record (spec/parts/gate-and-record.md, serves O2/O4).
mined from v0's red-team-tested policy.py; the dead kernel's wiring
(hooks, env keying, .mind paths) is not here.

one classifier, shared, so the gate and a connector can never disagree
about what a call is — two classifiers that drift are a bypass.

  classify(method, args, declared, table) -> (action_type, flag)
      field- and state-aware. unknown method fails high (fit_critical).
      stricter-of-two against the agent's declared class — an agent can
      declare HIGHER and be honored, never lower (no self-downgrade).
  decide(function, action_type, method, args, table) -> "auto" | "gate"
      per-function auto-approve classes plus money thresholds in minor
      units. fit_critical never auto-approves, whatever the config says.
  args_hash(method, args) -> sha256 hex
      binds a handle to its exact call. metadata (intent, rationale,
      provenance, ...) is stripped first, so notes can ride along without
      changing the call's identity — and an approved handle still cannot
      be replayed for a different value.

the table is config, per store: stores/<store>/policy-table.json.
mechanism here is store-agnostic; store #2 brings its own table.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from commerceos import stores

REVERSIBLE = "reversible"
CONSEQUENTIAL = "consequential"
FIT_CRITICAL = "fit_critical"
ORDER = (REVERSIBLE, CONSEQUENTIAL, FIT_CRITICAL)
RANK = {t: i for i, t in enumerate(ORDER)}

# what an agent may attach to a call (kept for the ledger, IGNORED for the
# handle binding) vs the world-args that define the call's identity.
METADATA_KEYS = {"intent", "rationale", "provenance", "declared_type", "function", "agent"}

# baseline class for write methods commerceos SHIPS as mechanism (their
# executor bodies live in spine/writes.py). a store's policy-table entry
# always wins; this is only the floor used when a table omits the method,
# so a shipped executor never silently falls to fit_critical for lack of a
# config row. a product state change (delist / relist / archive) is
# CONSEQUENTIAL — it parks for the owner, it is not reversible-by-default.
# a store may still raise it in its own table; it can never be lowered here.
_BUILTIN_METHOD_CLASS = {
    "mutate_product_state": CONSEQUENTIAL,
    # supplier + purchase-order facts entered by hand (SP1): the entry
    # parks for the owner — hand-typed money facts feed COGS, so a typo
    # must meet an eye before it becomes a number the books trust.
    "record_supplier": CONSEQUENTIAL,
    # smart-collection create (CW4): a collection deletes cleanly, so
    # REVERSIBLE — but registered deliberately so the fail-safe never
    # silently parks a shipped executor fit-critical. under WF-approve the
    # ~20-create batch still HOLDS for one glance-approve.
    "create_collection": REVERSIBLE,
    # main-navigation placement (CW4): CONSEQUENTIAL, ruled so on purpose.
    # menuUpdate replaces the whole item tree wholesale (no per-item diff),
    # and the main menu is a default, un-deletable menu whose prior tree we
    # do not snapshot — a nav rewrite is not reversible-in-practice, so the
    # owner rules each one (it parks per item).
    "mutate_menu": CONSEQUENTIAL,
}


def table_path() -> Path:
    """The policy table this process reads — the resolver honors the env override first."""
    return stores.resolve(stores.active_store(), "policy-table.json")


def load_table(path: Path | str | None = None) -> dict:
    return json.loads(Path(path or table_path()).read_text())


def world_args(args: dict | None) -> dict:
    """The canonical world-args for a call — the identity a handle binds to.

    Metadata stripped, keys sorted, values normalized to strings (containers
    as sorted JSON). Both the gate and the connector hash THIS, so they
    always agree regardless of attached notes.
    """
    out = {}
    for k in sorted(args or {}):
        if k in METADATA_KEYS:
            continue
        v = (args or {})[k]
        if v is None:
            continue
        if isinstance(v, (dict, list)):
            out[k] = json.dumps(v, sort_keys=True, separators=(",", ":"))
        else:
            out[k] = str(v)
    return out


def args_hash(method: str, args: dict | None = None) -> str:
    """Canonical hash binding a handle to its exact call. An approved
    temp_rating handle cannot be replayed for a price change, or for a
    different value of the same field — the connector checks this."""
    payload = {"method": method, "args": world_args(args)}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def classify(method: str, args: dict | None = None, declared: str | None = None,
             table: dict | None = None) -> tuple[str, str | None]:
    """The effective action_type for a call, and a flag when something smells.

    Field-level override wins (a wrong temp_rating is a safety claim, not
    content); a state override (publish, delist) raises the class; an
    unknown method fails SAFE-HIGH per the table (fit_critical). Then take
    the stricter of the table's class and the agent's declared class —
    an agent can never self-downgrade; declaring higher is honored.
    """
    table = table or load_table()
    args = args or {}
    flag = None

    spec = table.get("methods", {}).get(method)
    if spec is None and method in _BUILTIN_METHOD_CLASS:
        table_type = _BUILTIN_METHOD_CLASS[method]  # shipped method, table omitted it
    elif spec is None:
        table_type = table.get("unknown_method_class", FIT_CRITICAL)
        flag = "unknown-method"
    else:
        table_type = spec.get("default", CONSEQUENTIAL)
        field = args.get("field")
        if field and field in spec.get("field_overrides", {}):
            table_type = spec["field_overrides"][field]
        state = args.get("state") or args.get("publish_state")
        if state and state in spec.get("state_overrides", {}):
            table_type = _stricter(table_type, spec["state_overrides"][state])

    effective = table_type
    if declared is not None and declared not in RANK:
        flag = flag or "unknown-declared-class"  # junk declaration: table class stands
    elif declared and RANK[declared] < RANK[table_type]:
        flag = "self-downgrade-attempt"  # refused; the stricter table class stands
    elif declared:
        effective = _stricter(declared, table_type)  # declaring higher is honored
    return effective, flag


def decide(function: str, action_type: str, method: str | None = None,
           args: dict | None = None, table: dict | None = None) -> str:
    """auto (auto-approve, still recorded) vs gate (parks for the owner).

    Per-function autonomy: only listed auto_approve classes run free. A
    consequential money move at or under the function's money_threshold
    (minor units, > 0) also autos — the trust-ratchet dial. fit_critical
    NEVER autos, whatever the config says: always human-gated. Unknown
    function fails safe: gate.
    """
    table = table or load_table()
    if action_type == FIT_CRITICAL:
        return "gate"
    fn = table.get("functions", {}).get(function)
    if not fn:
        return "gate"
    if action_type in fn.get("auto_approve", []):
        return "auto"
    threshold = fn.get("money_threshold", 0) or 0
    if action_type == CONSEQUENTIAL and threshold > 0 and _is_money(method, table):
        amount = money_amount(args)
        if amount is not None and amount <= threshold:
            return "auto"
    return "gate"


def money_amount(args: dict | None) -> int | None:
    """The minor-unit amount a money move carries, or None (None gates)."""
    args = args or {}
    for key in ("amount_minor", "amount"):
        if key in args and args[key] is not None:
            try:
                return int(args[key])
            except (TypeError, ValueError):
                return None
    return None


def is_read(method: str, table: dict | None = None) -> bool:
    table = table or load_table()
    return bool(table.get("methods", {}).get(method, {}).get("_read"))


def _is_money(method: str | None, table: dict) -> bool:
    if not method:
        return False
    return bool(table.get("methods", {}).get(method, {}).get("_money"))


def _stricter(a: str, b: str) -> str:
    return a if RANK.get(a, 0) >= RANK.get(b, 0) else b
