# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The loopback server: one route per view, the Host and Origin checks, the content security policy, the desk token
(contract section 6), POST /answer, POST /welcome, POST /strike and POST /tick, files rewritten after a deletion before the next answer, and the
read-only preview server for the thing being made, another origin with no answer route."""
import datetime as _dt
import hashlib
import http.server
import json
import os
import re
import secrets
import threading
import urllib.parse

from sandbox_os import store as _store
from sandbox_os.store import Refused
from sandbox_os.store.line import ID_RE, UNIT_RE, iso
from sandbox_os.pages import measures, views, write
from sandbox_os.pages.frame import CSP, FONTS, Ctx
from sandbox_os.pages.read import Reader, standing, portraits, sentences, ticked
from sandbox_os.pages.words import Words, H, esc

LOOPBACK = "127.0.0.1"
ARABIC = re.compile("[\u0600-\u06ff]")
TOOL = write.TOOL
HEADERS = {"Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin",
           "Cache-Control": "no-store"}
ROUTES = {"": "brief", "project": "project", "run": "run", "card": "card", "present": "present", "find": "find", "learned": "learned",
          "charter": "charter", "book": "book", "tool": "tool", "graph": "graph", "moved": "moved", "welcome": "welcome", "week": "week", "cards": "cards",
          "thing": "thing", "things": "things", "type": "type", "you": "you"}
BY_UNIT, BY_ID = ("project", "present", "graph", "moved"), {"run": "run", "card": "card", "thing": "object"}  # a view by id, and the kind its line has
BY_NAME = ("type",)  # a view by a standing type's name


def first_view(s):
    """The welcome until welcome.md and a first run exist, unless the workshop holds imported lines (then the brief)."""
    r = Reader(s)
    if r.kind("move") or (r.welcome() is not None and r.kind("run")):
        return "brief"
    return "welcome"


def bound(host):
    if host != LOOPBACK:
        raise Refused(Words("en").plain("serve.bind", address=host))


class Base(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, host, port, handler):
        bound(host)
        super().__init__((host, port), handler)
        self.port = self.server_address[1]
        self.address = f"http://{LOOPBACK}:{self.port}"
        self.hosts = {f"{LOOPBACK}:{self.port}", f"localhost:{self.port}"}

    def start(self):
        threading.Thread(target=self.serve_forever, daemon=True).start()
        return self

    def stop(self):
        self.shutdown()
        self.server_close()


class Handler(http.server.BaseHTTPRequestHandler):
    version_string = lambda self: "sandbox"  # noqa: E731  the Server header: the tool's plain name, no version, no trailing space

    def log_message(self, *a):
        pass

    def send(self, status, body=b"", kind="text/html; charset=utf-8", extra=()):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        for k, v in list(HEADERS.items()) + list(extra):
            self.send_header(k, v)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def host_ok(self):
        if self.headers.get("Host") in self.server.hosts:
            return True
        self.server.refused(self, 421, self.headers.get("Host") or "")
        return False


class App(Base):
    """The pages for one workshop: every GET opens the store read-only; a POST opens it to write the maker's answer."""

    def __init__(self, workshop, port=0, *, clock=None, machine=None, session=None, host=LOOPBACK):
        self.root = os.path.realpath(workshop.root if hasattr(workshop, "lines") else workshop)
        self.clock, self.machine = clock or (lambda: _dt.datetime.now(_dt.timezone.utc)), machine
        self.token, self.spent, self.session = secrets.token_urlsafe(24), False, session or "pages-" + secrets.token_hex(4)
        self.lock = threading.Lock()
        super().__init__(host, port, PagesHandler)
        self.desk_url = f"{self.address}/desk/{self.token}"
        s, memo = self.store(), write.read_memo(self.root)
        self.acts = memo.get("acts") if memo is not None else self.newest_act(s)  # never written: nothing on disk holds a deleted line
        self.rewrite_after_acts(s)  # a deletion made while the pages were stopped is rewritten before the first response

    def store(self, write=False):
        return _store.open(self.root, read_only=not write, clock=self.clock, machine=self.machine if write else "pages")

    def words(self, s=None):
        return Ctx(s or self.store()).w

    def newest_act(self, s):
        try:
            acts = s.lines(kinds=["delete", "erase", "undelete"])
        except Exception:  # the index does not read: nothing is rewritten, and the brief says why (R-READ-20)
            return getattr(self, "acts", None)
        return acts[-1]["id"] if acts else None

    def refused(self, req, status, what):
        """A refusal is a line the brief lists, by the tool, naming what was refused and never who asked."""
        w = Words("en", root=self.root)
        key = "serve.host" if status == 421 else "serve.origin"
        try:
            self.store(write=True).append("workshop", "note", {"event": "refused", "status": status, "what": what[:200], "path": req.path[:200],
                                                               "text": w.plain("refused.text", status=str(status), why=w.plain(key, host=what, origin=what))}, by=TOOL)
        except Refused:
            pass
        req.send(status, w.plain(key, host=what, origin=what), "text/plain; charset=utf-8")

    def rewrite_after_acts(self, s):
        """After a deletion or an erasure, every written file of its unit is rewritten before this request is answered."""
        newest = self.newest_act(s)
        if newest != self.acts:
            units = sorted(write.acts_since(s, self.acts)[1] & set(s.units()))
            write.write_views(s, units[0] if units else None, clock=self.clock, machine=self.machine)
            self.acts = newest

    def desk(self, cookie):
        """presence: desk only for the token whose hash cache/desk-token keeps, set in this server's own session, not ended, not expired."""
        m = re.search(r"(?:^|;\s*)desk=([\w-]+)", cookie or "")
        p = os.path.join(self.root, "cache", "desk-token")
        if not m or not os.path.exists(p):
            return "none"
        kept = json.load(open(p))
        live = (kept.get("expires", "") > self.clock().strftime("%Y-%m-%dT%H:%M:%SZ") and kept.get("session") == self.session
                and not kept.get("ended"))
        return "desk" if live and hashlib.sha256(m.group(1).encode()).hexdigest() == kept.get("sha256") else "none"

    def opened(self, view):
        """A view answered with a page: one line in cache/pages-opened.jsonl, its time and the view's name and nothing else, on this machine
        (consistency item 10); a log that cannot be written refuses no page. Called under the lock."""
        try:
            os.makedirs(os.path.join(self.root, "cache"), exist_ok=True)
            with open(os.path.join(self.root, measures.OPENED), "a", encoding="utf-8") as f:
                f.write(json.dumps({"t": iso(self.clock()), "view": view}) + "\n")
        except OSError:
            pass

    def stop(self):
        """Stopping the pages ends their session: a desk token set in it no longer counts (contract section 6)."""
        p = os.path.join(self.root, "cache", "desk-token")
        if os.path.exists(p):
            kept = json.load(open(p))
            if kept.get("session") == self.session and not kept.get("ended"):
                with open(p, "w") as f:
                    json.dump(dict(kept, ended=self.clock().strftime("%Y-%m-%dT%H:%M:%SZ")), f)
        super().stop()


