"""the web surface — the brain's face. registry-driven: a part that
reports appears; a silent part renders stale, never vanishes. viewing is
free; acting goes through the gate's APIs (wired in C2/C3)."""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import date
from pathlib import Path
from html import escape as html_escape, unescape as html_unescape
from urllib.parse import parse_qs, quote, urlencode

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from commerceos import __version__
from commerceos import stores
from commerceos.db import connect
from commerceos.web import registry
from commerceos.web import teletext as tt
from commerceos.web import fusion, triage
from commerceos.web.auth import (
    COOKIE_NAME,
    claim_device,
    identity_label,
    is_localhost,
    list_devices,
    pair_device,
    require_operator,
    revoke_device,
)
from commerceos.gate import gate, ledger, policy
from commerceos.fleet import manifest as fleet_manifest
from commerceos.catalog import workflows as catalog_workflows
from commerceos.catalog import lifecycle as catalog_lifecycle
from commerceos.catalog import runs as catalog_runs
from commerceos.gate.status import report_status as gate_report
from commerceos.spine.status import report_status as spine_report

app = FastAPI(title="commerceos", version=__version__)

_subscribers: set[asyncio.Queue] = set()

# --- plain words for a person -------------------------------------------
# the feature keys (gtin, classification, delist, ...) are CODE — they live in
# FEATURES and in URLs like /catalog/run/gtin, and never change. these are the
# words a person actually reads on screen.
FEATURE_LABELS = {
    "gtin": "barcodes",
    "classification": "categories",
    "merchandising": "collections",
    "delist": "remove from store",
    "verification": "spec check",
    "seo": "listing text",
    "images": "photos",
    "specs": "product details",
    "specs_structured": "product details",
}


def feature_label(key: str) -> str:
    return FEATURE_LABELS.get(key, key.replace("_", " "))


# plain words for the raw counters each feature reports. shown value-first
# ("3 left to fix"), never as the code identifier.
PROGRESS_LABELS = {
    "valid": "valid",
    "total": "total",
    "fixable_remaining": "left to fix",
    "written": "written",
    "weak": "missing or weak",
    "to_draft": "ready to draft",
    "waiting": "waiting on you, item by item",
    "held_back": "held back",
    "resolved": "in a category",
    "queue_remaining": "to do",
    "delisted": "removed",
    # candidates, not staged waits — "waiting for your call" is reserved for
    # rows already in decisions (the UI-truth re-walk's one-phrase-one-meaning)
    "queued": "to stage for your call",
    "active": "live in store",
    "verified": "checked with the maker",
    "unverified": "still to check",
    "with_findings": "with evidence in hand",
    "products": "products",
    "products_with_findings": "products with evidence in hand",
    "pending": "waiting for your call",
    "lapsed": "lapsed",
}


def progress_label(key: str) -> str:
    return PROGRESS_LABELS.get(key, key.replace("_", " "))


# the line every stale wait earns — lapsed is never a live wait, and the way
# back is always a fresh batch, never a late approval.
LAPSED_LINE = "lapsed — run a fresh batch to re-propose with current numbers"


def progress_detail(feature: str, prog: dict) -> str:
    """the progress line under a front's meter, in plain words with its UNITS
    named. verification counts two different things — CLAIMS (details) and
    PRODUCTS — so its line says which is which, and its evidence figure opens
    to the evidence list (never a dead end). every other front renders its
    counters generically; a lapsed count always carries the re-run path."""
    if feature == "verification":
        parts = [f"{prog.get('total', 0):,} details across "
                 f"{prog.get('products', 0):,} products",
                 f"{prog.get('verified', 0):,} checked with the maker",
                 f"{prog.get('unverified', 0):,} still to check"]
        ev = prog.get("products_with_findings", 0)
        if ev:
            parts.append(f"<a href='/catalog/workflows/verification#evidence'>"
                         f"{ev:,} product{'s' if ev != 1 else ''} with evidence in hand</a>")
        parts.append(f"{prog.get('pending', 0):,} waiting for your call")
        if prog.get("lapsed"):
            parts.append(f"{prog['lapsed']:,} {LAPSED_LINE}")
        return " · ".join(parts)
    if feature == "seo":
        # one wait phrase, no double-count (M1): the per-item waits link to
        # decisions, held-back opens to the refusal list on the front page (M2).
        parts = [f"{prog.get('written', 0):,} written",
                 f"{prog.get('weak', 0):,} missing or weak",
                 f"{prog.get('to_draft', 0):,} ready to draft"]
        waiting = prog.get("waiting", 0)
        if waiting:
            parts.append(f"<a href='/approvals'>{waiting:,} waiting on you, "
                         f"item by item</a>")
        to_stage = prog.get("to_stage", 0)
        if to_stage:
            # the breathing gap: computed, not yet proposed — named so no weak
            # product goes unaccounted between computation and the writer's run.
            parts.append(f"{to_stage:,} write{'s' if to_stage == 1 else ''} "
                         f"item by item when the writer next runs")
        held = prog.get("held_back", 0)
        if held:
            parts.append(f"<a href='/catalog/workflows/seo#held-back'>{held:,} "
                         f"held back</a>")
        if prog.get("lapsed"):
            parts.append(f"{prog['lapsed']:,} {LAPSED_LINE}")
        return " · ".join(parts)
    if feature == "merchandising":
        # coverage is the headline (RULED): the share of products in at least
        # one smart collection — read from the synced memberships, so it is
        # honest only "as of the last sync" and moves as new shelves settle. the
        # raw counter keys carry code words, so this line names them by hand.
        covered = prog.get("covered", 0)
        total = prog.get("total", 0)
        live = prog.get("collections_live", 0)
        of = prog.get("collections_total", 0)
        to_create = prog.get("to_create", 0)
        parts = [f"{covered:,} of {total:,} products in a collection, as of the last sync",
                 f"{live:,} of {of:,} collections live"]
        if to_create:
            parts.append(f"{to_create:,} still to create")
        return " · ".join(parts)
    parts = []
    for k, v in prog.items():
        if k == "rate":
            continue
        if k == "lapsed":
            if v:
                parts.append(f"{v:,} {LAPSED_LINE}")
            continue
        # p204 comma drift: every count on this surface gets the same comma
        # treatment as its neighbors (seo's commaed count above) — an int renders
        # with its thousands separator; anything else renders as itself.
        v_plain = f"{v:,}" if isinstance(v, int) and not isinstance(v, bool) else v
        parts.append(f"{v_plain} {progress_label(k)}")
    return " · ".join(parts)


# plain words for the write-door method a record ran — the words a person
# reads on home's record card, the record view, and anywhere else a ledger
# row surfaces. the method key is CODE (it lives in proposals and the policy
# table, never changes); only the label a person reads is plain.
METHOD_LABELS = {
    "mutate_variant_field": "barcode fixed",
    "mutate_spec_verification": "spec checked with the maker",
    "mutate_product_state": "removed from / returned to the store",
    "mutate_seo": "listing text written",
    "mutate_price": "price changed",
    "mutate_product_field": "product detail changed",
    "create_collection": "collection created",
    # tense-neutral: a mutate_menu proposal PARKS per item, so this label lands
    # on a still-pending card too — "placed" there would be a past-tense lie.
    "mutate_menu": "store menu placement",
    "policy.move_threshold": "approval rule moved",
}


def method_label(key: str) -> str:
    if key in METHOD_LABELS:
        return METHOD_LABELS[key]
    return (key or "").replace("mutate_", "").replace("_", " ").replace(".", " ")


# the same acts before they land — tense-free, so a staged wait never reads
# as finished work (the producer's cold read: "barcode fixed · pending" told
# the owner a thing had happened when it was still his to decide).
METHOD_LABELS_AHEAD = {
    "mutate_variant_field": "a barcode fix",
    "mutate_spec_verification": "a spec check with the maker",
    "mutate_product_state": "a store removal / return",
    "mutate_seo": "new listing text",
    "mutate_price": "a price change",
    "mutate_product_field": "a product detail change",
    "create_collection": "a new collection",
    "mutate_menu": "a store menu change",
    "policy.move_threshold": "an approval rule move",
}


def act_label(key: str, status: str) -> str:
    """the act in plain words, honest about tense: done words only for done
    acts; anything still waiting or running reads as a thing ahead."""
    if status == "executed":
        return method_label(key)
    return METHOD_LABELS_AHEAD.get(key, method_label(key))


# the gate classes in plain words, short form — for a wait's parenthetical.
ACTION_TYPE_LABELS = {
    "reversible": "can be undone",
    "consequential": "needs your call",
    "fit_critical": "safety-critical",
}


def action_type_label(key: str) -> str:
    return ACTION_TYPE_LABELS.get(key, (key or "").replace("_", " "))


# plain words for a ledger record's function (its work area).
FUNCTION_LABELS = {
    "catalog-enrichment": "catalog",
    "policy": "approval rules",
}


def function_label(key: str) -> str:
    return FUNCTION_LABELS.get(key, (key or "").replace("-", " "))


# the fleet manifest's autonomy levels in plain words — what each agent
# function may do on its own. the level key (acts/parks/proposes-only) is
# CODE, frozen in the agent files; only the sentence a person reads is here.
AUTONOMY_PLAIN = {
    "acts": "acts on its own — every act is recorded and can be undone",
    "parks": "prepares the change, then waits for your call in decisions",
    "proposes-only": "suggests only — it never changes anything itself",
}


def autonomy_plain(key: str) -> str:
    return AUTONOMY_PLAIN.get(key, "waits for your call before anything moves")


# the fleet manifest's status values in plain words.
FLEET_STATUS_PLAIN = {"built": "built and working", "building": "being built now"}


def fleet_status_plain(key: str) -> str:
    return FLEET_STATUS_PLAIN.get(key, key)


# plain stage words. the state value stays as data in links/filters; only the
# label a person reads changes.
STATE_LABELS = {
    "active": "active",
    "draft": "draft",
    "flagged": "flagged",
    "delisted": "removed from store",
    "archived": "archived",
}


def state_label(key) -> str:
    return STATE_LABELS.get(key, key or "no stage yet")


# the enrichment gaps a product can carry, in plain words. the gap KEY is a
# short url-stable code (it rides ?gap=… like ?state=… does); only the label a
# person reads is plain. "flagged to remove" is spelled out so it never reads
# as the lifecycle 'flagged' stage — it is the quality gate's remove-from-store
# list. ordered worst-first: the ruling call leads.
GAP_LABELS = {
    "flagged": "flagged to remove",
    "barcodes": "needs barcodes",
    "category": "needs a category",
    "details": "needs product details",
    "listing": "needs listing text",
    "photo": "needs a photo",
}
GAP_ORDER = ["flagged", "barcodes", "category", "details", "listing", "photo"]

# the overview links carry ?feature=<key> (the code identifier that lives in
# FEATURES + URLs). map each onto the matching board gap so an incoming
# ?feature=delist lands on the flagged-to-remove filter, gtin on needs-barcodes,
# classification on needs-a-category.
FEATURE_TO_GAP = {"gtin": "barcodes", "classification": "category", "delist": "flagged",
                  "verification": "details", "seo": "listing"}


def gap_label(key: str) -> str:
    return GAP_LABELS.get(key, key)


# one plain sentence per enrichment front — what it does, for the workflow view.
# keyed by the feature CODE (gtin/classification/delist); the name a person
# reads is feature_label().
FRONT_BLURB = {
    "gtin": "give every product a barcode that scanners and shopping feeds accept.",
    "classification": "put every product in the right category so shoppers find it where they look.",
    "merchandising": "group products into shelves shoppers browse — one collection per category, "
                     "so the catalog reads as a store, not a list.",
    "delist": "pull the products that don't belong — leftover demo data and mis-shelved "
              "items — after you review each one.",
    "verification": "check each safety-bearing product detail against the maker's own "
                    "page, with the quote and the link kept as proof.",
    "seo": "write the search listing — the title and description shoppers see in search — "
           "for products whose listing is missing or just the raw name.",
}


def front_blurb(key: str) -> str:
    return FRONT_BLURB.get(key, "")


# the gate class in plain words — what your approval means for this front. the
# CODE (reversible/consequential/fit_critical) stays in the engine; this is the
# line a person reads about whether it needs their call.
GATE_CLASS_PLAIN = {
    "reversible": "can be undone, so a whole batch lands after one look and your approval.",
    "consequential": "changes what shoppers see, so you rule each one before anything moves.",
    "fit_critical": "safety-critical, so you rule each one against its evidence before anything moves.",
}


def gate_class_plain(key: str) -> str:
    return GATE_CLASS_PLAIN.get(key, "you approve before anything changes your store.")


# where each front's data comes from, in plain words (no fetch jargon).
SOURCE_PLAIN = {
    "gtin": "the barcodes already on file — repaired in place, nothing fetched from outside.",
    "classification": "each product's own type, matched to your locked category list.",
    "merchandising": "your locked category list, turned into one shelf each — a product joins by its "
                     "own type, nothing fetched from outside.",
    "delist": "the quality check's flags — matched signals in the title, type, tags, and brand.",
    "verification": "the maker's own product page — one check per product, quote and link kept.",
    "seo": "each product's own facts — its name, brand, category, and checked details — "
           "nothing invented, nothing fetched from outside.",
}


def source_plain(key: str) -> str:
    if not key:
        return "not recorded"
    if key in SOURCE_PLAIN:
        return SOURCE_PLAIN[key]
    # claim-level sources carry a code prefix — never show the code itself.
    if key.startswith("parsed:"):
        return "read from the supplier's spec sheet — not yet checked against the maker"
    if key.startswith("shopify:"):
        return "from your Shopify store"
    if key.startswith("writeback:"):
        return "confirmed live on your store"
    if key.startswith("http"):
        return "the maker's website"
    # last resort: strip any code shape so no colon or underscore reaches a person
    return key.split(":")[0].replace("_", " ").replace("-", " ") or "your landed facts"


# the quality gate's raw signal codes -> the plain reason a person reads. these
# codes ride in evidence lists (from quality.py) or inside a lifecycle reason
# string; the reader below maps each token and NEVER shows the code itself.
EVIDENCE_PLAIN = {
    "demo_handle": "it's a leftover demo product from the store's starter data",
    "demo_vendor": "it's sold under a demo or sample brand",
    "placeholder_title": "the title reads like a placeholder (test / sample)",
    "zero_price": "every version of it is priced at zero",
    "no_sku": "it has no stock code",
    "decor_keyword": "the title reads like home decor, not outdoor gear",
    "decor_type": "it's shelved under a home-decor product type",
    "decor_tag": "it's tagged or grouped as home decor",
    "home_brand": "it's sold under a home or patio brand",
}

_DECOR_CODES = {"decor_keyword", "decor_type", "decor_tag", "home_brand"}
_NOISE_CODES = {"demo_handle", "demo_vendor", "placeholder_title", "zero_price", "no_sku"}


def read_evidence(evidence: list) -> tuple[str, list[str]]:
    """turn a flag's raw evidence into a plain headline + plain reason lines.
    each entry may be a known signal code, or a free note, or a comma-joined
    string of codes (a lifecycle reason); every token is split, mapped, and the
    code itself is never shown. returns (headline, [reasons])."""
    tokens: list[str] = []
    for ev in evidence or []:
        for tok in str(ev).split(","):
            tok = tok.strip()
            if tok:
                tokens.append(tok)
    reasons, codes = [], set()
    for tok in tokens:
        if tok in EVIDENCE_PLAIN:
            reasons.append(EVIDENCE_PLAIN[tok])
            codes.add(tok)
        else:
            reasons.append(tok)  # already a human note — shown verbatim
    if codes & _DECOR_CODES:
        headline = "looks like home decor, not outdoor gear"
    elif codes & _NOISE_CODES:
        headline = "looks like leftover demo or placeholder data"
    else:
        headline = "flagged for your review"
    n = len(reasons)
    headline += f": matched {n} signal" + ("s" if n != 1 else "")
    return headline, reasons


# a few friendly names for spec-detail fields; anything without one is
# title-cased with underscores replaced (the plain-language rule for the drill).
SPEC_FIELD_LABELS = {
    "ip_water_rating": "water resistance",
    "beam_distance": "beam distance",
    "battery_life": "battery life",
    "burn_time": "burn time",
    "lumens": "brightness",
    "weight": "weight",
    "capacity": "capacity",
    "gtin": "barcode",
    "gtin13": "barcode",
}


def detail_label(field: str) -> str:
    return SPEC_FIELD_LABELS.get(field, field.replace("_", " ").title())


# plain words for the analyst's hunts. the hunt key (the metric's
# "analyst.<hunt>" suffix) is CODE — it lives in findings rows and the HUNTS
# registry, never changes; these are the words a person reads on the findings
# page. a hunt without a label falls back to its key with the underscores
# spelled out, so nothing raw ever reaches the screen.
HUNT_LABELS = {
    "category_sales_shift": "category sales shift",
    "vendor_sales_shift": "vendor sales shift",
    "basket_pairings": "what sells together",
    "aov_drift": "price per order drift",
    "return_rate_drift": "returns drift",
    "catalog_health_vs_sales": "listing health vs sales",
}


def slice_plain(slice_: str) -> str:
    """a finding's slice ('vendor=Acme', 'category=Flashlights', multi-dim
    joined with ·) in plain words. a pair slice carries raw product ids, so it
    renders nothing — the sentence already names both products."""
    if not slice_ or slice_.startswith("pair="):
        return ""
    parts = []
    for tok in slice_.split("·"):
        key, _, val = tok.partition("=")
        parts.append(f"{key.replace('_', ' ')} {val}".strip())
    return " · ".join(p for p in parts if p)


def finding_area(metric: str | None, slice_: str = "") -> str:
    """where a finding came from, in plain words — the watch-list row's name
    or the analyst hunt's label, plus the slice it looked at. the raw metric
    identifier (hyphens, dots, snake_case) never reaches the screen."""
    if not metric:
        return "—"
    if metric.startswith("analyst."):
        key = metric.split(".", 1)[1]
        label = HUNT_LABELS.get(key, key.replace("_", " "))
    else:
        label = metric.replace("-", " ").replace("_", " ")
    sliced = slice_plain(slice_)
    return f"{label} · {sliced}" if sliced else label


def watch_row_plain(label: str) -> str:
    """a self-reported watch-row label ('metric' or 'metric[slice]') in plain
    words — the same reader the findings page uses."""
    metric, _, sl = label.partition("[")
    return finding_area(metric, sl.rstrip("]"))


def drift_mode_plain(mode: str, drift_pct=None) -> str:
    """a stored drift mode in the words a person reads. the stored value
    ('banded' / 'warming up (n of N)') is DATA in the evaluations table and
    never changes; this is the sentence the parts view renders — how this
    number's change is judged, with the row's own warm-up percentage named
    when it has one."""
    if mode == "banded":
        return "judged against its own history's band"
    if mode.startswith("warming up (") and mode.endswith(")"):
        inner = mode[len("warming up ("):-1]  # 'n of N'
        line = f"still learning its normal — {inner} readings"
        if isinstance(drift_pct, (int, float)) and drift_pct:
            line += f"; a plain {drift_pct:g}% line carries it meanwhile"
        return line
    return mode


def _watch_drift_pcts() -> dict:
    """each watch row's warm-up percentage, from the store's watch-list —
    read guarded, so a missing file just means no percentage is named."""
    try:
        from commerceos.watching.engine import load_watch_list
        return {m["name"]: m.get("drift_pct")
                for m in load_watch_list().get("metrics", [])}
    except Exception:
        return {}


# a finding's lifecycle states in plain words — noticed → routed → decided →
# done, or aged out. the state value stays as data; only the word changes.
DISPOSITION_LABELS = {
    "noticed": "noticed",
    "routed": "routed",
    "decided": "decided",
    "done": "done",
    "aged_out": "aged out",
}


def disposition_label(key: str) -> str:
    return DISPOSITION_LABELS.get(key, (key or "").replace("_", " "))


def age_plain(days: float) -> str:
    """a finding's age in the words a person reads — whole days, never a
    decimal with a unit letter ('7 days', not '7.2d')."""
    n = int(days)
    if n < 1:
        return "under a day"
    return f"{n} day{'s' if n != 1 else ''}"


def fact_ref_plain(ref) -> str:
    """a finding's raw fact reference ('money_lines@2026-06 rows=12',
    'order_lines:1') in plain words — the table named plainly, the period or
    row it points at kept. no snake_case identifier reaches the screen."""
    ref = str(ref)
    if "@" in ref:
        table, _, rest = ref.partition("@")
        period, _, nrows = rest.partition(" rows=")
        out = f"{table.replace('_', ' ')} · {period}"
        if nrows:
            out += f" · {nrows} row{'s' if nrows != '1' else ''} read"
        return out
    if ":" in ref:
        table, _, rowid = ref.partition(":")
        return f"{table.replace('_', ' ')} · row {rowid}"
    return ref.replace("_", " ")


def sentence_plain(row: dict) -> str:
    """a finding's sentence with any raw metric label translated at render.
    newly minted sentences are already plain (the engine mints the plain
    label); sentences stored before that carry 'metric[slice]' or the bare
    metric key, and this reader swaps in the same plain words the rest of
    the page uses."""
    s = row["sentence"]
    metric = row.get("metric")
    if metric and not metric.startswith("analyst."):
        raw = f"{metric}[{row.get('slice') or ''}]" if row.get("slice") else metric
        s = s.replace(raw, finding_area(metric, row.get("slice") or ""))
        s = s.replace(metric, finding_area(metric, ""))
    return s


def evidence_count(evidence) -> str:
    """a finding's evidence, counted honestly — how many of the watching's own
    readings and how many landed facts it cites. the raw ids (evaluation
    numbers, fact row refs) stay in the record; the count is what a person
    reads, and a finding with no evidence never exists (the mint law)."""
    ev = evidence if isinstance(evidence, dict) else {}
    n_evals = len(ev.get("evaluations") or [])
    n_facts = len(ev.get("facts") or [])
    bits = []
    if n_evals:
        bits.append(f"{n_evals} reading{'s' if n_evals != 1 else ''}")
    if n_facts:
        bits.append(f"{n_facts} landed fact{'s' if n_facts != 1 else ''}")
    return " · ".join(bits) or "—"


# plain names for the P&L lines. the keys come from the economics engine and
# stay as code; these are the words shown in the money view.
ECON_LINES = {
    "books_sales": "sales",
    "books_purchases": "purchases",
    "gross_spread": "gross spread",
    "gross_margin_bps": "gross margin",
    "take_earned": "commission earned",
    "payable_outstanding": "owed to vendors",
    "unwinds": "refund reversals",
    "payouts": "payouts from shopify",
    "settlement": "order settlement",
    "gateway_fee": "payment fees",
    "platform_bill": "platform bill",
}


def econ_label(name: str) -> str:
    return ECON_LINES.get(name, name.replace("_", " "))


def _db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


async def emit(event: dict) -> None:
    """push an event to every connected client (SSE)."""
    for q in list(_subscribers):
        await q.put(event)


def _guard(request: Request, conn) -> None:
    require_operator(request, conn)


def _prefers_html(request: Request) -> bool:
    """content negotiation for the phone-facing refusal: pick the highest-q
    media type the Accept header names. a browser navigating to a guarded
    page puts text/html first (implicit q=1); an API caller sends no header,
    or an explicit application/json — both fall through to the JSON answer,
    byte-identical to today's, so no existing caller (test or otherwise)
    sees a change."""
    accept = request.headers.get("accept", "")
    if not accept:
        return False
    best_type, best_q = None, -1.0
    for part in accept.split(","):
        part = part.strip()
        if not part:
            continue
        media = part.split(";")[0].strip()
        q = 1.0
        for param in part.split(";")[1:]:
            param = param.strip()
            if param.startswith("q="):
                try:
                    q = float(param[2:])
                except ValueError:
                    q = 1.0
        if q > best_q:
            best_q, best_type = q, media
    return best_type in ("text/html", "application/xhtml+xml")


@app.exception_handler(HTTPException)
async def _guard_refusal(request: Request, exc: HTTPException):
    """the shared require_operator 401, made honest for a human without
    touching the 29 guarded surfaces or any API caller: a browser gets a
    small plain page naming the fix; everyone else gets the exact JSON
    FastAPI's own default HTTPException handler would have returned. the
    whole codebase raises HTTPException from exactly one place (auth.py's
    require_operator) — so this handler only ever answers for that refusal,
    never reinterprets some other status code's meaning."""
    if exc.status_code == 401 and _prefers_html(request):
        return HTMLResponse(
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>not paired · commerceos</title>"
            "<link rel='stylesheet' href='/static/tokens.css'>"
            "<link rel='stylesheet' href='/static/teletext.css'></head>"
            "<body><div class='channel'><div class='teletext-row'>"
            "<p>this phone isn't paired — pair it from the computer at "
            "<a href='/pair'>/pair</a>.</p>"
            "</div></div></body></html>",
            status_code=401)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code,
                        headers=exc.headers)


@app.get("/api/parts")
def api_parts(request: Request, conn=Depends(_db)):
    _guard(request, conn)
    return {"parts": registry.all_parts(conn)}


@app.get("/api/parts/{name}/config")
def api_part_config(name: str, request: Request, conn=Depends(_db)):
    _guard(request, conn)
    return {"part": name, "config": registry.config_for(conn, name)}


@app.get("/api/events")
async def api_events(request: Request, conn=Depends(_db)):
    _guard(request, conn)
    from sse_starlette.sse import EventSourceResponse

    q: asyncio.Queue = asyncio.Queue()
    _subscribers.add(q)

    async def stream():
        try:
            while True:
                event = await q.get()
                yield {"data": json.dumps(event)}
        finally:
            _subscribers.discard(q)

    return EventSourceResponse(stream())


def _asof() -> str:
    """the broadcast's as-of stamp — lowercase chrome, e.g. 'jul 12'."""
    return date.today().strftime("%b %d").lower().replace(" 0", " ")


