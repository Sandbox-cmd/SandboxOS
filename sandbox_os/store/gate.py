# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The replay gate: while the record is being read back (a rebuild of the index, a restore, a fork, the import
and the re-export), nothing that reaches outside this machine runs. A read path enters replaying(); a call that
would leave the machine wears outbound(name) and is refused, said plainly, while any replay is open on its thread.
Replays nest, so a restore that rebuilds its copy's index is one replay inside another."""
import contextlib
import functools
import threading

from sandbox_os.store import Refused

_depth = threading.local()  # how many replays are open on this thread; another thread's reading never shuts this one's gate


@contextlib.contextmanager
def replaying():
    """Holds the gate shut for as long as the block runs; re-entrant, counted per thread."""
    _depth.n = getattr(_depth, "n", 0) + 1
    try:
        yield
    finally:
        _depth.n -= 1


def is_replaying():
    """True while a replay is open on this thread."""
    return getattr(_depth, "n", 0) > 0


def outbound(name):
    """Marks a call that reaches outside the machine: it runs as written, except inside a replay, where it is refused."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if is_replaying():
                raise Refused(f"{name} would leave the machine while the record is being read; nothing left")
            return fn(*args, **kwargs)
        return wrapper
    return deco
