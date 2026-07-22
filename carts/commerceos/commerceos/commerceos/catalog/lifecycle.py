"""the product lifecycle — the small, ruled state model (CL1).

part: catalog-lifecycle (spec/parts/catalog-lifecycle.md). every product
sits in exactly ONE of five states, and every move between them is a single
recorded step with a who, a when, and a why. this module is the SOLE writer
of both lifecycle tables:

  product_lifecycle  — one current state per product (the invariant).
  lifecycle_history  — append-only, one row per move.

the five states and the legal moves, RULED 2026-07-12 (encode exactly):

    draft --publish--> active
    active <--raise flag / clear flag--> flagged
    active|flagged --delist--> delisted
    delisted --relist--> active            (relist is a TRANSITION, not a state)
    delisted|flagged --archive--> archived
    archived : terminal — no outgoing move

edit is an ACTION available in any state, never a state. `under-review` and
`relisted` are not states — a flagged product being worked is still flagged;
a relisted product is just active again.

the seam (load-bearing, AGENTS.md one-writer-per-table-set): this part NEVER
writes the store. a customer-visible move (publish / delist / relist /
archive-of-a-live-product) runs the store write through catalog-workflows'
executor (CW2), which returns a verified RECEIPT with its ledger id; only
THEN does the delist feature call transition() here to record the new state
on that verified outcome, passing the ledger_id. so the state field never
claims a change the store did not actually make. transition() is that hook —
it records local state and history, and only local state and history.

stdlib + the spine only.
"""

from __future__ import annotations

from commerceos.gate import ledger

TABLE_SET_NOTE = "lifecycle tables live in the facts migration set (schema.py); this module owns their writes"

# the five states — one, and only one, per product at any time.
STATES = frozenset({"draft", "active", "flagged", "delisted", "archived"})

# from_state -> the states it may legally move to. archived is terminal (no
# outgoing move). this map IS the ruled state machine; transition() reads it
# and refuses anything not listed.
TRANSITIONS: dict[str, frozenset[str]] = {
    "draft":     frozenset({"active"}),                        # publish
    "active":    frozenset({"flagged", "delisted"}),           # raise flag / delist
    "flagged":   frozenset({"active", "delisted", "archived"}),  # clear / delist / archive
    "delisted":  frozenset({"active", "archived"}),            # relist / archive
    "archived":  frozenset(),                                  # terminal
}

# Shopify status -> initial local state, read on sync (never a store write).
_SHOPIFY_STATUS = {"ACTIVE": "active", "DRAFT": "draft", "ARCHIVED": "archived"}


class LifecycleError(Exception):
    """A refused lifecycle operation — an illegal move, or a missing state."""


# ---------- reads ----------

def state_of(conn, product_id: str) -> str | None:
    """The product's current state, or None if it has never been placed."""
    row = conn.execute(
        "SELECT state FROM product_lifecycle WHERE product_id = ?", (product_id,)
    ).fetchone()
    return row["state"] if row else None


def history(conn, product_id: str) -> list[dict]:
    """The product's whole life — its ordered move rows, oldest first."""
    rows = conn.execute(
        'SELECT id, product_id, from_state, to_state, reason, "by", ts, ledger_id'
        " FROM lifecycle_history WHERE product_id = ? ORDER BY id",
        (product_id,),
    )
    return [dict(r) for r in rows]


def counts_by_state(conn) -> dict[str, int]:
    """{state: count} across the whole catalog — the dashboard's shape at a
    glance. Every one of the five states is present (0 when empty), so the
    tallies always sum to the placed-product count."""
    counts = {s: 0 for s in ("draft", "active", "flagged", "delisted", "archived")}
    for r in conn.execute(
        "SELECT state, COUNT(*) AS n FROM product_lifecycle GROUP BY state"
    ):
        counts[r["state"]] = r["n"]
    return counts


