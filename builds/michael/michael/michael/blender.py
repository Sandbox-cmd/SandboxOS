"""Talk to the live Blender session over the blender-mcp socket (127.0.0.1:9876).

Same wire protocol the measure-twice cartridge uses: a JSON message with a `type`
and `params`, one JSON object back. Everything the app does to Blender goes through
here.
"""

import socket
import json
import os

HOST, PORT = "127.0.0.1", 9876
TIMEOUT = 600
SKILL_SCRIPTS = os.path.expanduser("~/.claude/skills/measure-twice/scripts")


class BlenderError(Exception):
    pass


def _call(payload, timeout=TIMEOUT):
    try:
        s = socket.create_connection((HOST, PORT), timeout=timeout)
    except OSError as e:
        raise BlenderError(
            "Can't reach Blender on %s:%d (%s). Is Blender open with the BlenderMCP "
            "add-on running?" % (HOST, PORT, e)
        )
    with s:
        s.sendall(json.dumps(payload).encode())
        s.settimeout(timeout)
        buf = b""
        while True:
            try:
                chunk = s.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
            try:
                return json.loads(buf.decode())
            except Exception:
                continue
        try:
            return json.loads(buf.decode())
        except Exception:
            raise BlenderError("Malformed reply from Blender.")


def is_up():
    try:
        with socket.create_connection((HOST, PORT), timeout=2):
            return True
    except OSError:
        return False


def exec_code(code):
    """Run Python inside Blender; return whatever the script printed."""
    out = _call({"type": "execute_code", "params": {"code": code}})
    if out.get("status") != "success":
        raise BlenderError(json.dumps(out)[:800])
    res = out.get("result", {})
    return res.get("result", "") if isinstance(res, dict) else str(res)


def screenshot(filepath, max_size=1400):
    """Grab a viewport screenshot to filepath. Returns the path."""
    out = _call({"type": "get_viewport_screenshot",
                 "params": {"filepath": filepath, "max_size": max_size}})
    if out.get("status") != "success":
        raise BlenderError(json.dumps(out)[:800])
    return filepath


def mesh_check(object_name, material="TPU"):
    """Run the cartridge's mesh checker on an object; return its PASS/WARN/FAIL text.

    Pushes scripts/mesh_check.py into Blender with the sibling-dir + args injected the
    same way send_blender.py does, so it finds materials.json and reads the object.
    """
    path = os.path.join(SKILL_SCRIPTS, "mesh_check.py")
    with open(path) as f:
        code = f.read()
    inject = "_SKILL_SCRIPT_DIR = %r\n_SKILL_ARGS = %r\n" % (
        SKILL_SCRIPTS, [object_name, material])
    return exec_code(inject + code)
