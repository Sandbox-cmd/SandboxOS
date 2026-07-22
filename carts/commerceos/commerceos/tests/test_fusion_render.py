"""CS0 step 1 — the fixture render, pinned by packs/CS0/context.md "the test
plan". renders by calling fusion.page/ticket/group_label/aged directly — no
app, no TestClient, no db (context.md "prior art to copy": copy
test_seo_feature_web.py's grep-the-rendered-HTML assertion STYLE, not its
FastAPI rig). fixtures mirror spec/parts/collab-surface.md's stress test
(the calm tuesday, the heavy monday) and PACK.md's triage sentence law.

gap named honestly (see the builder's report): PACK.md's step plan says the
test "composes page(group_label + tickets, since_line)" — but page()'s own
signature (PACK.md "the ruled contracts") takes only (inner_html,
since_line), with no sentence parameter, while the same paragraph also
requires "the sentence in the HTML equals triage(...).sentence". The only
reading that satisfies both is that the sentence text is part of the
inner_html the test composes (alongside group_label + tickets) before
calling page() — so these fixtures prepend the sentence to inner_html
themselves. Flagged as an inference, not a pinned literal.
"""

from html import escape as html_escape

import pytest

from commerceos.web import fusion
from commerceos.web.triage import triage


def _row(id_, action_type):
    return {"id": id_, "action_type": action_type}


def test_calm_day_fixture():
    # both rows share a group (all-one-group law) so the sentence stays
    # flat, no eyes/routine breakdown — the mixed-group case is pinned
    # separately by tests/test_triage.py::test_two_things_one_group and
    # ::test_singular_eyes_agrees/::test_singular_routine_drops_together.
    waits = [_row("w1", "reversible"), _row("w2", "reversible")]
    t = triage(waits)
    assert t.sentence == "Two things need you."

    tickets_html = "".join([
        fusion.ticket(
            title="20 collections, ready to go live",
            meta="reversible · from the category plan you approved",
            edge="waiting",
            action_label="Approve",
            action_href="/gate/w1/approve",
        ),
        fusion.ticket(
            title="One menu change",
            meta="replaces the whole menu at once — your yes per item",
            edge="waiting",
            action_label="Review",
            action_href="/gate/w2/review",
        ),
    ])
    since_line = fusion.aged("78.5", "last night")
    assert since_line == "78.5 as of last night"

    doors_html = (
        "<p class='doors'>"
        "<a href='/demostore'>demostore</a>"
        "<a href='/scaffold'>scaffold</a>"
        "<a href='/record'>the record</a>"
        "</p>"
    )
    inner = f"<h2>{html_escape(t.sentence)}</h2>" + fusion.group_label("waiting on you") + tickets_html + doors_html
    html = fusion.page(inner, since_line=since_line)

    assert html.count(t.sentence) == 1
    assert "20 collections, ready to go live" in html
    assert "reversible · from the category plan you approved" in html
    assert "One menu change" in html
    assert "replaces the whole menu at once — your yes per item" in html
    assert html.count('class="ticket waiting"') == 2
    assert "78.5 as of last night" in html
    assert "demostore" in html
    assert "scaffold" in html
    assert "the record" in html


def test_heavy_day_fixture():
    eyes = [
        _row("c1", "consequential"),
        _row("c2", "consequential"),
        _row("c3", "consequential"),
    ]
    routine = [_row(f"r{i}", "reversible") for i in range(1, 9)]
    stopped_row = {"id": "s1", "action_type": "reversible"}
    t = triage(eyes + routine, stopped=[stopped_row])
    assert t.sentence == (
        "Eleven things need you. Three deserve your eyes. "
        "Eight are routine and can go together. One job stopped."
    )

    eyes_tickets = "".join([
        fusion.ticket(title="Refund over threshold — AED 1,840",
                      meta="money moves only on your yes · order and history attached",
                      edge="waiting", action_label="Review", action_href="/gate/c1/review"),
        fusion.ticket(title="One menu change",
                      meta="replaces the whole menu at once",
                      edge="waiting", action_label="Review", action_href="/gate/c2/review"),
        fusion.ticket(title="Price drop on 12 slow movers",
                      meta="reversible, but it touches money — so it waits for you",
                      edge="waiting", action_label="Review", action_href="/gate/c3/review"),
    ])
    routine_group_label = "routine — all reversible, verified before they count"
    batch_ticket = fusion.ticket(
        title="8 routine batches",
        meta="listing text ×5 · barcodes ×2 · categories ×1 — open any one, or take them together",
        edge="waiting", action_label="Approve all 8", action_href="/gate/batch/approve",
    )
    stopped_ticket = fusion.ticket(
        title="Feed sync stopped at product 122",
        meta="three failed calls in a row — I stopped, kept the receipts, touched nothing else",
        edge="stopped", action_label="See why", action_href="/gate/s1/receipt",
    )

    inner = (
        f"<h2>{html_escape(t.sentence)}</h2>"
        + fusion.group_label("your eyes first")
        + eyes_tickets
        + fusion.group_label(routine_group_label)
        + batch_ticket
        + fusion.group_label("stopped, honestly")
        + stopped_ticket
    )
    since_line = fusion.aged("76.1", "last night")
    html = fusion.page(inner, since_line=since_line)

    assert html.count(t.sentence) == 1
    assert html.count(routine_group_label) == 1
    assert "8 routine batches" in html
    assert html.count('class="ticket stopped"') == 1
    assert "Feed sync stopped at product 122" in html


def test_escape_proven():
    ticket_html = fusion.ticket(
        title="<b>sneaky</b>",
        meta="a fixture meta line",
        edge="waiting",
    )
    assert "<b>sneaky</b>" not in ticket_html
    assert html_escape("<b>sneaky</b>") in ticket_html


def test_edge_enum_loud():
    with pytest.raises(ValueError):
        fusion.ticket(title="x", meta="y", edge="sparkly")
