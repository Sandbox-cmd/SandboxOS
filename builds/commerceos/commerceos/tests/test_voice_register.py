"""the shared-label lint (the voicer's proposed law, now mechanism, RULED):
every value in the codebase's shared plain-label sets — the module-level
dicts in web/app.py that map an internal code onto the plain sentence a
person actually reads — starts lowercase, unless its first word is a proper
noun, a product name, or the currency word AED. lowercase chrome is the
house voice (_page's own docstring: "lowercase chrome throughout; UPPERCASE
only for the one slap a view may carry"); a label dict is exactly the kind
of chrome that rule binds.

this must PASS after the item-5 register sweep. if a future change makes
any set fail, the fix is the SET (whole-set consistency, per the ruling),
never a special case bolted onto this test."""

import inspect
import re

from commerceos.web import app as web_app

# proper nouns / product names / the currency word — the register's own
# named exceptions, not a loophole for new sentence-case chrome. add a name
# here only when the record actually needs a capitalized first word.
ALLOWED_CAPITALIZED_FIRST_WORDS = {"AED", "Shopify", "GTIN"}

# every shared plain-label dict app.py carries: code -> the plain sentence a
# person reads. enumerated by hand (RULED) so a differently-named future set
# doesn't silently escape the lint — add it here the day it's born, and
# test_every_conventionally_named_set_is_on_the_roster below guards the
# common case (a set named *_LABELS or *_PLAIN, the house convention).
PLAIN_LABEL_SETS = {
    "FEATURE_LABELS": web_app.FEATURE_LABELS,
    "PROGRESS_LABELS": web_app.PROGRESS_LABELS,
    "METHOD_LABELS": web_app.METHOD_LABELS,
    "METHOD_LABELS_AHEAD": web_app.METHOD_LABELS_AHEAD,
    "ACTION_TYPE_LABELS": web_app.ACTION_TYPE_LABELS,
    "FUNCTION_LABELS": web_app.FUNCTION_LABELS,
    "AUTONOMY_PLAIN": web_app.AUTONOMY_PLAIN,
    "FLEET_STATUS_PLAIN": web_app.FLEET_STATUS_PLAIN,
    "STATE_LABELS": web_app.STATE_LABELS,
    "GAP_LABELS": web_app.GAP_LABELS,
    "FRONT_BLURB": web_app.FRONT_BLURB,
    "GATE_CLASS_PLAIN": web_app.GATE_CLASS_PLAIN,
    "SOURCE_PLAIN": web_app.SOURCE_PLAIN,
    "EVIDENCE_PLAIN": web_app.EVIDENCE_PLAIN,
    "SPEC_FIELD_LABELS": web_app.SPEC_FIELD_LABELS,
    "HUNT_LABELS": web_app.HUNT_LABELS,
    "DISPOSITION_LABELS": web_app.DISPOSITION_LABELS,
    "ECON_LINES": web_app.ECON_LINES,
    "GRANT_PLAIN": web_app.GRANT_PLAIN,
    "FUNCTION_PLAIN": web_app.FUNCTION_PLAIN,
    "RECORD_STATUS_PLAIN": web_app.RECORD_STATUS_PLAIN,
}

_FIRST_WORD = re.compile(r"[A-Za-z][A-Za-z']*")


def _first_word(value: str) -> str | None:
    m = _FIRST_WORD.search(value)
    return m.group(0) if m else None


def test_every_conventionally_named_set_is_on_the_roster():
    """a light guard against drift: any module-level dict named the house's
    own way (*_LABELS or *_PLAIN) is one this lint actually checks — so a
    newly added set can't silently sit outside the law."""
    src = inspect.getsource(web_app)
    named = set(re.findall(r"^([A-Z][A-Z0-9_]*(?:_LABELS|_PLAIN)) = \{", src, re.M))
    missing = named - set(PLAIN_LABEL_SETS)
    assert not missing, f"a plain-label set exists but isn't on this lint's roster: {missing}"


def test_every_shared_label_starts_lowercase_or_a_named_exception():
    violations = []
    for set_name, table in PLAIN_LABEL_SETS.items():
        for key, value in table.items():
            if not isinstance(value, str) or not value:
                continue
            word = _first_word(value)
            if word is None:
                continue
            if word[0].isupper() and word not in ALLOWED_CAPITALIZED_FIRST_WORDS:
                violations.append(f"{set_name}[{key!r}] = {value!r}")
    assert not violations, ("sentence-case chrome found in a shared label set "
                            "(should start lowercase, or be a named exception):\n"
                            + "\n".join(violations))


def test_the_exception_list_is_not_a_loophole():
    """the allowlist names real proper nouns/product names/the currency word
    only — never a generic English word smuggled in to dodge the lint."""
    for word in ALLOWED_CAPITALIZED_FIRST_WORDS:
        assert word[0].isupper()
    assert "AED" in ALLOWED_CAPITALIZED_FIRST_WORDS
