# AI tells, weighted by what readers actually catch

Adapted from stephenoffer/human-voice (MIT) and its sources: a ~90,000-post Reddit audit of what readers cite as AI (JCarterJohnson/vibecoded-design-tells, MIT) and Pangram Labs measurements. The core finding: the tells readers cite and the tells a word list can match are different lists. Fix structure and substance first. Treat a generic-word hit as a whisper.

## Tier A: what readers cite most

These carry the verdict. Approximate share of audited posts citing each.

| Tell | Cited | Fix |
|---|---|---|
| Em dash overuse (AI uses them at 2 to 5x the human rate) | ~7.1% | replace with varied marks: comma here, period there, parens elsewhere. Never swap every one for a comma, that flattens rhythm into a new signature |
| Flat, uniform sentence rhythm | ~4.0% | mix short punches with long sentences. No run of 3+ same-length sentences |
| "not just X, it's Y" antithesis | ~2.8% | state the point plainly |
| Five-paragraph mold with "in conclusion" recap | ~2.5% | let structure follow the argument, end on the last real point |
| Sycophancy ("great question!", "you're absolutely right") | high, no word list catches it | cut entirely, open on the content |
| Saying nothing at length (fluent, confident, empty) | high, no word list catches it | delete the empty sentences. This usually cuts 15 to 25% of the words and most of the AI feel |

## Tier B: real but secondary

- Rule-of-three reflex ("fast, reliable, and scalable"): vary to two or four, or a sentence.
- Bold-lead-in bullets (`- **Term:** ...` on every item): convert some to prose.
- Meta-commentary ("This report will explore..."): state the finding.
- Chatbot scaffolding ("Sure! Here's...", "Let's break it down"): delete.
- Hedging stacks ("may potentially help to somewhat"): commit, or name the real uncertainty once.
- False agency ("the data tells us", "the complaint becomes a fix"): name the human who acted, or use "you".
- Fabricated specificity ("up to 40%" with no source): cite or cut. Never invent.
- Aidiolect phrases ("a testament to", "the complex interplay", "faced numerous challenges"): rewrite the claim.
- Significance inflation ("paves the way", "cannot be overstated"): state the finding.
- Vague attribution ("studies suggest", "experts believe"): name the source or cut.
- Fence-sitting ("several approaches, each with tradeoffs"): pick one and say why the others lose here.
- Terminology drift (one concept, three names): one term per concept. Consistency of materials is human; a document that renames its own subject reads machine.

## Tier C: matches often, cited almost never

however, thus, hence, nuanced, comprehensive, robust, "when it comes to". People genuinely write these. Flagging them hard is how detectors wrongly catch careful and non-native writers (Liang et al. 2023 showed detectors disproportionately misclassify non-native English as AI). A hit here nudges, it never carries a verdict.

## The over-correction costume

Deleting every tell creates a new uniform signature that also reads as AI: forced all-lowercase, sprinkled "lol/honestly?", staccato fragments, conspicuous dash-avoidance. The fix is a real voice with real judgment, and the deepest human quality is stance: commit to a position, weight lopsided tradeoffs, lead with the verdict, name genuine limits.

## Numeric targets

- Sentence-length coefficient of variation at or above roughly 0.5.
- Em-dash density near zero outside creative writing.
- Expect to cut 15 to 25% of words when de-AI-ifying a draft.
- No run of three or more same-length sentences.
