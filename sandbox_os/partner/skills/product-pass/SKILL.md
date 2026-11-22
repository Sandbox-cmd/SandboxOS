---
# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
name: product-pass
description: Load before a page or a thing is shown to a person outside the workshop. A method for reading it once, cold, as that person will, and writing down where they would stop; it reports to the maker and grades nothing.
license: LicenseRef-Winktank-Person-1.0
compatibility: Claude Code and Codex
metadata: {origin: the tool, version: 11.0.0a4}
allowed-tools: Read
---

# The product pass

Something of ours is about to reach a person outside the workshop, a customer or a friend the maker sends a link to. First I read it as they would, once and cold, and note every place they would stop.

What I look for:

- The engineering surface, which is never the product: an id, a code name, an internal shelf name, a status word only we use, a stray fixture line.
- The empty places: a photo box with no photo, a tile with nothing in it, a list that greets a stranger with "none yet".
- The dead ends: a line that sends them to email us, an "ask us" where a plain answer belongs, a step that needs an account.
- What such a page ordinarily shows: a shop names delivery, returns and the price with tax.
- The reach: when the same trip could recur elsewhere, I propose the fix at its source, not a patch here.

Each finding becomes a line in the record with the page and the words I saw; what needs the maker's eye goes to the brief or a card. I say what I did not read.

I never grade the page, never hold it back on my own say, and never show it outside myself: that is one of the five acts, and it asks the maker. A pass is my reading, never a check.

When I finish, I call skill_used with the name "product-pass".
