"""CS0 step 1 — the triage brain's own tests, pinned by packs/CS0/context.md
"the test plan". triage() is pure (gate/policy.py:35-39 REVERSIBLE ·
CONSEQUENTIAL · FIT_CRITICAL string-compared, no import of policy — CS0's
PACK.md "the ruled contracts"): feed literal dicts shaped like
gate/ledger.py:410-414 _record rows (the only field triage reads is
action_type), assert the sentence and the grouping.

the sentence law (PACK.md, verbatim strings):
  0 waits, 0 stopped -> "Nothing needs you."
  1 wait             -> "One thing needs you."
  N waits, one group -> "Two things need you." (etc, plural "things"/"need")
  N waits, two groups -> "Eleven things need you. Three deserve your eyes.
                          Eight are routine and can go together."
  any stopped, appended -> " One job stopped." / " Two jobs stopped."
  (orchestrator amendment, producer round 2 M-A: "overnight" dropped — it
   rendered false at 3pm; the stop is real regardless of hour)
  number words One..Twelve capitalized, digits from 13 — the count word
  starts the sentence.
"""

from commerceos.web.triage import Triage, triage


def _row(id_, action_type):
    return {"id": id_, "action_type": action_type}


def test_nothing_needs_you():
    t = triage([])
    assert isinstance(t, Triage)
    assert t.sentence == "Nothing needs you."
    assert t.eyes_first == []
    assert t.routine == []
    assert t.stopped == []


def test_one_thing():
    row = _row("r1", "reversible")
    t = triage([row])
    assert t.sentence == "One thing needs you."
    assert t.routine == [row]
    assert t.eyes_first == []


def test_two_things_one_group():
    rows = [_row("c1", "consequential"), _row("c2", "consequential")]
    t = triage(rows)
    assert t.sentence == "Two things need you."
    assert t.eyes_first == rows
    assert t.routine == []


def test_heavy_day_triage():
    eyes = [_row("c1", "consequential"), _row("c2", "consequential"), _row("c3", "consequential")]
    routine = [_row(f"r{i}", "reversible") for i in range(1, 9)]
    t = triage(eyes + routine)
    assert t.sentence == (
        "Eleven things need you. Three deserve your eyes. "
        "Eight are routine and can go together."
    )
    assert t.eyes_first == eyes
    assert t.routine == routine
    assert t.stopped == []


def test_stopped_appends():
    routine = [_row("r1", "reversible"), _row("r2", "reversible")]
    stopped_row = {"id": "s1", "action_type": "reversible", "outcome": {"status": "stopped"}}
    t = triage(routine, stopped=[stopped_row])
    assert t.sentence == "Two things need you. One job stopped."
    assert t.stopped == [stopped_row]
    assert t.routine == routine


def test_thirteen_uses_digits():
    eyes = [_row(f"c{i}", "consequential") for i in range(1, 6)]
    routine = [_row(f"r{i}", "reversible") for i in range(1, 9)]
    t = triage(eyes + routine)
    assert t.sentence.startswith("13 things need you.")
    assert len(t.eyes_first) == 5
    assert len(t.routine) == 8


def test_singular_eyes_agrees():
    """checkpoint-2 ruling: eyes_first == 1 takes the singular verb."""
    eyes = [_row("c1", "consequential")]
    routine = [_row(f"r{i}", "reversible") for i in range(1, 6)]
    t = triage(eyes + routine)
    assert t.sentence == (
        "Six things need you. One deserves your eyes. "
        "Five are routine and can go together."
    )
    assert t.eyes_first == eyes
    assert t.routine == routine


def test_singular_routine_drops_together():
    """checkpoint-2 ruling: routine == 1 drops "and can go together" (one
    item has no together) and takes the singular verb "is"."""
    eyes = [_row(f"c{i}", "consequential") for i in range(1, 4)]
    routine = [_row("r1", "reversible")]
    t = triage(eyes + routine)
    assert t.sentence == "Four things need you. Three deserve your eyes. One is routine."
    assert t.eyes_first == eyes
    assert t.routine == routine


def test_order_preserved():
    rows = [
        _row("c1", "consequential"),
        _row("r1", "reversible"),
        _row("c2", "consequential"),
        _row("r2", "reversible"),
    ]
    t = triage(rows)
    assert t.eyes_first == [rows[0], rows[2]]
    assert t.routine == [rows[1], rows[3]]


def test_unknown_action_type_is_eyes_first():
    row = _row("m1", "mystery_type")
    t = triage([row])
    assert row in t.eyes_first
    assert row not in t.routine
