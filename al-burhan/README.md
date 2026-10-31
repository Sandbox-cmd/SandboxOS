# Al-Burhan

A research base for a step-by-step rational case for Islam. The name means "the clear proof" (Quran 4:174).

## The chart (six steps)

1. A creator exists (kalam cosmological argument, contingency).
2. The creator is one (tawhid, mutual hindrance).
3. The creator would communicate with people (prophethood).
4. Muhammad ﷺ was a true prophet (character, fulfilled prophecies, preservation).
5. The Quran is from God (inimitability, i'jaz).
6. Islam completes and corrects earlier revelation.

Each file in `arguments/` supports one of these steps. `TEMPLATE.md` is a starting shape, not a requirement. The priority is fetchability: every hadith, verse, date and quotation should carry a link someone can open (sunnah.com, quran.com, a named page or paper), and a file may be organised however makes that clearest.

## House rules

- Objections are mandatory. A proof without its strongest objection is not ready.
- Every external fact carries a verify checkbox until checked against a primary source.
- Unfulfilled predictions are not evidence. They are catalogued, not argued from.
- Grade strength honestly. A weak argument kept honest beats a strong-sounding one that collapses on first contact.

## Structure

```
arguments/
  prophecies/            → chart step 4
    contemporary/          about the revelation's own time, verifiable then
    near-fulfillment/      fulfilled within or soon after the Prophet's ﷺ life
    signs-of-the-hour-minor/  signs unfolding across later history
    signs-of-the-hour-major/  eschatological, unfulfilled — non-evidential
  science/               → chart steps 4-5 ("could not have been known then")
    cosmology/
    biology/
    earth-and-water/
sources/                 raw third-party material, local only (gitignored — repo is public)
```

## Index of findings

| File | Category | Strength |
|---|---|---|
| `prophecies/contemporary/romans-victory.md` | contemporary | moderate |
| `prophecies/contemporary/abu-lahab.md` | contemporary | moderate |
| `prophecies/near-fulfillment/conquest-of-mecca.md` | near-fulfillment | weak (self-fulfilling objection) |
| `prophecies/near-fulfillment/persia-byzantium-conquests.md` | near-fulfillment | weak (hadith dating postdates events) |
| `prophecies/signs-of-the-hour-minor/bedouins-tall-buildings.md` | minor sign | moderate |
| `prophecies/signs-of-the-hour-minor/shrinking-of-time-and-distance.md` | minor sign | moderate (conditional on reading) |
| `prophecies/signs-of-the-hour-minor/spread-of-writing-and-knowledge.md` | minor sign | weak |
| `prophecies/signs-of-the-hour-minor/widespread-riba.md` | minor sign | weak (isnad likely broken) |
| `prophecies/signs-of-the-hour-major/README.md` | major signs index | n/a (unfulfilled, non-evidential) |
| `science/README.md` | charter | use with extreme caution |
| `science/cosmology/expanding-universe.md` | cosmology | weak (least weak in folder) |
| `science/cosmology/initial-joined-state.md` | cosmology | weak |
| `science/biology/embryology.md` | biology | weak (Galenic precedent near-decisive) |
| `science/earth-and-water/two-seas-barrier.md` | earth/water | weak |

All files are drafts: nothing is citable until its "Sources to verify" checklist is cleared. The original numbers were written from memory without network access.

Receipt check status (2026-10-27):

| Files | State |
|---|---|
| `contemporary/` (2), `near-fulfillment/` (2) | Hadith numbers, narrators, gradings and dates checked and linked. Open items: primary-source reads (Tabari, Ibn Sa'd, Kaegi), Quran wording, the Badr-versus-Nineveh chronology. |
| `signs-of-the-hour-minor/` (4), `signs-of-the-hour-major/` | Not yet checked. Numbers are still from memory. |
| `science/` (all) | Not yet checked. Numbers, translations and authorities are still from memory. |

Dates are currently checked against Wikipedia and encyclopedia pages only. Treat those as pointers to the primary sources, not replacements for them.

## Prophecy categorization

By when fulfillment occurs relative to the revelation:

| Category | Fulfilled | Evidential weight |
|---|---|---|
| Contemporary | at or around revelation | high if the outcome was genuinely uncertain then |
| Near-fulfillment | within ~decades | high, but check for post-event recording |
| Minor signs of the Hour | across later history | varies; specificity is everything |
| Major signs of the Hour | not yet | none yet, by definition |

The key skeptical test for every prophecy: could the text have been written or interpreted after the event it predicts? Each file must address dating.

## Science arguments

Form: the text states X; X was unknowable in 7th-century Arabia; X is true. Standard rebuttals every file must face: post-hoc reading (the verse is reinterpreted after the discovery), translation elasticity (key words stretched to fit), and precedent (the idea existed in Greek, Syriac or earlier Near Eastern thought — e.g. Galenic embryology). See `arguments/science/README.md`.