class PagesHandler(Handler):

    def framed(self, status, sid, s=None, lang=None, title="err.title"):
        """A refusal or a not-found as a page like the others: what happened and the way on, a link back to this server's page it came
        from, else to the brief; the status is the caller's (R-DESIGN-9)."""
        c = Ctx(s or self.server.store(), lang=lang)
        back = urllib.parse.urlsplit(self.headers.get("Referer") or "")
        own = back.netloc in self.server.hosts and not back.path.startswith("//") and back.path
        link = H(f'<p><a href="{esc(back.path if own else "/")}">{c.w.t("err.back" if own else "err.brief")}</a></p>')
        self.send(status, c.page(c.w.t(title), c.w.t(sid), H(""), link, view="refused"))

    def do_GET(self):
        app = self.server
        if not self.host_ok():
            return
        url = urllib.parse.urlsplit(self.path)
        q = urllib.parse.parse_qs(url.query)
        lang = (q.get("lang") or [None])[0]
        lang = lang if lang in ("en", "ar") else None
        bits = [urllib.parse.unquote(b) for b in url.path.strip("/").split("/")]
        if bits[0] == "desk" and len(bits) == 2:
            return self.open_desk(bits[1])
        if bits[0] == "fonts" and len(bits) == 2 and re.fullmatch(r"[\w.-]+\.woff2", bits[1]) and os.path.exists(os.path.join(FONTS, bits[1])):
            return self.send(200, open(os.path.join(FONTS, bits[1]), "rb").read(), "font/woff2")
        view = ROUTES.get(bits[0])
        with app.lock:
            s = app.store()
            try:
                app.rewrite_after_acts(s)
                ids, units = {}, s.units()
                if view in BY_UNIT and len(bits) == 2 and UNIT_RE.match(bits[1]) and bits[1] in units:
                    ids = {"unit": bits[1]}
                elif view in BY_ID and len(bits) == 2 and ID_RE.match(bits[1]) and (s.get(bits[1]) or {}).get("kind") == BY_ID[view]:
                    ids = {"id": bits[1]}
                elif view in BY_NAME and len(bits) == 2 and bits[1] in {t["body"]["name"] for t in s.types()}:
                    ids = {"name": bits[1]}
                elif view == "graph" and len(bits) == 1:  # the world graph; its day, type and unit are read by the view, which says what it left out
                    view, ids = "world", {k: (q.get(k) or [None])[0] for k in ("day", "type", "unit")}
                elif view == "find" and len(bits) == 1:
                    ids = {"q": (q.get("q") or [None])[0]}
                elif view == "week" and len(bits) == 2 and measures.valid(bits[1]):
                    ids = {"week": bits[1]}
                elif view == "cards" and bits[1:] == ["move"]:  # the move's cards (card 23), the one list this route serves
                    ids = {}
                elif view == "you" and bits[1:] == ["tick"]:  # the portraits, served only and never written as a file (consistency item 5)
                    view, ids = "portraits", {}
                elif view is None or len(bits) != 1 or view in BY_UNIT + tuple(BY_ID) + ("cards",) + BY_NAME:
                    return self.framed(404, "serve.notfound", s, lang, "err.title.notfound")
                if first_view(s) == "welcome":  # every route serves the welcome, so the welcome offers no link that only brings it back
                    view, ids = "welcome", {"gated": True}
            except Exception:  # a record that does not read is damaged: the brief, which names each fault the read-back finds (R-READ-20)
                view, ids = "brief", {}
            self.send(200, views.render(view, s, lang=lang, **ids))
            app.opened(view)

    def open_desk(self, token):
        app = self.server
        w = app.words()
        if app.spent or not secrets.compare_digest(token, app.token):
            return self.framed(410, "serve.spent")
        app.spent = True
        until = app.clock() + _dt.timedelta(hours=8)
        os.makedirs(os.path.join(app.root, "cache"), exist_ok=True)
        with open(os.path.join(app.root, "cache", "desk-token"), "w") as f:
            json.dump({"sha256": hashlib.sha256(token.encode()).hexdigest(), "session": app.session,
                       "expires": until.strftime("%Y-%m-%dT%H:%M:%SZ")}, f)
        self.send(303, H(w.t("serve.desk", tag="p", when=w.when(until))),
                  extra=[("Set-Cookie", f"desk={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=28800"), ("Location", "/")])

    def do_POST(self):
        app = self.server
        if not self.host_ok():
            return
        if self.headers.get("Origin") not in {f"http://{h}" for h in app.hosts}:
            return app.refused(self, 403, self.headers.get("Origin") or "")
        size = int(self.headers.get("Content-Length") or 0)
        form = {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(min(size, 65536)).decode("utf-8", "replace"), keep_blank_values=True).items()}
        with app.lock:
            if self.path == "/answer":
                return self.answer(form)
            if self.path == "/welcome":
                return self.welcome(form)
            if self.path == "/strike":
                return self.strike(form)
            if self.path == "/tick":
                return self.tick(form)
        self.framed(404, "serve.notfound", title="err.title.notfound")

    def went_back(self, w, sid, home):
        """After a post: back to this server's page it came from, else home, with the sentence that says what was kept."""
        back = urllib.parse.urlsplit(self.headers.get("Referer") or "")
        self.send(303, H(w.t(sid, tag="p")), extra=[("Location", back.path if back.netloc in self.server.hosts and back.path else home)])

    def answer(self, f):
        app = self.server
        s = app.store(write=True)
        c = Ctx(s)
        w, r = c.w, c.r
        card = r.get(f.get("card", "")) if ID_RE.match(f.get("card", "")) else None
        a, words = f.get("answer"), f.get("words", "")
        if not card or card["kind"] != "card" or a not in ("yes", "no", "later", "words"):
            return self.framed(400, "serve.bad", s)
        if a == "words" and not words:
            return self.framed(400, "serve.empty", s)
        before = [x for x in r.answers(card["id"]) if standing(x)]
        head = f.get("head") or ""
        presence = app.desk(self.headers.get("Cookie"))
        by = ({"kind": "maker", "name": c.welcome.get("name") or "maker", "model": None, "host": None} if presence == "desk"
              else {"kind": "tool", "name": "sandbox-os", "model": None, "host": None})  # no person at the desk: never the maker's line
        if words.strip() == "needless" and a == "words" and before:
            s.append(card["unit"], "needless", {"answer": before[-1]["id"]}, by=by)
        else:
            stale = bool(before and (not head or before[-1]["id"] > head))  # answered elsewhere since this page was drawn: kept, marked, deciding nothing
            prior = [x for x in before if not (x["body"] or {}).get("stale")]
            body = {"card": card["id"], "answer": a, "from": "page", "presence": presence}
            if presence != "desk":
                body["person"] = "not established"
            if words:
                body["words"] = words
            if stale or any((x["body"] or {}).get("version", 1) > (card["body"] or {}).get("version", 1) for x in r.into(card["id"], "follows") if x["kind"] == "card"):
                body["stale"] = True
            new = s.append(card["unit"], "answer", body, by=by)
            if prior and not body.get("stale"):
                s.link(new, "supersedes", prior[-1]["id"], by=by)
        write.write_views(s, card["unit"], clock=app.clock, machine=app.machine)
        self.went_back(w, "serve.kept", f"/card/{card['id']}")

    def strike(self, f):
        """A strike from a page: the maker's only with desk presence; without it nothing is struck and the tool writes the refusal."""
        app = self.server
        s = app.store(write=True)
        c = Ctx(s)
        w, en = c.w, Words("en", root=app.root)
        if app.desk(self.headers.get("Cookie")) != "desk":
            s.append("workshop", "note", {"event": "refused", "status": 403, "what": "strike", "path": self.path[:200],
                                          "text": en.plain("refused.text", status="403", why=en.plain("serve.strike.nodesk"))}, by=TOOL)
            return self.framed(403, "serve.strike.nodesk", s)
        line = s.get(f.get("line", "")) if ID_RE.match(f.get("line", "")) else None
        if not standing(line):
            return self.framed(400, "serve.strike.bad", s)
        try:
            s.strike(line["id"], by={"kind": "maker", "name": c.welcome.get("name") or "maker", "model": None, "host": None},
                     why=en.plain("you.struck.why"))
        except Refused:
            return self.framed(400, "serve.strike.bad", s)
        write.write_views(s, line["unit"], clock=app.clock, machine=app.machine)
        self.went_back(w, "serve.struck", "/you")

    def tick(self, f):
        """A tick: the sentence read again where it lives, found by its hash, and at the desk his said line about himself with its
        source, once; without the desk nothing is recorded in his name and the tool writes the refusal."""
        app = self.server
        s = app.store(write=True)
        c = Ctx(s)
        w, en = c.w, Words("en", root=app.root)
        if app.desk(self.headers.get("Cookie")) != "desk":
            s.append("workshop", "note", {"event": "refused", "status": 403, "what": "tick", "path": self.path[:200],
                                          "text": en.plain("refused.text", status="403", why=en.plain("serve.tick.nodesk"))}, by=TOOL)
            return self.framed(403, "serve.tick.nodesk", s)
        row = next((p for p in portraits(app.root) if str(p["n"]) == f.get("n")), None)
        got = next(((path, x) for path in (row or {}).get("files", []) for h, x in sentences(path, row["section"] or None)
                    if h == f.get("sha")), None)
        if not got:
            return self.framed(400, "serve.tick.bad", s)
        path, words = got
        if (path, f["sha"]) not in ticked(s):
            body = {"words": words, "surface": "tick", "source": path, "label": row["label"], "ticked": w.local(app.clock()).date().isoformat()}
            s.append("workshop", "said", body, by={"kind": "maker", "name": c.welcome.get("name") or "maker", "model": None, "host": None},
                     about=write.maker_object(s), lang="ar" if ARABIC.search(words) else None)
            write.write_views(s, "workshop", clock=app.clock, machine=app.machine)
        self.went_back(w, "serve.ticked", "/you/tick")

    def welcome(self, f):
        app = self.server
        s = app.store(write=True)
        w = Ctx(s).w
        answers = {} if f.get("go") == "skip" else {k: f.get(k, "") for k in ("name", "making", "ask")}
        try:
            write.save_welcome(s, answers)
        except FileExistsError:
            return self.framed(409, "welcome.once", s)
        self.send(303, H(w.t("welcome.saved", tag="p")), extra=[("Location", "/")])


