"""the catalog workflow engine — one machine; every catalog feature is config.

RULED 2026-07-12 (spec/parts/catalog-workflows.md): the catalog features —
gtin, classification, merchandising, seo, spec-verification, delist — are the
SAME machine: a queue of products with a gap -> a gated batch -> verify-
rendered before it counts -> progress. a feature differs only by config: its
queue, the write method it runs, its gate class, and its verify check. this
module is that engine; GTIN normalization is the first feature — the template
the others copy.

the loop, per item: build a proposal -> gate.submit (a reversible feature
auto-approves and mints+consumes its handle in one motion; a consequential or
fit-critical feature parks on the /approvals queue) -> for an approved
reversible, writes.execute performs the store write and reads it back -> the
feature's verify decides whether it counts. verify rendered, never
files-exist: a fix counts only when the live store reads it back. stdlib +
the gate + the one write door.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from commerceos.catalog.audit import classify_barcode, gtin_valid
from commerceos.db import connect, default_path
from commerceos.gate import gate, ledger, policy
from commerceos.spine import writes

REPO = Path(__file__).resolve().parents[2]
FUNCTION = "catalog-enrichment"


@dataclass
class Feature:
    """one catalog feature, expressed as config over the one engine."""

    name: str
    method: str          # the write-door method its executor runs
    declared_type: str   # reversible | consequential | fit_critical
    agent: str
    queue: Callable[[sqlite3.Connection], list]     # -> work items (each carries 'args' + 'display')
    verify: Callable[[dict, dict], bool]            # (execute outcome, item) -> did it count
    progress: Callable[[sqlite3.Connection], dict]  # the numbers a dashboard card reads
    intent: str = ""
    batch_default: int = 100
    # on a verified count, route the store-truth back into the facts so the
    # progress card + feed don't lag. the callable is the fact-owner's API,
    # never a direct write from the engine (one writer per table-set).
    writeback: Callable[[sqlite3.Connection, dict, dict], None] | None = None
    # the policy function a feature's ledger rows file under. defaults to the
    # module's catalog-enrichment; a feature whose agent has its own registered
    # policy function (e.g. content's content-geo) names it here so its rows
    # read under the right work area — every existing feature keeps the default,
    # so their gate behavior is unchanged.
    function: str = FUNCTION


# --------------------------------------------------------------- GTIN ---
# the first feature (the template). the data is already landed — most stored
# barcodes are real GTINs wearing a spreadsheet artifact; this normalizes them
# in place. no sourcing, no external dependency. gate class: reversible.


def normalize_barcode(b) -> str | None:
    """the fixable-artifact repair: strip a spreadsheet apostrophe, or restore
    a UPC's dropped leading zero, returning the checksum-valid GTIN. returns
    None when the barcode is not a one-step fix — already valid, or genuinely
    not a GTIN. reuses the audit's classifier so the engine and the audit can
    never disagree about what is fixable."""
    kind = classify_barcode(b)
    s = (b or "").strip().lstrip("'")
    if kind == "apostrophe_wrapped_gtin":
        return s
    if kind == "upc_missing_leading_zero":
        return "0" + s
    return None


def _gtin_queue(conn: sqlite3.Connection) -> list:
    """every variant one normalization away from a valid GTIN — the fixable
    artifacts, not a sourcing project. the args carry product_id + variant_id
    because the store write is a bulk-variant update scoped to its product."""
    work = []
    for vid, pid, bc in conn.execute(
        "SELECT shopify_id, product_id, barcode FROM variants"
    ):
        new = normalize_barcode(bc)
        if new is None:
            continue
        work.append({
            "variant_id": vid,
            "product_id": pid,
            "old": (bc or "").strip(),
            "new": new,
            "display": f"{pid}  {(bc or '').strip()!r} -> {new}",
            "args": {"field": "barcode", "product_id": pid,
                     "variant_id": vid, "value": new},
        })
    return work


def _gtin_verify(outcome: dict, item: dict) -> bool:
    """counts only if the store read the new barcode back AND that value is a
    checksum-valid GTIN. a bad-checksum value never counts, and a write the
    store did not render never counts."""
    return (bool(outcome.get("ok"))
            and outcome.get("barcode") == item["new"]
            and gtin_valid(item["new"]))


def _gtin_writeback(conn: sqlite3.Connection, item: dict, outcome: dict) -> None:
    """route the store-verified barcode back into the facts via the spine (the
    variants fact owner), so the audit, progress card, and feed read truth
    without waiting for the next full sync."""
    from commerceos.spine import connector_shopify
    connector_shopify.writeback_variant_barcode(conn, item["variant_id"], item["new"])


def _gtin_progress(conn: sqlite3.Connection) -> dict:
    """the dashboard-card numbers: how many barcodes are valid GTINs as stored,
    and how many fixable artifacts still wait. read live from the facts."""
    kinds: dict = {}
    for (bc,) in conn.execute("SELECT barcode FROM variants"):
        k = classify_barcode(bc)
        kinds[k] = kinds.get(k, 0) + 1
    total = sum(kinds.values())
    valid = kinds.get("valid_gtin_as_stored", 0)
    fixable = (kinds.get("apostrophe_wrapped_gtin", 0)
               + kinds.get("upc_missing_leading_zero", 0))
    return {"valid": valid, "total": total, "fixable_remaining": fixable,
            "rate": round(valid / total, 4) if total else 0.0}


GTIN = Feature(
    name="gtin",
    method="mutate_variant_field",
    declared_type="reversible",
    agent="catalog-gtin",
    queue=_gtin_queue,
    verify=_gtin_verify,
    progress=_gtin_progress,
    writeback=_gtin_writeback,
    # rendered on home's record card — plain words, no insider terms.
    intent="fix barcodes that are one spreadsheet slip away from valid",
)

# ----------------------------------------------------- CLASSIFICATION ---
# the second feature — pure config over the same engine, proving the engine is
# a real template. it persists each product's locked taxonomy category on the
# commerceos.category metafield, resolved from product_type. the resolver, the
# queue, verify, progress, and the write-back all live in classification.py;
# this is only the config row that wires them into the one engine. gate class:
# reversible (a metafield is fully reversible). the genuinely-unresolvable
# products are left OUT of the queue — silence over guesses.

from commerceos.catalog import classification as _cls  # noqa: E402

CLASSIFICATION = Feature(
    name="classification",
    method="mutate_product_field",
    declared_type="reversible",
    agent="catalog-classification",
    queue=_cls.classification_queue,
    verify=_cls.classification_verify,
    progress=_cls.classification_progress,
    writeback=_cls.classification_writeback,
    intent="persist each product's locked taxonomy category on the commerceos.category metafield",
    batch_default=200,
)

# ------------------------------------------------------------- DELIST ---
# the third feature — the quality gate's flags, gated. pure config over the
# same engine; its queue, verify, and progress live in delist.py, alongside
# execute_and_record (the approval -> execute -> lifecycle return leg, CW8).
# gate class: consequential — a state change PARKS, it is never reversible-
# by-default, so run_feature only STAGES parked proposals here; nothing flips
# in-run. one proposal PER PRODUCT (not per flag class), so each delist
# approves and records its own lifecycle transition on a verified store write.

from commerceos.catalog import delist as _delist  # noqa: E402

DELIST = Feature(
    name="delist",
    method=_delist.METHOD,
    declared_type=_delist.DECLARED_TYPE,
    agent=_delist.AGENT,
    queue=_delist.delist_queue,
    verify=_delist.delist_verify,
    progress=_delist.delist_progress,
    intent=_delist.INTENT,
)

# ------------------------------------------------------ VERIFICATION ---
# the fourth feature — the spec-verification legwork, gated (V2, on CW7).
# file-driven like the pilot: the queue reads the newest judged findings
# file (the evidence the legwork gathered); no findings file means an EMPTY
# queue — no legwork, no proposals, honestly. declared fit_critical, so
# every proposal PARKS at gate.submit (the wall, not a convention) and
# run_feature only stages here, exactly like DELIST. execution happens
# LATER, on the owner's approve, through the web resolve path calling
# verify_sources.execute_and_record — the local flip + the render check.

from commerceos.catalog import verify_sources as _verify  # noqa: E402

FINDINGS_DIR = REPO / "reports"
FINDINGS_GLOB = "verify-pilot-*-findings.json"


def _latest_findings() -> dict | None:
    """the newest findings file, judged (verdicts stamped mechanically).
    None when no legwork has landed or the file refuses judgment (a found
    value with no source) — either way the queue proposes nothing."""
    files = sorted(FINDINGS_DIR.glob(FINDINGS_GLOB))
    if not files:
        return None
    try:
        return _verify.judge(json.loads(files[-1].read_text()))
    except (ValueError, OSError, KeyError, TypeError):
        return None


def _verification_queue(conn: sqlite3.Connection) -> list:
    """ONE work item per product from the latest judged findings that still
    carries at least one FOUND claim (agree or disagree) on an unverified
    spec row. all-not_found products have nothing to put before the owner;
    fully verified products are done; a product whose claims drifted under
    the findings file is dropped (check_against_claims — never propose on
    stale evidence); an identical proposal already parked is not re-staged,
    so re-runs never stack the owner's queue."""
    findings = _latest_findings()
    if findings is None:
        return []
    work = []
    for p in findings["products"]:
        try:
            _verify.check_against_claims(conn, {"products": [p]})
        except ValueError:
            continue
        found = [c for c in p["claims"] if c["verdict"] in ("agree", "disagree")]
        if not found:
            continue
        unverified = {r[0] for r in conn.execute(
            "SELECT field FROM spec_claims WHERE product = ? AND verified = 0",
            (p["product_id"],))}
        if not any(c["field"] in unverified for c in found):
            continue
        prop = _verify.build_proposal(p)   # the pilot's own shape, reused verbatim
        try:
            if _verify._already_pending(
                    conn, policy.args_hash(prop["method"], prop["args"])):
                continue   # already on the owner's queue — pending, not work
        except sqlite3.OperationalError:
            pass           # no ledger yet — nothing can be pending
        agree = sum(1 for c in found if c["verdict"] == "agree")
        work.append({
            "product_id": p["product_id"],
            "handle": p["handle"],
            "display": (f"{p['handle']}  {agree} agree / {len(found) - agree} "
                        f"conflict of {len(p['claims'])} claims"),
            "args": prop["args"],
        })
    return work


