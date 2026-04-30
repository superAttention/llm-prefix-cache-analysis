from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from math import inf

import pandas as pd

from src.metrics import relative_gap
from src.simulate import build_strategy_registry
from src.radix_tree import RadixTree


@dataclass(slots=True)
class EvictionSnapshot:
    access_index: int
    eviction_round: int
    victim_prefix: tuple[int, ...]
    candidate_metrics: dict[tuple[int, ...], dict[str, object]]


def select_peak_gap_cache_size(
    results: dict[str, list[dict[str, float | int]]],
    baseline_name: str = "lru",
) -> int:
    optimal_points = {int(point["cache_size"]): float(point["token_hit_rate"]) for point in results["tc_belady"]}
    baseline_points = {int(point["cache_size"]): float(point["token_hit_rate"]) for point in results[baseline_name]}

    best_cache_size = -1
    best_gap = -1.0
    for cache_size, optimal_hit_rate in optimal_points.items():
        if cache_size not in baseline_points:
            continue
        gap = relative_gap(optimal_hit_rate=optimal_hit_rate, baseline_hit_rate=baseline_points[cache_size])
        if gap > best_gap:
            best_gap = gap
            best_cache_size = cache_size

    if best_cache_size < 0:
        raise ValueError(f"No overlapping cache sizes between tc_belady and {baseline_name}")
    return best_cache_size


def analyze_against_belady(
    trace: list[list[int]],
    cache_size: int,
    strategy_name: str = "lru",
    near_window_multiplier: int = 10,
    seed: int = 0,
) -> pd.DataFrame:
    strategy_snapshots = _simulate_eviction_snapshots(
        trace=trace,
        cache_size=cache_size,
        strategy_name=strategy_name,
        near_window_multiplier=near_window_multiplier,
        seed=seed,
    )
    belady_snapshots = _simulate_eviction_snapshots(
        trace=trace,
        cache_size=cache_size,
        strategy_name="tc_belady",
        near_window_multiplier=near_window_multiplier,
        seed=seed,
    )

    belady_by_key = {(snapshot.access_index, snapshot.eviction_round): snapshot for snapshot in belady_snapshots}
    records: list[dict[str, object]] = []

    for strategy_snapshot in strategy_snapshots:
        key = (strategy_snapshot.access_index, strategy_snapshot.eviction_round)
        belady_snapshot = belady_by_key.get(key)
        if belady_snapshot is None:
            continue

        shared_prefixes = (
            strategy_snapshot.candidate_metrics.keys() & belady_snapshot.candidate_metrics.keys()
        )
        for prefix in sorted(shared_prefixes):
            strategy_evicted = prefix == strategy_snapshot.victim_prefix
            belady_evicted = prefix == belady_snapshot.victim_prefix
            group = _label_group(strategy_evicted, belady_evicted)
            metrics = dict(strategy_snapshot.candidate_metrics[prefix])
            metrics.update(
                {
                    "group": group,
                    "prefix": prefix,
                    "access_index": strategy_snapshot.access_index,
                    "eviction_round": strategy_snapshot.eviction_round,
                    "strategy_name": strategy_name,
                }
            )
            records.append(metrics)

    return pd.DataFrame.from_records(records)


def _label_group(strategy_evicted: bool, belady_evicted: bool) -> str:
    if strategy_evicted and not belady_evicted:
        return "A"
    if belady_evicted and not strategy_evicted:
        return "B"
    if strategy_evicted and belady_evicted:
        return "C"
    return "D"


