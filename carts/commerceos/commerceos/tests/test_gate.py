"""A4's checks — the part spec's battery (spec/parts/gate-and-record.md
## checks), v0's red-team findings recreated, not trusted: consequential
without approval parks; an approved handle works exactly once and a replay
is refused; expired approvals do not execute; self-downgrade is gated at
the stricter class; an unknown method classifies fit_critical; an args-hash
or method mismatch is refused; a threshold move lands its own ledger
record; the anti-bypass grant check this part ships."""

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from commerceos.db import connect
from commerceos.gate import gate, handles, ledger, policy

REPO_ROOT = Path(__file__).resolve().parents[1]
TABLE_PATH = REPO_ROOT / "stores" / "demostore" / "policy-table.json"
TABLE = json.loads(TABLE_PATH.read_text())

T0 = datetime(2026, 7, 11, 8, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "test.db")
    ledger.ensure_schema(c)
    yield c
    c.close()


def prop(**over):
    p = {
        "agent": "pricing-agent",
        "function": "pricing",
        "method": "mutate_price",
        "args": {"variant": "v1", "amount_minor": 9900, "currency": "AED"},
        "intent": "raise the tent price to protect margin",
        "rationale": "landed orders show margin below floor",
        "impact": {"money_minor": 9900},
        "provenance": {"cite": "facts:orders@2026-07-10"},
    }
    p.update(over)
    return p


def submit(conn, table=TABLE, now_ts=T0, **over):
    return gate.submit(conn, prop(**over), table=table, now_ts=now_ts)


# ---------- config + classifier ----------

def test_the_default_table_is_demostores():
    table = policy.load_table()  # resolves stores/demostore/policy-table.json
    assert table["version"] == 1
    overrides = table["methods"]["mutate_product_field"]["field_overrides"]
    assert set(overrides) == {"temp_rating", "load_limit", "weight_limit",
                              "waterproof_rating", "ip_rating", "certifications",
                              "safety_rating", "material_spec"}
    assert all(v == "fit_critical" for v in overrides.values())
    assert table["unknown_method_class"] == "fit_critical"


def test_reads_are_free_no_record(conn):
    res = submit(conn, method="read_product", args={"id": "p1"})
    assert res["decision"] == "allow" and res["record_id"] is None
    assert ledger.query(conn) == []


def test_metadata_never_changes_the_binding():
    bare = {"variant": "v1", "amount_minor": 9900}
    noted = {**bare, "intent": "note", "rationale": "why", "provenance": "cite"}
    assert policy.args_hash("mutate_price", bare) == policy.args_hash("mutate_price", noted)
    other = {**bare, "amount_minor": 8800}
    assert policy.args_hash("mutate_price", bare) != policy.args_hash("mutate_price", other)


# ---------- behavior 1: reversible pass-through, never silent ----------

def test_reversible_passes_through_recorded_never_silent(conn):
    res = submit(conn, function="catalog-enrichment", agent="listing-writer",
                 method="mutate_seo", args={"product": "p1", "value": "Alpine Tent"})
    assert res["decision"] == "allow" and res["action_type"] == "reversible"
    rec = ledger.get(conn, res["record_id"])
    assert rec["status"] == "executing"  # approved, handle consumed, one motion
    assert rec["gate"] == {"required": False, "decision": "approved",
                           "by": "policy:auto", "ts": ledger.now(T0)}
    h = handles.get(conn, rec["id"])
    assert h["consumed_at"] is not None  # even the auto lane consumes a handle
    assert [e["kind"] for e in ledger.events(conn, kind="gate.auto_approved")] != []
    done = gate.report_outcome(conn, rec["id"], {"ok": True, "shopify_id": "p1"},
                               now_ts=T0 + timedelta(seconds=3))
    assert done["status"] == "executed" and done["outcome"]["ok"] is True


# ---------- behavior 2: consequential parks, agent cannot resolve ----------

