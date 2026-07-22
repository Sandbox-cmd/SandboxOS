"""M4's mechanism checks (spec/parts/multi-store.md behavior 2 + 5): one
launchd label per store, the armed process pinned to its store by
COMMERCEOS_STORE; arming disarms the legacy single-store label first and
says so; arming one store never touches another store's plist; the
registry writer registers (never as default) and stamps ceremony steps,
refusing unknown stores and unknown steps."""

import json
import plistlib
from pathlib import Path

import pytest

from commerceos import stores
from commerceos.rhythm import arm


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("COMMERCEOS_STORE", "COMMERCEOS_DB", "COMMERCEOS_POLICY_TABLE"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def tmp_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / "Library" / "LaunchAgents").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


@pytest.fixture()
def no_launchctl(monkeypatch):
    calls = []

    def fake(args, capture_output=True, text=True):
        calls.append(args)

        class P:
            returncode = 3  # launchctl's "not loaded" answer
            stdout = ""
            stderr = ""

        return P()

    monkeypatch.setattr(arm.subprocess, "run", fake)
    return calls


def write_registry(root, rows):
    (root / "stores").mkdir(parents=True, exist_ok=True)
    (root / "stores" / "registry.json").write_text(json.dumps({"stores": rows}))


# -- per-store labels --


def test_one_label_per_store():
    assert arm.label("demostore") == "com.commerceos.demostore.rhythm"
    assert arm.label("scaffold") == "com.commerceos.scaffold.rhythm"
    assert arm.label("demostore") != arm.LEGACY_LABEL


def test_plist_pins_the_store_and_its_own_log():
    content = arm.plist_content("scaffold")
    parsed = plistlib.loads(content.encode())
    assert parsed["Label"] == "com.commerceos.scaffold.rhythm"
    command = parsed["ProgramArguments"][2]
    assert "COMMERCEOS_STORE=scaffold" in command
    assert parsed["StandardOutPath"].endswith("scaffold.rhythm.log")
    assert parsed["RunAtLoad"] is False


def test_arming_one_store_never_touches_anothers_plist(tmp_home, no_launchctl, tmp_path):
    other = arm.plist_path("demostore")
    other.write_text("demostore's schedule — hands off")
    cfg = tmp_path / "rhythm.json"
    cfg.write_text(json.dumps({"store": "scaffold", "jobs": {}}))
    arm.arm(config_path=cfg, store="scaffold")
    assert arm.plist_path("scaffold").exists()
    assert other.read_text() == "demostore's schedule — hands off"


# -- the legacy sweep --


def test_arming_disarms_a_legacy_plist_first(tmp_home, no_launchctl, tmp_path, capsys):
    legacy = tmp_home / "Library" / "LaunchAgents" / f"{arm.LEGACY_LABEL}.plist"
    legacy.write_text("the orphan that must not keep ticking")
    cfg = tmp_path / "rhythm.json"
    cfg.write_text(json.dumps({"store": "scaffold", "jobs": {}}))
    arm.arm(config_path=cfg, store="scaffold")
    assert not legacy.exists()
    assert "legacy plist removed" in capsys.readouterr().out
    assert any(f"gui/{arm.os.getuid()}/{arm.LEGACY_LABEL}" in " ".join(c) for c in no_launchctl)


def test_legacy_sweep_reports_honestly_when_nothing_found(tmp_home, no_launchctl, capsys):
    assert arm.disarm_legacy() is False
    assert "nothing to disarm" in capsys.readouterr().out


# -- the registry writer --


def test_register_adds_a_row_never_the_default(tmp_path):
    write_registry(tmp_path, [{"name": "demostore", "default": True}])
    stores.register_store("scaffold", "Scaffold", tmp_path)
    reg = stores.load_registry(tmp_path)
    row = next(r for r in reg["stores"] if r["name"] == "scaffold")
    assert row.get("label") == "Scaffold"
    assert not row.get("default")
    assert stores.default_store(tmp_path) == "demostore"


def test_register_refuses_a_known_name(tmp_path):
    write_registry(tmp_path, [{"name": "demostore", "default": True}])
    with pytest.raises(ValueError, match="already registered"):
        stores.register_store("demostore", "Again", tmp_path)


def test_stamps_accumulate_on_the_row(tmp_path):
    write_registry(tmp_path, [{"name": "demostore", "default": True}, {"name": "scaffold"}])
    stores.stamp_step("scaffold", "config", "2026-07-19T00:00:00+00:00", tmp_path)
    stores.stamp_step("scaffold", "register", "2026-07-19T00:01:00+00:00", tmp_path)
    row = next(
        r for r in stores.load_registry(tmp_path)["stores"] if r["name"] == "scaffold"
    )
    assert row["onboarding"] == {
        "config": "2026-07-19T00:00:00+00:00",
        "register": "2026-07-19T00:01:00+00:00",
    }


def test_stamp_refuses_unknown_store_and_unknown_step(tmp_path):
    write_registry(tmp_path, [{"name": "demostore", "default": True}])
    with pytest.raises(ValueError, match="register it first"):
        stores.stamp_step("nope", "config", "2026-07-19T00:00:00+00:00", tmp_path)
    with pytest.raises(ValueError, match="unknown ceremony step"):
        stores.stamp_step("demostore", "vibes", "2026-07-19T00:00:00+00:00", tmp_path)
