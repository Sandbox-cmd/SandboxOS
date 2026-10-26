# Al-Burhan

A research base for a step-by-step rational case for Islam. The name means "the clear proof" (Quran 4:174).

## The chart (six steps)

1. A creator exists (kalam cosmological argument, contingency).
2. The creator is one (tawhid, mutual hindrance).
3. The creator would communicate with people (prophethood).
4. Muhammad ﷺ was a true prophet (character, fulfilled prophecies, preservation).
5. The Quran is from God (inimitability, i'jaz).
6. Islam completes and corrects earlier revelation.

Each file in `arguments/` supports one of these steps. Every file follows `TEMPLATE.md`: claim, primary texts, argument, objections and replies, sources to verify, status.

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