def _verification_verify(outcome: dict, item: dict) -> bool:
    """counts only when the return leg reports verified_rendered: the flips
    landed AND page, feed, and structured data re-read in agreement
    (execute_and_record's receipt shape)."""
    return bool(outcome.get("verified_rendered"))


def _verification_progress(conn: sqlite3.Connection) -> dict:
    """the dashboard-card numbers over the fit-critical claim set: verified
    against a real source / still unverified / with findings in hand that
    could flip them / proposals waiting on the owner / proposals that waited
    past their window (lapsed). cheap SQL over spec_claims plus one ledger
    read for the verification methods.

    the units are NAMED apart (the coldread's law): total/verified/unverified/
    with_findings count CLAIMS (details); products and products_with_findings
    count PRODUCTS. pending counts LIVE waits only — method-true, this
    feature's own method — while lapsed also claims the old-method pilot rows
    (mutate_product_field on the spec-verification field) that were never
    executable, so home's waits and this card agree on the same facts."""
    total, verified, products = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(verified), 0), COUNT(DISTINCT product)"
        " FROM spec_claims WHERE fit_critical = 1").fetchone()
    pending = lapsed = 0
    try:
        rows = conn.execute(
            "SELECT expires_at, json_extract(proposal, '$.method') AS m"
            " FROM ledger WHERE status = 'pending'"
            " AND (json_extract(proposal, '$.method') = ?"
            "      OR (json_extract(proposal, '$.method') = 'mutate_product_field'"
            "          AND json_extract(proposal, '$.args.field') = ?))",
            (_verify.METHOD, _verify.FIELD)).fetchall()
    except sqlite3.OperationalError:
        rows = []      # no ledger yet — nothing can be pending
    for r in rows:
        if ledger.expired(r["expires_at"]):
            lapsed += 1
        elif r["m"] == _verify.METHOD:
            pending += 1
    with_findings = 0
    ev_products: set = set()
    findings = _latest_findings() if total else None
    if findings is not None:
        # only findings that could actually flip count: the row is still
        # unverified AND the claim value has not drifted under the file.
        unverified_rows = {(r[0], r[1], str(r[2])) for r in conn.execute(
            "SELECT product, field, value FROM spec_claims"
            " WHERE fit_critical = 1 AND verified = 0")}
        for p in findings["products"]:
            for c in p["claims"]:
                if (c["verdict"] in ("agree", "disagree")
                        and (p["product_id"], c["field"], str(c["value"])) in unverified_rows):
                    with_findings += 1
                    ev_products.add(p["product_id"])
    return {"total": total, "verified": verified, "unverified": total - verified,
            "products": products, "with_findings": with_findings,
            "products_with_findings": len(ev_products),
            "pending": pending, "lapsed": lapsed,
            "rate": round(verified / total, 4) if total else 0.0}


