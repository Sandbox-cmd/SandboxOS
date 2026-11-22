# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""sandbox move STREAM --export FOLDER --census FOLDER [--write] (cards 34 and 52 to 57): what one stream's move would bring in from the old
workshop's export (move.show, with his seed.json, streams.json and objects.json from the census folder), printed, kept as a plain file in
the workshop's move/ folder and asked once on a card on the maker's desk; nothing else is written. With --write, only his binding yes there
lets the same command write that stream's lines, once, with a note by the tool naming the card and the yes (takeback's door, shared)."""
import os

from sandbox_os.command import MAKER, cards, options, say
from sandbox_os.command.takeback import _on_his_yes
from sandbox_os.store import Refused, move, open as _open


def main(argv, *, workshop=None, out=print):
    opts, args = options(list(argv[1:]), dict.fromkeys(("--export", "--census")))
    name, write = [a for a in args if a != "--write"], "--write" in args
    if len(name) != 1 or None in opts.values() or name[0].startswith("-"):
        return out(say("cli.move.usage")) or 2
    s = workshop if hasattr(workshop, "lines") else _open(workshop) if workshop and os.path.isfile(os.path.join(workshop, "home.json")) else None
    if s is None:
        return out(say("cli.noworkshop")) or 1
    stream, export, again = name[0], os.path.abspath(opts["--export"]), f"{name[0]} --export {opts['--export']} --census {opts['--census']} --write"
    census = move.read_census(opts["--census"])
    rows, on = move.show(s, export, stream, census), cards._on(s, "workshop", "move:" + stream)
    text = "\n".join(say(k, **{n: say("count.line", v) if n == "n" else v for n, v in sl.items()}) for k, sl in rows)
    if rows[-1][0].startswith("move.refuse.") or write and not on:  # nothing kept, asked or written; --write acts only on a card raised before
        return out(text if rows[-1][0].startswith("move.refuse.") else say("cli.move.nocard", stream=stream)) or 1
    text += "\n" + say("cli.move.kept", path=move.keep(s, stream, text + "\n"))
    if on and not write:  # the card is on his desk already: the showing again, and how to write after his yes there, never the writing
        return out(text + "\n" + say("cli.move.asks", card=max(on), again=again)) or 0
    try:
        with s.locked():
            return _on_his_yes(s, out, "move", "workshop", stream, {"id": again, "stream": stream},
                               lambda why: move.write(s, export, stream, census, by=MAKER),
                               lambda yes, ids: say("cli.move.written", stream=stream, answer=yes, lines=", ".join(ids)), text)
    except Refused as e:  # the store's own words: a stopped sitting it will not put back, a stream already written
        return out(say("cli.take.refused", why=str(e))) or 1