def _page(title: str, body: str, marquee: str | None = None,
          signoff_line: str | None = None) -> str:
    """the teletext broadcast frame every page wears: the masthead marquee,
    the nav teletext-bar, the dithered ground (tokens set it on <body>), and
    the sign-off. lowercase chrome throughout; UPPERCASE only for the one
    slap a view may carry. `marquee` overrides the default masthead when a
    page has a real headline number to announce."""
    mast = marquee if marquee is not None else tt.masthead(
        title, title, "run your store from here", as_of=_asof())
    nav = tt.nav_bar(title)
    sign = tt.signoff(title, signoff_line or "the counts open to the work behind them")
    return f"""<!doctype html><html lang="en"><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{title} · commerceos</title>
<link rel='stylesheet' href='/static/tokens.css'>
<link rel='stylesheet' href='/static/teletext.css'>
</head><body>
<div class='channel'>{mast}{nav}{body}{sign}</div>
</body></html>"""


_STATIC = Path(__file__).resolve().parent / "static"
_ALLOWED_STATIC = {"tokens.css": "text/css", "teletext.css": "text/css",
                   "fusion.css": "text/css"}


@app.get("/static/{name}")
def _static(name: str):
    """serve a vetted file from the static dir. only names on the allow-list
    are reachable — no path component, no traversal, can escape it."""
    from fastapi.responses import Response
    media = _ALLOWED_STATIC.get(name)
    if media is None:
        return Response(content="not found", status_code=404)
    return Response(content=(_STATIC / name).read_text(), media_type=media)


# p500 twin cassettes (RULED): the record's own voice always names this part
# "the watching" — every comment, the /findings block ("what the watching
# noticed"), the agent manifests — but its cassette title on /parts rendered
# the bare registry key, "watching", a self-contradiction between the two
# places a person reads the same part's name. every other part's raw key
# already reads as honest, un-ambiguous identifier text (or plain English)
# with no such clash, so only this one entry gets a display form here; the
# stored registry key ("watching", used for lookups and /api/parts/<name>
# /config) is untouched — this is a render-time label, not a rename.
_PART_TITLE = {"watching": "the watching"}


def part_title(part: str) -> str:
    return _PART_TITLE.get(part, part)


@app.get("/parts", response_class=HTMLResponse)
def parts_view(request: Request, conn=Depends(_db)):
    _guard(request, conn)
    _refresh_reports(conn)
    rows = registry.all_parts(conn)
    if not rows:
        inner = ("<div class='teletext-row'><p class='muted'>nothing has "
                 "reported in yet — each piece of the system shows up here "
                 "once it runs.</p></div>")
    else:
        drift_pcts = _watch_drift_pcts()
        cards = []
        for p in rows:
            lr = p["last_run"] or {}
            # a part that self-reports per-row drift modes (the watching) gets
            # them rendered here, each row in plain words: the watched number ·
            # how its change is judged ("judged against its own history's
            # band", or "still learning its normal — n of N readings"). the
            # spec's render law — each row states its drift mode, not just the
            # summary count. and the ABSENCE speaks: a watching that has
            # evaluated but whose evaluations predate the mode column says so
            # plainly rather than silently dropping the table.
            modes = lr.get("drift_modes") or {}
            drift = ""
            if modes:
                mrows = "".join(
                    f"<tr><td>{watch_row_plain(lbl)}</td>"
                    f"<td>{drift_mode_plain(modes[lbl], drift_pcts.get(lbl.partition('[')[0]))}</td></tr>"
                    for lbl in sorted(modes))
                drift = (f"<table class='drift-rows'>"
                         f"<tr><th>each watched number</th><th>how change is judged</th></tr>"
                         f"{mrows}</table>")
            elif "drift_modes" in lr and lr.get("last_evaluation"):
                drift = ("<p class='muted'>drift modes not yet known — "
                         "no evaluation since modes were added</p>")
            # a stale wait is named: a next-run moment already past renders
            # "overdue", never a date pretending to be a future promise.
            next_line = p["next_run"] or "on demand"
            if p["next_run"]:
                try:
                    from datetime import datetime as _dt, timezone as _tz
                    due = _dt.fromisoformat(p["next_run"].replace("Z", "+00:00"))
                    if due.tzinfo is None:
                        due = due.replace(tzinfo=_tz.utc)
                    if due < _dt.now(_tz.utc):
                        next_line = "overdue"
                except ValueError:
                    pass
            # parts are ownable — the ONE surface tokens.css permits the
            # supercolor spine. each cassette carries the part's own
            # self-report: what it is, its state, its last run.
            cards.append(
                f"<div class='cassette'>"
                f"<h3>{part_title(p['part'])} <span class='state'>· {p['state']}</span></h3>"
                f"<p class='self'>{p['is_']}</p>"
                f"<p class='meta'>last run: {lr.get('summary', '—')} · "
                f"next: {next_line} · reported {p['reported_at']}</p>"
                f"{drift}"
                f"</div>")
        inner = f"<div class='parts-rack'>{chr(10).join(cards)}</div>"
    body = tt.block("p500 · parts of the system", inner,
                    "what it is · state · last run")
    # p501 — the phones paired to this computer. labels are user ink: escaped
    # before markup (the record-born-ink law). a row is honest about its state:
    # a scanned phone reads "paired <when it scanned>"; a code that was shown
    # but never scanned reads "not scanned yet" — an abandoned code never poses
    # as a paired phone on the roster. both carry the same unpair door (clearing
    # an abandoned code is exactly why unpairing an unclaimed row must work).
    # revoke is a per-row _guarded POST a paired phone may fire on itself.
    devices = list_devices(conn)
    if devices:
        rows_html = []
        for d in devices:
            if d["claimed_at"]:
                when = f"paired {when_plain(d['claimed_at'])}"
            else:
                when = f"code shown {when_plain(d['paired_at'])} — not scanned yet"
            rows_html.append(
                f"<div class='teletext-row'>"
                f"<span class='name'>{html_escape(d['label'] or 'a phone')}</span>"
                f"<span class='stat'>{when}</span>"
                f"<form method='post' action='/pair/revoke' class='inline'>"
                f"<input type='hidden' name='token_hash' value='{html_escape(d['token_hash'])}'>"
                f"<button type='submit'>unpair</button></form>"
                f"</div>")
        drows = "".join(rows_html)
    else:
        drows = ("<div class='teletext-row'><p class='muted'>no phone is paired "
                 "yet — open <a href='/pair'>pair a phone</a> on this screen to "
                 "show a code the phone can scan.</p></div>")
    body += tt.block("p501 · phones paired to this computer", drows,
                     "phone · state · unpair")
    body += ("<p class='muted'><a href='/fleet'>who works here &rarr;</a> — "
             "the agents on the roster, each read from its own file.</p>")
    return _page("system", body,
                 signoff_line="every piece shows itself here — even a quiet one, as its last known state")


# --- WEB1: phone pairing (QR on localhost, cookie channel, revoke) ----------
# the auth core (paired_devices, mint, the localhost-or-token guard) lived in
# auth.py with no surface. these endpoints are that surface: mint on localhost
# only, hand the token to the phone as a QR, land it as a cookie the phone's
# browser can present, and revoke from /parts. identity is untouched — pairing
# makes a device LABEL, never a ledger identity (the 7c rides, app.py:1234).

_PAIR_QUIET_ZONE = 4   # modules of light border — a camera needs the margin
_PAIR_MODULE_PX = 6    # each module's pixel size in the inline SVG
_PAIR_SIGNOFF = "a code is shown once — paired phones live on the parts page"


def _qr_svg(text: str) -> str:
    """render a QR as one inline SVG: dark modules as a single path on a solid
    LIGHT block with a quiet zone, so the teletext dark ground never eats the
    code (a phone camera fails without the contrast). structurally the same
    matrix test_qr_matrix_invariants pins."""
    from commerceos.web.qrcodegen import QrCode

    qr = QrCode.encode_text(text, QrCode.Ecc.MEDIUM)
    size = qr.get_size()
    scale, border = _PAIR_MODULE_PX, _PAIR_QUIET_ZONE
    dim = (size + border * 2) * scale
    segs = []
    for y in range(size):
        for x in range(size):
            if qr.get_module(x, y):
                px, py = (x + border) * scale, (y + border) * scale
                segs.append(f"M{px},{py}h{scale}v{scale}h-{scale}z")
    path = "".join(segs)
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{dim}' height='{dim}' "
        f"viewBox='0 0 {dim} {dim}' role='img' aria-label='a code the phone can scan' "
        f"style='background:#fff;border-radius:6px'>"
        f"<rect width='{dim}' height='{dim}' fill='#fff'/>"
        f"<path d='{path}' fill='#000'/></svg>"
    )


def _reach_prefill(request: Request) -> str:
    """the reach address the QR should point at — the owner's tailscale/ntfy
    config if set (the ntfy precedent: read the owner's reach, never write it),
    else the address this very request came in on. a missing/broken config must
    never break /pair, so the read is fully guarded."""
    try:
        from commerceos.rhythm.runner import load_config
        base = ((load_config() or {}).get("ntfy") or {}).get("link_base")
        if base and "localhost" not in base and "127.0.0.1" not in base:
            return base.rstrip("/")
    except Exception:
        pass
    return str(request.base_url).rstrip("/")


def _pair_body(request: Request, minted: dict | None = None) -> str:
    reach = _reach_prefill(request)
    if minted is None:
        form = (
            "<div class='teletext-row'><p>pairing a phone shows a code once, "
            "below. scan it from the phone over your private network; the phone "
            "stays paired until you unpair it from the parts page. this only "
            "works here, on this computer.</p>"
            "</div>"
            "<form method='post' action='/pair' class='pair-form'>"
            "<label>what to call this phone "
            f"<input name='label' value='your phone' maxlength='60'></label>"
            "<label>where the phone reaches this from "
            f"<input name='reach' value='{html_escape(reach)}' size='40'></label>"
            "<button type='submit'>show the code</button>"
            "</form>"
        )
        return tt.block("p900 · pair a phone", form, "shows once · only from this computer")
    # minted: show the code once
    claim = f"{minted['reach']}/pair/claim?t={minted['token']}"
    shown = (
        f"<div class='teletext-row'><p>this code is for "
        f"<b>{html_escape(minted['label'])}</b>. scan it once from that phone. "
        f"it is shown only now — if you leave this page, make a new one.</p></div>"
        f"<div class='teletext-row' style='justify-content:center'>{_qr_svg(claim)}</div>"
        f"<div class='teletext-row'><p class='muted'>can't scan? open this on the "
        f"phone: <code>{html_escape(claim)}</code></p></div>"
        f"<div class='teletext-row'><p class='muted'>paired phones and unpair live "
        f"on <a href='/parts'>the parts page</a>.</p></div>"
    )
    return tt.block("p900 · a phone's code, shown once", shown, "scan once · then it's gone")


@app.get("/pair", response_class=HTMLResponse)
def pair_page(request: Request, conn=Depends(_db)):
    """the pairing surface — localhost ONLY (403 otherwise), stricter than the
    guard: minting a token from off-localhost would defeat the whole binding."""
    if not is_localhost(request):
        return HTMLResponse(
            "<p>pairing a phone only works from this computer. open it there.</p>",
            status_code=403)
    return HTMLResponse(_page("pair", _pair_body(request), signoff_line=_PAIR_SIGNOFF))


@app.post("/pair", response_class=HTMLResponse)
async def pair_mint(request: Request, conn=Depends(_db)):
    """mint a token on localhost and show its code once. the urlencoded body is
    parsed by hand (parse_qs) like api_resolve — python-multipart is not a
    dependency and FastAPI's Form() needs it."""
    if not is_localhost(request):
        return HTMLResponse(
            "<p>pairing a phone only works from this computer. open it there.</p>",
            status_code=403)
    form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
    label = (form.get("label") or "your phone").strip()[:60] or "your phone"
    reach = (form.get("reach") or _reach_prefill(request)).strip().rstrip("/")
    token = pair_device(conn, label)
    minted = {"label": label, "reach": reach, "token": token}
    return HTMLResponse(_page("pair", _pair_body(request, minted), signoff_line=_PAIR_SIGNOFF))


@app.get("/pair/claim")
def pair_claim(request: Request, conn=Depends(_db)):
    """the one unguarded door an unpaired phone may open: validate the minted
    token AND stamp the claim (so the roster stops calling it an unscanned
    code), land it as the device cookie, and redirect to /. a bad token gets
    the plain refusal — no stack, no code identifier. the 303 also drops the
    token from the visible url (it rode in the QR's query, device-local)."""
    token = request.query_params.get("t") or ""
    if not token or not claim_device(conn, token):
        return HTMLResponse(
            "<p>this pairing code is not valid. pair the phone again from the "
            "computer to get a fresh one.</p>", status_code=401)
    resp = RedirectResponse(url="/", status_code=303)
    # no Secure flag: tailscale reach is plain http and a Secure cookie would
    # never ride. HttpOnly + SameSite=Lax; long-lived (365d), revoke is control.
    resp.set_cookie(
        COOKIE_NAME, token, max_age=365 * 24 * 3600,
        httponly=True, samesite="lax", path="/")
    return resp


@app.post("/pair/revoke")
async def pair_revoke(request: Request, conn=Depends(_db)):
    """unpair a device by its stored hash. _guarded — a paired phone may revoke
    itself; localhost may revoke any. lands back on /parts (a browser click
    never ends on a raw dump — the SP1 lesson)."""
    _guard(request, conn)
    form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
    token_hash = (form.get("token_hash") or "").strip()
    if token_hash:
        revoke_device(conn, token_hash)
    return RedirectResponse(url="/parts", status_code=303)


# agent -> the policy-table function its writes flow through. named debt,
# like the agent-jobs map below: the manifest names work kinds, the ledger
# names policy functions, and this seam lives here until a real second
# store's roster forces it into config. None = the agent writes through no
# gate function (findings only) — there is nothing to widen.
AGENT_POLICY_FUNCTION = {
    "catalog-proposer": "catalog-enrichment",
    "spec-verifier": "catalog-enrichment",
    "content": "content-geo",
    "analyst": None,
}

# the widening ladder — each rung is a recorded policy-table move (FW1,
# RULED 2026-07-18). fit_critical is never on it: always human-gated.
GRANT_LADDER = ((), ("reversible",), ("reversible", "consequential"))

GRANT_PLAIN = {
    (): "nothing runs free — every act waits for your call",
    ("reversible",): "acts that can be undone run free, recorded; "
                     "the rest waits for your call",
    ("reversible", "consequential"):
        "acts that can be undone AND consequential acts run free, recorded; "
        "safety-critical work always waits for your call",
}

# the policy function in plain words — what the grant actually covers.
# non-possessive on purpose: the same string renders on cards that share
# the grant without writing that work themselves (the producer's re-walk).
FUNCTION_PLAIN = {
    "catalog-enrichment": "catalog repairs",
    "content-geo": "listing text",
}


def _grant_rung(auto: list | None) -> int | None:
    """where a function's auto_approve sits on the ladder — None when the
    table carries a shape the ladder doesn't know (never guessed at)."""
    current = tuple(sorted(auto or []))
    for i, rung in enumerate(GRANT_LADDER):
        if tuple(sorted(rung)) == current:
            return i
    return None


@app.get("/fleet", response_class=HTMLResponse)
def fleet_roster(request: Request, conn=Depends(_db)):
    """O4 — who works here. one block per agent, read straight from its
    file in .claude/agents/ (the frontmatter ALONE is the manifest — RULED
    2026-07-18; no duplicate config row anywhere): what I am (the scope
    sentence) · what it may write · what each function does on its own ·
    status · its track record, computed live from the ledger, never
    stored. rides the system corner of the nav — the roster is the O4
    self-report's sibling: the parts are what runs, the fleet is who
    works."""
    _guard(request, conn)
    ledger.ensure_schema(conn)
    try:
        agents = fleet_manifest.roster()
    except fleet_manifest.ManifestError as e:
        # a broken file is reported, never silently skipped — the roster
        # refuses to render a half-truth.
        body = (f"<p class='muted'>the roster can't be read — one agent "
                f"file is broken: {e}</p>")
        return _page("system", body,
                     signoff_line="an agent that does not render does not run")
    # the standing runs: which rhythm job is each agent's, read guarded from
    # the store's rhythm config + the rhythm's own state table. a disabled or
    # absent job renders "not armed" — arming is the owner's keystroke.
    agent_jobs = {"catalog-proposer": "propose", "analyst": "analyst"}
    jobs_cfg, jobs_state = {}, {}
    try:
        from commerceos.rhythm import runner as rhythm_runner
        jobs_cfg = rhythm_runner.job_configs(rhythm_runner.load_config())
        jobs_state = rhythm_runner.state_rows(conn)
    except Exception:
        pass

    def _plain_when(ts: str) -> str:
        try:
            from datetime import datetime as _dt
            return (_dt.fromisoformat(ts.replace("Z", "+00:00"))
                    .strftime("%b %d").lower().replace(" 0", " "))
        except (ValueError, AttributeError):
            return ts or "—"

    blocks = []
    for i, m in enumerate(agents):
        rows = (tt.state_row("what I am", m["scope"])
                + tt.state_row("what it may write", m["writer_class"]))
        for fn in m["functions"]:
            rows += tt.state_row(fn["name"].replace("-", " "),
                                 autonomy_plain(fn["autonomy"]))
        # last run and its outcome — the ledger's latest executed record for
        # this agent, never a stored self-grade.
        last = conn.execute(
            "SELECT ts, status FROM ledger WHERE agent = ?"
            " AND status IN ('executed', 'failed') ORDER BY ts DESC LIMIT 1",
            (m["name"],)).fetchone()
        if last:
            verdict = "ran and landed" if last["status"] == "executed" else "ran and failed"
            rows += tt.state_row("last run", f"{_plain_when(last['ts'])} · {verdict}")
        else:
            rows += tt.state_row("last run", "no run on the record yet")
        # next armed run — the rhythm registry's next-due for this agent's
        # job; "not armed" when the job is disabled or it has none.
        job = agent_jobs.get(m["name"])
        armed_line = "not armed"
        if job and jobs_cfg.get(job, {}).get("enabled"):
            try:
                from commerceos.rhythm import runner as rhythm_runner
                due = rhythm_runner.next_due(
                    (jobs_state.get(job) or {}).get("last_run"),
                    rhythm_runner.parse_cadence(jobs_cfg[job]["cadence"]))
                armed_line = _plain_when(due) if due else "next tick"
            except Exception:
                armed_line = "armed — next run unknown"
        rows += tt.state_row("next armed run", armed_line)
        # the track record: proposals · approved · carried out · REVERSED
        # (undone after execution — the number autonomy widening rests on).
        # every figure opens to the record filtered to this agent; a live
        # wait opens to decisions; a lapsed one names its way back.
        tr = fleet_manifest.track_record(conn, m["name"])
        rlink = f"/record?agent={m['name']}"
        bits = [
            f"<a href='{rlink}'>{tr['proposals']:,}</a> "
            f"proposal{'s' if tr['proposals'] != 1 else ''} made",
            f"<a href='{rlink}'>{tr['approved']:,}</a> approved",
            f"<a href='{rlink}'>{tr['executed']:,}</a> carried out",
            f"<a href='{rlink}'>{tr['reversed']:,}</a> reversed",
        ]
        if tr["pending"]:
            bits.append(f"<a href='/approvals'>{tr['pending']:,} waiting on "
                        f"your call in decisions</a>")
        if tr["lapsed"]:
            bits.append(f"{tr['lapsed']:,} {LAPSED_LINE}")
        rows += tt.state_row("track record", " · ".join(bits), total=True)
        # the autonomy grant (FW1): what the gate lets this agent's function
        # run free, read live from the policy table — and the two controls
        # that move it. a move is a recorded policy-table act, never silent:
        # it rides gate.move_threshold onto the same ledger as everything.
        fn_name = AGENT_POLICY_FUNCTION.get(m["name"])
        sharers = [a for a, f in AGENT_POLICY_FUNCTION.items()
                   if f and f == fn_name and a != m["name"]]
        owns_control = fn_name is not None and m["name"] == next(
            a for a, f in AGENT_POLICY_FUNCTION.items() if f == fn_name)
        if fn_name is None:
            rows += tt.state_row(
                "autonomy grant",
                "it never writes to the store, so there is nothing to widen")
        else:
            try:
                table_fns = policy.load_table().get("functions", {})
                auto = (table_fns.get(fn_name) or {}).get("auto_approve")
                rung = _grant_rung(auto) if fn_name in table_fns else None
            except Exception:
                table_fns, auto, rung = {}, None, None
            fn_plain = FUNCTION_PLAIN.get(fn_name, fn_name.replace("-", " "))
            if fn_name not in table_fns:
                rows += tt.state_row(
                    "autonomy grant",
                    f"the store's rulebook has no row for {fn_plain} — "
                    f"nothing runs free, and there is nothing to move")
            elif rung is None:
                rows += tt.state_row(
                    "autonomy grant",
                    f"the store's rulebook carries a hand-tuned grant here, off "
                    f"the widening ladder — it moves only by hand, in the "
                    f"store's policy-table.json")
            elif not owns_control:
                # the grant is shared: the control and its evidence live on ONE
                # card, and this card says so instead of offering a second
                # lever that would move another agent's room unannounced. no
                # possessive — this agent does not write that work itself.
                other = next(a for a, f in AGENT_POLICY_FUNCTION.items() if f == fn_name)
                rows += tt.state_row(
                    "autonomy grant",
                    f"this card rides the {fn_plain} grant, shared with {other} "
                    f"— {other}'s card holds the control and the evidence for "
                    f"moving it. {GRANT_PLAIN[GRANT_LADDER[rung]]}. this agent's "
                    f"own work keeps the classes listed above; the stricter "
                    f"rule always wins")
            else:
                grant_line = GRANT_PLAIN[GRANT_LADDER[rung]]
                shared_note = (
                    f" — shared with {', '.join(sharers)}: a move changes "
                    f"their room too" if sharers else "")
                controls = ""
                if rung + 1 < len(GRANT_LADDER):
                    dest = GRANT_PLAIN[GRANT_LADDER[rung + 1]]
                    controls += (
                        f"<p class='muted'>widen &rarr; {dest}</p>"
                        f"<form method='post' action='/fleet/autonomy'"
                        f" class='run-form'>"
                        f"<input type='hidden' name='agent' value='{m['name']}'>"
                        f"<input type='hidden' name='direction' value='widen'>"
                        f"<input name='why' size='32' required"
                        f" placeholder='why this agent earned more room'>"
                        f"<label><input type='checkbox' name='confirm'"
                        f" value='true' required> confirm</label>"
                        f"<button class='run'>widen one rung</button></form>")
                else:
                    controls += ("<p class='muted'>at the widest lawful grant — "
                                 "safety-critical work never runs free.</p>")
                if rung > 0:
                    back = GRANT_PLAIN[GRANT_LADDER[rung - 1]]
                    controls += (
                        f"<p class='muted'>narrow &rarr; {back}</p>"
                        f"<form method='post' action='/fleet/autonomy'"
                        f" class='run-form'>"
                        f"<input type='hidden' name='agent' value='{m['name']}'>"
                        f"<input type='hidden' name='direction' value='narrow'>"
                        f"<input name='why' size='32' required"
                        f" placeholder='why the room is being taken back'>"
                        f"<button class='run'>narrow one rung</button></form>")
                rows += tt.state_row("autonomy grant",
                                     f"the {fn_plain} it writes: {grant_line}{shared_note}")
                rows += f"<div class='teletext-row'>{controls}</div>"
        blocks.append(tt.block(f"p51{i} · {m['name']}", rows,
                               fleet_status_plain(m["status"])))
    widening = ("<p class='muted'>a widening is a recorded rule change — the "
                "old room, the new room, by whom, why, on the record like "
                "every other act; narrowing takes the same road back. a work "
                "kind runs free only when its class sits inside the grant: "
                "the grant row is the dial, the rows above are each kind's "
                "class, and the stricter one always wins.</p>")
    # the rest of the roster is still on paper: the backlog carries the
    # planned agents, and each shows up here only when its file lands —
    # the files alone are the roster, so nothing renders from a promise.
    # the dropped one stays visible (ignored-visible law), in one line.
    footer = ("<p class='muted'>the backlog carries 8 more planned agents — "
              "each joins this page when its file lands. the ads agent was "
              "dropped this run (2026-07-18) — no ad-platform access token and "
              "no connector; it waits on the owner's calendar with that work.</p>")
    body = ("<p><a href='/parts'>&larr; parts of the system</a></p>"
            + "".join(blocks) + widening + footer)
    marquee = tt.masthead("fleet", f"{len(agents)}",
                          "agents on the roster · each read from its own file",
                          as_of=_asof())
    return _page("system", body, marquee=marquee,
                 signoff_line="what I am · what it may write · what it did — "
                              "read from the files, counted from the record")


@app.post("/fleet/autonomy")
async def fleet_autonomy(request: Request, conn=Depends(_db)):
    """FW1 — move an agent's function one rung on the widening ladder, in
    either direction. the move is a recorded policy-table act through
    gate.move_threshold: old grant, new grant, by whom, why — on the same
    ledger as every other write. never silent, never more than one rung,
    fit-critical never grantable. widening takes the explicit confirm
    (approvals' second-gesture law); narrowing needs only its why."""
    _guard(request, conn)
    ledger.ensure_schema(conn)
    try:  # urlencoded only, parsed by hand — python-multipart is not a dependency
        form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
    except Exception:
        form = {}
    agent = form.get("agent") or ""
    direction = form.get("direction")
    why = (form.get("why") or "").strip()
    if agent not in AGENT_POLICY_FUNCTION:
        return JSONResponse({"error": f"unknown agent '{agent}' — the roster names them"},
                            status_code=400)
    fn_name = AGENT_POLICY_FUNCTION[agent]
    if fn_name is None:
        return JSONResponse({"error": f"{agent} is findings-only — it never writes "
                                      f"to the store, there is nothing to widen"},
                            status_code=400)
    owner_agent = next(a for a, f in AGENT_POLICY_FUNCTION.items() if f == fn_name)
    if agent != owner_agent:
        # the surface renders the control on one card only; the endpoint
        # agrees with the surface (the producer's re-walk).
        return JSONResponse({"error": f"this grant is shared — the control and its "
                                      f"evidence live on {owner_agent}'s card; "
                                      f"move it from there"}, status_code=409)
    if direction not in ("widen", "narrow"):
        return JSONResponse({"error": "direction must be widen|narrow"}, status_code=400)
    if not why:
        return JSONResponse({"error": "never silent — the move carries its why"},
                            status_code=400)
    if direction == "widen" and form.get("confirm") not in ("true", "on", "1"):
        return JSONResponse({"error": "confirm required — widening takes a second "
                                      "explicit gesture"}, status_code=400)
    table_fns = policy.load_table().get("functions", {})
    if fn_name not in table_fns:
        return JSONResponse({"error": f"the store's policy table has no row for "
                                      f"{fn_name} — nothing to move"}, status_code=409)
    rung = _grant_rung(table_fns[fn_name].get("auto_approve"))
    if rung is None:
        return JSONResponse({"error": "the store's rulebook carries a hand-tuned grant "
                                      "here, off the widening ladder — it moves only by "
                                      "hand, in the store's policy-table.json"},
                            status_code=409)
    step = 1 if direction == "widen" else -1
    if not 0 <= rung + step < len(GRANT_LADDER):
        edge = ("at the widest lawful grant — safety-critical work never runs free"
                if step > 0 else "already at the narrowest — nothing runs free")
        return JSONResponse({"error": edge}, status_code=409)
    by = form.get("by") or identity_label(request, conn)
    try:
        rec = gate.move_threshold(conn, fn_name, "auto_approve",
                                  list(GRANT_LADDER[rung + step]), by=by, why=why)
    except (ValueError, RuntimeError) as e:
        return JSONResponse({"error": str(e)}, status_code=409)
    await emit({"kind": "policy.threshold_moved", "record_id": rec["id"]})
    return RedirectResponse(url="/fleet", status_code=303)


