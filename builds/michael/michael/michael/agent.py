"""Bench's brain: a Claude agent that designs 3D products and drives Blender.

Loads the measure-twice cartridge as its system prompt, then runs a streaming
agentic loop with three tools that reach into the live Blender session. The app
layer (app.py) turns the yielded events into server-sent events for the UI.
"""

import os
import glob
import itertools
import anthropic

import blender

MODEL = "claude-opus-4-8"
CARTRIDGE = os.path.expanduser("~/.claude/skills/measure-twice")
RENDER_DIR = os.path.join(os.path.dirname(__file__), "renders")

_render_seq = itertools.count(1)


# ---------------------------------------------------------------- system prompt
def _load_cartridge():
    parts = []
    skill = os.path.join(CARTRIDGE, "SKILL.md")
    if os.path.exists(skill):
        parts.append(open(skill).read())
    for ref in sorted(glob.glob(os.path.join(CARTRIDGE, "references", "*.md"))):
        parts.append("\n\n# ===== reference: %s =====\n\n%s"
                     % (os.path.basename(ref), open(ref).read()))
    return "\n".join(parts) if parts else "(measure-twice cartridge not found)"


PREAMBLE = """You are Bench — a friendly desktop assistant that helps design physical,
3D-printable products by chatting, and builds them in a live Blender session.

You have three tools:
- blender_exec: run Python (bpy) inside the user's live Blender to build or edit geometry.
- render_view: take a snapshot of the Blender viewport so the user can see the result.
- mesh_check: run the manufacturability checker on an object and read back the gates.

How to work:
- If the user drops a photo of a drawing, run the drawing-intake movement from the
  cartridge first: read it back, ask what you don't understand, agree a short spec,
  then build. Ask your questions before modeling.
- Build parametrically and idempotently; after a change, call render_view so the user
  sees it, and mesh_check when they care about printability. Never overwrite the user's
  files — they export the STL themselves.
- Talk warmly and plainly, like a maker at a bench. Keep replies short; let the
  viewport and the gates do the showing.

The full method, principles, workflow, materials, gates, and the drawing-intake steps
follow below — treat them as your working knowledge."""


def build_system():
    text = PREAMBLE + "\n\n" + _load_cartridge()
    # one cached block — big and stable, so it caches across turns
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


# ---------------------------------------------------------------------- tools
TOOLS = [
    {
        "name": "blender_exec",
        "description": "Run Python (bpy) inside the user's live Blender session to build "
                       "or edit geometry. Returns whatever the script prints. Build "
                       "idempotently (purge then rebuild). Print a short status line.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The bpy Python to execute."}
            },
            "required": ["code"],
        },
    },
    {
        "name": "render_view",
        "description": "Take a snapshot of the current Blender viewport so the user can "
                       "see the current design. Call this after making a visible change.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "mesh_check",
        "description": "Run the manufacturability checker on an object: watertight, "
                       "minimum member thickness, overhang, envelope, facet size. Returns "
                       "a PASS/WARN/FAIL table. Use when the user cares about printability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string", "description": "Name of the mesh object to check."},
                "material": {"type": "string", "enum": ["TPU", "PLA", "PETG"],
                             "description": "Material row for the thresholds (default TPU)."},
            },
            "required": ["object_name"],
        },
    },
]


class BenchAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY
        self.system = build_system()
        self.messages = []

    def _run_tool(self, name, tool_input):
        """Return (result_text, ui_event_or_None)."""
        try:
            if name == "blender_exec":
                out = blender.exec_code(tool_input["code"])
                return (out or "(no output)"), None
            if name == "render_view":
                os.makedirs(RENDER_DIR, exist_ok=True)
                fn = "r%d.png" % next(_render_seq)
                blender.screenshot(os.path.join(RENDER_DIR, fn))
                return ("Rendered the viewport for the user.",
                        {"type": "render", "url": "/renders/" + fn})
            if name == "mesh_check":
                out = blender.mesh_check(tool_input["object_name"],
                                         tool_input.get("material", "TPU"))
                return out, {"type": "gates", "text": out}
            return "ERROR: unknown tool %s" % name, None
        except blender.BlenderError as e:
            return "ERROR: " + str(e), None
        except Exception as e:  # noqa: BLE001 — surface any tool failure to the model
            return "ERROR: " + repr(e), None

    def send(self, user_content):
        """Stream the full agentic turn. Yields UI event dicts."""
        self.messages.append({"role": "user", "content": user_content})
        try:
            while True:
                final = None
                with self.client.messages.stream(
                    model=MODEL,
                    max_tokens=16000,
                    system=self.system,
                    messages=self.messages,
                    tools=TOOLS,
                    thinking={"type": "adaptive"},
                ) as stream:
                    for text in stream.text_stream:
                        yield {"type": "text", "text": text}
                    final = stream.get_final_message()

                self.messages.append({"role": "assistant", "content": final.content})

                if final.stop_reason != "tool_use":
                    break

                tool_results = []
                for block in final.content:
                    if block.type != "tool_use":
                        continue
                    yield {"type": "tool_start", "name": block.name}
                    result, ui = self._run_tool(block.name, block.input)
                    if ui:
                        yield ui
                    yield {"type": "tool_done", "name": block.name,
                           "error": result.startswith("ERROR")}
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                        "is_error": result.startswith("ERROR"),
                    })
                self.messages.append({"role": "user", "content": tool_results})
        except anthropic.AuthenticationError:
            yield {"type": "error",
                   "text": "Anthropic rejected the API key. Set ANTHROPIC_API_KEY and restart."}
        except anthropic.APIStatusError as e:
            yield {"type": "error", "text": "Claude API error %s: %s" % (e.status_code, e.message)}
        except Exception as e:  # noqa: BLE001
            yield {"type": "error", "text": "Something broke: " + repr(e)}
        yield {"type": "done"}
