from __future__ import annotations

from pathlib import Path
import pickle
import subprocess
import sys


def test_mechanism_script_writes_pickle(tmp_path: Path):
    results_path = tmp_path / "results.pkl"
    output_path = tmp_path / "mechanism.pkl"
    results = {
        "tc_belady": [
            {"cache_size": 2, "token_hit_rate": 0.5, "request_hit_rate": 0.0},
            {"cache_size": 4, "token_hit_rate": 0.8, "request_hit_rate": 0.5},
        ],
        "lru": [
            {"cache_size": 2, "token_hit_rate": 0.2, "request_hit_rate": 0.0},
            {"cache_size": 4, "token_hit_rate": 0.7, "request_hit_rate": 0.0},
        ],
    }
    trace = [[1], [2], [3], [1], [2]]

    with results_path.open("wb") as handle:
        pickle.dump({"results": results, "trace": trace}, handle)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/03_mechanism.py",
            "--results",
            str(results_path),
            "--output",
            str(output_path),
            "--strategies",
            "lru",
            "--progress-interval",
            "0",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "[mechanism] peak_gap baseline=lru cache_size=2" in completed.stderr
    assert "[mechanism] lru cache_size=2 (1/1)" in completed.stderr
    assert "[mechanism] lru cache_size=2: 5/5 accesses" in completed.stderr
    assert "[mechanism] lru cache_size=2: building DataFrame" in completed.stderr
    assert "[mechanism] result lru rows=" in completed.stderr
    assert "groups=" in completed.stderr
    assert "[mechanism] writing" in completed.stderr
    assert (tmp_path / "mechanism-summary.csv").exists()
    assert (tmp_path / "mechanism-summary.md").exists()
    assert "strategy,cache_size,rows,group_A,group_B,group_C,group_D" in (
        tmp_path / "mechanism-summary.csv"
    ).read_text()
    assert "| strategy | cache_size | rows | group_A | group_B | group_C | group_D |" in (
        tmp_path / "mechanism-summary.md"
    ).read_text()
    with output_path.open("rb") as handle:
        payload = pickle.load(handle)

    assert list(payload) == ["lru"]
