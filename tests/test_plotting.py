from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.plotting import plot_gap_curve, plot_mechanism_scatter


def test_plot_gap_curve_writes_pdf(tmp_path: Path):
    results = {
        "tc_belady": [
            {"cache_size": 2, "token_hit_rate": 0.4, "request_hit_rate": 0.0},
            {"cache_size": 4, "token_hit_rate": 0.8, "request_hit_rate": 0.5},
        ],
        "lru": [
            {"cache_size": 2, "token_hit_rate": 0.2, "request_hit_rate": 0.0},
            {"cache_size": 4, "token_hit_rate": 0.6, "request_hit_rate": 0.0},
        ],
        "random": [
            {"cache_size": 2, "token_hit_rate": 0.1, "request_hit_rate": 0.0},
            {"cache_size": 4, "token_hit_rate": 0.3, "request_hit_rate": 0.0},
        ],
    }

    output_path = tmp_path / "gap_curve.pdf"
    plot_gap_curve(results, output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_plot_mechanism_scatter_writes_pdf(tmp_path: Path):
    frame = pd.DataFrame.from_records(
        [
            {"group": "A", "time_since_last_access": 8, "time_to_next_access": 2},
            {"group": "C", "time_since_last_access": 7, "time_to_next_access": 9},
        ]
    )

    output_path = tmp_path / "mechanism_scatter.pdf"
    plot_mechanism_scatter({"lru": frame}, output_path, strategy_name="lru")

    assert output_path.exists()
    assert output_path.stat().st_size > 0