def _simulate_eviction_snapshots(
    trace: list[list[int]],
    cache_size: int,
    strategy_name: str,
    near_window_multiplier: int,
    seed: int,
) -> list[EvictionSnapshot]:
    registry = build_strategy_registry(seed=seed)
    if strategy_name == "naive_lru":
        raise ValueError("Mechanism analysis only supports tree-based strategies")

    if strategy_name == "tc_belady":
        simulator = RadixTree(token_budget=cache_size, eviction_strategy=None)
    else:
        simulator = registry[strategy_name](cache_size)
    access_history = _build_access_history(trace)
    snapshots: list[EvictionSnapshot] = []

    if strategy_name == "tc_belady":
        choose_victim = lambda leaves, access_index: max(
            leaves,
            key=lambda node: _time_to_next_access(node.prefix, access_history, access_index),
        )
    else:
        choose_victim = simulator.eviction_strategy.get_priority

    for access_index, tokens in enumerate(trace):
        result = simulator.lookup(tokens, access_index=access_index)
        simulator.insert_suffix(tokens, result.hit_tokens, access_index)

        eviction_round = 0
        while simulator.cached_token_count > simulator.token_budget:
            leaves = simulator.iter_leaves()
            candidate_metrics = _build_candidate_metrics(
                leaves=leaves,
                access_index=access_index,
                access_history=access_history,
                near_window_multiplier=near_window_multiplier,
            )

            if strategy_name == "tc_belady":
                victim = choose_victim(leaves, access_index)
            else:
                victim = min(leaves, key=choose_victim)

            snapshots.append(
                EvictionSnapshot(
                    access_index=access_index,
                    eviction_round=eviction_round,
                    victim_prefix=victim.prefix,
                    candidate_metrics=candidate_metrics,
                )
            )
            simulator.remove_leaf(victim)
            eviction_round += 1

    return snapshots


def _build_access_history(trace: list[list[int]]) -> dict[tuple[int, ...], list[int]]:
    history: dict[tuple[int, ...], list[int]] = {}
    for access_index, tokens in enumerate(trace):
        prefix: list[int] = []
        for token in tokens:
            prefix.append(token)
            history.setdefault(tuple(prefix), []).append(access_index)
    return history


def _build_candidate_metrics(
    leaves,
    access_index: int,
    access_history: dict[tuple[int, ...], list[int]],
    near_window_multiplier: int,
) -> dict[tuple[int, ...], dict[str, object]]:
    window = max(1, near_window_multiplier * len(leaves))
    lru_order = sorted(leaves, key=lambda node: node.last_access_index)
    lru_ranks = {node.prefix: index for index, node in enumerate(lru_order)}

    return {
        node.prefix: {
            "reuse_count_near": _reuse_count_near(node.prefix, access_history, access_index, window),
            "reuse_count_total": _reuse_count_total(node.prefix, access_history, access_index),
            "time_since_last_access": access_index - node.last_access_index,
            "time_to_next_access": _time_to_next_access(node.prefix, access_history, access_index),
            "tree_depth": len(node.prefix),
            "subtree_size": _subtree_leaf_count(node),
            "is_leaf": node.is_leaf,
            "token_length": node.token_length,
            "lru_rank_at_evict": _percentile_rank(lru_ranks[node.prefix], len(leaves)),
        }
        for node in leaves
    }


def _reuse_count_total(
    prefix: tuple[int, ...],
    access_history: dict[tuple[int, ...], list[int]],
    access_index: int,
) -> int:
    history = access_history.get(prefix, [])
    next_position = bisect_right(history, access_index)
    return len(history) - next_position


def _reuse_count_near(
    prefix: tuple[int, ...],
    access_history: dict[tuple[int, ...], list[int]],
    access_index: int,
    window: int,
) -> int:
    history = access_history.get(prefix, [])
    start = bisect_right(history, access_index)
    end = bisect_right(history, access_index + window)
    return end - start


def _time_to_next_access(
    prefix: tuple[int, ...],
    access_history: dict[tuple[int, ...], list[int]],
    access_index: int,
) -> float:
    history = access_history.get(prefix, [])
    next_position = bisect_right(history, access_index)
    if next_position >= len(history):
        return inf
    return float(history[next_position] - access_index)


def _subtree_leaf_count(node) -> int:
    if node.is_leaf:
        return 1
    return sum(_subtree_leaf_count(child) for child in node.children.values())


def _percentile_rank(rank: int, total: int) -> float:
    if total <= 1:
        return 0.0
    return rank / (total - 1)