def verification_evidence(conn: sqlite3.Connection) -> list[dict]:
    """the evidence behind 'with evidence in hand', product by product: each
    FOUND claim (agree or disagree) whose spec row is still unverified and
    whose claim value has not drifted under the findings file — the SAME
    facts _verification_progress counts, so the card's number and this list
    can never disagree. each claim carries its field, the found value, the
    quote, and the source link, straight from the findings file the queue
    reads."""
    findings = _latest_findings()
    if findings is None:
        return []
    unverified_rows = {(r[0], r[1], str(r[2])) for r in conn.execute(
        "SELECT product, field, value FROM spec_claims"
        " WHERE fit_critical = 1 AND verified = 0")}
    out = []
    for p in findings["products"]:
        claims = [c for c in p["claims"]
                  if c["verdict"] in ("agree", "disagree")
                  and (p["product_id"], c["field"], str(c["value"])) in unverified_rows]
        if claims:
            out.append({"product_id": p["product_id"], "handle": p["handle"],
                        "title": p.get("title"), "claims": claims})
    return out


VERIFICATION = Feature(
    name="verification",
    method=_verify.METHOD,
    declared_type=policy.FIT_CRITICAL,
    agent=_verify.AGENT,
    queue=_verification_queue,
    verify=_verification_verify,
    progress=_verification_progress,
    # writeback stays None: canonical IS the record here. the return leg's
    # own writer (canonical.record_verification) already landed the flip
    # before verify ran — there is no separate facts row to route back into.
    # rendered on home's record card — plain words, no insider terms.
    intent=("check safety-bearing product details against the maker's own page — "
            "conflicts stated for your ruling, never silently resolved"),
)

