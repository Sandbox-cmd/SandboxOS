# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The onboarding flow (design.md section 3; R-CMD-07 to 19): the opening, the folder (always typed), the hosts (found by reading PATH,
placed by their adapters), the three questions, the first project, and the line that starts the first run. Every step is a flow line
by the tool with its seconds; a stall is a line with its cause; an unfinished step resumes at the next start; lines written before a
workshop exists wait in the install folder and open its record. Nothing skips it, it reads no name from the system, and it raises no
card but the one for a synced folder. Until its done line, flow.md beside the instruction block names the open step."""
import datetime as _dt
import hashlib, json, os, re, shlex, time

from sandbox_os import store as _store
from sandbox_os.store.line import iso, mint_id, parse_t
from sandbox_os.command import TOOL, cards, partner, words
from sandbox_os.hosts import claude_code, codex
from sandbox_os.store.line import TEXT_MAX
from sandbox_os.store.seed import TYPES
from sandbox_os.pages import write
from sandbox_os.pages.frame import welcome_answers
from sandbox_os.pages.words import Words

STEPS = ("opening", "folder", "hosts", "welcome", "project", "first_run")
ENDS = ("answered", "skipped", "done")
LIMIT = {"folder": 120, "hosts": 180, "welcome": 300, "first_run": 600}  # seconds; the last runs from the welcome to the first run
HOSTS = (("claude", claude_code), ("codex", codex))  # the command each host is found by, and this release's adapter for it
ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")  # a person's words in Arabic script: lang "ar"
SYNCED = (("Library", "CloudStorage"), ("Library", "Mobile Documents"))
ICLOUD = ("Library", "Mobile Documents", "com~apple~CloudDocs")  # when iCloud syncs the Desktop or Documents in place, each appears here


def synced_roots(home):
    """The folders under a home whose contents leave the machine by the Mac's own sync: the cloud folders, and the Desktop or
    Documents when iCloud's sync of them is on (their entry exists inside iCloud Drive; read only, never opened)."""
    roots = [os.path.join(home, *x) for x in SYNCED]
    roots += [os.path.join(home, d) for d in ("Desktop", "Documents") if os.path.exists(os.path.join(home, *ICLOUD, d))]
    return roots
NINTH = ("system", "sandbox")  # the ninth's command file in its system/ folder
FENCE = "fence-user-settings"  # the welcome's fence card (contract section 9, row 95)
W, AR = Words("en"), Words("ar")
say = W.plain
SETTING = {w: k for k in ("little", "some", "often") for w in (k, AR.plain("setting." + k))}  # the ask setting in the table's words, English and Arabic
ANSWERS = dict(cards.KEYS, **{AR.plain("answer." + a).strip().lower(): a for a in ("yes", "no", "later")})  # a card's answer: keys and words
STUCK = re.compile(r"\s*(?:stuck|" + re.escape(AR.plain("stall.stuck").split("،")[0].strip()) + r")(?!\w)", re.I)  # stuck, or the table's Arabic for it
LOCALE = ("LC_ALL", "LC_MESSAGES", "LANG")  # the machine's locale, in POSIX order: it names welcome.md's language and is never asked


FIRST_CUT = re.compile(r"[,،]| for | with | لـ| ل(?=[\u0621-\u064A])")  # where the first thing's name ends in his sentence: a comma, for, with, or Arabic's attached for
FIRST_DROP = re.compile(r"(?:a|an|the|my)\s+", re.I)  # a leading article or my, dropped from the name
FIRST_FIT = {"facet": "fit", "value": "poor", "basis": "I read it in", "source": "welcome.md",  # the tool's reading of his sentence, kept there
             "reason": "the seed has no type near your words; build is the nearest"}
AR_ARTICLE, AR_SMALL = re.compile(r"^(?:[وفبك]?ال|لل)(?=\w{3})"), {"على", "عبر", "تحت", "فيه", "أحد", "كبير"}  # the article taken off; words that name no type


