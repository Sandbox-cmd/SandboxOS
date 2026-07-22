`git diff --quiet 3c506f9..HEAD -- spec/parts/catalog-workflows.md spec/frames/roster.md spec/parts/fleet.md commerceos/catalog/workflows.py commerceos/catalog/runs.py commerceos/spine/writes.py commerceos/fleet/content.py .claude/agents/content.md || echo "STALE — re-true before build (see RUNBOOK)"`

# scout — arabic localization + descriptions/copy (wave 2)

as-of: commit 3c506f9, suite 394 green.

mission of this scout: map the seams for the two wave-2 content features —
Arabic localization and descriptions/copy generation — and frame the one
ruling that gates them: where the Arabic text comes from, and what the
human-confirm loop concretely is. no build here; a full pack becomes
draftable the moment the ruling card gets its k.

## why it is gated

the spec says so twice, verbatim seams:

- spec/parts/catalog-workflows.md:169 — the Arabic feature row: source
  strategy "generated + human confirm; fit-critical specs stay gated",
  gate class reversible content, verify-render "the localized surface
  renders in Arabic as real as English (C2)".
- spec/parts/catalog-workflows.md:170 — descriptions/copy: "generated
  from the record's typed claims, never invented specs".
- spec/parts/catalog-workflows.md:339-341 (open block) — "Arabic
  localization and copy generation need a source and a human-confirm
  step ruled before they run."
- spec/frames/roster.md:27 and spec/parts/fleet.md:54 — the
  localization/arabic agent row: writer-class translations, "pulled on
  the source + human-confirm ruling".

## seam map (verified 2026-07-19 against the repo)

- **the feature engine**: commerceos/catalog/workflows.py — `Feature`
  dataclass at :40-55 (queue / verify / progress / writeback / intent),
  the `FEATURES` registry at :367-368, `run_feature` at :374-376 now
  carrying `hold: bool = False` (WF-approve, commit dd20d15): a held
  reversible batch parks every proposal and groups them into one
  workflow run.
- **the batch-approve loop**: commerceos/catalog/runs.py — `create` :88,
  `approve` :100 (one glance-approve walks every record through
  gate.resolve → the one-use handle → writes.execute → the feature's
  verify), `reject` :157. this loop is the strongest candidate for the
  human-confirm surface — it already previews was → becomes in plain
  words with the source named.
- **the write door**: commerceos/spine/writes.py `execute` :61 with the
  method dispatch at :87-105. NO translation method exists today — the
  full set is mutate_product_field :123, mutate_seo :176, mutate_price
  :193, mutate_variant_field :220, mutate_spec_verification :243,
  mutate_product_state :290, record_supplier :312. localization needs a
  NEW gated method on the one door (Shopify translations api —
  `translationsRegister`; verify the current api shape at build time).
  a repo-wide grep for "translat" confirms no translation code anywhere
  (the one hit, web/app.py:494, is metric-label wording).
- **the drafting prior art**: commerceos/fleet/content.py — the content
  agent is the shape to copy: refusal at construction (`DraftRefused`
  :38, hype-word law :33-35), `check_draft_against_catalog` :106 (an
  unverified claim never enters a draft), `compute_listing_drafts` :151,
  `propose_and_run` :219. descriptions/copy is nearly an extension of
  this module; Arabic is the same discipline in a second script.
- **the manifest shape**: .claude/agents/content.md — frontmatter-only
  manifest (name, description, scope, writer_class, status, functions),
  ruled the sole source of truth (spec/parts/fleet.md:22-30). the parser
  (commerceos/fleet/manifest.py :43-46) accepts status "built" or
  "building" ONLY — a localization manifest lands when the build starts,
  not before. the /fleet footer "8 more planned agents"
  (commerceos/web/app.py:932) moves by hand when it does.
