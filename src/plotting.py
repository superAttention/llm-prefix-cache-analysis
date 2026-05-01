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
        linestyle = "--" if strategy_name == "tc_belady" else ":"
        if strategy_name not in {"tc_belady", "random"}:
            linestyle = "-"
        ax_hits.plot(group["cache_size"], group["token_hit_rate"], label=strategy_name, linestyle=linestyle)

    belady = frame[frame["strategy_name"] == "tc_belady"].sort_values("cache_size")
    competitors = frame[~frame["strategy_name"].isin({"tc_belady", "random"})]
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
    ax_gap.set_xlabel("Cache Size (blocks)")
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
    summary = _mechanism_group_summary(frame)
    colors = {"A": "tab:red", "B": "tab:blue", "C": "0.5", "D": "0.75"}
    bar_colors = [colors.get(group, "0.4") for group in summary.index]

    fig, axes = plt.subplots(2, 2, figsize=(9, 6.8))
    fig.suptitle(f"Mechanism summary: {strategy_name}")

    summary["count"].plot.bar(ax=axes[0, 0], color=bar_colors)
    axes[0, 0].set_title("Candidate records")
    axes[0, 0].set_ylabel("count")
    axes[0, 0].grid(axis="y", alpha=0.25)

    summary["never_reuse_rate"].plot.bar(ax=axes[0, 1], color=bar_colors)
    axes[0, 1].set_title("Never reused")
    axes[0, 1].set_ylabel("share")
    axes[0, 1].set_ylim(0, 1)
    axes[0, 1].grid(axis="y", alpha=0.25)

    summary[["median_time_since_last_access", "median_time_to_next_access_finite"]].plot.bar(
        ax=axes[1, 0],
        color=["tab:orange", "tab:green"],
    )
    axes[1, 0].set_title("Recency vs finite future reuse")
    axes[1, 0].set_ylabel("accesses")
    axes[1, 0].legend(["median since last", "median to next"], fontsize=8)
    axes[1, 0].grid(axis="y", alpha=0.25)

    summary["median_tree_depth"].plot.bar(ax=axes[1, 1], color=bar_colors)
    axes[1, 1].set_title("Tree depth")
    axes[1, 1].set_ylabel("median depth")
    axes[1, 1].grid(axis="y", alpha=0.25)

    for ax in axes.ravel():
        ax.set_xlabel("group")
        ax.tick_params(axis="x", rotation=0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def _mechanism_group_summary(frame: pd.DataFrame) -> pd.DataFrame:
    summaries: list[dict[str, float | int | str]] = []
    for group_name in ["A", "B", "C", "D"]:
        subset = frame[frame["group"] == group_name]
        if subset.empty:
            continue

        finite_next = subset[subset["time_to_next_access"] != float("inf")]["time_to_next_access"]
        summaries.append(
            {
                "group": group_name,
                "count": len(subset),
                "never_reuse_rate": float((subset["time_to_next_access"] == float("inf")).mean()),
                "median_time_since_last_access": float(subset["time_since_last_access"].median()),
                "median_time_to_next_access_finite": float(finite_next.median()) if not finite_next.empty else 0.0,
                "median_tree_depth": float(subset["tree_depth"].median()),
            }
        )

    return pd.DataFrame.from_records(summaries).set_index("group")


def _results_frame(results: dict[str, list[dict[str, float | int]]]) -> pd.DataFrame:
    records: list[dict[str, float | int | str]] = []
    for strategy_name, points in results.items():
        for point in points:
            records.append({"strategy_name": strategy_name, **point})
    return pd.DataFrame.from_records(records)
