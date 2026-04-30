from __future__ import annotations

import argparse
from pathlib import Path
import pickle
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.plotting import plot_gap_curve, plot_mechanism_scatter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the paper figures from simulation outputs.")
    parser.add_argument("--results", default="cache/results.pkl")
    parser.add_argument("--mechanism", default="cache/mechanism.pkl")
    parser.add_argument("--figures-dir", default="paper/figures")
    parser.add_argument("--strategy", default="lru", help="Mechanism-analysis strategy to visualize.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = _load_pickle(Path(args.results))
    mechanism = _load_pickle(Path(args.mechanism))
    figures_dir = Path(args.figures_dir)

    plot_gap_curve(results, figures_dir / "gap_curve.pdf")
    plot_mechanism_scatter(mechanism, figures_dir / "mechanism_scatter.pdf", strategy_name=args.strategy)


def _load_pickle(path: Path):
    with path.open("rb") as handle:
        return pickle.load(handle)


if __name__ == "__main__":
    main()
