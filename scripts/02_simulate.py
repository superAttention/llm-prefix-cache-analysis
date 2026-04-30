from __future__ import annotations

import argparse
from pathlib import Path
import pickle
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.simulate import derive_cache_sizes, run_suite


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep cache sizes across eviction strategies.")
    parser.add_argument("--trace", default="cache/trace.pkl", help="Path to the serialized trace pickle.")
    parser.add_argument("--output", default="cache/results.pkl", help="Path to write simulation results.")
    parser.add_argument(
        "--strategies",
        nargs="+",
        help="Optional subset of strategies to run. Defaults to all registered strategies.",
    )
    parser.add_argument("--sizes", nargs="+", type=int, help="Explicit cache sizes to sweep.")
    parser.add_argument("--n-sizes", type=int, default=8, help="Number of derived logarithmic cache sizes.")
    parser.add_argument("--seed", type=int, default=0, help="Seed for randomized strategies.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trace_path = Path(args.trace)
    output_path = Path(args.output)

    with trace_path.open("rb") as handle:
        trace = pickle.load(handle)

    cache_sizes = args.sizes or derive_cache_sizes(trace, n_sizes=args.n_sizes)
    results = run_suite(
        trace=trace,
        cache_sizes=cache_sizes,
        strategy_names=args.strategies,
        seed=args.seed,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        pickle.dump(results, handle)


if __name__ == "__main__":
    main()
