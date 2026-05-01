from __future__ import annotations

from pathlib import Path
import pickle
import subprocess
import sys


def test_simulate_script_writes_results_pickle(tmp_path: Path):
    trace_path = tmp_path / "trace.pkl"
    output_path = tmp_path / "results.pkl"
    with trace_path.open("wb") as handle:
        pickle.dump([[1, 2, 3], [1, 2, 4], [1, 2, 3]], handle)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/02_simulate.py",
            "--trace",
            str(trace_path),
            "--output",
            str(output_path),
            "--strategies",
            "lru",
            "tc_belady",
            "--sizes",
            "2",
            "3",
            "--page-size",
            "2",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "[simulate] result lru cache_size=2" in completed.stderr
    assert "token_hit_rate=" in completed.stderr
    assert "[simulate] wrote" in completed.stderr
    assert (tmp_path / "results.csv").exists()
    assert (tmp_path / "results.md").exists()
    assert "strategy,cache_size,token_hit_rate,request_hit_rate" in (tmp_path / "results.csv").read_text()
    assert "| strategy | cache_size | token_hit_rate | request_hit_rate |" in (tmp_path / "results.md").read_text()
    with output_path.open("rb") as handle:
        results = pickle.load(handle)

    assert sorted(results) == ["lru", "tc_belady"]
