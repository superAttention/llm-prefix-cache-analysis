from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Callable

from src.belady import TreeConstrainedBelady
from src.eviction import FIFO, FILO, LFU, LRU, MRU, Priority, Random, SLRU, DepthLRU
from src.metrics import request_hit_rate, token_hit_rate
from src.paging import iter_block_prefixes
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


def build_strategy_registry(seed: int = 0, page_size: int = 1) -> dict[str, StrategyFactory]:
    depth_alpha = 0.01 * page_size
    return {
        "lru": lambda budget: RadixTree(block_budget=budget, eviction_strategy=LRU(), page_size=page_size),
        "lfu": lambda budget: RadixTree(block_budget=budget, eviction_strategy=LFU(), page_size=page_size),
        "fifo": lambda budget: RadixTree(block_budget=budget, eviction_strategy=FIFO(), page_size=page_size),
        "mru": lambda budget: RadixTree(block_budget=budget, eviction_strategy=MRU(), page_size=page_size),
        "filo": lambda budget: RadixTree(block_budget=budget, eviction_strategy=FILO(), page_size=page_size),
        "slru": lambda budget: RadixTree(block_budget=budget, eviction_strategy=SLRU(), page_size=page_size),
        "priority": lambda budget: RadixTree(block_budget=budget, eviction_strategy=Priority(), page_size=page_size),
        "random": lambda budget: RadixTree(
            block_budget=budget,
            eviction_strategy=Random(seed=seed),
            page_size=page_size,
        ),
        "depth_lru": lambda budget: RadixTree(
            block_budget=budget,
            eviction_strategy=DepthLRU(alpha=depth_alpha),
            page_size=page_size,
        ),
        "tc_belady": lambda budget: TreeConstrainedBelady(block_budget=budget, page_size=page_size),
    }


def run_suite(
    trace: list[list[int]],
    cache_sizes: list[int],
    strategy_names: list[str] | None = None,
    seed: int = 0,
    page_size: int = 1,
    progress_callback: Callable[[str, int, int, int], None] | None = None,
    request_progress_callback: Callable[[str, int, int, int], None] | None = None,
    progress_interval_seconds: float = 5.0,
) -> dict[str, list[dict[str, float | int]]]:
    registry = build_strategy_registry(seed=seed, page_size=page_size)
    selected_names = strategy_names or list(registry)
    total_unique_blocks = count_unique_blocks(trace, page_size)
    full_cache_hits: list[int] | None = None

    results: dict[str, list[dict[str, float | int]]] = {}
    for strategy_name in selected_names:
        factory = registry[strategy_name]
        points: list[dict[str, float | int]] = []

        for point_index, cache_size in enumerate(cache_sizes, start=1):
            if progress_callback is not None:
                progress_callback(strategy_name, cache_size, point_index, len(cache_sizes))
            if cache_size >= total_unique_blocks:
                if full_cache_hits is None:
                    full_cache_hits = no_eviction_hit_tokens(trace, page_size)
                hit_tokens = full_cache_hits
            else:
                hit_tokens = run_strategy(
                    trace,
                    factory(cache_size),
                    progress_callback=(
                        None
                        if request_progress_callback is None
                        else lambda completed, total, name=strategy_name, size=cache_size: request_progress_callback(
                            name,
                            size,
                            completed,
                            total,
                        )
                    ),
                    progress_interval_seconds=progress_interval_seconds,
                )
            point = SimulationPoint(
                cache_size=cache_size,
                token_hit_rate=token_hit_rate(trace, hit_tokens),
                request_hit_rate=request_hit_rate(trace, hit_tokens),
            )
            points.append(point.as_dict())

        results[strategy_name] = points

    return results


def count_unique_blocks(trace: list[list[int]], page_size: int) -> int:
    return len({prefix for access in trace for prefix in iter_block_prefixes(access, page_size)})


def no_eviction_hit_tokens(trace: list[list[int]], page_size: int) -> list[int]:
    cached_prefixes: set[tuple[int, ...]] = set()
    hit_tokens: list[int] = []

    for tokens in trace:
        access_hit_tokens = 0
        access_prefixes = list(iter_block_prefixes(tokens, page_size))
        for prefix in access_prefixes:
            if prefix not in cached_prefixes:
                break
            access_hit_tokens = len(prefix)

        cached_prefixes.update(access_prefixes)
        hit_tokens.append(access_hit_tokens)

    return hit_tokens


def run_strategy(
    trace: list[list[int]],
    simulator: object,
    progress_callback: Callable[[int, int], None] | None = None,
    progress_interval_seconds: float = 5.0,
) -> list[int]:
    if isinstance(simulator, TreeConstrainedBelady):
        return simulator.simulate(
            trace,
            progress_callback=progress_callback,
            progress_interval_seconds=progress_interval_seconds,
        ).hit_tokens

    hit_tokens: list[int] = []
    total_accesses = len(trace)
    next_progress_at = time.monotonic() + progress_interval_seconds
    for access_index, tokens in enumerate(trace):
        result = simulator.access(tokens, access_index=access_index)
        hit_tokens.append(result.hit_tokens)
        if progress_callback is not None:
            now = time.monotonic()
            completed = access_index + 1
            if progress_interval_seconds <= 0 or completed == total_accesses or now >= next_progress_at:
                progress_callback(completed, total_accesses)
                next_progress_at = now + progress_interval_seconds
    return hit_tokens


def derive_cache_sizes(
    trace: list[list[int]],
    n_sizes: int = 8,
    min_fraction: float = 0.001,
    max_fraction: float = 1.0,
    page_size: int = 1,
) -> list[int]:
    total_unique_blocks = max(1, count_unique_blocks(trace, page_size))
    min_size = max(1, math.floor(total_unique_blocks * min_fraction))
    max_size = max(min_size, math.ceil(total_unique_blocks * max_fraction))

    if n_sizes <= 1 or min_size == max_size:
        return [max_size]

    raw_sizes = [
        round(math.exp(math.log(min_size) + step * (math.log(max_size) - math.log(min_size)) / (n_sizes - 1)))
        for step in range(n_sizes)
    ]
    return sorted(set(max(1, size) for size in raw_sizes))