def _table_exists(conn, name: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


@app.get("/", response_class=HTMLResponse)
def brief(request: Request, conn=Depends(_db)):
    """O1 — minutes to the picture. four reads; every line links onward;
    a part that hasn't landed renders as a named gap, never invisibly."""
    _guard(request, conn)
    _refresh_reports(conn)
    sections = []

    # what waits on me — LIVE waits only. a pending row past its expiry is
    # not a wait: it renders lapsed below, never actionable (the law: stale
    # approvals expire rather than execute late).
    ledger.ensure_schema(conn)
    pending = ledger.pending_queue(conn)
    # a held batch (WF-approve) waits as ONE glance, not as its hundred
    # rows — fold its members into one line so the card stays readable
    # and the count stays honest (N waits, M of them inside batches).
    catalog_runs.ensure_schema(conn)
    staged_runs = [r for r in catalog_runs.list_runs(conn, status="staged")
                   if r["status"] == "staged"]
    in_batch = {it["record_id"] for r in staged_runs for it in r["items"]}
    singles = [r for r in pending if r["id"] not in in_batch]
    if pending:
        items = "".join(
            f"<li><a href='/catalog/runs/{r['id']}'>a batch of {r['live']:,} "
            f"{feature_label(r['feature'])} fixes — one glance approves the lot"
            f"</a></li>"
            for r in staged_runs)
        items += "".join(
            f"<li><a href='/approvals'>{intent_plain(r['intent'], 70)}</a> "
            f"<span class='muted'>({action_type_label(r['action_type'])}, "
            f"expires {(r['expires_at'] or 'never')[:16]})</span></li>"
            for r in singles[:8])
        # the heading counts what the LIST shows — a folded batch is named as
        # one, so the number over the list never disagrees with the lines
        if staged_runs and singles:
            head = (f"waits on you ({len(staged_runs)} batch"
                    f"{'es' if len(staged_runs) != 1 else ''} + "
                    f"{len(singles)} single item{'s' if len(singles) != 1 else ''})")
        elif staged_runs:
            n_changes = sum(r["live"] for r in staged_runs)
            head = (f"waits on you (a batch of {n_changes:,})" if len(staged_runs) == 1
                    else f"waits on you ({len(staged_runs)} batches, {n_changes:,} changes)")
        else:
            head = f"waits on you ({len(pending)})"
        sections.append(f"<div class='card'><strong>{head}</strong><ul>{items}</ul></div>")
    else:
        # honest even when empty: staged waits may be zero while removal
        # candidates idle un-staged in operations — home never says
        # "nothing" over work that exists one door away (UI-truth re-walk).
        idle = ""
        try:
            n_delist = len(catalog_workflows.FEATURES["delist"].queue(conn))
            if n_delist:
                idle = (f" <span class='muted'>though <a href='/catalog#p206'>"
                        f"{n_delist} removal candidates</a> wait to be staged"
                        f" in operations.</span>")
        except Exception:
            pass
        sections.append(f"<div class='card'><strong>waits on you</strong>"
                        f"<div class='muted'>nothing staged.{idle}</div></div>")
    lapsed = ledger.lapsed_queue(conn)
    if lapsed:
        sections.append(
            f"<div class='card'><strong>lapsed</strong><div class='muted'>"
            f"{len(lapsed)} request{'s' if len(lapsed) != 1 else ''} waited past "
            f"the approval window and expired — nothing runs late. still wanted "
            f"means a fresh batch, re-proposed with current numbers. "
            f"<a href='/record?status=lapsed'>the record keeps them</a>.</div></div>")

    # what happened — the method in plain words, never the raw identifier.
    recent = ledger.query(conn, limit=10)
    if recent:
        # honest tense + plain status + plain time, and every line is a door
        # to the record (the producer's cold read on all three)
        rows = "".join(
            f"<li><a href='/record'>{act_label(r['proposal']['method'], r['status'])}"
            f" — {intent_plain(r['intent'], 50)}</a> "
            f"<span class='muted'>· {RECORD_STATUS_PLAIN.get(r['status'], r['status'])}"
            f" · {when_plain(r['ts'])}</span></li>" for r in recent)
        sections.append(f"<div class='card'><strong>what happened</strong> <a class='muted' href='/record'>the record</a><ul>{rows}</ul></div>")

    # what the watching flagged — both directions
    if _table_exists(conn, "findings"):
        frows = conn.execute(
            "SELECT direction, count(*) c FROM findings"
            " WHERE disposition IN ('noticed','routed') GROUP BY direction").fetchall()
        mix = " · ".join(f"{r['direction']}: {r['c']}" for r in frows) or "nothing open"
        sections.append(f"<div class='card'><strong>what we're watching</strong> <a class='muted' href='/findings'>findings</a><div>{mix}</div></div>")
    else:
        sections.append("<div class='card'><strong>what we're watching</strong><div class='muted'>this part isn't set up yet.</div></div>")

    # the money line — with its age said out loud: an old month rendered
    # bare reads as current (UI-truth: the stale money line).
    if _table_exists(conn, "money_lines"):
        r = conn.execute(
            "SELECT strftime('%Y-%m', date) ym, sum(amount_minor) s,"
            " max(CASE WHEN source LIKE 'fta:%' OR source LIKE 'zoho:%'"
            "     THEN 1 ELSE 0 END) old"
            " FROM money_lines WHERE account='sales'"
            " GROUP BY ym ORDER BY ym DESC LIMIT 2").fetchall()
        if len(r) >= 1:
            from datetime import datetime as _dt, timezone as _tz
            cur = f"{r[0]['s']/100:,.0f} AED ({r[0]['ym']})"
            prev = f" · prior {r[1]['s']/100:,.0f} ({r[1]['ym']})" if len(r) > 1 else ""
            this_month = _dt.now(_tz.utc).strftime("%Y-%m")
            if r[0]["old"]:
                age = (" <span class='muted'>— the old company's books, for"
                       " reference; your new store has no sales facts yet</span>")
            elif r[0]["ym"] < this_month:
                age = (f" <span class='muted'>— as of {r[0]['ym']}, no newer"
                       f" sales facts landed</span>")
            else:
                age = ""
            sections.append(f"<div class='card'><strong>the money line</strong> <a class='muted' href='/economics'>money</a><div>sales {cur}{prev}{age}</div></div>")
    else:
        sections.append("<div class='card'><strong>the money line</strong><div class='muted'>no money data yet.</div></div>")

    return _page("home", "\n".join(sections))


def _refresh_reports(conn) -> None:
    """each part fills its own row through the shared helper."""
    try:
        spine_report(conn)
        gate_report(conn)
        from commerceos.watching.status import report_status as watching_report
        from commerceos.catalog.status import report_status as catalog_report
        from commerceos.economics.status import report_status as econ_report
        from commerceos.catalog.workflows import report_status as workflows_report
        from commerceos.catalog.lifecycle import report_status as lifecycle_report
        watching_report(conn)
        catalog_report(conn)
        econ_report(conn)
        workflows_report(conn)
        lifecycle_report(conn)
        registry.report(conn, "web-surface",
                        "the brain's face — every part shows itself here or does not ship (O4)",
                        state="running", functions=["surfaces", "approvals", "registry"])
    except Exception:
        pass  # reporting must never take a surface down


@app.get("/api/approvals")
def api_approvals(request: Request, conn=Depends(_db)):
    _guard(request, conn)
    ledger.ensure_schema(conn)
    return {"pending": ledger.pending_queue(conn)}


@app.post("/api/approvals/{record_id}")
async def api_resolve(record_id: str, request: Request, conn=Depends(_db)):
    """the system's only approve verb. consequential resolves require the
    explicit confirm field — a pocket-tap cannot move money.

    two callers, two answers (the producer's SP1 re-walk): a browser form
    (urlencoded — parsed by hand, python-multipart is not a dependency)
    lands back on decisions with the outcome in plain words; an API caller
    (JSON body) gets JSON. the approve click never ends on a raw dump."""
    _guard(request, conn)
    ctype = request.headers.get("content-type") or ""
    is_form = "urlencoded" in ctype
    try:
        if is_form:
            form = {k: v[0] for k, v in
                    parse_qs((await request.body()).decode()).items()}
        else:
            form = (await request.json()
                    if int(request.headers.get("content-length") or 0) else {})
    except Exception:
        return JSONResponse({"error": "unreadable body — send form fields or JSON"}, status_code=400)

    def answer_error(msg: str, code: int):
        if is_form:
            return RedirectResponse(url=f"/approvals?flash={quote(msg)}&kind=refused",
                                    status_code=303)
        return JSONResponse({"error": msg}, status_code=code)

    decision = form.get("decision")
    if decision not in ("approved", "rejected"):
        return answer_error("decision must be approved|rejected", 400)
    if decision == "approved" and form.get("confirm") not in ("true", "on", True, "1", 1):
        return answer_error("confirm required — a second explicit gesture", 400)
    try:
        rec = gate.resolve(conn, record_id, decision,
                           by=(form.get("by") or identity_label(request, conn)),
                           reason=form.get("reason"))
    except Exception as e:
        return answer_error(str(e), 409)
    outcome = None
    if decision == "approved":
        from commerceos.catalog import delist, lifecycle, verify_sources
        from commerceos.spine import writes
        try:
            # the verification return leg (V2): an approved spec-verification
            # record runs through its own seam — the local flip, recorded and
            # render-checked — not the bare store door.
            record = ledger.get(conn, record_id)
            if record and record["proposal"]["method"] == verify_sources.METHOD:
                outcome = verify_sources.execute_and_record(conn, record_id)
            elif record and record["proposal"]["method"] == delist.METHOD:
                # the delist return leg (CW8w): the store write AND the
                # product's lifecycle move happen in the same act. the inner
                # store receipt (outcome, carrying top-level ok +
                # verified_rendered from writes.execute) IS the outcome, with
                # the lifecycle facts riding alongside.
                #
                # the lifecycle leg gets its OWN try — wrapping only this
                # call: a LifecycleError raised AFTER the store already
                # verify-rendered must never fall to the outer except and
                # read back as "nothing was written" (the store DID change).
                # the ledger already has the store's own receipt (writes.
                # execute fills it before lifecycle.transition runs), so on
                # failure we recover THAT receipt and answer honestly.
                try:
                    res = delist.execute_and_record(conn, record_id)
                except lifecycle.LifecycleError as e:
                    inner = (ledger.get(conn, record_id) or {}).get("outcome") or {}
                    if inner.get("verified_rendered"):
                        outcome = {**inner, "recorded": False, "transition": None,
                                   "error": "the change landed on the store; "
                                            f"recording its history failed — {e}"}
                    else:
                        outcome = {**inner, "recorded": False, "transition": None,
                                   "error": str(e)}
                else:
                    outcome = {**res["outcome"], "recorded": res["recorded"],
                               "transition": res["transition"], "state": res["state"]}
            else:
                outcome = writes.execute(conn, record_id)
        except Exception as e:
            outcome = {"ok": False, "error": str(e)[:300]}
    _refresh_reports(conn)
    await emit({"kind": f"gate.{decision}", "record_id": record_id})
    if is_form:
        record = ledger.get(conn, record_id)
        intent = (record or {}).get("intent") or "the request"
        if decision == "rejected":
            flash, kind = f"rejected: {intent} — nothing runs", "done"
        elif outcome and outcome.get("ok"):
            flash, kind = f"landed: {intent} — on the record", "done"
        else:
            err = (outcome or {}).get("error") or "the write did not land"
            flash, kind = f"refused: {err} — nothing was written", "refused"
        return RedirectResponse(url=f"/approvals?flash={quote(flash)}&kind={kind}",
                                status_code=303)
    return {"record": ledger.get(conn, record_id), "outcome": outcome}


@app.get("/approvals", response_class=HTMLResponse)
def approvals_view(request: Request, conn=Depends(_db)):
    _guard(request, conn)
    ledger.ensure_schema(conn)
    items = ledger.pending_queue(conn)          # live waits only, never lapsed
    # a held batch (WF-approve) shows ONCE — its own glance card, never its
    # hundred member rows; the members leave the per-item list.
    catalog_runs.ensure_schema(conn)
    staged_runs = [r for r in catalog_runs.list_runs(conn, status="staged")
                   if r["status"] == "staged"]
    in_batch = {it["record_id"] for r in staged_runs for it in r["items"]}
    items = [r for r in items if r["id"] not in in_batch]
    batch_cards = "".join(
        f"<div class='card'><strong>a batch of {r['live']:,} "
        f"{feature_label(r['feature'])} fixes</strong> waits as one glance — "
        f"every change previewed in plain words, one approve lands the lot. "
        f"<a href='/catalog/runs/{r['id']}'>glance and approve &rarr;</a></div>"
        for r in staged_runs)
    lapsed_note = ""
    lapsed = ledger.lapsed_queue(conn)
    if lapsed:
        lapsed_note = (
            f"<p class='muted'>{len(lapsed)} earlier request"
            f"{'s' if len(lapsed) != 1 else ''} waited past the approval window "
            f"and expired — nothing runs late. still wanted means a fresh batch, "
            f"re-proposed with current numbers.</p>")
    # the outcome of the click that just happened, in plain words — the
    # decisive moment never lands on a raw dump (the producer's SP1 re-walk).
    flash = request.query_params.get("flash")
    flash_card = ""
    if flash:
        strong = "refused" if request.query_params.get("kind") == "refused" else "done"
        flash_card = (f"<div class='card'><strong>{strong}:</strong> "
                      f"{html_escape(flash)}</div>")
    if not items and not batch_cards:
        body = flash_card + "<p class='muted'>nothing waits on you.</p>" + lapsed_note
    elif not items:
        body = flash_card + batch_cards + lapsed_note
    else:
        cards = []
        for r in items:
            prop = r["proposal"]
            # a listing draft gets its own plain card — product by name, the
            # change as was -> becomes, and why it parks (B2). never the raw
            # gate dump.
            if prop["method"] == "mutate_seo":
                cards.append(_seo_approval_card(conn, r))
                continue
            # the exact proposed change, in plain words — the ONE shared
            # renderer both decisions and the wall read (_change_plain), so
            # the two surfaces never disagree.
            change = _change_plain(conn, r)
            cards.append(f"""<div class='card'>
<strong>{function_label(r['function'])}</strong> · {action_type_label(r['action_type'])} · {method_label(prop['method'])}
 <span class='muted'>· by {r['agent']} · waits until {when_plain(r['expires_at'])}</span>
<div>{r['intent']}</div><div class='muted'>{r['rationale']}</div>
{change}
<form method='post' action='/api/approvals/{r['id']}' style='display:flex;gap:.6rem;align-items:center'>
 <label><input type='checkbox' name='confirm' value='true' required> confirm</label>
 <button name='decision' value='approved'>approve</button>
 <button name='decision' value='rejected' formnovalidate>reject</button>
</form></div>""")
        body = flash_card + batch_cards + "\n".join(cards) + lapsed_note
    return _page("decisions", body)


# the record's plain renderings (UI-truth, 2026-07-19): raw ISO stamps,
# Python booleans, machine-era intents, and mid-word cuts never reach the
# screen. the ledger stays append-only — these maps live at render time.
RECORD_STATUS_PLAIN = {
    "pending": "waiting on you", "approved": "approved", "executing": "running",
    "executed": "landed", "failed": "failed", "expired": "lapsed",
    "rejected": "rejected", "retired": "retired",
}

_OLD_BARCODE_INTENT = re.compile(r'^normalize barcode "\'?[^"]*" -> (\S+)$')
# the live ledger's dominant machine-era shape — most rows carry this exact
# batch intent (the producer's re-walk counted them; the single-row shape
# above covers only 100).
_OLD_BARCODE_BATCH = "normalize barcodes that are one spreadsheet artifact from a valid GTIN"


def intent_plain(intent: str, limit: int = 60) -> str:
    """old stored intents in today's words, cut at a word, never mid-letter."""
    m = _OLD_BARCODE_INTENT.match(intent or "")
    if m:
        intent = f"fix the barcode (now {m.group(1)})"
    elif (intent or "").startswith(_OLD_BARCODE_BATCH):
        intent = "fix barcodes a spreadsheet export broke"
    if len(intent) <= limit:
        return html_escape(intent)
    cut = intent[:limit].rsplit(" ", 1)[0].rstrip() or intent[:limit]
    return html_escape(cut) + "&hellip;"


def when_plain(ts: str) -> str:
    try:
        from datetime import datetime as _dt
        return (_dt.fromisoformat(ts.replace("Z", "+00:00"))
                .strftime("%b %d %H:%M").lower().replace(" 0", " "))
    except (ValueError, AttributeError):
        return (ts or "—")[:16]


def _product_name(conn, pid: str) -> str:
    """a product's shown name from the live facts (RAW — the caller escapes at
    the render site: fusion.ticket escapes a title, _change_plain escapes its
    interpolation). a plain fallback when it isn't found — never a gid, never a
    raw id on screen."""
    try:
        row = conn.execute("SELECT title FROM products WHERE shopify_id = ?",
                            (pid,)).fetchone()
        if row and row["title"]:
            return row["title"]
    except Exception:
        pass
    return "this product"


def _fmt_local(ts) -> str:
    """a stored ISO ts as LOCAL wall-clock, plain (coordinator ruling M2):
    '7:56 pm today' or 'jul 23, 9:04 am' when not today. the ONE absolute-time
    renderer on the wall — no raw stamp, no timezone claim reaches the screen.
    the 'changes today' COUNT stays UTC-internal (untouched); only display
    localizes."""
    from datetime import datetime as _dt
    try:
        dt = _dt.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return "—"
    if dt.tzinfo is not None:
        dt = dt.astimezone()          # to the server's local zone
    now = _dt.now(dt.tzinfo) if dt.tzinfo else _dt.now()
    hour = dt.hour % 12 or 12
    ampm = "am" if dt.hour < 12 else "pm"
    clock = f"{hour}:{dt.minute:02d} {ampm}"
    if dt.date() == now.date():
        return f"{clock} today"
    return f"{dt.strftime('%b').lower()} {dt.day}, {clock}"


def _age_plain(ts) -> str:
    """how long a wait has stood, plain and LOCAL (ruling M2 / minor 3):
    'just now', '9 minutes old', '3 hours old', '2 days old' — the wall's age
    renderer, never a raw stamp."""
    from datetime import datetime as _dt
    try:
        dt = _dt.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return ""
    now = _dt.now(dt.tzinfo) if dt.tzinfo else _dt.now()
    secs = (now - dt).total_seconds()
    if secs < 90:
        return "just now"
    mins = int(secs // 60)
    if mins < 60:
        return f"{mins} minute{'s' if mins != 1 else ''} old"
    hrs = int(secs // 3600)
    if hrs < 24:
        return f"{hrs} hour{'s' if hrs != 1 else ''} old"
    days = int(secs // 86400)
    return f"{days} day{'s' if days != 1 else ''} old"


def _change_plain(conn, r: dict, fusion_safe: bool = False) -> str:
    """the proposed change in plain words — the ONE renderer both /approvals
    and the wall/board read, so the surfaces cannot disagree (spec: the receipt
    in place). extracted move-only from the decisions per-method renderings
    (record_supplier, mutate_menu, the raw fallback); grown PLAIN branches
    (mutate_product_state, mutate_spec_verification, the barcode fix) so a
    fusion surface never shows a raw args dump.

    fusion_safe (CS2, ruled): the fusion surfaces (wall + board) pass True so
    an UNMAPPED method renders a plain 'technical change' line with a door to
    the record — a raw JSON dump may never reach a person's board/wall. the
    decisions page keeps the default (False → the raw <pre>): its per-method
    cards already carry the raw detail deliberately."""
    prop = r["proposal"]
    method = prop["method"]
    a = prop.get("args") or {}
    if method == "mutate_variant_field" and a.get("field") == "barcode":
        name = html_escape(_product_name(conn, str(a.get("product_id") or "")))
        val = html_escape(str(a.get("value") or ""))
        return f"<div>sets {name}'s barcode to {val}</div>"
    if method == "mutate_seo":
        return f"<div>{_seo_change(conn, r)}</div>"
    if method == "record_supplier":
        sup = a.get("supplier") or {}
        lines = [f"supplier: {html_escape(sup.get('name') or '')}"
                 + (f", terms {html_escape(sup['payment_terms'])}"
                    if sup.get("payment_terms") else ", no terms given")]
        po = a.get("purchase_order")
        if po:
            for ln in po.get("lines") or []:
                cost = ln.get("unit_cost_minor", 0)
                lines.append(
                    f"po {html_escape(po.get('id') or '')}"
                    f" dated {html_escape(po.get('created_at') or 'today')}:"
                    f" {ln.get('qty')} at {cost / 100:,.2f} AED"
                    f" ({cost} fils) each")
        return ("<div>" + "<br>".join(lines)
                + "<br><span class='muted'>lands in your own books"
                  " only — the store is never touched</span></div>")
    if method == "mutate_menu":
        titles = [it.get("title") for it in (a.get("items") or [])
                  if it.get("title")]
        n = len(titles)
        shown = ", ".join(html_escape(t) for t in titles[:6])
        if n > 6:
            shown += f", and {n - 6} more"
        return (f"<div>places {n} collection{'s' if n != 1 else ''} into "
                f"your store's main menu, in order — {shown}."
                f"<br><span class='muted'>this replaces your current menu "
                f"tree; your store's navigation changes only after you "
                f"approve</span></div>")
    if method == "mutate_product_state":
        name = html_escape(_product_name(conn, str(a.get("product_id") or "")))
        state = str(a.get("state") or "")
        if state == "delisted":
            return (f"<div>removes {name} from your store — buyers stop seeing "
                    f"it until you put it back.</div>")
        if state == "active":
            return (f"<div>returns {name} to your store — buyers can find and "
                    f"buy it again.</div>")
        return f"<div>changes {name}'s standing in your store.</div>"
    if method == "mutate_spec_verification":
        name = html_escape(_product_name(conn, str(a.get("product_id") or "")))
        return (f"<div>records a safety-detail check for {name} against the "
                f"maker's own page — the checked claims confirmed or flagged."
                f"</div>")
    if fusion_safe:
        return ("<div>a technical change — the record holds the raw details. "
                "<a href='/record'>the record</a></div>")
    return f"<pre style='overflow-x:auto'>{json.dumps(prop['args'], indent=1)}</pre>"


def _wall_title(r: dict) -> str:
    """the wait's title carries the PRODUCT, not the method (coordinator ruling
    M3): a verb + the product's name (via _product_name, attached as r['_name']
    at gather). the method identifier never reaches the screen. the name is RAW
    here — fusion.ticket escapes the whole title once."""
    prop = r["proposal"]
    method = prop["method"]
    a = prop.get("args") or {}
    name = r.get("_name") or "this product"
    if method == "mutate_product_state":
        state = str(a.get("state") or "")
        if state == "delisted":
            return f"remove {name} from the store"
        if state == "active":
            return f"return {name} to the store"
        return f"update {name} in the store"
    if method == "mutate_spec_verification":
        return f"check {name}'s details with the maker"
    if method == "mutate_seo":
        return f"rewrite {name}'s listing"
    if method == "record_supplier":
        return "record a supplier and its terms"
    if method == "mutate_menu":
        return "set the store's main menu"
    return html_unescape(intent_plain(r.get("intent") or "", 70))


# ---------- the wall (/wall): the collaboration surface's first screen ----

def _wall_clock() -> str:
    """the masthead's tiny stamp: server-local, lowercase 'thursday 10:30'
    (coordinator ruling 3 — a clock, not a record; no timezone claim)."""
    from datetime import datetime as _dt
    return _dt.now().strftime("%A %H:%M").lower()


def _fusion_doc(inner: str, since_line: str, head_extra: str = "") -> str:
    """the wall's full document — doctype + head (title, viewport) wrapping
    CS0's fusion.page() shell (coordinator ruling 3 — wrap page(), never
    duplicate its link/tiny-bar). the masthead clock rides page()'s since_line
    slot; the <title> is 'commerceos'. head_extra rides an optional extra head
    tag (CS2's board passes the meta-refresh ONLY while a run is executing — a
    resting page never reloads); the wall passes nothing and is unchanged."""
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        + head_extra +
        "<title>commerceos</title></head><body>"
        + fusion.page(inner, since_line=since_line)
        + "</body></html>"
    )


def _wall_eyes_ticket(conn, r: dict) -> str:
    """an ACTIVE-store wait the owner can act on: the title names the product
    (M3); the left meta carries the age and when it lapses (M2/minor 3); the
    row's RIGHT side is the wait's class in plain words ('needs your call'),
    NOT a link (producer round 2 M-D — the OPEN form is the only affordance,
    the self-anchor is dead weight). the confirm+approve+reject form is the
    opened depth (<details open>). hand-rendered to place the plain class on
    the right (fusion.ticket has no plain-text action slot — it only emits an
    anchor); every interpolated value escapes at its site, once."""
    rid = r["id"]
    title = html_escape(_wall_title(r))
    urgency = html_escape(action_type_label(r["action_type"]))
    age = _age_plain(r["ts"])
    submeta = ((f"{age} · " if age else "")
               + f"waits until {_fmt_local(r['expires_at'])}")
    change = _change_plain(conn, r, fusion_safe=True)
    form = (
        f"<form method='post' action='/api/approvals/{rid}'"
        f" style='display:flex;gap:.6rem;align-items:center'>"
        f"<label><input type='checkbox' name='confirm' value='true' required>"
        f" confirm</label>"
        f"<button name='decision' value='approved'>approve</button>"
        f"<button name='decision' value='rejected' formnovalidate>reject</button>"
        f"</form>")
    return (
        f'<div class="ticket waiting" id="wait-{rid}">'
        f'<div><span class="t">{title}</span>'
        f'<span class="m">{html_escape(submeta)}</span></div>'
        f'<span class="m">{urgency}</span>'
        f"</div>"
        f'<div class="receipt"><details open><summary>the change</summary>'
        f"{change}{form}</details></div>")


def _wall_batch_ticket(run: dict) -> str:
    """a held reversible batch as ONE amber ticket (never its members): the
    visible 'approve →' affordance doors to the run's glance-approve page where
    the one gesture lands the lot."""
    return fusion.ticket(
        title=f"a batch of {run['live']:,} {feature_label(run['feature'])} fixes",
        meta="one glance approves the lot",
        edge="waiting",
        action_label="approve",
        action_href=f"/catalog/runs/{run['id']}")


def _stopped_reason_plain(why: str) -> str:
    """a stopped item's why in plain words (m5, ruled): a raw error constant
    from an exception never reaches the screen — it maps to a sentence a person
    reads, and the raw string stays in the run receipt behind the ticket's
    door. an item that ran but did not verify already carries plain words
    ('executed, not verified — not counted'), so it rides through unchanged."""
    if why.startswith("errored"):
        if "THROTTLED" in why:
            return "the store told us to slow down"
        return "something failed — the receipt has the details"
    return why


def _wall_stopped_ticket(run: dict) -> str:
    """a stopped job as a first-class RED ticket (law 6): names the feature,
    what stopped and why (from the items' own state strings), and what was
    left untouched — doored to the full run receipt. fusion.ticket escapes the
    title and meta, so the record-born whys ride in the meta and escape there
    (the 1f7936e law)."""
    oc = run.get("outcome") or {}
    errored = oc.get("errored", 0)
    failed = oc.get("failed", 0)
    lapsed = oc.get("lapsed", 0)
    executed = oc.get("executed", 0)
    n_stopped = errored + failed
    whys = [it.get("state") or "" for it in run.get("items", [])
            if (it.get("state") or "").startswith("errored")
            or "not counted" in (it.get("state") or "")]
    why = whys[0] if whys else "a step did not finish"
    total = run.get("batch") or len(run.get("items", []))
    # m5 (ruled): a raw error constant (THROTTLED, a stack string) never reaches
    # the screen — a small plain map speaks here; the raw string stays in the
    # run receipt behind the door.
    bits = [f"{n_stopped} of {total} didn't finish", _stopped_reason_plain(why)]
    # m6 (ruled): finished members DO count in today's changes — say so on the
    # ticket so the top line reconciles on-page (no phantom mismatch).
    if executed:
        bits.append(f"the {executed} that finished count in today's changes")
    if lapsed:
        bits.append(f"{lapsed} lapsed, skipped — never run late")
    return fusion.ticket(
        title=f"{feature_label(run['feature'])} stopped",
        meta=" · ".join(bits),
        edge="stopped",
        action_label="see the run",
        action_href=f"/catalog/runs/{run['id']}")


def _foreign_line(active_label: str, label: str) -> str:
    """the line a non-active store's wait carries INSTEAD of an approve form
    (behavior 4: this process may only act for the store it speaks for). ruled
    string (producer round 2 M-C): states the fact, instructs NOTHING — no door
    that doesn't exist yet. returns the INNER receipt content; fusion.ticket
    wraps it in exactly one .receipt (no double-nest, the round-2 minor)."""
    return (f"waits at {html_escape(label)} — this desk speaks for "
            f"{html_escape(active_label)}")


def _wall_foreign_ticket(r: dict, view: dict, active_label: str) -> str:
    """another store's single wait — counted in the sentence, rendered FORMLESS
    (B1): the title names the product (M3), the meta carries the SAME age /
    waits-until shape as an active ticket (round-2 minor), the body states the
    fact. NO approve form, NO action anchor here."""
    age = _age_plain(r["ts"])
    meta = (f"{action_type_label(r['action_type'])}"
            + (f" · {age}" if age else "")
            + f" · waits until {_fmt_local(r['expires_at'])}")
    return fusion.ticket(title=_wall_title(r), meta=meta, edge="waiting",
                         body=_foreign_line(active_label, view["label"]))


def _wall_foreign_batch(run: dict, view: dict, active_label: str) -> str:
    """another store's held batch as ONE formless ticket (B1): named, counted,
    stating the fact — never an approve here."""
    return fusion.ticket(
        title=f"a batch of {run['live']:,} {feature_label(run['feature'])} fixes",
        meta="a held batch — its own desk approves it",
        edge="waiting",
        body=_foreign_line(active_label, view["label"]))


def _stopped_runs(conn) -> list[dict]:
    """for each feature, the LATEST done run; it is STOPPED iff its outcome
    shows errored>0 or failed>0 (the per-item isolation writes those states,
    runs.py:138-145). self-clearing (law 4, computed at render): a newer clean
    run of the same feature drops the stop off — no invented time window.
    wired to triage as its stopped source (CS0's separate argument)."""
    catalog_runs.ensure_schema(conn)
    latest: dict[str, dict] = {}
    for run in catalog_runs.list_runs(conn, status="done"):
        latest.setdefault(run["feature"], run)   # ts DESC → first is newest
    out = []
    for run in latest.values():
        oc = run.get("outcome") or {}
        if oc.get("errored", 0) > 0 or oc.get("failed", 0) > 0:
            out.append(run)
    return out


def _calm_line(label: str, waiting: int, running: int, changes: int) -> str:
    # "1 change today", "2 changes today" — a tiny pluralizer at the site
    # (round-2 minor); label is the registry label VERBATIM (never lowercased).
    return (f"<div class='calm'>{html_escape(label)} — "
            f"<b>{waiting}</b> waiting on you · {running} running · "
            f"{changes} change{'s' if changes != 1 else ''} today</div>")


def _folded_waits(views) -> list[dict]:
    """the triage INPUT, folded to DECISIONS not members (producer round 2
    M-B): a held batch is ONE thing needing you — one glance lands it. each
    store contributes its singles plus one reversible stand-in per staged run,
    so the sentence counts a batch as one. the calm lines fold the same way
    (waiting = staged + singles), so sentence and calm never disagree."""
    rows: list[dict] = []
    for v in views:
        rows.extend(v["singles"])
        rows.extend({"action_type": "reversible"} for _ in v["staged"])
    return rows


def _view_from_conn(c, name: str, label: str, is_active: bool) -> dict:
    """read one store's wall picture from a live connection: its pending waits
    (each tagged with the store + its product name for the M3 title), its held
    batches, and the calm-line counts. changes-today prefix-matches today's UTC
    date against the OUTCOME ts (ledger.py:275) — NEVER query's day= submission
    filter (the audit's ruled trap). SELECT-only: a read-only conn survives it
    (no ensure_schema)."""
    from datetime import datetime as _dt, timezone as _tz
    pending = ledger.pending_queue(c)
    staged = [r for r in catalog_runs.list_runs(c, status="staged")
              if r["status"] == "staged"]
    # a member of ANY unfinished run is NOT a loose wait: a staged batch folds
    # to one wait (its stand-in below), and an EXECUTING batch is not a wait at
    # all — it is my-side's running work. excluding both here means neither the
    # board's your-side nor the wall ever renders a batch member as a stray
    # ticket with its own form (B1 — the double-zone lie, latent on both).
    executing = catalog_runs.list_runs(c, status="executing")
    in_batch = {it["record_id"] for r in (staged + executing) for it in r["items"]}
    singles = [r for r in pending if r["id"] not in in_batch]
    for r in pending:
        a = r["proposal"].get("args") or {}
        r["_name"] = _product_name(c, str(a.get("product_id") or ""))
        r["_store"] = name
    running = len(catalog_runs.list_runs(c, status="executing"))
    today = _dt.now(_tz.utc).strftime("%Y-%m-%d")
    changes = c.execute(
        "SELECT COUNT(*) FROM ledger WHERE status = 'executed'"
        " AND substr(json_extract(outcome, '$.ts'), 1, 10) = ?",
        (today,)).fetchone()[0]
    return {"name": name, "label": label, "is_active": is_active, "ok": True,
            "missing": False, "pending": pending, "staged": staged,
            "singles": singles, "in_batch": in_batch,
            "waiting": len(staged) + len(singles), "running": running,
            "changes": changes}


def _blank_view(name: str, label: str, *, ok: bool, missing: bool) -> dict:
    return {"name": name, "label": label, "is_active": False, "ok": ok,
            "missing": missing, "pending": [], "staged": [], "singles": [],
            "in_batch": set(), "waiting": 0, "running": 0, "changes": 0}


def _wall_store_views(conn):
    """read EVERY registry store once (B1: the wall triages the WHOLE
    business). the active store from this request's conn; every OTHER store
    from its own db opened READ-ONLY (mode=ro enforces the never-written law
    mechanically) — behavior 4 means this process may ACT only for the active
    store, so other stores' waits render formless. returns (views, active)."""
    import sqlite3
    try:
        reg = stores.load_registry()
        active = stores.active_store()
    except Exception:
        return [], None
    views = []
    for row in reg["stores"]:
        name = row["name"]
        label = row.get("label") or name
        if name == active:
            views.append(_view_from_conn(conn, name, label, True))
            continue
        try:
            path = Path(stores.resolve(name, stores.DB))
        except Exception:
            views.append(_blank_view(name, label, ok=False, missing=False))
            continue
        if not path.exists():
            views.append(_blank_view(name, label, ok=True, missing=True))
            continue
        try:
            ro = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            ro.row_factory = sqlite3.Row
            try:
                views.append(_view_from_conn(ro, name, label, False))
            finally:
                ro.close()
        except Exception:
            views.append(_blank_view(name, label, ok=False, missing=False))
    return views, active


def _wall_calm_from_views(views) -> str:
    """one calm line per store, from the SAME gather the sentence used — the
    two cannot disagree. mirror/health numbers do NOT ride here (law 3 by
    absence: repo-global, store-ambiguous, they would lie per-store)."""
    lines = []
    for v in views:
        if v.get("missing"):
            lines.append(f"<div class='calm'>{html_escape(v['label'])} — "
                         f"nothing set up yet</div>")
        elif not v.get("ok", True):
            lines.append(f"<div class='calm'>{html_escape(v['label'])} — "
                         f"couldn't read its numbers right now</div>")
        else:
            lines.append(_calm_line(v["label"], v["waiting"], v["running"],
                                    v["changes"]))
    return "".join(lines)


def _wall_doors_from_views(views, active) -> str:
    """the doors row: every store's name is now a REAL door to its own board
    (CS2 flipped M4's 'no link' default — /board/{store} exists now, so the
    active store's door moves off /catalog and every once-dead plain-text name
    becomes a true link to its board). the record is always a real door."""
    doors = []
    for v in views:
        doors.append(f"<a href='/board/{v['name']}'>{html_escape(v['label'])}</a>")
    if not doors:
        doors.append("<a href='/catalog'>your store</a>")
    doors.append("<a href='/record'>the record</a>")
    return f"<div class='doors'>{''.join(doors)}</div>"


@app.get("/wall", response_class=HTMLResponse)
def wall(request: Request, conn=Depends(_db)):
    """the collaboration surface's first screen (spec/parts/collab-surface.md,
    the fusion of the quiet page and the desk). one sentence names the size of
    the WHOLE business's day (every store's live waits); the active store's
    work renders as tickets the owner can act on (eyes-first per item, ONE
    honest batch ticket per held reversible run); every OTHER store's waits are
    counted and rendered formless, doored to their own desk (behavior 4); one
    calm line per store; doors. an empty day says so honestly. opens BESIDE
    home — `/` is untouched. reads only: a GET of /wall writes NOTHING (no
    _refresh_reports, no writer)."""
    _guard(request, conn)
    ledger.ensure_schema(conn)
    catalog_runs.ensure_schema(conn)

    # read every store ONCE (B1). the sentence and the calm lines come from
    # this one gather, so they can never disagree.
    views, active = _wall_store_views(conn)
    active_view = next((v for v in views if v["is_active"]), None)
    active_label = active_view["label"] if active_view else (active or "your store")
    active_stopped = _stopped_runs(conn)

    # the sentence triages the WHOLE business, counting DECISIONS not members
    # (M-B): a held batch folds to one wait. split at the first ". " — the
    # first sentence is the h2 focus, the triage-split + stopped clauses ride
    # a quiet .sub line under it (the ruled comp's h2+sub; triage.sentence
    # stays one string).
    tri = triage.triage(_folded_waits(views), stopped=active_stopped)
    first, _sep, rest = tri.sentence.partition(". ")
    head = first if first.endswith(".") else first + "."
    parts = [f"<h2>{html_escape(head)}</h2>"]
    if rest:
        parts.append(f"<div class='sub'>{html_escape(rest)}</div>")

    # the active store — the desk this process speaks for: full tickets the
    # owner can act on, grouped eyes-first (needs-your-call singles) then
    # routine (held batches folded to one ticket + any loose reversible).
    if active_view:
        eyes = [r for r in active_view["singles"]
                if r["action_type"] != "reversible"]
        loose = [r for r in active_view["singles"]
                 if r["action_type"] == "reversible"]
        if eyes:
            parts.append(fusion.group_label("your eyes first"))
            for r in eyes:
                parts.append(_wall_eyes_ticket(conn, r))
        if active_view["staged"] or loose:
            parts.append(fusion.group_label(
                "routine — all reversible, verified before they count"))
            for run in active_view["staged"]:
                parts.append(_wall_batch_ticket(run))
            for r in loose:
                parts.append(_wall_eyes_ticket(conn, r))

    # stopped (active store): first-class red tickets (law 6).
    if active_stopped:
        parts.append(fusion.group_label("stopped, honestly"))
        for run in active_stopped:
            parts.append(_wall_stopped_ticket(run))

    # every OTHER store's waits — counted in the sentence above, rendered
    # FORMLESS under their own label, stating the fact (behavior 4, M-C).
    for v in views:
        if v["is_active"] or not (v["staged"] or v["singles"]):
            continue
        parts.append(fusion.group_label(v["label"]))
        for run in v["staged"]:
            parts.append(_wall_foreign_batch(run, v, active_label))
        for r in v["singles"]:
            parts.append(_wall_foreign_ticket(r, v, active_label))

    # one calm line per store (from the same gather), then a quiet lapsed line
    # (minor 2) doored to the real record, then the doors.
    parts.append(_wall_calm_from_views(views))
    lapsed = ledger.lapsed_queue(conn)
    if lapsed:
        n = len(lapsed)
        parts.append(
            f"<div class='calm'>{n} wait{'s' if n != 1 else ''} lapsed, named "
            f"on <a href='/record?status=lapsed'>the record</a></div>")
    parts.append(_wall_doors_from_views(views, active))

    return _fusion_doc("\n".join(parts), _wall_clock())


# ---------- the board (/board/{store}): the desk for one store ------------

# the onboarding ceremony in plain words (RULED so no builder invents it) —
# a non-active store's read-only card reads its registry stamps through this;
# a missing stamp renders "not yet" beside the same phrase (stores.py:124).
_BOARD_STAMP_MAP = (
    ("config", "settings written"),
    ("register", "on the roster"),
    ("migrate", "database ready"),
    ("first_tick", "first heartbeat ran"),
    ("first_render", "first screen rendered"),
)


def _board_health_line() -> str:
    """the active store's audit number wearing its measured date through CS0's
    aged() (law 3, the mirror-as-of lint's one formatter — the source is
    _health(), its date field read the same way /catalog reads it) — else the
    honest gap. the mirror is repo-global (store-ambiguous, named in
    context.md's open questions); it rides HERE because the board IS the active
    store's desk, its audit."""
    h = _health()
    score = h.get("overall_score")
    if not isinstance(score, (int, float)):
        return "no health check yet"
    mdate = h.get("date") or ""
    try:
        from datetime import datetime as _dt
        asof = _dt.strptime(mdate, "%Y-%m-%d").strftime("%b %d").lower().replace(" 0", " ")
    except Exception:
        asof = mdate or "—"
    return "health " + fusion.aged(f"{score:g}", asof)


def _board_readonly(row: dict, label: str, active_label: str) -> str:
    """a known store that is NOT this desk's: an honest read-only card — the
    label, its onboarding ceremony in plain words (the RULED stamp map), and
    the behavior-4 line. NO zones, NO forms: this process may act only for the
    store it speaks for (teletext.py:90-92) — pretending to act across stores
    would aim the gate at the wrong ledger."""
    stamps = row.get("onboarding") or {}
    lines = []
    for key, phrase in _BOARD_STAMP_MAP:
        lines.append(f"<div>{phrase}</div>" if key in stamps
                     else f"<div>{phrase} — not yet</div>")
    return (
        f"<h2>{html_escape(label)}</h2>"
        f"<div class='readonly'>{''.join(lines)}</div>"
        f"<div class='sub'>this desk speaks for {html_escape(active_label)} — "
        f"open {html_escape(label)} from its own desk to act.</div>"
        f"<div class='doors'><a href='/wall'>the wall</a></div>")


def _board_landed(conn, today: str, stopped_ids: set) -> list[str]:
    """below the zones — what landed on YOUR approve today: done runs (each ONE
    green ticket, doored to its receipt; a stopped run is omitted here, it rides
    the red group above), and executed singles that are NOT run members (the run
    ticket already carries its members — the double-count guard). the group
    label is inline in app.py, never a FUSION_*_PLAIN set: the land-guard's
    allowlist entries must open with 'you', so a fusion.py placement would hit
    an unfixable lint (the audit's named trap). empty → the group is omitted;
    silence is the product."""
    all_done = [run for run in catalog_runs.list_runs(conn, status="done")
                if (run.get("approved_ts") or "")[:10] == today]
    # a loose landed single is an executed record that belongs to NO run. so
    # exclude the members of every done run today (stopped or not) AND every
    # still-EXECUTING run (B1's twin): an executing batch's committed members
    # are its progress on my side, never N separate landed gestures — they
    # reach landed-today only when the run flips done, as ONE batch ticket
    # (the same union _view_from_conn folds waits by). only NON-stopped done
    # runs earn a green batch ticket (a stop is first-class red above, never green).
    executing = catalog_runs.list_runs(conn, status="executing")
    members = {it["record_id"] for run in all_done for it in run["items"]}
    members |= {it["record_id"] for run in executing for it in run["items"]}
    done = [run for run in all_done if run["id"] not in stopped_ids]
    singles = [r for r in ledger.query(conn, status="executed", limit=500)
               if ((r.get("outcome") or {}).get("ts") or "")[:10] == today
               and r["id"] not in members]
    if not done and not singles:
        return []
    # the group label LEADS with "you" so the land-guard reads the owner as the
    # subject of "landed" (M4): one phrase, owner-first, "landed today" intact.
    parts = [fusion.group_label("you approved these — landed today")]
    for run in done:
        counted = (run.get("outcome") or {}).get("counted", 0)
        parts.append(fusion.ticket(
            title=f"a batch of {run['batch']:,} {feature_label(run['feature'])} fixes",
            meta=f"you approved · {counted:,} showed up live",
            edge="done", action_label="open",
            action_href=f"/catalog/runs/{run['id']}"))
    for r in singles:
        a = r["proposal"].get("args") or {}
        r["_name"] = _product_name(conn, str(a.get("product_id") or ""))
        who = html_escape(who_plain((r.get("gate") or {}).get("by")))
        body = (f"<details><summary>the receipt</summary>"
                f"<div class='sub'>you approved · {who}</div>"
                f"{_change_plain(conn, r, fusion_safe=True)}</details>")
        parts.append(fusion.ticket(
            title=html_escape(_wall_title(r)),
            meta="you approved · verified on the store",
            edge="done", body=body))
    return parts


@app.get("/board/{store}", response_class=HTMLResponse)
def board(store: str, request: Request, conn=Depends(_db)):
    """the collaboration surface's second screen (spec/parts/collab-surface.md):
    GET /board/{store}, the desk proper for ONE store. three answers — an
    unknown store is a plain fusion 404 with a door to the wall (never a raw
    JSON dump on a person's screen); a known store that is not this desk's is a
    read-only card stating its onboarding, no forms (behavior 4); the active
    store is the full board: two zones — MY SIDE (running work, progress read
    LIVE from ledger statuses) and YOUR SIDE (waiting tickets through the wall's
    own landed helpers) — a stopped group, landed today, five doors. READS only
    (ledger rows, workflow-run rows, the registry, the health mirror); a GET
    writes NOTHING."""
    _guard(request, conn)
    ledger.ensure_schema(conn)
    catalog_runs.ensure_schema(conn)

    try:
        reg = stores.load_registry()
        active = stores.active_store()
    except Exception:
        reg, active = {"stores": []}, None
    rows = {r["name"]: r for r in reg.get("stores", [])}
    row = rows.get(store)

    # (1) unknown store → a plain fusion 404, never a raw JSON answer.
    if row is None:
        inner = (f"<h2>no store called {html_escape(store)} here.</h2>"
                 f"<div class='doors'><a href='/wall'>the wall</a></div>")
        return HTMLResponse(_fusion_doc(inner, None), status_code=404)

    label = row.get("label") or store
    active_label = (rows.get(active) or {}).get("label") or active or "the active store"

    # (2) a known store that is NOT this desk's → the read-only card.
    if store != active:
        return HTMLResponse(_fusion_doc(_board_readonly(row, label, active_label), None))

    # (3) the active store → the full board.
    from datetime import datetime as _dt, timezone as _tz
    view = _view_from_conn(conn, active, label, True)
    executing = catalog_runs.list_runs(conn, status="executing")
    running = len(executing)
    # M3 (ruled): an auto-refresh would wipe a half-filled confirm checkbox.
    # so the meta-refresh rides ONLY when a run executes AND no approve form is
    # on the page; when a form IS present, my-side offers a person-controlled
    # 'refresh ↻' link instead (a real door the owner chooses to walk).
    has_forms = bool(view["singles"])

    # the top line (the comp's tiny bar): {label} · running|quiet, then the
    # health mirror (aged) and today's real change count.
    state = "running" if running else "quiet"
    changes = view["changes"]
    # the health number wears a quiet door to its breakdown (owner-ruled
    # 2026-07-22: every number opens; /catalog is where the score lives).
    # the honest no-mirror gap stays doorless — nothing to open.
    health = _board_health_line()
    health_html = (f"<a href='/catalog'>{html_escape(health)}</a>"
                   if health != "no health check yet" else html_escape(health))
    right_rest = f"{changes:,} change{'s' if changes != 1 else ''} today"
    parts = [
        f"<div class='tiny'><span>{html_escape(label)} · {state}</span>"
        f"<span>{health_html} · {html_escape(right_rest)}</span></div>",
        "<div class='zones'>",
    ]

    # MY SIDE: executing runs. the progress law — the run row's items json is
    # written ONLY at the end (runs.py:149-150); mid-run truth is the ledger's
    # per-record commits. n_done = the run's records whose ledger status is
    # executed/failed/expired (an in-flight 'executing' item is NOT done —
    # the trailing-by-one honesty). computed at render, never cached (law 4).
    refresh_link = (f" <a href='/board/{html_escape(active)}'>refresh ↻</a>"
                    if running and has_forms else "")
    parts.append(f"<div><h3>my side{refresh_link}</h3>")
    if executing:
        for run in executing:
            n_done = sum(
                1 for it in run["items"]
                if (rec := ledger.get(conn, it["record_id"]))
                and rec["status"] in ("executed", "failed", "expired"))
            parts.append(fusion.ticket(
                title=f"{feature_label(run['feature'])} — {n_done:,} of {run['batch']:,}",
                meta="each verified before it counts", edge="running"))
    else:
        parts.append("<div class='sub'>my hands are empty — nothing running.</div>")
    parts.append("</div>")

    # YOUR SIDE: waiting tickets, folded (a held batch counts as ONE — the
    # home-heading honesty law), rendered through the wall's OWN helpers (a
    # third caller of _change_plain via _wall_eyes_ticket, never a re-derive).
    parts.append(f"<div><h3>your side — {view['waiting']:,} waiting</h3>")
    if view["staged"] or view["singles"]:
        for run in view["staged"]:
            parts.append(_wall_batch_ticket(run))
        for r in view["singles"]:
            parts.append(_wall_eyes_ticket(conn, r))
    else:
        parts.append("<div class='sub'>nothing waits on you.</div>")
    parts.append("</div></div>")   # close your-side, then zones

    # STOPPED: first-class red tickets, above landed today (law 6) — from the
    # LANDED _stopped_runs, called not reimplemented.
    stopped = _stopped_runs(conn)
    if stopped:
        parts.append(fusion.group_label("stopped, honestly"))
        for run in stopped:
            parts.append(_wall_stopped_ticket(run))

    # LANDED TODAY (below the zones).
    today = _dt.now(_tz.utc).strftime("%Y-%m-%d")
    parts.extend(_board_landed(conn, today, {r["id"] for r in stopped}))

    # the comp's five doors, mapped to real pages (checks → /parts, the system
    # self-report; the naming rides context.md's open question).
    parts.append(
        "<div class='doors'>"
        "<a href='/catalog'>catalog</a><a href='/economics'>money</a>"
        "<a href='/parts'>checks</a><a href='/fleet'>agents</a>"
        "<a href='/record'>the record</a></div>")

    # the meta-refresh rides ONLY while a run executes AND no confirm form is on
    # the page (M3) — a resting board never reloads, and a board carrying a
    # half-filled confirm never has it wiped from under the owner's hands.
    head_extra = ("<meta http-equiv='refresh' content='3'>"
                  if running and not has_forms else "")
    return _fusion_doc("\n".join(parts), None, head_extra)


@app.get("/record", response_class=HTMLResponse)
def record_view(request: Request, conn=Depends(_db)):
    """the record — every act, newest first. ?agent=<name> narrows it to one
    agent's acts (the fleet page's track-record figures land here), and the
    who column names the actor on every row, each opening to that filter."""
    _guard(request, conn)
    ledger.ensure_schema(conn)
    agent = (request.query_params.get("agent") or "").strip() or None
    status = (request.query_params.get("status") or "").strip() or None
    if status == "lapsed":
        # lapsed is a render truth, not a stored status: pending rows past
        # their expiry plus the sweep's flipped ones (UI-truth2 — the home
        # lapsed card's door lands here and finds all of them)
        pend = [r for r in ledger.query(conn, agent=agent, status="pending", limit=500)
                if ledger.expired(r["expires_at"])]
        rows = sorted(pend + ledger.query(conn, agent=agent, status="expired", limit=500),
                      key=lambda r: r["ts"], reverse=True)[:100]
        total = len(pend) + len(ledger.query(conn, agent=agent, status="expired", limit=500))
    elif status:
        rows = ledger.query(conn, agent=agent, status=status, limit=100)
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM ledger WHERE status = ?"
            + (" AND agent = ?" if agent else ""),
            (status, agent) if agent else (status,)).fetchone()["n"]
    else:
        rows = ledger.query(conn, agent=agent, limit=100)
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM ledger" + (" WHERE agent = ?" if agent else ""),
            (agent,) if agent else ()).fetchone()["n"]
    filter_line = ""
    if agent or status:
        showing = " ".join(x for x in (
            RECORD_STATUS_PLAIN.get(status, status) if status else "",
            f"acts by <strong>{agent}</strong>" if agent else "acts") if x)
        filter_line = (f"<p class='muted'>showing: {showing} · "
                       f"<a href='/record'>see everything</a></p>")
    if total > len(rows):
        # a page named "record" implies the whole memory — a window says so
        filter_line += (f"<p class='muted'>showing the newest {len(rows):,}"
                        f" of {total:,} acts.</p>")
    if not rows:
        empty = (f"no acts by {agent} on the record yet."
                 if agent else "the record is empty — nothing has acted yet.")
        body = filter_line + f"<p class='muted'>{empty}</p>"
    else:
        def landed(r):
            ok = (r["outcome"] or {}).get("ok")
            if ok is True:
                return "yes"
            if ok is False:
                return "no — nothing changed"
            return "—"  # no outcome yet: still waiting, or never ran

        def status_plain(r):
            # a pending row past its expiry is lapsed wherever it renders —
            # the stored status is the mechanism's, the word is the truth's
            if r["status"] == "pending" and ledger.expired(r["expires_at"]):
                return "lapsed"
            return RECORD_STATUS_PLAIN.get(r["status"], r["status"])

        trs = "".join(
            f"<tr><td class='muted'>{when_plain(r['ts'])}</td>"
            f"<td><a href='/record?agent={r['agent']}'>{r['agent']}</a></td>"
            f"<td>{function_label(r['function'])}</td>"
            f"<td>{method_label(r['proposal']['method'])}</td>"
            f"<td>{status_plain(r)}</td>"
            f"<td>{intent_plain(r['intent'])}</td>"
            f"<td class='muted'>{landed(r)}</td></tr>"
            for r in rows)
        body = (filter_line
                + f"<table><tr><th>when</th><th>who</th><th>area</th><th>action</th>"
                  f"<th>status</th><th>what it was for</th><th>did it land</th></tr>{trs}</table>")
    return _page("record", body)


@app.get("/findings", response_class=HTMLResponse)
def findings_view(request: Request, conn=Depends(_db)):
    """the findings page — everything the watching noticed, both directions,
    engine rows and analyst hunts as the SAME first-class shape: the plain
    sentence, where it came from (the watch row or the hunt, plainly named),
    its lifecycle state, its age, its evidence counted honestly, and where it
    was sent. no raw identifier — metric keys, dispositions, evidence ids —
    ever reaches the screen."""
    _guard(request, conn)
    from commerceos.watching import findings as f, schema as wschema
    wschema.ensure_schema(conn)
    rows = f.query(conn, limit=100)
    open_n = sum(1 for r in rows if r["disposition"] in f.OPEN_DISPOSITIONS)

    # the watch rows resting on stale facts — said on the page, not just in
    # the self-report: a finding fed by week-old facts is a different claim.
    stale = [r["metric"] for r in conn.execute(
        "SELECT DISTINCT metric FROM evaluations e WHERE stale = 1 AND period ="
        " (SELECT max(period) FROM evaluations WHERE metric = e.metric AND slice = e.slice)"
        " ORDER BY metric")]
    total_watched = conn.execute(
        "SELECT count(DISTINCT metric) c FROM evaluations").fetchone()["c"]
    stale_line = ""
    if stale:
        names = ", ".join(finding_area(m) for m in stale)
        stale_line = (f"<p class='muted'>{len(stale)} of {total_watched} watched "
                      f"numbers rest on stale facts right now ({names}) — those "
                      f"rows say nothing new until fresh facts land.</p>")

    # ?finding=<id> opens ONE finding: its evidence laid out row by row in
    # plain words, and — the lifecycle's middle step — a recorded decide
    # action while it is still open.
    detail = ""
    fid = (request.query_params.get("finding") or "").strip()
    if fid:
        fr = f.get(conn, fid)
        if fr is None:
            detail = "<p class='muted'>no such finding — it may have been trimmed from the list below.</p>"
        else:
            def _fmt_val(v):
                if v is None:
                    return "still forming"
                return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:g}"

            drows = (tt.state_row("what was noticed", sentence_plain(fr))
                     + tt.state_row("kind", fr["direction"])
                     + tt.state_row("state", disposition_label(fr["disposition"]))
                     + tt.state_row("age", age_plain(fr["age_days"]))
                     + tt.state_row("routes to", fr["route"] or "—"))
            if fr.get("decided_reason"):
                drows += tt.state_row("the decision", fr["decided_reason"])
            ev = fr["evidence"] if isinstance(fr["evidence"], dict) else {}
            etrs = ""
            for eid in ev.get("evaluations") or []:
                er = conn.execute(
                    "SELECT metric, slice, period, value, baseline FROM evaluations"
                    " WHERE id = ?", (eid,)).fetchone()
                if er is None:
                    etrs += ("<tr><td class='muted' colspan='4'>a reading no longer "
                             "on file (its id stays in the record)</td></tr>")
                else:
                    etrs += (f"<tr><td>{finding_area(er['metric'], er['slice'])}</td>"
                             f"<td>{er['period']}</td><td>{_fmt_val(er['value'])}</td>"
                             f"<td class='muted'>{_fmt_val(er['baseline'])}</td></tr>")
            if etrs:
                drows += (f"<table><tr><th>the reading</th><th>period</th>"
                          f"<th>number</th><th>baseline</th></tr>{etrs}</table>")
            facts = ev.get("facts") or []
            if facts:
                flis = "".join(f"<li>{fact_ref_plain(x)}</li>" for x in facts)
                drows += (f"<div class='teletext-row'><p class='muted'>the landed "
                          f"facts behind it:</p></div><ul>{flis}</ul>")
            if fr["disposition"] in f.OPEN_DISPOSITIONS:
                drows += (
                    f"<form method='post' action='/findings/{fr['id']}/decide'"
                    f" class='run-form'>"
                    f"<input name='reason' size='40' required"
                    f" placeholder='what you decided, and why'>"
                    f"<button class='run'>record the decision</button></form>"
                    f"<div class='teletext-row'><p class='muted'>recording a decision "
                    f"moves this finding to decided with your reason kept — it "
                    f"changes nothing in your store.</p></div>")
            detail = tt.block("p701 · one finding, opened", drows,
                              "the readings and facts behind it",
                              block_id="finding")
            detail += "<p><a href='/findings'>&larr; all findings</a></p>"

    if not rows:
        body = stale_line + (detail or "<p class='muted'>nothing flagged yet.</p>")
    else:
        trs = "".join(
            f"<tr><td>{r['direction']}</td><td>{sentence_plain(r)}</td>"
            f"<td class='muted'>{finding_area(r['metric'], r['slice'])}</td>"
            f"<td>{disposition_label(r['disposition'])}</td>"
            f"<td class='muted'>{age_plain(r['age_days'])}</td>"
            f"<td><a href='/findings?finding={r['id']}#finding'>"
            f"{evidence_count(r['evidence'])}</a></td>"
            f"<td class='muted'>{r['route'] or '—'}</td></tr>" for r in rows)
        body = stale_line + detail + tt.block(
            "p700 · what the watching noticed",
            f"<table><tr><th>kind</th><th>what was noticed</th><th>where</th>"
            f"<th>state</th><th>age</th><th>the evidence</th><th>routes to</th></tr>{trs}</table>",
            "noticed → routed → decided → done · or aged out")
    marquee = tt.masthead(
        "growth", f"{open_n}",
        f"finding{'s' if open_n != 1 else ''} open · risks and openings both",
        as_of=_asof())
    return _page("growth", body, marquee=marquee,
                 signoff_line="every finding carries its evidence · an ignored one ages "
                              "visibly, it never disappears")