# ---------------------------------------------------------------- SEO ---
# the fifth feature — the content agent's listing-text drafts (F4a) as a front
# (CW6/F4b). pure config over the same engine; the queue/verify/progress/
# writeback live in fleet/content.py, beside the drafting half. gate class:
# reversible — a plain listing is fully reversible, so a batch HOLDS for one
# glance-approve (WF-approve). the queue is reversible-only BY CONSTRUCTION: a
# draft that quotes a verified spec value declares consequential and is dropped
# from the batch (it rides content.propose_and_run's per-item park instead), and
# the queue also runs the refusal law itself — the engine has no refusal hook.
# function content-geo: the content agent's own registered policy function, so
# these rows read under content's work area, not catalog-enrichment.

from commerceos.fleet import content as _content  # noqa: E402

SEO = Feature(
    name="seo",
    method="mutate_seo",
    declared_type="reversible",
    agent=_content.AGENT,
    queue=_content.seo_queue,
    verify=_content.seo_verify,
    progress=_content.seo_progress,
    writeback=_content.seo_writeback,
    function=_content.FUNCTION,
    # the spec's proposed batch size (catalog-workflows.md).
    batch_default=50,
    # rendered on home's record card — plain words, no insider terms.
    intent="write the search listing for products whose listing is missing or weak",
)

