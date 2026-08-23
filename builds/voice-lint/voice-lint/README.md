# voice-lint — the plain-language law as a portable check

One check, keyed to `soul/voice.md`, that any channel can load and run. It
reads the banned-word list straight from the law — no hardcoded copy that
drifts — and scans a path for it. A hit names its file and line.

## why this exists

The same check had been paid for three times: the tool's own
`engine/tests/test_voice.py`, commerceos's by-hand "plain-language pass" over
its web copy, and sandbox-site's `build/check.py`. One lesson, three
rebuilds. This is that lesson made mechanism, once.

## load it on a channel

    sandbox load voice-lint

Then add one line under `## checks` in the channel's CHANNEL.md:

    python3 voice_lint.py . --dict ~/Desktop/SandboxOS_workshop/soul/voice.md

Or set `VOICE_DICT` once and drop the flag:

    VOICE_DICT=~/Desktop/SandboxOS_workshop/soul/voice.md python3 voice_lint.py .

## what it checks

- **banned words** — pulled live from `voice.md`'s `- cut:` list. Single
  words (`leverage`, `delve`, `robust`) and quoted phrases
  (`"it's worth noting"`). 22 in force at last count.
- **the programmer plural** — `user(s)`, `file(s)`, `check(s)`. voice.md bans
  it by stance: "you build a thing", never "users can create artifacts."

## what it deliberately does NOT check

The multi-word style notes in voice.md — `adjective pile-ups`,
`warm-up intros`, `transitions that restate` — are left out. A regex can't
enforce judgment. Those stay a human read (the `voicer` crew agent).

## what it scans

- `.py` -> string literals only (never code identifiers)
- `.md` `.html` `.txt` `.json` `.js` `.ts` `.jsx` `.tsx` `.css` `.yml` -> full text

Skips `.git`, `node_modules`, `venv`, `__pycache__`, `.sandbox`, build dirs.
Never lints `voice.md` itself or this script.

## exit

`0` clean, `1` if anything tripped — so it drops straight into a channel's
`## checks` and a ship rests on it honestly.
