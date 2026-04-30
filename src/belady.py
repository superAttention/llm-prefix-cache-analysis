from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from src.radix_tree import RadixTree, TreeNode


@dataclass(slots=True)
class SimulationResult:
    hit_tokens: list[int]


class _NoOpStrategy:
    def get_priority(self, node) -> int:
        return 0


class TreeConstrainedBelady:
    def __init__(self, token_budget: int) -> None:
        self.token_budget = token_budget

    def simulate(self, trace: list[list[int]]) -> SimulationResult:
        access_history = self._build_access_history(trace)
        tree = RadixTree(token_budget=self.token_budget, eviction_strategy=_NoOpStrategy())
        hit_tokens: list[int] = []

        for access_index, tokens in enumerate(trace):
            result = tree.lookup(tokens, access_index=access_index)
            tree.insert_suffix(tokens, result.hit_tokens, access_index)
            self._evict_until_within_budget(tree, access_history, access_index)
            hit_tokens.append(result.hit_tokens)

        return SimulationResult(hit_tokens=hit_tokens)

    def _build_access_history(self, trace: list[list[int]]) -> dict[tuple[int, ...], list[int]]:
        history: dict[tuple[int, ...], list[int]] = {}

        for access_index, tokens in enumerate(trace):
            prefix: list[int] = []
            for token in tokens:
                prefix.append(token)
                history.setdefault(tuple(prefix), []).append(access_index)

        return history

    def _evict_until_within_budget(
        self,
        tree: RadixTree,
        access_history: dict[tuple[int, ...], list[int]],
        access_index: int,
    ) -> None:
        while tree.cached_token_count > tree.token_budget:
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