def test_consequential_without_approval_is_refused_and_parked(conn):
    res = submit(conn)
    assert res["decision"] == "parked" and res["status"] == "pending"
    assert res["expires_at"] == ledger.now(T0 + timedelta(minutes=30))  # money: 30m
    rec = ledger.get(conn, res["record_id"])
    assert rec["status"] == "pending" and rec["gate"]["decision"] == "pending"
    assert handles.get(conn, rec["id"]) is None  # no approval, no handle
    # the queue reads live-at-T0: past its expiry the row is lapsed, not a wait
    assert [r["id"] for r in ledger.pending_queue(conn, ts=T0)] == [rec["id"]]
    assert [r["id"] for r in ledger.lapsed_queue(conn, ts=T0 + timedelta(hours=1))] == [rec["id"]]
    assert ledger.events(conn, kind="gate.pending")
    # an unknown function fails safe: gated even for a reversible method
    res2 = submit(conn, function="mystery", method="mutate_seo", args={"product": "p1"})
    assert res2["decision"] == "parked"


def test_no_approve_verb_on_the_agent_facing_surface(conn):
    first, again = submit(conn), submit(conn)  # re-filing never approves
    for res in (first, again):
        assert res["decision"] == "parked"
        assert "approve" not in " ".join(res.keys())
        assert ledger.get(conn, res["record_id"])["status"] == "pending"
    assert not hasattr(gate, "approve")  # resolve() is the web surface's, not an agent verb
    with pytest.raises(ValueError):
        gate.resolve(conn, first["record_id"], "auto-yes", by="pricing-agent", now_ts=T0)


# ---------- behavior 3 + the handle laws ----------

def test_approved_handle_works_exactly_once_replay_refused(conn):
    parked = submit(conn)
    rec = gate.resolve(conn, parked["record_id"], "approved", by="owner",
                       now_ts=T0 + timedelta(minutes=5))
    assert rec["status"] == "approved" and rec["gate"]["by"] == "owner"
    h = handles.get(conn, rec["id"])
    assert h["consumed_at"] is None and h["expires_at"] == rec["expires_at"]

    took = handles.validate_and_consume(conn, rec["id"], "mutate_price",
                                        prop()["args"], ts=T0 + timedelta(minutes=6))
    assert took["ok"] is True
    assert ledger.get(conn, rec["id"])["status"] == "executing"

    replay = handles.validate_and_consume(conn, rec["id"], "mutate_price",
                                          prop()["args"], ts=T0 + timedelta(minutes=7))
    assert replay["ok"] is False and "replay" in replay["reason"]

    done = gate.report_outcome(conn, rec["id"], {"ok": True}, now_ts=T0 + timedelta(minutes=8))
    assert done["status"] == "executed"


def test_args_hash_or_method_mismatch_is_refused(conn):
    parked = submit(conn)
    rec = gate.resolve(conn, parked["record_id"], "approved", by="owner", now_ts=T0)
    tweaked = {"variant": "v1", "amount_minor": 100, "currency": "AED"}  # not what was approved
    res = handles.validate_and_consume(conn, rec["id"], "mutate_price", tweaked, ts=T0)
    assert res["ok"] is False and "args-hash mismatch" in res["reason"]
    res = handles.validate_and_consume(conn, rec["id"], "mutate_inventory_adjust",
                                       prop()["args"], ts=T0)
    assert res["ok"] is False and "method mismatch" in res["reason"]
    assert handles.get(conn, rec["id"])["consumed_at"] is None  # refusals never consume
    # the exact approved call, notes attached, still lands: metadata is stripped
    ok = handles.validate_and_consume(conn, rec["id"], "mutate_price",
                                      {**prop()["args"], "intent": "note"}, ts=T0)
    assert ok["ok"] is True


# ---------- behaviors 4 + 5: reject, expiry ----------

