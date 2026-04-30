from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable

from src.belady import TreeConstrainedBelady
from src.eviction import FIFO, FILO, LFU, LRU, MRU, Priority, Random, SLRU
from src.lru_naive import NaiveLRU
from src.metrics import request_hit_rate, token_hit_rate
from src.radix_tree import RadixTree


@dataclass(slots=True)
class SimulationPoint:
    cache_size: int
    token_hit_rate: float
    request_hit_rate: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "cache_size": self.cache_size,
            "token_hit_rate": self.token_hit_rate,
            "request_hit_rate": self.request_hit_rate,
        }


StrategyFactory = Callable[[int], object]


def build_strategy_registry(seed: int = 0) -> dict[str, StrategyFactory]:
    return {
        "lru": lambda budget: RadixTree(token_budget=budget, eviction_strategy=LRU()),
        "lfu": lambda budget: RadixTree(token_budget=budget, eviction_strategy=LFU()),
        "fifo": lambda budget: RadixTree(token_budget=budget, eviction_strategy=FIFO()),
        "mru": lambda budget: RadixTree(token_budget=budget, eviction_strategy=MRU()),
        "filo": lambda budget: RadixTree(token_budget=budget, eviction_strategy=FILO()),
        "slru": lambda budget: RadixTree(token_budget=budget, eviction_strategy=SLRU()),
        "priority": lambda budget: RadixTree(token_budget=budget, eviction_strategy=Priority()),
        "random": lambda budget: RadixTree(token_budget=budget, eviction_strategy=Random(seed=seed)),
        "naive_lru": lambda budget: NaiveLRU(token_budget=budget),
        "tc_belady": lambda budget: TreeConstrainedBelady(token_budget=budget),
    }


def run_suite(
    trace: list[list[int]],
    cache_sizes: list[int],
    strategy_names: list[str] | None = None,
    seed: int = 0,
) -> dict[str, list[dict[str, float | int]]]:
    registry = build_strategy_registry(seed=seed)
    selected_names = strategy_names or list(registry)

    results: dict[str, list[dict[str, float | int]]] = {}
    for strategy_name in selected_names:
        factory = registry[strategy_name]
        points: list[dict[str, float | int]] = []

        for cache_size in cache_sizes:
            hit_tokens = run_strategy(trace, factory(cache_size))
            point = SimulationPoint(
                cache_size=cache_size,
                token_hit_rate=token_hit_rate(trace, hit_tokens),
                request_hit_rate=request_hit_rate(trace, hit_tokens),
            )
            points.append(point.as_dict())

        results[strategy_name] = points

    return results


def run_strategy(trace: list[list[int]], simulator: object) -> list[int]:
    if isinstance(simulator, TreeConstrainedBelady):
        return simulator.simulate(trace).hit_tokens

    hit_tokens: list[int] = []
    for access_index, tokens in enumerate(trace):
        result = simulator.access(tokens, access_index=access_index)
        hit_tokens.append(result.hit_tokens)
    return hit_tokens


def derive_cache_sizes(
    trace: list[list[int]],
    n_sizes: int = 8,
    min_fraction: float = 0.001,
    max_fraction: float = 1.0,
) -> list[int]:
    unique_prefixes = {tuple(access[:index]) for access in trace for index in range(1, len(access) + 1)}
    total_unique_tokens = max(1, len(unique_prefixes))
    min_size = max(1, math.floor(total_unique_tokens * min_fraction))
    max_size = max(min_size, math.ceil(total_unique_tokens * max_fraction))

    if n_sizes <= 1 or min_size == max_size:
        return [max_size]

    raw_sizes = [
        round(math.exp(math.log(min_size) + step * (math.log(max_size) - math.log(min_size)) / (n_sizes - 1)))
        for step in range(n_sizes)
    ]
    return sorted(set(max(1, size) for size in raw_sizes))
