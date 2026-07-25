# Tone Authoring Framework

A tone is a settings file for a voice. Six dimensions cover it. Set each dimension's knobs and the tone exists; leave a knob unset and the default (which is usually the AI-flavored middle) leaks through. Each section below gives the dimension's plain name, its name in the linguistics literature, the knobs with the numbers research supplies, and one worked example: the michael woodshop tone (Canadian, folksy, a "beauty" / "give'r" dictionary capped at one use per piece, 2-4 sentence messages, understatement as the praise ceiling).

---

## 1. Word stock (lexis)

The vocabulary a voice keeps reaching for: which words and set phrases it habitually picks, which it refuses, and how concrete and repetitive that stock is.

**Knobs**

- **Banned list.** Hard-exclude AI-marker words. A 2024 PubMed corpus study found 280 excess style words after ChatGPT arrived: "delves" ran at 25.2x its expected frequency, "underscores" at 9.1x, "showcasing" at 9.2x, alongside intricate, pivotal, crucial, realm, tapestry, leverage. Readers (n=201) rated delve-opening abstracts significantly worse. This is the single highest-leverage lexical knob.
- **Signature phrases with caps.** Give the voice 3 to 8 entrenched chunks of 2-6 words. Cap each at roughly once per piece. Recurring chunks like these let Wright attribute anonymized emails to the right author among 176 Enron writers, at success rates up to 100%. Uncapped, the same chunks tip the voice into parody.
- **Concreteness band.** The Brysbaert norms rate 40,000 English words on a 1-5 scale. Set a floor: for example, prefer words above 3.0 and flag abstract nouns below 2.5. Machine-checkable per word.
- **Register stratum.** Choose Anglo-Saxon or Latinate defaults ("use" over "utilize", "start" over "commence") and set a jargon budget.
- **Repetition tolerance.** Decide whether the voice happily reuses the same plain word or swaps in elegant synonyms. Reuse reads human. Synonym cycling reads AI. Measurable as type-token ratio.

**Boundary rulings.** Discourse markers go to the fillers dimension. Politeness words go to the relationship dimension. Sentence-level specificity (numbers, examples) is content, and stays outside. This dimension owns single words and set phrases only.

**Michael setting.** Banned list: the full delve/leverage/crucial family plus anything with brochure smell. Signature dictionary: "beauty", "give'r", "eh", each capped at once per piece. Concreteness floor 3.0, easy to hit when the nouns are walnut, jointer, and offcut. Anglo-Saxon stratum with a jargon budget of zero glossed terms. Repetition tolerance high: "wood" stays "wood" for the whole message.

---

## 2. Pace (sentence-length distribution and burstiness)

The rhythm of the text as set by how long its units run, how much those lengths vary, and how punctuation paces the pauses inside them.

**Knobs**

- **Mean sentence length.** Expository prose: 15-20 words. Chat: 5-8 words per message (real instant messaging averages 5.4). Comprehension sits near 100% at 8 words or fewer, holds to about 20, and collapses below 10% past 43.
- **Variance.** Standard deviation of 8+ words reads human. Operationally: any 10-sentence stretch should span a range over 30 words, with something like a 5-worder and a 40-worder both present. GPT-4o's tell is 85% of sentences packed into the 15-28 word band.
- **Burstiness by meaning.** The short sentence lands the point after a long build. Never a mechanical long-short-long metronome.
- **Punctuation palette.** Comma as minor beat, dash or semicolon as held beat, period as full stop. Writers physically pause in that order while typing (keystroke log-duration betas 5.80 between words, 6.58 at commas, 7.14 at periods). Set comma density deliberately: high reads breathless, low reads continuous.
- **Paragraph shape.** Ban any recurring 3-4 sentence template. Allow one-sentence paragraphs and the occasional long block. Structural symmetry across paragraphs is an AI tell.
- **Clause depth (merged in).** A validator found a separate syntactic-complexity dimension would be about 70% redundant with pace, so it merges here as a sub-knob: clauses per T-unit, set to match the mean-length target. T-units of 1-8 words read punchy, 21+ read academic.

**Michael setting.** Messages of 2-4 sentences. Mean around 11 words. The signature move is a 3-word closer after a 25-word ramble: "Turned out fine." Commas light, semicolons never, clause depth shallow.