- **the fit-critical wall**: a live store's database carries spec_claims
  across its products, a subset with fit_critical=1, every row
  verified=0 today. the spec row's law: fit-critical values ride into
  Arabic VERBATIM from spec_claims and stay gated — a translation never
  restates a temp rating in its own words.

## the ruling card — one k

**the question (two halves, one sitting):** where does the Arabic come
from, and what is the human-confirm step?

**half 1 — the source:**

- (a) generated from the canonical record's typed claims — the same law
  the descriptions row already carries (spec :170, "never invented
  specs"), fit-critical values inserted verbatim.
- (b) supplier/manufacturer Arabic text where it exists — it mostly
  doesn't; product_meta carries English.
- (c) an external translation service — cost, and a third party inside a
  loop the owner can already close himself.

**half 2 — the human-confirm loop:**

- (a) WF-approve's hold batch IS the confirm: every Arabic draft parks;
  the owner glance-approves the EN → AR preview per batch. the machinery
  exists since dd20d15 (runs.py:100); the preview would show both
  scripts side by side.
- (b) per-item in-session read with the owner before anything stages.
- (c) an external native reviewer — ruled out by the record: the B3
  lesson (backlog.md, B3 row) says the owner IS the native Arabic/Gulf
  speaker; dialect judgments are his in-session call, never an external
  gate.

**recommendation:** (a) + (a). generation from typed claims matches the
already-ruled descriptions law and reuses content.py's refusal
machinery; WF-approve's hold batch gives the confirm loop for free, and
the owner's glance is the native read — which is exactly what the B3
lesson says it should be. dialect calls surface in the preview and he
rules them on the spot.

**what the k unlocks:** the localization feature row and the
localization agent row become pull-ready; a full pack (likely two — the
executor+feature, then the agent) can be drafted the same day. the
descriptions/copy row shares this ruling but NOT the door: its target
is the product description body (spec :170 — "product description /
body"), and no executor can write that today — mutate_product_field
stops at tags/title/commerceos.* metafields (writes.py:123) and
_mutate_seo writes only the seo.title/seo.description listing fields,
never descriptionHtml (writes.py:176). descriptions/copy becomes
pull-ready only with the description-body write named in the needs
list below.

## what the full pack needs

1. a new gated write method (translation registration) in
   spine/writes.py + a policy row (reversible content per spec :169) —
   same walls as every method: handle consumed before any network call,
   replay refused, read-back receipt.
1a. for the descriptions/copy row: a description-body write —
   descriptionHtml via productUpdate or the current api's equivalent
   (verify the shape at build time) — as its own gated method or a
   widened mutate_product_field branch, same walls. without it the
   descriptions feature has no executor: today's methods stop at
   tags/title/metafields (writes.py:123) and the seo listing fields
   (writes.py:176).
2. a `Feature` row: queue predicate = products with no AR translation;
   verify-render = the localized surface renders on the dev store
   fixture (AGENTS.md names it: your-store.myshopify.com);
   progress = AR coverage per surface (the spec row's metric).
3. `hold=` wired per WF-approve — reversible content still holds for the
   glance-approve; nothing auto-lands.
4. the agent manifest (.claude/agents/localization.md, frontmatter
   alone), landing with the build, footer count moved by hand.
5. tests copying tests/test_content_agent.py (refusal shapes) and
   tests/test_workflow_runs.py (hold/approve pins); replay-refusal and
   provenance assertions are mandatory for any executor (RUNBOOK env
   block).
6. traps to carry: the plain-first guard (tests/test_catalog_dashboard.py)
   governs the OPERATOR surface — Arabic renders on the storefront, but
   any Arabic previewed on the operator surface must escape before
   markup like all record-born ink; and the owner's terminal (Ghostty)
   cannot render RTL (home CLAUDE.md) — previews live on the web
   surface, never in a terminal readback.

## open questions

- none beyond the ruling card itself. the Shopify translations api shape
  should be re-verified at build time, not ruled now.
