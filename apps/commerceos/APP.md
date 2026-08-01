# commerceos
version: 1.0.0
min-core: 8.1.0
description: a template for running your own store — mechanism, specs, execution packs, and 551 checks of its own; it ships with nobody's catalog, credentials, or numbers

## placements
apps/commerceos/

## checks
cd apps/commerceos/commerceos && uv sync -q && uv run pytest -q
