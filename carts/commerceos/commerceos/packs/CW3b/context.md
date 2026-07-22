# CW3b context — the frozen research (verified at 3c506f9)

## seam map (every ref read fresh from the repo)

**commerceos/catalog/classification.py**
- module docstring :1-19 — CW3's contract: config over the engine, reuses the
  audit's resolver "so the audit and this feature can never disagree",
  silence over guesses.
- `load_taxonomy` :35-41 — taxonomy.json → `_index_taxonomy` (the one indexing
  door). `_TAX` global cache + `_tax()` :44-55 (tests pass their own dict).
- `_normalize_ptype` :58-67 — docstring says "no synonyms, no fuzzy match" —
  the line CW3b supersedes (RULED via the backlog row; the spec already allows
  keyword fallback). the function itself stays as-is: one tidy, last '>'
  segment + whitespace collapse.
- `resolve_leaf` :70-88 — THE single feature-side choke point: resolve_category
  on the raw ptype (:80), then ONE retry on the normalized ptype (:83-87),
  else `(None, is_fold)` → the caller leaves the product out of the queue.
  inherits any resolve_category fallback for free on both calls.
- `_persisted_categories` :91-101 — product_meta commerceos.category facts.
- `_is_resolved` :104-112 — resolved = persisted category in tax["cats"] OR
  product_type resolves NON-fold via resolve_category (:111). **this is where
  a synonym match must NOT count as resolved** or the product never queues.
- `classification_queue` :115-138 — skip resolved (:125), resolve_leaf (:127),
  `None` → not queued (:129, silence over guesses), item shape :131-137
  (`args` = {field: "commerceos.category", product_id, value: leaf}).
- `classification_verify` :141-148 · `classification_progress` :151-164 ·
  `classification_writeback` :167-173 — untouched by this item.

**commerceos/catalog/audit.py**
- `_index_taxonomy` :95-116 — builds `{"cats", "subcat_to_cat", "schema",
  "fc"}`; curated subcategory lists first (:107-109), then the 417-leaf
  `classification.leaf_category_map` via `setdefault` (:113-115, last path
  segment, lowercased). CW3b adds the `synonyms` index here + validation.
- `resolve_category` :119-129 — empty → (None, True); "… — Other" fold branch
  :126-128; else exact `subcat_to_cat` lookup :129. CW3b's fallback goes after
  the exact miss on the NON-fold branch, behind `use_synonyms=True`.
- audit's call :239 (`resolve_category(r["product_type"], tax)`) → the
  classification dimension check :251 (`cat is not None and != "Uncategorized"`).
  synonyms default-on means the audit counts a synonym-typed product as
  classifiable — the same posture it already takes for fold buckets.
- `connect_readonly` :499 — the read-only door for the demostore.db mining step.
- config fail-closed precedent :194-199 (raise ValueError on bad dimensions).

**commerceos/catalog/canonical.py**
- :252 — `category = cat_meta if cat_meta in tax["cats"] else
  resolve_category(p["product_type"], tax)[0]` — the third resolver consumer;
  picks the synonym fallback up automatically. read-side seam: verify, don't
  edit.

**stores/demostore/taxonomy.json** (live instance data, git-tracked)
- top-level keys include `classification` (with `ordered_rules`, `fallback`,
  `leaf_category_map` — 417 leaves) and `version: 2`,
  `status: "LOCKED v1.2 2026-06-30 (owner) …"`. the proposed data home:
  `classification.synonyms`. the LOCK is the open question below.
- in the LIVE taxonomy: "Flashlights" is a subcategory whose category is
  "Lighting" (pinned by tests/test_catalog_classification.py:77 against the
  real file).

**tests/test_catalog_classification.py** (the rig to extend)
- `seed_product` :20-34 (products + optional product_meta fact) · `conn`
  fixture :37-43 (scratch db, spine schema + ledger) · `FakeStore` :46-70
  (scripted metafieldsSet echo/reject).
- the resolver tests :75-87 run against the LIVE demostore taxonomy (no
  fixture passed) — they must stay green untouched.
- queue semantics pins :92-104 · engine round-trip :109-127 · rejection
  honesty :141-149 · dry-run :152-157.

## prior art (copy these shapes)

- the whole of tests/test_catalog_classification.py — same file gains the new
  block; same seed/FakeStore/fixture conventions.
- the fold-bucket precedent (classification.py:104-112 + audit) — "audit says
  classifiable, feature still queues it to persist the metafield" is an
  EXISTING agreed shape; the synonym case is deliberately modeled on it.
- fail-closed config validation: audit.py:194-199.

## binding laws specific to this item

- spec/parts/catalog-workflows.md:158 — the classification feature row:
  *"source-anchored leaf map first, keyword rules only as fallback"*. this IS
  the spec cover for CW3b; the order clause is binding (exact wins, synonym
  only after exact + normalize both miss).
- the refuse-to-guess invariant (classification.py:1-19, :129): a synonym is
  curated data with a validated target — never similarity, never stemming.
  genuine nonsense returns None and stays un-queued.
