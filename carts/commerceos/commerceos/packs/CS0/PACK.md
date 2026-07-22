git diff --quiet 888de9c..HEAD -- commerceos/gate/ledger.py commerceos/gate/policy.py commerceos/web/app.py tests/test_voice_register.py || echo "STALE — re-true before build (see RUNBOOK)"

# CS0 — the fusion register's foundation

## mission

the collaboration surface (spec/parts/collab-surface.md, RULED 2026-07-22)
needs three foundations before its screens exist: the register (a light,
sentence-first stylesheet with the ticket as its unit), the triage brain
(the sentence that names the size of the owner's day, computed from real
gate waits, grouped by reversibility), and the three lints from the SF1
voice pass armed as tests. CS0 ships all three as NEW FILES ONLY — it
never touches web/app.py, so it collides with nothing. CS1 (the wall) and
CS2 (the board) compose these pieces into routed pages.

as-of: commit 888de9c · suite 508 green (zero skips)

## the backlog check (verbatim, backlog.md CS0 row)

lints green in the suite; a rendered fixture page shows the sentence
matching the true wait count and every audit number wearing "as of";
plain-language guard walks it

(the "rendered fixture page" is test-rendered — render helpers composed
with fixture waits, asserted by string; NO route is added in CS0. the
guard "walks it" via the lint suite walking every fusion string set —
route-walking arrives with CS1/CS2's real pages.)

## model

sonnet — new pure modules with contracts ruled below; no surgery on
existing files; the test rigs to copy are named with line numbers.

## boundaries

- **files you may create**: commerceos/web/fusion.py ·
  commerceos/web/triage.py · commerceos/web/static/fusion.css ·
  tests/test_sf1_lints.py · tests/test_triage.py ·
  tests/test_fusion_render.py. NOTHING ELSE — no edit to any existing
  file. if you believe an existing file must change, STOP (escalation).
- **stores/dbs**: triage is a pure function over row dicts — tests feed
  literal dicts; no database is opened, no store client exists here.
  data/<store>.db may hold a real catalog — never opened, never written.
- **no commits, no record commands** — the orchestrator owns both.
  stage nothing; report honestly.

## the ruled contracts (so no builder guesses)

**triage.py** — pure, no imports beyond stdlib + typing:

    Triage = dataclass: sentence: str · eyes_first: list[dict] ·
             routine: list[dict] · stopped: list[dict]
    def triage(waits: list[dict], stopped: list[dict] = ()) -> Triage

- input rows are gate ledger pending rows (shape: gate/ledger.py:410-414
  `_record`; class field is `action_type`, values per gate/policy.py:35-38:
  reversible · consequential · fit_critical).
- grouping law (spec/parts/collab-surface.md "under load"): routine =
  action_type == "reversible"; eyes_first = everything else, ORDER
  preserved within groups, eyes_first before routine.
- the sentence, exact strings (spelled numbers One..Twelve capitalized,
  digits from 13; the count word starts the sentence):
  - 0 waits, 0 stopped → `Nothing needs you.`
  - 1 wait → `One thing needs you.`
  - N waits, all one group → `Two things need you.` (etc.)
  - N waits, both groups → `Eleven things need you. Three deserve your
    eyes. Eight are routine and can go together.`
  - any stopped, appended as its own sentence → ` One job stopped.` /
    `Two jobs stopped.` — AMENDED 2026-07-22 during CS1's producer
    round two: the original "stopped overnight" was minted true at the
    comp's fixture hour and rendered false at 3pm (the exact
    minted-true-once class the producer hunts); the bare form is
    always true.
- no other words. the sentence never names stores, methods, or money —
  tickets carry detail; the sentence carries triage only.

**fusion.py** — render helpers returning HTML strings, escaping every
interpolated value with html.escape (the record's law: record-born
strings escape before markup — copy the convention at web/app.py:13,856):

    def ticket(title, meta, edge, action_label=None, action_href=None,
               body=None) -> str
    def group_label(text) -> str
    def page(inner_html, since_line=None) -> str   # wraps in the fusion
        # shell: <link> to /static/fusion.css is CS1's business — page()
        # here inlines nothing and references the stylesheet by path only
    def aged(value: str, asof: str) -> str  # "78.5" + "last night" ->
        # "78.5 as of last night" — THE ONLY formatter for audit-derived
        # numbers on this surface (the mirror-as-of lint depends on it)

