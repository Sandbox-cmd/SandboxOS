# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The files: where each line lives, the one lock, the home, the one door every line passes through, torn tails, joins after a merge, and verify."""
import datetime as _dt
import contextlib, fcntl, glob, hashlib, json, os, re, subprocess, sys, threading, time

from sandbox_os import VERSION
from sandbox_os.store import FORMAT, Refused, Busy
from sandbox_os.store.line import (KINDS, RELATIONS, LINE_MAX, UNIT_RE, ID_RE, T_RE, DATE_RE, canonical, line_hash,
                                   mint_id, iso, iso_ms, check_body, check_by, links_of, ends_ok, payload_refs, words_of)

GITATTR = "projects/*/record/*.jsonl merge=union\nprojects/*/record/sessions/*.jsonl merge=union\n"
TOOL = {"kind": "tool", "name": "sandbox-os", "model": None, "host": None}
FIELDS = {"id", "t", "kind", "by", "unit", "seq", "prev", "hash", "body"}
SESSION_RE = re.compile(r"[A-Za-z0-9._-]{1,128}\Z")


def _put(path, data, mode="ab"):
    """The one place the store writes a file: one write, then the full flush to disk (F_FULLFSYNC on macOS, fsync elsewhere), then return."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode) as f:
        f.write(data)
        f.flush()
        try:
            fcntl.fcntl(f.fileno(), fcntl.F_FULLFSYNC)
        except (AttributeError, OSError):
            os.fsync(f.fileno())


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _rows(data):
    """The whole lines of a log's bytes; anything after the last newline is a torn tail and is not a line."""
    end = data.rfind(b"\n")
    return data[:end].split(b"\n") if end >= 0 else []


def _record_file(data):
    """Whether a session file holds the record's lines: any whole row an object with the five fields a line carries. Such a file is the
    record's and is verified whole, so a row of another shape inside it fails (Astra's challenge of batch E, finding 3)."""
    for b in _rows(data):
        try:
            r = json.loads(b)
        except ValueError:
            continue
        if isinstance(r, dict) and {"id", "t", "kind", "by", "body"} <= set(r):
            return True
    return False


def _tail(path):
    """The last whole line of a file and any torn bytes after it, read backwards so an append never reads the whole log."""
    with open(path, "rb") as f:
        end = pos = f.seek(0, 2)
        buf = b""
        while pos > 0:
            pos = max(0, pos - 65536)
            f.seek(pos)
            buf = f.read(end - pos)
            nl = buf.rfind(b"\n")
            if nl >= 0 and (pos == 0 or buf.rfind(b"\n", 0, nl) >= 0):
                break
    nl = buf.rfind(b"\n")
    if nl < 0:
        return None, buf
    return json.loads(buf[buf.rfind(b"\n", 0, nl) + 1:nl]), buf[nl + 1:]


def _stat(path):
    st = os.stat(path)
    return st.st_size, st.st_mtime_ns


IOREG = "/usr/sbin/ioreg"  # by its own path: a narrow PATH (a host's hook, a scripted shell) must not turn this Mac's id into "unknown"


def _machine_id():
    try:
        out = subprocess.run([IOREG, "-rd1", "-c", "IOPlatformExpertDevice"], capture_output=True, text=True, timeout=10).stdout
        m = re.search(r'"IOPlatformUUID" = "([^"]+)"', out)
        return m.group(1) if m else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"



def _real_day(v):
    """Whether a value is a calendar day that exists, written YYYY-MM-DD."""
    try:
        return bool(DATE_RE.match(str(v))) and _dt.date.fromisoformat(str(v)) is not None
    except ValueError:
        return False

