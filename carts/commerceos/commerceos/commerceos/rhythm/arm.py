"""arming — the owner's keystroke, and nothing else.

the law (spec/build.md standing constraints): nothing arms itself —
scheduled/autonomous runs start owner-armed. this module is the
mechanism only. without --yes it is a dry run: it prints the current
state, the exact plist --yes would write, and the exact commands —
and writes nothing. --yes (typed by the owner) writes the launchd
plist under ~/Library/LaunchAgents, loads it, and flips every job's
enabled flag in the store's rhythm.json. --disarm unloads, removes the
plist, and flips the flags back to false.

the tick fires every 15 minutes; each job then gates itself by its own
cadence in rhythm.json — arming sets the heartbeat, the config sets
the clocks.

  uv run python -m commerceos.rhythm.arm            # dry run: state + exact steps
  uv run python -m commerceos.rhythm.arm --yes      # arm (the owner's keystroke)
  uv run python -m commerceos.rhythm.arm --disarm   # unload + remove
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

from commerceos import stores
from commerceos.rhythm import notify, runner

# the pre-multi-store label (one schedule, no store name). arming any store
# disarms it first if found — an orphaned plist must not keep ticking the
# default config against whatever the default then resolves to (M4).
LEGACY_LABEL = "com.commerceos.rhythm"
TICK_EVERY_SECONDS = 900  # 15 minutes; the jobs gate themselves by their own cadence


def label(store: str | None = None) -> str:
    """one launchd label per store: com.commerceos.<store>.rhythm."""
    return f"com.commerceos.{store or stores.active_store()}.rhythm"


def plist_path(store: str | None = None) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{label(store)}.plist"


def plist_content(store: str | None = None) -> str:
    """the exact plist --yes writes. RunAtLoad is false: arming installs
    the schedule; it does not fire a run the owner didn't type. the armed
    process is pinned to its store by COMMERCEOS_STORE (behavior 5); the
    command is XML-escaped (the && would otherwise break the plist)."""
    store = store or stores.active_store()
    command = escape(
        f"cd {runner.REPO} && COMMERCEOS_STORE={store}"
        f" uv run python -m commerceos.rhythm.runner tick"
    )
    log = escape(str(runner.REPO / "data" / f"{store}.rhythm.log"))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{label(store)}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>{command}</string>
  </array>
  <key>StartInterval</key>
  <integer>{TICK_EVERY_SECONDS}</integer>
  <key>RunAtLoad</key>
  <false/>
  <key>StandardOutPath</key>
  <string>{log}</string>
  <key>StandardErrorPath</key>
  <string>{log}</string>
</dict>
</plist>
"""


def _launchctl(*args: str) -> tuple[int, str]:
    try:
        p = subprocess.run(["launchctl", *args], capture_output=True, text=True)
    except FileNotFoundError:
        return 127, "launchctl not found (not macOS?)"
    return p.returncode, (p.stdout + p.stderr).strip()


def _set_enabled(config_path, value: bool) -> list[str]:
    """flip every job's enabled flag in rhythm.json; returns what flipped."""
    path = Path(config_path or runner.default_config_path())
    cfg = json.loads(path.read_text())
    flipped = []
    for name, jcfg in runner.job_configs(cfg).items():
        if jcfg.get("enabled") is not value:
            jcfg["enabled"] = value
            flipped.append(name)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    return flipped


def show(config_path=None) -> int:
    """the dry run: current state + the exact steps. writes NOTHING."""
    cfg = runner.load_config(config_path)
    p = plist_path()
    armed = p.exists()
    print(f"state: {'ARMED' if armed else 'DISARMED'} — plist"
          f" {'present' if armed else 'absent'} at {p}")
    for name, jcfg in runner.job_configs(cfg).items():
        print(f"  {name}: every {jcfg.get('cadence')} · "
              f"{'enabled' if jcfg.get('enabled') else 'disabled'}")
    ntfy = cfg.get("ntfy") or {}
    print(f"  push: {'ntfy configured' if notify.configured(ntfy) else 'ntfy not configured (server/topic null) — pushes are skipped with a log line'}")
    print()
    print("this was a dry run — nothing was written. nothing arms itself;")
    print("arming is your keystroke:")
    print()
    print("  to arm:    uv run python -m commerceos.rhythm.arm --yes")
    print(f"             writes the plist below to {p},")
    print(f"             loads it (tick every {TICK_EVERY_SECONDS // 60} minutes; each job gates itself")
    print("             by its cadence), and flips every job's enabled flag to true in")
    print(f"             {Path(config_path or runner.default_config_path())}")
    print("  to disarm: uv run python -m commerceos.rhythm.arm --disarm")
    print()
    print("the plist --yes would write:")
    print()
    print(plist_content())
    return 0


