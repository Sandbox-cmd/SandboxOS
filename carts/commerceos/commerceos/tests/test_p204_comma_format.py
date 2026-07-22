"""p204 comma drift: the overview's gtin front row rendered its counts
uncommaed beside p209's commaed ones — the generic branch of
progress_detail (used by gtin, classification, delist) skipped the comma
treatment its neighbors (seo, verification) already had. every count >= 1,000
on this surface now gets the same thousands separator."""

from commerceos.web.app import progress_detail


def test_gtin_front_counts_carry_the_comma_like_their_neighbors():
    # the exact repro shape: valid + total both over 1,000.
    line = progress_detail("gtin", {
        "valid": 4206, "total": 5140, "fixable_remaining": 3, "rate": 0.8183,
    })
    assert line == "4,206 valid · 5,140 total · 3 left to fix"
    assert "4206" not in line
    assert "5140" not in line


def test_classification_front_counts_also_get_the_comma():
    line = progress_detail("classification", {
        "resolved": 1234, "total": 5678, "queue_remaining": 12, "rate": 0.217,
    })
    assert "1,234 in a category" in line
    assert "5,678 total" in line
