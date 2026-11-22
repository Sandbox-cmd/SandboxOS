# Where each face came from

Written by builder C (claude-opus-5-5), stage 6's second half, on 2026-11-02 at 15:24, on the maker's yes to card 6 (the one
download the build was allowed). You are reading this because the pages now carry their three faces in the tree instead of the
system's own: each file below was fetched once from its maker's public address on GitHub, and this table says where from, how many
bytes it is and its sha256, so anyone can fetch it again and compare. `tests/pages/test_fonts.py` reads this table against the files.

What I fetched, and what I did not:

- **IBM Plex Mono**: the release `@ibm/plex-mono@2.5.0` of `IBM/plex` (published 2026-06-11), its archive `ibm-plex-mono.zip`
  (6,940,652 bytes, sha256 `6d23f01257663d8cc49a0d64c22ced630b79e0e2a0ac08a0da86e9a38bbc481c`, the same digest GitHub publishes for
  that asset). The three weights from `fonts/complete/woff2/`; the family's licence is the archive's `LICENSE.txt`.
- **IBM Plex Sans Arabic**: the release `@ibm/plex-sans-arabic@1.1.0` of `IBM/plex` (published 2024-11-13, the newest for this family),
  its archive `ibm-plex-sans-arabic.zip` (3,898,251 bytes, sha256 `f03915581aea37d82792c188b08064023a73494d679b8e19f85f5971db714013`;
  GitHub publishes no digest for it). The four weights from `fonts/complete/woff2/`; the licence is the archive's `LICENSE.txt`.
- **Bricolage Grotesque**: its maker's repository `ateliertriay/bricolage` has no release and no tag, so the two files came from the
  repository itself, pinned to its newest commit, `84745e5b96261ae5f8c6c856e262fe78d1d6efdd` (2023-07-19, "All fonts exported"): the
  variable font as the maker exports it for the web, `fonts/webfonts/BricolageGrotesque[opsz,wdth,wght].woff2`, and `OFL.txt`. Each
  file's git blob id matched the one the repository lists for it.

Each file is renamed by family and weight, the names the pages declare (`sandbox_os/pages/frame.py`, `faces`); the two Plex licence
files hold the same text. The archives themselves are not kept in the tree.

| file | fetched from | bytes | sha256 | inside the archive, or the repository path |
|---|---|---|---|---|
| `BricolageGrotesque-Variable.woff2` | https://github.com/ateliertriay/bricolage/raw/84745e5b96261ae5f8c6c856e262fe78d1d6efdd/fonts/webfonts/BricolageGrotesque%5Bopsz,wdth,wght%5D.woff2 | 204,636 | `b51a8ebd169637e47cb7db430431ab3e122d2f09b03ee2a03ea06f4cb46f1a8e` | `fonts/webfonts/BricolageGrotesque[opsz,wdth,wght].woff2` |
| `BricolageGrotesque-OFL.txt` | https://github.com/ateliertriay/bricolage/raw/84745e5b96261ae5f8c6c856e262fe78d1d6efdd/OFL.txt | 4,403 | `4b5a7d8f37f5602621c8a8d7358a6a2e71317e6c231c661e15aef0275d3e07ba` | `OFL.txt` |
| `IBMPlexMono-Regular.woff2` | https://github.com/IBM/plex/releases/download/%40ibm/plex-mono%402.5.0/ibm-plex-mono.zip | 49,248 | `ba204497f16b6d334cee9d1e963a831b73e3a56e1d6300a8489d18df7214b350` | `ibm-plex-mono/fonts/complete/woff2/IBMPlexMono-Regular.woff2` |
| `IBMPlexMono-Medium.woff2` | https://github.com/IBM/plex/releases/download/%40ibm/plex-mono%402.5.0/ibm-plex-mono.zip | 50,400 | `33faf307fa6031fb4062276d7320a6d632de890cbb347576fd80cfa01077bc25` | `ibm-plex-mono/fonts/complete/woff2/IBMPlexMono-Medium.woff2` |
| `IBMPlexMono-SemiBold.woff2` | https://github.com/IBM/plex/releases/download/%40ibm/plex-mono%402.5.0/ibm-plex-mono.zip | 50,600 | `6a825b4824c01cbb401e829e5a066a1818411bcb3538b5a5792c5ca9b82343c3` | `ibm-plex-mono/fonts/complete/woff2/IBMPlexMono-SemiBold.woff2` |
| `IBMPlexMono-OFL.txt` | https://github.com/IBM/plex/releases/download/%40ibm/plex-mono%402.5.0/ibm-plex-mono.zip | 4,456 | `7e6b2818edbd8f6a01ae80641cc8f16a51080d08fb4e532be3a0b6f74adb07da` | `ibm-plex-mono/LICENSE.txt` |
| `IBMPlexSansArabic-Regular.woff2` | https://github.com/IBM/plex/releases/download/%40ibm/plex-sans-arabic%401.1.0/ibm-plex-sans-arabic.zip | 71,904 | `74112e1b7bf2e2c547989a4e947a60cba6cd1f9156e0065670134636e717199d` | `ibm-plex-sans-arabic/fonts/complete/woff2/IBMPlexSansArabic-Regular.woff2` |
| `IBMPlexSansArabic-Medium.woff2` | https://github.com/IBM/plex/releases/download/%40ibm/plex-sans-arabic%401.1.0/ibm-plex-sans-arabic.zip | 75,936 | `c72f6986f50ded745d06e71e508096209c52a55a6b3a81029954e33c52ba1dd2` | `ibm-plex-sans-arabic/fonts/complete/woff2/IBMPlexSansArabic-Medium.woff2` |
| `IBMPlexSansArabic-SemiBold.woff2` | https://github.com/IBM/plex/releases/download/%40ibm/plex-sans-arabic%401.1.0/ibm-plex-sans-arabic.zip | 76,408 | `869b2acd0a9660607a2025f0fe1c640110bf23d33417509328f07722922b8063` | `ibm-plex-sans-arabic/fonts/complete/woff2/IBMPlexSansArabic-SemiBold.woff2` |
| `IBMPlexSansArabic-Bold.woff2` | https://github.com/IBM/plex/releases/download/%40ibm/plex-sans-arabic%401.1.0/ibm-plex-sans-arabic.zip | 73,788 | `db6650a05969c144ab5ab9bb6c3beca6ca4dbb3537bb5f2311c878dd293875b4` | `ibm-plex-sans-arabic/fonts/complete/woff2/IBMPlexSansArabic-Bold.woff2` |
| `IBMPlexSansArabic-OFL.txt` | https://github.com/IBM/plex/releases/download/%40ibm/plex-sans-arabic%401.1.0/ibm-plex-sans-arabic.zip | 4,456 | `7e6b2818edbd8f6a01ae80641cc8f16a51080d08fb4e532be3a0b6f74adb07da` | `ibm-plex-sans-arabic/LICENSE.txt` |
