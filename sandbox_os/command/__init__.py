# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The command: the calls the maker's verbs, the brief and the night run on (contract section 8's command calls), each recording
through the store as the partner, as the tool, or as the maker only where the maker's own words are established."""
MAKER = {"kind": "maker", "name": "maker", "model": None, "host": None}
TOOL = {"kind": "tool", "name": "sandbox-os", "model": None, "host": None}
DOWN = ("struck", "deleted", "erased", "superseded")
_words = {}


def words(lang="en"):
    """The table of words in a language, read once for every sentence this part says in it: English, or a card's (card 38)."""
    if lang not in _words:
        from sandbox_os.pages.words import Words
        _words[lang] = Words(lang)
    return _words[lang]


def say(key, n=None, /, lang="en", **slots):
    return words(lang).plain(key, n, **slots)


def counted(n, noun):
    """A count with its noun, plural unless it is one."""
    return f"{n} {noun}" + ("" if n == 1 else "s")


def options(rest, opts):
    """A command's words read once: each option in opts takes the word after it, every other word is an argument, in order."""
    args = []
    while rest:
        a = rest.pop(0)
        if a in opts and rest:
            opts[a] = rest.pop(0)
        else:
            args.append(a)
    return opts, args