def test_reject_stores_reason_and_nothing_executes(conn):
    parked = submit(conn)
    rec = gate.resolve(conn, parked["record_id"], "rejected", by="owner",
                       reason="wrong variant", now_ts=T0 + timedelta(minutes=1))
    assert rec["status"] == "rejected" and rec["gate"]["reason"] == "wrong variant"
    assert handles.get(conn, rec["id"]) is None  # no handle, so no write path
    assert ledger.events(conn, kind="gate.rejected")


def test_expired_pending_is_no_longer_approvable(conn):
    parked = submit(conn)  # money move: expires T0+30m
    with pytest.raises(ledger.StateError):
        gate.resolve(conn, parked["record_id"], "approved", by="owner",
                     now_ts=T0 + timedelta(minutes=45))
    rec = ledger.get(conn, parked["record_id"])
    assert rec["status"] == "expired" and rec["gate"]["decision"] == "expired"
    with pytest.raises(ledger.StateError):  # still not approvable after the flip
        gate.resolve(conn, parked["record_id"], "approved", by="owner",
                     now_ts=T0 + timedelta(minutes=46))


def test_an_expired_approval_does_not_execute(conn):
    parked = submit(conn)
    rec = gate.resolve(conn, parked["record_id"], "approved", by="owner",
                       now_ts=T0 + timedelta(minutes=5))
    stale = handles.validate_and_consume(conn, rec["id"], "mutate_price",
                                         prop()["args"], ts=T0 + timedelta(minutes=40))
    assert stale["ok"] is False and "expired" in stale["reason"]
    assert handles.get(conn, rec["id"])["consumed_at"] is None
    with pytest.raises(ledger.StateError):  # never reached executing, so no outcome
        gate.report_outcome(conn, rec["id"], {"ok": True})


def test_expire_sweep_flips_only_whats_lapsed(conn):
    money = submit(conn)                                # expires T0+30m
    slow = submit(conn, method="mutate_meltdown")       # unknown -> 1h default
    swept = gate.expire_sweep(conn, now_ts=T0 + timedelta(minutes=45))
    assert swept == [money["record_id"]]
    assert ledger.get(conn, money["record_id"])["status"] == "expired"
    assert ledger.get(conn, slow["record_id"])["status"] == "pending"
    assert ledger.events(conn, kind="gate.expired")


# ---------- the classifier under attack ----------

def test_self_downgrade_is_gated_at_the_stricter_class_and_flagged(conn):
    res = submit(conn, declared_type="reversible")  # a price change is not reversible
    assert res["decision"] == "parked"
    assert res["action_type"] == "consequential"  # the stricter class stands
    assert res["flag"] == "self-downgrade-attempt"
    assert ledger.get(conn, res["record_id"])["gate"]["flag"] == "self-downgrade-attempt"
    # declaring HIGHER is honored: a nominally reversible edit gates
    up = submit(conn, function="catalog-enrichment", method="mutate_seo",
                args={"product": "p1", "value": "x"}, declared_type="consequential")
    assert up["decision"] == "parked" and up["action_type"] == "consequential"


def test_an_unknown_method_classifies_fit_critical_and_gates(conn):
    res = submit(conn, method="mutate_meltdown", args={"anything": 1})
    assert res["decision"] == "parked"
    assert res["action_type"] == "fit_critical"
    assert res["flag"] == "unknown-method"
    assert res["expires_at"] == ledger.now(T0 + timedelta(hours=1))  # non-money default


def test_a_fit_critical_field_gates_even_on_a_reversible_method(conn):
    res = submit(conn, function="catalog-enrichment", agent="listing-writer",
                 method="mutate_product_field",
                 args={"product": "p1", "field": "temp_rating", "value": "-10C"})
    assert res["decision"] == "parked" and res["action_type"] == "fit_critical"
    pub = submit(conn, function="catalog-enrichment", method="mutate_product_field",
                 args={"product": "p1", "field": "title", "value": "x", "state": "publish"})
    assert pub["decision"] == "parked" and pub["action_type"] == "consequential"


