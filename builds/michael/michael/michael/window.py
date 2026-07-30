"""Open Bench in a native desktop window (no browser tab).

Needs pywebview:  pip install pywebview
Then:             python window.py
"""

import threading
import app as bench_app

try:
    import webview
except ImportError:
    raise SystemExit("Install pywebview first:  pip install pywebview")


def _serve():
    bench_app.app.run(host="127.0.0.1", port=5178, threaded=True, debug=False)


if __name__ == "__main__":
    threading.Thread(target=_serve, daemon=True).start()
    webview.create_window("Bench", "http://127.0.0.1:5178", width=1120, height=760)
    webview.start()
