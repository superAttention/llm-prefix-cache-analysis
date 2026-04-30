from __future__ import annotations

from pathlib import Path
import pickle
import subprocess
import sys

import pandas as pd


def test_plot_script_writes_both_figures(tmp_path: Path):
    results_path = tmp_path / "results.pkl"
    mechanism_path = tmp_path / "mechanism.pkl"
    figures_dir = tmp_path / "figures"

    results = {
        "tc_belady": [
            {"cache_size": 2, "token_hit_rate": 0.4, "request_hit_rate": 0.0},
            {"cache_size": 4, "token_hit_rate": 0.8, "request_hit_rate": 0.5},
        ],
        "lru": [
            {"cache_size": 2, "token_hit_rate": 0.2, "request_hit_rate": 0.0},
            {"cache_size": 4, "token_hit_rate": 0.6, "request_hit_rate": 0.0},
        ],
    }
    mechanism = {
        "lru": pd.DataFrame.from_records(
            [
                {"group": "A", "time_since_last_access": 8, "time_to_next_access": 2},
                {"group": "C", "time_since_last_access": 7, "time_to_next_access": 9},
            ]
        )
    }

    with results_path.open("wb") as handle:
        pickle.dump(results, handle)
    with mechanism_path.open("wb") as handle:
        pickle.dump(mechanism, handle)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/04_plot.py",
            "--results",
            str(results_path),
            "--mechanism",
            str(mechanism_path),
            "--figures-dir",
            str(figures_dir),
            "--strategy",
            "lru",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert (figures_dir / "gap_curve.pdf").exists()
    assert (figures_dir / "mechanism_scatter.pdf").exists()