def propose_first(words, types):
    """The first thing proposed from his sentence: the name is his words up to the first comma, for, with or Arabic's attached for,
    a leading a, an, the or my dropped; the type is the first of `types` (rows with a name and a ground, in seed order) whose name or
    its plural with s, or whose ground's last segment split at capitals (schema.org/PodcastEpisode: podcast, episode), or a word of
    three letters or more of its ground's Arabic in the strings table (the seed names its types in English only), shares a word with
    the sentence, an Arabic word's article taken off; with none, build, and matched is false (03-design.md section 9 point 10)."""
    head = FIRST_CUT.split(" " + words.strip(), 1)[0].strip()
    name = FIRST_DROP.sub("", head, count=1).strip() if FIRST_DROP.match(head) else head
    name = name or words.strip()
    said = {AR_ARTICLE.sub("", x) for x in re.findall(r"\w+", words.lower())}
    for t in types:
        own = t["name"].lower().split()
        ground = t.get("ground") or ""
        seg = ground.rsplit("/", 1)[-1] if "/" in ground else ""
        ar = (AR.tab.get(("ground." + ground, "")) or {}).get("ar") or "" if ground else ""
        near = set(own) | {own[-1] + "s"} | {w.lower() for w in re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z]+", seg)}
        near |= {AR_ARTICLE.sub("", x) for x in re.findall(r"\w+", ar) if len(x) > 2 and x not in AR_SMALL}
        if near & said:
            return {"name": name, "type": t["name"], "matched": True}
    return {"name": name, "type": "build", "matched": False}


def is_ws(path):
    return bool(path) and os.path.isfile(os.path.join(path, "home.json")) and os.path.isdir(os.path.join(path, "projects"))


def secs(a, b):
    return round((b - a).total_seconds(), 3)