def review_queue(conn) -> list[dict]:
    """The flag-review queue — the flagged products a person reviews, each
    carrying its evidence. The evidence is the detector's signal list from
    quality.py when the landed facts still corroborate the flag; otherwise it
    falls back to the lifecycle reason recorded when the flag was raised. A
    work-list, not a graveyard — a flag leaves it only when the operator rules
    and a transition fires."""
    flagged = conn.execute(
        "SELECT product_id, reason FROM product_lifecycle WHERE state = 'flagged'"
        " ORDER BY product_id"
    ).fetchall()

    # best-effort: recompute detector evidence from the landed facts. Guarded —
    # if the facts tables are empty or absent (state-only tests, fresh DB),
    # the lifecycle reason stands as the evidence on its own.
    evidence: dict[str, list[str]] = {}
    try:
        from commerceos.catalog import quality
        cands = quality.compute_delist_candidates(conn)
        for klass in ("noise", "decor"):
            for c in cands.get(klass, []):
                evidence[c["product_id"]] = c["evidence"]
    except Exception:
        evidence = {}

    queue = []
    for r in flagged:
        pid = r["product_id"]
        ev = evidence.get(pid)
        queue.append({
            "product_id": pid,
            "reason": r["reason"],
            "evidence": ev if ev else ([r["reason"]] if r["reason"] else []),
        })
    return queue


# ---------- placement + moves (the sole writers) ----------

def set_initial(conn, product_id: str, shopify_status: str, ts=None) -> str:
    """Place a newly-synced product from its inherited Shopify status:
    ACTIVE -> active, DRAFT -> draft, ARCHIVED -> archived. Idempotent — a
    product already placed is left untouched and its current state returned
    (no duplicate first row). The placement is read from what the store
    already shows; it is NOT a store write. Records the product's first
    history row (who: 'sync', from_state: NULL)."""
    existing = state_of(conn, product_id)
    if existing is not None:
        return existing

    key = (shopify_status or "").strip().upper()
    state = _SHOPIFY_STATUS.get(key)
    if state is None:
        raise LifecycleError(
            f"unknown Shopify status {shopify_status!r} — expected one of "
            f"{sorted(_SHOPIFY_STATUS)}"
        )

    stamp = ledger.now(ts)
    reason = f"synced from Shopify status {key}"
    conn.execute(
        "INSERT INTO product_lifecycle (product_id, state, reason, updated_at)"
        " VALUES (?, ?, ?, ?)",
        (product_id, state, reason, stamp),
    )
    conn.execute(
        'INSERT INTO lifecycle_history (product_id, from_state, to_state, reason, "by", ts, ledger_id)'
        " VALUES (?, NULL, ?, ?, 'sync', ?, NULL)",
        (product_id, state, reason, stamp),
    )
    conn.commit()
    return state


def transition(conn, product_id: str, to_state: str, reason: str, by: str,
               ledger_id: str | None = None, ts=None) -> dict:
    """Move a product to `to_state`, if the move is legal. THE sole mutator of
    the state field and the sole appender of history. Enforces the ruled state
    machine (TRANSITIONS): an illegal move — leaving `archived`, or any arrow
    the machine does not draw — is refused with a clear LifecycleError and
    writes nothing. On a legal move it updates product_lifecycle and appends
    exactly one lifecycle_history row (from, to, who, when, why).

    `ledger_id` records the store write's ledger record when one backed the
    move — this is the delist-feature seam: the executor (CW2) performs and
    verifies the Shopify write, then this is called with the verified
    outcome's ledger id so the state field only ever records a change the
    store actually made. A purely-local move (raise/clear a flag, a
    local-only mark) passes None.
    """
    if to_state not in STATES:
        raise LifecycleError(f"unknown state {to_state!r} — the five are {sorted(STATES)}")

    current = state_of(conn, product_id)
    if current is None:
        raise LifecycleError(
            f"no lifecycle state for product {product_id!r}; call set_initial first"
        )

    allowed = TRANSITIONS[current]
    if to_state not in allowed:
        if not allowed:
            raise LifecycleError(
                f"{current} is terminal: {current} -> {to_state} refused "
                f"(product {product_id!r})"
            )
        raise LifecycleError(
            f"illegal transition {current} -> {to_state} for product {product_id!r}; "
            f"legal from {current}: {sorted(allowed)}"
        )

    stamp = ledger.now(ts)
    conn.execute(
        "UPDATE product_lifecycle SET state = ?, reason = ?, updated_at = ?"
        " WHERE product_id = ?",
        (to_state, reason, stamp, product_id),
    )
    conn.execute(
        'INSERT INTO lifecycle_history (product_id, from_state, to_state, reason, "by", ts, ledger_id)'
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (product_id, current, to_state, reason, by, stamp, ledger_id),
    )
    conn.commit()
    return {"product_id": product_id, "from_state": current, "to_state": to_state,
            "reason": reason, "by": by, "ts": stamp, "ledger_id": ledger_id}


