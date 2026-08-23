# design-system
goal: the SandboxOS production design system — Bootleg OS soul, playful/loud as the foundation premise
sketch: the full v2 kit (205 files: components, ui_kits, templates, guidelines, explorations, tokens, lib, assets, CANON, SKILL) now lives here at system/ — the source of truth to evolve. brought over from the tombstoned SandboxOS2 canonical, with the newer substrate.js engine and a playful-register voice reconciliation (paranoid/fortress tone -> whimsical/rebellious; "nobody's tool" kept). owner-lock stands: loud is the premise, not a tier. license/pricing parked. next step: press the first saved build. full frame in inherited/context.md.
state: active

## checks
node --check system/_ds_bundle.js && node --check system/lib/substrate.js && python3 -m json.tool system/_ds_manifest.json >/dev/null && for f in system/CANON.md system/SKILL.md system/styles.css system/tokens/colors.css system/components/forms/Knob.jsx system/ui_kits/website/index.html; do test -s "$f" || { echo "MISSING $f"; exit 1; }; done && echo "kit intact"

## notes
- the full kit was reconciled in staging (playful register) then imported here on 2026-07-19, replacing the earlier thin site-slice. sandbox-site still consumes its own in-place copy; nothing there was touched.
- voice: paranoid/fortress framing rewritten to playful/whimsical/rebellious per owner ruling; "nobody's tool" kept as the signature catchphrase; GhostEye reframed from surveillance eye to a companion that watches your build; "sovereign" swept from brand prose (kept only as code option-values).
- next fork (owner's): press the first saved build (cart) off this channel; then re-point sandbox-site at the pressing so the two copies stop being able to drift.
- Phase 2 (in flight): the same playful reconciliation applied system-wide to the load-bearing voice files (soul/bootleg.md, voice.md, registers.md, voice.json...) across the SandboxOS bodies — staged as reviewable diffs for the owner.
