# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The index: a cache in cache/index-2.sqlite, caught up from the files at every read, holding the lines, links, marks and holds, and answering find, present, as-of and counts."""
import datetime as _dt
import collections, hashlib, json, os, re, sqlite3, time

from sandbox_os.store.line import (KINDS, RELATIONS, CLAIM_KINDS, FACT_KINDS, IMPLIED, canonical, links_of, ends_ok,
                                   text_of, strip_arabic_marks, iso, parse_t, one_space, local_date, day_end)
from sandbox_os.store.log import _read, _rows, _stat
from sandbox_os.store import gate, verbs

SCHEMA = """
CREATE TABLE lines(id TEXT PRIMARY KEY, unit TEXT, seq INT, t TEXT, kind TEXT, by_kind TEXT, by_name TEXT, by_model TEXT,
  by_host TEXT, version TEXT, lang TEXT, valid_until TEXT, about TEXT, file TEXT, row INT, hash TEXT, prev TEXT, erased TEXT, body TEXT,
  text TEXT, named_late INT, world_moved INT);
CREATE INDEX lines_unit ON lines(unit, seq); CREATE INDEX lines_kind ON lines(kind, t); CREATE INDEX lines_prev ON lines(unit, prev);
CREATE INDEX lines_about ON lines(about, t);
CREATE TABLE links(made TEXT, frm TEXT, rel TEXT, target TEXT, t TEXT, outside INT);
CREATE INDEX links_target ON links(target, rel); CREATE INDEX links_frm ON links(frm, rel);
CREATE TABLE marks(id TEXT PRIMARY KEY, mark TEXT, since TEXT, set_by TEXT);
CREATE TABLE holds(delete_id TEXT PRIMARY KEY, target TEXT, start TEXT, end_at TEXT, taken_back TEXT, erased INT);
CREATE TABLE consumed(file TEXT PRIMARY KEY, bytes INT, size INT, mtime INT, sha TEXT, last_hash TEXT, lines INT);
CREATE TABLE rejected(file TEXT, row INT, id TEXT, what TEXT);
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE objects(id TEXT PRIMARY KEY, unit TEXT, type TEXT, name TEXT, ground TEXT, t TEXT);
CREATE TABLE facets(object TEXT, facet TEXT, value TEXT, basis TEXT, source TEXT, line TEXT, t TEXT, confidence TEXT, standing INT);
CREATE INDEX facets_obj ON facets(object, facet, t);
CREATE VIRTUAL TABLE fts USING fts5(text, content='lines', content_rowid='rowid', tokenize='unicode61 remove_diacritics 2');
"""
SCHEMA_SHA = hashlib.sha256(SCHEMA.encode()).hexdigest()  # kept in meta; an index built with another schema is rebuilt when opened
COLS = ("l.id, l.t, l.kind, l.by_kind, l.by_name, l.by_model, l.by_host, l.version, l.unit, l.seq, l.prev, l.hash, l.body, "
        "l.lang, l.valid_until, l.about, m.mark, m.since, m.set_by, l.named_late, l.world_moved")
SELECT = f"SELECT {COLS} FROM lines l LEFT JOIN marks m ON m.id = l.id"
DOWN = ("erased", "deleted", "struck")
OUT = DOWN + ("superseded",)  # a line with one of these marks no longer stands for what it says
ACTING = set(IMPLIED) | {"link", "brief", "grant_back", "erase", "join"}
INDEX_FILE = "index-2.sqlite"  # the eleventh's own name: the installed tenth keeps cache/index.sqlite in the same workshop until the move, untouched
RESTS, LEANS = "rests on a struck line", ("came_from", "serves")  # the mark a correction spreads along the two relations a line leans on
BODIES = ("check", "receipt", "answer", "card", "brief", "delete", "link")
BASIS = "l.kind = 'fact' AND json_extract(l.body, '$.basis') = ?"  # a fact with this basis: he said, a check showed, I read it in, my guess
RETYPED = ("(SELECT json_extract(f.value, '$') FROM facets f JOIN lines fl ON fl.id = f.line WHERE f.object = {} AND f.facet = 'type' "
           "AND f.standing = 1 ORDER BY f.t DESC, fl.seq DESC LIMIT 1)")  # a thing's type moved by its newest standing type fact
LIVE_TYPES = "SELECT o.name FROM objects o JOIN lines l ON l.id = o.id WHERE json_extract(l.body, '$.type') = 'type'"
TOUCHED = ("(coalesce(ol.by_kind, '') != 'tool' OR json_extract(ol.body, '$.first') = 1 OR EXISTS (SELECT 1 FROM lines x WHERE x.about = ol.id "
           "AND coalesce(x.by_kind, '') != 'tool'{}))")  # not only the tool's: the object line ol, its first thing he named at the welcome, or
# a line about it by another hand (review of batch D, finding 7), by a cut when one is given; the one rule in_hand and graph read
NOT_THINGS = ("type", "relation", "verb")  # the vocabulary's own objects, never drawn as things
UNUSED = "types and relations with no new line about their things in the last {} days, from the index now"


def _dict(r):
    d = {"id": r[0], "t": r[1], "kind": r[2], "by": dict(zip(("kind", "name", "model", "host", "version"), r[3:8])),
         "unit": r[8], "seq": r[9], "prev": r[10], "hash": r[11], "body": json.loads(r[12]) if r[12] else None}
    d.update({k: v for k, v in (("lang", r[13]), ("valid_until", r[14]), ("about", r[15])) if v})
    d.update(mark=r[16], mark_since=r[17], mark_set_by=r[18])
    if d["kind"] == "check":  # named after a standing check of the same run, name and command went green
        d["named_late"] = bool(r[19])
        d["world_moved"] = bool(r[20])  # red where nothing changed since the last green of its command: the world moved, not the work
    return d


def _level_one(L, inc):
    """Erased, deleted and struck, which depend only on the acts that name a line and whether those acts stand."""
    m1 = {}

    def lvl(x):
        if x not in m1:
            m1[x], r = None, L.get(x)
            if r and r[7] and r[7] in L:
                m1[x] = ("erased", L[r[7]][1], r[7])
            elif r:
                for want, mark in (("deletes", "deleted"), ("strikes", "struck")):
                    hit = next((m for m, f, rel in inc[x] if rel == want and stands(m) and stands(f)), None)
                    if hit:
                        m1[x] = (mark, L[hit][1], hit)
                        break
        return m1[x]

    def stands(i):
        return i in L and lvl(i) is None
    for x in sorted(L, key=lambda i: L[i][1:4], reverse=True):
        lvl(x)
    return lvl, stands


def _struck(typ, live):
    """A thing is of a struck type when its present type is no standing type's name (struck, deleted, erased or superseded); 'type' and
    'relation' are the tool's own words for the vocabulary's objects and are never struck."""
    return typ not in live and typ not in ("type", "relation")


def _ground(g):
    return g if g is None or isinstance(g, str) else canonical(g)


