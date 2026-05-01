from __future__ import annotations

import argparse
import csv
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
    parser.add_argument("--page-size", type=int, default=1, help="Number of tokens per cached block.")
    parser.add_argument("--seed", type=int, default=0, help="Seed for randomized strategies.")
    parser.add_argument(
        "--progress-interval",
        type=float,
        default=5.0,
        help="Seconds between per-request progress updates during each simulation point.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trace_path = Path(args.trace)
    output_path = Path(args.output)

    with trace_path.open("rb") as handle:
        trace = pickle.load(handle)

    cache_sizes = args.sizes or derive_cache_sizes(trace, n_sizes=args.n_sizes, page_size=args.page_size)

    def report_progress(strategy_name: str, cache_size: int, point_index: int, point_count: int) -> None:
        print(
            f"[simulate] {strategy_name} cache_size={cache_size} ({point_index}/{point_count})",
            file=sys.stderr,
            flush=True,
        )

    def report_request_progress(strategy_name: str, cache_size: int, completed: int, total: int) -> None:
        print(
            f"[simulate] {strategy_name} cache_size={cache_size}: {completed}/{total} accesses",
            file=sys.stderr,
            flush=True,
        )

    results = run_suite(
        trace=trace,
        cache_sizes=cache_sizes,
        strategy_names=args.strategies,
        seed=args.seed,
        page_size=args.page_size,
        progress_callback=None if args.quiet else report_progress,
        request_progress_callback=None if args.quiet else report_request_progress,
        progress_interval_seconds=args.progress_interval,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        pickle.dump(results, handle)
    csv_path, markdown_path = _write_readable_results(results, output_path)
    if not args.quiet:
        _print_results_summary(results, output_path)
        print(f"[simulate] wrote {csv_path}", file=sys.stderr, flush=True)
        print(f"[simulate] wrote {markdown_path}", file=sys.stderr, flush=True)


def _print_results_summary(results: dict[str, list[dict[str, float | int]]], output_path: Path) -> None:
    print("[simulate] results summary", file=sys.stderr, flush=True)
    for strategy_name, points in results.items():
        for point in points:
            print(
                "[simulate] result "
                f"{strategy_name} "
                f"cache_size={int(point['cache_size'])} "
                f"token_hit_rate={float(point['token_hit_rate']):.4f} "
                f"request_hit_rate={float(point['request_hit_rate']):.4f}",
                file=sys.stderr,
                flush=True,
            )
    print(f"[simulate] wrote {output_path}", file=sys.stderr, flush=True)


def _write_readable_results(
    results: dict[str, list[dict[str, float | int]]],
    output_path: Path,
) -> tuple[Path, Path]:
    csv_path = output_path.with_suffix(".csv")
    markdown_path = output_path.with_suffix(".md")
    rows = [
        {
            "strategy": strategy_name,
            "cache_size": int(point["cache_size"]),
            "token_hit_rate": float(point["token_hit_rate"]),
            "request_hit_rate": float(point["request_hit_rate"]),
        }
        for strategy_name, points in results.items()
        for point in points
    ]

    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["strategy", "cache_size", "token_hit_rate", "request_hit_rate"],
        )
        writer.writeheader()
        writer.writerows(rows)

    with markdown_path.open("w") as handle:
        handle.write("# Simulation Results\n\n")
        handle.write("| strategy | cache_size | token_hit_rate | request_hit_rate |\n")
        handle.write("| --- | ---: | ---: | ---: |\n")
        for row in rows:
            handle.write(
                f"| {row['strategy']} | {row['cache_size']} | "
                f"{row['token_hit_rate']:.6f} | {row['request_hit_rate']:.6f} |\n"
            )

    return csv_path, markdown_path


if __name__ == "__main__":
    main()