- edge ∈ {"waiting","running","stopped","done"} — anything else raises
  ValueError loudly. these are the four meanings; a fifth color is a
  design change, not a parameter.
- module-level string sets follow the house convention so the lint
  roster guard sees them: any dict of surface strings is named
  FUSION_*_PLAIN (test_voice_register.py:61-68 shows the convention
  guard pattern to copy).

**fusion.css** — the fusion register, self-contained, no imports, no
external requests: light ground (#FAFAF7 on the comp), system font
stack, the sentence scale (~2rem/600), ticket component (white card,
1px border #E7E4D9, 3px left edge: waiting #E0A63C · running #5B8DEF ·
stopped #C4442A · done #5FA168), group labels (small caps letterspaced),
doors row, receipt-in-place block. reports/collab-surface/fusion.html is
the ruled comp — transcribe its values; do not redesign.

**test_sf1_lints.py** — three deterministic lints + one roster guard:

1. land-guard: over every FUSION_*_PLAIN set in fusion.py AND every
   sentence triage can emit (call triage with representative fixtures),
   any match of r"\bland(s|ed|ing)?\b" must sit in a phrase starting
   with "you " (the owner as subject). machine acts say made/updated/
   done. the allowlist is phrase-level, in the test, and every entry
   must itself start with "you".
2. fiction-collision: the fusion register carries no fiction —
   FICTION_WORDS = {"cassette","cartridge","teletext","tuned",
   "on air","serial","broadcast"} never appear in any FUSION_*_PLAIN
   value or triage sentence. (the page's internal name "the wall" is
   spec vocabulary and NEVER a rendered string — CS1's masthead says
   "commerceos"; assert fusion.py contains no rendered "the wall"
   string.)
3. mirror-as-of: any FUSION_*_PLAIN value matching r"health \d|\d+(\.\d+)?%"
   must contain "as of" in the same string; and aged() is the only
   place fusion.py concatenates "as of" (one formatter, one law).
4. roster guard: any module-level dict in fusion.py named FUSION_*_PLAIN
   is on the lint's roster (copy test_voice_register.py:61-68).

## step plan (M-size: 3 checkpoints)

**step 1 — failing tests first.** write test_triage.py (pins named in
context.md), test_sf1_lints.py, test_fusion_render.py against the
contracts above. run them; watch them fail on the missing modules.
**CHECKPOINT 1**: show the test list + the failure output.

**step 2 — triage.py + the lints green.** implement triage exactly to
contract; implement fusion.py string sets enough for the lints.
**CHECKPOINT 2**: uv run pytest tests/test_triage.py tests/test_sf1_lints.py -q
— all green, output shown.

**step 3 — fusion.py render + fusion.css + the fixture render.** the
fixture test composes page(group_label + tickets, since_line) with the
calm-day fixture (2 waits) and the heavy-day fixture (11 waits + 1
stopped) and asserts: the sentence in the HTML equals triage(...)
.sentence · every ticket title/meta present · edge classes correct ·
"as of last night" present via aged() · html.escape proven (a fixture
title carrying `<b>` renders escaped). **CHECKPOINT 3**: full suite —
uv run pytest -q — 508 + your new tests, zero failures, zero skips;
paste the tail.

## escalation triggers (stop and report, don't improvise)

the runbook's six, plus:
- any contract above under-determines a behavior you must pick — name
  the gap instead of inferring silently (inferences are wanted data).
- you find yourself wanting to edit web/app.py or any existing file.
- the ruled comp (fusion.html) and this pack disagree on a value.
- a lint as specified would fail on a string you believe is correct —
  report the string, do not weaken the lint.

## done contract

all three checkpoints shown with real output · every file inside the
boundary list · inferences and residuals named honestly · NOTHING
committed, NOTHING staged to the record — the orchestrator closes out.

## risks (inline)

- the sentence's number-words: One..Twelve then digits is RULED here to
  kill bikeshedding; if a fixture makes "13 things need you." read
  wrong, report it as a residual, don't change the rule.
- triage takes stopped rows as a separate argument because stopped work
  lives in workflow-run rows, not the gate ledger — CS1 wires the real
  source (its `_stopped_runs`); CS0's tests feed literal dicts. do not
  go looking for a stopped-jobs query; it is out of scope here.
- fusion.css transcribes the comp; contrast on #E0A63C text does not
  matter because the edge is a border, never text ink. body text stays
  #1A1A17 / #7A766A on #FAFAF7 (both clear 4.5:1).
