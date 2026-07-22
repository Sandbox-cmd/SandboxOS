# the list

two saved builds. each row is read from the build's own card — if a checksum
here disagrees with `CART.md`, the card wins and this list owes a fix.

| saved build | what it is | kept | checksum |
|---|---|---|---|
| [commerceos](carts/commerceos/) | the whole commerce build — the mechanism, the specs, the packs, 551 checks, the claude agents and skills. no store data. 503 passed / 48 skipped on a cold install; each skip names the file you owe. | 2026-07-22 | `5081ac25ba56677ab8b1a32e9900d83e1947723ee096523c4f4baa7dad6a1278` |
| [michael](carts/michael/) | michael, the woodshop — a claude terminal that designs 3d-printable parts and drives your live blender. his command file, the app, one example project (a mug), and his face for the icon. | 2026-07-22 | `4c05e3ca5c356566c735a0db6310c128f99110013305219ed4879d1a2a59e501` |

left out before sharing, on the cards themselves: commerceos ships without
the owner's stores, data, or brand file; michael ships without the owner's
api key or personal projects.
