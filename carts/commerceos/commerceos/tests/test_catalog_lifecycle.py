"""CL1's checks: the five-state lifecycle as local state (no store writes).

the ruled model, encoded exactly — sync placement maps Shopify status onto
draft/active; a detector flag reaches the review queue with its reason and
clears back to active; a legal move appends exactly one who/when/why history
row and delist<->relist round-trips; an illegal move (archived is terminal)
is refused with a clear error and writes nothing; counts_by_state tallies the
catalog. lifecycle.py is the SOLE writer of both tables.
"""

import pytest

from commerceos.catalog import lifecycle as L
from commerceos.db import connect
from commerceos.spine.schema import ensure_schema


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "t.db")
    ensure_schema(c)
    yield c
    c.close()


def test_set_initial_maps_shopify_status_to_state(conn):
    assert L.set_initial(conn, "p-live", "ACTIVE") == "active"
    assert L.set_initial(conn, "p-draft", "DRAFT") == "draft"
    assert L.set_initial(conn, "p-gone", "ARCHIVED") == "archived"
    assert L.state_of(conn, "p-live") == "active"
    assert L.state_of(conn, "p-draft") == "draft"

    # the first row is the sync placement: from NULL, who 'sync'.
    rows = L.history(conn, "p-live")
    assert len(rows) == 1
    assert rows[0]["from_state"] is None and rows[0]["to_state"] == "active"
    assert rows[0]["by"] == "sync"


def test_set_initial_is_idempotent(conn):
    L.set_initial(conn, "p1", "ACTIVE")
    # re-syncing leaves the state untouched and appends no duplicate first row.
    assert L.set_initial(conn, "p1", "DRAFT") == "active"
    assert L.state_of(conn, "p1") == "active"
    assert len(L.history(conn, "p1")) == 1


def test_set_initial_rejects_unknown_status(conn):
    with pytest.raises(L.LifecycleError):
        L.set_initial(conn, "p1", "PENDING")


def test_raise_flag_reaches_review_queue_and_clears(conn):
    L.set_initial(conn, "p1", "ACTIVE")
    L.raise_flag(conn, "p1", reason="decor_keyword, decor_type", by="detector")
    assert L.state_of(conn, "p1") == "flagged"

    queue = L.review_queue(conn)
    assert len(queue) == 1
    row = queue[0]
    assert row["product_id"] == "p1"
    assert row["reason"] == "decor_keyword, decor_type"
    # evidence falls back to the lifecycle reason when no landed facts corroborate.
    assert "decor_keyword, decor_type" in row["evidence"]

    L.clear_flag(conn, "p1", reason="reviewed, product is fine", by="operator")
    assert L.state_of(conn, "p1") == "active"
    assert L.review_queue(conn) == []


def test_legal_transition_appends_exactly_one_history_row_with_who_when_why(conn):
    L.set_initial(conn, "p1", "ACTIVE")           # 1 row (sync)
    before = len(L.history(conn, "p1"))
    move = L.delist(conn, "p1", reason="pulled on suspicion", by="operator")
    after = L.history(conn, "p1")

    assert len(after) == before + 1               # exactly one appended
    last = after[-1]
    assert last["from_state"] == "active" and last["to_state"] == "delisted"
    assert last["by"] == "operator"               # who
    assert last["reason"] == "pulled on suspicion"  # why
    assert last["ts"]                              # when
    assert move["to_state"] == "delisted"


def test_delist_then_relist_round_trips_with_two_history_rows(conn):
    L.set_initial(conn, "p1", "ACTIVE")
    L.delist(conn, "p1", reason="pulled", by="operator", ledger_id="led-delist")
    assert L.state_of(conn, "p1") == "delisted"

    L.relist(conn, "p1", reason="fixed, back live", by="operator", ledger_id="led-relist")
    assert L.state_of(conn, "p1") == "active"      # relisted product is just active again

    rows = L.history(conn, "p1")
    # sync + delist + relist = 3 rows; the pair carries its ledger ids (the seam).
    assert len(rows) == 3
    assert rows[1]["to_state"] == "delisted" and rows[1]["ledger_id"] == "led-delist"
    assert rows[2]["to_state"] == "active" and rows[2]["ledger_id"] == "led-relist"


def test_illegal_transition_out_of_archived_is_refused_and_writes_nothing(conn):
    L.set_initial(conn, "p1", "ARCHIVED")
    before = L.history(conn, "p1")

    with pytest.raises(L.LifecycleError) as exc:
        L.transition(conn, "p1", "active", reason="try to revive", by="operator")
    assert "terminal" in str(exc.value)

    # archived is unchanged; no history row written.
    assert L.state_of(conn, "p1") == "archived"
    assert L.history(conn, "p1") == before


def test_illegal_transition_between_unconnected_states_is_refused(conn):
    L.set_initial(conn, "p1", "DRAFT")
    # draft only publishes to active; draft -> delisted is not an arrow.
    with pytest.raises(L.LifecycleError):
        L.transition(conn, "p1", "delisted", reason="nope", by="operator")
    assert L.state_of(conn, "p1") == "draft"


def test_transition_on_unplaced_product_is_refused(conn):
    with pytest.raises(L.LifecycleError):
        L.transition(conn, "ghost", "active", reason="x", by="operator")


def test_counts_by_state_tallies_the_catalog(conn):
    L.set_initial(conn, "a1", "ACTIVE")
    L.set_initial(conn, "a2", "ACTIVE")
    L.set_initial(conn, "d1", "DRAFT")
    L.set_initial(conn, "g1", "ARCHIVED")
    # move a2 active -> flagged -> delisted.
    L.raise_flag(conn, "a2", reason="looks off")
    L.delist(conn, "a2", reason="pulled")

    counts = L.counts_by_state(conn)
    assert counts == {"draft": 1, "active": 1, "flagged": 0,
                      "delisted": 1, "archived": 1}
    # every product placed exactly once; tallies sum to the placed count.
    assert sum(counts.values()) == 4


def test_archive_from_flagged_and_from_delisted(conn):
    L.set_initial(conn, "p1", "ACTIVE")
    L.raise_flag(conn, "p1", reason="bad")
    L.archive(conn, "p1", reason="gone for good", by="operator")
    assert L.state_of(conn, "p1") == "archived"

    L.set_initial(conn, "p2", "ACTIVE")
    L.delist(conn, "p2", reason="pulled")
    L.archive(conn, "p2", reason="done", by="operator")
    assert L.state_of(conn, "p2") == "archived"
