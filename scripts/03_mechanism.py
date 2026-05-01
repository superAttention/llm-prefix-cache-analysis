from __future__ import annotations

import argparse
import csv
from pathlib import Path
import pickle
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mechanism import analyze_against_belady, select_peak_gap_cache_size
from src.metrics import relative_gap


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
    if not args.quiet:
        _print_peak_gap_summary(results, args.baseline, cache_size, selected_by_gap=args.cache_size is None)
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

        def report_status(message: str, name: str = strategy_name) -> None:
            print(
                f"[mechanism] {name} cache_size={cache_size}: {message}",
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
            status_callback=None if args.quiet else report_status,
            progress_interval_seconds=args.progress_interval,
        )
        if not args.quiet:
            _print_strategy_summary(strategy_name, mechanism[strategy_name])

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not args.quiet:
        print(f"[mechanism] writing {output_path}", file=sys.stderr, flush=True)
    with output_path.open("wb") as handle:
        pickle.dump(mechanism, handle)
    csv_path, markdown_path = _write_readable_summary(
        mechanism=mechanism,
        output_path=output_path,
        cache_size=cache_size,
        baseline_name=args.baseline,
        results=results,
        selected_by_gap=args.cache_size is None,
    )
    if not args.quiet:
        print(f"[mechanism] wrote {output_path}", file=sys.stderr, flush=True)
        print(f"[mechanism] wrote {csv_path}", file=sys.stderr, flush=True)
        print(f"[mechanism] wrote {markdown_path}", file=sys.stderr, flush=True)


def _load_pickle(path: Path):
    with path.open("rb") as handle:
        return pickle.load(handle)


def _unpack_results_payload(payload):
    if isinstance(payload, dict) and "results" in payload:
        return payload["results"], payload.get("trace")
    return payload, None


def _print_peak_gap_summary(
    results: dict[str, list[dict[str, float | int]]],
    baseline_name: str,
    cache_size: int,
    selected_by_gap: bool,
) -> None:
    belady = _point_for_cache_size(results["tc_belady"], cache_size)
    baseline = _point_for_cache_size(results[baseline_name], cache_size)
    gap = relative_gap(
        optimal_hit_rate=float(belady["token_hit_rate"]),
        baseline_hit_rate=float(baseline["token_hit_rate"]),
    )
    label = "peak_gap" if selected_by_gap else "cache_size"
    print(
        f"[mechanism] {label} baseline={baseline_name} "
        f"cache_size={cache_size} "
        f"tc_belady={float(belady['token_hit_rate']):.4f} "
        f"{baseline_name}={float(baseline['token_hit_rate']):.4f} "
        f"relative_gap={gap:.4f}",
        file=sys.stderr,
        flush=True,
    )


def _point_for_cache_size(points: list[dict[str, float | int]], cache_size: int) -> dict[str, float | int]:
    for point in points:
        if int(point["cache_size"]) == cache_size:
            return point
    raise ValueError(f"cache_size={cache_size} is not present in results")


def _print_strategy_summary(strategy_name: str, frame) -> None:
    group_counts = frame["group"].value_counts().sort_index().to_dict() if "group" in frame else {}
    group_summary = ",".join(f"{group}:{count}" for group, count in group_counts.items()) or "none"
    print(
        f"[mechanism] result {strategy_name} rows={len(frame)} groups={group_summary}",
        file=sys.stderr,
        flush=True,
    )


def _write_readable_summary(
    mechanism,
    output_path: Path,
    cache_size: int,
    baseline_name: str,
    results: dict[str, list[dict[str, float | int]]],
    selected_by_gap: bool,
) -> tuple[Path, Path]:
    csv_path = output_path.with_name(f"{output_path.stem}-summary.csv")
    markdown_path = output_path.with_name(f"{output_path.stem}-summary.md")
    rows = [_strategy_summary_row(strategy_name, cache_size, frame) for strategy_name, frame in mechanism.items()]

    fieldnames = [
        "strategy",
        "cache_size",
        "rows",
        "group_A",
        "group_B",
        "group_C",
        "group_D",
    ]
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    belady = _point_for_cache_size(results["tc_belady"], cache_size)
    baseline = _point_for_cache_size(results[baseline_name], cache_size)
    gap = relative_gap(
        optimal_hit_rate=float(belady["token_hit_rate"]),
        baseline_hit_rate=float(baseline["token_hit_rate"]),
    )

    with markdown_path.open("w") as handle:
        handle.write("# Mechanism Summary\n\n")
        selector = "peak gap" if selected_by_gap else "explicit cache size"
        handle.write(f"- Selector: {selector}\n")
        handle.write(f"- Baseline: `{baseline_name}`\n")
        handle.write(f"- Cache size: `{cache_size}`\n")
        handle.write(f"- `tc_belady` token hit rate: `{float(belady['token_hit_rate']):.6f}`\n")
        handle.write(f"- `{baseline_name}` token hit rate: `{float(baseline['token_hit_rate']):.6f}`\n")
        handle.write(f"- Relative gap: `{gap:.6f}`\n\n")
        handle.write("| strategy | cache_size | rows | group_A | group_B | group_C | group_D |\n")
        handle.write("| --- | ---: | ---: | ---: | ---: | ---: | ---: |\n")
        for row in rows:
            handle.write(
                f"| {row['strategy']} | {row['cache_size']} | {row['rows']} | "
                f"{row['group_A']} | {row['group_B']} | {row['group_C']} | {row['group_D']} |\n"
            )

    return csv_path, markdown_path


def _strategy_summary_row(strategy_name: str, cache_size: int, frame) -> dict[str, int | str]:
    group_counts = frame["group"].value_counts().to_dict() if "group" in frame else {}
    return {
        "strategy": strategy_name,
        "cache_size": cache_size,
        "rows": len(frame),
        "group_A": int(group_counts.get("A", 0)),
        "group_B": int(group_counts.get("B", 0)),
        "group_C": int(group_counts.get("C", 0)),
        "group_D": int(group_counts.get("D", 0)),
    }


if __name__ == "__main__":
    main()
