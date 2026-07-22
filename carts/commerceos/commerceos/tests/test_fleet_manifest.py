"""F1's checks: the fleet manifest reader + the roster surface.

the ruling (2026-07-18), encoded: the `.claude/agents/` frontmatter ALONE
is the manifest — the reader parses the real files, a malformed file is
refused loudly (named, never silently skipped), the track record is
computed from the ledger at render time, and the /fleet page renders
every agent from its file. no duplicate config row anywhere.
"""

import pytest
from fastapi.testclient import TestClient

from commerceos.db import connect
from commerceos.fleet import manifest
from commerceos.gate import ledger
from commerceos.web.app import app


# --- the reader over the real files -----------------------------------------

def test_roster_reads_the_real_agent_files():
    agents = manifest.roster()
    names = [m["name"] for m in agents]
    assert names == ["analyst", "catalog-proposer", "content", "spec-verifier"]
    for m in agents:
        for key in manifest.REQUIRED:
            assert m[key], f"{m['name']}: {key} missing or empty"
        assert m["status"] in manifest.STATUSES
        for fn in m["functions"]:
            assert fn["autonomy"] in manifest.AUTONOMY
        assert m["body"], f"{m['name']}: an agent file carries a plain body"
    by_name = {m["name"]: m for m in agents}
    # all four exist in code now — the files (the ruled source of truth)
    # say built, matching reality (analyst + content landed 2026-07-18).
    assert by_name["catalog-proposer"]["status"] == "built"
    assert by_name["spec-verifier"]["status"] == "built"
    assert by_name["analyst"]["status"] == "built"
    assert by_name["content"]["status"] == "built"
    # the ruled autonomy shape: analyst never writes a store; content parks
    # customer-facing claims; the proposer's reversible work acts.
    assert by_name["analyst"]["functions"] == [
        {"name": "pattern-hunts", "autonomy": "proposes-only"}]
    assert {f["name"]: f["autonomy"] for f in by_name["content"]["functions"]} == {
        "listing-text": "acts", "customer-facing-claims": "parks"}
    assert {f["name"]: f["autonomy"] for f in by_name["catalog-proposer"]["functions"]} == {
        "barcode-repair": "acts", "publish-state": "parks"}


def test_manifest_names_match_the_code_constants():
    """the ledger's agent names come from these module constants — the files
    must carry the same names or the track record counts nothing."""
    from commerceos.catalog import verify_sources
    from commerceos.fleet import proposer
    names = {m["name"] for m in manifest.roster()}
    assert proposer.AGENT in names
    assert verify_sources.AGENT in names


# --- malformed files are refused loudly -------------------------------------

def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return p


def test_missing_required_keys_are_refused_loudly(tmp_path):
    _write(tmp_path, "half.md",
           "---\nname: half\ndescription: d\nstatus: built\n---\nbody\n")
    with pytest.raises(manifest.ManifestError) as e:
        manifest.roster(tmp_path)
    assert "half.md" in str(e.value) and "missing required keys" in str(e.value)


def test_a_name_filename_mismatch_is_refused(tmp_path):
    _write(tmp_path, "alias.md",
           "---\nname: other\ndescription: d\nscope: s\nwriter_class: w\n"
           "status: built\nfunctions:\n  - work: acts\n---\nbody\n")
    with pytest.raises(manifest.ManifestError, match="does not match the filename"):
        manifest.roster(tmp_path)


def test_an_unknown_autonomy_or_status_is_refused(tmp_path):
    _write(tmp_path, "wild.md",
           "---\nname: wild\ndescription: d\nscope: s\nwriter_class: w\n"
           "status: built\nfunctions:\n  - work: freely\n---\nbody\n")
    with pytest.raises(manifest.ManifestError, match="autonomy"):
        manifest.read_manifest(tmp_path / "wild.md")
    _write(tmp_path, "soon.md",
           "---\nname: soon\ndescription: d\nscope: s\nwriter_class: w\n"
           "status: planned\nfunctions:\n  - work: acts\n---\nbody\n")
    with pytest.raises(manifest.ManifestError, match="status"):
        manifest.read_manifest(tmp_path / "soon.md")


def test_non_key_value_lines_and_unclosed_fences_are_refused(tmp_path):
    _write(tmp_path, "loose.md",
           "---\nname: loose\njust some prose\n---\nbody\n")
    with pytest.raises(manifest.ManifestError, match="strict"):
        manifest.read_manifest(tmp_path / "loose.md")
    _write(tmp_path, "open.md", "---\nname: open\n")
    with pytest.raises(manifest.ManifestError, match="never closes"):
        manifest.read_manifest(tmp_path / "open.md")
    _write(tmp_path, "bare.md", "name: bare\n")
    with pytest.raises(manifest.ManifestError, match="fence"):
        manifest.read_manifest(tmp_path / "bare.md")