# ------------------------------------------------------ MERCHANDISING ---
# the sixth feature — the V1 keystone (CW5), pure config over the same engine.
# it creates one smart collection per major category (the ~20 definitions live
# as DATA in the active store's collections.json, derived from the locked
# taxonomy); the queue is the definitions not yet on the store, the write is
# the CW4 create_collection door, and progress is collection-coverage — the
# share of products in at least one smart collection (RULED the card's headline
# 2026-07-12). gate class: reversible (a collection deletes cleanly), so under
# WF-approve the ~20-create batch HOLDS for one glance-approve. writeback stays
# None: membership settles asynchronously on the store and lands on the next
# full sync, so coverage reads products.collections "as of the last sync" — no
# per-create writeback can honestly know membership at create time. the main-
# navigation placement is a SEPARATE consequential flow (merchandising.nav_*),
# not this reversible feature — a menu write parks per item.

from commerceos.catalog import merchandising as _merch  # noqa: E402

MERCHANDISING = Feature(
    name="merchandising",
    method=_merch.METHOD,
    declared_type="reversible",
    agent=_merch.AGENT,
    queue=_merch.merch_queue,
    verify=_merch.merch_verify,
    progress=_merch.merch_progress,
    intent="group products into shelves shoppers browse — one smart collection per category",
    batch_default=20,
)

FEATURES = {GTIN.name: GTIN, CLASSIFICATION.name: CLASSIFICATION,
            DELIST.name: DELIST, VERIFICATION.name: VERIFICATION,
            SEO.name: SEO, MERCHANDISING.name: MERCHANDISING}


# ------------------------------------------------------------- engine ---


def run_feature(conn, feature: Feature, client=None, batch_size: int | None = None,
                apply: bool = False, now_ts=None, pause_s: float = 0.0,
                hold: bool = False) -> dict:
    """run one batch of a feature.

    apply=False stages the gated proposals only — a dry run that proves the
    queue and the proposals without touching the store. apply=True (with a
    client) executes the approved reversible writes and verify-renders each.

    hold=True (WF-approve — the batch-approve loop): every proposal PARKS,
    even on a reversible front, and the batch is grouped into one workflow
    run (catalog/runs.py) staged as a preview. nothing executes here; the
    run waits for one glance-approve, which walks each record through the
    standard resolve + one-door walls. hold and apply are exclusive.

    a fix lands in `counted` only when the live store read it back — verify
    rendered, never files-exist. one item's failure (a throttled call, a
    network blip) is isolated: it is marked errored and the batch continues,
    never crashes. because a verified fix writes its truth back into the facts,
    the queue shrinks as it goes — so a batch that stops partway is resumable
    by simply running again. pause_s paces the store calls (be a good API
    citizen; the client has no backoff of its own).

    returns a run report: the queue depth, the per-item log, and the counts a
    dashboard card reads.
    """
    if hold and apply:
        raise ValueError("hold stages for a person's approve — it never applies")
    queue = feature.queue(conn)
    batch = queue[: (batch_size or feature.batch_default)]
    log = []
    counts = {"staged": 0, "executed": 0, "counted": 0, "parked": 0,
              "failed": 0, "errored": 0}
    held_items = []
    prov = [{"source": f"audit:{feature.name}", "fetched_at": ledger.now(now_ts)}]
    for item in batch:
        res = gate.submit(conn, {
            "agent": feature.agent, "function": feature.function, "method": feature.method,
            "args": item["args"], "declared_type": feature.declared_type,
            "intent": feature.intent, "rationale": item["display"], "provenance": prov,
        }, now_ts=now_ts, hold=hold)
        counts["staged"] += 1
        entry = {"item": item["display"], "decision": res["decision"],
                 "record_id": res.get("record_id")}
        if res["decision"] == "parked":
            counts["parked"] += 1
            entry["state"] = ("held for your batch approve" if hold
                              else "parked — awaiting approval")
            if hold:
                # the whole queue item rides into the run row — the approve
                # leg's verify/writeback need the same shape the queue built
                held_items.append({**item, "record_id": res["record_id"],
                                   "state": entry["state"]})
        elif res.get("record_id") and res.get("status") == "executing":
            if apply and client is not None:
                try:
                    out = writes.execute(conn, res["record_id"], client)
                except Exception as e:  # one item's failure never kills the batch
                    counts["errored"] += 1
                    entry["state"] = f"errored — {str(e)[:80]}"
                    log.append(entry)
                    if pause_s:
                        time.sleep(pause_s)
                    continue
                counts["executed"] += 1
                ok = feature.verify(out, item)
                counts["counted" if ok else "failed"] += 1
                entry["state"] = "counted" if ok else "executed, not verified — not counted"
                entry["rendered"] = out
                # a verified fix routes store-truth back into the facts so the
                # progress card + feed don't lag behind the store.
                if ok and feature.writeback is not None:
                    feature.writeback(conn, item, out)
                if pause_s:
                    time.sleep(pause_s)
            else:
                entry["state"] = "staged (dry — not executed)"
        else:
            entry["state"] = f"unexpected gate decision: {res.get('decision')}"
        log.append(entry)
    rep = {"feature": feature.name, "queue_depth": len(queue), "batch": len(batch),
           **counts, "progress": feature.progress(conn), "log": log}
    if hold and held_items:
        from commerceos.catalog import runs as _runs
        _runs.ensure_schema(conn)
        rep["run_id"] = _runs.create(conn, feature.name, held_items, now_ts=now_ts)
    return rep