@app.post("/findings/{finding_id}/decide")
async def findings_decide(finding_id: str, request: Request, conn=Depends(_db)):
    """record the owner's decision on ONE open finding — the lifecycle's
    middle step (noticed/routed -> decided), reason required and kept. this
    is disposition bookkeeping on the watching's own table: it touches no
    store and approves nothing — anything consequential still rides the gate."""
    _guard(request, conn)
    from commerceos.watching import findings as f
    reason = request.query_params.get("reason")
    if not reason:
        try:
            reason = parse_qs((await request.body()).decode()).get("reason", [None])[0]
        except Exception:
            reason = None
    if not (reason and reason.strip()):
        return JSONResponse({"error": "a decision carries its reason"}, status_code=400)
    try:
        f.decide(conn, finding_id, reason.strip())
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=409)
    return RedirectResponse(url=f"/findings?finding={finding_id}#finding", status_code=303)


@app.get("/economics", response_class=HTMLResponse)
def economics_view(request: Request, conn=Depends(_db)):
    _guard(request, conn)
    from commerceos.economics import engine
    period = request.query_params.get("period", "2025")
    lane = request.query_params.get("lane", "company")
    try:
        pnl = engine.assemble(conn, period, lane=lane)
    except Exception as e:
        return _page("money", f"<p class='muted'>couldn't load the {period} numbers ({lane}): {e}</p>")
    trs = ""
    for key, cell in pnl.get("cells", {}).items():
        val = cell.get("value")
        if cell.get("unit") == "fils" and isinstance(val, (int, float)):
            shown = f"{val/100:,.2f} AED"
        elif cell.get("unit") == "bps" and isinstance(val, (int, float)):
            shown = f"{val/100:.2f}%"
        else:
            shown = str(val)
        count = sum(src.get("count", 0) for src in cell.get("sources", []))
        trs += f"<tr><td>{econ_label(key)}</td><td>{shown}</td><td class='muted'>from {count} facts</td></tr>"
    for gap in pnl.get("gaps", []):
        trs += f"<tr><td>{econ_label(gap['name'])}</td><td class='muted'>{gap['reason']}</td><td class='muted'>no data yet</td></tr>"
    scenario_form = """<div class='card'><strong>what-if</strong> — change a number over your real baseline and see the effect
<form method='get' action='/economics/scenario'>
 <input type='hidden' name='period' value='%s'>
 sales <input name='sales_pct' value='0' size='4'>%% ·
 purchases <input name='purchases_pct' value='0' size='4'>%%
 <button>show me</button></form></div>""" % period
    other = "learnings" if lane == "company" else "company"
    lane_line = (f"showing: <strong>{lane}</strong> · "
                 f"<a href='/economics?period={period}&lane={other}'>see {other}</a>"
                 + (" <span class='muted'>— the old company's books, for reference only — never mixed in</span>"
                    if lane == "learnings" else
                    " <span class='muted'>— your own store's real numbers</span>"))
    body = (f"<div class='card'>{lane_line}</div>"
            f"<div class='card'><strong>profit &amp; loss · {period} ({lane})</strong> — every number from real, sourced data"
            f"<table><tr><th>line</th><th>value</th><th>where from</th></tr>{trs}</table></div>"
            + scenario_form
            + "<p class='muted'><a href='/suppliers'>suppliers &amp; purchase costs"
              " &rarr;</a> — enter what you buy and what it costs; every entry"
              " waits for your approval before it becomes a number here.</p>")
    return _page("money", body)