# --- the track record, computed from the ledger -----------------------------

@pytest.fixture()
def env(tmp_path, monkeypatch):
    db = tmp_path / "fleet.db"
    monkeypatch.setenv("COMMERCEOS_DB", str(db))
    conn = connect(db)
    ledger.ensure_schema(conn)
    yield conn, TestClient(app)
    conn.close()


def _mint(conn, agent, status="pending", **extra):
    rec = {
        "agent": agent, "function": "catalog-enrichment",
        "action_type": "reversible", "intent": "t",
        "proposal": {"connector": "commerce", "method": "mutate_variant_field",
                     "args": {}, "args_hash": "h", "declared_type": "reversible"},
        "status": status,
    }
    if status == "approved":
        rec["gate"] = {"required": False, "decision": "approved",
                       "by": "policy:auto", "ts": ledger.now()}
    rec.update(extra)
    return ledger.mint(conn, rec)


def test_track_record_computes_from_seeded_ledger_rows(env):
    conn, _ = env
    # one approved and executed, one rejected, one live wait, one lapsed wait
    rid = _mint(conn, "catalog-proposer", status="approved")
    ledger.begin_execution(conn, rid)
    ledger.fill_outcome(conn, rid, {"ok": True}, "executed")
    ledger.resolve_gate(conn, _mint(conn, "catalog-proposer"), "rejected", by="owner")
    _mint(conn, "catalog-proposer")
    _mint(conn, "catalog-proposer", expires_at="2026-01-01T00:00:00+00:00")
    # a REVERSAL: a record whose proposal marks reverts:<id> — undone after
    # execution, the number autonomy widening rests on
    rev = _mint(conn, "catalog-proposer", status="approved",
                proposal={"connector": "commerce", "method": "mutate_variant_field",
                          "args": {}, "args_hash": "h-back", "declared_type": "reversible",
                          "reverts": rid})
    ledger.begin_execution(conn, rev)
    ledger.fill_outcome(conn, rev, {"ok": True}, "executed")
    _mint(conn, "someone-else")   # never counted for this agent
    tr = manifest.track_record(conn, "catalog-proposer")
    assert tr == {"proposals": 5, "approved": 2, "executed": 2, "rejected": 1,
                  "reversed": 1, "pending": 1, "lapsed": 1}
    assert manifest.track_record(conn, "analyst") == {
        "proposals": 0, "approved": 0, "executed": 0, "rejected": 0,
        "reversed": 0, "pending": 0, "lapsed": 0}


# --- the roster surface -----------------------------------------------------

def test_the_roster_page_renders_every_manifest_agent(env):
    conn, client = env
    _mint(conn, "catalog-proposer")
    page = client.get("/fleet")
    assert page.status_code == 200
    for m in manifest.roster():
        assert m["name"] in page.text, f"{m['name']} missing from the roster page"
        assert m["scope"] in page.text
    # autonomy and status in plain words, and the live count from the ledger
    assert "waits for your call in decisions" in page.text
    assert "acts on its own" in page.text
    assert "built and working" in page.text
    # the track record renders REVERSED (undone after execution — the number
    # widening rests on), never the gate's turned-down count; every figure
    # opens to the record filtered to the agent, and a live wait opens to
    # decisions.
    assert ">1</a> proposal made" in page.text
    assert "reversed" in page.text and "turned down" not in page.text
    assert "/record?agent=catalog-proposer" in page.text
    assert "waiting on your call in decisions" in page.text
    # each card carries its last run and next armed run, honestly
    assert "no run on the record yet" in page.text
    assert "not armed" in page.text
    # widening is wired (FW1) and the page names its law plainly
    assert "recorded rule change" in page.text
    # the planned rest of the roster is one honest footer, not fake cards —
    # and the dropped ads agent stays visible in one line, never invisible
    assert "8 more planned agents" in page.text
    assert "ads agent" in page.text and "dropped" in page.text
    # the masthead announces the fleet's own page number, matching its blocks
    assert "p510" in page.text
    # reachable from the system page — no dead ends
    assert "/fleet" in client.get("/parts").text


def test_the_record_filters_by_agent(env):
    """the agent→record path: /record carries a who column and an ?agent=
    filter — the fleet page's track-record figures land here."""
    conn, client = env
    _mint(conn, "catalog-proposer")
    _mint(conn, "someone-else")
    page = client.get("/record")
    assert "catalog-proposer" in page.text and "someone-else" in page.text
    page = client.get("/record?agent=catalog-proposer")
    assert "acts by" in page.text and "see everything" in page.text
    assert "catalog-proposer" in page.text and "someone-else" not in page.text
    # a filter with no rows says so plainly, never an empty table
    none = client.get("/record?agent=nobody")
    assert "no acts by nobody" in none.text
