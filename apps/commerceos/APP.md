# commerceos
version: 1.0.0
min-core: 8.1.0
description: a commerce operating system — mechanism, specs, packs, and its own 551-check suite; bring your own store data

## placements
apps/commerceos/

## checks
cd apps/commerceos/commerceos && uv sync -q && uv run pytest -q