def render_report(rep: dict) -> str:
    """the run log a person reads — the no-blackbox surface for a batch.
    feature-agnostic: the progress line renders whatever numbers the feature
    reports, so every feature (not just GTIN) prints cleanly."""
    progress = " · ".join(f"{k} {v}" for k, v in rep["progress"].items())
    lines = [
        f"catalog workflow: {rep['feature']}",
        f"  queue {rep['queue_depth']} · batch {rep['batch']} · staged {rep['staged']} · "
        f"executed {rep['executed']} · counted {rep['counted']} · "
        f"parked {rep['parked']} · failed {rep['failed']} · errored {rep['errored']}",
        f"  progress: {progress}",
    ]
    for e in rep["log"][:20]:
        lines.append(f"  {e['state']:<40} {e['item']}")
    if len(rep["log"]) > 20:
        lines.append(f"  ... and {len(rep['log']) - 20} more")
    return "\n".join(lines)


def report_status(conn) -> None:
    """the engine's self-report — its own row on /parts: one line per feature
    with its queue depth. reporting must never take a surface down."""
    from commerceos.web import registry
    parts = []
    for name, feat in FEATURES.items():
        try:
            parts.append(f"{name}: queue {len(feat.queue(conn))}")
        except Exception:
            parts.append(f"{name}: (unavailable)")
    registry.report(
        conn, "catalog-workflows",
        "the catalog workflow engine — one machine, every feature is config: "
        "queue -> gate -> verify-render -> progress (O3, C2)",
        state="idle", functions=sorted(FEATURES),
        last_run={"summary": " · ".join(parts), "ok": True} if parts else None,
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description="run a catalog workflow feature")
    ap.add_argument("feature", choices=sorted(FEATURES),
                    help="which feature to run (gtin is the first)")
    ap.add_argument("--db", default=str(default_path()))
    ap.add_argument("--batch", type=int, default=None, help="max items this run")
    ap.add_argument("--apply", action="store_true",
                    help="execute writes against the store (default: stage only)")
    ap.add_argument("--pause", type=float, default=0.1,
                    help="seconds to wait between store calls (be gentle on the API)")
    a = ap.parse_args(argv)
    conn = connect(a.db)
    ledger.ensure_schema(conn)
    client = writes.ShopifyClient() if a.apply else None
    rep = run_feature(conn, FEATURES[a.feature], client=client,
                      batch_size=a.batch, apply=a.apply, pause_s=a.pause)
    print(render_report(rep))
    return rep


if __name__ == "__main__":
    main()
