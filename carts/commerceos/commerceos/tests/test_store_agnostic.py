"""M2's grep-guard (spec/parts/multi-store.md ## checks): the name of
store #1 has no business in mechanism code — comments and strings
included, *.py only so stale .pyc binaries stay out of the verdict."""

from pathlib import Path

MECHANISM = Path(__file__).resolve().parents[1] / "commerceos"


def test_no_store_name_in_mechanism_code():
    hits = [
        f"{path.relative_to(MECHANISM.parent)}:{n}: {line.strip()}"
        for path in sorted(MECHANISM.rglob("*.py"))
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if "demostore" in line.lower()
    ]
    assert not hits, "store #1's name leaked into mechanism code:\n" + "\n".join(hits)
