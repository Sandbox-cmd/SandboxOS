"""the content/seo agent's drafting half (F4a) — listing text from facts.

it reads the catalog record and drafts the search listing (title +
description) for products whose listing is missing or weak. every word
comes from facts on hand — the product's title, vendor, category, and
VERIFIED spec claims (verified=1). a spec value is pulled from the
catalog, never re-derived: an unverified claim never enters
customer-facing text, and a draft that would quote a value the catalog
has not verified is refused at construction. every proposal rides the
gate with provenance; the manifest split is implemented at declare time:
plain title/vendor/category drafts declare reversible (content-geo
auto-approves them), drafts quoting a verified spec value declare
consequential and park for the owner — a customer-facing claim waits
for a human, even a true one.
"""

from __future__ import annotations

import re

from commerceos.gate import gate, ledger
from commerceos.spine import writes

AGENT = "content"          # matches .claude/agents/content.md (the manifest)
FUNCTION = "content-geo"   # the policy function registered in the store table

# search-listing convention: results pages truncate titles near 60 chars
# and descriptions near 155 — text past the cut is text nobody reads.
TITLE_LIMIT = 60
DESCRIPTION_LIMIT = 155

# invented superlatives have no fact behind them — refused, not trimmed.
_HYPE = ("best", "amazing", "unbeatable", "world-class", "premium",
         "revolutionary", "perfect", "ultimate", "finest")
_HYPE_RE = re.compile(r"\b(" + "|".join(_HYPE) + r")\b", re.IGNORECASE)


class DraftRefused(RuntimeError):
    """a draft that states what the catalog has not verified — refused."""


# ---- text assembly: facts in, plain words out ---------------------------

def _squeeze(text: str) -> str:
    return " ".join((text or "").split())


# a trimmed line must never dangle on a connective — "…Extra Long Zip And"
# is not a listing, it's a truncation showing. strip trailing conjunctions and
# prepositions after the word-boundary cut so the line ends on a real word.
_DANGLERS = {"and", "or", "with", "the", "a", "an", "for", "to", "of", "in",
             "on", "by", "at", "from", "as", "&", "|", "-", "plus", "into"}


