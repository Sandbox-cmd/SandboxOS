"""CS0 step 1 — the three SF1 voice lints armed as tests, plus the roster
guard (PACK.md "the ruled contracts", test_sf1_lints.py). shape copied from
tests/test_voice_register.py: a hand-shaped convention guard (:29-51 the
hand-enumerated roster, :61-68 the drift check) applied here to fusion.py's
FUSION_*_PLAIN sets and to every sentence commerceos.web.triage can emit.

gap named honestly (see the builder's report): context.md/PACK.md do not
name fusion.py's actual FUSION_*_PLAIN set identifiers — those are born in
step 2. test_voice_register.py's roster (PLAIN_LABEL_SETS) could be hand-
enumerated because web/app.py's sets already existed when it was written;
here they don't yet. So this file discovers the roster by introspecting
commerceos.web.fusion for names matching the house convention, rather than
hand-listing names that don't exist yet — the drift-guard test still checks
that regex-over-source and introspection agree, which is the same safety
net test_voice_register.py's guard performs.
"""

import inspect
import re

from commerceos.web import fusion
from commerceos.web.triage import triage

FUSION_SET_NAME_RE = re.compile(r"^(FUSION_[A-Z0-9_]*_PLAIN)$")

# the SF1 voice pass's registered fiction words (spec/parts/collab-surface.md
# "the register") — none of these may bind to a second meaning on this
# surface. verbatim from PACK.md.
FICTION_WORDS = {
    "cassette", "cartridge", "teletext", "tuned", "on air", "serial", "broadcast",
}

LAND_RE = re.compile(r"\bland(s|ed|ing)?\b", re.I)

# phrase-level allowlist for the land-guard: an exact phrase already proven
# to read fine with a landing word inside it, owner always the subject.
# empty until a real fixture needs one — every entry must itself start with
# "you " (asserted below), never a loophole for a machine-subject phrase.
LAND_GUARD_ALLOWLIST: set[str] = set()


def _fusion_plain_sets() -> dict[str, dict]:
    """every module-level dict in fusion.py named the house convention
    (FUSION_*_PLAIN) — the lint roster this file's tests walk."""
    return {
        name: value
        for name, value in vars(fusion).items()
        if FUSION_SET_NAME_RE.match(name) and isinstance(value, dict)
    }


def _representative_triage_sentences() -> list[str]:
    """every sentence shape triage() can emit, per PACK.md's sentence law —
    calm, one, two-in-one-group, heavy (both groups), stopped (singular and
    plural), and the unknown-type fail-safe."""
    sentences = []
    sentences.append(triage([]).sentence)
    sentences.append(triage([{"id": "r1", "action_type": "reversible"}]).sentence)
    sentences.append(triage([
        {"id": "c1", "action_type": "consequential"},
        {"id": "c2", "action_type": "consequential"},
    ]).sentence)
    sentences.append(triage(
        [{"id": f"c{i}", "action_type": "consequential"} for i in range(1, 4)]
        + [{"id": f"r{i}", "action_type": "reversible"} for i in range(1, 9)]
    ).sentence)
    sentences.append(triage(
        [{"id": "r1", "action_type": "reversible"}, {"id": "r2", "action_type": "reversible"}],
        stopped=[{"id": "s1", "action_type": "reversible"}],
    ).sentence)
    sentences.append(triage(
        [{"id": "r1", "action_type": "reversible"}],
        stopped=[{"id": "s1", "action_type": "reversible"}, {"id": "s2", "action_type": "reversible"}],
    ).sentence)
    sentences.append(triage([{"id": "m1", "action_type": "mystery_type"}]).sentence)
    return sentences


def _phrases(text: str) -> list[str]:
    """clause-ish units, split on sentence and comma boundaries, so a
    "land" mid-string is checked against its own local subject rather than
    the whole string's leading word."""
    return [p.strip() for p in re.split(r"(?<=[.!?])\s+|(?<=,)\s+", text) if p.strip()]


def _assert_land_guard(text: str, where: str):
    for phrase in _phrases(text):
        if not LAND_RE.search(phrase):
            continue
        if phrase in LAND_GUARD_ALLOWLIST:
            continue
        assert phrase.startswith("you "), (
            f"land-guard: {where} phrase {phrase!r} does not open with "
            f"'you ' as the subject — machine acts say made/updated/done"
        )


# ---------- 1. land-guard ----------

def test_land_guard_owner_is_subject():
    for entry in LAND_GUARD_ALLOWLIST:
        assert entry.startswith("you "), "land-guard allowlist entries must open with 'you '"

    for set_name, table in _fusion_plain_sets().items():
        for key, value in table.items():
            if isinstance(value, str):
                _assert_land_guard(value, f"{set_name}[{key!r}]")

    for sentence in _representative_triage_sentences():
        _assert_land_guard(sentence, "a triage sentence")


def _surface_visible(html: str) -> str:
    """the text a person actually reads, with each tag boundary turned into a
    phrase break ('. ') so a land word is judged against ITS OWN text node's
    subject — never against a neighbour's leading word that tag-stripping would
    have glued on. scripts/styles dropped whole."""
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", ". ", html)


