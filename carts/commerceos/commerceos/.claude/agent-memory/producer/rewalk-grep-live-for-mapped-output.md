---
name: rewalk-grep-live-for-mapped-output
description: re-walk method — grep the LIVE capture for the fix's output string; a test pinning a minted row passes while live data's dominant shape misses the map
metadata:
  type: feedback
---

When a fix claims a render-time mapping ("X now renders as Y"), grep the live capture for Y, not just for the absence of X's test shape.
**Why:** commerceos UI-truth sweep 2026-07-19 — the barcode intent map matched the per-row shape (`normalize barcode "..." -> N`, 100 ledger rows) and its test minted exactly that shape, so the suite was green; but the live ledger's dominant shape ("normalize barcodes that are one spreadsheet artifact from a valid GTIN", thousands of rows) missed the regex, and the mapped output appeared ZERO times in the real /record capture. Test-green, surface-false — the reskin class in miniature.
**How to apply:** every re-walk debt of the form "A now renders as B": (1) grep the fresh capture for B and count; (2) if the fix is a pattern match, sample the live data for all shapes the pattern must cover, not the shape the test minted. Related: [[cold-read-walk-to-terminal]].
