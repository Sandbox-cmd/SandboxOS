# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The store: opens a workshop's record and answers every call the other parts may make of it."""

FORMAT = 2  # how the record is stored; it moves only by adding what the previous version ignores, with a migration line named (row 96); 2 adds the field about and five kinds, 2026-11-07


class Refused(ValueError):
    """A write or a call the store would not do, said plainly: what was refused and why, never a secret's value."""


class Busy(Refused):
    """The record's one lock is held by another writer past the wait."""


from sandbox_os.store.log import Log  # noqa: E402  (the exceptions above come first; the parts import them)
from sandbox_os.store.acts import Acts  # noqa: E402
from sandbox_os.store.index import Index  # noqa: E402


class Store(Log, Acts, Index):
    """A workshop's record: the files under projects/<unit>/record/, the lock, and the index in cache/."""

    def __init__(self, root, *, read_only=False, clock=None, machine=None):
        self._setup(root, read_only, clock, machine)

    def close(self):
        """Lets go of the index's connection; the next read opens it again."""
        self._conn = self._conn.close() if self._conn else None

    def seed(self, *, by):
        """Records the seed's types and relations once, as objects of the workshop unit; returns how many of each it recorded now (seed.seed)."""
        from sandbox_os.store import seed
        return seed.seed(self, by=by)

    def types(self):
        """The standing types of the maker's world, each an object line of type 'type', in time order."""
        from sandbox_os.store import seed
        return seed.standing(self, "type")

    def relations(self):
        """The standing relations between things, each an object line of type 'relation', in time order."""
        from sandbox_os.store import seed
        return seed.standing(self, "relation")

    def verbs(self):
        """The standing verbs, each a view read from its present facets (verbs.view), struck and superseded ones left out, by name."""
        from sandbox_os.store import verbs
        return verbs.standing(self)

    def verb(self, id):
        """One verb's view by its object's id, whatever its mark, or None when the id names no object of type verb."""
        from sandbox_os.store import verbs
        o = self.get(id) if isinstance(id, str) else None
        return verbs.view(self, o) if o and o["kind"] == "object" and (o["body"] or {}).get("type") == "verb" else None

    def verb_for(self, argvs):
        """The first act in these simple commands (a list of word lists): the declared, standing verb with the longest shape the first
        command a verb names is of, as its view plus "shape" and "argv", or None; every act in order is verbs.acts_in."""
        from sandbox_os.store import verbs
        got = verbs.acts_in(self, argvs)
        return got[0] if got else None

    def proposal_for(self, verb_id, unit, act_sha256=None):
        """The oldest proposal of a verb in a unit with an act not yet spent: answered yes on a card, or under a standing grant; given the
        act's words hash (verbs.act_sha256), a pending retry only for the same command (verbs.proposal_for)."""
        from sandbox_os.store import verbs
        return verbs.proposal_for(self, verb_id, unit, act_sha256=act_sha256)

    def door(self, verb_id, unit):
        """Which of the three doors a verb takes in a unit, {door, grant}: asks, inside, grant (with its id) or asks once (verbs.door)."""
        from sandbox_os.store import verbs
        return verbs.door(self, verb_id, unit)

    def play(self, unit):
        """The play folder's top-level entries, projects/<unit>/play/, by name, size in bytes and modification time; nothing inside them is read (R-STORE-PLAY-1)."""
        import datetime as _dt, os
        from sandbox_os.store.line import iso, UNIT_RE
        if not isinstance(unit, str) or not UNIT_RE.match(unit):
            raise Refused(f"a unit is named in lower-case letters, digits, dots, dashes and underscores, not {unit!r}")
        d = self._p("projects", unit, "play")
        if not os.path.isdir(d):
            return []
        with os.scandir(d) as it:
            ents = sorted(it, key=lambda e: e.name)
        return [{"name": e.name, "bytes": e.stat(follow_symlinks=False).st_size,
                 "modified": iso(_dt.datetime.fromtimestamp(e.stat(follow_symlinks=False).st_mtime, _dt.timezone.utc))} for e in ents]

    def play_lesson(self, unit, text, *, by):
        """A card in the unit asking whether a lesson from play is kept, with the lesson's words as what it decides; returns the card's id (R-STORE-PLAY-2)."""
        return self.append(unit, "card", {
            "decides": text, "stand": "Keep it: the lesson becomes a line of this project's record.",
            "other": "Leave it in play, where nothing is graded.", "wrong": "a lesson kept that was only a try",
            "saw": f"a lesson from projects/{unit}/play/, the folder the store lists by name and never reads",
            "answers": ["yes", "no", "later"], "version": 1, "about_play": True}, by=by)

    def push(self, remote, *, by):
        """The second copy: the record's folders to a remote as heads and snapshot (copy.push)."""
        from sandbox_os.store import copy
        return copy.push(self, remote, by=by)

    @staticmethod
    def restore(remote, into, *, unit=None):
        """A copy from a remote into a new folder, checked against the remote's heads (copy.restore)."""
        from sandbox_os.store import copy
        return copy.restore(remote, into, unit=unit)

    def fork(self, unit, into, *, by):
        """One unit's record into a new workshop, without the lines about the maker or his grants (copy.fork)."""
        from sandbox_os.store import copy
        return copy.fork(self, unit, into, by=by)

    def import_export(self, path, *, by, report_dir=None, **kw):
        """The import of the ninth's export (move.import_export), with its keywords: one stream's units, the ledgers before, things, carries."""
        from sandbox_os.store import move
        return move.import_export(self, path, by=by, report_dir=report_dir, **kw)

    def reexport(self, dest, *, ledger):
        """The ninth's journal rebuilt from this record (move.reexport)."""
        from sandbox_os.store import move
        return move.reexport(self, dest, ledger=ledger)


def open(root, *, read_only=False, clock=None, machine=None):
    """Opens the record at root; the first writable open makes projects/, cache/, home.json and .gitattributes."""
    return Store(root, read_only=read_only, clock=clock, machine=machine)