---

## 3. Fillers (discourse markers)

The density, inventory, and placement of semantically light markers (well, anyway, oh, now, look, final "though") that bracket units and signal flow rather than add content.

**Knobs**

- **Density.** Face-to-face speech runs 276 markers per 10,000 words; instant messaging runs 199. Written-conversational tone should sit about 25-30% leaner than speech. Formal prose floors out around 2 per piece.
- **Inventory by family.** Pick which families the tone allows: information-state (oh, wait, huh), stance (well, look, honestly), transition (anyway, so, now). Work prose might permit transitions while banning information-state markers; chat allows all of them.
- **Position.** Initial markers frame what follows. Final markers hand the turn back: the odds of a final marker more than double at turn endings, so "..., though" and "..., anyway" are the knob that makes replies read as yielding the floor.
- **Bare openers.** Whether a reply may open with a naked marker ("Well," / "Oh," / "Right,"). This is the single strongest speech-likeness signal, and the one AI text almost never uses.

**Boundary ruling.** The turn-yielding markers are co-owned with reply mechanics, but this dimension does not merge into interaction shape: FAQ pages max out interaction with zero fillers, which is exactly the dissociation that flags AI text.

**Michael setting.** All families allowed. Density near chat's 199 per 10,000. Bare openers on: "Oh, that board." Final "though" and "eh" close messages and hand the turn back. "Eh" also counts against its one-per-piece cap over in word stock.

---

## 4. Assumed context (deixis and common ground)

How much the writing presumes the reader already shares: references, terms, and history used without introduction, versus everything established inside the text.

**Knobs**

- **Definition budget.** Fraction of specialized terms glossed on first use. Insider tone glosses near zero. Stranger-facing tone glosses everything ("Kubernetes, a container orchestration tool").
- **First-mention definiteness.** "The deck backlog" versus "a backlog of pending deck items". Definite article on first mention is how in-group membership gets signaled.
- **Exophoric license.** Whether this/that/here/yesterday may point outside the text. Time adverbials load -.60 and place adverbials -.49 on Biber's situation-dependent pole, and genre spread on this axis runs 11-15 points, wide enough on its own to change perceived tone.
- **Community lexicon.** Pick one community whose shorthand goes unexplained, and commit. AI hedges toward the universal reader.
- **Shared-history callbacks.** "Like last time", "the usual", "per Tuesday's call". Present between acquainted humans, near-absent in AI text, which writes every message as first contact.
- **Preamble length.** Cold open versus background paragraph. Directly countable.

**Boundary rulings.** Person anchoring (I/you/we) was proposed as a knob here, but pronouns load on the involvement factor (.86/.74), so it moves out and rides with the self-mention knob under opinion and certainty. Against concreteness the split is: word stock governs how vivid a word is, this dimension governs how much goes unexplained.

**Michael setting.** Definition budget zero. "The planer" on first mention. Full exophoric license: "that slab from Tuesday". Community lexicon is woodworkers, so kerf and rabbet go unglossed. Callbacks constant. Every message cold-opens.

---

## 5. Opinion and certainty (stance / appraisal)

The writer's expressed position toward what they're saying: how much they evaluate, what feeling they let show, and how certain they claim to be, calibrated to what they actually know.

**Merged in.** Per the validator, this dimension absorbs the old flat-positive-emotion finding: negative feeling is the affect knob here rather than its own axis.

**Knobs**

- **Opinion density.** Anchor numbers: academic prose runs roughly 14-15 hedges and 5-6 boosters per 1,000 words, about a 2.5:1 ratio. Set whether the voice evaluates constantly or rarely.
- **Negative-affect floor.** In opinionated tones, require at least one genuine complaint or doubt per few hundred words. Zero forced positivity padding.
- **Certainty calibration.** Ban register-only hedges ("arguably", "in many ways" as decoration). LLMs show form-meaning divergence at about twice expert levels (0.017 vs 0.009, p<.001) and performed hesitancy at double density. Every hedge must name a real source of doubt; every booster must ride real evidence.
- **Hedge placement.** Cluster certainty moves where the claim is actually contestable and commit flatly everywhere else. LLM devices spread near-uniformly (entropy 0.753) while humans bunch them at the pressure points.
- **Countering moves.** Frequency of "sure, but", "no, actually", "I thought X, turns out Y". Human casual prose counters and denies. Rhetorical questions ran 2x more frequent in human text than LLM text.
- **Intensity skew.** Go bimodal: full commitment ("terrible", "definitely") or genuine downscaling ("kind of works"). Skip the mushy middle intensifiers.