# ---------- named moves (convenience over transition) ----------

def raise_flag(conn, product_id: str, reason: str, by: str = "detector", ts=None) -> dict:
    """active -> flagged. Raised by the detector (quality.py, with its signal
    list as the reason) or by the operator by hand (with a note). A local move
    — raising a flag does not, by default, pull the product from customer
    surfaces (an explicit delist does). Puts the product in the review queue
    with its evidence."""
    return transition(conn, product_id, "flagged", reason, by, ts=ts)


def clear_flag(conn, product_id: str, reason: str = "flag cleared",
               by: str = "operator", ts=None) -> dict:
    """flagged -> active. The flag was wrong or the product is fine; it leaves
    the review queue. A local move."""
    return transition(conn, product_id, "active", reason, by, ts=ts)


def delist(conn, product_id: str, reason: str, by: str = "operator",
           ledger_id: str | None = None, ts=None) -> dict:
    """active|flagged -> delisted. Reversible — relist is one ruling away, and
    a delisted product carries no lost data. Customer-visible, so the store
    write runs through the executor (CW2) + gate FIRST; this records the state
    only on that verified outcome, with its ledger_id."""
    return transition(conn, product_id, "delisted", reason, by, ledger_id=ledger_id, ts=ts)


def relist(conn, product_id: str, reason: str = "relisted", by: str = "operator",
           ledger_id: str | None = None, ts=None) -> dict:
    """delisted -> active. The revenue-recovery path — the product returns
    live. Customer-visible: store write through the executor + gate first,
    state recorded here on the verified outcome."""
    return transition(conn, product_id, "active", reason, by, ledger_id=ledger_id, ts=ts)


def archive(conn, product_id: str, reason: str, by: str = "operator",
            ledger_id: str | None = None, ts=None) -> dict:
    """delisted|flagged -> archived. Terminal and irreversible — always an
    explicit operator ruling, never automated. Archiving a product still live
    on the store also pulls it (a store write through the seam); pass its
    ledger_id when one backed the move."""
    return transition(conn, product_id, "archived", reason, by, ledger_id=ledger_id, ts=ts)


def backfill_from_products(conn) -> int:
    """CL1b — seed the lifecycle from the synced products' Shopify status.
    idempotent (set_initial is), so it is safe to re-run; returns the count
    of products seeded. this is what makes the dashboard's state view real."""
    n = 0
    for pid, status in conn.execute("SELECT shopify_id, status FROM products"):
        set_initial(conn, pid, status or "ACTIVE")
        n += 1
    return n


def report_status(conn) -> None:
    """the lifecycle's self-report — its own row on /parts: counts by state and
    the flag-review queue depth. reporting must never take a surface down."""
    from commerceos.web import registry
    try:
        counts = counts_by_state(conn)
        flags = len(review_queue(conn))
    except Exception:
        registry.report(conn, "catalog-lifecycle", _LIFECYCLE_IS,
                        state="starting", functions=["lifecycle", "flag-review"])
        return
    total = sum(counts.values())
    live = " · ".join(f"{s} {n}" for s, n in counts.items() if n)
    summary = (f"{total} products tracked"
               + (f" · {live}" if live else "")
               + (f" · {flags} flags awaiting review" if flags else ""))
    registry.report(
        conn, "catalog-lifecycle", _LIFECYCLE_IS,
        state="idle", functions=["lifecycle", "flag-review"],
        last_run={"summary": summary, "ok": True, "counts": counts, "flags": flags},
    )


_LIFECYCLE_IS = ("the product lifecycle — draft/active/flagged/delisted/archived, "
                 "every move on the record with who/when/why (O2, O4)")
