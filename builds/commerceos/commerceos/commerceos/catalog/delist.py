"""the delist feature — the quality flags, gated, and the return leg (CW8).

part: catalog-workflows (spec/parts/catalog-workflows.md), wiring the gated
state executor (CW2, spine/writes.py:_mutate_product_state) to the product
lifecycle (CL1, catalog/lifecycle.py). RULED 2026-07-12.

the shape, end to end:

  1. the queue is quality.py's flagged products (noise + decor), ONE work
     item per product — not one per class. each item carries the exact call
     the executor runs: method mutate_product_state, args {product_id,
     state:"delisted"}, declared consequential. run_feature (the engine)
     stages these through the gate; a consequential proposal PARKS on the
     owner's /approvals queue and does NOT execute in-run.
  2. the store write happens LATER, on the owner's approve, through the one
     write door (writes.execute). only THEN — on a verified read-back — does
     the lifecycle state move.
  3. execute_and_record() is that seam. it runs the approved record's store
     write and, only if the store rendered the change, calls
     lifecycle.transition() to record the matching state (delisted / active /
     archived) with the record's ledger id. so the state field never claims a
     change the store did not actually make, and catalog-lifecycle stays the
     SOLE writer of product state + history.

the invariant this file exists to hold: lifecycle state changes ONLY on a
verified store execution, never at staging. verify rendered, never
files-exist. stdlib + the spine + the gate.
"""

from __future__ import annotations

import sqlite3

from commerceos.catalog import lifecycle, quality
from commerceos.gate import ledger
from commerceos.spine import writes

# the delist feature's config, read by the one engine (workflows.py builds the
# Feature row from these — the classification pattern, so no circular import).
AGENT = "catalog-delist"
METHOD = "mutate_product_state"
DECLARED_TYPE = "consequential"
INTENT = "delist the products the quality gate flagged (noise + decor)"

# lifecycle target state -> the Shopify status the executor verify-renders.
# a delist lands the product in DRAFT (off the storefront); this is the
# report-time verify for the delist batch, whose items are all "delisted".
_DELIST_RENDERED_STATUS = "DRAFT"


def delist_queue(conn: sqlite3.Connection) -> list[dict]:
    """the delist work list: quality.py's flagged products, ONE item per
    product (not per flag class), so each delist approves and records its own
    lifecycle transition. detection is quality.py's, unchanged — this only
    flattens noise + decor into per-product work items carrying the exact
    call the executor runs. the held single-signal near-misses and brand-only
    products are NOT queued (quality's conservative law keeps them back)."""
    cands = quality.compute_delist_candidates(conn)
    work = []
    for klass in ("noise", "decor"):
        for c in cands.get(klass) or []:
            pid = c["product_id"]
            work.append({
                "product_id": pid,
                "handle": c["handle"],
                "flag_class": klass,
                "evidence": c["evidence"],
                "display": f"{klass}: {c['handle']}  [{', '.join(c['evidence'])}]",
                "args": {"product_id": pid, "state": "delisted"},
            })
    return work


def delist_verify(outcome: dict, item: dict) -> bool:
    """counts only when the live store read the delist back: the product is
    off the storefront (status DRAFT), verify-rendered. a write the store did
    not render never counts — the return leg refuses to record state on it."""
    return (bool(outcome.get("verified_rendered"))
            and outcome.get("status") == _DELIST_RENDERED_STATUS)


def delist_progress(conn: sqlite3.Connection) -> dict:
    """the dashboard-card numbers: how many products are delisted as recorded
    (lifecycle truth), and how many flagged products still wait in the queue.
    read live — lifecycle for the recorded state, quality for the backlog."""
    counts = lifecycle.counts_by_state(conn)
    queue = delist_queue(conn)
    return {
        "delisted": counts.get("delisted", 0),
        "queued": len(queue),
        "active": counts.get("active", 0),
    }


def execute_and_record(conn, record_id: str, client=None) -> dict:
    """THE seam — the approval -> execute -> lifecycle chain (the return leg).

    run the approved record's stored state-change through the one write door
    (writes.execute), then, ONLY if the store verify-rendered the change,
    record the matching lifecycle state via catalog-lifecycle, passing this
    record's ledger id. the executor flips the store status and returns a
    verified receipt; catalog-lifecycle is the SOLE writer of the local state
    field + the history row and commits on THAT receipt — so the state never
    claims a change the store did not make.

    this is what the web /approvals resolve path calls for a
    mutate_product_state record after the owner approves. it is state-agnostic:
    the record's args.state (delisted / active / archived) is the lifecycle
    target, so the same seam serves delist, relist, and archive.

    returns {outcome, recorded, transition, product_id, state}: `recorded`
    says whether a lifecycle transition was written (only on a verified store
    change); `transition` is the move dict, or None when the store did not
    render (verify rendered, never files-exist).
    """
    rec = ledger.get(conn, record_id)
    if rec is None:
        raise KeyError(f"no ledger record {record_id}")
    prop = rec["proposal"]
    if prop["method"] != METHOD:
        raise ValueError(
            f"execute_and_record is the state-change seam; record {record_id[:8]} "
            f"runs {prop['method']}, not {METHOD}")
    args = prop["args"]
    product_id = args["product_id"]
    target_state = args["state"]

    outcome = writes.execute(conn, record_id, client)

    # the return leg: state follows a VERIFIED store change, never a staged
    # one and never an unrendered one. a write the store did not read back
    # records no lifecycle move — the store and the state never disagree.
    if not outcome.get("verified_rendered"):
        return {"outcome": outcome, "recorded": False, "transition": None,
                "product_id": product_id, "state": target_state}

    reason = rec.get("rationale") or rec.get("intent") or f"state change ruled ({record_id[:8]})"
    move = lifecycle.transition(
        conn, product_id, target_state, reason,
        by=rec.get("agent") or AGENT, ledger_id=record_id)
    return {"outcome": outcome, "recorded": True, "transition": move,
            "product_id": product_id, "state": target_state}
