from __future__ import annotations

import argparse
from pathlib import Path
import pickle
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the paper figures from simulation outputs.")
    parser.add_argument("--results", default="cache/results.pkl")
    parser.add_argument("--mechanism", default="cache/mechanism.pkl")
    parser.add_argument("--figures-dir", default="paper/figures")
    parser.add_argument("--strategy", default="lru", help="Mechanism-analysis strategy to visualize.")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    figures_dir = Path(args.figures_dir)

    def report(message: str) -> None:
        if not args.quiet:
            print(f"[plot] {message}", file=sys.stderr, flush=True)

    report("importing plotting stack")
    from src.plotting import plot_gap_curve, plot_mechanism_scatter
    report("imported plotting stack")

    results_path = Path(args.results)
    mechanism_path = Path(args.mechanism)
    gap_path = figures_dir / "gap_curve.pdf"
    scatter_path = figures_dir / "mechanism_scatter.pdf"

    report(f"loading results {results_path}")
    results = _load_pickle(results_path)
    report(f"loaded results with {len(results)} strategies")

    report(f"loading mechanism {mechanism_path}")
    mechanism = _load_pickle(mechanism_path)
    report(f"loaded mechanism with {len(mechanism)} strategies")

    report(f"writing gap curve {gap_path}")
    plot_gap_curve(results, gap_path)
    report(f"wrote gap curve {gap_path}")

    frame = mechanism.get(args.strategy)
    row_count = "unknown" if frame is None else len(frame)
    report(f"writing mechanism scatter {scatter_path} for {args.strategy} ({row_count} rows)")
    plot_mechanism_scatter(mechanism, scatter_path, strategy_name=args.strategy)
    report(f"wrote mechanism scatter {scatter_path}")


def _load_pickle(path: Path):
    with path.open("rb") as handle:
        return pickle.load(handle)


if __name__ == "__main__":
    main()