class Index:
    def _connect(self):
        path = self._p("cache", INDEX_FILE)
        self._conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self._conn.execute("PRAGMA secure_delete=ON")
        self._ino = os.stat(path).st_ino

    def _db(self):
        """The index, opened, built if missing, and caught up with the files."""
        try:
            ino = os.stat(self._p("cache", INDEX_FILE)).st_ino
        except FileNotFoundError:
            ino = None
        if self._conn is None or ino != self._ino:
            self._conn and self._conn.close()
            self._conn = None
            if ino is None:
                self.rebuild_index()
            else:
                self._connect()
                if self._meta("schema") != SCHEMA_SHA:
                    self.rebuild_index()
        if not (self._fresh and self._depth):
            self._catch_up()
        return self._conn

    def rebuild_index(self):
        """Builds the index afresh from the files into a new file that replaces the old; returns what it read and what it left out."""
        started = time.monotonic()
        with self.locked(timeout=30), gate.replaying():
            new = self._p("cache", INDEX_FILE + ".new")
            for f in (new, new + "-journal"):
                os.path.exists(f) and os.remove(f)
            c = sqlite3.connect(new, isolation_level=None)
            c.executescript(SCHEMA)
            c.execute("INSERT INTO meta(key, value) VALUES('schema', ?)", (SCHEMA_SHA,))
            c.execute("BEGIN")
            for u in self.units():
                for path in self._files(u):
                    self._consume(c, path, _read(path), 0, 0, None, fts=False)
            self._derive(c, rebuild=True)
            self._carry_shapes(c)
            c.execute("INSERT INTO fts(fts) VALUES('rebuild')")
            c.execute("COMMIT")
            c.close()
            self._conn and self._conn.close()
            os.replace(new, self._p("cache", INDEX_FILE))
            self._connect()
            self._fresh = True
            n = self._conn.execute("SELECT count(*) FROM lines").fetchone()[0]
            rej = [dict(zip(("file", "row", "id", "what"), r)) for r in self._conn.execute("SELECT * FROM rejected ORDER BY file, row")]
        return {"seconds": round(time.monotonic() - started, 3), "lines": n, "rejected": rej}

    def _catch_up(self):
        """Reads in lines appended since the index last looked; any other change to a file rebuilds the index."""
        c, day = self._conn, local_date(self.clock()).isoformat()
        rels = {os.path.relpath(f, self.root): f for u in self.units() for f in self._files(u)}
        have = {r[0]: r[1:] for r in c.execute("SELECT file, bytes, size, mtime, sha, last_hash, lines FROM consumed")}
        stale = [r for r, f in rels.items() if have.get(r, (0, 0, 0))[1:3] != _stat(f)]
        if not stale and set(have) <= set(rels) and self._meta("day") == day:
            self._fresh = True
            return
        with self.locked(timeout=30), gate.replaying():
            if set(have) - set(rels):
                return self.rebuild_index()
            c.execute("BEGIN")
            new = []
            for r in stale:
                data = _read(rels[r])
                b, _, _, sha, last, n = have.get(r, (0, 0, 0, hashlib.sha256(b"").hexdigest(), None, 0))
                if len(data) < b or hashlib.sha256(data[:b]).hexdigest() != sha:
                    c.execute("ROLLBACK")
                    return self.rebuild_index()
                new += self._consume(c, rels[r], data, b, n, last)
            self._derive(c, only=new if self._meta("day") == day else None)
            c.execute("COMMIT")
            self._fresh = True

    def _meta(self, key):
        r = self._conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return r and r[0]

    def _consume(self, c, path, data, start, n, last, fts=True):
        """Puts the whole lines after byte `start` into the lines and links tables; an unknown kind or relation is left out and recorded in rejected."""
        rel, end, ids = os.path.relpath(path, self.root), data.rfind(b"\n") + 1, []
        for k, b in enumerate(_rows(data[start:end]), n + 1):
            try:
                obj = json.loads(b)
                body = obj["body"] if isinstance(obj.get("body"), dict) else {}
            except (ValueError, AttributeError):
                c.execute("INSERT INTO rejected VALUES(?,?,?,?)", (rel, k, None, "not a JSON object"))
                continue
            i, kind, by, last = obj.get("id"), obj.get("kind"), obj.get("by") or {}, obj.get("hash")
            if kind not in KINDS:
                c.execute("INSERT INTO rejected VALUES(?,?,?,?)", (rel, k, i, f"unknown kind: {kind}"))
                continue
            erased = body.get("by") if body.get("erased") is True else None
            text = None if erased else strip_arabic_marks(text_of(body))
            cur = c.execute("INSERT OR IGNORE INTO lines VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)", (
                i, obj.get("unit"), obj.get("seq"), obj.get("t"), kind, by.get("kind"), by.get("name"), by.get("model"),
                by.get("host"), by.get("version"), obj.get("lang"), obj.get("valid_until"), obj.get("about"), rel, k, obj.get("hash"),
                obj.get("prev"), erased, None if erased else canonical(body), text))
            if not cur.rowcount:
                continue
            if fts and text:
                c.execute("INSERT INTO fts(rowid, text) VALUES(?, ?)", (cur.lastrowid, text))
            ids.append(i)
            for frm, r_, to in [] if erased else links_of(obj):
                if r_ in RELATIONS or isinstance(r_, str) and kind == "link":  # a relation between things is kept; _derive keeps it only between two objects
                    c.execute("INSERT INTO links VALUES(?,?,?,?,?,0)", (i, frm, r_, to, obj.get("t")))
                else:
                    c.execute("INSERT INTO rejected VALUES(?,?,?,?)", (rel, k, i, f"relation outside the list: {r_}"))
        st = _stat(path)
        c.execute("INSERT OR REPLACE INTO consumed VALUES(?,?,?,?,?,?,?)", (
            rel, end, st[0], st[1], hashlib.sha256(data[:end]).hexdigest(), last, n + len(_rows(data[start:end]))))
        return ids

    def _derive(self, c, only=None, rebuild=False):
        """Computes every mark and hold from the lines and links; when the new lines act on nothing, only their own marks."""
        today = local_date(self.clock()).isoformat()  # his local day, as the pages read a month and a week
        c.execute("INSERT OR REPLACE INTO meta VALUES('day', ?)", (today,))
        only = None if only is not None and len(only) > 900 else only
        q = ",".join("?" * len(only or ()))
        fast = only is not None and not c.execute(f"SELECT 1 FROM lines WHERE id IN ({q}) AND kind IN ({','.join('?' * len(ACTING))}) "
                                              f"UNION SELECT 1 FROM links WHERE target IN ({q}) UNION SELECT 1 FROM links WHERE frm IN ({q}) AND rel IN {LEANS}",
                                              (*only, *ACTING, *only, *only)).fetchone()  # a new line that leans on another takes the full path
        if fast:
            L = {r[0]: r for r in c.execute(f"SELECT id, t, unit, seq, kind, by_kind, valid_until, erased FROM lines WHERE id IN ({q})", only)}
            lvl, stands, inc, out, B = (lambda x: None), (lambda x: True), collections.defaultdict(list), collections.defaultdict(list), {}
        else:
            L = {r[0]: r for r in c.execute("SELECT id, t, unit, seq, kind, by_kind, valid_until, erased FROM lines")}
            B = {i: json.loads(b) for i, b in c.execute(f"SELECT id, body FROM lines WHERE body IS NOT NULL AND kind IN {BODIES}")}
            inc, out = collections.defaultdict(list), collections.defaultdict(list)
            for made, frm, rel, target in c.execute("SELECT made, frm, rel, target FROM links ORDER BY t, made").fetchall():
                fk, tk = (L[frm][4] if frm in L else None), (L[target][4] if target in L else None)
                bad = (None if fk == tk == "object" else f"relation outside the list: {rel}") if rel not in RELATIONS else (  # between things
                    None if ends_ok(rel, fk, tk, frm in L and target in L and L[frm][2] != L[target][2] and L[target][3] == 1)
                    else f"link ends outside the rules: {rel}")
                if bad:
                    c.execute("DELETE FROM links WHERE made=? AND rel=? AND target=?", (made, rel, target))
                    c.execute("INSERT INTO rejected SELECT file, row, id, ? FROM lines WHERE id=?", (bad, made))
                    continue
                inc[target].append((made, frm, rel))
                out[frm].append((made, rel, target))
            c.execute("UPDATE links SET outside = 1 - (target IN (SELECT id FROM lines) AND frm IN (SELECT id FROM lines))")
            lvl, stands = _level_one(L, inc)

        def followed(s):
            return any(rel == "follows" and stands(m) and stands(f) and L[f][4] == L[s][4] for m, f, rel in inc[s] if f in L)

        def proving(s):
            b = B.get(s, {})
            if L[s][4] == "check":  # by the tool, exit 0, its output kept, not followed by a newer check
                return L[s][5] == "tool" and b.get("exit") == 0 and isinstance(b.get("output"), dict) and isinstance(b["output"].get("payload"), str) and not followed(s)
            return (L[s][5] == "tool" and b.get("opened") is True and not followed(s)) if L[s][4] == "receipt" else L[s][5] == "maker"
        yes_answers = {a for a, b in B.items() if L[a][4] == "answer" and b.get("answer") == "yes" and L[a][5] == "maker" and stands(a)
                       and b.get("presence") != "none" and b.get("stale") is not True}  # no person at the desk, or a stale page: binds nothing
        yes = {B.get(tgt, {}).get("about") for a in yes_answers for m, rel, tgt in out[a]  # only the answer's own link, to a card, whose about is the line
               if rel == "answers" and m == a and tgt in L and L[tgt][4] == "card"}
        marks = {}
        for x, r in L.items():
            m = lvl(x)
            if m is None:
                sup = next((mm for mm, f, rel in inc[x] if rel == "supersedes" and stands(mm) and stands(f)), None)
                prv = next((f for mm, f, rel in inc[x] if rel == "proves" and stands(mm) and stands(f) and proving(f) and (mm == f or L[f][4] not in  # row 98:
                            ("check", "receipt") or isinstance(B.get(mm, {}).get("reason"), str) and B[mm]["reason"].strip())), None)  # a check's link says why
                waits = (r[4] == "grant" or (r[4] == "about_you" and r[5] == "partner")) and x not in yes
                m = (("superseded", L[sup][1], sup) if sup else ("past", r[6], None) if r[6] and r[6] < today else
                     ("waiting", r[1], None) if waits else ("proved", L[prv][1], prv) if prv else
                     ("not yet" if r[4] in CLAIM_KINDS and r[5] != "maker" else "recorded", r[1], None))
            marks[x] = m

        def rests(x):
            """The nearest struck, deleted, erased or superseded line x leans on through came_from and serves, as x's mark; else None."""
            seen, todo = {x}, [x]
            while todo:
                nxt = []
                for y in todo:
                    for made, rel, tgt in out[y]:
                        if rel in LEANS and stands(made) and tgt in marks and tgt not in seen:
                            if marks[tgt][0] in OUT:
                                return (RESTS, marks[tgt][1], tgt)
                            seen.add(tgt)
                            nxt.append(tgt)
                todo = nxt
        # waiting is never replaced: a line that still needs the maker's yes keeps needing it, so a strike can never widen a grant
        leaning = {x: rests(x) for x, m in marks.items() if m[0] in ("recorded", "not yet") and L[x][4] not in ("check", "receipt")}
        marks.update({x: m for x, m in leaning.items() if m})
        old = {r[0]: r[1:] for r in (c.execute(f"SELECT id, mark, since, set_by FROM marks WHERE id IN ({q})", only) if fast
                                     else c.execute("SELECT id, mark, since, set_by FROM marks"))}
        for x, m in marks.items():
            if old.get(x) != m:
                c.execute("INSERT OR REPLACE INTO marks VALUES(?,?,?,?)", (x, *m))
                if (m[0] in ("deleted", "erased")) != ((old.get(x) or ("",))[0] in ("deleted", "erased")):
                    self._show(c, x, m[0] not in ("deleted", "erased"), rebuild)
        self._things(c, marks, only if fast else None)
        if not fast:
            self._late(c, L, B, marks)
            self._moved(c, L, B, marks)
            listed = {}
            for b in sorted((i for i in B if L[i][4] == "brief"), key=lambda i: L[i][1]):
                for d in B[b].get("listed") or []:
                    listed.setdefault(d, L[b][1])
            c.execute("DELETE FROM holds")
            for d, r in L.items():
                tgt = next((t for m, rel, t in out[d] if rel == "deletes"), None) if r[4] == "delete" else None
                if tgt:
                    start = r[1] if r[5] == "maker" else listed.get(d)
                    end = iso(parse_t(start) + _dt.timedelta(days=int(B.get(d, {}).get("hold_days") or 7))) if start else None
                    c.execute("INSERT INTO holds VALUES(?,?,?,?,?,?)", (d, tgt, start, end, (lvl(d) or (0, 0, None))[2], int(bool(L.get(tgt) and L[tgt][7]))))

    def _late(self, c, L, B, marks):
        """Flags a check named late: it says when it was named (named_at) and a check of the same run, name and command (compared
        null-safe, the command's whitespace made single) went green, exit 0 with its output kept, before that time; every green check
        written counts, struck, superseded or deleted (a deleted one read from its file), since the flag says it had passed before it was
        named and a strike does not undo that; only an erased line is gone. Another line green at that very moment counts, as batch A's
        rule had it, and so does the line itself when it went green before its own naming. A check that names no time was named when it
        ran; running it again is not late."""
        B = dict(B, **{i: json.loads(_rows(_read(self._p(f)))[r - 1])["body"] for i, f, r in c.execute(
            "SELECT id, file, row FROM lines WHERE kind = 'check' AND body IS NULL AND erased IS NULL").fetchall()})
        checks = [x for x in L if L[x][4] == "check" and isinstance(B.get(x), dict)]
        green = collections.defaultdict(list)
        for x in checks:
            b = B[x]
            if b.get("exit") == 0 and isinstance(b.get("output"), dict):
                green[(canonical(b.get("run")), canonical(b.get("name")), canonical(one_space(b.get("command"))))].append(x)
        late = set()
        for x in checks:
            at = B[x].get("named_at") if isinstance(B[x].get("named_at"), str) else None
            key = (canonical(B[x].get("run")), canonical(B[x].get("name")), canonical(one_space(B[x].get("command"))))
            if at is not None and any(L[y][1] < at or L[y][1] == at and y != x for y in green[key]):
                late.add(x)
        was = {i for (i,) in c.execute("SELECT id FROM lines WHERE named_late = 1")}
        for x in was ^ late:
            c.execute("UPDATE lines SET named_late = ? WHERE id = ?", (int(x in late), x))

    def _moved(self, c, L, B, marks):
        """Flags a red check whose cause is the world (batch E, Task 15): exit not 0 with a state, and the newest earlier standing check of
        the same unit and the same command (whitespace made single) that exited 0 has the same state; a changed folder, another command or
        no earlier green is not the world. Computed with the marks, so a struck green stands for nothing."""
        newest, moved = {}, set()
        for x in sorted((x for x in L if L[x][4] == "check" and isinstance(B.get(x), dict)), key=lambda x: (L[x][1], L[x][3])):
            b, key = B[x], (L[x][2], canonical(one_space(B[x].get("command"))))
            if isinstance(b.get("exit"), int) and b["exit"] != 0 and isinstance(b.get("state"), dict) and key in newest:
                moved |= {x} if B[newest[key]].get("state") == b["state"] else set()
            if b.get("exit") == 0 and marks.get(x, ("",))[0] not in OUT:
                newest[key] = x
        was = {i for (i,) in c.execute("SELECT id FROM lines WHERE world_moved = 1")}
        for x in was ^ moved:
            c.execute("UPDATE lines SET world_moved = ? WHERE id = ?", (int(x in moved), x))

    def _things(self, c, marks, only):
        """Fills the objects table from the standing object lines and the facets table from the facts about them, standing = 1 for the
        standing ones; a fact taken away keeps its row as its shape only (facet, basis, confidence), its value and source gone, read once
        from its file when the index never saw it whole, so calibration counts a deleted belief without its words; only the new lines when
        only is given."""
        if only is None:
            c.execute("DELETE FROM objects")
            c.execute("DELETE FROM facets WHERE line NOT IN (SELECT id FROM lines WHERE kind = 'fact' AND body IS NULL)")
            c.execute("UPDATE facets SET value = NULL, source = NULL, standing = 0")
        q = f" AND id IN ({','.join('?' * len(only))})" if only is not None else ""
        kept = {r[0] for r in c.execute("SELECT line FROM facets")}
        for i, u, t, k, ab, b, file, row in c.execute("SELECT id, unit, t, kind, about, body, file, row FROM lines WHERE kind IN ('object', 'fact') "
                                                      f"AND (body IS NOT NULL OR kind = 'fact'){q}", only or ()).fetchall():
            gone = b is None
            if gone and (i in kept or not ab):
                continue
            b = json.loads(_rows(_read(self._p(file)))[row - 1])["body"] if gone else json.loads(b)  # a deleted fact's file body, for its shape
            if k == "object":
                if marks.get(i, ("",))[0] not in OUT:
                    g = b.get("ground")
                    c.execute("INSERT OR REPLACE INTO objects VALUES(?,?,?,?,?,?)",
                              (i, u, b.get("type"), b.get("name"), g if g is None or isinstance(g, str) else canonical(g), t))
            elif ab and isinstance(b, dict) and isinstance(b.get("facet"), str):
                src, conf = b.get("source") if isinstance(b.get("source"), str) else None, b.get("confidence") if isinstance(b.get("confidence"), str) else None
                c.execute("DELETE FROM facets WHERE line = ?", (i,))
                c.execute("INSERT INTO facets VALUES(?,?,?,?,?,?,?,?,?)", (ab, b["facet"], None if gone else canonical(b.get("value")), b.get("basis"),
                                                                           None if gone else src, i, t, conf, int(marks.get(i, ("",))[0] not in OUT)))
        mine = "" if only is None else f" WHERE id IN (SELECT coalesce(about, id) FROM lines WHERE id IN ({','.join('?' * len(only))}))"
        c.execute(f"UPDATE objects SET type = coalesce({RETYPED.format('objects.id')}, type){mine}", only or ())  # the body's type is the fallback

    def _carry_shapes(self, c):
        """At a rebuild, an erased fact's shape (its facet, basis and confidence, never its words) is carried from the index it replaces,
        since its file no longer holds it; an index built with nothing before it has none to carry."""
        old = self._p("cache", INDEX_FILE)
        erased = [r[0] for r in c.execute("SELECT id FROM lines WHERE kind = 'fact' AND erased IS NOT NULL AND id NOT IN (SELECT line FROM facets)")]
        if not erased or not os.path.exists(old):
            return
        try:
            o = sqlite3.connect(f"file:{old}?mode=ro", uri=True)
            rows = o.execute(f"SELECT object, facet, basis, line, t, confidence FROM facets WHERE line IN ({','.join('?' * len(erased))})", erased).fetchall()
            o.close()
        except sqlite3.Error:
            return
        c.executemany("INSERT INTO facets VALUES(?,?,NULL,?,NULL,?,?,?,0)", rows)

    def beliefs(self):
        """Every fact about a thing by its shape, in time order: line, object, facet, basis, confidence, t, mark, and value (None once it is
        taken away), from the facets table, so a deleted or erased belief is still counted and never read in words."""
        cols = ("line", "object", "facet", "basis", "confidence", "t", "mark", "value")
        return [dict(zip(cols, r[:-1] + (None if r[-1] is None else json.loads(r[-1]),))) for r in self._db().execute(
            "SELECT f.line, f.object, f.facet, f.basis, f.confidence, f.t, m.mark, f.value FROM facets f LEFT JOIN marks m ON m.id = f.line "
            "ORDER BY f.t, f.line")]

    def _show(self, c, x, visible, rebuild):
        """Takes a deleted line's words out of the index's text and find, or puts them back when the deletion is taken back."""
        rowid, text, file, row = c.execute("SELECT rowid, text, file, row FROM lines WHERE id=?", (x,)).fetchone()
        if not visible:
            if text and not rebuild:
                c.execute("INSERT INTO fts(fts, rowid, text) VALUES('delete', ?, ?)", (rowid, text))
            c.execute("UPDATE lines SET body=NULL, text=NULL WHERE id=?", (x,))
            return
        body = json.loads(_rows(_read(self._p(file)))[row - 1])["body"]
        text = strip_arabic_marks(text_of(body))
        c.execute("UPDATE lines SET body=?, text=? WHERE id=?", (canonical(body), text, x))
        if not rebuild and text:
            c.execute("INSERT INTO fts(rowid, text) VALUES(?, ?)", (rowid, text))

    def _heads(self, unit):
        return [dict(zip(("id", "seq", "hash"), r)) for r in self._db().execute(
            "SELECT id, seq, hash FROM lines l WHERE unit=? AND NOT EXISTS (SELECT 1 FROM lines m WHERE m.unit=l.unit AND m.prev=l.hash) "
            "AND l.hash NOT IN (SELECT json_extract(h.value, '$.hash') FROM lines j, json_each(j.body, '$.heads') h "
            "WHERE j.unit=l.unit AND j.kind='join') ORDER BY seq", (unit,))]

    def get(self, id):
        """One line by id, with its mark; a deleted or erased line comes back with body None."""
        r = self._db().execute(SELECT + " WHERE l.id=?", (id,)).fetchone()
        return _dict(r) if r else None

    def lines(self, *, unit=None, kinds=None, since=None, until=None, about=None, basis=None):
        """Lines from the index in time order, each with its mark: about one thing, or facts with one basis, when asked."""
        w, a = ["1"], []
        for cond, val in (("l.unit=?", unit), ("l.t>=?", since), ("l.t<=?", until), ("l.about=?", about), (BASIS, basis)):
            if val is not None:
                w.append(cond)
                a.append(val)
        if kinds:
            w.append(f"l.kind IN ({','.join('?' * len(kinds))})")
            a += list(kinds)
        return [_dict(r) for r in self._db().execute(f"{SELECT} WHERE {' AND '.join(w)} ORDER BY l.t, l.unit, l.seq", a)]

    def marks(self, id):
        r = self._db().execute("SELECT mark FROM marks WHERE id=?", (id,)).fetchone()
        return r and r[0]

    def find(self, query, *, unit=None, kinds=None, limit=20, about=None, basis=None):
        """Full text over every kept line, BM25 then newest; nothing found is said plainly, with lines holding some of the words and the unit's present line when the query names a unit.
        about keeps the lines about one thing, basis the facts with one basis; a hit about a thing names it."""
        q = strip_arabic_marks(str(query))
        phrases = [" ".join(re.findall(r"\w+", p)) for p in re.findall(r'"([^"]*)"', q)]
        terms = [p for p in phrases if p] + re.findall(r"\w+", re.sub(r'"[^"]*"?', " ", q))
        c = self._db()
        extra = (" AND (l.unit = ? OR l.id IN (SELECT k.frm FROM links k JOIN lines o ON o.id = k.target LEFT JOIN marks km ON km.id = k.made "  # card 22:
                 f"WHERE k.rel = 'part_of' AND o.unit = ? AND coalesce(km.mark, '') NOT IN {DOWN}))" if unit else "") + (  # about the unit, by part_of
            f" AND l.kind IN ({','.join('?' * len(kinds))})" if kinds else "") + (
            " AND l.about = ?" if about is not None else "") + (f" AND {BASIS}" if basis is not None else "")
        args = [*([unit, unit] if unit else []), *(kinds or []), *([about] if about is not None else []), *([basis] if basis is not None else [])]

        def run(match, n):
            return c.execute(f"SELECT {COLS}, snippet(fts, 0, '[', ']', '…', 12), l.text FROM fts CROSS JOIN lines l ON l.rowid = fts.rowid "
                             f"LEFT JOIN marks m ON m.id = l.id WHERE fts MATCH ?{extra} ORDER BY bm25(fts), l.t DESC LIMIT ?",
                             (match, *args, n)).fetchall() if terms else []
        quoted = ['"' + t + '"' for t in terms]
        forms = [q_ + ("*" if re.fullmatch(r"[^\W_]{4,}", t) else "") for q_, t in zip(quoted, terms)]  # other forms: words of 4+ letters as prefixes
        hits = [self._hit(r, terms) for r in run(" ".join(quoted), limit)]
        formed = not hits and forms != quoted and [self._hit(r, terms) for r in run(" ".join(forms), limit)]
        hits = hits or formed or []
        some = [self._hit(r, terms) for r in run(" OR ".join(forms), limit)] if not hits and len(terms) > 1 else []
        [h.update(about_unit=unit if unit and h["unit"] != unit else None) for h in hits + some]  # card 22: a hit from another unit says which unit it is about
        units = set(self.units())
        named = next((u for u in [q.strip().lower()] + [t.lower() for t in terms] if u in units), None)
        said = (f"nothing found for “{query}” as written; these lines hold other forms of its words" if formed else None if hits else
                f"nothing found for “{query}”" + ("; below, lines with some of the words" if some else ""))
        return {"query": query, "hits": hits, "nothing_found": not hits, "said": said, "some": some,
                "present": self._present_line(named) if named else None}

    def _hit(self, r, terms):
        d, c, words = _dict(r[:-2]), self._conn, set(re.findall(r"\w+", (r[-1] or "").lower()))  # COLS, then the snippet and the text
        formed = [w for w in (t.lower() for t in terms) if w not in words and any(x.startswith(w) for x in words)]
        side = ("SELECT o.id, o.t, substr(coalesce(o.text, ''), 1, 160) FROM links k JOIN lines o ON o.id = k.{0} "
                "LEFT JOIN marks km ON km.id = k.made WHERE k.{1} = ? AND k.rel = 'supersedes' "
                "AND coalesce(km.mark, '') NOT IN ('erased', 'deleted', 'struck') ORDER BY o.t DESC LIMIT 1")
        rep, by = c.execute(side.format("target", "frm"), (d["id"],)).fetchone(), c.execute(side.format("frm", "target"), (d["id"],)).fetchone()
        o = self.get(d["about"]) if d.get("about") else None  # the thing's own line, so a struck thing is still named
        thing = (o["id"], (o["body"] or {}).get("name"), (o["body"] or {}).get("type")) if o else None
        return {"id": d["id"], "t": d["t"], "kind": d["kind"], "unit": d["unit"], "by": d["by"], "mark": d["mark"],
                "proved": d["mark"] == "proved", "snippet": r[-2], "matched": "word forms" if formed else "words",
                "about": dict(zip(("id", "name", "type"), thing)) if thing else None,
                "replaced": dict(zip(("id", "t", "snippet"), rep)) if rep else None,
                "replaced_by": dict(zip(("id", "t", "snippet"), by)) if by else None}

    def _present_line(self, unit):
        r = self._db().execute(f"{SELECT} WHERE l.unit=? AND l.kind='present' AND coalesce(m.mark, '') NOT IN {DOWN} "
                               "ORDER BY l.t DESC, l.seq DESC LIMIT 1", (unit,)).fetchone()
        return _dict(r) if r else None

    def present(self, unit):
        """The unit's newest standing present line, its newest twenty lines with marks, and its counts."""
        rows = self._db().execute(f"{SELECT} WHERE l.unit=? ORDER BY l.t DESC, l.seq DESC LIMIT 20", (unit,)).fetchall()
        return {"unit": unit, "present": self._present_line(unit), "newest": [_dict(r) for r in rows], "counts": self.counts(unit)}

    def counts(self, unit):
        c = self._db()
        by_kind = dict(c.execute("SELECT kind, count(*) FROM lines WHERE unit=? GROUP BY kind ORDER BY kind", (unit,)))
        by_mark = dict(c.execute("SELECT m.mark, count(*) FROM lines l JOIN marks m ON m.id = l.id WHERE l.unit=? GROUP BY m.mark ORDER BY m.mark", (unit,)))
        out = ",".join("?" * len(OUT))  # world_moved counts the standing red checks only (the review of batch E, finding 11e)
        late, moved = c.execute(f"SELECT sum(named_late = 1), sum(world_moved = 1 AND id NOT IN (SELECT id FROM marks WHERE mark IN ({out}))) "
                                "FROM lines WHERE unit=? AND kind='check'", (*OUT, unit)).fetchone()
        return {"unit": unit, "lines": sum(by_kind.values()), "by_kind": by_kind, "by_mark": by_mark, "named_late": late or 0, "world_moved": moved or 0,
                "counts": "lines in this unit's record, every kind and mark included, computed from the index now; named_late counts "
                          "the checks named after one of the same run, name and command went green; world_moved the standing red checks "
                          "whose folder was as it stood at the last green of their command"}

    def stood(self, unit, as_of):
        """The fact lines that stood on a date, from the index alone: written by then and not struck, deleted, erased or superseded by a line written by then, nor past."""
        day = as_of.isoformat()[:10] if hasattr(as_of, "isoformat") else str(as_of)[:10]
        c, cut = self._db(), day_end(day)
        L = {r[0]: r for r in c.execute("SELECT id, t, unit, seq, kind, by_kind, valid_until, erased FROM lines WHERE t <= ?", (cut,))}
        inc = collections.defaultdict(list)
        for made, frm, rel, target in c.execute("SELECT made, frm, rel, target FROM links WHERE t <= ? ORDER BY t, made", (cut,)):
            inc[target].append((made, frm, rel))
        lvl, stands = _level_one(L, inc)
        keep = [x for x, r in L.items() if r[2] == unit and r[4] in FACT_KINDS and stands(x) and not (r[6] and r[6] < day)
                and not any(rel == "supersedes" and stands(m) and stands(f) for m, f, rel in inc[x])]
        return sorted((self.get(x) for x in keep), key=lambda d: (d["t"], d["seq"]))

    def holds(self, *, ended=None):
        """Every deletion's hold: when it started and ends, whether it was taken back or erased, and its state now."""
        now, out = iso(self.clock()), []
        for r in self._db().execute("SELECT * FROM holds ORDER BY start, delete_id"):
            h = dict(zip(("delete", "target", "start", "end", "taken_back", "erased"), r))
            h["state"] = ("taken back" if h["taken_back"] else "erased" if h["erased"] else "not started" if not h["start"]
                          else "ended" if h["end"] <= now else "running")
            if ended is None or ended == (h["state"] == "ended") and h["state"] in ("ended", "running", "not started"):
                out.append(h)
        return out

    def heads(self):
        return {u: self._heads(u) for u in self.units()}

    def grant_state(self, id):
        """A grant's state, computed: read_back until the maker's yes, standing from then, taken_back, or past after its until."""
        g = self.get(id)
        if not g or g["kind"] != "grant":
            return None
        if g["mark"] in DOWN or g["mark"] == "superseded":  # a superseded reading covers nothing
            return g["mark"]
        back = self._conn.execute(f"SELECT 1 FROM lines l JOIN marks m ON m.id = l.id WHERE l.kind='grant_back' AND "
                                  f"json_extract(l.body, '$.grant') = ? AND m.mark NOT IN {DOWN}", (id,)).fetchone()
        until = (g["body"] or {}).get("until")
        return ("taken_back" if back else "past" if until and until < local_date(self.clock()).isoformat()
                else "read_back" if g["mark"] == "waiting" else "standing")

    def _summary(self, r, live):
        return dict(zip(("id", "unit", "type", "name", "ground", "t"), r), type_struck=_struck(r[2], live))

    def _live(self, c):
        return {n for (n,) in c.execute(LIVE_TYPES)}

    def thing(self, id):
        """A thing's read: its object line, type, name and ground, its aliases, its present facets (the newest standing fact per facet,
        with its basis), its standing questions, assumptions and goals, its newest 20 lines, the things linked to it, its newest 5 struck or superseded lines
        and the verbs that reach it (verbs.reaching)."""
        c, o = self._db(), self.get(id)
        if not o or o["kind"] != "object":
            return None
        b, facets, aliases = o["body"] or {}, {}, []
        for f, v, basis, src, line, t in c.execute("SELECT f.facet, f.value, f.basis, f.source, f.line, f.t FROM facets f JOIN lines l ON l.id = f.line "
                                                   "WHERE f.object=? AND f.standing = 1 ORDER BY f.t, l.seq", (id,)):
            facets[f] = {"value": json.loads(v), "basis": basis, "source": src, "line": line, "t": t}
            if f == "alias":
                aliases.append(facets[f]["value"])

        def about(kinds=None, marks=None, n=None, out=OUT):
            w = (f" AND l.kind IN ({','.join('?' * len(kinds))})" if kinds else "") + (
                f" AND coalesce(m.mark, '') IN ({','.join('?' * len(marks))})" if marks else f" AND coalesce(m.mark, '') NOT IN {out}" if kinds else "")
            order = " ORDER BY l.t DESC, l.seq DESC LIMIT ?" if n else " ORDER BY l.t, l.seq"
            return [_dict(r) for r in c.execute(f"{SELECT} WHERE l.about=?{w}{order}", (id, *(kinds or ()), *(marks or ()), *([n] if n else ())))]
        related = []
        for rel, frm, to in c.execute("SELECT k.rel, k.frm, k.target FROM links k JOIN objects a ON a.id = k.frm JOIN objects z ON z.id = k.target "
                                      f"LEFT JOIN marks m ON m.id = k.made WHERE ? IN (k.frm, k.target) AND coalesce(m.mark, '') NOT IN {DOWN} "
                                      "ORDER BY k.t, k.made", (id,)).fetchall():
            other = to if frm == id else frm
            _, _, typ, name, _, _ = c.execute("SELECT * FROM objects WHERE id=?", (other,)).fetchone()
            related.append({"rel": rel, "id": other, "name": name, "type": typ, "direction": "out" if frm == id else "in"})
        typ = c.execute(f"SELECT coalesce({RETYPED.format('?')}, ?)", (id, b.get("type"))).fetchone()[0]
        return {"object": o, "type": typ, "type_struck": _struck(typ, self._live(c)),
                "name": b.get("name"), "ground": b.get("ground"), "aliases": aliases, "facets": facets,
                "questions": about(["question"], out=OUT + ("past",)), "assumptions": about(["assumption"]), "goals": about(["goal"]),
                "lines": about(n=20), "related": related, "struck": about(marks=["struck", "superseded"], n=5), "verbs": verbs.reaching(self, id)}

    def in_hand(self, unit=None, limit=None, among=None):
        """The ids of the standing things in hand, newest touched first (the newest time among a thing's object line and every line about
        it), from the index in one query: of a unit (every unit for None or the workshop), never a type, a relation or a verb, and never a
        thing only the tool has touched (TOUCHED; the first thing he named counts as his); or, given among, those of these ids that are standing objects, whoever touched them. At most limit."""
        w, a = [], []
        if among is not None:
            ids = [i for i in among if isinstance(i, str)]
            w.append(f"o.id IN ({','.join('?' * len(ids))})" if ids else "0")
            a += ids
        else:
            w += ["o.type NOT IN ('type', 'relation', 'verb')", TOUCHED.format("")]
            if unit not in (None, "workshop"):
                w.append("o.unit = ?")
                a.append(unit)
        q = (f"SELECT o.id FROM objects o JOIN lines ol ON ol.id = o.id WHERE {' AND '.join(w)} ORDER BY max(o.t, coalesce((SELECT max(l.t) "
             f"FROM lines l WHERE l.about = o.id), '')) DESC, o.id DESC" + (" LIMIT ?" if limit is not None else ""))
        return [r[0] for r in self._db().execute(q, a + ([int(limit)] if limit is not None else []))]

    def things(self, *, type=None, unit=None, without=None, days=None):
        """The standing things, in time order: of a type, in a unit, and with no standing line of the kind `without` about them in the last `days` days."""
        w, a = ["1"], []
        for cond, val in (("o.type=?", type), ("o.unit=?", unit)):
            if val is not None:
                w.append(cond)
                a.append(val)
        if without is not None:
            since = iso(self.clock() - _dt.timedelta(days=days)) if days is not None else ""
            w.append(f"NOT EXISTS (SELECT 1 FROM lines l LEFT JOIN marks m ON m.id = l.id WHERE l.about = o.id AND l.kind = ? AND l.t >= ? "
                     f"AND coalesce(m.mark, '') NOT IN {OUT})")
            a += [without, since]
        c = self._db()
        live = self._live(c)
        return [self._summary(r, live) for r in c.execute(f"SELECT * FROM objects o WHERE {' AND '.join(w)} ORDER BY o.t, o.id", a)]

    def unused(self, *, days=90, as_of=None):
        """The standing types and relations nobody touched in the `days` days before as_of (a date or YYYY-MM-DD, the end of his local day; now by the
        store's clock when None), by name: a type whose own line is older than that and about none of whose things (their object lines
        included) a standing line was written since, with how many things are of it now; a relation as old, with no standing link line of
        its name since, with how many stand; each with its newest such time, or None (design section 2 point 5). For a day given, all of it
        as it stood at that day's end, from the lines written by then (_unused_then), so a later line never changes a day once read."""
        from sandbox_os.store import Refused
        try:
            day = as_of.isoformat()[:10] if hasattr(as_of, "isoformat") else None if as_of is None else str(as_of)[:10]
            end = self.clock() if day is None else parse_t(day_end(day))
        except ValueError:
            raise Refused(f"as_of is a day, YYYY-MM-DD; {str(as_of)[:40]!r} is not one") from None
        c, cut, got = self._db(), iso(end - _dt.timedelta(days=days)), {"type": [], "relation": []}
        for kind, i, name, t, n, last in (self._unused_now(c) if day is None else self._unused_then(c, day_end(day))):
            if t < cut and (last is None or last < cut):
                got[kind].append({"id": i, "name": name, "objects" if kind == "type" else "links": n, "last": last})
        return {"days": days, "as_of": day or local_date(end).isoformat(), "types": got["type"], "relations": got["relation"],
                "counts": UNUSED.format(days)}

    def _unused_now(self, c):
        """Each standing type and relation from the present index: (kind, id, name, its line's time, its count, its newest touch)."""
        stand = f"coalesce(m.mark, '') NOT IN {OUT}"
        for kind in ("type", "relation"):
            for i, name, t in c.execute("SELECT o.id, o.name, l.t FROM objects o JOIN lines l ON l.id = o.id WHERE json_extract(l.body, '$.type') = ? "
                                        "ORDER BY o.name, o.id", (kind,)).fetchall():
                if kind == "type":
                    n = c.execute("SELECT count(*) FROM objects WHERE type = ?", (name,)).fetchone()[0]
                    last = c.execute(f"SELECT max(t) FROM (SELECT t FROM objects WHERE type = ? UNION ALL SELECT l.t FROM lines l LEFT JOIN marks m "
                                     f"ON m.id = l.id WHERE l.about IN (SELECT id FROM objects WHERE type = ?) AND {stand})", (name, name)).fetchone()[0]
                else:
                    n, last = c.execute(f"SELECT count(*), max(k.t) FROM links k LEFT JOIN marks m ON m.id = k.made WHERE k.rel = ? AND {stand}",
                                        (name,)).fetchone()
                yield kind, i, name, t, n, last

    def _unused_then(self, c, end):
        """The same rows as they stood at end (Astra's challenge of batch D, finding 10): membership, marks, re-typing and touches from the
        lines written by then alone, each mark by a line written by then, as _world_then reads the world; a line deleted since has no
        words in the index, so its type fact is not read on any day."""
        L = {r[0]: r for r in c.execute("SELECT id, t, unit, seq, kind, by_kind, valid_until, erased FROM lines WHERE t <= ?", (end,))}
        links, inc = c.execute("SELECT made, frm, rel, target, t FROM links WHERE t <= ? ORDER BY t, made", (end,)).fetchall(), collections.defaultdict(list)
        for made, frm, rel, target, _ in links:
            inc[target].append((made, frm, rel))
        stands = _level_one(L, inc)[1]
        up = lambda x: stands(x) and not any(rel == "supersedes" and stands(m) and stands(f) for m, f, rel in inc[x])  # noqa: E731
        obj, typ, touch, of = {}, {}, collections.defaultdict(list), collections.defaultdict(list)
        for i, t, k, b, ab in c.execute("SELECT id, t, kind, body, about FROM lines WHERE t <= ? AND (about IS NOT NULL OR kind = 'object' AND "
                                        "body IS NOT NULL) ORDER BY t, seq", (end,)).fetchall():
            if not up(i):
                continue
            b = json.loads(b) if b else None
            if ab:
                touch[ab].append(t)
            if isinstance(b, dict) and k == "object":
                obj[i] = (t, b)
            elif isinstance(b, dict) and k == "fact" and ab and b.get("facet") == "type":
                typ[ab] = b.get("value")  # in time order, so the newest standing one is kept
        for i, (t, b) in obj.items():
            of[typ.get(i, b.get("type"))].append(i)
        for kind in ("type", "relation"):
            for i, (t, b) in sorted(((i, v) for i, v in obj.items() if v[1].get("type") == kind), key=lambda x: (str(x[1][1].get("name")), x[0])):
                name = b.get("name")
                ts = [obj[o][0] for o in of[name]] + [x for o in of[name] for x in touch[o]] if kind == "type" else \
                    [lt for m, _, r, _, lt in links if r == name and up(m)]
                yield kind, i, name, t, len(of[name]) if kind == "type" else len(ts), max(ts, default=None)

    def graph(self, as_of=None, types=None, units=None):
        """The things and the world relations between them, across units: now, from the present index, or as they stood at the end of his local day
        (a date or YYYY-MM-DD), from the lines written by then and the same cut stood uses (not struck, deleted, erased or superseded by a line
        written by then). A thing is an object that is not a type, a relation or a verb and that someone other than the tool touched (TOUCHED), as
        in_hand reads them; its type the newest standing type fact, else its own; its ground the newest standing ground fact, else its own;
        its type's ground and whether that type was struck. An edge is a standing link line of a standing relation's name between two kept
        things. types and units filter the things; nodes by (type, name, id), edges by (rel, from, to) (design section 9 point 3)."""
        from sandbox_os.store import Refused
        try:
            day = as_of.isoformat()[:10] if hasattr(as_of, "isoformat") else None if as_of is None else str(as_of)[:10]
            cut = day and day_end(day)
        except ValueError:
            raise Refused(f"as_of is a day, YYYY-MM-DD; {str(as_of)[:40]!r} is not one") from None
        objs, links, live, rels = self._world_now(self._db()) if day is None else self._world_then(self._db(), cut)
        keep = lambda x, f: f is None or x in ([f] if isinstance(f, str) else f)  # noqa: E731
        nodes = sorted(({"id": i, "name": n, "type": t, "unit": u, "ground": g, "type_ground": live.get(t), "type_struck": _struck(t, live)}
                        for i, n, t, u, g in objs if keep(t, types) and keep(u, units)), key=lambda n: (n["type"] or "", n["name"] or "", n["id"]))
        ids = {n["id"] for n in nodes}
        edges = sorted(({"id": m, "from": f, "to": t, "rel": r} for m, f, r, t in links if r in rels and f in ids and t in ids),
                       key=lambda e: (e["rel"], e["from"], e["to"]))
        return {"as_of": day, "nodes": nodes, "edges": edges, "counts": "things and the links between them that "
                + (f"stood on {day}" if day else "stand now") + ", from the index"}

    def _world_now(self, c):
        live = {n: g for n, g in c.execute("SELECT o.name, o.ground FROM objects o JOIN lines l ON l.id = o.id WHERE json_extract(l.body, '$.type') = 'type'")}
        rels = {n for (n,) in c.execute("SELECT o.name FROM objects o JOIN lines l ON l.id = o.id WHERE json_extract(l.body, '$.type') = 'relation'")}
        ground = {o: json.loads(v) for o, v in c.execute("SELECT f.object, f.value FROM facets f JOIN lines l ON l.id = f.line "
                                                         "WHERE f.facet = 'ground' AND f.standing = 1 ORDER BY f.t, l.seq")}  # the newest wins
        objs = [(i, n, t, u, _ground(ground[i]) if i in ground else g) for i, n, t, u, g in c.execute(
            "SELECT o.id, o.name, o.type, o.unit, o.ground FROM objects o JOIN lines ol ON ol.id = o.id WHERE json_extract(ol.body, '$.type') "
            f"NOT IN {NOT_THINGS} AND {TOUCHED.format('')}")]
        links = c.execute(f"SELECT k.made, k.frm, k.rel, k.target FROM links k JOIN lines l ON l.id = k.made AND l.kind = 'link' "
                          f"LEFT JOIN marks m ON m.id = k.made WHERE coalesce(m.mark, '') NOT IN {OUT}").fetchall()
        return objs, links, live, rels

    def _world_then(self, c, cut):
        """The world's parts as they stood at cut, from the lines alone; a line deleted or erased since has no words in the index, so it is
        not drawn on any day (a deleted line leaves the pages at once)."""
        L = {r[0]: r for r in c.execute("SELECT id, t, unit, seq, kind, by_kind, valid_until, erased FROM lines WHERE t <= ?", (cut,))}
        links, inc = c.execute("SELECT made, frm, rel, target FROM links WHERE t <= ? ORDER BY t, made", (cut,)).fetchall(), collections.defaultdict(list)
        for made, frm, rel, target in links:
            inc[target].append((made, frm, rel))
        lvl, stands = _level_one(L, inc)
        up = lambda x: stands(x) and not any(rel == "supersedes" and stands(m) and stands(f) for m, f, rel in inc[x])  # noqa: E731
        obj, facet = {}, collections.defaultdict(dict)
        for i, k, b, ab in c.execute("SELECT id, kind, body, about FROM lines WHERE t <= ? AND kind IN ('object', 'fact') AND body IS NOT NULL "
                                     "ORDER BY t, seq", (cut,)).fetchall():
            b = json.loads(b) if up(i) else None
            if isinstance(b, dict) and k == "object":
                obj[i] = b
            elif isinstance(b, dict) and ab and b.get("facet") in ("type", "ground"):
                facet[ab][b["facet"]] = b.get("value")  # in time order, so the newest standing one is kept
        live = {b.get("name"): _ground(b.get("ground")) for b in obj.values() if b.get("type") == "type"}
        rels = {b.get("name") for b in obj.values() if b.get("type") == "relation"}
        touched = {r[0] for r in c.execute(f"SELECT ol.id FROM lines ol WHERE ol.kind = 'object' AND ol.t <= ? AND {TOUCHED.format(' AND x.t <= ?')}",
                                           (cut, cut))}
        objs = [(i, b.get("name"), facet[i].get("type", b.get("type")), L[i][2], _ground(facet[i]["ground"] if "ground" in facet[i] else b.get("ground")))
                for i, b in obj.items() if b.get("type") not in NOT_THINGS and i in touched]
        return objs, [x for x in links if L.get(x[0], (0,) * 5)[4] == "link" and up(x[0])], live, rels

    def resolve(self, words):
        """The standing things whose name or a standing alias is these words, case-insensitive, Arabic marks stripped, in time order."""
        def bare(s):
            return strip_arabic_marks(str(s)).strip().lower()
        c, want = self._db(), bare(words)
        hit = {r[0] for r in c.execute("SELECT id, name FROM objects") if bare(r[1]) == want}
        hit |= {o for o, v in c.execute("SELECT object, value FROM facets WHERE facet='alias' AND standing = 1") if bare(json.loads(v)) == want}
        live = self._live(c)
        return [self._summary(r, live) for r in c.execute(f"SELECT * FROM objects WHERE id IN ({','.join('?' * len(hit))}) ORDER BY t, id", sorted(hit))]

    def rests_on(self, id):
        """Every line marked rests on a struck line whose path along came_from and serves reaches this line, in time order."""
        c, hit = self._db(), []
        for x in [r[0] for r in c.execute("SELECT id FROM marks WHERE mark=?", (RESTS,))]:
            seen, todo = {x}, [x]
            while todo and id not in seen:
                y = todo.pop()
                for (tgt,) in c.execute(f"SELECT k.target FROM links k LEFT JOIN marks m ON m.id = k.made WHERE k.frm=? AND k.rel IN {LEANS} "
                                        f"AND coalesce(m.mark, '') NOT IN {DOWN}", (y,)):
                    if tgt not in seen:
                        seen.add(tgt)
                        todo.append(tgt)
            if id in seen and x != id:
                hit.append(x)
        return sorted(map(self.get, hit), key=lambda d: (d["t"], d["unit"], d["seq"]))