def test_the_money_threshold_is_the_dial_and_fit_critical_never_autos(conn):
    table = copy.deepcopy(TABLE)
    table["functions"]["pricing"]["money_threshold"] = 5000
    under = submit(conn, table=table, args={"variant": "v1", "amount_minor": 4900})
    assert under["decision"] == "allow"  # at or under the dial: auto, still recorded
    over = submit(conn, table=table, args={"variant": "v1", "amount_minor": 5100})
    assert over["decision"] == "parked"
    blank = submit(conn, table=table, args={"variant": "v1"})  # no amount: fail safe
    assert blank["decision"] == "parked"
    rigged = {"functions": {"x": {"auto_approve": ["reversible", "fit_critical"]}}, "methods": {}}
    assert policy.decide("x", "fit_critical", table=rigged) == "gate"  # always human-gated


# ---------- behavior 6: the threshold move ----------

def test_a_threshold_move_lands_its_own_ledger_record(conn, tmp_path):
    table_copy = tmp_path / "policy-table.json"
    table_copy.write_text(TABLE_PATH.read_text())
    rec = gate.move_threshold(conn, "pricing", "money_threshold", 5000,
                              by="owner", why="trust ratchet: first widening after 30 clean days",
                              table_path=table_copy, now_ts=T0)
    assert json.loads(table_copy.read_text())["functions"]["pricing"]["money_threshold"] == 5000
    assert rec["function"] == "policy" and rec["status"] == "executed"
    assert rec["gate"]["by"] == "owner"
    assert rec["proposal"]["args"] == {"function": "pricing", "key": "money_threshold",
                                       "old": 0, "new": 5000}
    assert rec["rationale"].startswith("trust ratchet")
    assert rec["outcome"]["old"] == 0 and rec["outcome"]["new"] == 5000
    assert handles.get(conn, rec["id"])["consumed_at"] is not None  # same one-law write path
    assert ledger.events(conn, kind="policy.threshold_moved")


def test_the_threshold_move_is_owner_only_and_never_silent(conn, tmp_path):
    table_copy = tmp_path / "policy-table.json"
    table_copy.write_text(TABLE_PATH.read_text())
    with pytest.raises(ValueError):  # a name goes on the move
        gate.move_threshold(conn, "pricing", "money_threshold", 100, by="", why="x",
                            table_path=table_copy)
    with pytest.raises(ValueError):  # and its why
        gate.move_threshold(conn, "pricing", "money_threshold", 100, by="owner", why="  ",
                            table_path=table_copy)
    with pytest.raises(ValueError):  # only the two movable keys
        gate.move_threshold(conn, "pricing", "expiry_seconds", 60, by="owner", why="w",
                            table_path=table_copy)
    with pytest.raises(ValueError):  # fit_critical is never auto-approvable
        gate.move_threshold(conn, "pricing", "auto_approve", ["fit_critical"],
                            by="owner", why="w", table_path=table_copy)
    with pytest.raises(ValueError):  # minor units, an integer >= 0
        gate.move_threshold(conn, "pricing", "money_threshold", -5, by="owner", why="w",
                            table_path=table_copy)
    assert ledger.query(conn) == []  # a refused move records nothing


# ---------- behavior 7: the anti-bypass wall's check ----------

def test_check_grant_ships_the_anti_bypass_wall():
    gated = {"commerce.mutate_price", "commerce.mutate_product_field"}
    reads = {"commerce.read_product", "commerce.read_orders"}
    clean = ["commerce.mutate_price", "commerce.read_product"]
    assert gate.check_grant(clean, gated, reads) == []
    # v0's red-team hole: another mutate-capable tool, or raw Bash, walks past the gate
    leaky = clean + ["Bash", "shopify_admin.graphql_mutation"]
    assert gate.check_grant(leaky, gated, reads) == ["Bash", "shopify_admin.graphql_mutation"]
    assert gate.check_grant(["Bash"], gated_tools=["Bash"]) == ["Bash"]  # never grantable
