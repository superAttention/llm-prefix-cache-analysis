from __future__ import annotations

import argparse
from pathlib import Path
import pickle
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mechanism import analyze_against_belady, select_peak_gap_cache_size


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build mechanism-analysis records against TC-Belady.")
    parser.add_argument("--results", default="cache/results.pkl", help="Simulation results pickle.")
    parser.add_argument("--trace", help="Trace pickle. Optional if bundled into the results payload.")
    parser.add_argument("--output", default="cache/mechanism.pkl", help="Output pickle path.")
    parser.add_argument("--baseline", default="lru", help="Baseline strategy used to choose the peak-gap cache size.")
    parser.add_argument("--cache-size", type=int, help="Override the chosen cache size.")
    parser.add_argument(
        "--strategies",
        nargs="+",
        help="Strategies to analyze against TC-Belady. Defaults to all tree-based online strategies in the results.",
    )
    parser.add_argument("--page-size", type=int, default=1, help="Number of tokens per cached block.")
    parser.add_argument("--near-window-multiplier", type=int, default=10)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--progress-interval",
        type=float,
        default=5.0,
        help="Seconds between mechanism progress updates during each strategy analysis.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results_payload = _load_pickle(Path(args.results))
    results, bundled_trace = _unpack_results_payload(results_payload)
    trace = bundled_trace

    if args.trace:
        trace = _load_pickle(Path(args.trace))
    if trace is None:
        raise ValueError("Mechanism analysis requires a trace. Pass --trace or bundle it with the results payload.")

    cache_size = args.cache_size or select_peak_gap_cache_size(results, baseline_name=args.baseline)
    strategies = args.strategies or [name for name in results if name != "tc_belady"]

    mechanism = {}
    for strategy_index, strategy_name in enumerate(strategies, start=1):
        if not args.quiet:
            print(
                f"[mechanism] {strategy_name} cache_size={cache_size} ({strategy_index}/{len(strategies)})",
                file=sys.stderr,
                flush=True,
            )

        def report_progress(completed: int, total: int, records: int, name: str = strategy_name) -> None:
            print(
                f"[mechanism] {name} cache_size={cache_size}: {completed}/{total} accesses, {records} records",
                file=sys.stderr,
                flush=True,
            )

        mechanism[strategy_name] = analyze_against_belady(
            trace=trace,
            cache_size=cache_size,
            strategy_name=strategy_name,
            near_window_multiplier=args.near_window_multiplier,
            seed=args.seed,
            page_size=args.page_size,
            progress_callback=None if args.quiet else report_progress,
            progress_interval_seconds=args.progress_interval,
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        pickle.dump(mechanism, handle)


def _load_pickle(path: Path):
    with path.open("rb") as handle:
        return pickle.load(handle)


def _unpack_results_payload(payload):
    if isinstance(payload, dict) and "results" in payload:
        return payload["results"], payload.get("trace")
    return payload, None


if __name__ == "__main__":
    main()