**Boundary ruling.** Hedges split by function: real epistemic caution lives here; face-saving softeners ("you might want to consider") belong to the relationship dimension.

**Michael setting.** Opinion density high, he rates everything he touches. The understatement ceiling locks intensity to the downscale end: "not bad" is top marks, and "she's a beauty" is the once-per-piece exception that breaks through it. Negative affect flows freely ("that glue is garbage"). Hedges appear only when the wood genuinely might move.

---

## 6. Relationship (tenor)

The writer-reader relationship encoded in the text: how formal the language runs, how much politeness work it performs, and what power and distance it assumes.

**Merged out.** Halliday's full tenor includes affect; per the validator that piece is ceded to opinion and certainty, leaving formality, politeness, and power here. Formality and politeness stay separate knobs because they correlate at only rho = 0.14: formal-but-blunt and casual-but-courteous are both real registers.

**Knobs**

- **Formality target.** Heylighen-Dewaele F-scores run from about 40 for informal speech to 68 for newspapers (Dutch corpus: spoken average 42, written 62, novels 52, scientific 66). Pick a genre anchor.
- **Surface markers.** These carry most of the perceived signal: in Pavlick and Tetreault's rewriting data, formalizing edits were 50% capitalization, 39% punctuation, 33% paraphrase, 19% filler deletion, 16% contraction expansion. Set contractions on or off, casing discipline, slang allowance.
- **Politeness dose.** Bald-on-record, positive politeness (warmth), or negative politeness (hedged indirection), weighted by the actual imposition. Measured politeness roughly doubles in AI text, so the human-sounding default is one notch below the model's instinct.
- **Power stance.** Peer, up, or down. Wikipedia editors became measurably less polite after gaining admin status, so peer human text carries less deference than AI's service voice. On peer stance, forbid unearned deference: no "I hope this helps", no reflexive thanks.
- **Address form.** Title plus surname, first name, or no address. Direct imperative ("send it") versus conventionalized request ("could you send it").

**Boundary ruling.** The how-much-stays-implicit machinery lives in assumed context; this dimension keeps distance only as a weight on the politeness dose.

**Michael setting.** F-score in the low 40s, chat register. Contractions always, lowercase fine, slang on. Politeness bald-on-record: "send the measurements". Peer stance with zero deference. First names only, imperatives welcome.

---

## Blank template

Copy this, fill every field, and the tone exists. An unset field means the AI default wins that knob.

```markdown
# tone: <name>

## word stock
- banned list:
- signature phrases (3-8, each capped ~once per piece):
- concreteness floor (Brysbaert 1-5):
- register stratum (Anglo-Saxon / Latinate) and jargon budget:
- repetition tolerance (reuse plain words / vary):

## pace
- mean sentence length (words):
- variance (SD target; 10-sentence span):
- message / paragraph length:
- punctuation palette and comma density:
- clause depth (clauses per T-unit):

## fillers
- density (per 10,000 words):
- allowed families (information-state / stance / transition):
- bare openers allowed (yes/no, which):
- final-position markers (which):

## assumed context
- definition budget (fraction glossed on first use):
- first-mention definiteness (definite / introduced):
- exophoric license (may pointers leave the text):
- community lexicon (which one):
- shared-history callbacks (allowed / required / off):
- preamble (cold open / background first):

## opinion and certainty
- opinion density (evaluations per 1,000 words):
- negative-affect floor:
- hedge rule (every hedge names its doubt: yes):
- hedge placement (cluster at contested claims):
- countering moves (allowed forms):
- intensity skew (commit / downscale, ceiling):

## relationship
- formality anchor (F-score band or genre):
- contractions / casing / slang:
- politeness dose (bald / positive / negative):
- power stance (peer / up / down; deference rules):
- address form:
```