from __future__ import annotations

from pathlib import Path


def test_report_site_contains_required_technical_sections_and_facts():
    page = Path("report_site.html")

    assert page.exists(), "report_site.html should exist at the repo root"

    content = page.read_text()

    required_fragments = [
        "Prefix Cache Eviction Gap",
        'id="abstract"',
        'id="trace-construction"',
        'id="cache-model"',
        'id="policies"',
        'id="offline-oracle"',
        'id="mechanism-analysis"',
        'id="heuristic-motivation"',
        'id="results"',
        'id="fidelity"',
        "<svg",
        "300 conversations",
        "978 accesses",
        "811,050",
        "319,862",
        "80.2%",
        "79.3%",
        "last_access_index - alpha * depth",
        "priority reduces to plain lru",
        "|A| == |B| == number of disagreement events",
    ]

    for fragment in required_fragments:
        assert fragment in content
