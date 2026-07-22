# What Makes Language Human

Prepared 2026-07-22 as the evidence base for a writing skill. Every finding below carries its sources; where a verifier checked the underlying paper, the caveats from that check are folded into the text.

## 1. The answer in one paragraph

Human language is uneven and machine language is smooth. In every corpus comparison the human side shows more spread: scattered sentence lengths, unequal paragraphs, emotional swings that include fear and annoyance, plain words that repeat because the writer never reached for a thesaurus. One LIWC study measured human dialogues at a mean of 58 words with a standard deviation of 120.5 against ChatGPT's mean of 300 with a standard deviation of 25.6, and found lower machine variance on all 118 categories tested. Readers feel this before they can name it: in a large Turing test, 43% of judges' stated reasons concerned linguistic style and 24% concerned social and emotional texture, while only about 10% concerned knowledge or reasoning. The craft therefore has two moves. First, match the register natives write in, because "human" inverts between registers (contractions belong in a DM and would be a defect in a spec). Second, inside that register, keep the human irregularity in length, structure, emotion, and vocabulary that models sand away.

## 2. Universal markers (apply to all tones)

**Keep sentence-length variance high.** Humans show scattered sentence-length distributions where every LLM tested clusters near its mean; detector heuristics treat a standard deviation of 8+ words as human-like and under 5 as AI-like, and a feature-based detector combining length variance with other stylometric features hit F1 = 0.94 against 0.81 for perplexity alone. Sources: [Muñoz-Ortiz et al.](https://arxiv.org/abs/2308.09067), [detector heuristics guide](https://fast.io/resources/is-this-ai-generated-checker-guide/), [feature-based detection study](https://www.researchgate.net/publication/398588043_Feature-Based_Detection_of_AI-Generated_Text_An_Analysis_of_Stylometric_and_Perplexity_Markers_in_Contemporary_Large_Language_Models).

**Cut the four grammatical tics with the largest measured effect sizes.** Reinhart et al. (PNAS 2025) measured GPT-4o against parallel human corpora: present-participial clause openers at 5.3x the human rate (d = 1.38), nominalizations at 1.5-2x (d = 1.23), paired phrasal coordination ("clarity and confidence") at 1.9x (d = 0.81), and that-clauses as subjects at 2.6x (d = 0.77); a classifier on these features separated humans from individual LLMs at 93-98% accuracy. Rewrite participial openers as finite clauses and turn -tion/-ment nouns back into verbs. Sources: [Reinhart et al. (arXiv)](https://arxiv.org/html/2410.16107), [PNAS version](https://www.pnas.org/doi/10.1073/pnas.2422455122).

**Ban the statistically flagged vocabulary, and refresh the list.** "Tapestry" appeared in 23% of GPT-4o outputs and "amidst" in 27%; words like "camaraderie", "palpable", "intricate", and "delve" run at 100-171x human rates, and GPT-4 separately overuses "significant" and "notable" (SHAP ranked such words among the top discriminators, up to 0.98 accuracy). The list decays: "delve" dropped sharply in arXiv abstracts after early 2024 once publicized, while "significant" kept rising, so second-generation tells matter as much as famous ones. Sources: [Reinhart et al.](https://arxiv.org/html/2410.16107), [Geng et al. on coevolution](https://arxiv.org/abs/2502.09606), [refsmmat LLM-style review](https://www.refsmmat.com/notebooks/llm-style.html), [stylometry study](https://arxiv.org/html/2507.00838v1), [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).

**Break structural uniformity, from clause to document.** LLM text is "frequency-standardised": its POS and syntactic patterns sit in a narrow band with deeper, longer dependency structures, while human syntax is messier and spreads wider. At document scale, detection guides flag templated intro-body-conclusion architecture, near-equal paragraph lengths, and paragraph openers like "Additionally" or "Moreover"; human documents spend disproportionate space on the interesting part and end on a point instead of a restatement. Sources: [stylometry study](https://arxiv.org/html/2507.00838v1), [dependency analysis](https://arxiv.org/pdf/2308.09067), [Paperpal](https://paperpal.com/blog/academic-writing-guides/reasons-your-writing-looks-like-ai-and-how-to-fix-it-manually), [Pangram](https://www.pangram.com/blog/did-ai-write-this).

**Kill rule-of-three padding and manufactured contrast.** Triple adjective lists and "not just X, but Y" negative parallelisms are catalogued machine patterns that pad thin analysis with false rhythm. Source: [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).

**Style carries the humanness verdict; knowledge does not move it.** In Jones & Bergen's preregistered Turing test (GPT-4 judged human 54% of the time against 67% for real humans), 43% of judges' reasons were linguistic style, 24% were socio-emotional, and about 10% were knowledge; "too perfect grammar" and templatic sentence shapes triggered AI verdicts. Verified exactly against the paper; the setting was adversarial live chat, so generalization to static text leans on the Jakesch evidence below, which exists. Source: [Jones & Bergen](https://arxiv.org/html/2405.08007).

**Readers key on first-person pronouns, contractions, and lived specifics.** Across 6 experiments with roughly 4,600 participants, people could not detect AI self-presentations and relied on exactly those heuristics, which are exploitable to make text "more human than human"; the practical rule is to ground the markers in real detail, since a separate adversarial study found "forcing a persona" is itself a classic tell (that backfire link is a cross-study inference, so hold it looser). Sources: [Jakesch, Hancock & Naaman](https://arxiv.org/abs/2206.07271), [Jones & Bergen](https://arxiv.org/html/2405.08007).

**The stakes are warmth stakes.** When text gets pegged as AI, readers dock warmth, sincerity, effort, and authenticity while still granting clarity and competence; recipients of identical messages rated the sender "lazy, insincere" under an AI label and "genuine, thoughtful" under a human one, and blind raters kept favoring whatever was labeled human even when labels were swapped. Human markers therefore matter most where the text must convey care. Sources: [IUI disclosure study](https://arxiv.org/pdf/2510.24011), [The Conversation on Molnar & Zhu](https://theconversation.com/most-people-do-not-realize-when-a-personal-message-they-receive-was-written-by-ai-study-finds-278874), [label-bias study](https://arxiv.org/pdf/2410.03723), [CASA literature](https://www.sciencedirect.com/science/article/abs/pii/S0747563222001431).

**Calibrate to the register every time.** A register-aware evaluation across 5 datasets and 7 LLMs found model rankings flip by register and concluded human-likeness must be judged per register; the feature mix that reads human in news prose reads inhuman in chat, and spoken conversation showed the largest human-LLM gaps of any register. Source: [register-aware evaluation](https://arxiv.org/abs/2605.23651).

## 3. Per-tone findings

### Work

**Stay at the informational pole; do not inject chattiness into a spec.** Biber's Dimension 1 puts academic prose and official documents at the noun-heavy, preposition-dense, lexically varied pole, the mirror image of conversation; informational density is what reads as native there. Sources: [Biber's dimensions](https://www.uni-bamberg.de/fileadmin/eng-ling/fs/Chapter_21/23DimensionsofEnglish.html), [Kilgarriff's Biber review](https://kilgarriff.co.uk/Publications/1995-K-BiberReview.asc).

**Hold reading grade near 12 and let plain words repeat.** ChatGPT essays beat human essays on every diversity metric (TTR 0.69 vs 0.61, MTLD 118 vs 66.6) while landing at Flesch-Kincaid grade 16.6 against the human 12.1 and Gunning-Fog 20.1 against 14.2; the robust rule is the readability gap plus tolerance for repetition, since the diversity direction flips by genre (professional news writers out-vary LLMs). Sources: [Frontiers in Education corpus study](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2025.1616935/full), [Muñoz-Ortiz et al.](https://arxiv.org/abs/2308.09067).

**Cut trailing significance clauses.** Sentences ending in "highlighting Y" or "underscoring Z" imply depth without evidence; Wikipedia's catalog documents the pattern, and corpus work puts LLM participial-clause use at roughly 2-5x the human rate (treat that multiplier as approximate; the specific survey citation could not be spot-checked, though it matches Reinhart's numbers). Sources: [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), [linguistic characteristics survey](https://www.researchgate.net/publication/396291341_Linguistic_Characteristics_of_AI-Generated_Text_A_Survey).

**An occasional natural passive is fine here.** GPT-4o uses agentless passives at about half the human rate, so scrubbing every passive from formal prose moves you toward the machine profile; reserve abstract machinery (passives, formal connectors, abstract nouns) for the registers that call for it. Sources: [PNAS](https://www.pnas.org/doi/10.1073/pnas.2422455122), [Biber's dimensions](https://www.uni-bamberg.de/fileadmin/eng-ling/fs/Chapter_21/23DimensionsofEnglish.html), [marketing MDA study](https://www.mdpi.com/2076-3387/15/12/492).

**Default to running prose; formatting chrome is the fastest tell.** Bold-label bullets, headings jammed into short answers, and numbered steps where paragraphs belong are practitioner-catalogued dead giveaways, because chat models are tuned to produce them by default; use structure only when the reader will genuinely scan. Sources: [aicleantext](https://aicleantext.com/how-to-stop-chatgpt-from-formatting-text/), [vrid](https://vrid.ai/blog/signs-of-ai-writing), [OpenAI community thread](https://community.openai.com/t/excessive-bullet-point-formatting-issue-in-chatgpt-responses/1097391).

**Every claim gets a nameable source or number, or it gets cut.** Weasel attributions ("industry reports suggest", "experts note") and hollow "from X to Y" range constructions are signature AI patterns that create the illusion of sourced analysis. Sources: [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), [Forbes summary](https://www.forbes.com/sites/jodiecook/2025/09/08/the-10-giveaway-signs-of-ai-writing-wikipedia-reveals/).

**Add hedges where you are actually uncertain.** LLM text is measurably poorer in interactional metadiscourse (hedges, boosters, attitude markers, personal asides) and prefers nouns where humans anchor meaning in verbs, modals, tense, and mood; verb-driven clauses with honest epistemic markers read human in reports too. Sources: [refsmmat review](https://www.refsmmat.com/notebooks/llm-style.html), [authorship-traits study](https://arxiv.org/abs/2508.16385).

### Conversation

**One short line is a normal reply.** Baron's AIM corpus (2,185 transmissions) averaged 5.4 words per message, with 21.8% single-word messages and users sending 4.0 messages per minute; 5.4 words sits nearer spoken intonation units (6.2) than written prose (9.3). Source: [Baron](https://nl.ijs.si/janes/wp-content/uploads/2014/09/baron10.pdf).

**Split one thought across rapid messages.** 42% of sender sequences ran more than one transmission (mean 1.7, max 18), and 16.2% of all transmissions were utterance-break pairs splitting a sentence at a clause boundary ("that must be nice" / "to be in love"). Source: [Baron](https://nl.ijs.si/janes/wp-content/uploads/2014/09/baron10.pdf).

**Brevity plus variance beats length.** In the LIWC comparison, human dialogues ran M = 58 words (SD 120.5) against ChatGPT's M = 300 (SD 25.6), with lower machine variance across all 118 categories and higher human authenticity (63.99 vs 52.49). Verified exactly, with one mandatory downgrade: the figures are per dialogue from one dataset and one model, so quote the direction (AI longer, far less variable) as robust and never "5x" as a constant. Source: [LIWC study](https://arxiv.org/html/2401.16587v1).

**Dial politeness down and "I" up.** Measured politeness roughly doubles in ChatGPT text (0.49 vs human 0.22), prosocial markers more than double (1.75 vs 0.72), and ChatGPT over-attends to "you"/"we" (attentional focus 64.79 vs 34.89) where humans write from "I". Sources: [LIWC study](https://arxiv.org/html/2401.16587v1), [expert-panel detection study](https://arxiv.org/pdf/2601.19913).

**Answer minimal with minimal.** Whole human turns consist of "okay.", "haha", "jah", "blech", or "haha aight" (all verified in Raclaw's corpus), and laughter tokens preface agreement ("haha homework IS stupid"); the backchannel literature treats these as real turn-management work, so a habit of always elaborating after acknowledging breaks the pattern (the MDPI corpus is spoken conversation, supporting the general point). Sources: [Raclaw corpus](https://doi.org/10.25810/5e6r-fk53), [backchannel timing study](https://www.mdpi.com/2226-471X/10/8/194).

**Close like a person leaving.** IM closings run a pre-close ("okay", "anyway"), an account with a hedge ("i should probably start my paper"), often an arrangement ("talk tomorrow?"), then a short terminal token ("later!"); Baron measured closing sequences at about seven transmissions over roughly 32 seconds. One flat "Goodbye!" is nobody's pattern. Sources: [Raclaw corpus](https://doi.org/10.25810/5e6r-fk53), [Baron](https://nl.ijs.si/janes/wp-content/uploads/2014/09/baron10.pdf).

**Use informality as seasoning.** In Thurlow's 544-message SMS corpus, abbreviations were 18.75% of content even though 82% of participants claimed to use them; the whole corpus held only 73 letter-number homophones ("gr8") and 39 emoticons, with most typographic play being kisses, exclamation marks, and lengthening ("byeeeeeeeee"). Mostly standard spelling with spot informality is the real texture. Sources: [Thurlow](https://extra.shu.ac.uk/daol/articles/v1/n1/a3/thurlow2002003-04.html), [Raclaw corpus](https://doi.org/10.25810/5e6r-fk53).

**A corrected typo humanizes; perfection and sloppiness both fail.** Across five studies with 3,000+ participants, chatbot agents that made and then fixed typos ("*meant X") were rated significantly more human and warmer than both no-typo and uncorrected-typo agents, even when participants knew it was a bot; the mechanism named was that correction shows an engaged mind. Verified in full; rests on one paper's line of studies. Sources: [Berkeley Haas newsroom](https://newsroom.haas.berkeley.edu/research/to-err-is-human-and-in-the-age-of-ai-it-may-be-humanizing/), [TechXplore](https://techxplore.com/news/2024-08-err-human-age-ai-humanizing.html).

**Take a stance.** Judges cited "overly polite or helpful demeanor" and lack of personality as top AI tells, while humor, contrarian responses, and spontaneous unprompted comments drove human verdicts. Verified verbatim for chat; the extension to copy and work documents is unevidenced extrapolation, so treat stance-taking outside conversation as hypothesis. Source: [Jones & Bergen](https://arxiv.org/html/2405.08007).

**Lean into the involved register.** Conversation scores highest on Biber's involved pole: private verbs (think, guess, feel), that-deletion, contractions, present tense, second-person pronouns ("I think you're right" over "I believe that you are correct"); LLMs consistently underuse contractions and involved pronouns, and conversation is where the human-LLM gap is widest, so restoring them buys the most per edit. Sources: [Biber's dimensions](https://www.uni-bamberg.de/fileadmin/eng-ling/fs/Chapter_21/23DimensionsofEnglish.html), [register-aware evaluation](https://arxiv.org/html/2605.23651).

**Let drafting show.** Keystroke research finds human writing is pause-and-revise throughout, with repairs signaling spontaneity and polish signaling preparedness; a mid-thought restart ("actually, scratch that") in a supposedly dashed-off message is authentic. This is process evidence, so weight it lighter than the corpus findings. Sources: [pauses in spontaneous written communication](https://www.researchgate.net/publication/276487969_Pauses_in_spontaneous_written_communication_A_keystroke_logging_study), [keystroke logging in writing research](https://www.researchgate.net/publication/283794735_Keystroke_logging_in_writing_research_Analyzing_online_writing_processes).

**Humor should withhold the turn.** LLM humor defaults to puns and telegraphed punchlines and collapses the two-interpretation structure jokes need by revealing the resolution early; human-sounding humor is observational and situation-specific, lands at the end, and is allowed to be dry. Sources: [humor generation study](https://arxiv.org/pdf/2509.12158), [irony/sarcasm survey](https://arxiv.org/html/2511.09133v1), [satire study](https://arxiv.org/pdf/2508.07959).

### Copy

**Swap category words for picturable ones.** Packard & Berger (Journal of Consumer Research, 1,000+ real customer interactions): one SD more concreteness in employee language raised satisfaction 8.9% on phone calls and spending 10-13% over 90 days via email, because customers infer the speaker is listening; the effect vanished when concrete words were irrelevant to what the customer asked. "Grey jeans" beats "pants" only when jeans were the question. Source: [Packard & Berger](https://academic.oup.com/jcr/article/47/5/787/5873524).

**Address the reader as "you".** Cruz, Leonhardt & Pezzuti (Journal of Interactive Marketing 2017) found second-person pronouns in brand posts correlate with higher involvement and brand attitude, mediated by self-referencing; the effect weakens for collectivist audiences, and the data is correlational. The companion "write as I" half is craft lore whose cited Ogilvy source is dead (HTTP 410); Ogilvy's 1982 memo ("Write the way you talk. Naturally.") is the honest primary source. Sources: [Cruz et al.](https://www.sciencedirect.com/science/article/abs/pii/S1094996817300348), [enchantingmarketing on Halbert](https://www.enchantingmarketing.com/gary-halbert-boron-letters/).

**Make prose move like talk.** Halbert's Boron Letters model three techniques: opening questions aimed at the reader personally, everyday transitions ("Well," "anyway," "now") appearing about 33 times across 18 letters, and vivid particulars from the writer's actual situation ("It's so hot in this room I have to keep a bandanna..."). Source: [enchantingmarketing analysis](https://www.enchantingmarketing.com/gary-halbert-boron-letters/).

**Write to grade 6-8 for general audiences and never past 12.** NN/g's plain-language research found even highly educated readers prefer succinct, scannable text; in usability sessions an IT manager, a professor, and a nurse practitioner all preferred the plainer versions, and Oppenheimer (2006) documents the penalty for needless complexity. Source: [NN/g plain language for experts](https://www.nngroup.com/articles/plain-language-experts/).

**Assume scanning and front-load meaning.** NN/g's eye-tracking corpus (500+ participants, 750+ hours over 13 years) found 79% of users scanned rather than read, and the 232-participant 2006 study established the F-shaped pattern; structure so the fraction they do read is the right fraction. This is the counterweight to the formatting-chrome warning above: use headings and bullets for genuinely scannable web copy, plain prose everywhere else. Sources: [NN/g eyetracking report](https://www.nngroup.com/reports/how-people-read-web-eyetracking-evidence/), [NN/g background](https://en.wikipedia.org/wiki/Nielsen_Norman_Group).

**Average 15-20 words per sentence, split past 30, and vary on purpose.** Comprehension drops sharply on long sentences and web readers skip what they cannot parse on first read; a short sentence lands the point after longer ones elaborate, while uniformly short sentences read choppy and robotic. Craft consensus plus readability research, no single controlled result. Sources: [sentence-length readability](https://lettercounter.org/blog/sentence-length-readability/), [NN/g](https://www.nngroup.com/articles/plain-language-experts/), [CUNY writing guide](https://gcwritingcenter.commons.gc.cuny.edu/rs_style-tone-and-voice-introduction/rs_style_diversify-sentence-structure-and-length/).

**Test the words; judge on granular behavior.** Practitioners report 5-25% conversion improvements from small copy changes to headlines and CTAs, and Booking.com pairs conversion with interaction metrics to interpret copy tests; these are practitioner-reported ranges, unrefereed. Sources: [UX Content Collective](https://uxcontent.com/how-to-ab-test-copy/), [Booking.com writing team](https://medium.com/booking-writes/a-b-tests-and-copy-what-why-how-8cc4ae17eae2).

**Draft as a letter to one person, out loud in your head.** The verified leg is Halbert's friendly-conversation frame; the Ogilvy attributions failed verification (one source gone, the other lacking the claim), so cite his 1982 memo directly if the skill quotes him. Keep only what you would say across a table. Sources: [enchantingmarketing](https://www.enchantingmarketing.com/gary-halbert-boron-letters/), [qualaroo (weak; does not contain the attribution)](https://qualaroo.com/blog/the-science-of-website-copywriting-tips-from-david-ogilvy/).

**Mix involvement with overt persuasion.** A Biber-MDA study of 225 top-brand marketing texts found effective ads combine personal pronouns, contractions, and private verbs with imperatives, conditional "if", and necessity modals (will/should/must); the impersonal informational default is the wrong pole for copy. Sources: [marketing MDA study](https://www.mdpi.com/2076-3387/15/12/492), [Biber's dimensions](https://www.uni-bamberg.de/fileadmin/eng-ling/fs/Chapter_21/23DimensionsofEnglish.html).

**Keep the negative affect.** Human text carries more fear and disgust and less joy than LLM output, which skews evenly upbeat; when the honest reaction is annoyance or ambivalence, say it plainly, because relentless positivity is a statistical tell. Source: [Muñoz-Ortiz et al.](https://arxiv.org/abs/2308.09067).

**Use "is". Cut puffery.** Wikipedia's catalog (verified: it has an "avoidance of basic copulatives" section) documents AI rewriting "is" into "serves as" and "stands as", plus advertisement adjectives like "vibrant", "rich", "nestled", and "renowned"; this advice predates LLMs as style guidance, so following it costs nothing even where the AI attribution is loose. Source: [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).

## 4. Folk beliefs that did not survive verification

**"Em dashes mean AI."** Frequency does not separate the groups: AI learned the habit from professional essayists who use them heavily, while AP-style journalists avoid them. Stripping them to look human targets a myth. Sources: [duey.ai](https://www.duey.ai/post/em-dash-ai-writing), [Fraise](https://victoriafraise.medium.com/no-em-dashes-are-not-a-sign-of-ai-f14629a4d217).

**"Low perplexity and low burstiness mean AI."** Perplexity-based detection misclassifies the Declaration of Independence as AI (memorized text scores low), is model-dependent, cannot run on closed models, and falsely flags non-native writers whose constrained vocabulary lowers perplexity; modern models also mix sentence lengths now, so gaming word-surprise fails in both directions. Source: [Pangram Labs](https://www.pangram.com/blog/why-perplexity-and-burstiness-fail-to-detect-ai).

**"Passing a detector proves the text reads human."** Seven GPT detectors flagged 61.3% of real human TOEFL essays as AI (about 20% flagged unanimously) while scoring near-perfectly on US 8th-grade essays; the cause was low perplexity from constrained expression, which is exactly the profile a mechanical humanizing checklist can produce. The success criterion is reader experience. Sources: [Liang et al.](https://arxiv.org/abs/2304.02819), [Patterns version](https://www.sciencedirect.com/science/article/pii/S2666389923001307), [The Markup on false accusations](https://themarkup.org/machine-learning/2023/08/14/ai-detection-tools-falsely-accuse-international-students-of-cheating).

**"Never repeat a word; richer vocabulary reads more human."** Reversed in the student-essay data: ChatGPT beat humans on every lexical-diversity metric (TTR 0.69 vs 0.61) while being far harder to read (grade 16.6 vs 12.1); thesaurus-swapping moves text toward the machine profile. The direction flips against professional news writers, so raw diversity is unreliable in either direction as a humanness signal. Sources: [Frontiers study](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2025.1616935/full), [Muñoz-Ortiz et al.](https://arxiv.org/abs/2308.09067).

**"A fixed AI-word blacklist stays valid."** "Delve" was the famous 2023-2024 tell and dropped off sharply by 2025 while "significant" kept rising; word tells decay as models retrain, so any ban list needs a dated refresh cycle. Sources: [Geng et al.](https://arxiv.org/pdf/2502.09606), [stylometry study](https://arxiv.org/html/2507.00838v1).

**"Typos make text human."** Only repaired ones do. Agents with uncorrected typos rated no better than flawless ones; the humanizing signal was the visible correction. Source: [Berkeley Haas](https://newsroom.haas.berkeley.edu/research/to-err-is-human-and-in-the-age-of-ai-it-may-be-humanizing/).

**"AI conversational text is 5x longer than human, as a constant."** The measured ratio came from one dataset regenerated by one model with a 250-token cap; the verifier required downgrading the number. The direction (AI longer and far less variable) is what generalizes. Source: [LIWC study](https://arxiv.org/html/2401.16587v1).

**Citation failures worth knowing about.** Two Ogilvy sources cited in the craft findings failed checks: one returned HTTP 410 and the other never contained the "personal letters" attribution. The Halbert leg verified. If the skill quotes Ogilvy, quote the 1982 memo.

## 5. Sources

**Corpus and stylometry**
- [Muñoz-Ortiz et al., human vs LLM news text (arXiv 2308.09067)](https://arxiv.org/abs/2308.09067)
- [Reinhart et al., Biber-feature comparison, PNAS 2025 (arXiv 2410.16107)](https://arxiv.org/html/2410.16107) / [PNAS](https://www.pnas.org/doi/10.1073/pnas.2422455122)
- [Geng et al., Human-LLM Coevolution (arXiv 2502.09606)](https://arxiv.org/abs/2502.09606)
- [Stylometric analysis of LLM vs Wikipedia text (arXiv 2507.00838)](https://arxiv.org/html/2507.00838v1)
- [Authorship traits study (arXiv 2508.16385)](https://arxiv.org/abs/2508.16385)
- [Register-aware human-likeness evaluation (arXiv 2605.23651)](https://arxiv.org/abs/2605.23651)
- [Frontiers in Education, ChatGPT vs student essays](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2025.1616935/full)
- [refsmmat, review of LLM style research](https://www.refsmmat.com/notebooks/llm-style.html)
- [Japanese stylometry classifier (PMC12558491)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12558491/)
- [Feature-based detection study (ResearchGate)](https://www.researchgate.net/publication/398588043_Feature-Based_Detection_of_AI-Generated_Text_An_Analysis_of_Stylometric_and_Perplexity_Markers_in_Contemporary_Large_Language_Models)
- [Linguistic Characteristics of AI-Generated Text survey (ResearchGate, unspot-checked)](https://www.researchgate.net/publication/396291341_Linguistic_Characteristics_of_AI-Generated_Text_A_Survey)

**Conversation**
- [Baron, AIM corpus study](https://nl.ijs.si/janes/wp-content/uploads/2014/09/baron10.pdf)
- [Raclaw, IM closings corpus](https://doi.org/10.25810/5e6r-fk53)
- [Thurlow, SMS corpus](https://extra.shu.ac.uk/daol/articles/v1/n1/a3/thurlow2002003-04.html)
- [LIWC human vs ChatGPT dialogues (arXiv 2401.16587)](https://arxiv.org/html/2401.16587v1)
- [Backchannel distribution and timing (Languages 10(8):194)](https://www.mdpi.com/2226-471X/10/8/194)
- [Expert-panel detection study (arXiv 2601.19913)](https://arxiv.org/pdf/2601.19913)
- [Keystroke pauses study](https://www.researchgate.net/publication/276487969_Pauses_in_spontaneous_written_communication_A_keystroke_logging_study) / [keystroke logging methods](https://www.researchgate.net/publication/283794735_Keystroke_logging_in_writing_research_Analyzing_online_writing_processes)

**Perception**
- [Jones & Bergen, Turing test (arXiv 2405.08007)](https://arxiv.org/html/2405.08007)
- [Jakesch, Hancock & Naaman (arXiv 2206.07271)](https://arxiv.org/abs/2206.07271) / [PNAS](https://www.pnas.org/doi/10.1073/pnas.2208839120) / [Cornell summary](https://news.cornell.edu/stories/2023/03/ai-or-human-written-language-assumptions-mislead)
- [Schroeder et al. via Berkeley Haas](https://newsroom.haas.berkeley.edu/research/to-err-is-human-and-in-the-age-of-ai-it-may-be-humanizing/) / [TechXplore](https://techxplore.com/news/2024-08-err-human-age-ai-humanizing.html)
- [AI-authorship disclosure study (arXiv 2510.24011)](https://arxiv.org/pdf/2510.24011)
- [The Conversation, Molnar & Zhu coverage](https://theconversation.com/most-people-do-not-realize-when-a-personal-message-they-receive-was-written-by-ai-study-finds-278874)
- [AI-authorship effect, Journal of Business Research](https://www.sciencedirect.com/science/article/abs/pii/S0148296324004880)
- [Label-bias study (arXiv 2410.03723)](https://arxiv.org/pdf/2410.03723)
- [CASA study (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0747563222001431)

**Register**
- [Biber's dimensions of English (Bamberg)](https://www.uni-bamberg.de/fileadmin/eng-ling/fs/Chapter_21/23DimensionsofEnglish.html)
- [Kilgarriff, review of Biber](https://kilgarriff.co.uk/Publications/1995-K-BiberReview.asc)
- [Biber-MDA study of 225 marketing texts (MDPI)](https://www.mdpi.com/2076-3387/15/12/492)

**Copy and craft**
- [Packard & Berger, concreteness (JCR)](https://academic.oup.com/jcr/article/47/5/787/5873524)
- [Cruz, Leonhardt & Pezzuti, second-person pronouns](https://www.sciencedirect.com/science/article/abs/pii/S1094996817300348)
- [Halbert's Boron Letters analysis](https://www.enchantingmarketing.com/gary-halbert-boron-letters/)
- [NN/g plain language for experts](https://www.nngroup.com/articles/plain-language-experts/) / [eyetracking report](https://www.nngroup.com/reports/how-people-read-web-eyetracking-evidence/)
- [Sentence-length readability](https://lettercounter.org/blog/sentence-length-readability/) / [CUNY guide](https://gcwritingcenter.commons.gc.cuny.edu/rs_style-tone-and-voice-introduction/rs_style_diversify-sentence-structure-and-length/)
- [UX Content Collective, A/B testing copy](https://uxcontent.com/how-to-ab-test-copy/) / [Booking.com writing team](https://medium.com/booking-writes/a-b-tests-and-copy-what-why-how-8cc4ae17eae2)
- [qualaroo Ogilvy page (failed verification for the attribution)](https://qualaroo.com/blog/the-science-of-website-copywriting-tips-from-david-ogilvy/)

**Detection folk beliefs and tells**
- [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) / [Forbes summary](https://www.forbes.com/sites/jodiecook/2025/09/08/the-10-giveaway-signs-of-ai-writing-wikipedia-reveals/)
- [Pangram on perplexity and burstiness](https://www.pangram.com/blog/why-perplexity-and-burstiness-fail-to-detect-ai) / [Pangram, did AI write this](https://www.pangram.com/blog/did-ai-write-this)
- [Liang et al., detector bias against non-native writers (arXiv 2304.02819)](https://arxiv.org/abs/2304.02819) / [Patterns](https://www.sciencedirect.com/science/article/pii/S2666389923001307) / [The Markup](https://themarkup.org/machine-learning/2023/08/14/ai-detection-tools-falsely-accuse-international-students-of-cheating)
- [duey.ai on the em-dash myth](https://www.duey.ai/post/em-dash-ai-writing) / [Fraise on Medium](https://victoriafraise.medium.com/no-em-dashes-are-not-a-sign-of-ai-f14629a4d217)
- [fast.io detector heuristics guide](https://fast.io/resources/is-this-ai-generated-checker-guide/)
- [aicleantext on ChatGPT formatting](https://aicleantext.com/how-to-stop-chatgpt-from-formatting-text/) / [vrid signs of AI writing](https://vrid.ai/blog/signs-of-ai-writing) / [OpenAI community on bullet overuse](https://community.openai.com/t/excessive-bullet-point-formatting-issue-in-chatgpt-responses/1097391)
- [Paperpal on AI-looking writing](https://paperpal.com/blog/academic-writing-guides/reasons-your-writing-looks-like-ai-and-how-to-fix-it-manually) / [eyesift](https://www.eyesift.com/blog/how-to-tell-if-ai-written/)

**Humor**
- [Humor generation limits (arXiv 2509.12158)](https://arxiv.org/pdf/2509.12158) / [irony and sarcasm (arXiv 2511.09133)](https://arxiv.org/html/2511.09133v1) / [satirical headlines (arXiv 2508.07959)](https://arxiv.org/pdf/2508.07959)