def _fit(text: str, limit: int) -> str:
    """trim to the limit at a word boundary — a cut word is a cut word,
    never an invented one. no ellipsis: the text is what it says. only a
    TRUNCATED line strips its trailing dangler/punctuation (that's the cut
    showing); text that fits whole keeps its own sentence-ending period."""
    text = _squeeze(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return _strip_danglers(cut.rstrip(" ,;:.—-"))


def _strip_danglers(text: str) -> str:
    """drop trailing connectives (and/with/for/…) and stray punctuation so a
    trimmed title reads as a finished phrase, not a mid-sentence cut."""
    words = text.split()
    while words and words[-1].lower().strip(",;:.—-") in _DANGLERS:
        words.pop()
    return " ".join(words).rstrip(" ,;:.—-")


def _claim_phrase(claim: dict) -> str:
    """'Beam output: 900 lm.' — the field named plainly, the value verbatim."""
    label = claim["field"].replace("_", " ").strip().capitalize()
    value = str(claim["value"]).strip()
    unit = (claim.get("unit") or "").strip()
    if unit and not value.endswith(unit):
        value = f"{value} {unit}"
    return f"{label}: {value}."


def draft_title(title: str, vendor: str | None) -> str:
    """product title, vendor appended when it fits and adds a fact."""
    base = _squeeze(title)
    if vendor and vendor.lower() not in base.lower():
        joined = f"{base} | {_squeeze(vendor)}"
        if len(joined) <= TITLE_LIMIT:
            return joined
    return _fit(base, TITLE_LIMIT)


def draft_description(title: str, vendor: str | None, category: str | None,
                      verified_claims: list[dict]) -> tuple[str, list[dict]]:
    """assemble the description from facts, greedily, inside the limit.

    returns (text, used_claims) — only the claims actually quoted count,
    because only they make the draft a customer-facing spec statement.
    """
    title = _squeeze(title)
    if vendor and vendor.lower() not in title.lower():
        pieces = [f"{title} from {_squeeze(vendor)}."]
    else:
        pieces = [f"{title}."]
    if category:
        # the category is a fact, but "Category: X." is a form label, not
        # customer copy — fold it into a plain sentence instead.
        pieces.append(f"Find it in {_squeeze(str(category))}.")
    text = _fit(" ".join(pieces), DESCRIPTION_LIMIT)
    used: list[dict] = []
    for c in verified_claims:
        candidate = f"{text} {_claim_phrase(c)}"
        if len(candidate) <= DESCRIPTION_LIMIT:
            text = candidate
            used.append(c)
    return text, used


# ---- the refusal law ----------------------------------------------------

def check_draft_against_catalog(conn, draft: dict) -> None:
    """refuse a draft the catalog cannot back. raises DraftRefused when:

    - the title or description overruns the search-listing limits;
    - the text carries a hype word (an invented superlative has no fact);
    - a cited claim is missing, unverified, or drifted from its catalog
      value — a spec value is pulled from the catalog, never re-derived;
    - the text states the value of an UNVERIFIED claim for this product
      (verified=0 values of length >= 2 are scanned verbatim) — the
      manifest's parking law applied at draft time: an unverified claim
      never enters customer-facing text;
    - the draft would say nothing beyond the raw name and vendor (M5) — a
      near-echo of the product name is template smell, refused honestly.

    a field the draft leaves alone (None — a real value kept) is not checked.
    """
    title = draft.get("title")
    description = draft.get("description")
    text = " ".join(p for p in (title, description) if p)
    if title is not None and len(title) > TITLE_LIMIT:
        raise DraftRefused(f"title overruns {TITLE_LIMIT} chars")
    if description is not None and len(description) > DESCRIPTION_LIMIT:
        raise DraftRefused(f"description overruns {DESCRIPTION_LIMIT} chars")
    hype = _HYPE_RE.search(text)
    if hype:
        raise DraftRefused(f"hype word {hype.group(0)!r} — no fact behind it")
    for c in draft.get("claims", []):
        row = conn.execute(
            "SELECT value, verified FROM spec_claims WHERE id = ?",
            (c["id"],)).fetchone()
        if row is None:
            raise DraftRefused(f"cited claim {c['id']} is not in the catalog")
        if not row["verified"]:
            raise DraftRefused(
                f"cited claim {c['id']} ({c['field']}) is unverified — parks, never publishes")
        if str(row["value"]) != str(c["value"]):
            raise DraftRefused(
                f"claim {c['id']} ({c['field']}) drifted: catalog says "
                f"{row['value']!r}, draft says {c['value']!r}")
    for row in conn.execute(
            "SELECT field, value FROM spec_claims WHERE product = ? AND verified = 0",
            (draft["product"],)):
        value = str(row["value"]).strip()
        if len(value) >= 2 and value in text:
            raise DraftRefused(
                f"text states unverified {row['field']} value {value!r} — "
                "not a verified claim, not customer-facing text")
    # M5, last: a draft that adds nothing past the raw name + vendor is
    # template smell — refuse it after every more specific reason.
    if draft.get("thin"):
        raise DraftRefused("the facts are too thin to write this one")


# ---- compute: the weak listings and their drafts ------------------------

def compute_listing_drafts(conn, limit: int = 50) -> list[dict]:
    """draft listings for products whose listing is missing or weak.

    the weak rule, read from what the data can honestly mean:
      - no-seo-title:          seo_title NULL or blank — nothing written;
      - no-seo-description:    seo_description NULL or blank;
      - seo-title-is-raw-title: seo_title equals the raw product title —
        the platform default echoed back, which is a listing nobody wrote.

    each draft is built ONLY from facts on hand — product title, vendor,
    category, and verified spec claims — and carries provenance for every
    fact it drew from. a draft writes PER FIELD: a real human description is
    never replaced with fewer facts — only an empty or platform-echo field is
    drafted, and a field already good stays untouched (a None on that field in
    the draft means "leave it"). declared_type is the manifest split:
    reversible when no spec value is quoted, consequential when one is. a draft
    that would say nothing beyond the raw name and vendor is marked thin — the
    refusal wall turns template smell away (M5).
    """
    rows = conn.execute(
        "SELECT p.shopify_id pid, p.title, p.vendor, p.seo_title, p.seo_description,"
        "       p.source, c.title c_title, c.vendor c_vendor, c.category"
        " FROM products p LEFT JOIN canonical_products c ON c.shopify_id = p.shopify_id"
        " WHERE p.title IS NOT NULL AND TRIM(p.title) <> ''"
        "   AND (p.seo_title IS NULL OR TRIM(p.seo_title) = ''"
        "        OR p.seo_description IS NULL OR TRIM(p.seo_description) = ''"
        "        OR p.seo_title = p.title)"
        " ORDER BY p.shopify_id").fetchall()
    out: list[dict] = []
    for r in rows:
        cur_title = (r["seo_title"] or "").strip()
        cur_desc = (r["seo_description"] or "").strip()
        title_weak = (not cur_title) or (r["seo_title"] == r["title"])   # empty or echo
        desc_weak = not cur_desc                                          # empty only
        if not r["seo_title"] or not cur_title:
            reason = "no-seo-title"
        elif not cur_desc:
            reason = "no-seo-description"
        else:
            reason = "seo-title-is-raw-title"
        title = r["c_title"] or r["title"]          # the catalog record first
        vendor = r["c_vendor"] or r["vendor"]
        verified = [dict(c) for c in conn.execute(
            "SELECT id, field, value, unit, source FROM spec_claims"
            " WHERE product = ? AND verified = 1 ORDER BY field",
            (r["pid"],))]
        # draft ONLY the weak fields — a real description is kept, never
        # overwritten with fewer facts (B1a). a None field means "leave it".
        new_title = draft_title(title, vendor) if title_weak else None
        if desc_weak:
            new_desc, used = draft_description(title, vendor, r["category"], verified)
        else:
            new_desc, used = None, []
        if ((new_title is None or new_title == cur_title)
                and (new_desc is None or new_desc == cur_desc)):
            continue  # nothing to improve — a no-op write proves nothing
        # thin: a drafted description that adds nothing past the raw name +
        # vendor (no category folded, no verified claim) is template smell.
        thin = bool(new_desc is not None and not used and not r["category"])
        provenance = [{"fact": "products", "id": r["pid"], "source": r["source"]}]
        if r["category"]:
            provenance.append({"fact": "canonical_products", "id": r["pid"],
                               "field": "category", "value": r["category"]})
        provenance += [{"fact": "spec_claims", "claim_id": c["id"],
                        "field": c["field"], "source": c["source"]} for c in used]
        out.append({
            "product": r["pid"],
            "name": _squeeze(title),                 # the raw name, for cards + lists
            "product_id": r["pid"] if str(r["pid"]).startswith("gid://")
                          else f"gid://shopify/Product/{r['pid']}",
            "title": new_title, "description": new_desc,
            "was": {"seo_title": r["seo_title"], "seo_description": r["seo_description"]},
            "weak_reason": reason,
            "thin": thin,
            "claims": [{"id": c["id"], "field": c["field"], "value": c["value"]}
                       for c in used],
            "declared_type": "consequential" if used else "reversible",
            "provenance": provenance,
        })
        if len(out) >= limit:
            break
    return out


WORK_KINDS = {"listing_draft": compute_listing_drafts}


def propose_and_run(conn, kind: str = "listing_draft", limit: int = 50,
                    client=None) -> dict:
    """compute -> refuse dishonest drafts -> gate -> (auto) execute.

    the manifest split, live: a reversible draft (no spec value quoted)
    auto-approves under content-geo and executes with a verify-rendered
    receipt; a draft quoting a verified spec value declares consequential
    and parks for the owner. a draft the catalog cannot back is refused
    with its reason on the receipt — skipped, never softened.
    """
    compute = WORK_KINDS[kind]
    proposals = compute(conn, limit=limit)
    receipts = {"kind": kind, "computed": len(proposals), "executed": 0,
                "parked": 0, "refused": 0, "failed": 0, "records": []}
    for p in proposals:
        try:
            check_draft_against_catalog(conn, p)
        except DraftRefused as e:
            receipts["refused"] += 1
            receipts["records"].append({"product": p["product"], "refused": str(e)[:120]})
            continue
        res = gate.submit(conn, {
            "agent": AGENT, "function": FUNCTION, "method": "mutate_seo",
            "args": {"product_id": p["product_id"], "title": p["title"],
                     "description": p["description"]},
            "declared_type": p["declared_type"],
            "intent": f"draft the search listing for {p['product']}"
                      f" ({p['weak_reason']})",
            "rationale": "listing text drafted from catalog facts only —"
                         " title, vendor, category, verified claims (F4a, C2)",
            "provenance": p["provenance"],
        })
        if res["decision"] == "parked":
            receipts["parked"] += 1
            receipts["records"].append({"id": res["record_id"][:8], "parked": True})
            continue
        try:
            out = writes.execute(conn, res["record_id"], client=client)
            ok = bool(out.get("ok") and out.get("verified_rendered"))
            receipts["executed"] += 1 if ok else 0
            receipts["failed"] += 0 if ok else 1
            receipts["records"].append({"id": res["record_id"][:8], "ok": ok})
        except Exception as e:
            receipts["failed"] += 1
            receipts["records"].append({"id": res["record_id"][:8], "error": str(e)[:120]})
    return receipts


# ---- F4b: the listing-text FEATURE — a front over the one workflow engine ----
# the drafting half above stays the consequential lane's door (propose_and_run
# parks a spec-quoting draft per item). these four callables give the reversible
# plain drafts a batch front: seo_queue is the refusal WALL (the engine has no
# refusal hook — an unverified-claim draft would ride straight to a glance-
# approve unless the queue stops it), reversible-only by construction (a mixed
# batch would let runs.approve glance-approve a consequential draft); seo_verify
# is the count check; seo_writeback routes the store-verified listing back into
# the facts so the queue drops.

def _seo_split(conn, limit: int = 50) -> dict:
    """compute the drafts once and split them the way the laws demand:
      - the QUEUE: reversible drafts that pass the refusal law, shaped for the
        engine (args = the mutate_seo executor's fields with the gid; the STORED
        id kept on the item for the receipts' name lookup; the old values for
        the was -> becomes preview);
      - PARKED: the consequential (spec-quoting) drafts — never batched, they
        ride propose_and_run per item; counted here so the card names them;
      - REFUSED: drafts the catalog cannot back — counted, never proposed.
    one compute feeds both the queue and the progress card, so the number a
    person reads and the wall that enforces it can never disagree."""
    queue, parked, refused = [], 0, []
    for d in compute_listing_drafts(conn, limit=limit):
        try:
            check_draft_against_catalog(conn, d)
        except DraftRefused as e:
            refused.append({"product": d["product"], "name": d.get("name"),
                            "reason": _refusal_plain(str(e))})
            continue
        if d["declared_type"] != "reversible":
            parked += 1                 # a customer-facing claim waits for a human
            continue
        queue.append({
            "product": d["product"],
            "product_id": d["product"],          # the STORED id — for _titles_for
            "name": d.get("name"),
            "args": {"product_id": d["product_id"],   # the gid — the executor's arg
                     "title": d["title"], "description": d["description"]},
            "title": d["title"], "description": d["description"],
            "was": d["was"],
            "weak_reason": d["weak_reason"],
            "display": f"{d['product']}  listing text: {d['title'] or d['description']}",
        })
    return {"queue": queue, "parked": parked, "refused": refused}


# the wall's raw reasons in one plain sentence each — never the code word.
def _refusal_plain(msg: str) -> str:
    m = msg.lower()
    if "too thin" in m:
        return "the facts on hand are too thin to write a real listing"
    if "hype" in m:
        return "it leaned on a sales word the facts don't back"
    if "overruns" in m:
        return "it ran longer than a search listing shows"
    if "unverified" in m or "drifted" in m or "not in the catalog" in m:
        return "it would state a detail no one has checked yet"
    return "the catalog can't back it yet"


def seo_queue(conn) -> list:
    """the reversible plain-listing drafts, shaped for the engine. the wall runs
    inside here: a draft the refusal law kills, or one that quotes a verified
    spec value (consequential), never reaches this list."""
    return _seo_split(conn)["queue"]


def seo_held_back(conn) -> list:
    """the drafts the wall turned away — each product by name with one plain
    reason, so 'held back' opens to a real list, never a dead number (M2)."""
    return _seo_split(conn)["refused"]


def seo_verify(outcome: dict, item: dict) -> bool:
    """counts only when the store read the drafted listing back — for EACH field
    the item actually drafted (a None field was left alone and is not checked).
    a dishonest read-back on a written field never counts."""
    if not outcome.get("ok"):
        return False
    back = outcome.get("seo") or {}
    for field in ("title", "description"):
        want = item.get(field)
        if want is not None and back.get(field) != want:
            return False
    return True


def seo_writeback(conn, item: dict, outcome: dict) -> None:
    """route the store-verified listing back into the products facts (the spine
    is the products fact owner — one writer per table-set), so the weak-listing
    rule, the progress card, and the feed read truth without waiting for the
    next full sync. this is what makes the queue drop."""
    from commerceos.spine import connector_shopify
    back = outcome.get("seo") or {}
    connector_shopify.writeback_product_seo(
        conn, item["product_id"], back.get("title"), back.get("description"))


def seo_progress(conn) -> dict:
    """the card numbers, all live from the facts: how many listings are written
    vs still missing-or-weak, how many drafts are ready to stage (the queue),
    and — named honestly — the consequential drafts that park per item and the
    drafts the wall refused. pending/lapsed count the LIVE mutate_seo waits from
    the ledger (the parked spec-quoting drafts), the lapsed ones lapsed, so the
    card and home agree on the same facts."""
    total = conn.execute(
        "SELECT COUNT(*) FROM products WHERE title IS NOT NULL"
        " AND TRIM(title) <> ''").fetchone()[0]
    weak = conn.execute(
        "SELECT COUNT(*) FROM products"
        " WHERE title IS NOT NULL AND TRIM(title) <> ''"
        "   AND (seo_title IS NULL OR TRIM(seo_title) = ''"
        "        OR seo_description IS NULL OR TRIM(seo_description) = ''"
        "        OR seo_title = title)").fetchone()[0]
    written = total - weak
    split = _seo_split(conn)
    # the LIVE per-item waits: consequential (spec-quoting) mutate_seo drafts
    # parked in decisions. the reversible batch-held records are NOT counted
    # here — they wait as one batch, named on p203, not item by item. this is
    # the single wait number (M1): no separate "parked" line double-counts it.
    pending = lapsed = 0
    try:
        rows = conn.execute(
            "SELECT expires_at FROM ledger WHERE status = 'pending'"
            " AND json_extract(proposal, '$.method') = 'mutate_seo'"
            " AND json_extract(proposal, '$.declared_type') = 'consequential'"
        ).fetchall()
    except Exception:
        rows = []      # no ledger yet — nothing can be pending
    for r in rows:
        if ledger.expired(r["expires_at"]):
            lapsed += 1
        else:
            pending += 1
    # the breathing gap: a consequential (spec-quoting) draft is computed but
    # the writer hasn't proposed it yet, so it's inside the missing-or-weak
    # door but no per-item wait names it. count exactly those — the whole
    # consequential bucket minus the ones already parked live — so the breakdown
    # names every weak product (ready to draft + waiting + to_stage + held back
    # = weak). once the writer stages it, `waiting` covers it and this clears.
    to_stage = max(0, split["parked"] - pending)
    return {"written": written, "weak": weak, "to_draft": len(split["queue"]),
            "waiting": pending, "to_stage": to_stage,
            "held_back": len(split["refused"]), "lapsed": lapsed,
            "rate": round(written / total, 4) if total else 0.0}