class Flow:
    def __init__(self, home, path_env, ask, out, terminal, clock, machine, serve, hidden, wait, env):
        self.home, self.path_env, self.ask, self.out, self.terminal, self.env = home, path_env, ask, out, terminal, env
        self.clock = clock or (lambda: _dt.datetime.now(_dt.timezone.utc))
        self.machine, self.serve, self.hidden, self.wait = machine, serve, hidden, wait
        self.inst = os.path.join(home, ".local", "share", "sandbox-os")
        self.held_path, self.session_path = os.path.join(self.inst, "held-lines.jsonl"), os.path.join(self.inst, "flow-session")
        self.s = self.address = self.given = self.session = None

    # the record: a workshop's lines once it exists, the install folder's held lines before
    def line(self, step, event, seconds=None, **extra):  # the person's own words in it (an answer, a refused value, a stall's) in Arabic: lang "ar"
        body = dict({"step": step, "event": event, "seconds": seconds}, **extra, **({"session": self.session} if self.session else {}))
        lang = "ar" if ARABIC.search(json.dumps([extra.get("words"), extra.get("value")], ensure_ascii=False)) else None
        if self.s:
            self.s.append("workshop", "flow", body, by=TOOL, lang=lang)
        else:
            self.hold(dict({"kind": "flow", "body": dict(body, at=iso(self.clock()))}, **({"lang": lang} if lang else {})))

    def hold(self, entry):
        os.makedirs(self.inst, exist_ok=True)
        with open(self.held_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def held(self):
        """What waits for a workshop: the opening's and the folder's flow lines, a synced folder's card and its answer, nothing else."""
        rows = [json.loads(r) for r in open(self.held_path, encoding="utf-8")] if os.path.exists(self.held_path) else []
        return [e for e in rows if e.get("kind") in ("card", "answer") or (e.get("kind") == "flow" and e["body"].get("step") in STEPS[:2])]

    def state(self):
        """The flow lines so far, each with _t, the time it happened (a held line's own, else the record's)."""
        if self.s:
            return [dict(l["body"], _t=l["body"].get("at") or l["t"]) for l in self.s.lines(unit="workshop", kinds=["flow"]) if l["by"]["kind"] == "tool"]
        return [dict(e["body"], _t=e["body"]["at"]) for e in self.held() if e["kind"] == "flow"]

    def opened_session(self, st):
        """The one session of this run of the welcome: the state file's while the flow is open (kept across a quit), else the newest
        flow line's, else minted now and written there; every flow line carries it (the release gate counts first runs by it)."""
        sid = open(self.session_path).read().strip() if os.path.exists(self.session_path) else ""
        sid = sid or next((b["session"] for b in reversed(st) if b.get("session")), None) or mint_id(int(self.clock().timestamp() * 1000))
        os.makedirs(self.inst, exist_ok=True)
        open(self.session_path, "w").write(sid + "\n")
        return sid

    def pointer(self):
        p = os.path.join(self.inst, "workshop")
        return (open(p).read().strip() or None) if os.path.exists(p) else None

    def open(self, root):
        """The workshop's record, the install folder pointing at it, and the held lines appended to it first, then let go."""
        self.s = _store.open(root, clock=self.clock, machine=self.machine)
        if self.pointer() != self.s.root:
            os.makedirs(self.inst, exist_ok=True)
            open(os.path.join(self.inst, "workshop"), "w").write(self.s.root + "\n")
        ids = {}
        for e in self.held():
            if e["kind"] == "flow":
                self.s.append("workshop", "flow", e["body"], by=TOOL, lang=e.get("lang"))
            elif e["kind"] == "card":
                ids[e["body"]["path"]] = cards.raise_(self.s, "workshop", e["body"], by=TOOL, before_act="a workshop in a synced folder", can_wait=False)
            elif ids.get(e["path"]):
                cards.answer(self.s, ids[e["path"]], e["answer"], by=TOOL, words=e["words"])
        os.remove(self.held_path) if os.path.exists(self.held_path) else None

    # a step's lines: shown, then stalls and refusals within it, then its end; over its time, a stall
    def begin(self, step):  # each step after a blank line, so the terminal reads in steps
        self.out("")
        self.line(step, "shown")
        self.t0 = self.started = self.clock()
        self.flowmd(step) if self.s else None

    def mid(self, step, event, **extra):
        now = self.clock()
        self.line(step, event, secs(self.t0, now), **extra)
        self.t0 = now

    def end(self, step, event, **extra):
        self.mid(step, event, **extra)
        self.over(step, secs(self.started, self.t0)) if secs(self.started, self.t0) > LIMIT.get(step, 1e9) else None

    def over(self, step, took):
        self.line(step, "stalled", cause="over time", limit=LIMIT[step], text=say("cli.stall.overtime", step=say("cli.step." + step),
                                                                                  seconds=f"{took:g}", limit=f"{LIMIT[step]} seconds"))

    def stuck(self, step, words):
        if not STUCK.match(words):
            return False
        self.mid(step, "stalled", cause="stuck", words=words)
        return True

    def flowmd(self, step=None):
        text = f"# {say('cli.flowmd.title')}\n\n" + (say("cli.flowmd.open", step=say("cli.step." + step)) if step else say("cli.flowmd.done")) + "\n"
        p = os.path.join(self.s.root, "flow.md")
        if not os.path.exists(p) or open(p, encoding="utf-8").read() != text:
            open(p, "w", encoding="utf-8").write(text)

    # the run, from wherever it stopped
    def run(self, folder):
        prev = self.pointer() if is_ws(self.pointer()) else None
        if folder and is_ws(folder):
            self.open(folder)
            self.out(say("cli.pointer", path=self.s.root)) if prev != self.s.root else None
        elif folder:
            self.given = folder
        elif prev:
            self.open(prev)
        st = self.state()
        done = [b for b in st if b["step"] == "flow" and b["event"] == "done"]
        if self.s and done:
            self.session = done[-1].get("session") or mint_id(int(self.clock().timestamp() * 1000))  # the welcome's own, on its later lines
            return self.after()
        self.session = self.opened_session(st)
        done = {b["step"] for b in st if b["event"] in ENDS}
        todo = [s for s in STEPS if s not in done]
        if st and todo and not (st[-1]["step"] in STEPS and st[-1]["event"] in ENDS):  # left mid-step: the time away is a quit's
            self.line(todo[0], "stalled", secs(parse_t(st[-1]["_t"]), self.clock()), cause="quit",
                      text=say("cli.stall.quit", step=say("cli.step." + todo[0])))
        if "opening" in done and todo:
            self.out(say("cli.flow.resume", step=say("cli.step." + todo[0])))
        for step in todo:
            r = getattr(self, step)()
            if r is not None:
                return r
        return self.finish()

    def opening(self):  # card 39: the third sentence counts the steps, the same on every machine; it reads no earlier welcome
        [self.out(t) for t in (say("cli.flow.what"), say("cli.flow.next"), say("cli.flow.long"), "", say("cli.flow.stuck"))]
        self.line("opening", "shown")
        self.line("opening", "done", 0)

    def folder(self):
        self.begin("folder")
        while True:
            typed = self.given if self.given is not None else self.ask(say("cli.folder.ask"))
            self.given = None
            if self.stuck("folder", typed):
                continue
            if not typed.strip():
                self.out(say("cli.folder.again"))
                continue
            t = typed.strip()
            path = os.path.abspath(self.home + t[1:] if t == "~" or t.startswith("~/") else t)
            why = self.refusal(path)
            if why:
                self.out(why)
                self.mid("folder", "refused", value=path, cause=why)
                continue
            root = next((r for r in synced_roots(self.home) if path.startswith(r + os.sep)), None)
            if root:
                answer, words = self.card(path, root)
                if answer == "later":
                    self.out(say("cli.card.later"))
                    self.mid("folder", "stalled", cause="later", words=words)
                    return 1
                if answer == "no":
                    continue
            os.makedirs(path, exist_ok=True)
            self.open(path)
            self.end("folder", "answered", value=self.s.root)
            return self.out(say("cli.folder.made", path=self.s.root))

    def refusal(self, path):
        """Why a typed folder is not used: the ninth's (named by the rule, never listed), a file, or a folder neither empty nor a
        workshop, its visible entries named and its hidden ones counted."""
        if os.path.isfile(os.path.join(path, *NINTH)) or (self.hidden and os.path.isdir(os.path.join(path, self.hidden))):
            return say("cli.folder.ninth", path=path)
        if os.path.exists(path) and not os.path.isdir(path):
            return say("cli.folder.file", path=path)
        names = [n for n in os.listdir(path) if n != ".DS_Store"] if os.path.isdir(path) and not is_ws(path) else []
        if not names:
            return None
        seen = sorted(n + ("/" if os.path.isdir(os.path.join(path, n)) else "") for n in names if not n.startswith("."))
        hidden = sum(1 for n in names if n.startswith("."))
        parts = seen[:12] + ([say("cli.folder.more", n=len(seen) - 12)] if len(seen) > 12 else []) + ([W.plain("cli.count.hidden", hidden)] if hidden else [])
        return say("cli.folder.full", path=path, contents=", ".join(parts))

    def card(self, path, root):
        """The first-leaving card, held until a workshop exists, raised once per folder, answered in the terminal; card 50: in the language
        the welcome is about to record, as the fence card is."""
        body = dict(cards.five("cli.card", lang=self.language()[0]["value"], path=path, root=root), purpose="first-leaving", path=path)
        if not any(e["kind"] == "card" and e["body"].get("path") == path for e in self.held()):
            self.hold({"kind": "card", "body": body})
        [self.out(t) for t in (say("cli.synced", path=path, root=root), say("cli.card.show", decides=body["decides"]), say("cli.card.showstand", stand=body["stand"]),
                               say("cli.card.showother", other=body["other"]), say("cli.card.showwrong", wrong=body["wrong"]))]
        while True:
            words = self.ask(say("cli.card.prompt"))
            answer = ANSWERS.get(words.strip().lower().rstrip(".!,،"))
            if answer:
                break
        if answer != "later":
            self.hold({"kind": "answer", "path": path, "answer": answer, "words": words})
        self.out(say("cli.card.open")) if answer == "yes" else None
        return answer, words

    def found(self):  # each host found by reading PATH, never run: (its command, this release's adapter for it, its path)
        return [(n, a, p) for n, a in HOSTS for p in [next((os.path.join(d, n) for d in self.path_env.split(os.pathsep)
                                                            if d and os.path.isfile(os.path.join(d, n)) and os.access(os.path.join(d, n), os.X_OK)), None)] if p]

    def user(self, a, scope="user"):  # an adapter's scopes under this home: the user settings it writes on the fence card's yes, and the rest
        scopes = a.scope_paths(self.home, self.s.root) if hasattr(a, "scope_paths") else \
            {"user": os.path.join(self.home, ".claude", "settings.json"), "local": os.path.join(self.s.root, ".claude", "settings.local.json")}
        return scopes[scope] if scope else scopes

    def hosts(self):
        """Each host found gets its adapter's files, named by hash in a placed note; then the one fence card with every host's user-scope lines."""
        self.begin("hosts")
        self.s.seed(by=TOOL)  # the vocabulary and the verbs first, so the plan placed and the fence card's lines carry the asks derived from them
        found = self.found()
        [self.place_host(n, a, p) for n, a, p in found]
        if not any(a for _, a, _ in found):
            self.out(say("cli.host.none"))
            self.mid("hosts", "stalled", cause="error", text=say("cli.stall.nohost"))
            return 1
        self.fence_card([a for _, a, _ in found if a])
        self.end("hosts", "done", value=[n for n, _, _ in found])

    def place_host(self, n, a, p):
        self.out(say("cli.host.found", host=n, path=p))
        if a is None:
            return self.out(say("cli.host.noadapter", host=n))
        placed = partner.place(self.s.root, host=a.NAME, home=self.home, clock=self.clock)  # the flow's clock on every line the hosts step writes
        settings = a.write_settings(self.s.root, user_scope=False, clock=self.clock)
        over = a.overrides(self.s.root, scopes=self.user(a, None), clock=self.clock)
        files = [placed["instructions"]["path"]] + [os.path.join(self.s.root, f) for f in ("charter.md", "book.md", "grants.md")] + settings.get("files", [settings["path"]])
        self.s.append("workshop", "note", {"event": "placed", "host": a.NAME, "files": [{"path": f, "sha256": hashlib.sha256(open(f, "rb").read()).hexdigest()} for f in files if os.path.exists(f)],
                                           "text": say("cli.note.placed", host=n)}, by=TOOL)
        self.out(say("cli.host.placed", host=n))
        if not settings["written"] or any(o["key"] in ("permissions.defaultMode", "approval_policy") for o in over):
            self.out(say("cli.host.noprompt", host=n))

    def back(self, n, c, d, st):
        """Card 42: a placed file gone missing is asked about once, in a card; his yes places it again, once, with a note naming the card and the yes."""
        if st == "yes":
            claude_code.instruction_file(self.s.root, clock=self.clock) if n == "CLAUDE.md" else partner.put(self.s.root, n)
            self.s.append("workshop", "note", {"event": "placed-again", "file": n, "card": c["id"], "yes": d["id"], "text": say("cli.placed.note", file=n)}, by=TOOL)
            return self.out(say("cli.placed.done", file=n))
        new = cards.raise_(self.s, "workshop", dict(cards.five("cli.placed", lang=cards.language(self.s.root), file=n), purpose=f"placed:{n}", file=n,
                                                   **({"changed": {"ruling": d["id"], "card": c["id"]}} if c else {})), by=TOOL)
        c and new and self.s.link(new, "follows", c["id"], by=TOOL)
        self.out(say("cli.placed.raised", file=n))

    def fence_card(self, adapters):
        """The welcome's fence card with each found host's user-scope lines, raised once; a host found after it brings it back as its next version
        naming the new host, whose lines wait on a fresh yes (the old yes writes nothing for them)."""
        card = self.fence_of()
        card and self.fence()  # a yes already given writes what its card named before a new version asks for the rest
        new = [a.NAME for a in adapters if a.NAME not in (card["body"].get("paths") or {claude_code.NAME: 1} if card else {})]
        if not card or new:
            user, lang = self.user(adapters[0]), cards.language(self.s.root, self.language()[0]["value"])  # card 38: in the welcome's language; card 50: before it, the one it is about to record
            c = cards.raise_(self.s, "workshop", dict(cards.five("cli.fence", "", lang=lang, path=user), purpose=FENCE, path=user, paths={a.NAME: self.user(a) for a in adapters},
                                                      **self.plan_text([l for a in adapters for l in a.settings_plan(self.s.root, True)], lang),
                                                      **({"changed": {"hosts": new, "card": card["id"]}} if card else {})), by=TOOL)
            card and c and self.s.link(c, "follows", card["id"], by=TOOL)
            self.out(say("cli.fence.raised"))
        self.fence()

    def plan_text(self, plan, lang="en"):  # the card's saw: the whole plan when it fits a line's text, else its first lines and the whole kept beside as a payload
        text = "\n".join(plan)
        if len(text.encode()) <= TEXT_MAX:
            return {"saw": text}
        sha, shown, size = self.s.payload(text.encode(), unit="workshop"), [], 0
        for l in plan:
            if size + len(l.encode()) + 1 > TEXT_MAX - 400:
                break
            shown.append(l)
            size += len(l.encode()) + 1
        return {"saw": "\n".join(shown + [words(lang).plain("cli.fence.more", n=len(plan) - len(shown), sha=sha)]), "saw_payload": sha}

    def fence_of(self):  # the fence card's newest version
        return next((c for c in reversed(self.s.lines(unit="workshop", kinds=["card"])) if (c["body"] or {}).get("purpose") == FENCE), None)

    def fence(self):
        """On the maker's standing yes to the fence card, each host's entries into its user settings, once, each step read back."""
        card = self.fence_of()
        d = card and cards.decision(self.s, card["id"])
        done = {n["body"].get("path") for n in self.s.lines(unit="workshop", kinds=["note"]) if n["body"].get("event") == "settings-written" and n["body"].get("written")}
        for name, path in ((card["body"].get("paths") or {claude_code.NAME: card["body"]["path"]}).items() if d and d["body"].get("answer") == "yes" else ()):
            if path not in done:
                {a.NAME: a for _, a in HOSTS if a}[name].write_settings(self.s.root, user_scope=True, path=path, yes=d["id"], clock=self.clock)
                self.out(say("cli.fence.written", path=path))

    def welcome(self):
        """The three things in the terminal (--terminal) or on the pages' welcome view, kept by the pages' own writer of welcome.md. A
        welcome.md with no answers in the record is a file, not an answer: it is set aside, named, and the questions are asked."""
        self.begin("welcome")
        path, vals, extra = os.path.join(self.s.root, "welcome.md"), None, {}
        if os.path.exists(path) and not self.recorded():
            found = next(f for f in (path + ".found" + (f"-{n}" if n else "") for n in range(1000)) if not os.path.exists(f))
            os.replace(path, found)
            self.out(say("cli.welcome.found", path=found))
            self.mid("welcome", "refused", value=found, cause=say("cli.welcome.found", path=found))
        if not os.path.exists(path) and self.terminal:
            vals, (lang, locale) = self.questions(), self.language()
            write.save_welcome(self.s, {"name": vals["name"], "making": vals["making"], "ask": vals["ask"], "language": lang["value"], "locale": locale})
            self.out(say("cli.welcome.kept"))
            extra = dict({"language": lang}, **({"typed": self.typed} if self.typed else {}))
        elif not os.path.exists(path):
            self.address = self.serve(self.s.root)
            [self.out(t) for t in (say("serve.address", address=self.address), say("cli.welcome.page"))]
            while not (os.path.exists(path) and self.recorded()):
                time.sleep(self.wait)
        vals = vals or {k: v for k, v in self.answers().items() if k in ("name", "making", "ask")}
        self.end("welcome", "answered" if any(v.strip() for v in vals.values()) else "skipped", value=vals, **extra)

    def language(self):
        """welcome.md's language: in the terminal the machine's locale when the strings table has it, else English, and English on the page,
        which writes it so (card 50: the cards raised before the welcome read it too); never asked, edited by hand in welcome.md."""
        var = next((v for v in LOCALE if self.env.get(v)), None) if self.terminal else None
        m = re.match(r"([A-Za-z]+)(?:_([A-Za-z]+))?", self.env[var]) if var else None
        words = Words(m.group(1).lower() if m else "en")
        loc = f"{words.lang}-{m.group(2).upper()}" if m and m.group(2) else None
        return ({"value": words.lang, "from": var and f"the machine's locale, {var}={self.env[var]}", "asked": False},
                loc if loc in words.locs and words.locs[loc]["language"] == words.lang else words.locale)

    def recorded(self):
        """Whether the record holds the pages' lines for the three questions (save_welcome writes one each with welcome.md)."""
        return {"name", "making", "ask"} <= {b["step"] for b in self.state()}

    def answers(self):
        return welcome_answers(open(os.path.join(self.s.root, "welcome.md"), encoding="utf-8").read(), W)

    def questions(self):
        """The five acts, then the three things in the terminal, each question before its hint, with its default and a skip; skip all
        keeps every default."""
        [self.out(say(t)) for t in ("acts.list", "acts.leaves", "acts.where-yes", "cli.welcome.head")]
        vals, self.typed = {"name": "", "making": "", "ask": ""}, {}
        for k in vals:
            prompt = "\n".join([say("welcome." + k), say("welcome." + k + ".hint")] + [say("ask." + o) for o in ("little", "some", "often") if k == "ask"])
            while True:
                a = self.ask(prompt)
                if a.strip().lower() == "skip all":
                    return vals
                if self.stuck("welcome", a):
                    continue
                if k == "ask" and a.strip() and a.strip().lower() not in SETTING:  # asked again: a stall, the maker's words verbatim
                    self.mid("welcome", "stalled", cause="asked again", words=a)
                    prompt = say("cli.welcome.choose")
                    continue
                if k == "ask" and a.strip() and SETTING[a.strip().lower()] != a:  # the table's word kept as typed, the setting in English
                    self.typed["ask"], a = a, SETTING[a.strip().lower()]
                vals[k] = a
                break
        return vals

    def project(self):
        self.begin("project")
        words = self.answers().get("making", "")
        if not words.strip():
            self.out(say("cli.project.none"))
            return self.end("project", "skipped")
        unit = re.sub(r"[^a-z0-9]+", "-", words.lower()).strip("-")[:48].strip("-") or "first-project"
        unit = "workshop-project" if unit == "workshop" else unit
        folder = os.path.join(self.s.root, "projects", unit)  # ASCII by the unit rule; the name stays the maker's words, verbatim
        os.makedirs(os.path.join(folder, ".agents", "skills"), exist_ok=True)
        if unit not in self.s.units():
            self.s.append(unit, "note", {"event": "project-made", "words": words, "text": say("cli.note.project")}, by=TOOL, lang="ar" if ARABIC.search(words) else None)
        self.out(say("cli.project.made", path=os.path.join("projects", unit), words=words))
        r = self.first(unit, words)
        if r is not None:
            return r
        self.end("project", "done", value={"unit": unit, "words": words, "folder": folder})

    def first(self, unit, words):
        """The unit's first thing, once: proposed from his sentence, named by him in the terminal (Enter keeps the proposed name, stuck
        a stall), from his sentence on the pages' welcome; one object by the tool, a poor fit said when no seed type is near, and the
        named line with what he typed, verbatim."""
        self.s.seed(by=TOOL)
        if any((l["body"] or {}).get("first") for l in self.s.lines(unit=unit, kinds=["object"])):
            return None
        p = propose_first(words, TYPES)
        kind = say("cli.first.an" if p["type"][:1] in "aeiou" else "cli.first.a", type=p["type"])
        typed = ""
        if self.terminal:
            self.out(say("cli.first.propose", name=p["name"], type=kind))
            while True:
                typed = self.ask(say("cli.first.ask"))
                if not self.stuck("project", typed):
                    break
        name = typed.strip() or p["name"]
        o = self.s.append(unit, "object", {"type": p["type"], "name": name, "first": True}, by=TOOL, lang="ar" if ARABIC.search(name) else None)
        if not p["matched"]:
            self.s.append(unit, "fact", dict(FIRST_FIT), by=TOOL, about=o)
            self.out(say("cli.first.nearest"))
        self.out(say("cli.first.made", name=name, type=kind))
        self.mid("project", "named", words=typed, value={"id": o, "name": name, "type": p["type"]})

    def first_run(self):
        self.begin("first_run")
        lines = [f"cd {shlex.quote(self.s.root)} && {n}" for n, a, _ in self.found() if a] or [f"cd {shlex.quote(self.s.root)} && claude"]
        address = self.address or self.serve(self.s.root)
        [self.out(t) for t in (say("cli.start.both" if len(lines) > 1 else "cli.start", line=lines[0]), say("cli.start.say"), say("serve.address", address=address))]
        self.end("first_run", "done", value=lines[0], lines=lines)

    def finish(self):
        """The done line: seconds, the whole passage by the clock from the opening's first line; recorded, the steps' sum; and the
        difference, unaccounted. The sentence on the screen says only that the welcome is done."""
        st = self.state()
        recorded = round(sum(b["seconds"] for b in st if b["step"] != "flow" and isinstance(b.get("seconds"), (int, float))), 3)
        whole = secs(parse_t(st[0]["_t"]), self.clock())
        stalls = [{"step": b["step"], "event": b["event"], "cause": b["cause"]} for b in st if b["event"] in ("stalled", "refused")]
        self.line("flow", "done", whole, recorded=recorded, unaccounted=round(whole - recorded, 3), stalls=stalls)
        os.remove(self.session_path) if os.path.exists(self.session_path) else None  # the next welcome mints its own
        self.flowmd()
        self.out(say("cli.done"))  # the seconds and the stalls stay on the done line, off the screen: nobody is timed (R-READ-13)
        return 0

    def after(self):
        """A workshop whose welcome is done: the first run's time once it has come (seconds since the done line), once, a stall if it
        came (or has not come) ten minutes after the welcome, the fence on the maker's yes, and the pages."""
        ls = self.s.lines(unit="workshop", kinds=["flow"])
        ev = lambda step, events: [l for l in ls if l["body"]["step"] == step and l["body"]["event"] in events]
        done, w = ev("flow", ("done",))[-1], ev("welcome", ENDS)
        ran = self.s.lines(kinds=["run"], since=done["t"])
        if ran and not ev("first_run", ("opened",)):
            self.line("first_run", "opened", secs(parse_t(done["t"]), parse_t(ran[0]["t"])), run=ran[0]["id"])
        if w and not ev("first_run", ("stalled",)):
            took = secs(parse_t(w[-1]["t"]), parse_t(ran[0]["t"]) if ran else self.clock())
            self.over("first_run", took) if took > LIMIT["first_run"] else None
        found, placed = [x for x in self.found() if x[1]], {l["body"].get("host") for l in self.s.lines(unit="workshop", kinds=["note"]) if l["body"].get("event") == "placed"}
        [self.back(n, *x) for n, x in partner.gone(self.s).items() if x[2] in ("ask", "yes") and (n != "CLAUDE.md" or claude_code.NAME in placed)]  # card 42
        [self.place_host(n, a, p) for n, a, p in found if a.NAME not in placed]  # a host found after the welcome gets its files, after a missing one is asked about
        self.fence_card([a for _, a, _ in found]) if found else self.fence()
        self.out(say("serve.address", address=self.serve(self.s.root)))
        return 0


def run(home, *, path_env="", ask=input, out=print, terminal=False, folder=None, clock=None, machine=None, serve=None, hidden=None, wait=0.5, env=None):
    """The flow on this home's install folder: 0 when it is done (or was), 1 when it waits at a step (a stall, a refusal, a card for
    later, a closed terminal), with every line it wrote. `hidden` names a hidden folder of the ninth's; tests supply it, the tool does not."""
    f = Flow(home, path_env, ask, out, terminal, clock, machine, serve, hidden, wait, os.environ if env is None else env)
    try:
        return f.run(os.path.abspath(folder) if folder else None)
    except EOFError:
        return 1
    except _store.Refused as e:
        out(str(e))
        return 1