# ------------------------------------------------------- /suppliers ---
# SP1: supplier + purchase-order facts entered by hand, landed only through
# the gate. the form submits a proposal that PARKS; your approval in
# decisions runs the local executor, which writes the facts with operator:
# provenance; the economics COGS cell (po_purchases) reads them. errors
# re-render this page inline with the typing preserved — a JSON body is
# never a page the operator lands on (the producer's cold read).

def _suppliers_page(conn, error: str | None = None, vals: dict | None = None,
                    submitted: str | None = None) -> str:
    v = {k: html_escape(str(vals.get(k) or "")) for k in
         ("name", "payment_terms", "po_id", "po_date", "qty", "unit_cost",
          "variant_id", "why")} if vals else dict.fromkeys(
        ("name", "payment_terms", "po_id", "po_date", "qty", "unit_cost",
         "variant_id", "why"), "")
    rows = ""
    sup_rows = list(conn.execute(
        "SELECT name, payment_terms, source, fetched_at FROM suppliers"
        " ORDER BY name")) if _table_exists(conn, "suppliers") else []
    po_count = (conn.execute("SELECT COUNT(*) AS n FROM purchase_orders").fetchone()["n"]
                if _table_exists(conn, "purchase_orders") else 0)
    for s in sup_rows:
        if s["source"].startswith(("fta:", "zoho:")):
            book = "the FTA purchase listing" if s["source"].startswith("fta:") \
                else "the Zoho books"
            prov = f"carried over from the old company's records ({book})"
        elif s["source"].startswith("operator:"):
            prov = ("entered by hand, approved —"
                    " <a href='/record?agent=operator-web'>the record</a>")
        else:
            prov = "landed by an earlier import"
        rows += tt.state_row(s["name"],
                             f"{s['payment_terms'] or 'no payment terms yet'} · {prov}")
    listing = tt.block(
        "p601 · suppliers on the books",
        rows or tt.state_row("none yet", "the form below lands the first one"),
        f"{len(sup_rows)} suppliers · {po_count} purchase orders — each row"
        f" says where it came from")
    pending = [r for r in ledger.pending_queue(conn)
               if r["proposal"].get("method") == "record_supplier"]
    notes = ""
    if submitted:
        notes += (f"<div class='card'><strong>parked:</strong> your entry for "
                  f"{html_escape(submitted)} waits for your approval — "
                  f"<a href='/approvals'>decide it in decisions</a>.</div>")
    if error:
        notes += (f"<div class='card'><strong>not sent:</strong> {error} — "
                  f"your typing is kept below.</div>")
    if pending and not submitted:
        notes += (f"<p class='muted'><a href='/approvals'>{len(pending)} supplier "
                  f"entr{'y' if len(pending) == 1 else 'ies'} waiting on your call in "
                  f"decisions</a></p>")
    form = f"""<div class='card'><strong>enter a supplier</strong>
<p class='muted'>what you type parks for your approval — nothing lands until you
say so in decisions. costs are in fils — 100 fils to the dirham, so AED 25.50
is 2550. an existing supplier name updates that supplier's terms.</p>
<form method='post' action='/suppliers/submit'>
 supplier name <input name='name' required size='28' value='{v["name"]}'> ·
 payment terms <input name='payment_terms' size='18' placeholder='e.g. net 30'
  value='{v["payment_terms"]}'>
 <div style='margin-top:.5rem'><strong>purchase order</strong> <span class='muted'>(optional
 — leave the id empty to enter the supplier alone. one line per entry: send the
 same po id again to add its next line; nothing already approved is ever
 replaced.)</span><br>
 po id <input name='po_id' size='14' value='{v["po_id"]}'> ·
 date <input name='po_date' size='11' placeholder='YYYY-MM-DD'
  value='{v["po_date"]}'> <span class='muted'>(leave blank = today)</span> ·
 qty <input name='qty' size='5' value='{v["qty"]}'> ·
 unit cost (fils) <input name='unit_cost' size='8' value='{v["unit_cost"]}'> ·
 variant <input name='variant_id' size='14' value='{v["variant_id"]}'
  placeholder='optional — a product variant id, to track cost per item'></div>
 <div style='margin-top:.5rem'>why <input name='why' size='40' required
  value='{v["why"]}'
  placeholder='where this came from — an invoice, a contract, a call'>
 <button class='run'>submit for approval</button></div>
</form></div>"""
    return ("<p><a href='/economics'>&larr; the money</a></p>"
            + listing + notes + form)


@app.get("/suppliers", response_class=HTMLResponse)
def suppliers_view(request: Request, conn=Depends(_db)):
    _guard(request, conn)
    ledger.ensure_schema(conn)
    submitted = request.query_params.get("submitted")
    return _page("suppliers", _suppliers_page(conn, submitted=submitted),
                 signoff_line="hand-entered facts wait for your approval —"
                              " then the money page can cite them")


@app.post("/suppliers/submit", response_class=HTMLResponse)
async def suppliers_submit(request: Request, conn=Depends(_db)):
    _guard(request, conn)
    ledger.ensure_schema(conn)
    try:
        form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
    except Exception:
        form = {}

    def refuse(msg: str, code: int = 400):
        return HTMLResponse(
            _page("suppliers", _suppliers_page(conn, error=msg, vals=form),
                  signoff_line="nothing was sent — fix the line and try again"),
            status_code=code)

    name = (form.get("name") or "").strip()
    why = (form.get("why") or "").strip()
    if not name:
        return refuse("a supplier carries a name")
    if not why:
        return refuse("never silent — say where this came from")
    args: dict = {"supplier": {"name": name,
                               "payment_terms": (form.get("payment_terms") or "").strip() or None},
                  "source": "operator:web-form"}
    known = bool(conn.execute("SELECT 1 FROM suppliers WHERE name = ?", (name,)).fetchone()
                 ) if _table_exists(conn, "suppliers") else False
    po_id = (form.get("po_id") or "").strip()
    po_note = ""
    if po_id:
        try:
            qty = int(form.get("qty") or "")
            cost = int(form.get("unit_cost") or "")
        except ValueError:
            return refuse("a purchase order carries qty and unit cost as whole"
                          " numbers (cost in fils — AED 25.50 is 2550)")
        po_date = (form.get("po_date") or "").strip()
        if po_date:
            from datetime import datetime as _dt
            try:  # strictly YYYY-MM-DD — anything else (dashless, week
                # dates) would land raw and misplace in the period
                # filters' string compares
                _dt.strptime(po_date, "%Y-%m-%d")
            except ValueError:
                return refuse("the date reads YYYY-MM-DD (leave it blank for today)")
        line = {"qty": qty, "unit_cost_minor": cost}
        if (form.get("variant_id") or "").strip():
            line["variant_id"] = form["variant_id"].strip()
        args["purchase_order"] = {"id": po_id, "created_at": po_date or None,
                                  "lines": [line]}
        po_note = (f" + po {po_id}: {qty} at {cost} fils"
                   f" ({cost / 100:,.2f} AED) each")
    verdict = gate.submit(conn, {
        "agent": "operator-web", "function": "supplier-facts",
        "method": "record_supplier", "args": args,
        "declared_type": "consequential",
        "intent": (f"update supplier {name}" if known else f"new supplier {name}")
                  + po_note,
        "rationale": why,
        "provenance": {"cite": "operator:web-form"},
        "connector": "spine-local",
    })
    if verdict["decision"] != "parked":
        # a policy surprise: hand-entered money facts must park, never run
        # free — anything else is a misconfigured table, said out loud.
        return refuse(f"policy surprise — expected the entry to park, got"
                      f" {verdict['decision']}; nothing was written", code=500)
    return RedirectResponse(url=f"/suppliers?submitted={quote(name)}", status_code=303)


@app.get("/economics/scenario", response_class=HTMLResponse)
def economics_scenario(request: Request, conn=Depends(_db)):
    """E4 — a scenario is a named baseline period plus deltas, nothing else."""
    _guard(request, conn)
    from commerceos.economics import engine
    q = request.query_params
    period = q.get("period", "2025")
    try:
        sales_pct = float(q.get("sales_pct", 0) or 0)
        purchases_pct = float(q.get("purchases_pct", 0) or 0)
    except ValueError:
        return _page("money", "<p class='muted'>the changes have to be numbers.</p>")
    pnl = engine.assemble(conn, period)
    cells = pnl.get("cells", {})

    def _v(name):
        c = cells.get(name) or {}
        return c.get("value") if isinstance(c, dict) else None

    s0, p0 = _v("books_sales"), _v("books_purchases")
    if s0 is None or p0 is None:
        return _page("money", "<p class='muted'>not enough to work from — a what-if needs real sales and purchases first.</p>")
    s1 = round(s0 * (1 + sales_pct / 100))
    p1 = round(p0 * (1 + purchases_pct / 100))
    rows = [
        ("sales", s0, s1), ("purchases", p0, p1),
        ("gross spread", s0 - p0, s1 - p1),
    ]
    trs = "".join(
        f"<tr><td>{n}</td><td>{a/100:,.0f}</td><td>{b/100:,.0f}</td>"
        f"<td class='muted'>{(b-a)/100:+,.0f}</td></tr>" for n, a, b in rows)
    margin0 = (s0 - p0) / s0 * 100 if s0 else 0
    margin1 = (s1 - p1) / s1 * 100 if s1 else 0
    body = (f"<div class='card'><strong>scenario over {period}</strong> "
            f"<span class='muted'>(sales {sales_pct:+.1f}%, purchases {purchases_pct:+.1f}%)</span>"
            f"<table><tr><th>line</th><th>now (AED)</th><th>what-if (AED)</th><th>change</th></tr>{trs}</table>"
            f"<div class='muted'>margin {margin0:.1f}% → {margin1:.1f}%</div>"
            f"<div class='muted'>nothing is saved — this is your real baseline with the change applied, worked out live.</div></div>")
    return _page("money", body)


# ----------------------------------------------------------- /catalog ---
# the catalog area — the first _operation_. its five views (overview, products,
# workflows, flags, drill) carry the catalog channel's own sub-nav; the top nav
# is the one job masthead. this surface READS workflows (front coverage +
# queues), lifecycle (state mix, flags, drill state), the audit health mirror,
# and the canonical record (drill claims); it WRITES nothing directly. every
# operator gesture leaves as a gate proposal and lands through the SAME
# /approvals (decisions) resolve verb — this surface invents no second approve
# path. this slice builds view 1, the OVERVIEW; the other views land next.

_REPORTS = Path(__file__).resolve().parents[2] / "reports"


def _health() -> dict:
    """read the audit's health mirror — overall score, per-dimension rates, and
    the prior-body trend. a mirror wears its as-of or says it is stale; a
    missing/unreadable file returns {} so the overview renders a named gap,
    never a blank or an invented number."""
    try:
        return json.loads((_REPORTS / "health-latest.json").read_text())
    except Exception:
        return {}


def _run_report(feature_name: str) -> dict:
    """the last recorded batch for a front, read plainly. a run writes its
    report to reports/run-<front>-latest.json (the shape run_feature returns:
    counted / failed / parked, and a per-item log carrying each verify-render).
    a missing file returns {} so the workflow view says 'no batch yet' plainly,
    never a faked receipt — verify rendered, never files-exist."""
    try:
        return json.loads((_REPORTS / f"run-{feature_name}-latest.json").read_text())
    except Exception:
        return {}


def _front_row(conn, name, feature, no: str) -> str:
    """one enrichment FRONT as a teletext index row: NAME · block-mosaic
    coverage meter + headline % · queue depth (opening to exactly the products
    carrying that gap) · a gated run affordance. a coverage-less front (delist
    is ruled per item, not a coverage %) leads with its queue instead of a
    lonely dash. every figure is live from feature.progress/queue."""
    try:
        prog = feature.progress(conn)
        depth = len(feature.queue(conn))
    except Exception:
        # never the raw error on an operator's screen (the producer's B1) —
        # plain words; the health check is where a broken part gets diagnosed
        return tt.idx_row(no, feature_label(name),
                          "<span class='muted'>can't read its numbers right now "
                          "— nothing is lost; this fix just has no data to "
                          "show yet</span>")
    rate = prog.get("rate")
    # the counters in plain words with their units named, value-first ("3 left
    # to fix") — every figure the health check reports stays on the surface.
    detail = progress_detail(name, prog)
    head = (tt.meter(rate) + "<br>") if isinstance(rate, (int, float)) else ""
    # the "need this" count agrees with the board it links to: for listing
    # text the board shows the missing-or-weak set (B4), not the draftable
    # queue, so the row counts the weak set too.
    need = prog.get("weak", depth) if name == "seo" else depth
    if name == "merchandising":
        # the queue is COLLECTIONS to create, not products with a gap — its
        # count opens to the front's own page (the real rows), never the board.
        need_href = f"/catalog/workflows/{name}"
        need_tail = f"collection{'s' if need != 1 else ''} to create"
    else:
        need_href = f"/catalog/products?feature={name}"
        need_tail = (f"product{'s' if need != 1 else ''} "
                     f"need{'s' if need == 1 else ''} this")
    stat = (f"{head}<span class='muted'>{detail} · "
            f"<a href='{need_href}'>{need:,}</a> {need_tail}</span>")
    # one label per gate class, not one label for everything (UI-truth):
    # a reversible batch fixes, a consequential one stages for the call.
    verb = {"gtin": "fix these", "classification": "fix these",
            "delist": "stage for your call",
            "verification": "queue the check",
            "merchandising": "make these",
            "seo": "write these"}.get(name, "run this")
    if depth:
        action = (f"<form method='post' action='/catalog/run/{name}' class='run-form'>"
                  f"<button class='run'>{verb} &rarr;</button></form>")
    else:  # a verb promising work that doesn't exist is a lie in a button
        action = "<span class='muted'>queue clear</span>"
    return tt.idx_row(no, feature_label(name), stat, action, row_id=f"p{no}")


