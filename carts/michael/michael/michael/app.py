"""Bench — a local desktop app for designing 3D-printable products by chatting.

FREE version: the brain is the local `claude` CLI (your Claude subscription), not the
paid API. No API key needed.

Run:
    pip install flask
    python3 app.py           # then open http://127.0.0.1:5178
    (or python3 window.py for a native window — needs pywebview)
Keep Blender open with the BlenderMCP add-on running.
"""

import os
import json
import shutil
import subprocess

from flask import Flask, request, Response, send_from_directory, render_template, jsonify

import blender
from engine import ClaudeEngine

HERE = os.path.dirname(os.path.abspath(__file__))
INTAKE_DIR = os.path.join(HERE, "intake")
RENDER_DIR = os.path.join(HERE, "renders")
READABLE = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

app = Flask(__name__)
_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = ClaudeEngine()
    return _engine


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/status")
def status():
    return jsonify({"blender": blender.is_up(),
                    "brain": bool(shutil.which("claude"))})


@app.route("/sketch", methods=["POST"])
def sketch():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400
    os.makedirs(INTAKE_DIR, exist_ok=True)
    name = os.path.basename(f.filename) or "sketch.png"
    dest = os.path.join(INTAKE_DIR, name)
    f.save(dest)
    ext = os.path.splitext(dest)[1].lower()
    read_path, url = dest, "/intake/" + name
    if ext not in READABLE:  # e.g. .heic -> jpeg so Claude's Read tool can view it
        jpg = dest + ".jpg"
        try:
            subprocess.run(["sips", "-s", "format", "jpeg", dest, "--out", jpg],
                           check=True, capture_output=True)
            read_path = jpg
            url = "/intake/" + os.path.basename(jpg)
        except Exception:
            pass
    return jsonify({"path": read_path, "name": name, "url": url})


@app.route("/intake/<path:fn>")
def intake_file(fn):
    return send_from_directory(INTAKE_DIR, fn)


@app.route("/renders/<path:fn>")
def render_file(fn):
    return send_from_directory(RENDER_DIR, fn)


@app.route("/reset", methods=["POST"])
def reset():
    global _engine
    _engine = None
    return jsonify({"ok": True})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    text = (data.get("message") or "").strip()
    image_path = data.get("image_path")

    def stream():
        for event in engine().send(text, image_path if image_path and os.path.exists(image_path) else None):
            yield "data: " + json.dumps(event) + "\n\n"

    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    print("Bench (free / subscription brain) on http://127.0.0.1:5178")
    print("Blender:", "connected" if blender.is_up() else "NOT reachable (open Blender + the add-on)")
    print("Brain:", "claude CLI found" if shutil.which("claude") else "claude CLI MISSING")
    app.run(host="127.0.0.1", port=5178, threaded=True, debug=False)
