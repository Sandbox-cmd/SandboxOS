# Bench

A small desktop app to design 3D-printable products by chatting. You talk to it,
it builds and edits geometry in your live Blender session, shows you renders, and
runs a manufacturability checker — all driven by the `measure-twice` cartridge as
its brain.

## What it does
- **Chat** with a product-design assistant (Claude, model `claude-opus-4-8`).
- **Drop a drawing** onto the viewport → it runs the drawing-intake flow (reads it
  back, asks what it's unsure about, agrees a spec, then builds).
- **Live preview** — it renders the Blender viewport after changes.
- **Manufacturability gates** — watertight, member thickness, overhang, envelope.

## Requirements
1. **Blender open** with the BlenderMCP add-on running (socket on 127.0.0.1:9876).
2. **An Anthropic API key.**
3. Python 3.9+.

## Run
```bash
cd ~/Desktop/michael-app
python3 -m pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...        # your key
python3 app.py
```
Open http://127.0.0.1:5178 in a browser.

### Native window (no browser tab)
```bash
python3 -m pip install pywebview
python3 window.py
```

## Files
- `app.py` — Flask server: serves the UI, streams the agent (SSE), handles sketch
  uploads (converts HEIC→JPEG via macOS `sips`), serves renders.
- `agent.py` — the Claude agentic loop; loads the cartridge as its system prompt;
  tools: `blender_exec`, `render_view`, `mesh_check`.
- `blender.py` — socket client to the live Blender session.
- `templates/index.html` — the Bench UI.

## Notes
- One conversation per run (single-user desktop app). `POST /reset` starts fresh.
- It never exports your STL — you do that from Blender. It leaves the object in the
  scene for you.
- The brain is the cartridge at `~/.claude/skills/measure-twice/`. Improve the
  cartridge, and Bench gets smarter — no app change needed.