class Log:
    def _setup(self, root, read_only, clock, machine):
        self.root, self.version, self.read_only = os.path.realpath(root), VERSION, read_only
        self.clock = clock or (lambda: _dt.datetime.now(_dt.timezone.utc))
        self.machine = machine or _machine_id()
        self._depth, self._known, self._conn, self._ino, self._fresh, self._owner = 0, {}, None, None, False, None
        home = self._p("home.json")
        if not os.path.exists(home) and not read_only:
            os.makedirs(self._p("projects"), exist_ok=True)
            os.makedirs(self._p("cache"), exist_ok=True)
            _put(self._p(".gitattributes"), GITATTR.encode(), "wb")
            _put(home, (canonical({"format": FORMAT, "machine": self.machine, "path": self.root, "since": iso(self.clock())}) + "\n").encode(), "wb")
        self.home = json.loads(_read(home)) if os.path.exists(home) else None
        h = self.home or {}
        if h and h.get("machine") is None and not read_only and self.machine != "unknown":  # a fork, wholly the forker's: adopted (row 80)
            h = self.home = dict(h, machine=self.machine, path=self.root)
            _put(home, (canonical(h) + "\n").encode(), "wb")
        self._away = ("this workshop has no home.json, so it opens read-only" if not h else None
                      if (h.get("machine"), h.get("path")) == (self.machine, self.root) else
                      (f"this machine's id could not be read ({IOREG} gave none), so " if self.machine == "unknown" else "") +
                      ("this fork has no home yet, so it opens read-only until an open that may write adopts it" if h.get("machine") is None else
                       f"this record's home is {h.get('path')} on machine {h.get('machine')}; a copy anywhere else reads "
                       "everything and writes nothing, because a lease across machines is not built"))
        self._away = self._away or ("this store was opened read-only" if read_only else None)
        if not self._away and os.path.exists(self._p("cache", "reseal.pending")):
            with self.locked():
                self._finish_reseal(json.loads(_read(self._p("cache", "reseal.pending"))))
        if not self._away and h.get("format", 1) < FORMAT:  # an older record opens at this format by one line, rewriting none (row 96)
            self._migrate(h.get("format", 1))

    def _migrate(self, was):
        """One migration line in the workshop unit by the tool, then home.json names the format; no line already written is touched."""
        with self.locked():
            self.home = json.loads(_read(self._p("home.json")))  # read again under the lock: a second process opening at once migrates nothing
            if self.home.get("format", 1) >= FORMAT:
                return
            self._append("workshop", "migration", {"from": was, "to": FORMAT, "rewritten": 0, "text": f"format {was} to {FORMAT}: lines may carry "
                         "about; five kinds added; a fact about a thing carries its basis; nothing rewritten"}, by=TOOL)
            self.home = dict(self.home, format=FORMAT)
            _put(self._p("home.json"), (canonical(self.home) + "\n").encode(), "wb")

    def _p(self, *parts):
        return os.path.join(self.root, *parts)

    def units(self):
        d = self._p("projects")
        return sorted(u for u in (os.listdir(d) if os.path.isdir(d) else []) if os.path.isdir(os.path.join(d, u, "record")))

    def unit_dir(self, unit):
        return self._p("projects", unit, "record")

    def _files(self, unit):
        """A unit's yearly logs, under its record/ folder only: projects/<unit>/play/ is never read, counted, indexed or verified (R-STORE-PLAY-1)."""
        # the play rule (R-STORE-PLAY-1) by construction: one folder, projects/<unit>/record/, only its yearly names, never a walk,
        # and only regular files, so a symbolic link (to play/ or anywhere) is never followed; verify names it
        return sorted(f for f in glob.glob(os.path.join(self.unit_dir(unit), "[0-9][0-9][0-9][0-9].jsonl")) if not os.path.islink(f) and os.path.isfile(f))

    def _log_path(self, unit, t, session=None):
        return os.path.join(self.unit_dir(unit), *(("sessions", session + ".jsonl") if session is not None else (t[:4] + ".jsonl",)))

    @property
    def away(self):
        """Why this record takes no writes here (opened read-only, no home.json, a copy whose home is elsewhere), or None when it does."""
        return self._away

    def _writable(self):
        if self._away:
            raise Refused(self._away)

    @contextlib.contextmanager
    def locked(self, timeout=2.0):
        """Holds the record's one lock (an exclusive flock on cache/record.lock) for a whole act; after the wait it raises Busy naming the holder."""
        if self._depth and self._owner == threading.get_ident():  # the holder's own nested call; another thread waits
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
            return
        os.makedirs(self._p("cache"), exist_ok=True)
        fd = os.open(self._p("cache", "record.lock"), os.O_RDWR | os.O_CREAT, 0o644)
        end = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= end:
                    held = os.pread(fd, 4096, 0).decode(errors="replace").strip() or "another process"
                    os.close(fd)
                    raise Busy(f"the record is held by {held}; I waited {timeout:g} s and wrote nothing") from None
                time.sleep(0.02)
        os.ftruncate(fd, 0)
        os.pwrite(fd, f"process {os.getpid()} ({' '.join(sys.argv)[:160]}), since {iso(self.clock())}".encode(), 0)
        self._depth, self._fresh, self._owner = 1, False, threading.get_ident()
        try:
            yield
        finally:
            self._depth, self._fresh, self._owner = 0, False, None
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def append(self, unit, kind, body, *, by, lang=None, valid_until=None, about=None):
        """Records one line in a unit's log and returns its id; the line is on disk before this returns. about names the object line it concerns."""
        return self._append(unit, kind, body, by=by, lang=lang, valid_until=valid_until, about=about)

    def _append(self, unit, kind, body, *, by, t=None, id=None, lang=None, valid_until=None, about=None):
        return self._append_many(unit, [dict(kind=kind, body=body, by=by, t=t, id=id, lang=lang, valid_until=valid_until, about=about)])[0]

    def session_append(self, unit, session_id, kind, body, *, by):
        """One line into the per-session file beside the log, chained within that file, taken without the lock."""
        return self._append_many(unit, [dict(kind=kind, body=body, by=by)], session=session_id)[0]

    def _append_many(self, unit, planned, *, session=None, dry=None):
        """The one door every line passes through: the kind, author, body, link, act and secret rules, then one write and one full flush per file.
        dry: a sitting's dry pass (move._dry), every rule judged against the lines and payloads planned before it in the same pass (its
        batch, pending and payloads) and nothing written (the review of batch E, finding 5)."""
        if not isinstance(unit, str) or not UNIT_RE.match(unit):
            raise Refused(f"a unit is named in lower-case letters, digits, dots, dashes and underscores, not {unit!r}")
        if session is not None and not SESSION_RE.match(str(session)):
            raise Refused(f"a session id is letters, digits, dots, dashes and underscores, not {session!r}")
        with contextlib.nullcontext() if session is not None else self.locked():
            self._writable()
            batch, checked = (dry["batch"], dry["pending"]) if dry is not None else ({}, [])
            n0, kept = len(checked), dry["payloads"] if dry is not None else ()
            look = lambda i: batch.get(i) or self.get(i)
            for p in planned:  # a carried line keeps the version its author carried (the review of batch E, finding 7)
                kind, by, body = p.get("kind"), check_by(p.get("by"), kept=bool(p.get("_carried"))), p.get("body")
                if kind not in KINDS:
                    raise Refused(f"{kind!r} is not a kind of line; the kinds are: {', '.join(KINDS)}")
                if kind in ("erase", "join") and not p.get("_internal"):
                    raise Refused(f"an {kind} line is written only by the store itself, never through append")
                check_body(body, erasing=kind == "erase")
                if kind != "erase" and self._blocked(body):
                    raise Refused("the words match a line that was erased; they are not written again, under any kind or unit")
                self._may(unit, kind, body, by, look, about=p.get("about"), valid_until=p.get("valid_until"), pending=checked,
                          carried=bool(p.get("_carried")))  # a line carried from another workshop's record (move.rekey); append never sets it
                missing = [r for r in payload_refs(body) if r not in kept and not self.payload_path(r)]
                if missing:
                    raise Refused(f"the body names a payload that is not kept beside the record ({missing[0][:12]}…); keep it with payload() first")
                if p.get("id") is not None and (not ID_RE.match(str(p["id"])) or (not p.get("_internal") and look(p["id"]))):
                    raise Refused(f"an id is 26 characters of base32 and new to this workshop; {p['id']!r} is not")
                if p.get("valid_until") is not None and not _real_day(p["valid_until"]):
                    raise Refused(f"valid_until is a real calendar day, YYYY-MM-DD; {str(p['valid_until'])[:40]!r} is not one, so nothing was written")
                if p.get("about") is not None and (isinstance(p["about"], str) and look(p["about"]) or {}).get("kind") != "object":
                    raise Refused(f"about names the thing a line concerns, which is an object line; {p['about']!r} is not")
                checked.append(dict(p, by=by))
                if p.get("id"):
                    batch[p["id"]] = {"id": p["id"], "kind": kind, "unit": unit, "by": by, "body": body, "t": p.get("t"), "mark": None}
            if dry is not None:
                for p in checked[n0:]:
                    self._row(unit, p, self._time(p), 1, "0" * 64)
                return [p.get("id") for p in checked[n0:]]
            seq, prev, prev_t, pre = self._head(unit, session)
            rows, ids = [], []
            for p in pre + checked:
                t = self._time(p)
                t = max(t, prev_t or t)
                seq = p.get("_seq") or seq + 1
                obj, row = self._row(unit, p, t, seq, prev)
                prev, prev_t = obj["hash"], t
                rows.append((self._log_path(unit, t, session), row))
                ids.append(obj["id"])
            for path in dict.fromkeys(q for q, _ in rows):
                if os.path.islink(path):  # the record writes only into its own files, never through a link to play/ or elsewhere
                    raise Refused(f"{os.path.relpath(path, self.root)} is a link, not a file of the record; nothing was written, "
                                  "and the link waits for the maker to remove it")
            for path in dict.fromkeys(q for q, _ in rows):
                _put(path, b"".join(r for q, r in rows if q == path), "ab")
                self._known[path] = _stat(path)
            self._fresh = False
            return ids[len(pre):]

    def _time(self, p):
        t = p.get("t") or self.clock()
        t = t if isinstance(t, str) else iso(t)
        if not T_RE.match(t):
            raise Refused(f"a time is YYYY-MM-DDTHH:MM:SS.mmmZ in UTC, not {t!r}")
        return t

    def _row(self, unit, p, t, seq, prev):
        """One line as the file keeps it, hashed and in canonical form; refused over 64 KiB."""
        obj = {"id": p.get("id") or mint_id(iso_ms(t)), "t": t, "kind": p["kind"], "by": p["by"], "unit": unit, "seq": seq, "prev": prev, "body": p["body"]}
        obj.update({k: p[k] for k in ("lang", "valid_until", "about") if p.get(k) is not None})
        obj["hash"] = line_hash(obj)
        row = (canonical(obj) + "\n").encode()
        if len(row) > LINE_MAX:
            raise Refused("a line over 64 KiB does not fit; keep it beside as a payload with payload()")
        return obj, row

    def _blocked(self, body):
        """Whether an erasure's block holds these words (a salted hash kept in a unit's record folder, never the words)."""
        w = words_of(body)
        for u in self.units():
            p = os.path.join(self.unit_dir(u), "blocked.jsonl")
            for b in (json.loads(x) for x in _rows(_read(p))) if os.path.exists(p) else ():
                if b.get("words_sha256") and hashlib.sha256((b["salt"] + w).encode()).hexdigest() == b["words_sha256"]:
                    return True
        return False

    def _head(self, unit, session=None):
        """The line to chain to, after setting aside a torn tail and joining the heads a merge left: (seq, hash, t, lines to write first)."""
        files = self._files(unit) if session is None else [f for f in [self._log_path(unit, "", session)] if os.path.exists(f)]
        last, pre = None, []
        for k, path in enumerate(reversed(files)):
            last, torn = _tail(path)
            if torn and k == 0 and session is None:
                pre.append(self._set_aside(unit, path, torn))
            if last:
                break
        if files and session is None and self._known.get(files[-1]) != _stat(files[-1]):
            heads = self._heads(unit)
            others = [h for h in heads if h["hash"] != (last or {}).get("hash")]
            if last and others:
                pre.append({"kind": "join", "by": check_by(TOOL), "_internal": True,
                            "_seq": max([h["seq"] for h in heads] + [last["seq"] + len(pre)]) + 1,
                            "body": {"heads": [{"id": h["id"], "hash": h["hash"]} for h in others],
                                     "text": f"{len(others) + 1} branches of this unit's record met in a merge; this line joins them"}})
        last = last or {}
        return last.get("seq", 0), last.get("hash"), last.get("t"), pre

    def _set_aside(self, unit, path, torn):
        name = f"torn/{os.path.basename(path)[:4]}.{iso(self.clock()).replace(':', '')}.bin"
        _put(os.path.join(self.unit_dir(unit), name), torn, "wb")
        os.truncate(path, os.path.getsize(path) - len(torn))
        return {"kind": "note", "by": check_by(TOOL), "body": {
            "event": "torn tail", "bytes": len(torn), "kept": name,
            "text": f"{len(torn)} bytes after the last whole line of {os.path.basename(path)} were set aside in {name}; "
                    "no line returned to a caller was touched"}}

    def _session_files(self, unit):
        """A unit's per-session files: regular files under record/sessions/ named <session>.jsonl, never through a link."""
        d = os.path.join(self.unit_dir(unit), "sessions")
        return [] if not os.path.isdir(d) or os.path.islink(d) else sorted(
            f for f in glob.glob(os.path.join(d, "*.jsonl")) if SESSION_RE.match(os.path.basename(f)[:-6]) and os.path.isfile(f) and not os.path.islink(f))

    def verify(self, unit=None, *, sessions=False):
        """Checks the files as they are, without the index: canonical form, the fields, every hash and prev, time and seq along the chain, ids, times and authors in the store's form, kinds, links, erasures and payloads; names each failure by file, row and id, and counts in elsewhere the lines about a thing no unit here holds. sessions: each per-session file holding a record line is checked the same way, along its own chain (Astra's challenge of batch E, finding 3)."""
        fails, parsed, every, heads, elsewhere, chains = [], {}, {}, {}, [0], {}  # walks record/ only, through _files and the payloads' glob; play/ is never read (R-STORE-PLAY-1)

        def fail(rel, row, i, what):
            fails.append({"file": rel, "row": row, "id": i, "what": what})

        def rows_of(path, mine):
            rel, data, out = os.path.relpath(path, self.root), _read(path), []
            if data and not data.endswith(b"\n") and mine:
                fail(rel, data.count(b"\n") + 1, None, f"torn tail: {len(data) - data.rfind(b'\n') - 1} bytes after the last whole line")
            for r, b in enumerate(_rows(data), 1):
                try:
                    obj = json.loads(b)
                except ValueError:
                    obj = None
                if not isinstance(obj, dict):
                    fail(rel, r, None, "not a JSON object") if mine else None
                    continue
                out.append((rel, r, b, obj))
                every.setdefault(obj.get("id"), obj)
            return out

        def chain(rows):
            seen, byhash, joined = set(), {}, set()
            for n, (rel, r, b, obj) in enumerate(rows):
                i, body = obj.get("id"), obj.get("body") if isinstance(obj.get("body"), dict) else {}
                f = lambda what: fail(rel, r, i, what)
                if b != canonical(obj).encode():
                    f("not in canonical form")
                for k in sorted(set(obj) - FIELDS - {"lang", "valid_until", "about"}):
                    f(f"a field outside the contract: {k}")
                for k in sorted(FIELDS - set(obj)):
                    f(f"a field missing: {k}")
                if obj.get("hash") != line_hash(obj):
                    f("content altered")
                if i in seen:
                    f("id repeated")
                if not (isinstance(i, str) and ID_RE.match(i)) or not (isinstance(obj.get("t"), str) and T_RE.match(obj["t"])):
                    f("an id or a time not in the store's form")
                try:
                    kept = check_by(obj.get("by"), kept=True) == obj.get("by")
                except Refused:
                    kept = False
                if not kept:
                    f("an author not in the store's form")
                if obj.get("kind") not in KINDS:
                    f(f"unknown kind: {obj.get('kind')}")
                if "about" in obj and isinstance(obj["about"], str) and ID_RE.match(obj["about"]) and obj["about"] not in every:
                    elsewhere[0] += 1  # about a thing in a unit this copy does not hold (design section 1 point 7): counted, not failed
                elif "about" in obj and (isinstance(obj["about"], str) and every.get(obj["about"]) or {}).get("kind") != "object":
                    f("about names no object line")
                parent = byhash.get(obj.get("prev"))
                if (obj.get("prev") is None) != (n == 0) or (obj.get("prev") is not None and parent is None):
                    f("chain broken")
                elif parent:
                    named = [byhash[h.get("hash")]["seq"] for h in body.get("heads", []) if h.get("hash") in byhash] if obj.get("kind") == "join" else []
                    if obj.get("t", "") < parent.get("t", ""):
                        f("time runs backwards")
                    if obj.get("seq") != max([parent.get("seq", 0)] + named) + 1:
                        f("seq out of step")
                seen.add(i)
                byhash[obj.get("hash")] = obj
                joined |= {h.get("hash") for h in body.get("heads", [])} if obj.get("kind") == "join" else set()
                for frm, rel_, to in links_of(obj):
                    if rel_ not in RELATIONS:
                        # between two things a relation is data (an object of type relation), which the index judges; here only its ends
                        if not ((every.get(frm) or {}).get("kind") == (every.get(to) or {}).get("kind") == "object"):
                            f(f"relation outside the list: {rel_}")
                    elif not ends_ok(rel_, (fl := every.get(frm) or {}).get("kind"), (tl := every.get(to) or {}).get("kind"),
                                     fl.get("unit") not in (None, tl.get("unit")) and tl.get("seq") == 1):
                        f(f"link ends outside the rules: {rel_}")
                if body.get("erased") is True:
                    e = every.get(body.get("by")) or {}
                    if e.get("kind") != "erase" or (e.get("body") or {}).get("erased") not in (i, True):
                        f("erased without its erase line")
            return joined
        for u in self.units():
            mine = unit in (None, u)
            for e in sorted(os.scandir(self.unit_dir(u)), key=lambda e: e.name) if mine else []:
                if e.is_symlink():
                    fail(os.path.relpath(e.path, self.root), None, None, "a link in the record folder, not read")
            parsed[u] = [x for path in self._files(u) for x in rows_of(path, mine)]
            chains[u] = [rows_of(p, True) for p in self._session_files(u) if _record_file(_read(p))] if sessions and mine else []
        for u in [unit] if unit else self.units():
            joined = chain(parsed.get(u, []))
            for rows in chains.get(u, []):
                chain(rows)
            gone = {o.get("prev") for _, _, _, o in parsed.get(u, [])} | joined  # made once: per line it made verify quadratic (R-READ-1)
            heads[u] = [o.get("id") for _, _, _, o in parsed.get(u, []) if o.get("hash") not in gone]
            for p in sorted(glob.glob(os.path.join(self.unit_dir(u), "payloads", "*"))):
                if hashlib.sha256(_read(p)).hexdigest() != os.path.basename(p):
                    fail(os.path.relpath(p, self.root), None, None, "payload changed")
        return {"ok": not fails, "failures": fails, "heads": heads, "lines": sum(len(v) for v in parsed.values()), "elsewhere": elsewhere[0]}
