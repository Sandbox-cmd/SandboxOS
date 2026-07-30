"""the rhythm's checks: the shipped config is all-disabled (nothing arms
itself); the due math holds; a tick runs the job registry — the config's
rows in row order, expire_sweep first, "calls" resolving against the
built-ins with the row's own name as the default — and one failure (or
one refused row) never stops the others, every outcome recorded; every
job gets the tick's own config, never a re-read of the default path;
push is notify-only — skipped honestly when ntfy is unconfigured, POSTed
when configured; arm's dry run writes NOTHING, --yes (the owner's
keystroke) writes the plist, --disarm removes it."""

import json
import plistlib
import shutil
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from commerceos.db import connect
from commerceos.gate import gate, ledger
from commerceos.rhythm import arm, notify, runner
from commerceos.rhythm import status as rhythm_status
from commerceos.watching import findings
from commerceos.web import registry

REPO = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO / "stores" / "demostore" / "rhythm.json"

NOW = datetime(2026, 7, 11, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "rhythm.db")
    yield c
    c.close()


@pytest.fixture()
def fake_home(monkeypatch, tmp_path):
    """a tmp HOME so plist reads/writes never touch the real LaunchAgents."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture()
def tmp_config(tmp_path):
    p = tmp_path / "rhythm.json"
    shutil.copyfile(CONFIG_PATH, p)
    return p


def enabled_config(**cadences):
    cfg = json.loads(CONFIG_PATH.read_text())
    for name, jcfg in runner.job_configs(cfg).items():
        jcfg["enabled"] = True
        if name in cadences:
            jcfg["cadence"] = cadences[name]
    return cfg


def fake_jobs(calls, fail=()):
    def make(name):
        def job(conn, jcfg):
            calls.append(name)
            if name in fail:
                raise RuntimeError(f"{name} broke")
            return {"summary": f"{name} ran"}
        return job
    return {n: make(n) for n in runner.BUILTIN_JOBS}


class FakeUrlopen:
    """captures every Request; answers 200."""

    def __init__(self):
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req)

        class R:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return R()


# ---------- config: shipped disarmed, parseable ----------

def test_config_is_parseable_and_arming_is_a_boolean_choice():
    # the shipped default is all-disabled; the OWNER may have armed the live
    # file (his keystroke — 2026-07-11 he did). the law this test holds is
    # structural: every job carries an explicit boolean enabled and a valid
    # cadence; arming happens only through arm.py (covered by the arm tests).
    cfg = runner.load_config()
    jobs = runner.job_configs(cfg)
    assert set(jobs) == {"expire_sweep", "sync", "propose", "audit", "evaluate", "analyst"}
    assert jobs["analyst"]["enabled"] is False  # F3 ships disabled; arming is the owner's
    for jcfg in jobs.values():
        assert isinstance(jcfg["enabled"], bool)
        assert runner.parse_cadence(jcfg["cadence"]) > 0
    ntfy = cfg["ntfy"]
    assert ntfy["server"] is None and ntfy["topic"] is None  # never a third-party default


def test_demostore_ships_the_audit_row_disabled_and_resolvable():
    # UI-polish's cadence half: the audit row already exists in the shipped
    # config, disabled — this build pins it as law and reads it at render; it
    # never flips enabled (arming is the owner's keystroke, runner.py:13-17).
    cfg = json.loads(CONFIG_PATH.read_text())
    jobs = runner.job_configs(cfg)
    row = jobs["audit"]
    assert row["enabled"] is False
    assert runner.parse_cadence(row["cadence"]) > 0
    assert "calls" not in row               # nothing names a callable —
    assert runner.resolve_job("audit", row) is runner._job_audit  # the F2
    # defaulting rule resolves the row's own name to its built-in.


# ---------- due math ----------

def test_cadence_parses_minutes_hours_days_and_refuses_the_rest():
    assert runner.parse_cadence("15m") == 900
    assert runner.parse_cadence("6h") == 6 * 3600
    assert runner.parse_cadence("24h") == 86400
    assert runner.parse_cadence("2d") == 2 * 86400
    for bad in ("", "6", "h6", "6x", "-6h", "1.5h", "0m"):
        with pytest.raises(ValueError):
            runner.parse_cadence(bad)


def test_due_math():
    assert runner.is_due(None, 3600, NOW) is True  # never ran -> due
    five_h_ago = (NOW - timedelta(hours=5)).isoformat(timespec="seconds")
    six_h_ago = (NOW - timedelta(hours=6)).isoformat(timespec="seconds")
    assert runner.is_due(five_h_ago, 6 * 3600, NOW) is False
    assert runner.is_due(six_h_ago, 6 * 3600, NOW) is True  # exactly one cadence -> due
    assert runner.next_due(None, 3600) is None  # due now
    assert runner.next_due("2026-07-11T06:00:00+00:00", 6 * 3600) == "2026-07-11T12:00:00+00:00"


# ---------- tick ----------

def test_tick_with_a_disarmed_config_runs_nothing(conn, fake_home):
    calls = []
    cfg = runner.load_config()
    for jcfg in runner.job_configs(cfg).values():
        jcfg["enabled"] = False  # the disarmed shape, whatever the live file says
    out = runner.tick(conn, cfg, now=NOW, jobs=fake_jobs(calls))
    assert calls == []
    assert all(r["ran"] is False and "disabled" in r["why"] for r in out["results"].values())


def test_tick_runs_due_jobs_in_order_and_a_failure_stops_nothing(conn, fake_home):
    calls = []
    out = runner.tick(conn, enabled_config(), now=NOW, jobs=fake_jobs(calls, fail={"sync"}))
    assert calls == ["expire_sweep", "sync", "propose", "audit", "evaluate", "analyst"]  # the config's row order, all attempted
    assert out["failed"] == ["sync"]
    state = runner.state_rows(conn)
    assert state["sync"]["ok"] == 0 and "sync broke" in state["sync"]["error"]
    for name in ("expire_sweep", "audit", "evaluate", "analyst"):
        assert state[name]["ok"] == 1
        assert state[name]["last_run"] == NOW.isoformat(timespec="seconds")
    assert state["tick"]["ok"] == 0 and "sync" in state["tick"]["error"]
    # every orchestrated part's registry row refreshed, plus the rhythm's own
    parts = {p["part"]: p for p in registry.all_parts(conn)}
    assert {"rhythm", "data-spine", "gate-and-record", "catalog-loop", "watching"} <= set(parts)
    assert parts["rhythm"]["state"] == "disarmed"  # no plist under the tmp HOME


def test_second_tick_respects_each_jobs_cadence(conn, fake_home):
    calls = []
    cfg = enabled_config()  # expire_sweep 15m · sync 6h · propose 1h · audit 24h · evaluate 6h · analyst 1d
    runner.tick(conn, cfg, now=NOW, jobs=fake_jobs(calls))
    assert len(calls) == 6
    runner.tick(conn, cfg, now=NOW + timedelta(minutes=5), jobs=fake_jobs(calls))
    assert len(calls) == 6  # five minutes later nothing is due
    out = runner.tick(conn, cfg, now=NOW + timedelta(minutes=20), jobs=fake_jobs(calls))
    assert calls == ["expire_sweep", "sync", "propose", "audit", "evaluate", "analyst",
                     "expire_sweep"]
    assert "not due until" in out["results"]["sync"]["why"]


def test_run_one_is_the_owners_keystroke_ignores_enabled_and_due(conn, fake_home):
    calls = []
    out = runner.run_one(conn, "audit", runner.load_config(), now=NOW, jobs=fake_jobs(calls))
    assert calls == ["audit"] and out["ok"] is True  # disabled in config; runs by hand anyway
    assert runner.state_rows(conn)["audit"]["ok"] == 1
    with pytest.raises(ValueError):
        runner.run_one(conn, "nonsense", runner.load_config(), jobs=fake_jobs(calls))


def test_cli_run_records_a_real_failed_job_honestly(tmp_path, fake_home):
    db = tmp_path / "cli.db"
    rc = runner.main(["run", "audit", "--db", str(db)])
    assert rc == 1  # empty store: the audit fails closed ("no landed products")
    c = connect(db)
    try:
        row = runner.state_rows(c)["audit"]
        assert row["ok"] == 0 and "no landed products" in row["error"]
    finally:
        c.close()


# ---------- the job registry (spec/parts/fleet.md behavior 1) ----------

def test_registry_runs_config_rows_in_row_order_expire_sweep_first(conn, fake_home):
    # row order is the run order — except expire_sweep, written last here,
    # still runs first: stale approvals flip before anything reads the queue.
    calls = []
    cfg = {"jobs": {
        "evaluate": {"cadence": "15m", "enabled": True},
        "sync": {"cadence": "15m", "enabled": True},
        "expire_sweep": {"cadence": "15m", "enabled": True},
    }}
    out = runner.tick(conn, cfg, now=NOW, jobs=fake_jobs(calls))
    assert calls == ["expire_sweep", "evaluate", "sync"]
    assert out["failed"] == []


def test_a_row_naming_no_known_job_is_refused_loudly_and_stops_nothing(conn, fake_home):
    # "theme" has no built-in yet (F4 adds it) and names no callable:
    # the row is refused — recorded, counted failed — and the jobs before
    # and after it still run.
    calls = []
    cfg = {"jobs": {
        "expire_sweep": {"cadence": "15m", "enabled": True},
        "theme": {"cadence": "15m", "enabled": True},
        "evaluate": {"cadence": "15m", "enabled": True},
    }}
    out = runner.tick(conn, cfg, now=NOW, jobs=fake_jobs(calls))
    assert calls == ["expire_sweep", "evaluate"]  # the refusal stopped nothing
    assert out["results"]["theme"]["refused"] is True
    assert "theme" in out["failed"]
    state = runner.state_rows(conn)
    assert state["theme"]["ok"] == 0 and "refused" in state["theme"]["error"]
    assert state["tick"]["ok"] == 0 and "theme" in state["tick"]["error"]


def test_a_disabled_unknown_row_waits_quietly(conn, fake_home):
    # the pre-landing shape (analyst rode it into F3): a per-agent row lands
    # in the config before its built-in exists. disabled, it skips honestly —
    # no refusal screamed every tick.
    cfg = {"jobs": {"theme": {"cadence": "15m", "enabled": False}}}
    out = runner.tick(conn, cfg, now=NOW, jobs=fake_jobs([]))
    assert "disabled" in out["results"]["theme"]["why"]
    assert out["failed"] == [] and "theme" not in runner.state_rows(conn)


def test_the_live_demostore_config_ticks_unchanged_via_the_defaulting_rule(conn, fake_home):
    # the real file, read-only: no row names a callable, so every row
    # defaults to the built-in of its own name — the defaulting rule is
    # why this config keeps ticking exactly as before the registry.
    cfg = json.loads(CONFIG_PATH.read_text())
    rows = runner.registry_rows(cfg)
    assert [n for n, _ in rows] == ["expire_sweep", "sync", "propose", "audit",
                                    "evaluate", "analyst"]
    for name, jcfg in rows:
        assert "calls" not in jcfg
        assert runner.resolve_job(name, jcfg) is runner.BUILTIN_JOBS[name]
    for jcfg in runner.job_configs(cfg).values():
        jcfg["enabled"] = True  # in memory only; the file is never written
    calls = []
    out = runner.tick(conn, cfg, now=NOW, jobs=fake_jobs(calls))
    assert calls == ["expire_sweep", "sync", "propose", "audit", "evaluate", "analyst"]
    assert out["failed"] == []


def test_a_tick_never_rereads_the_default_config_and_propose_uses_its_row(
        conn, fake_home, monkeypatch):
    # the cross-store leak, closed: every job works from the config the
    # tick was given. propose's kind and batch come from its own row.
    from commerceos.fleet import proposer

    def no_default_read(*a, **k):
        raise AssertionError("a job re-read the default config path — the tick's config is the law")
    monkeypatch.setattr(runner, "load_config", no_default_read)

    seen = {}

    def fake_propose(conn_, kind, limit=50, client=None):
        seen.update(kind=kind, limit=limit)
        return {"executed": 1, "parked": 0, "failed": 0, "computed": 1}
    monkeypatch.setattr(proposer, "propose_and_run", fake_propose)

    cfg = {"jobs": {"propose": {"cadence": "15m", "enabled": True,
                                "kind": "title_fix", "batch": 7}}}
    out = runner.tick(conn, cfg, now=NOW)  # jobs=None: the real built-ins run
    assert out["results"]["propose"]["ran"] is True and out["failed"] == []
    assert seen == {"kind": "title_fix", "limit": 7}


def test_a_custom_row_calls_a_builtin_by_name(conn, fake_home):
    # the per-agent seam: a row's "calls" key picks the callable; the row's
    # own name is only the default. state is recorded under the row's name.
    calls = []
    cfg = {"jobs": {"nightly_sweep": {"cadence": "15m", "enabled": True,
                                      "calls": "expire_sweep"}}}
    out = runner.tick(conn, cfg, now=NOW, jobs=fake_jobs(calls))
    assert calls == ["expire_sweep"]
    assert out["results"]["nightly_sweep"]["ran"] is True
    assert runner.state_rows(conn)["nightly_sweep"]["ok"] == 1
    # and against the real map, without the test override
    assert runner.resolve_job("nightly_sweep", {"calls": "propose"}) \
        is runner.BUILTIN_JOBS["propose"]


# ---------- notify ----------

def test_notify_skips_honestly_when_unconfigured(monkeypatch, capsys):
    def wire(*a, **k):
        raise AssertionError("no wire may be touched while ntfy is unconfigured")
    monkeypatch.setattr(urllib.request, "urlopen", wire)
    assert notify.send({"server": None, "topic": None}, "t", "m") is False
    out = capsys.readouterr().out
    assert "skipped" in out and "unconfigured" in out


def test_notify_posts_to_the_configured_server(monkeypatch):
    fake = FakeUrlopen()
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    ntfy = {"server": "http://ntfy.local:8090", "topic": "demostore-private",
            "link_base": "http://brain.local:8000"}
    assert notify.pending_approvals(ntfy, new=2, waiting=3) is True
    req = fake.requests[0]
    assert req.full_url == "http://ntfy.local:8090/demostore-private"
    assert req.get_method() == "POST"
    assert "2 new approvals" in req.get_header("Title")
    assert req.get_header("Click") == "http://brain.local:8000/approvals"
    assert b"3 waiting" in req.data


def test_notify_builders_carry_the_item_and_a_link_never_the_decision(monkeypatch):
    fake = FakeUrlopen()
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    ntfy = {"server": "http://n", "topic": "t"}
    notify.job_failed(ntfy, "sync", "RuntimeError: wire down")
    notify.risk_finding(ntfy, ["return-rate at 0.18 is above the 0.12 edge for 2026-07"])
    failed_req, risk_req = fake.requests
    assert failed_req.get_header("Click") == notify.DEFAULT_LINK_BASE + "/parts"
    assert risk_req.get_header("Click") == notify.DEFAULT_LINK_BASE + "/findings"
    for req in (failed_req, risk_req):  # notify-only: no approve verb, no decision payload
        assert b"approve" not in req.data.lower()


def test_notify_wire_failure_never_raises(monkeypatch, capsys):
    def down(*a, **k):
        raise OSError("connection refused")
    monkeypatch.setattr(urllib.request, "urlopen", down)
    assert notify.send({"server": "http://n", "topic": "t"}, "t", "m") is False
    assert "failed" in capsys.readouterr().out


def test_tick_pushes_failures_new_pending_and_new_risks_once(conn, fake_home, monkeypatch):
    fake = FakeUrlopen()
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    cfg = enabled_config()
    cfg["ntfy"] = {"server": "http://ntfy.local", "topic": "demostore",
                   "link_base": "http://brain:8000"}
    # a consequential proposal parks pending on the ledger (minted before this tick)
    ledger.ensure_schema(conn)
    gate.submit(conn, {
        "agent": "pricing-draft", "function": "pricing", "method": "mutate_price",
        "args": {"product_id": "gid://x/1", "variant_id": "v1", "price": "180.00"},
        "declared_type": "consequential", "intent": "reprice test variant",
        "rationale": "rhythm push test",
    }, now_ts=NOW - timedelta(minutes=5))
    # a risk finding noticed before this tick
    findings.mint(conn, "return-rate above the 0.12 band", "risk",
                  {"evaluations": [1]}, now=NOW - timedelta(minutes=1))

    calls = []
    out = runner.tick(conn, cfg, now=NOW, jobs=fake_jobs(calls, fail={"audit"}))
    clicks = [r.get_header("Click") for r in fake.requests]
    assert "http://brain:8000/parts" in clicks       # the failed job
    assert "http://brain:8000/approvals" in clicks   # the pending approval, count + deep link
    assert "http://brain:8000/findings" in clicks    # the new risk finding
    assert out["notifications"]["sent"] == 3

    # the next tick sees nothing new: no repeat pushes for the same items
    seen = len(fake.requests)
    runner.tick(conn, cfg, now=NOW + timedelta(minutes=20), jobs=fake_jobs(calls))
    new_clicks = [r.get_header("Click") for r in fake.requests[seen:]]
    assert not any(c.endswith(("/approvals", "/findings")) for c in new_clicks)


# ---------- arm: nothing arms itself ----------

def test_arm_dry_run_writes_nothing(fake_home, tmp_config, monkeypatch, capsys):
    def no_launchctl(*a, **k):
        raise AssertionError("a dry run must not touch launchctl")
    monkeypatch.setattr(arm.subprocess, "run", no_launchctl)
    before = tmp_config.read_text()
    rc = arm.main(["--config", str(tmp_config)])
    assert rc == 0
    assert not arm.plist_path().exists()
    assert not (fake_home / "Library").exists()      # not even the directory
    assert tmp_config.read_text() == before          # config untouched
    out = capsys.readouterr().out
    assert "--yes" in out and "dry run" in out
    assert arm.label() in out and "StartInterval" in out  # the active store's own label


def _fake_launchctl(record):
    def run(cmd, **kwargs):
        record.append(list(cmd))

        class P:
            returncode = 0
            stdout = ""
            stderr = ""

        return P()
    return run


def test_arm_yes_writes_the_plist_and_enables_the_jobs(fake_home, tmp_config, monkeypatch):
    launchctl_calls = []
    monkeypatch.setattr(arm.subprocess, "run", _fake_launchctl(launchctl_calls))
    rc = arm.main(["--yes", "--config", str(tmp_config)])
    assert rc == 0
    p = arm.plist_path()
    assert p.exists() and str(p).startswith(str(fake_home))
    plist = plistlib.loads(p.read_bytes())  # valid XML or launchd would refuse it
    assert plist["Label"] == arm.label()
    assert plist["StartInterval"] == arm.TICK_EVERY_SECONDS
    assert plist["RunAtLoad"] is False
    command = plist["ProgramArguments"][-1]
    assert command == (
        f"cd {runner.REPO} && COMMERCEOS_STORE=demostore"
        f" uv run python -m commerceos.rhythm.runner tick"
    )  # the armed process is pinned to its store (behavior 5)
    cfg = json.loads(tmp_config.read_text())
    assert all(j["enabled"] is True for j in runner.job_configs(cfg).values())
    assert any("bootstrap" in c for c in launchctl_calls)


def test_disarm_removes_the_plist_and_disables_the_jobs(fake_home, tmp_config, monkeypatch):
    launchctl_calls = []
    monkeypatch.setattr(arm.subprocess, "run", _fake_launchctl(launchctl_calls))
    arm.main(["--yes", "--config", str(tmp_config)])
    assert arm.plist_path().exists()
    rc = arm.main(["--disarm", "--config", str(tmp_config)])
    assert rc == 0
    assert not arm.plist_path().exists()
    cfg = json.loads(tmp_config.read_text())
    assert all(j["enabled"] is False for j in runner.job_configs(cfg).values())
    assert any("bootout" in c for c in launchctl_calls)


# ---------- the registry row ----------

def test_status_row_reports_armed_state_next_due_and_ntfy(conn, fake_home):
    cfg = enabled_config()
    runner.record_run(conn, "sync", (NOW - timedelta(hours=2)).isoformat(timespec="seconds"),
                      True, "landed")
    rhythm_status.report_status(conn, cfg, now=NOW)
    row = {p["part"]: p for p in registry.all_parts(conn)}["rhythm"]
    assert row["state"] == "disarmed"
    jobs = row["last_run"]["jobs"]
    assert jobs["sync"]["next_due"] == (NOW + timedelta(hours=4)).isoformat(timespec="seconds")
    assert jobs["audit"]["next_due"] == "next tick"  # enabled, never ran
    assert row["last_run"]["ntfy_configured"] is False
    assert row["next_run"] is None  # disarmed: no heartbeat, no next run

    # the plist present under HOME is the armed fact
    p = arm.plist_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("plist")
    rhythm_status.report_status(conn, cfg, now=NOW)
    row = {p_["part"]: p_ for p_ in registry.all_parts(conn)}["rhythm"]
    assert row["state"] == "armed"
    assert row["next_run"] is not None