- one resolver, no disagreement (classification.py:14-18): audit, canonical,
  and the feature must resolve through the same map — verified consumer list
  above; the build must not create a second resolution path.
- spec-first (pull rule 3 / RUNBOOK trigger 1): the code docstrings that say
  "no synonyms" update in the same diff; if any OTHER spec text is found
  contradicting the fallback, the spec edit stages first.
- data vs mechanism (catalog-workflows.md "data" block): the synonym map is
  store data (this store's words), the lookup is mechanism (store-agnostic).
  the automated grep-guard (tests/test_store_agnostic.py:15) bans only the
  store's NAME ("demostore") from commerceos/*.py, comments included — but the
  design law is wider: no gear-specific synonym entries in engine code, ever;
  they live in stores/<store>/ data and in test fixtures only.

## cold-start pointers

- environment: RUNBOOK.md's env block (`uv run pytest -q` ~90s; COMMERCEOS_DB /
  COMMERCEOS_STORE call-time resolution; default store is demostore, which is
  why the no-fixture resolver tests read the live taxonomy).
- required reading: AGENTS.md · .claude/agent-memory/producer/MEMORY.md ·
  the plain-first guard test tests/test_catalog_dashboard.py:240-313 (no new
  surface is built here, but any string that can render must pass it).

## test plan (the pins to write, in tests/test_catalog_classification.py)

fixture: a small tax dict passed explicitly (never the global cache), built
via `_index_taxonomy` from a dict carrying categories {"Lighting":
{"subcategories": ["Flashlights"]}} + `classification.synonyms
{"torch": "Flashlights"}` — plus the live-file pins where named.

1. `test_a_synonym_resolves_through_its_target_leaf` — the backlog check's
   first clause: `resolve_leaf("Torch", tax) == ("Lighting", False)` via the
   torch→Flashlights hop; case-insensitive ("TORCH", "torch").
2. `test_a_seeded_torch_enters_the_queue_and_nonsense_stays_out` — the check
   verbatim at the queue level: seed_product "Torch" → in
   `classification_queue(conn, tax)` with args value = the locked category;
   seed "Zzz Nonsense Widget" → NOT queued. (drop-in beside :92-104.)
3. `test_exact_resolution_always_beats_a_synonym` — the order law: a ptype
   that IS a real leaf resolves identically with and without a synonyms map
   present; and `_index_taxonomy` REFUSES a synonym shadowing a real leaf name.
4. `test_a_synonym_with_an_unknown_target_refuses_loudly` — ValueError from
   `_index_taxonomy` naming the synonym and its dead target (a promised key
   must open a real door).
5. `test_synonym_resolved_stays_queued_until_persisted` — the `_is_resolved`
   escape: "Torch" without a persisted metafield → queued; with
   `category_meta="Lighting"` seeded → not queued (the :98 pattern).
6. `test_audit_and_feature_agree_on_a_synonym_type` — `resolve_category
   ("Torch", tax)` (defaults) == ("Lighting", False): the audit-side and
   canonical-side consumers see the same answer the feature acts on.
7. `test_the_normalized_retry_also_hits_synonyms` — "Something > Torch"
   resolves via normalize → synonym.
8. `test_fold_buckets_never_resolve_via_synonyms` — "Xyz — Other" stays
   unresolvable even if "xyz" were a synonym key; the live-file pin :87 stays
   green.
9. the run round-trip (engine unchanged): seed "Torch", run_feature with
   FakeStore, apply=True → counted, product_meta persisted, queue empties —
   proving the fallback rides the existing gated batch end to end.

no capture script owed: the row is not marked [product]/HARD. the rendered
half of "done" is the seeded-scratch-db TestClient render of /catalog showing
the categories row counting the torch product in its queue (the surfaces are
generic and already guard-walked).

## open questions

- **the locked file** [owner-adjacent]: taxonomy.json reads "LOCKED v1.2
  2026-06-30 (owner)". adding `classification.synonyms` (+ a version note,
  v1.3) is a data change to an owner-ratified artifact. recommendation: build
  the mechanism on fixtures (the check needs no live data), STAGE the demostore
  starter map as a normal staged change named plainly in the make note, and
  let his k land it — same posture as every staged change. if the record shows
  a stricter law for this file, escalate per the pack's trigger.
- **starter map contents**: which of the live unresolved product_types (spec
  counted 17 + 935 fold-bucket at ruling time) get a synonym is a judgment
  call per entry. the rule proposed: only entries with one obviously-correct
  leaf; everything debatable stays unresolved and is listed in the note for
  his glance. no ruling needed to proceed — the mechanism ships either way.
- **audit health movement**: once live synonyms land, the classification
  dimension's live count shifts on the next audit run. that is the item's
  purpose ("the resolver undercounts drift"), but the health mirror's as-of
  discipline means the number moves only when the audit re-runs — worth one
  line in the note so the mirror isn't read as stale-wrong.
