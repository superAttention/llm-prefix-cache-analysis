from __future__ import annotations

from bisect import bisect_right
from math import inf

import pandas as pd

from src.metrics import relative_gap
from src.paging import iter_block_prefixes
from src.simulate import build_strategy_registry
from src.radix_tree import RadixTree



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
    page_size: int = 1,
) -> pd.DataFrame:
    """Shadow-oracle approach: run one strategy simulation; at each eviction
    ask what TC-Belady would have chosen from the identical candidate pool.

    This avoids the tree-divergence problem of running two separate simulations.
    On disagreement events, the shared candidate pool produces exactly one Group
    A node (strategy evicted, Belady would not) and one Group B node (Belady
    would evict, strategy did not), both drawn from the same tree state at the
    same moment.
    """
    registry = build_strategy_registry(seed=seed, page_size=page_size)
    simulator = registry[strategy_name](cache_size)
    access_history = _build_access_history(trace, page_size=page_size)
    records: list[dict[str, object]] = []

    for access_index, tokens in enumerate(trace):
        result = simulator.lookup(tokens, access_index=access_index)
        simulator.insert_suffix(tokens, result.hit_blocks, access_index)

        eviction_round = 0
        while simulator.cached_block_count > simulator.block_budget:
            leaves = simulator.iter_leaves()
            candidate_metrics = _build_candidate_metrics(
                leaves=leaves,
                access_index=access_index,
                access_history=access_history,
                near_window_multiplier=near_window_multiplier,
            )

            strategy_victim = min(leaves, key=simulator.eviction_strategy.get_priority)
            belady_victim = max(
                leaves,
                key=lambda node: _time_to_next_access(node.prefix, access_history, access_index),
            )

            for node in leaves:
                strategy_evicted = node.prefix == strategy_victim.prefix
                belady_evicted = node.prefix == belady_victim.prefix
                group = _label_group(strategy_evicted, belady_evicted)
                metrics = dict(candidate_metrics[node.prefix])
                metrics.update(
                    {
                        "group": group,
                        "prefix": node.prefix,
                        "access_index": access_index,
                        "eviction_round": eviction_round,
                        "strategy_name": strategy_name,
                    }
                )
                records.append(metrics)

            simulator.remove_leaf(strategy_victim)
            eviction_round += 1

    return pd.DataFrame.from_records(records)


def _label_group(strategy_evicted: bool, belady_evicted: bool) -> str:
    if strategy_evicted and not belady_evicted:
        return "A"
    if belady_evicted and not strategy_evicted:
        return "B"
    if strategy_evicted and belady_evicted:
        return "C"
    return "D"


def _build_access_history(trace: list[list[int]], page_size: int) -> dict[tuple[int, ...], list[int]]:
    history: dict[tuple[int, ...], list[int]] = {}
    for access_index, tokens in enumerate(trace):
        for prefix in iter_block_prefixes(tokens, page_size):
            history.setdefault(prefix, []).append(access_index)
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
            "tree_depth": node.depth,
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