def serve(workshop, port=0, *, clock=None, machine=None, session=None, host=LOOPBACK, background=True, out=print):
    """The pages on 127.0.0.1 only, already running when returned (stop() ends them); prints the address with its one-time
    desk path; background=False keeps the caller here until interrupted."""
    app = App(workshop, port, clock=clock, machine=machine, session=session, host=host).start()
    out(app.words().plain("serve.address", address=app.desk_url) + "\n")
    if not background:
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            app.stop()
    return app


class PreviewHandler(Handler):

    def do_GET(self):
        p = self.server
        if not self.host_ok():
            return
        rel = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path).lstrip("/") or "index.html"
        path = os.path.realpath(os.path.join(p.folder, rel))
        if path != p.folder and not path.startswith(p.folder + os.sep):
            return self.send(403)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        if not os.path.isfile(path):
            return self.send(404)
        if path.endswith(".html"):
            p.opened()
        kind = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
                ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".woff2": "font/woff2"}.get(os.path.splitext(path)[1], "application/octet-stream")
        data = open(path, "rb").read()
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.host_ok():
            self.send(405, Words("en").plain("serve.readonly"), "text/plain; charset=utf-8")

    do_PUT = do_DELETE = do_PATCH = do_POST


class PreviewServer(Base):
    """One folder served read-only on its own loopback port, another origin than the pages; an open is a preview line by the tool."""

    def __init__(self, folder, port=0, *, workshop=None, clock=None, machine=None, host=LOOPBACK):
        self.folder = os.path.realpath(folder)
        self.workshop, self.clock, self.machine = workshop, clock, machine
        super().__init__(host, port, PreviewHandler)

    def opened(self):
        if not self.workshop:
            return
        s = _store.open(self.workshop, clock=self.clock, machine=self.machine)
        rel = os.path.relpath(self.folder, s.root).split(os.sep)
        unit = rel[1] if len(rel) > 1 and rel[0] == "projects" and rel[1] in s.units() else "workshop"
        s.append(unit, "preview", {"thing": os.path.basename(self.folder), "address": self.address, "event": "opened",
                                   "text": Words("en", root=s.root).plain("preview.opened", folder=os.path.basename(self.folder))}, by=TOOL)

    def refused(self, req, status, what):
        req.send(status, Words("en").plain("serve.host", host=what), "text/plain; charset=utf-8")
