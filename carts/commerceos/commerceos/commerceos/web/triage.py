"""triage.py — the sentence that names the size of the owner's day.

part: the collaboration surface (spec/parts/collab-surface.md "the sentence
is the triage"). pure: stdlib + typing only, no db, no fastapi, no import of
gate/policy.py — triage string-compares a row's action_type against
gate/policy.py:35-38's REVERSIBLE value directly, so this module drags
nothing in and CS0 collides with nothing (PACK.md "the ruled contracts").

input rows are gate ledger pending-queue-shaped dicts (gate/ledger.py:342-347
pending_queue, :410-414 _record) — only the "action_type" field is read.
grouping law (spec/parts/collab-surface.md "under load"): routine = rows
whose action_type == "reversible"; eyes_first = everything else (including
any action_type this module doesn't recognize — fail safe, the same
instinct as gate/policy.py's unknown-method fail-high), order preserved
within each group, eyes_first before routine.
"""

from __future__ import annotations

from dataclasses import dataclass

REVERSIBLE = "reversible"

# spelled numbers One..Twelve capitalized; digits from 13 (PACK.md, ruled to
# kill bikeshedding).
_NUMBER_WORDS = {
    1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six",
    7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve",
}


def _count_word(n: int) -> str:
    return _NUMBER_WORDS.get(n, str(n))


@dataclass
class Triage:
    sentence: str
    eyes_first: list[dict]
    routine: list[dict]
    stopped: list[dict]


def _stopped_clause(stopped: list[dict]) -> str:
    n = len(stopped)
    if n == 0:
        return ""
    word = "job" if n == 1 else "jobs"
    # ruled string (orchestrator amendment, producer round 2 M-A): "overnight"
    # was minted true at the comp's fixture but renders false at 3pm — the
    # stop is real regardless of hour, so the clause names only the fact.
    return f" {_count_word(n)} {word} stopped."


def triage(waits: list[dict], stopped: list[dict] = ()) -> Triage:
    stopped = list(stopped)
    eyes_first: list[dict] = []
    routine: list[dict] = []
    for row in waits:
        if row.get("action_type") == REVERSIBLE:
            routine.append(row)
        else:
            eyes_first.append(row)

    total = len(eyes_first) + len(routine)
    stopped_clause = _stopped_clause(stopped)

    if total == 0:
        base = "Nothing needs you."
    elif total == 1:
        base = "One thing needs you."
    elif eyes_first and routine:
        eyes_n = len(eyes_first)
        routine_n = len(routine)
        # singular agreement (owner ruling, checkpoint 2 review): "One
        # deserves your eyes." not "One deserve"; "One is routine." not
        # "One are routine and can go together" — the "and can go
        # together" clause names a batch, and one item has no together.
        eyes_clause = (
            f"{_count_word(eyes_n)} deserves your eyes."
            if eyes_n == 1
            else f"{_count_word(eyes_n)} deserve your eyes."
        )
        routine_clause = (
            f"{_count_word(routine_n)} is routine."
            if routine_n == 1
            else f"{_count_word(routine_n)} are routine and can go together."
        )
        base = f"{_count_word(total)} things need you. {eyes_clause} {routine_clause}"
    else:
        base = f"{_count_word(total)} things need you."

    return Triage(
        sentence=base + stopped_clause,
        eyes_first=eyes_first,
        routine=routine,
        stopped=stopped,
    )
