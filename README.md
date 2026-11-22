# Sandbox OS, the eleventh

A workshop on your own machine for projects, ideas and experiments, worked with an AI partner inside the terminal you already use (Claude Code, Codex). It keeps a dated record of what you make, in plain files you can read with any tool, and a page each morning of what needs your answer. It belongs to Winktank, the lab that made it; this is its tool, and the lab's own site is a different place. **Nobody's tool.** Nobody rents it to you: Winktank owns it and you may use it.

> Sandbox OS belongs to Winktank. If you're a person, you may use it.

**Three things to know before anything else.**

1. **Is there a release, and what are the two lines?** Yes: 11.0.0a14, an early alpha, on the releases page. Two lines install it on macOS (others not yet):

       curl -LsSf https://astral.sh/uv/install.sh | sh        # or: brew install uv
       uv tool install https://github.com/Sandbox-cmd/SandboxOS/releases/download/11.0.0a14/sandbox_os-11.0.0a14-py3-none-any.whl

   It needs Claude Code or Codex already installed; uv brings Python 3.14 itself. Then, in a new terminal, type `sandbox`: its welcome makes your workshop. Before that first `sandbox`, check the copy (`brew install minisign`) inside the installed tree (`$(uv tool dir)/sandbox-os/lib/python3.14/site-packages/sandbox_os`):

       minisign -V -H -P RWTJW4ev2fQxFoS8ADhw9vSIKyHzTPh9RXtKzsCJXuDO5Xwgjzn+Zqwz -m MANIFEST
       shasum -a 256 -c MANIFEST

   Key id 1631F4D9AF875BC9: the maker's own key.
2. **If my host does not prompt, what stops one of the five acts?** Nothing of this tool does. The five acts that always ask (anything that leaves this machine, moves money, destroys what the partner did not make, deploys or pushes, changes a live safety or legal claim) are asked by your host in its own prompt. The tool records afterwards which host asked and what ran, and where a host could not see an act, the morning page says so: not seen. On a host that never prompts, the partner is told to say so before the act and to ask with a card, and the page still says not seen.
3. **Can I use it for paid work in my own one-person company?** Not under these terms. Any natural person may use it for anything they do with their own hands, including work a client pays for, when they trade on their own account. A company of any size, a one-person company included, is an organisation and gets no licence under these terms; it can write and ask for one.

To leave: `sandbox remove` keeps your workshop and takes away the tool's own folder; then `uv tool uninstall sandbox-os`.

## What opens today

The record, the pages, the partner's instructions in Claude Code and Codex, and the packed release, unpacked here. The tests are not in this repository yet: they still hold the maker's notes. What the suite counted at the pack is inside (`suite-summary.json`, `release-checks.txt`); its full printout stays with the maker.

## What leaves the machine

Nothing of the tool's: no telemetry, no account, no server of ours, no font or script fetched by a page. What does leave is the host's own traffic: the conversation you have with the partner goes to the host's vendor on the host's terms, and that is your plan and your call. A copy of your record leaves only when you push it, by your own hand, to a remote you own.

## The licence, in plain words

> Sandbox OS belongs to Winktank. If you're a person, you may use it.
> Use it for anything you make with your own hands: your own projects, things you sell, work a client pays you for.
> Change it, copy it, and share it with other people, as long as these terms go with it.
> What you make with it is yours. Winktank claims nothing in it.
> Companies, charities, schools and governments don't get it under these terms, and neither do you when you're doing your employer's work. They can write and ask.
> If you break the terms, you have 32 days after being told to put things right.
> It comes as it is, with no promises, and as far as the law allows, nobody owes you for what goes wrong.
> This is the short version. The licence itself is what counts.

The licence is the Winktank Person Licence 1.0 (`LicenseRef-Winktank-Person-1.0`), in `LICENSE` at the root of this tree. A lawyer's read of it is owed and has not happened: not yet. An organisation that wants its own terms writes to hi@winktank.org.

## What this tree is made of

Six parts, each with one job in one sentence in `BUDGETS.md`: the store, the partner's instructions, the pages, the host adapters, the command, the tests. They depend on each other in one direction and never in a cycle. Plain Python on the standard library, nothing else.
