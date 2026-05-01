from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import time
from typing import Callable

from src.paging import iter_block_prefixes
from src.radix_tree import RadixTree, TreeNode


@dataclass(slots=True)
class SimulationResult:
    hit_tokens: list[int]


class _NoOpStrategy:
    def get_priority(self, node) -> int:
        return 0


class TreeConstrainedBelady:
    """Offline optimal under the simplified fixed-block radix model.

    The cache is budgeted in blocks, each node stores exactly one page-sized
    block, and eviction removes one leaf block at a time. This keeps the
    oracle well-defined: evict the leaf block whose block-aligned prefix is
    used farthest in the future.
    """

    def __init__(self, block_budget: int, page_size: int = 1) -> None:
        self.block_budget = block_budget
        self.page_size = page_size

    def simulate(
        self,
        trace: list[list[int]],
        progress_callback: Callable[[int, int], None] | None = None,
        progress_interval_seconds: float = 5.0,
    ) -> SimulationResult:
        access_history = self._build_access_history(trace)
        tree = RadixTree(
            block_budget=self.block_budget,
            eviction_strategy=_NoOpStrategy(),
            page_size=self.page_size,
        )
        hit_tokens: list[int] = []
        total_accesses = len(trace)
        next_progress_at = time.monotonic() + progress_interval_seconds

        for access_index, tokens in enumerate(trace):
            result = tree.lookup(tokens, access_index=access_index)
            tree.insert_suffix(tokens, result.hit_blocks, access_index)
            self._evict_until_within_budget(tree, access_history, access_index)
            hit_tokens.append(result.hit_tokens)
            if progress_callback is not None:
                now = time.monotonic()
                completed = access_index + 1
                if progress_interval_seconds <= 0 or completed == total_accesses or now >= next_progress_at:
                    progress_callback(completed, total_accesses)
                    next_progress_at = now + progress_interval_seconds

        return SimulationResult(hit_tokens=hit_tokens)

    def _build_access_history(self, trace: list[list[int]]) -> dict[tuple[int, ...], list[int]]:
        history: dict[tuple[int, ...], list[int]] = {}

        for access_index, tokens in enumerate(trace):
            for prefix in iter_block_prefixes(tokens, self.page_size):
                history.setdefault(prefix, []).append(access_index)

        return history

    def _evict_until_within_budget(
        self,
        tree: RadixTree,
        access_history: dict[tuple[int, ...], list[int]],
        access_index: int,
    ) -> None:
        while tree.cached_block_count > tree.block_budget:
            leaves = tree.iter_leaves()
            victim = max(leaves, key=lambda node: self._next_access(node, access_history, access_index))
            tree.remove_leaf(victim)

    def _next_access(
        self,
        node: TreeNode,
        access_history: dict[tuple[int, ...], list[int]],
        access_index: int,
    ) -> float:
        history = access_history.get(node.prefix, [])
        next_position = bisect_right(history, access_index)
        if next_position >= len(history):
            return float("inf")
        return float(history[next_position])
