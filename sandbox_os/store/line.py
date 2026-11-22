# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""What a line is: its canonical bytes, its id and hash, the closed kinds and relations, who may author it, and what it may never hold."""
import datetime as _dt
import hashlib, json, os, re, threading, time

from sandbox_os import VERSION
from sandbox_os.store import Refused

KINDS = ("session", "brief", "run", "close", "abandoned", "accept", "said", "card", "answer", "needless", "grant",
         "grant_back", "note", "finding", "learned", "changed", "fact", "about_you", "rule", "moment", "recall",
         "receipt", "check", "acceptance", "strike", "unstrike", "delete", "undelete", "erase", "join", "link",
         "present", "bet", "night", "host_ask", "host_ran", "hook", "not_seen", "usage", "live", "preview", "flow",
         "held", "release", "move", "migration", "copy", "fork", "measure", "object", "verb", "goal", "assumption",
         "question")
RELATIONS = ("proves", "answers", "follows", "came_from", "supersedes", "strikes", "deletes", "part_of", "serves")
CLAIM_KINDS = ("close", "note", "finding", "learned", "changed", "present", "live")
FACT_KINDS = ("note", "finding", "learned", "changed", "fact", "about_you", "rule", "present", "answer", "grant", "bet",
              "goal", "assumption", "question", "object", "verb")
CHAIN_KINDS = ("erase", "join", "move", "migration")
BASES = ("he said", "a check showed", "I read it in", "my guess")  # how a fact came to be known: his word, a check, a reading, a guess
IMPLIED = {"strike": ("target", "strikes"), "unstrike": ("target", "strikes"), "delete": ("target", "deletes"),
           "undelete": ("target", "deletes"), "answer": ("card", "answers"), "accept": ("run", "answers"),
           "receipt": ("claim", "proves"), "check": ("claim", "proves"), "needless": ("answer", "follows"),
           "fact": ("source", "came_from")}  # a belief's source, when it is a line id; a path, an address or a fact about no thing makes no link
_QUIET = {"session", "hook", "host_ask", "host_ran", "not_seen", "usage", "link", "strike", "unstrike", "delete",
          "undelete", "erase", "join"}
ENDS = {"proves": (set(KINDS) - _QUIET, set(CLAIM_KINDS) | {"goal"}),  # a goal is met when a check proves it
        "answers": ({"answer", "accept", "fact", "check"}, {"card", "close", "run", "grant", "question"}),
        "follows": (None, None), "came_from": (None, None), "supersedes": (set(FACT_KINDS) | {"said", "receipt"}, set(FACT_KINDS) | {"said", "receipt"}),  # his newer word replaces his older; an undo's receipt the act's
        "strikes": ({"strike", "unstrike"}, set(KINDS) - set(CHAIN_KINDS)), "deletes": ({"delete", "undelete"}, None),
        "part_of": (None, {"run", "night", "session"}), "serves": ({"run", "night", "card"}, {"bet", "grant", "goal"})}
ACROSS = {"part_of": {"note", "present", "finding", "said", "close"}}  # card 22: a line about another unit, part_of that unit's first line
AUTHORS = ("maker", "person", "partner", "tool")
MARK_KEYS = ("proved", "struck", "deleted", "mark", "ink")
DOWN_MARKS = ("erased", "deleted", "struck")  # a line with one of these marks no longer weighs; superseded is its own mark beside them
TEXT_MAX, LINE_MAX = 16 * 1024, 64 * 1024
UNIT_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
ID_RE = re.compile(r"[0-9A-HJKMNP-TV-Z]{26}\Z")
T_RE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z\Z")
DATE_RE = re.compile(r"\d{4}-\d\d-\d\d\Z")
SKIP = {"id", "ids", "hash", "prev", "sha256", "payload", "salt", "card", "claim", "run", "target", "from", "to",
        "erased", "by"}
