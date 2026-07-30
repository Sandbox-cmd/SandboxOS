"""Snap the shop into place: Blender up top, Terminal down below, split screen.

Blender takes the top half, Terminal the bottom, each filling the width.
Waits for Blender's window to exist first (it boots slower than the terminal),
so this is safe to fire right after the launcher opens newsession.blend.

Run it whenever the windows drift:   python3 split_shop.py
Needs Accessibility permission for Terminal (System Settings → Privacy &
Security → Accessibility) — a one-time grant so it can move other apps' windows.
"""

import subprocess
import time


def _osa(script):
    r = subprocess.run(["osascript", "-e", script],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def _screen():
    # Finder desktop bounds → "0, 0, W, H"
    b = _osa('tell application "Finder" to get bounds of window of desktop')
    _, _, w, h = (int(n) for n in b.split(","))
    return w, h


def _blender_has_window():
    try:
        n = _osa('tell application "System Events" to get count of windows of '
                 'process "Blender"')
        return int(n) > 0
    except Exception:
        return False


def split(timeout=25):
    # wait for Blender to finish booting and put up a window
    deadline = time.time() + timeout
    while not _blender_has_window():
        if time.time() > deadline:
            print("Blender window never showed — is it open? Skipping split.")
            return
        time.sleep(0.5)

    w, h = _screen()
    top = 25                      # sit just under the menu bar
    avail = h - top
    half = avail // 2

    _osa(f'''
    tell application "System Events"
      tell process "Blender"
        set position of front window to {{0, {top}}}
        set size of front window to {{{w}, {half}}}
      end tell
      tell process "Terminal"
        set position of front window to {{0, {top + half}}}
        set size of front window to {{{w}, {avail - half}}}
      end tell
    end tell
    ''')
    print("Shop split: Blender up top, Terminal below.")


if __name__ == "__main__":
    split()
