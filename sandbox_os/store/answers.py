# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""His words on the week's card, read by one strict reader that the store's door and the command's card share, so the store never reads
as a strike what the card reads as nothing (Astra's challenge of batch D, finding 2)."""
import re

from sandbox_os.store.line import strip_arabic_marks

STRIKE_WORDS = ("strike", "اشطب")  # the strings table's growth.strike row, English and Arabic; tests/store/test_review_d.py holds them equal
ANSWER_WORDS = {"yes": "yes", "y": "yes", "no": "no", "n": "no", "later": "later", "l": "later", "غ": "yes", "ى": "no", "ل": "later",
                "نعم": "yes", "لا": "no", "لاحقا": "later"}  # cards.answer_words(), its keys and the table's labels; tests/store/test_astra_d.py holds them equal
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")  # Arabic-Indic and Persian digits, read as Western


def plain(w):
    """A word as an answer is compared: trimmed, lower case, a closing stop or comma dropped, Arabic without its short vowels."""
    return strip_arabic_marks(str(w).strip().lower().rstrip(".!,،"))


def read_choice(words, n):
    """His words on the week's card, item by item: groups of an answer word (cards.answer_words()'s, or strike or its Arabic) each followed by
    one or more numbers from 1 to n, in Western or Arabic-Indic digits, separated by spaces or commas; as {number: yes, no, later or
    strike}. Anything else, a number out of range or one number given two answers included, is None."""
    if not isinstance(words, str) or not words.strip():
        return None
    out, word, bare, strikes = {}, None, False, {plain(w) for w in STRIKE_WORDS}
    for tok in (t for t in re.split(r"[\s,،]+", words.translate(DIGITS)) if t):
        if re.fullmatch(r"[0-9]+", tok):
            k = int(tok)
            if word is None or not 1 <= k <= n or out.get(k, word) != word:
                return None
            out[k], bare = word, False
            continue
        if bare:
            return None  # an answer word with no number after it answers nothing
        w = plain(tok)
        word, bare = "strike" if w in strikes else ANSWER_WORDS.get(w), True
        if word is None:
            return None
    return out if out and not bare else None