SECRET_PATTERNS = {name: re.compile(p) for name, p in (
    ("private_key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("aws_access_key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("github_token", r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    ("slack_token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("stripe_live_key", r"\b[sr]k_live_[A-Za-z0-9]{10,}"),
    ("anthropic_key", r"\bsk-ant-[A-Za-z0-9_-]{10,}"),
    ("openai_style_key", r"\bsk-[A-Za-z0-9]{32,}"),
    ("google_api_key", r"\bAIza[0-9A-Za-z_-]{35}"),
    ("shopify_token", r"\bshp(?:at|ca|pa|ss)_[a-fA-F0-9]{32}"),
    ("jwt", r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    ("named_secret", r"(?i)\b(?:password|passwd|secret|token|api[ _-]?key)\s*[=:]\s*\S{8,}"),
    # a wallet's private key, 64 hex digits with or without 0x, named as a key on a command line, in an environment line or in a printed line
    # (--private-key, PRIVATE_KEY=, "Private key:", pk=); a bare 0x and 64 hex digits is a transaction's or a block's hash as often, a
    # receipt among them, so it is not matched alone
    ("hex_private_key", r"(?i)(?:priv(?:ate)?[\s_-]*key|\bpk)[\"'\s:=]*(?:0x)?[0-9a-f]{64}\b"))}
CROCK = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)
_last, _mint = [0, 0], threading.Lock()


def canonical(obj):
    """The one form a line has on disk: keys sorted, no spaces, non-ASCII kept as written, no NaN."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def line_hash(obj):
    """SHA-256 over the canonical JSON of every field but the hash itself."""
    return hashlib.sha256(canonical({k: v for k, v in obj.items() if k != "hash"}).encode()).hexdigest()


def _b32(n, width):
    return "".join(CROCK[(n >> 5 * i) & 31] for i in reversed(range(width)))


def mint_id(ms=None):
    """26 characters: 48 bits of milliseconds, then 80 random bits; a second id in the same millisecond takes the first's random part plus one, so ids sort as text in mint order."""
    with _mint:
        if ms is None:
            ms = max(time.time_ns() // 1_000_000, _last[0])
        r = (_last[1] + 1) % (1 << 80) if ms == _last[0] else int.from_bytes(os.urandom(10), "big")
        _last[:] = [ms, r]
    return _b32(ms, 10) + _b32(r, 16)


def id_time_ms(i):
    return sum(CROCK.index(c) << 5 * k for k, c in enumerate(reversed(i[:10])))


def iso(dt):
    dt = dt.astimezone(_dt.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def parse_t(s):
    return _dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=_dt.timezone.utc)


def iso_ms(s):
    return (parse_t(s) - EPOCH) // _dt.timedelta(milliseconds=1)


def find_secret(text):
    """The name of the first secret pattern the text matches, or None."""
    return next((name for name, rx in SECRET_PATTERNS.items() if rx.search(text)), None)


def text_of(body):
    """Every string a person reads in a body, in order, skipping the keys that hold ids, hashes and payload refs."""
    out = []

    def walk(v):
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, dict):
            [walk(x) for k, x in v.items() if k not in SKIP and not k.endswith(("_id", "_sha256"))]
        elif isinstance(v, list):
            [walk(x) for x in v]
    walk(body)
    return " ".join(out)


def words_of(body):
    """The words a person reads in a body: its text, words, purpose, decides or sentence, else every string in it; what an erasure's block hashes."""
    for k in ("text", "words", "purpose", "decides", "sentence"):
        if isinstance(body.get(k), str) and body[k]:
            return body[k]
    return text_of(body)


def local_date(x, zone=None):
    """The maker's local day of a moment (an aware datetime, or a line's time): in zone when one is given, else this machine's own zone,
    the one the pages' month and week are read in. The store's past marks and the pages' measures share it."""
    if isinstance(x, str):
        x = parse_t(x)
    return (x.astimezone(zone) if zone else x.astimezone()).date()


def day_end(day):
    """The last millisecond of one of his local days (a date or YYYY-MM-DD), in this machine's zone as local_date and the pages read a day,
    as a line's time in UTC: the cut of the world as it stood on that day (review of batch D, finding 4). A day that is none: ValueError."""
    d = _dt.date.fromisoformat(day.isoformat()[:10] if hasattr(day, "isoformat") else str(day)[:10])
    return iso(_dt.datetime.combine(d + _dt.timedelta(days=1), _dt.time()).astimezone() - _dt.timedelta(milliseconds=1))


def one_space(command):
    """A check's command as two checks are compared: split on whitespace and joined on single spaces; anything not a string as it is."""
    return " ".join(command.split()) if isinstance(command, str) else command


def strip_arabic_marks(s):
    """Arabic as bare letters: the short vowels, the dagger alif and the tatweel removed."""
    return re.sub("[\u064B-\u0652\u0670\u0640]", "", s)


def payload_refs(v):
    """Every payload a body names as {"payload": sha256, ...}, at any depth."""
    if isinstance(v, dict):
        return ([v["payload"]] if isinstance(v.get("payload"), str) else []) + [r for x in v.values() for r in payload_refs(x)]
    return [r for x in v for r in payload_refs(x)] if isinstance(v, list) else []


def links_of(obj):
    """The links a line makes, as (from, relation, to): a link line's own, or the one its kind implies."""
    b, k = obj.get("body") or {}, obj.get("kind")
    if k == "link":
        return [(b.get("from"), b.get("rel"), b.get("to"))]
    if k == "goal":  # a goal cites the said lines it was made from, one came_from link each
        return [(obj["id"], "came_from", f) for f in b.get("fragments") or [] if isinstance(f, str) and ID_RE.match(f)]
    out = []
    if k in IMPLIED and isinstance(b.get(IMPLIED[k][0]), str) and (k != "fact" or obj.get("about") is not None and ID_RE.match(b[IMPLIED[k][0]])):
        # a fact's source leans only for a belief (a fact with about); a fact about no thing, as format 1 wrote them, reads as it always did
        out.append((obj["id"], IMPLIED[k][1], b[IMPLIED[k][0]]))
    if k == "fact" and isinstance(b.get("answer"), str) and ID_RE.match(b["answer"]):  # the maker's yes a verb's fact rests on (batch C, Task 2)
        out.append((obj["id"], "came_from", b["answer"]))
    return out


def binds(l):
    """The page's and the index's answer rules: the maker's, standing, not from a client with no one at the desk, not a stale page's,
    not the recorder's report of a person not established. The command's cards.binds is this name (batch C, Task 4)."""
    b = l["body"] or {}
    return l["by"]["kind"] == "maker" and l["mark"] not in DOWN_MARKS + ("superseded",) and b.get("presence") != "none" and b.get("stale") is not True \
        and b.get("person") != "not established"


def ends_ok(rel, from_kind, to_kind, across=False):  # across: the far end is another unit's first line
    f, t = ENDS[rel]
    return across and from_kind in ACROSS.get(rel, ()) or (f is None or from_kind is None or from_kind in f) and (t is None or to_kind is None or to_kind in t)


def check_by(by, *, kept=False):
    """The author as the store writes it, with the store's own version; refuses anything else. kept: a line carried from another workshop's
    record keeps the version its author carried (the review of batch E, finding 7), set only by the door from a carried planned line."""
    if not isinstance(by, dict):
        raise Refused("by names who wrote a line, as {kind, name, model, host}")
    if "version" in by and not (kept and isinstance(by["version"], str) and by["version"].strip()):
        raise Refused("the store writes its own version into by; a caller cannot supply one")
    extra = sorted(set(by) - {"kind", "name", "model", "host", "version"})
    if extra:
        raise Refused(f"by holds kind, name, model and host only, not {', '.join(extra)}")
    if by.get("kind") not in AUTHORS:
        raise Refused(f"an author is the maker, a person, the partner or the tool, not {by.get('kind')!r}")
    if not isinstance(by.get("name"), str) or not by["name"]:
        raise Refused("an author carries a name")
    if by["kind"] == "partner" and not by.get("model"):
        raise Refused("the partner records with its model named, and this by has no model")
    return {"kind": by["kind"], "name": by["name"], "model": by.get("model"), "host": by.get("host"), "version": by.get("version") or VERSION}


def check_body(body, *, erasing=False):
    """Refuses a body that is not an object, carries a mark, holds a text over 16 KiB, or matches a secret pattern."""
    if not isinstance(body, dict):
        raise Refused(f"a body is an object of named fields, not a {type(body).__name__}")
    for k in MARK_KEYS + (() if erasing else ("erased",)):
        if k in body:
            raise Refused(f"a body may not carry the mark '{k}'; marks are computed from the record, never written into it")
    try:
        text = canonical(body)
    except (TypeError, ValueError) as e:
        raise Refused(f"a body holds only plain JSON values ({e})") from None

    def walk(v):
        if isinstance(v, str) and len(v.encode()) > TEXT_MAX:
            raise Refused("a text over 16 KiB does not fit in a line; keep it beside as a payload with payload()")
        [walk(x) for x in (v.values() if isinstance(v, dict) else v if isinstance(v, list) else ())]
    walk(body)
    name = find_secret(text)
    if name:
        raise Refused(f"the words match the secret pattern '{name}', so nothing was written; keep secrets out of the record")
