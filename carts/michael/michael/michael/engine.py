"""Michael's engine, the FREE version. Instead of the paid Anthropic API, this pipes
each turn to the local `claude` CLI (Claude Code), which runs on the user's
subscription. Claude drives Blender itself (via Bash + the cartridge's socket
scripts), so this is a thin window over the terminal brain.

Key detail: we strip ANTHROPIC_API_KEY from the subprocess env so `claude` uses the
logged-in subscription, NOT the (empty) paid API key.
"""

import os
import json
import subprocess

HOME = os.path.dirname(os.path.abspath(__file__))

def _load_voice():
    """Michael's voice, embedded with the app so it travels with the cart. Reads the
    output-style file next to this module and strips the YAML frontmatter."""
    path = os.path.join(HOME, ".claude", "output-styles", "voice-michael.md")
    try:
        body = open(path).read()
    except OSError:
        return ""
    if body.startswith("---"):
        body = body.split("---", 2)[-1]
    return body.strip()


_OPS = """You are Michael at the bench, and you drive the user's LIVE Blender session.
The voice above is how you talk. What follows is how you work.

Use the `measure-twice` skill. Its cartridge is your working knowledge: principles,
the parametric build -> preview -> verify workflow, materials, the mesh checker, and the
drawing-intake flow. Invoke it whenever you're designing a part.

To act on the live Blender session, use Bash from this directory (the michael-app folder):
- BUILD or EDIT geometry: write a bpy script to a temp file, then run
    python3 ~/.claude/skills/measure-twice/scripts/send_blender.py /tmp/michael_build.py
  Build idempotently (purge the objects you make, then rebuild). The socket is at
  127.0.0.1:9876.
- SHOW the user: after any visible change, run  python3 render_now.py . It snapshots
  the Blender viewport into this window. Always render after building.
- CHECK printability: run
    python3 ~/.claude/skills/measure-twice/scripts/send_blender.py ~/.claude/skills/measure-twice/scripts/mesh_check.py OBJECT MATERIAL
  and paste the PASS/WARN/FAIL table into your reply so the gates panel updates.

If the user dropped a drawing (you'll get a file path), use your Read tool to VIEW the
image, then run the drawing-intake flow: read it back, ask what you're unsure about,
agree a short spec, then build.

You're running headless, so don't ask permission for routine build/render/check steps.
Just do them and show the result. Never export the user's STL; they do that themselves.
Keep replies short. Let the viewport and the gates do the showing."""

PERSONA = ((_load_voice() + "\n\n") if _load_voice() else "") + _OPS


def _env():
    e = dict(os.environ)
    e.pop("ANTHROPIC_API_KEY", None)     # <- use the subscription, not the paid API
    e.pop("ANTHROPIC_AUTH_TOKEN", None)
    return e


def _friendly(name):
    if not name:
        return "working"
    if name == "Bash":
        return "working in Blender"
    if name.startswith("mcp__"):
        return name.split("__")[-1]
    return name


class ClaudeEngine:
    def __init__(self):
        self.session_id = None

    def send(self, text, image_path=None):
        prompt = text or ""
        if image_path:
            prompt = ("The user dropped a drawing at %s. Use your Read tool to view "
                      "that image, then run the drawing-intake flow. %s"
                      % (image_path, text or "")).strip()

        cmd = ["claude", "-p", prompt,
               "--output-format", "stream-json", "--verbose", "--include-partial-messages",
               "--permission-mode", "bypassPermissions",
               "--append-system-prompt", PERSONA]
        if self.session_id:
            cmd += ["--resume", self.session_id]

        try:
            proc = subprocess.Popen(cmd, cwd=HOME, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, bufsize=1, env=_env())
        except FileNotFoundError:
            yield {"type": "error", "text": "Can't find the `claude` command. Is Claude Code installed?"}
            yield {"type": "done"}
            return

        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                for out in self._translate(ev):
                    yield out
        finally:
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        yield {"type": "done"}

    def _translate(self, ev):
        t = ev.get("type")
        if t == "system" and ev.get("subtype") == "init":
            self.session_id = ev.get("session_id")
        elif t == "stream_event":
            d = ev.get("event", {}).get("delta", {})
            if d.get("type") == "text_delta" and d.get("text"):
                yield {"type": "text", "text": d["text"]}
        elif t == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "tool_use":
                    yield {"type": "tool_start", "name": _friendly(b.get("name"))}
        elif t == "user":
            for b in (ev.get("message", {}).get("content") or []):
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    yield {"type": "tool_done", "error": bool(b.get("is_error"))}
        elif t == "tool_result":
            yield {"type": "tool_done", "error": bool(ev.get("is_error"))}
        elif t == "rate_limit_event":
            info = ev.get("rate_limit_info", {})
            if info.get("status") and info["status"] != "allowed":
                yield {"type": "error",
                       "text": "You've hit your Claude plan's usage limit for now. It "
                               "resets on a timer. Try again a little later."}
        elif t == "result":
            if ev.get("is_error") or ev.get("subtype") != "success":
                yield {"type": "error", "text": (ev.get("result") or "The brain hit an error.")[:500]}