def disarm_legacy() -> bool:
    """sweep the pre-multi-store label: unload it and remove its plist.
    Returns whether anything was found — the caller records the act."""
    uid = os.getuid()
    found = False
    rc, _ = _launchctl("bootout", f"gui/{uid}/{LEGACY_LABEL}")
    if rc == 0:
        print(f"[arm] legacy label {LEGACY_LABEL} was loaded — unloaded")
        found = True
    legacy = Path.home() / "Library" / "LaunchAgents" / f"{LEGACY_LABEL}.plist"
    if legacy.exists():
        legacy.unlink()
        print(f"[arm] legacy plist removed: {legacy}")
        found = True
    if not found:
        print(f"[arm] legacy label {LEGACY_LABEL}: not loaded, no plist — nothing to disarm")
    return found


def arm(config_path=None, store: str | None = None) -> int:
    """the owner typed --yes: write the plist, load it, enable the jobs.
    the legacy single-store label is disarmed first, every time (M4)."""
    store = store or stores.active_store()
    disarm_legacy()
    p = plist_path(store)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(plist_content(store))
    print(f"[arm] wrote {p}")
    flipped = _set_enabled(config_path, True)
    cfg_path = Path(config_path or runner.default_config_path())
    print(f"[arm] enabled {', '.join(flipped) if flipped else 'nothing (all were already enabled)'}"
          f" in {cfg_path}")
    uid = os.getuid()
    _launchctl("bootout", f"gui/{uid}/{label(store)}")  # clear any prior load; rc ignored
    rc, out = _launchctl("bootstrap", f"gui/{uid}", str(p))
    if rc == 0:
        print(f"[arm] loaded — tick every {TICK_EVERY_SECONDS // 60} minutes."
              f" disarm: uv run python -m commerceos.rhythm.arm --disarm")
        return 0
    print(f"[arm] plist written but launchctl bootstrap answered {rc}: {out}")
    print(f"[arm] load it by hand: launchctl bootstrap gui/{uid} {p}")
    return 1


def disarm(config_path=None, store: str | None = None) -> int:
    """unload the store's schedule, remove its plist, disable every job."""
    store = store or stores.active_store()
    uid = os.getuid()
    rc, out = _launchctl("bootout", f"gui/{uid}/{label(store)}")
    if rc == 0:
        print("[disarm] launchctl bootout: unloaded")
    else:
        print(f"[disarm] launchctl bootout answered {rc}: {out or 'was not loaded'}")
    p = plist_path()
    if p.exists():
        p.unlink()
        print(f"[disarm] removed {p}")
    else:
        print(f"[disarm] no plist at {p} — already disarmed")
    flipped = _set_enabled(config_path, False)
    print(f"[disarm] disabled {', '.join(flipped) if flipped else 'nothing (all were already disabled)'}"
          f" in {Path(config_path or runner.default_config_path())}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m commerceos.rhythm.arm",
        description="arm or disarm the standing rhythm. nothing arms itself:"
                    " without --yes this is a dry run that writes nothing.")
    ap.add_argument("--yes", action="store_true",
                    help="the owner's keystroke: write + load the launchd plist"
                         " and enable every job")
    ap.add_argument("--disarm", action="store_true",
                    help="unload the schedule, remove the plist, disable every job")
    ap.add_argument("--config", default=None,
                    help="rhythm.json path (default: the active store's)")
    args = ap.parse_args(argv)
    if args.yes and args.disarm:
        ap.error("--yes and --disarm are opposites; pick one")
    if args.disarm:
        return disarm(args.config)
    if args.yes:
        return arm(args.config)
    return show(args.config)


if __name__ == "__main__":
    raise SystemExit(main())