def _state_block(counts: dict, total: int, products_n: int | None = None) -> str:
    """the lifecycle state mix as a P-block — one row per state, each count
    opening to the browser filtered to that state, then the all-products
    total. "all products" means the loaded universe, so it never reads 0 on
    a screen whose other numbers count real products (the producer's cold
    read); when some are not yet placed into a stage, the caption says so."""
    rows = ""
    for state in ("active", "draft", "flagged", "delisted", "archived"):
        n = counts.get(state, 0)
        rows += tt.state_row(
            state_label(state), f"<a href='/catalog/products?state={state}'>{n:,}</a>")
    universe = products_n if products_n is not None else total
    rows += tt.state_row(
        "all products", f"<a href='/catalog/products'>{universe:,}</a>", total=True)
    cap = "how many in each"
    if universe > total:
        cap = (f"how many in each · {universe - total:,} loaded product"
               f"{'s' if universe - total != 1 else ''} not placed in a stage yet")
    return tt.block("p201 · products by stage", rows, cap)


@app.get("/catalog", response_class=HTMLResponse)
def catalog_home(request: Request, conn=Depends(_db)):
    """view 1 — the OVERVIEW: 'is my catalog healthy, and what's the one thing
    that needs me?' the health score + trend lead the masthead; the one call
    awaiting a ruling wears the single amber accent; the enrichment fronts are
    teletext index rows; the lifecycle state mix is a P-block. every number
    opens to its rows; acting rides the one gate (decisions)."""
    _guard(request, conn)

    # (a) the catalog health score + trend, from the audit mirror. the mirror
    # wears its OWN as-of (not today) — it is honest only while fresh, and the
    # live fronts below have moved since the last full audit.
    h = _health()
    score = h.get("overall_score")
    prior = (h.get("prior_body") or {}).get("overall_prior")
    mdate = h.get("date") or ""
    try:
        from datetime import datetime as _dt
        mirror_asof = _dt.strptime(mdate, "%Y-%m-%d").strftime("%b %d").lower().replace(" 0", " ")
    except Exception:
        mirror_asof = mdate or _asof()
    if isinstance(score, (int, float)):
        big = (f"{score:g}<span style='font-size:var(--fs-2);"
               f"color:var(--text-faint)'>/100</span>")
        # the audit's measurement date belongs ON the figure it dates, not in
        # the page-freshness slot — a mirror reading wears when it was measured.
        sub = f"catalog health · measured {mirror_asof}"
    else:
        big = "—"
        sub = "catalog health · no health check yet"

    # the lifecycle state mix — the marquee split + the state P-block.
    try:
        counts = catalog_lifecycle.counts_by_state(conn)
    except Exception:
        counts = {s: 0 for s in ("draft", "active", "flagged", "delisted", "archived")}
    total = sum(counts.values())
    # "all products" is the loaded universe — never 0 beside live product
    # counts on the same screen (the producer's cold read)
    try:
        products_n = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    except Exception:
        products_n = total
    universe = max(total, products_n)
    split_cells = "".join(
        f"<div><b><a href='/catalog/products?state={s}'>{counts.get(s, 0):,}</a></b>"
        f"<span>{state_label(s)}</span></div>" for s in ("active", "draft", "archived"))
    split_cells += (f"<div><b><a href='/catalog/products'>{universe:,}</a></b>"
                    f"<span>all products</span></div>")
    marquee = tt.masthead("operations", big, sub,
                          split_html=f"<div class='split'>{split_cells}</div>")

    # (c) the enrichment fronts as teletext index rows, one per FEATURE.
    front_no = {"gtin": "204", "classification": "205", "delist": "206",
                "verification": "208", "seo": "209", "merchandising": "210"}
    numbered = [(front_no.get(name, "20x"), _front_row(conn, name, feat,
                                                       front_no.get(name, "20x")))
                for name, feat in catalog_workflows.FEATURES.items()]
    try:
        n_flags = len(catalog_lifecycle.review_queue(conn))
    except Exception:
        n_flags = 0
    numbered.append(("207", tt.idx_row(
        "207", "flagged products",
        f"<a href='/catalog/flags'>{n_flags}</a> need your review",
        "<a class='run' href='/catalog/flags'>review &rarr;</a>", row_id="p207")))
    # the p-numbers read in order on the page, whatever order they were built
    front_rows = "".join(row for _, row in sorted(numbered))
    fronts = tt.block("p200 · what needs work", front_rows,
                      "act on a row · or open the list")

    # (b) the ONE call needing a ruling — the single amber accent. the delist
    # front is consequential (ruled per item), so its queue is what awaits you.
    try:
        delist_depth = len(catalog_workflows.FEATURES["delist"].queue(conn))
    except Exception:
        delist_depth = 0
    # a real per-item wait already sitting in decisions — catalog-scoped
    # consequential listing drafts (B5). the single amber never says "nothing
    # needs your call" over a live wait.
    try:
        seo_waiting = catalog_workflows.FEATURES["seo"].progress(conn).get("waiting", 0)
    except Exception:
        seo_waiting = 0
    if delist_depth:
        # "queued", not "flagged" — flagged already means the review queue
        # two rows up; one word, one meaning per screen. and no pointing at
        # decisions while decisions is empty: these are feature-state until
        # the remove row stages them, and the door named is the real one.
        call = (
            f"<div class='call'>"
            f"<div class='subtle'>p206 · waiting for you</div>"
            f"<div class='big'><a href='/catalog/products?feature=delist'>{delist_depth}</a>"
            f" products are queued to remove from the store — not staged yet</div>"
            f"<div class='subtle'>nothing leaves your store until you approve — "
            f"press 'stage for your call' on the remove row (<a href='#p206'>p206"
            f"</a>) and each product then waits for your yes in decisions</div></div>")
    elif seo_waiting:
        # the one amber is shared — delist leads if both; otherwise the waiting
        # listing drafts wear it, linking to the real door (decisions).
        draft_word = "draft" if seo_waiting == 1 else "drafts"
        call = (
            f"<div class='call'>"
            f"<div class='subtle'>waiting for you</div>"
            f"<div class='big'><a href='/approvals'>{seo_waiting:,}</a> listing "
            f"{draft_word} wait{'s' if seo_waiting == 1 else ''} on you, item by item</div>"
            f"<div class='subtle'>each one quotes a checked detail, so it waits for "
            f"your yes in <a href='/approvals'>decisions</a> — nothing changes your "
            f"store until you approve</div></div>")
    else:
        call = ("<p class='muted' style='margin-top:var(--sp-4)'>"
                "nothing needs your call — the remove-from-store list is clear.</p>")

    # one slap max — only a true finished win. the gtin front is the candidate:
    # it slaps ONLY when the normalize queue is genuinely clear (fixable == 0),
    # so the boast is checkable, never mockup fiction. today it is not clear, so
    # no slap renders — loud is earned by being true.
    slap = ""
    try:
        g = catalog_workflows.GTIN.progress(conn)
        if g.get("fixable_remaining") == 0 and g.get("valid"):
            # the boast claims exactly what its own meter shows — the rows
            # that can't be repaired from the facts are named, not vanished
            # (UI-truth: the 540-unaccounted overclaim).
            rest = g.get("total", 0) - g.get("valid", 0)
            tail = (f" the other {rest:,} can't be repaired from the landed "
                    f"facts — they wait on real sources." if rest > 0 else "")
            slap = (f"<div class='win'><span class='slap'>{g['valid']:,} BARCODES VALID</span>"
                    f"<p>the fixable queue is clear — <b>0 auto-repairs left</b>, "
                    f"every one <a href='/catalog/products?feature=gtin'>open to "
                    f"see</a>.{tail}</p></div>")
    except Exception:
        slap = ""

    legend = (
        "<div class='legend'>"
        "<span><b>████</b> done</span>"
        "<span><b>underline</b> = click through to the products</span>"
        "<span>amber = the one thing that needs you</span></div>")

    # (d, right column) the state mix + the audit's OTHER dimensions + a
    # fasttext jump. the dimensions with a live enrichment front (gtin,
    # classification, delist) are shown live above; this block carries only the
    # dimensions without a front yet, so no number contradicts its twin. it is
    # a mirror — the bar wears its as-of.
    dims = h.get("dimensions") or {}

    def _dim(key, label):
        d = dims.get(key) or {}
        r = d.get("rate")
        return tt.state_row(label, f"{r:g}%" if isinstance(r, (int, float)) else "—")

    # listing text has a LIVE front now (p209) — its number is there, not here
    # in the doorless mirror (M4). only fronts not yet built stay in this block.
    health_rows = (_dim("specs_structured", "product details")
                   + _dim("images", "photos")
                   + _dim("merchandising", "tags")
                   + _dim("provenance", "sources"))

    # the standing cadence, named plainly: a guarded, call-time read of the
    # active store's rhythm config (never import-time — the store can change
    # between requests). a missing/unreadable config never takes the overview
    # down; the caption simply gains no extra sentence.
    def _cadence_plain(seconds: int) -> str:
        if seconds % 86400 == 0:
            days = seconds // 86400
            return "every day" if days == 1 else f"every {days:,} days"
        if seconds % 3600 == 0:
            hours = seconds // 3600
            return "every hour" if hours == 1 else f"every {hours:,} hours"
        minutes = max(1, seconds // 60)
        return "every minute" if minutes == 1 else f"every {minutes:,} minutes"

    cadence_line = ""
    try:
        from commerceos.rhythm import runner as _rhythm_runner
        audit_row = _rhythm_runner.job_configs(_rhythm_runner.load_config()).get("audit")
        if audit_row:
            every = _cadence_plain(_rhythm_runner.parse_cadence(audit_row["cadence"]))
            # a separate sentence — never fused onto "...front is built", or
            # the two claims read as one false run-on.
            if audit_row.get("enabled"):
                cadence_line = f". a fresh reading runs {every}."
            else:
                cadence_line = (f". a fresh reading is set for {every}, but the "
                                f"schedule isn't switched on yet — switching it "
                                f"on is yours.")
    except Exception:
        cadence_line = ""

    health_block = tt.block("p202 · other health numbers", health_rows,
                            f"measured {mirror_asof} — mirror readings; each "
                            f"opens to its products when its front is built"
                            f"{cadence_line}")

    fasttext = tt.block(
        "p299 · jump to",
        ("<div class='teletext-row' style='gap:var(--sp-3);flex-wrap:wrap'>"
         "<span class='no'>&rarr;</span><p>"
         "<a href='/catalog/products'>products</a> · "
         "<a href='/catalog/flags'>flagged</a> · "
         "<a href='/approvals'>decisions</a></p></div>"),
        "")

    # batches waiting for one glance (WF-approve) — visible where the work
    # is armed, opening to the preview; quiet chrome, the amber stays p206's
    catalog_runs.ensure_schema(conn)
    _staged = [r for r in catalog_runs.list_runs(conn, status="staged")
               if r["status"] == "staged"]
    batches = ""
    if _staged:
        brows = "".join(
            tt.state_row(feature_label(r["feature"]),
                         f"<a href='/catalog/runs/{r['id']}'>{r['live']:,} changes "
                         f"— glance and approve &rarr;</a>")
            for r in _staged)
        batches = tt.block("p203 · batches waiting for your glance", brows,
                           "one approve lands the lot · nothing lands without you")

    left = fronts + batches + call + slap + legend
    right = _state_block(counts, total, products_n=universe) + health_block + fasttext
    body = (tt.catalog_subnav("overview")
            + f"<div class='grid'><div>{left}</div><div>{right}</div></div>")
    return _page("operations", body, marquee=marquee,
                 signoff_line="every product count opens to its products · nothing changes your store until you approve")


_LANE_STAGES = ("draft", "active", "flagged", "delisted", "archived")
_LANE_NO = {"draft": "p221", "active": "p222", "flagged": "p223",
            "delisted": "p224", "archived": "p225"}
_LANE_CAP = 25   # cards rendered per lane; the rest is a "show all" count


def _board_gap_sets(conn) -> dict[str, set]:
    """which products carry each enrichment gap — precomputed ONCE per request
    as five set-based reads, never a per-product loop over every row. three
    gaps come from the workflow queues (barcodes/category/flagged); two are
    read straight from the facts (photo = no store image; details = a
    fit-critical claim not yet verified). every read is guarded, so a missing
    table yields an empty set, not a 500."""
    sets: dict[str, set] = {g: set() for g in GAP_ORDER}
    for fkey, gap in FEATURE_TO_GAP.items():
        try:
            sets[gap] = {w["product_id"]
                         for w in catalog_workflows.FEATURES[fkey].queue(conn)}
        except Exception:
            sets[gap] = set()
    # "needs listing text" means missing-or-weak, not merely draftable-now (B4):
    # a product whose listing waits per item or is held back still needs it, so
    # the gap set is the whole weak set — the honest board filter.
    if _table_exists(conn, "products"):
        try:
            sets["listing"] = {r["shopify_id"] for r in conn.execute(
                "SELECT shopify_id FROM products"
                " WHERE title IS NOT NULL AND TRIM(title) <> ''"
                "   AND (seo_title IS NULL OR TRIM(seo_title) = ''"
                "        OR seo_description IS NULL OR TRIM(seo_description) = ''"
                "        OR seo_title = title)")}
        except Exception:
            sets["listing"] = set()
    if _table_exists(conn, "products") and _table_exists(conn, "product_media"):
        try:
            sets["photo"] = {r["shopify_id"] for r in conn.execute(
                "SELECT p.shopify_id FROM products p"
                " LEFT JOIN product_media m ON m.product_id = p.shopify_id"
                " WHERE COALESCE(m.media_count, 0) = 0")}
        except Exception:
            sets["photo"] = set()
    if _table_exists(conn, "spec_claims"):
        try:
            sets["details"] = {r["product"] for r in conn.execute(
                "SELECT DISTINCT product FROM spec_claims"
                " WHERE fit_critical = 1 AND verified = 0")}
        except Exception:
            sets["details"] = set()
    return sets


def _verified_set(conn) -> set:
    """products that carry at least one verified spec claim — the 'verified'
    side of the verified/not filter. read once, guarded."""
    if not _table_exists(conn, "spec_claims"):
        return set()
    try:
        return {r["product"] for r in conn.execute(
            "SELECT DISTINCT product FROM spec_claims WHERE verified = 1")}
    except Exception:
        return set()


def _titles(conn, pids: list[str]) -> dict[str, str]:
    """plain titles for a set of product ids — from the facts first, the
    canonical record as a fallback. one guarded read per source; a product with
    no title anywhere is simply absent (its id stands in its place)."""
    out: dict[str, str] = {}
    if not pids:
        return out
    want = set(pids)
    if _table_exists(conn, "products"):
        try:
            for r in conn.execute("SELECT shopify_id, title FROM products"):
                if r["shopify_id"] in want and r["title"]:
                    out[r["shopify_id"]] = r["title"]
        except Exception:
            pass
    if _table_exists(conn, "canonical_products"):
        try:
            for r in conn.execute("SELECT shopify_id, title FROM canonical_products"):
                if r["shopify_id"] in want and r["title"] and r["shopify_id"] not in out:
                    out[r["shopify_id"]] = r["title"]
        except Exception:
            pass
    return out


@app.get("/catalog/products", response_class=HTMLResponse)
def catalog_products(request: Request, conn=Depends(_db)):
    """view 2 — the COMBINED BOARD: the stage pipeline (a lane per stage, with
    its live count and the products in it) fused with a filter/sort/search bar
    that constrains every lane at once. columns for where a product IS, chips
    for which products you mean. the filtered set is the scope a later
    select->run slice will target; today a card links to the drill.

    efficient over a full catalog: a handful of set-based reads precompute the
    gap membership + lifecycle map ONCE, each lane renders at most _LANE_CAP
    cards (the rest a 'show all' count) — never every card in every lane."""
    _guard(request, conn)
    q = request.query_params

    # --- read the filter set from the url (no PII ever in the query) --------
    state = q.get("state") if q.get("state") in _LANE_STAGES else None
    # ?feature=<key> from the overview maps onto the matching board gap.
    gap = q.get("gap")
    if not gap and q.get("feature"):
        gap = FEATURE_TO_GAP.get(q.get("feature"))
    if gap not in GAP_LABELS:
        gap = None
    vendor = (q.get("vendor") or "").strip() or None
    category = (q.get("category") or "").strip() or None
    verified = q.get("verified") if q.get("verified") in ("yes", "no") else None
    sort = q.get("sort") if q.get("sort") in ("health", "changed", "vendor") else "health"
    search = (q.get("q") or "").strip()
    # the board's second density (UI-polish): a flat teletext table instead of
    # the stage lanes. cards is the unmarked default — it never joins the url.
    density = "table" if q.get("density") == "table" else None

    # the canonical filter set — every composed link/form carries exactly these,
    # so the active filter always lives in the url and nothing stray leaks in.
    current = {"state": state, "gap": gap, "vendor": vendor, "category": category,
               "verified": verified, "sort": sort, "q": search, "density": density}

    def compose(**overrides) -> str:
        merged = dict(current)
        merged.update(overrides)
        # a default sort need not clutter the url
        if merged.get("sort") == "health":
            merged["sort"] = None
        qs = urlencode({k: v for k, v in merged.items() if v})
        return "/catalog/products" + (f"?{qs}" if qs else "")

    has_lc = _table_exists(conn, "product_lifecycle")
    counts = (catalog_lifecycle.counts_by_state(conn) if has_lc
              else {s: 0 for s in _LANE_STAGES})

    # --- precompute once: gap membership, lifecycle map, verified set --------
    gap_sets = _board_gap_sets(conn)
    verified_set = _verified_set(conn)

    lc: dict[str, tuple] = {}   # pid -> (state, updated_at)
    if has_lc:
        for r in conn.execute("SELECT product_id, state, updated_at FROM product_lifecycle"):
            lc[r["product_id"]] = (r["state"], r["updated_at"] or "")

    # the universe: every product the facts landed + every product placed in the
    # lifecycle (either may exist without the other).
    meta: dict[str, dict] = {}
    if _table_exists(conn, "products"):
        for r in conn.execute("SELECT shopify_id, title, handle, vendor FROM products"):
            meta[r["shopify_id"]] = {"title": r["title"], "handle": r["handle"],
                                     "vendor": r["vendor"] or "", "category": None}
    if _table_exists(conn, "canonical_products"):
        try:
            for r in conn.execute("SELECT shopify_id, category FROM canonical_products"):
                if r["shopify_id"] in meta:
                    meta[r["shopify_id"]]["category"] = r["category"]
                else:
                    meta[r["shopify_id"]] = {"title": None, "handle": None,
                                             "vendor": "", "category": r["category"]}
        except Exception:
            pass
    for pid in lc:
        meta.setdefault(pid, {"title": None, "handle": None, "vendor": "", "category": None})

    # --- build the rows, apply the composed filters --------------------------
    prods = []
    for pid, m in meta.items():
        st, updated = lc.get(pid, (None, ""))
        gaps = [g for g in GAP_ORDER if pid in gap_sets[g]]
        if state and st != state:
            continue
        if gap and pid not in gap_sets[gap]:
            continue
        if vendor and m["vendor"] != vendor:
            continue
        if category and (m["category"] or "") != category:
            continue
        if verified == "yes" and pid not in verified_set:
            continue
        if verified == "no" and pid in verified_set:
            continue
        if search:
            hay = f"{m['title'] or ''} {m['handle'] or ''}".lower()
            if search.lower() not in hay:
                continue
        prods.append({"pid": pid, "state": st, "updated": updated,
                      "title": m["title"], "handle": m["handle"],
                      "vendor": m["vendor"], "category": m["category"], "gaps": gaps})

    # --- sort (worst health first is the default) ----------------------------
    if sort == "changed":
        prods.sort(key=lambda p: p["updated"], reverse=True)
    elif sort == "vendor":
        prods.sort(key=lambda p: ((p["vendor"] or "~").lower(), (p["title"] or p["pid"]).lower()))
    else:  # health — most gaps first, then title
        prods.sort(key=lambda p: (-len(p["gaps"]), (p["title"] or p["pid"]).lower()))

    def _n_products(n: int) -> str:
        return f"{n:,} product" if n == 1 else f"{n:,} products"

    # --- the filter / sort / search bar --------------------------------------
    tab_defs = [
        ("needs review", "p210", compose(gap="flagged", state=None, sort="health", verified=None),
         gap == "flagged"),
        ("worst health", "p211", compose(gap=None, state=None, sort="health", verified=None),
         gap is None and sort == "health" and not (state or vendor or category or verified or search)),
        ("recently changed", "p212", compose(gap=None, state=None, sort="changed", verified=None),
         sort == "changed"),
    ]
    tabs = "".join(
        f"<a class='tab{' here' if on else ''}' href='{href}'>"
        f"<span class='p'>{no}</span>{label}</a>"
        for label, no, href, on in tab_defs)

    gap_chips = "".join(
        tt.chip(gap_label(g), href=compose(gap=(None if gap == g else g)),
                active=(gap == g), tone=("flag" if g == "flagged" else "gap"))
        for g in GAP_ORDER)
    ver_chips = (
        tt.chip("verified", href=compose(verified=(None if verified == "yes" else "yes")),
                active=(verified == "yes"))
        + tt.chip("not verified yet", href=compose(verified=(None if verified == "no" else "no")),
                  active=(verified == "no")))
    sort_chips = "".join(
        tt.chip(lbl, href=compose(sort=key), active=(sort == key))
        for key, lbl in (("health", "worst health first"),
                         ("changed", "recently changed"), ("vendor", "vendor")))
    # the board's second density: a compact card per lane, or one flat table.
    # plain screen words only — "cards" / "table"; never the spec term itself.
    view_chips = (
        tt.chip("cards", href=compose(density=None), active=(density is None))
        + tt.chip("table", href=compose(density="table"), active=(density == "table")))

    vendors = []
    if _table_exists(conn, "products"):
        try:
            vendors = [r["vendor"] for r in conn.execute(
                "SELECT DISTINCT vendor FROM products WHERE vendor IS NOT NULL"
                " AND vendor <> '' ORDER BY vendor")]
        except Exception:
            vendors = []
    cats = []
    if _table_exists(conn, "canonical_products"):
        try:
            cats = [r["category"] for r in conn.execute(
                "SELECT DISTINCT category FROM canonical_products WHERE category IS NOT NULL"
                " AND category <> '' ORDER BY category")]
        except Exception:
            cats = []

    def _opts(values, chosen):
        out = ["<option value=''>any</option>"]
        for v in values:
            sel = " selected" if v == chosen else ""
            out.append(f"<option{sel}>{v}</option>")
        return "".join(out)

    # search + vendor + category ride a GET form; the chip selections above ride
    # as hidden fields so submitting the form composes, never resets, the filter.
    hidden = "".join(
        f"<input type='hidden' name='{k}' value='{v}'>"
        for k, v in (("state", state), ("gap", gap), ("verified", verified),
                     ("sort", sort if sort != "health" else ""), ("density", density))
        if v)
    search_form = (
        f"<form class='fb-search' method='get' action='/catalog/products'>{hidden}"
        f"<span class='fb-label'>search</span>"
        f"<input type='text' name='q' value='{search}' placeholder='title or handle' size='16'>"
        f"<span class='fb-label'>vendor</span>"
        f"<select name='vendor'>{_opts(vendors, vendor)}</select>"
        f"<span class='fb-label'>category</span>"
        f"<select name='category'>{_opts(cats, category)}</select>"
        f"<button class='btn' type='submit'>apply</button></form>")

    active_bits = []
    if state:
        active_bits.append(f"stage: {state_label(state)}")
    if gap:
        active_bits.append(gap_label(gap))
    if vendor:
        active_bits.append(f"vendor: {vendor}")
    if category:
        active_bits.append(f"category: {category}")
    if verified:
        active_bits.append("verified" if verified == "yes" else "not verified yet")
    if search:
        active_bits.append(f"'{search}'")
    active_line = ""
    if active_bits:
        active_line = (f"<div class='fb-row'><span class='fb-label'>showing</span>"
                       f"<span class='muted'>{_n_products(len(prods))} · "
                       f"{' · '.join(active_bits)}</span> "
                       f"{tt.chip('clear all', href='/catalog/products')}</div>")

    filterbar = tt.block(
        "p220 · filter · sort · search",
        (f"<div class='fb-row'><span class='fb-label'>gap</span>{gap_chips}</div>"
         f"<div class='fb-row'><span class='fb-label'>verified</span>{ver_chips}</div>"
         f"<div class='fb-row'><span class='fb-label'>sort</span>{sort_chips}</div>"
         f"<div class='fb-row'><span class='fb-label'>view</span>{view_chips}</div>"
         f"<div class='fb-row'>{search_form}</div>"
         f"{active_line}"),
        # the table density has no lanes to constrain — word its own truth.
        "narrows the table" if density == "table" else "constrains every lane at once")

    _TABLE_CAP = 100   # rows rendered in the table density; the /record precedent's cap

    if density == "table":
        # --- the table density: one flat teletext data table, no lanes -------
        # the spec names a lifecycle-state COLUMN here — with one flat table
        # that column is what replaces the lanes (a lane layout would make it
        # redundant), so this is the "full row" the spec deferred, read as ONE
        # table, not stacked full-width lanes.
        shown = prods[:_TABLE_CAP]
        rows_html = "".join(
            f"<tr><td><a href='/catalog/products/{p['pid']}'>{p['title'] or p['pid']}</a>"
            + (f"<br><span class='muted'>@{p['handle']}</span>" if p["handle"] else "")
            + f"</td>"
            f"<td>{p['vendor'] or '—'}</td>"
            f"<td>{p['category'] or '—'}</td>"
            f"<td>{state_label(p['state'])}</td>"
            f"<td><span class='chips'>"
            + "".join(tt.chip(gap_label(g), tone=("flag" if g == "flagged" else "gap"))
                      for g in p["gaps"]) + "</span></td>"
            f"<td class='muted'>{when_plain(p['updated']) if p['updated'] else '—'}</td></tr>"
            for p in shown)
        capped = len(prods) > len(shown)
        cap_line = ""
        if capped:
            # the honesty cap line (the /record precedent's shape): name the
            # window, never claim every row is one row here when it isn't.
            cap_line = (f"<p class='muted'>showing the first {len(shown):,} of "
                        f"{len(prods):,} products — filter to narrow.</p>")
        if shown:
            block_sub = (f"showing {len(shown):,} of {len(prods):,} — filter to narrow"
                        if capped else f"{_n_products(len(prods))}, one row each")
            table_body = (
                cap_line
                + tt.block(
                    "p227 · products",
                    (f"<table class='board-table'><tr><th>product</th><th>vendor</th>"
                     f"<th>category</th><th>state</th><th>gaps</th><th>last change</th></tr>"
                     f"{rows_html}</table>"),
                    block_sub))
        else:
            table_body = ("<p class='muted'>no products match this filter — "
                          f"{tt.chip('clear all', href='/catalog/products')}</p>")
        board_html = table_body
        intro = ("<p class='muted'>every product, in one table. filter, sort, or search "
                 "to narrow it — then open a row for its details. "
                 "nothing here changes your store.</p>")
    else:
        # --- the board: a lane per stage, capped, the filtered set fills them -
        lanes_out = (_LANE_STAGES + (None,) if any(p["state"] not in _LANE_STAGES for p in prods)
                     else _LANE_STAGES)
        lanes_html = ""
        for stage in lanes_out:
            in_lane = [p for p in prods if p["state"] == stage]
            if stage is None and not in_lane:
                continue
            label = state_label(stage) if stage else "no stage yet"
            page_no = _LANE_NO.get(stage, "p226")
            cards = "".join(
                tt.pcard(
                    f"/catalog/products/{p['pid']}",
                    p["title"] or p["pid"],
                    " · ".join(x for x in (
                        (f"@{p['handle']}" if p["handle"] else None),
                        (p["vendor"] or None),
                        (p["category"] or None)) if x) or "—",
                    "".join(tt.chip(gap_label(g), tone=("flag" if g == "flagged" else "gap"))
                            for g in p["gaps"]))
                for p in in_lane[:_LANE_CAP])
            more = ""
            if len(in_lane) > _LANE_CAP:
                more = (f"<div class='lane-more'><a href='{compose(state=stage)}'>"
                        f"show all {len(in_lane):,} &rarr;</a></div>")
            lanes_html += tt.board_lane(page_no, label, len(in_lane), cards, more)
        board_html = tt.board(lanes_html)
        intro = ("<p class='muted'>every product, laid across its stage. filter, sort, or "
                 "search to narrow every lane at once — then open a card for its details. "
                 "nothing here changes your store.</p>")

    # B4: never silently show zero — when loaded products sit in no stage yet,
    # say so plainly instead of a lane that reads empty. count the SHOWN set
    # (the filtered products with no stage) so the banner never contradicts an
    # active filter's own count.
    unplaced = sum(1 for p in prods if p["state"] is None)
    filtered = bool(state or gap or vendor or category or verified or search)
    banner = ""
    if unplaced:
        where = ("the ones matching your filter show" if filtered else "they show")
        stage_word = ("with the plain state &ldquo;no stage yet&rdquo;" if density == "table"
                      else "under &ldquo;no stage yet&rdquo; below")
        banner = (f"<div class='card'><span class='muted'>{unplaced:,} loaded "
                  f"product{'s' if unplaced != 1 else ''}, not yet placed in a "
                  f"stage — {where} {stage_word}.</span></div>")
    body = (tt.catalog_subnav("products")
            + f"<div class='tabs'>{tabs}</div>"
            + f"<div class='filterbar'>{filterbar}</div>"
            + intro + banner
            + board_html)

    total = sum(counts.values())
    universe = max(total, len(meta))   # the loaded universe — never 0 beside cards
    split_cells = "".join(
        f"<div><b><a href='/catalog/products?state={s}'>{counts.get(s, 0):,}</a></b>"
        f"<span>{state_label(s)}</span></div>" for s in ("active", "draft", "flagged"))
    split_cells += (f"<div><b><a href='/catalog/products'>{universe:,}</a></b>"
                    f"<span>all products</span></div>")
    marquee = tt.masthead(
        "operations", f"{universe:,}", "products · where every one of them is",
        split_html=f"<div class='split'>{split_cells}</div>", as_of=_asof())

    return _page("operations", body, marquee=marquee,
                 signoff_line="columns for where a product is · chips for which you mean · "
                              "nothing changes your store until you approve")


_WF_NO = {"gtin": "231", "classification": "232", "delist": "233", "verification": "234",
          "seo": "235", "merchandising": "236"}


@app.get("/catalog/workflows", response_class=HTMLResponse)
def catalog_workflows_index(request: Request, conn=Depends(_db)):
    """view 3 index — one working page per enrichment front. each front leads
    with its plain name, shows its coverage now (block-mosaic meter) and how
    many products still need it, and opens to its own run-and-watch page. every
    figure is live from feature.progress/queue; every number opens to its rows."""
    _guard(request, conn)
    rows = ""
    for name, feat in catalog_workflows.FEATURES.items():
        no = _WF_NO.get(name, "23x")
        try:
            prog = feat.progress(conn)
            depth = len(feat.queue(conn))
        except Exception as e:
            rows += tt.idx_row(no, feature_label(name),
                               f"<span class='muted'>no data yet ({str(e)[:50]})</span>")
            continue
        rate = prog.get("rate")
        head = (tt.meter(rate) + "<br>") if isinstance(rate, (int, float)) else ""
        stat = (f"{head}<span class='muted'>"
                f"<a href='/catalog/workflows/{name}'>{depth:,}</a> products still need this — "
                f"{front_blurb(name)}</span>")
        action = f"<a class='run' href='/catalog/workflows/{name}'>open &rarr;</a>"
        rows += tt.idx_row(no, feature_label(name), stat, action, row_id=f"wf-{name}")
    block = tt.block("p230 · the fixes", rows,
                     "coverage now · how many still need it")
    intro = ("<p class='muted'>each fix does one kind of work, run as a batch. open one to "
             "see its coverage, run a batch, and watch what showed up live. nothing here changes "
             "your store until you approve.</p>")
    body = tt.catalog_subnav("workflows") + intro + block
    marquee = tt.masthead("operations", f"{len(catalog_workflows.FEATURES)}",
                          "the fixes · pick one to run and watch", as_of=_asof())
    return _page("operations", body, marquee=marquee,
                 signoff_line="each fix opens to its own run-and-watch page · "
                              "nothing changes your store until you approve")


@app.get("/catalog/workflows/{feature}", response_class=HTMLResponse)
def catalog_workflow(feature: str, request: Request, conn=Depends(_db)):
    """view 3 page — run and watch ONE enrichment front. coverage now + how many
    left; the queue (opening to the products board filtered to this gap); the
    last batch read plainly with its verify-render receipts; the front's setup
    in plain words; and a run control that rides the EXISTING gated run path —
    it stages a batch into decisions, it never approves here."""
    _guard(request, conn)
    if feature not in catalog_workflows.FEATURES:
        from fastapi.responses import HTMLResponse as _HR
        return _HR(_page("operations", tt.catalog_subnav("workflows")
                         + "<p class='muted'>no such fix — pick one from "
                           "<a href='/catalog/workflows'>the fixes</a>.</p>"),
                   status_code=404)
    feat = catalog_workflows.FEATURES[feature]
    no = _WF_NO.get(feature, "23x")
    try:
        prog = feat.progress(conn)
        depth = len(feat.queue(conn))
    except Exception as e:
        prog, depth = {}, 0
        _err = str(e)[:80]
    rate = prog.get("rate")

    # (a) coverage now — the meter + how many still need it, opening to the
    # board. the counters name their units (details vs products).
    detail = progress_detail(feature, prog)
    meter_html = (tt.meter(rate) + "<br>") if isinstance(rate, (int, float)) else ""
    # "still to do" must count exactly what its own link opens: for listing
    # text the board shows the missing-or-weak set (not the draftable queue —
    # "ready to draft" already lives on the meter line above). a count opens
    # to exactly its rows.
    still = prog.get("weak", depth) if feature == "seo" else depth
    if feature == "merchandising":
        # the queue is COLLECTIONS to create, not products — the real rows are
        # the shelves themselves, each named with the products it will gather.
        try:
            q_items = feat.queue(conn)
        except Exception:
            q_items = []
        listed = "".join(
            tt.state_row(html_escape(it["title"]),
                         html_escape(it["display"].split(" — ", 1)[-1]))
            for it in q_items[:feat.batch_default])
        cover_rows = (
            f"<div class='teletext-row'><p>{meter_html}"
            f"<span class='muted'>{detail}</span></p></div>"
            + tt.state_row("still to create",
                           f"{still:,} collection{'s' if still != 1 else ''}")
            + listed)
        # the header + cap wear the lag the detail already states — a shopper
        # coverage figure is only true as of the last sync, never "now".
        cover = tt.block(f"p{no} · coverage, as of the last sync", cover_rows,
                         "products already in a collection · the collections still to create")
    else:
        cover_rows = (
            f"<div class='teletext-row'><p>{meter_html}"
            f"<span class='muted'>{detail}</span></p></div>"
            + tt.state_row("still to do",
                           f"<a href='/catalog/products?feature={feature}'>{still:,}</a> products")
            + tt.state_row("the queue",
                           f"<a href='/catalog/products?feature={feature}'>open the list &rarr;</a>"))
        cover = tt.block(f"p{no} · coverage now", cover_rows, "how full · how many left")

    # (b) the run control — the EXISTING gated path (POST /catalog/run/<front>).
    # the button says its batch size (the queue, capped at the feature's batch
    # default), and "decisions" is a real link, not just a word.
    batch_n = min(depth, feat.batch_default)
    batch_label = (f"start a batch of {batch_n:,} &rarr;" if batch_n
                   else "start a batch — nothing queued right now &rarr;")
    # this front's own waiting batch, if one holds — the page is never blind
    # to it, and the arm control steps aside for the open door
    catalog_runs.ensure_schema(conn)
    _waiting = [r for r in catalog_runs.list_runs(conn, status="staged")
                if r["status"] == "staged" and r["feature"] == feature]
    if _waiting:
        w = _waiting[0]
        run_block = tt.block(
            f"p{no}.1 · run a batch",
            (f"<div class='teletext-row'><p>a batch of {w['live']:,} change"
             f"{'s' if w['live'] != 1 else ''} is already waiting for your "
             f"glance — <a href='/catalog/runs/{w['id']}'>open it and "
             f"approve or decline &rarr;</a></p></div>"
             f"<div class='teletext-row'><p class='muted'>one batch waits at a "
             f"time: rule on the waiting one and you can arm the next.</p></div>"),
            "a batch is waiting · rule on it first")
    else:
        if feat.declared_type == "reversible":
            stage_line = ("a batch holds as one preview — every change in plain "
                          "words, one glance-approve lands the lot. nothing "
                          "changes your store until you approve.")
            stage_cap = "holds for your glance · never approves here"
        else:
            stage_line = ("a batch stages into <a href='/approvals'>decisions</a> — "
                          "you rule each item there before anything changes your "
                          "store.")
            stage_cap = "stages into decisions · never approves here"
        # a run affordance promising work that doesn't exist is a lie in a
        # button — with nothing queued it renders inert (a span, never a POST).
        if batch_n:
            control = (f"<form method='post' action='/catalog/run/{feature}' class='run-form'>"
                       f"<button class='run run--act'>{batch_label}</button></form>")
        else:
            control = ("<div class='teletext-row'><span class='muted'>nothing is "
                       "queued to run right now — every draftable listing is done "
                       "or waiting on you.</span></div>")
        run_block = tt.block(
            f"p{no}.1 · run a batch",
            (f"<div class='teletext-row'><p class='muted'>{gate_class_plain(feat.declared_type)}</p></div>"
             + control
             + f"<div class='teletext-row'><p class='muted'>{stage_line}</p></div>"),
            stage_cap)

    # (c) the last batch, read plainly + the verify-render receipts. no faked
    # receipt: a missing report says so, verify rendered never files-exist.
    # the latest batch that ran THROUGH THIS SURFACE (WF-approve) is the truth
    # (B3) — read the run object; a CLI apply report is the fallback for fronts
    # driven from the command line.
    latest_run = next((r for r in catalog_runs.list_runs(conn)
                       if r["feature"] == feature
                       and r["status"] in ("done", "rejected", "lapsed")), None)
    rep = _run_report(feature)
    if latest_run:
        o = latest_run.get("outcome") or {}
        link = f"<a href='/catalog/runs/{latest_run['id']}'>open the batch &rarr;</a>"
        if latest_run["status"] == "done":
            summary = (tt.state_row("showed up live", f"{o.get('counted', 0):,}")
                       + tt.state_row("didn't show live",
                                      f"{o.get('failed', 0) + o.get('errored', 0):,}")
                       + tt.state_row("was in this batch", f"{latest_run['batch']:,}"))
            line = (f"<div class='teletext-row'><p class='muted'>the last batch "
                    f"landed and read back live — {link}</p></div>")
            cap = "how many showed up live · open for every change"
        elif latest_run["status"] == "rejected":
            summary = tt.state_row("was in this batch", f"{latest_run['batch']:,}")
            line = (f"<div class='teletext-row'><p class='muted'>you declined the "
                    f"last batch — nothing ran. {link}</p></div>")
            cap = "declined · nothing ran"
        else:  # lapsed
            summary = tt.state_row("was in this batch", f"{latest_run['batch']:,}")
            line = (f"<div class='teletext-row'><p class='muted'>the last batch "
                    f"lapsed — still wanted means a fresh batch with current "
                    f"numbers. {link}</p></div>")
            cap = "lapsed · nothing ran late"
        last = tt.block(f"p{no}.2 · the last batch", summary + line, cap)
    elif rep:
        counted = rep.get("counted", 0)
        still = rep.get("failed", 0) + rep.get("errored", 0) + rep.get("parked", 0)
        summary = (
            tt.state_row("fixed and showing live", f"{counted:,}")
            + tt.state_row("still to check", f"{still:,}")
            + tt.state_row("was in this batch", f"{rep.get('batch', 0):,}"))
        receipts = ""
        for e in (rep.get("log") or [])[:20]:
            state = e.get("state", "")
            if state == "counted":
                verdict, tone = "showed up live? yes", "ok"
            elif state.startswith("parked"):
                verdict, tone = "waiting for your approval", "warn"
            elif state.startswith("held"):
                verdict, tone = "waiting for your glance", "warn"
            elif state.startswith("errored"):
                verdict, tone = "didn't run", "warn"
            elif "not verified" in state or "not counted" in state:
                verdict, tone = "showed up live? no", "warn"
            else:
                verdict, tone = "staged only", ""
            receipts += tt.receipt(verdict, e.get("item", ""), tone=tone)
        more = ""
        if len(rep.get("log") or []) > 20:
            more = (f"<div class='teletext-row'><span class='muted'>"
                    f"… and {len(rep['log']) - 20} more</span></div>")
        last = tt.block(f"p{no}.2 · the last batch",
                        summary + receipts + more,
                        "how many fixed · showed up live?")
    else:
        # no stranded pointer: "start one above" only while the arm control
        # is actually above — with a batch waiting, point at the batch
        if _waiting:
            empty_line = ("no batch has landed through this surface yet — one is "
                          "waiting for your glance above. rule on it and its "
                          "receipts land right here.")
        else:
            empty_line = ("no batch has run through this surface yet. start one "
                          "above — you'll see every fix and whether it showed up "
                          "live, right here.")
        last = tt.block(
            f"p{no}.2 · the last batch",
            f"<div class='teletext-row'><p class='muted'>{empty_line}</p></div>",
            "nothing run yet")

    # (c2) the evidence in hand — verification only. "N products with evidence
    # in hand" opens HERE (never a dead end): per product, each found claim's
    # detail in plain words, the value the maker states, the quote, and the
    # link — straight from the findings file the queue reads.
    evidence = ""
    if feature == "verification":
        ev = catalog_workflows.verification_evidence(conn)
        if ev:
            cards = ""
            for p in ev:
                crows = ""
                for c in p["claims"]:
                    found = str(c.get("found_value") or "")
                    if c.get("found_unit"):
                        found += f" {c['found_unit']}"
                    verdict = ("matches what we claim" if c["verdict"] == "agree"
                               else "conflicts with what we claim")
                    quote = (f"&ldquo;{c['quote']}&rdquo;" if c.get("quote")
                             else "no quote kept")
                    link = (f"<a href='{c['source_url']}'>the maker's page &rarr;</a>"
                            if c.get("source_url") else "no link kept")
                    crows += (f"<tr><td>{detail_label(c['field'])}</td><td>{found}</td>"
                              f"<td>{verdict}</td><td class='muted'>{quote}</td>"
                              f"<td>{link}</td></tr>")
                cards += (
                    f"<div class='card'><strong><a href='/catalog/products/"
                    f"{p['product_id']}'>{p['title'] or p['handle']}</a></strong>"
                    f"<table><tr><th>detail</th><th>the maker says</th><th>agrees?</th>"
                    f"<th>their words</th><th>the page</th></tr>{crows}</table></div>")
            evidence = tt.block(
                f"p{no}.4 · the evidence in hand",
                cards, "each detail · the quote · the maker's page",
                block_id="evidence")
        else:
            evidence = tt.block(
                f"p{no}.4 · the evidence in hand",
                "<div class='teletext-row'><p class='muted'>no evidence gathered "
                "yet — when the checking work lands its findings, every quote and "
                "link shows up here before anything is proposed.</p></div>",
                "nothing gathered yet", block_id="evidence")

    # (d) the front's setup, in plain words — where the data comes from, whether
    # it needs your approval.
    setup = tt.block(
        f"p{no}.3 · how this fix works",
        (tt.state_row("what it fixes", front_blurb(feature))
         + tt.state_row("where the data comes from", source_plain(feature))
         + tt.state_row("does it need your approval", gate_class_plain(feat.declared_type))),
        "the setup, in plain words")

    # (c3) held back — the drafts the wall turned away, each product by name
    # with one plain reason (M2). "held back" on the coverage line opens here.
    held_block = ""
    if feature == "seo":
        from commerceos.fleet import content as _content
        try:
            refused = _content.seo_held_back(conn)
        except Exception:
            refused = []
        if refused:
            names = _titles(conn, [x["product"] for x in refused])
            rows = "".join(
                tt.state_row(
                    f"<a href='/catalog/products/{x['product']}'>"
                    f"{html_escape(names.get(x['product']) or x.get('name') or x['product'])}</a>",
                    html_escape(x["reason"]))
                for x in refused)
            held_block = ("<a id='held-back'></a>" + tt.block(
                f"p{no}.4 · held back", rows,
                "the facts can't back these yet · nothing was written"))

    # (e) merchandising only — the SEPARATE nav-placement flow. placing the
    # collections into your store menu is a consequential change (a menu write
    # replaces the whole nav tree), so it never rides the reversible batch above:
    # it stages ONE proposal into decisions and waits on you, item by item.
    nav_block = ""
    if feature == "merchandising":
        from commerceos.catalog import merchandising as _merch
        pending_nav = _merch.nav_pending(conn)
        if pending_nav:
            # one navigation change waits at a time: the control steps aside for
            # the open door (mirrors the reversible batch's one-waits pattern)
            nav_block = tt.block(
                f"p{no}.5 · put them in your store menu",
                (f"<div class='teletext-row'><p class='muted'>a navigation change is "
                 f"already waiting for your call — <a href='/approvals'>rule on it in "
                 f"decisions &rarr;</a></p></div>"
                 f"<div class='teletext-row'><p class='muted'>one navigation change "
                 f"waits at a time: rule on the waiting one and you can stage the "
                 f"next.</p></div>"),
                "a navigation change waits · rule on it first")
        else:
            prop = _merch.nav_proposal(conn)
            if prop is None:
                nav_block = tt.block(
                    f"p{no}.5 · put them in your store menu",
                    ("<div class='teletext-row'><p class='muted'>once your collections "
                     "are live and their members have synced, you can place them into "
                     "your store's main menu from here.</p></div>"),
                    "waits for live collections")
            else:
                n_items = len(prop["args"]["items"])
                nav_block = tt.block(
                    f"p{no}.5 · put them in your store menu",
                    (f"<div class='teletext-row'><p class='muted'>{_merch.NAV_WHY} "
                     f"you rule this one before your navigation moves.</p></div>"
                     f"<form method='post' action='/catalog/merchandising/nav' class='run-form'>"
                     f"<button class='run'>add {n_items} collection"
                     f"{'s' if n_items != 1 else ''} to your store menu &rarr;</button></form>"
                     f"<div class='teletext-row'><p class='muted'>this stages one change "
                     f"into <a href='/approvals'>decisions</a> — nothing in your store "
                     f"menu moves until you approve it there.</p></div>"),
                    "a navigation change · stages for your call, never lands here")

    # merchandising's coverage is a synced figure — it wears "as of the last
    # sync" everywhere it shows, never "now" and never "live from the facts"
    # (the other fronts read their coverage live; this one lags until a sync).
    cover_word = ("coverage, as of the last sync" if feature == "merchandising"
                  else "coverage now")
    if isinstance(rate, (int, float)):
        big, sub = f"{round(rate * 100, 1):g}%", f"{feature_label(feature)} · {cover_word}"
    else:
        big, sub = f"{depth:,}", f"{feature_label(feature)} · waiting for your call"
    marquee = tt.masthead("operations", big, sub, as_of=_asof())

    coverage_clause = ("collection-coverage is a synced figure, true as of the last sync"
                       if feature == "merchandising" else "coverage is live from the facts")
    body = (tt.catalog_subnav("workflows")
            + f"<p><a href='/catalog/workflows'>← the fixes</a></p>"
            + f"<p class='muted'>{front_blurb(feature)}</p>"
            + cover + run_block + nav_block + evidence + last + held_block + setup)
    return _page("operations", body, marquee=marquee,
                 signoff_line=f"{coverage_clause} · a fix counts only when it "
                              "showed up live · nothing changes your store until you approve")


@app.get("/catalog/flags", response_class=HTMLResponse)
def catalog_flags(request: Request, conn=Depends(_db)):
    """view 4 — flag review: the products the quality gate flagged, each with its
    evidence in plain words, and the ruling choices as GATED actions. keep /
    remove from store / archive each stage a proposal into decisions (the
    existing gate) and redirect there — nothing is executed or approved here,
    and this surface invents no second approve verb."""
    _guard(request, conn)
    queue = (catalog_lifecycle.review_queue(conn)
             if _table_exists(conn, "product_lifecycle") else [])
    body = tt.catalog_subnav("flags")
    if not queue:
        body += ("<p class='muted'>nothing flagged right now — no products are waiting on your "
                 "ruling. when the quality check flags one, it shows up here with its evidence.</p>")
        marquee = tt.masthead("operations", "0", "flagged · nothing waiting on you", as_of=_asof())
        return _page("operations", body, marquee=marquee,
                     signoff_line="a flag waits here until you rule on it")

    intro = ("<p class='muted'>these are the products the quality check flagged. each one waits "
             "here until you rule on it — ignore one and it just gets older, it never disappears. "
             "your ruling doesn't change the store here: it becomes a request in "
             "<a href='/approvals'>decisions</a>, and nothing moves until you approve there.</p>")

    titles = _titles(conn, [fl["product_id"] for fl in queue])

    # the batch ruling: rule the whole flagged queue as remove-from-store, staged
    # into decisions through the existing run path (one proposal per product).
    batch = tt.block(
        "p240 · rule the batch",
        (f"<div class='teletext-row'><span class='muted'>{len(queue):,} products flagged. "
         f"send them all to decisions as remove-from-store, one request per product — "
         f"you still approve each move there.</span></div>"
         f"<form method='post' action='/catalog/run/delist' class='run-form'>"
         f"<button class='run run--act'>send all {len(queue):,} to decisions &rarr;</button></form>"),
        "one glance · then rule per product below")

    cards = ""
    for fl in queue:
        pid = fl["product_id"]
        headline, reasons = read_evidence(fl["evidence"])
        why = "".join(f"<li>{r}</li>" for r in reasons) or \
            "<li class='muted'>no reason recorded</li>"
        rulings = (
            f"<form method='post' action='/catalog/rule/{pid}' class='ruling'>"
            f"<button class='run' name='ruling' value='keep'>keep · clear the flag</button> "
            f"<button class='run run--act' name='ruling' value='remove'>remove from store</button> "
            f"<button class='run' name='ruling' value='archive'>archive</button></form>")
        cards += (
            f"<div class='card flag-card'>"
            f"<strong><a href='/catalog/products/{pid}'>{titles.get(pid) or pid}</a></strong> "
            f"<span class='muted'>· {headline}</span>"
            f"<div>why it looks wrong:<ul>{why}</ul></div>"
            f"<div class='muted'>your ruling waits for your approval in "
            f"<a href='/approvals'>decisions</a> before anything changes.</div>"
            f"{rulings}</div>")

    marquee = tt.masthead("operations", f"{len(queue):,}",
                          "flagged · waiting on your ruling", as_of=_asof())
    body += intro + batch + cards
    return _page("operations", body, marquee=marquee,
                 signoff_line="each ruling routes to decisions · nothing changes your store until you approve")


def plain_reason(reason) -> str:
    """a recorded lifecycle 'why' in plain words — the detector's signal codes
    mapped to sentences, a human note kept verbatim, and NO raw code ever left
    on screen. a comma-joined reason (a detector's signal list) maps token by
    token."""
    if not reason:
        return ""
    parts = []
    for tok in str(reason).split(","):
        tok = tok.strip()
        if tok:
            parts.append(EVIDENCE_PLAIN.get(tok, tok))
    return "; ".join(parts)


@app.get("/catalog/products/{product_id:path}", response_class=HTMLResponse)
def catalog_drill(product_id: str, request: Request, conn=Depends(_db)):
    """view 5 — the per-product drill: the identity; the canonical claims each
    with its source and a plain checked / only-claimed chip; the lifecycle stage
    + full history as a plain who/when/why timeline; the gaps it still carries;
    a plain store-preview line (page = feed = structured data agree); and a
    gated act affordance that STAGES a request into decisions, never a direct
    write. plain words throughout — no field code ever left on screen."""
    _guard(request, conn)

    # --- identity — title, handle, brand, category, stage --------------------
    title = product_id
    ident = {"handle": None, "vendor": None, "category": None}
    if _table_exists(conn, "canonical_products"):
        cp = conn.execute(
            "SELECT title, handle, vendor, category FROM canonical_products"
            " WHERE shopify_id = ?", (product_id,)).fetchone()
        if cp:
            title = cp["title"] or title
            ident = {"handle": cp["handle"], "vendor": cp["vendor"], "category": cp["category"]}
    if _table_exists(conn, "products"):
        pr = conn.execute(
            "SELECT title, handle, vendor FROM products WHERE shopify_id = ?",
            (product_id,)).fetchone()
        if pr:
            title = title if title != product_id else (pr["title"] or title)
            ident["handle"] = ident["handle"] or pr["handle"]
            ident["vendor"] = ident["vendor"] or pr["vendor"]

    has_lc = _table_exists(conn, "product_lifecycle")
    st = catalog_lifecycle.state_of(conn, product_id) if has_lc else None

    id_rows = (tt.state_row("name", title)
               + tt.state_row("handle", ("@" + ident["handle"]) if ident["handle"] else "—")
               + tt.state_row("brand", ident["vendor"] or "—")
               + tt.state_row("category", ident["category"] or "not in a category yet")
               + tt.state_row("stage", state_label(st), total=True))
    identity_panel = tt.block("p250 · this product", id_rows, "who it is · where it sits")

    # --- claims + provenance — each with a plain checked / only-claimed chip --
    claims = []
    if _table_exists(conn, "spec_claims"):
        claims = conn.execute(
            "SELECT field, value, unit, source, verified, verified_on, fit_critical"
            " FROM spec_claims WHERE product = ? ORDER BY field", (product_id,)).fetchall()
    if claims:
        crows = ""
        for c in claims:
            fc = " <span class='fc-mark'>must be right</span>" if c["fit_critical"] else ""
            val = f"{c['value']}{(' ' + c['unit']) if c['unit'] else ''}"
            if c["verified"]:
                ink = tt.chip(("checked " + (c["verified_on"] or "")).strip(), tone="ok")
            else:
                ink = tt.chip("only claimed", tone="claim")
            crows += (f"<tr><td>{detail_label(c['field'])}{fc}</td><td>{val}</td>"
                      f"<td class='muted'>{source_plain(c['source'])}</td><td>{ink}</td></tr>")
        claims_panel = tt.block(
            "p251 · what we claim, and where it came from",
            f"<table><tr><th>detail</th><th>value</th><th>where from</th>"
            f"<th>checked?</th></tr>{crows}</table>",
            "each detail · its source · checked or only claimed")
    else:
        claims_panel = tt.block(
            "p251 · what we claim, and where it came from",
            "<div class='teletext-row'><p class='muted'>nothing recorded for this product yet. "
            "we record a detail only when it comes from a real, sourced fact — we never make one "
            "up.</p></div>",
            "no claim without a source")

    # --- stage + full history as a plain who/when/why timeline ---------------
    hist = catalog_lifecycle.history(conn, product_id) if has_lc else []
    if hist:
        tl = "".join(
            tt.timeline_row(
                h["ts"][:19],
                f"{state_label(h['from_state'])} → {state_label(h['to_state'])}",
                h["by"], plain_reason(h["reason"]))
            for h in hist)
    else:
        tl = "<div class='teletext-row'><span class='muted'>no history yet.</span></div>"
    history_panel = tt.block(f"p252 · stage · {state_label(st)}", tl, "who · when · why")

    # --- the gaps it still carries, as plain chips ---------------------------
    gap_sets = _board_gap_sets(conn)
    gaps = [g for g in GAP_ORDER if product_id in gap_sets[g]]
    if gaps:
        gchips = "".join(
            tt.chip(gap_label(g), tone=("flag" if g == "flagged" else "gap")) for g in gaps)
        gaps_html = f"<div class='teletext-row'>{gchips}</div>"
    else:
        gaps_html = ("<div class='teletext-row'><span class='muted'>no gaps — this product is "
                     "complete on every fix.</span></div>")
    gaps_panel = tt.block("p253 · what it still needs", gaps_html, "the gaps it carries")

    # --- store preview: do the page, the feed, and the structured data agree? -
    preview_line = ("no store preview yet — this product has no recorded details to publish. "
                    "we only publish a detail once it has a source.")
    if _table_exists(conn, "canonical_products"):
        try:
            from commerceos.catalog import emitters
            chk = emitters.check_product(conn, product_id)
            if not chk["failures"]:
                preview_line = ("the product page, the shopping feed, and the structured data all "
                                "agree — they read from this one record, so they say the same thing.")
            else:
                preview_line = (f"these surfaces disagree on {len(chk['failures'])} point"
                                + ("s" if len(chk["failures"]) != 1 else "")
                                + " — the page, the shopping feed, and the structured data don't "
                                  "yet match. run this product to bring them back in line.")
        except Exception:
            pass
    preview_panel = tt.block(
        "p254 · does the store agree?",
        f"<div class='teletext-row'><p class='muted'>{preview_line}</p></div>",
        "the page · the shopping feed · the structured data")

    # --- the gated act affordance — STAGES a request, never a direct write ----
    ruling_form = (
        f"<form method='post' action='/catalog/rule/{product_id}' class='ruling'>"
        f"<button class='run' name='ruling' value='keep'>keep as it is</button> "
        f"<button class='run run--act' name='ruling' value='remove'>remove from store</button> "
        f"<button class='run' name='ruling' value='archive'>archive</button></form>"
    ) if st else ("<div class='teletext-row'><span class='muted'>this product isn't tracked in "
                  "the lifecycle yet, so there's nothing to rule.</span></div>")
    act_panel = tt.block(
        "p255 · change this product",
        (ruling_form
         + "<div class='teletext-row'><p class='muted'>any change here is staged, never live: it "
           "becomes a request in <a href='/approvals'>decisions</a>, and only goes live — and gets "
           "checked that it actually showed up — after you approve. there's no way to skip that "
           "step. orders, checkout, theme, and stock stay in Shopify.</p></div>"),
        "stages a request · never a direct write")

    marquee = tt.masthead("operations", state_label(st), "one product · its record",
                          as_of=_asof())
    body = (tt.catalog_subnav("products")
            + f"<p><a href='/catalog/products'>← products</a></p>"
            + identity_panel + claims_panel + history_panel
            + gaps_panel + preview_panel + act_panel)
    return _page("operations", body, marquee=marquee,
                 signoff_line="what we claim · on what evidence · did it show up live · "
                              "nothing changes your store until you approve")


_RULE_STATE = {"keep": "active", "remove": "delisted", "archive": "archived"}


@app.post("/catalog/rule/{product_id:path}")
async def catalog_rule(product_id: str, request: Request, conn=Depends(_db)):
    """rule ONE flagged product — keep (clear the flag) · remove from store ·
    archive. it STAGES a gated proposal into decisions (gate.submit) and
    redirects there; it NEVER approves and NEVER writes the store. the SAME one
    write door, the SAME one resolve verb — this surface invents no second
    approve path, exactly like [run batch]. the redirect proves it."""
    _guard(request, conn)
    ledger.ensure_schema(conn)
    # read the ruling from the form body (urlencoded) or the query — no
    # python-multipart dependency, the same shape [run batch] would accept.
    ruling = request.query_params.get("ruling")
    if not ruling:
        try:
            ruling = parse_qs((await request.body()).decode()).get("ruling", [None])[0]
        except Exception:
            ruling = None
    if ruling not in _RULE_STATE:
        return JSONResponse({"error": "ruling must be keep|remove|archive"}, status_code=400)
    target = _RULE_STATE[ruling]
    gate.submit(conn, {
        "agent": "catalog-operator", "function": "catalog-enrichment",
        "method": "mutate_product_state",
        "args": {"product_id": product_id, "state": target},
        "declared_type": "consequential",
        "intent": f"{ruling} — rule a flagged product",
        "rationale": f"operator ruling from the catalog surface: {ruling}",
        "provenance": [{"source": "operator:flag-review", "fetched_at": ledger.now()}],
    })
    return RedirectResponse(url="/approvals", status_code=303)


@app.post("/catalog/run/{feature}")
def catalog_run(feature: str, request: Request, conn=Depends(_db)):
    """[run batch] — stage a run of the feature's queue through the gate.
    this handler NEVER approves: every front has an approval step (WF-approve,
    RULED — nothing auto-lands). a reversible batch HOLDS: every proposal
    parks and the batch groups into one run, previewed on its own page and
    landed by one glance-approve there. a consequential batch parks per item
    in /approvals and is ruled per item, as before. there is no second
    approve path — the redirect proves it."""
    _guard(request, conn)
    if feature not in catalog_workflows.FEATURES:
        return JSONResponse({"error": f"unknown feature {feature!r}"}, status_code=404)
    ledger.ensure_schema(conn)
    feat = catalog_workflows.FEATURES[feature]
    if feat.declared_type == "reversible":
        # one batch waits at a time per front: arming again while one waits
        # opens the waiting one instead of staging a silent duplicate
        catalog_runs.ensure_schema(conn)
        waiting = [r for r in catalog_runs.list_runs(conn, status="staged")
                   if r["status"] == "staged" and r["feature"] == feature]
        if waiting:
            return RedirectResponse(url=f"/catalog/runs/{waiting[0]['id']}",
                                    status_code=303)
        rep = catalog_workflows.run_feature(conn, feat, client=None, hold=True)
        if rep.get("run_id"):
            return RedirectResponse(url=f"/catalog/runs/{rep['run_id']}",
                                    status_code=303)
        return RedirectResponse(
            url=f"/catalog/workflows/{feature}", status_code=303)
    catalog_workflows.run_feature(conn, feat, client=None, apply=False)
    return RedirectResponse(url="/approvals", status_code=303)


@app.post("/catalog/merchandising/nav")
def catalog_merchandising_nav(request: Request, conn=Depends(_db)):
    """stage the ONE nav-placement proposal (mutate_menu) — the separate
    consequential flow. it does NOT approve: a menu write replaces the whole nav
    tree, so it parks in /approvals and waits on your call, item by item. no
    live shelves means nothing to place — a plain flash, never a broken form."""
    _guard(request, conn)
    ledger.ensure_schema(conn)
    from commerceos.catalog import merchandising as _merch
    # one navigation change waits at a time — a re-press never stages a
    # duplicate; it opens the one already waiting (the reversible lane's rule)
    if _merch.nav_pending(conn):
        return RedirectResponse(
            url="/approvals?flash=" + quote("a navigation change is already waiting "
                                            "for your call") + "&kind=refused",
            status_code=303)
    prop = _merch.nav_proposal(conn)
    if prop is None:
        return RedirectResponse(
            url="/catalog/workflows/merchandising", status_code=303)
    gate.submit(conn, prop)
    return RedirectResponse(url="/approvals", status_code=303)


def who_plain(by: str | None) -> str:
    """the approver in a person's words (the 7c, RULED: device labels). the
    desk renders as itself; a paired device renders as its owner-typed label
    ("your <label>" — the plain reading picked and pinned here). 'localhost'
    and 'paired-device' are the ledger's own former ink, from before this
    ruling landed — the append-only law means old rows still carry them, so
    they keep mapping to the words this screen always used. the label case
    returns the raw string; every caller here already wraps the result in
    html_escape before it reaches markup, so a user-typed label (possibly
    carrying '<' or '&') is escaped exactly once, at render, never stored
    escaped."""
    if by in ("localhost", "the desk"):
        return "you, at this desk"
    if by == "paired-device":
        return "you, from your paired device"
    if by:
        return f"your {by}"
    return "—"


def _who(request: Request, form: dict | None = None) -> str:
    """the same identity convention the per-item approve uses — the open
    [owner] ruling on 'by whom' rides both paths equally."""
    if form and form.get("by"):
        return form["by"]
    if request.client and request.client.host in ("127.0.0.1", "::1", "testclient"):
        return "localhost"
    return "paired-device"


def _mark_diff(old: str, new: str) -> tuple[str, str]:
    """make a small change visible at a glance: the shared head and tail stay
    quiet, the part that actually changes is bold in both values. a glance-
    approve is only honest if the glance can SEE the change (the producer's
    cold read: a one-character fix was invisible)."""
    old, new = str(old), str(new)
    i = 0
    while i < min(len(old), len(new)) and old[i] == new[i]:
        i += 1
    j = 0
    while (j < min(len(old), len(new)) - i and old[len(old) - 1 - j] == new[len(new) - 1 - j]):
        j += 1

    def mark(s: str) -> str:
        end = len(s) - j
        head, mid, tail = s[:i], s[i:end], s[end:]
        mid_html = f"<b>{html_escape(mid)}</b>" if mid else ""
        return html_escape(head) + mid_html + html_escape(tail)

    return mark(old), mark(new)


def _mark_diff_words(old: str, new: str) -> tuple[str, str]:
    """like _mark_diff, but the bold span snaps out to whole words — a listing
    change reads as words, never a mid-word highlight (the producer's polish)."""
    old, new = str(old), str(new)
    i = 0
    while i < min(len(old), len(new)) and old[i] == new[i]:
        i += 1
    j = 0
    while (j < min(len(old), len(new)) - i and old[len(old) - 1 - j] == new[len(new) - 1 - j]):
        j += 1

    def mark(s: str) -> str:
        a = i
        while a > 0 and s[a - 1] != " ":       # snap head back to the word start
            a -= 1
        b = len(s) - j
        while b < len(s) and s[b] != " ":       # snap tail out to the word end
            b += 1
        head, mid, tail = s[:a], s[a:b], s[b:]
        mid_html = f"<b>{html_escape(mid)}</b>" if mid.strip() else html_escape(mid)
        return html_escape(head) + mid_html + html_escape(tail)

    return mark(old), mark(new)


def _seo_change(conn, r: dict) -> str:
    """the listing draft's was -> becomes lines (mutate_seo), the product by
    name linked to its drill — factored so /approvals (_seo_approval_card) and
    the wall (_change_plain) render the SAME words from the one place."""
    prop = r["proposal"]
    a = prop.get("args") or {}
    # the LIVE products table keys shopify_id on the FULL gid — look up (and
    # link the drill) with the raw args product_id, never a rsplit tail.
    pid = str(a.get("product_id") or "")
    name, old_title, old_desc = "the product", "", ""
    try:
        row = conn.execute(
            "SELECT title, seo_title, seo_description FROM products"
            " WHERE shopify_id = ?", (pid,)).fetchone()
        if row:
            name = row["title"] or name
            old_title = (row["seo_title"] or "").strip()
            old_desc = (row["seo_description"] or "").strip()
    except Exception:
        pass
    lines = []
    for label, old_v, new_v in (("title", old_title, a.get("title")),
                                ("description", old_desc, a.get("description"))):
        if new_v is None:
            continue
        if old_v:
            old_m, new_m = _mark_diff_words(old_v, str(new_v))
        else:
            old_m, new_m = "empty", f"<b>{html_escape(str(new_v))}</b>"
        lines.append(f"{label}: was {old_m}, becomes {new_m}")
    return (f"<a href='/catalog/products/{pid}'>{html_escape(name)}</a> — "
            + " · ".join(lines))


def _seo_approval_card(conn, r: dict) -> str:
    """a parked listing draft (mutate_seo) as a plain per-item card (B2): the
    product by name linked to its drill, title/description as was -> becomes,
    a plain 'waits until', and the WHY it parks — no raw JSON, no gid, no code."""
    prop = r["proposal"]
    a = prop.get("args") or {}
    pid = str(a.get("product_id") or "")
    change = _seo_change(conn, r)
    # the WHY (M3): name the checked detail the draft quotes.
    quoted = []
    desc = a.get("description") or ""
    try:
        for c in conn.execute(
            "SELECT field, value, unit FROM spec_claims"
            " WHERE product = ? AND verified = 1 ORDER BY field", (pid,)):
            if str(c["value"]) and str(c["value"]) in desc:
                phrase = f"{c['field'].replace('_', ' ')}: {c['value']}"
                if c["unit"]:
                    phrase += f" {c['unit']}"
                quoted.append(phrase)
    except Exception:
        pass
    why = ""
    if quoted:
        why = (f"<div class='muted'>this draft quotes a checked detail "
               f"({html_escape(', '.join(quoted))}) — a claim on your store's "
               f"word, so it waits on you by itself.</div>")
    return f"""<div class='card'>
<strong>{act_label(prop['method'], r['status'])}</strong> <span class='muted'>· waits until {when_plain(r['expires_at'])}</span>
<div>{change}</div>
{why}
<form method='post' action='/api/approvals/{r['id']}' style='display:flex;gap:.6rem;align-items:center'>
 <label><input type='checkbox' name='confirm' value='true' required> confirm</label>
 <button name='decision' value='approved'>approve</button>
 <button name='decision' value='rejected' formnovalidate>reject</button>
</form></div>"""


def _run_receipts(items: list[dict], titles: dict[str, str] | None = None) -> str:
    """each item of a batch as a receipt row — the plain verdict first,
    then the exact change in plain words: the product by name, was → now
    (record-born ink escapes before markup)."""
    titles = titles or {}
    receipts = ""
    for it in items[:30]:
        state = it.get("state", "")
        if state == "counted":
            verdict, tone = "showed up live? yes", "ok"
        elif state.startswith("held"):
            verdict, tone = "waiting for your glance", "warn"
        elif state.startswith("lapsed"):
            verdict, tone = "lapsed — never executed", "warn"
        elif state.startswith("errored"):
            verdict, tone = "didn't run", "warn"
        elif state.startswith("declined"):
            verdict, tone = "declined — nothing ran", ""
        elif "not verified" in state or "not counted" in state:
            verdict, tone = "showed up live? no", "warn"
        else:
            verdict, tone = state, ""
        if it.get("new") is not None and "old" in it:
            pid = it.get("product_id")
            name = titles.get(pid) or "the product"
            old_s = str(it["old"]).strip()
            if old_s:
                old_m, new_m = _mark_diff(old_s, str(it["new"]))
            else:
                old_m, new_m = "empty", f"<b>{html_escape(str(it['new']))}</b>"
            change = (f"<a href='/catalog/products/{pid}'>{html_escape(name)}</a> — "
                      f"was {old_m}, becomes {new_m}")
        elif it.get("was") is not None and ("title" in it or "description" in it):
            # the listing-text change (F4b): two plain lines, the title and the
            # description each read was -> becomes, record-born ink escaped
            # before markup (via _mark_diff / html_escape).
            pid = it.get("product_id")
            name = titles.get(pid) or "the product"
            was = it.get("was") or {}
            lines = []
            for field_key, was_key in (("title", "seo_title"),
                                       ("description", "seo_description")):
                new_v = it.get(field_key)
                if new_v is None:
                    continue
                old_v = (was.get(was_key) or "").strip()
                if old_v:
                    old_m, new_m = _mark_diff_words(old_v, str(new_v))
                else:
                    old_m, new_m = "empty", f"<b>{html_escape(str(new_v))}</b>"
                lines.append(f"{field_key}: was {old_m}, becomes {new_m}")
            change = (f"<a href='/catalog/products/{pid}'>{html_escape(name)}</a> — "
                      + " · ".join(lines))
        else:
            disp = it.get("display", "")
            # a create (merchandising) has no "was → becomes" — its whole
            # sentence IS the change being approved, so it renders in full,
            # never truncated mid-rule ("… water bottle, bike water,…").
            if disp.startswith("new collection:"):
                change = html_escape(disp)
            else:
                change = intent_plain(disp, 90)
        receipts += tt.receipt(verdict, change, tone=tone)
    if len(items) > 30:
        receipts += (f"<div class='teletext-row'><span class='muted'>"
                     f"… and {len(items) - 30} more, all in the batch</span></div>")
    return receipts


def _titles_for(conn, items: list[dict]) -> dict[str, str]:
    """product names for a batch's receipts — one scoped read, never a scan."""
    pids = sorted({it.get("product_id") for it in items if it.get("product_id")})
    if not pids:
        return {}
    marks = ",".join("?" * len(pids))
    try:
        return {r[0]: r[1] for r in conn.execute(
            f"SELECT shopify_id, title FROM products WHERE shopify_id IN ({marks})",
            pids)}
    except Exception:
        return {}


@app.get("/catalog/runs/{run_id}", response_class=HTMLResponse)
def workflow_run_view(run_id: str, request: Request, conn=Depends(_db)):
    """the batch, before (and after) it lands — the WF-approve preview. every
    change in the batch in plain words, then ONE approve for the lot or a
    decline with the why. after the glance: the same page reads the receipts,
    each change saying whether it showed up live."""
    _guard(request, conn)
    catalog_runs.ensure_schema(conn)
    run = catalog_runs.get(conn, run_id)
    if run is None:
        return HTMLResponse(_page("operations", tt.catalog_subnav("workflows")
                                  + "<p class='muted'>no such batch — pick a fix from "
                                    "<a href='/catalog/workflows'>the fixes</a>.</p>"),
                            status_code=404)
    feat_label = feature_label(run["feature"])
    n = run["batch"]
    if run["status"] == "staged":
        sub = f"{feat_label} · a batch waiting for your glance"
        act = (
            f"<form method='post' action='/catalog/runs/{run['id']}/approve' class='run-form'>"
            f"<button class='run run--act'>approve the lot — {run['live']:,} change"
            f"{'s' if run['live'] != 1 else ''} &rarr;</button></form>"
            f"<form method='post' action='/catalog/runs/{run['id']}/decline' class='run-form'>"
            f"<input name='why' placeholder='why not (lands on the record)' required> "
            f"<button class='run'>decline the lot</button></form>"
            f"<div class='teletext-row'><p class='muted'>one approve lands the whole "
            f"batch through the same wall every approval walks — each change is "
            f"recorded as approved by you, executed, and checked live before it "
            f"counts. nothing changes your store until you approve. once you "
            f"approve, the batch runs to its end and reads back every change — "
            f"declining is your door until then.</p></div>")
        if run["lapsed"]:
            act += (f"<div class='teletext-row'><p class='muted'>{run['lapsed']} of the "
                    f"{n} waited past the approval window and will be skipped, never "
                    f"executed late.</p></div>")
    elif run["status"] == "lapsed":
        sub = f"{feat_label} · this batch lapsed"
        act = ("<div class='teletext-row'><p class='muted'>every change in this batch "
               "waited past the approval window — nothing runs late. still wanted "
               "means a fresh batch with current numbers.</p></div>")
    elif run["status"] == "rejected":
        sub = f"{feat_label} · declined"
        act = (f"<div class='teletext-row'><p class='muted'>declined: "
               f"{html_escape(run.get('reason') or '')} — nothing ran. "
               f"the why is on <a href='/record'>the record</a>.</p></div>")
    else:
        sub = f"{feat_label} · the batch landed"
        o = run.get("outcome") or {}
        act = (tt.state_row("showed up live", f"{o.get('counted', 0):,}")
               + tt.state_row("didn't show live", f"{o.get('failed', 0):,}")
               + tt.state_row("didn't run", f"{o.get('errored', 0):,}")
               + tt.state_row("lapsed, skipped", f"{o.get('lapsed', 0):,}")
               + tt.state_row("approved by", html_escape(who_plain(run.get("approved_by")))))
    marquee = tt.masthead("operations", f"{n:,}", sub, as_of=_asof())
    flash = request.query_params.get("flash")
    flash_card = (f"<div class='card'><strong>refused:</strong> "
                  f"{html_escape(flash)}</div>" if flash else "")
    body = (tt.catalog_subnav("workflows")
            + f"<p><a href='/catalog/workflows/{run['feature']}'>&larr; "
              f"{feat_label}</a></p>"
            + flash_card
            + tt.block("the batch, change by change",
                       (f"<div class='teletext-row'><p class='muted'>where these "
                        f"come from: {source_plain(run['feature'])}</p></div>"
                        + _run_receipts(run["items"], _titles_for(conn, run["items"]))),
                       "each change in plain words · nothing lands without you")
            # the header reads ahead while the call is yours, past once it landed.
            + tt.block("your call" if run["status"] == "staged" else "the call you made",
                       act,
                       "one glance · one approve" if run["status"] == "staged"
                       else "what you decided · already recorded"))
    return _page("operations", body, marquee=marquee,
                 signoff_line="a batch lands only on your approve · every change is "
                              "checked live before it counts")


@app.post("/catalog/runs/{run_id}/approve")
async def workflow_run_approve(run_id: str, request: Request, conn=Depends(_db)):
    """ONE glance-approve for a held reversible batch. walks the standard
    walls per record (resolve by you, the one-use handle, the one write door,
    verify-render) — this is the same approve verb, applied to the lot."""
    _guard(request, conn)
    catalog_runs.ensure_schema(conn)
    run = catalog_runs.get(conn, run_id)
    if run is None:
        return JSONResponse({"error": "no such batch"}, status_code=404)
    feat = catalog_workflows.FEATURES.get(run["feature"])
    if feat is None:
        return JSONResponse({"error": "this batch's fix no longer exists"},
                            status_code=409)
    try:
        catalog_runs.approve(conn, run_id, feat, by=_who(request))
    except ledger.StateError as e:
        return RedirectResponse(
            url=f"/catalog/runs/{run_id}?flash={quote(str(e))}", status_code=303)
    _refresh_reports(conn)
    await emit({"kind": "workflow_run.approved", "run_id": run_id})
    return RedirectResponse(url=f"/catalog/runs/{run_id}", status_code=303)


@app.post("/catalog/runs/{run_id}/decline")
async def workflow_run_decline(run_id: str, request: Request, conn=Depends(_db)):
    """decline the held batch — the why is required and lands on every
    record, so the record reads the reason wherever any of them shows."""
    _guard(request, conn)
    catalog_runs.ensure_schema(conn)
    body = (await request.body()).decode()
    form = {k: v[0] for k, v in parse_qs(body).items()}
    why = (form.get("why") or "").strip()
    if not why:
        return RedirectResponse(
            url=f"/catalog/runs/{run_id}?flash="
                + quote("a decline needs its why — it lands on the record"),
            status_code=303)
    try:
        catalog_runs.reject(conn, run_id, by=_who(request, form), why=why)
    except (KeyError, ledger.StateError) as e:
        return RedirectResponse(
            url=f"/catalog/runs/{run_id}?flash={quote(str(e))}", status_code=303)
    await emit({"kind": "workflow_run.rejected", "run_id": run_id})
    return RedirectResponse(url=f"/catalog/runs/{run_id}", status_code=303)


@app.get("/health")
def health():
    return {"ok": True, "version": __version__}
