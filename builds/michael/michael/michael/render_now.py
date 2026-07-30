"""Snapshot the live Blender viewport into the Bench window. Claude runs this after
a visible change. Writes an absolute path (Blender's process has its own cwd)."""

import os
import blender

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders", "latest.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
blender.screenshot(OUT)
print("rendered ->", OUT)
