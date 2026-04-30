from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from src.metrics import relative_gap


def plot_gap_curve(results: dict[str, list[dict[str, float | int]]], output_path: Path) -> None:
    frame = _results_frame(results)
    fig, (ax_hits, ax_gap) = plt.subplots(2, 1, figsize=(7.5, 8), sharex=True)

    for strategy_name, group in frame.groupby("strategy_name"):
        linestyle = "--" if strategy_name in {"tc_belady", "naive_lru"} else ":"
        if strategy_name not in {"tc_belady", "naive_lru", "random"}:
            linestyle = "-"
        ax_hits.plot(group["cache_size"], group["token_hit_rate"], label=strategy_name, linestyle=linestyle)

    belady = frame[frame["strategy_name"] == "tc_belady"].sort_values("cache_size")
    competitors = frame[~frame["strategy_name"].isin({"tc_belady", "naive_lru", "random"})]
    if not competitors.empty:
        best = (
            competitors.groupby("cache_size", as_index=False)["token_hit_rate"]
            .max()
            .rename(columns={"token_hit_rate": "best_token_hit_rate"})
        )
        shaded = belady.merge(best, on="cache_size", how="inner")
        ax_hits.fill_between(
            shaded["cache_size"],
            shaded["best_token_hit_rate"],
            shaded["token_hit_rate"],
            alpha=0.15,
            color="tab:blue",
        )

        gap_points = [
            relative_gap(optimal_hit_rate=row.token_hit_rate, baseline_hit_rate=row.best_token_hit_rate)
            for row in shaded.itertuples(index=False)
        ]
        ax_gap.plot(shaded["cache_size"], gap_points, color="tab:blue")

    ax_hits.set_xscale("log")
    ax_hits.set_ylim(0, 1)
    ax_hits.set_ylabel("Token Hit Rate")
    ax_hits.legend()
    ax_hits.grid(alpha=0.25)

    ax_gap.set_xscale("log")
    ax_gap.set_ylim(0, 1)
    ax_gap.set_xlabel("Cache Size (tokens)")
    ax_gap.set_ylabel("Relative Gap")
    ax_gap.grid(alpha=0.25)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_mechanism_scatter(
    mechanism: dict[str, pd.DataFrame],
    output_path: Path,
    strategy_name: str = "lru",
) -> None:
    frame = mechanism[strategy_name].copy()
    fig, ax = plt.subplots(figsize=(7, 5.5))

    for group_name, color in [("A", "tab:red"), ("B", "tab:blue"), ("C", "0.6")]:
        subset = frame[frame["group"] == group_name]
        if subset.empty:
            continue
        ax.scatter(
            subset["time_since_last_access"],
            subset["time_to_next_access"],
            label=group_name,
            color=color,
            alpha=0.75,
        )

    finite_values = frame[frame["time_to_next_access"] != float("inf")]["time_to_next_access"]
    diagonal_max = max(
        frame["time_since_last_access"].max() if not frame.empty else 1,
        finite_values.max() if not finite_values.empty else 1,
    )
    ax.plot([0, diagonal_max], [0, diagonal_max], linestyle="--", color="0.3", linewidth=1)

    ax.set_xlabel("Time Since Last Access")
    ax.set_ylabel("Time To Next Access")
    ax.legend()
    ax.grid(alpha=0.25)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def _results_frame(results: dict[str, list[dict[str, float | int]]]) -> pd.DataFrame:
    records: list[dict[str, float | int | str]] = []
    for strategy_name, points in results.items():
        for point in points:
            records.append({"strategy_name": strategy_name, **point})
    return pd.DataFrame.from_records(records)