def test_land_guard_on_the_rendered_surfaces(tmp_path, monkeypatch):
    """the surface land-guard (M4, ruled): render the WALL and the BOARD with a
    fixture carrying a waiting ticket, a landed batch, a landed single, and a
    stopped run, then scan the visible text — every land word must sit in a
    phrase the owner opens ('you …'); a machine-subject 'landed' anywhere on
    either surface fails this test. deterministic, no timing, no network."""
    monkeypatch.setenv("COMMERCEOS_DB", str(tmp_path / "lint.db"))
    from fastapi.testclient import TestClient
    from commerceos.db import connect
    from commerceos.gate import gate, ledger
    from commerceos.catalog import runs as R, workflows as W, lifecycle as L
    from commerceos.spine import writes
    from commerceos.spine.schema import ensure_schema
    from commerceos.web.app import app
    from tests.test_catalog_workflows import FakeStore, seed_variant, VALID13
    from tests.test_catalog_delist import FakeClient

    c = connect(tmp_path / "lint.db")
    ensure_schema(c); ledger.ensure_schema(c); R.ensure_schema(c)
    client = TestClient(app)

    def add_product(pid, title):   # titles carry NO land word (fixture hygiene)
        c.execute("INSERT INTO products (shopify_id,handle,title,status,vendor,"
                  "product_type,tags,raw,source,fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (pid, f"h-{pid}", title, "ACTIVE", "V", "Flashlights", "[]",
                   "{}", "t", "2026-07-12T00:00:00Z"))
        c.commit()

    def submit_delist(pid):
        return gate.submit(c, {"agent": "catalog-delist",
            "function": "catalog-enrichment", "method": "mutate_product_state",
            "args": {"product_id": pid, "state": "delisted"},
            "declared_type": "consequential", "intent": "pull it",
            "rationale": "quality flag ruled", "provenance": [{"source": "q"}]})["record_id"]

    add_product("d0", "Trail Lantern"); submit_delist("d0")            # a wait
    seed_variant(c, "b1", "'" + VALID13); seed_variant(c, "b2", "'" + VALID13)
    loc = client.post("/catalog/run/gtin", follow_redirects=False).headers["location"]
    R.approve(c, loc.rsplit("/", 1)[1], W.GTIN, by="the desk", client=FakeStore())  # landed batch
    add_product("d1", "Camp Lantern"); L.set_initial(c, "d1", "ACTIVE")
    rid = submit_delist("d1")
    monkeypatch.setattr(writes, "ShopifyClient", lambda: FakeClient(status="ACTIVE"))
    client.post(f"/api/approvals/{rid}", data={"confirm": "true", "decision": "approved"},
                follow_redirects=False)                                 # landed single
    seed_variant(c, "s1", "'" + VALID13); seed_variant(c, "s2", "'" + VALID13)
    loc2 = client.post("/catalog/run/gtin", follow_redirects=False).headers["location"]

    class OneRaises(FakeStore):
        def graphql(self, q, v=None):
            if v and v.get("variants") and v["variants"][0]["id"] == "v-s2":
                raise RuntimeError("THROTTLED")
            return super().graphql(q, v)

    R.approve(c, loc2.rsplit("/", 1)[1], W.GTIN, by="the desk", client=OneRaises())  # stopped

    for path in ("/board/demostore", "/wall"):
        r = client.get(path)
        assert r.status_code == 200, path
        _assert_land_guard(_surface_visible(r.text), path)
    c.close()


# ---------- 2. fiction-collision ----------

def test_fiction_words_never_appear_on_the_fusion_register():
    fiction_re = re.compile(
        r"\b(" + "|".join(re.escape(w) for w in FICTION_WORDS) + r")\b", re.I
    )
    for set_name, table in _fusion_plain_sets().items():
        for key, value in table.items():
            if isinstance(value, str):
                m = fiction_re.search(value)
                assert not m, f"{set_name}[{key!r}] = {value!r} carries fiction word {m.group(0)!r}"

    for sentence in _representative_triage_sentences():
        m = fiction_re.search(sentence)
        assert not m, f"triage sentence {sentence!r} carries fiction word {m.group(0)!r}"


def test_the_wall_is_never_a_rendered_string():
    """"the wall" is spec vocabulary (spec/parts/collab-surface.md) for the
    page CS1 builds — never a string a person reads. CS1's masthead says
    "commerceos". checked against every rendered FUSION_*_PLAIN value and
    every triage sentence, not fusion.py's comments/docstrings (those may
    cite the spec name)."""
    for set_name, table in _fusion_plain_sets().items():
        for key, value in table.items():
            if isinstance(value, str):
                assert "the wall" not in value.lower(), (
                    f"{set_name}[{key!r}] = {value!r} renders the spec's internal page name"
                )
    for sentence in _representative_triage_sentences():
        assert "the wall" not in sentence.lower()


# ---------- 3. mirror-as-of ----------

def test_mirror_as_of_is_the_only_law():
    numberish = re.compile(r"health \d|\d+(?:\.\d+)?%")
    for set_name, table in _fusion_plain_sets().items():
        for key, value in table.items():
            if isinstance(value, str) and numberish.search(value):
                assert "as of" in value, (
                    f"{set_name}[{key!r}] = {value!r} is an audit-derived number missing its age"
                )

    src = inspect.getsource(fusion)
    aged_src = inspect.getsource(fusion.aged)
    assert "as of" in aged_src, "aged() must be the formatter that says \"as of\""
    assert src.count("as of") == aged_src.count("as of"), (
        "\"as of\" is concatenated somewhere in fusion.py outside aged() — "
        "one formatter, one law"
    )


# ---------- 4. roster guard ----------

def test_every_fusion_plain_set_is_on_the_roster():
    """copy of test_voice_register.py:61-68's drift guard: any module-level
    dict named the house convention (FUSION_*_PLAIN) in fusion.py's source
    is one this lint's roster (_fusion_plain_sets) actually sees."""
    src = inspect.getsource(fusion)
    named = set(re.findall(r"^(FUSION_[A-Z0-9_]*_PLAIN) = \{", src, re.M))
    discovered = set(_fusion_plain_sets())
    missing = named - discovered
    assert not missing, f"a FUSION_*_PLAIN set exists in fusion.py but isn't on this lint's roster: {missing}"
