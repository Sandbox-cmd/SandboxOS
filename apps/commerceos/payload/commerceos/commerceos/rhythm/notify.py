"""push — the phone's reach, notify-only by law.

spec/experience.md: push carries the item and a deep link, never the
decision — approving lives solely on the authenticated web surface. the
wire is ntfy (one plain HTTP POST per notification); server and topic
live in the store's rhythm.json and are BOTH null by default:
unconfigured means every push is skipped with an honest log line —
never a silent third-party default. no action buttons, no approve verb,
ever.

three triggers, all called from runner.tick: new pending approvals,
a failed job, a new risk finding.
"""

from __future__ import annotations

import urllib.request

# where deep links point when the config names nothing: the local web
# surface. the owner sets ntfy.link_base to his tailscale hostname when
# the phone needs reach.
DEFAULT_LINK_BASE = "http://localhost:8000"


def configured(ntfy: dict | None) -> bool:
    """both server and topic set — the only state in which a wire is touched."""
    ntfy = ntfy or {}
    return bool(ntfy.get("server")) and bool(ntfy.get("topic"))


def link(ntfy: dict | None, path: str) -> str:
    base = (ntfy or {}).get("link_base") or DEFAULT_LINK_BASE
    return base.rstrip("/") + path


def send(ntfy: dict | None, title: str, message: str,
         click: str | None = None, priority: str | None = None) -> bool:
    """POST one notification. True = sent; False = skipped (unconfigured)
    or the wire failed — logged honestly either way, never raised: a push
    that cannot go out must not stop the rhythm."""
    if not configured(ntfy):
        print(f"[notify] skipped — ntfy unconfigured (server/topic are null in the"
              f" store's rhythm.json): {title} · {message}")
        return False
    url = str(ntfy["server"]).rstrip("/") + "/" + str(ntfy["topic"]).strip("/")
    headers = {"Title": title}
    if click:
        headers["Click"] = click
    if priority:
        headers["Priority"] = str(priority)
    req = urllib.request.Request(url, data=message.encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = 200 <= getattr(resp, "status", 0) < 300
    except OSError as e:  # URLError subclasses OSError; the rhythm must not die on a push
        print(f"[notify] failed — {type(e).__name__}: {e} · {title}")
        return False
    print(f"[notify] {'sent' if ok else 'refused by server'} -> {url}: {title}")
    return ok


# ---------- the three triggers ----------

def pending_approvals(ntfy: dict | None, new: int, waiting: int) -> bool:
    """new pending approvals: the count and the deep link. the decision
    itself happens only on the web surface — never here."""
    title = f"{new} new approval{'s' if new != 1 else ''} waiting"
    message = f"{waiting} waiting in the queue"
    return send(ntfy, title, message, click=link(ntfy, "/approvals"), priority="high")


def job_failed(ntfy: dict | None, job: str, error: str) -> bool:
    """a rhythm job failed: the error line and a link to the parts view."""
    return send(ntfy, f"rhythm: {job} failed", error, click=link(ntfy, "/parts"))


def risk_finding(ntfy: dict | None, sentences: list[str]) -> bool:
    """new risk finding(s): the first sentence and a link to the findings stream."""
    n = len(sentences)
    title = "new risk finding" if n == 1 else f"{n} new risk findings"
    message = sentences[0] + (f" (+{n - 1} more)" if n > 1 else "")
    return send(ntfy, title, message, click=link(ntfy, "/findings"), priority="high")
