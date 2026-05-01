from __future__ import annotations

from abc import ABC, abstractmethod
import random


class EvictionStrategy(ABC):
    @abstractmethod
    def get_priority(self, node) -> float | tuple:
        """Return a sortable priority where lower values evict first."""


class LRU(EvictionStrategy):
    def get_priority(self, node) -> int:
        return node.last_access_index


class LFU(EvictionStrategy):
    def get_priority(self, node) -> tuple[int, int]:
        return (node.access_count, node.last_access_index)


class FIFO(EvictionStrategy):
    def get_priority(self, node) -> int:
        return node.created_at


class MRU(EvictionStrategy):
    def get_priority(self, node) -> int:
        return -node.last_access_index


class FILO(EvictionStrategy):
    def get_priority(self, node) -> int:
        return -node.created_at


class SLRU(EvictionStrategy):
    def __init__(self, protected_threshold: int = 2) -> None:
        self.protected_threshold = protected_threshold

    def get_priority(self, node) -> tuple[int, int]:
        segment = 1 if node.access_count >= self.protected_threshold else 0
        return (segment, node.last_access_index)


class Priority(EvictionStrategy):
    def get_priority(self, node) -> tuple[int | float, int]:
        return (node.priority, node.last_access_index)


class DepthLRU(EvictionStrategy):
    """LRU penalized by tree depth.

    Problem: LRU keeps deep nodes because they look recently accessed ("false warmth"),
    but deep nodes are conversation tails that won't be reused. Shallow nodes are shared
    prefixes that LRU wrongly evicts because they look slightly stale.

    Fix: subtract a depth penalty from last_access_index so deep recently-accessed nodes
    compete with old nodes rather than always surviving.

    priority = last_access_index - alpha * tree_depth
    Lower = evict first. alpha controls how much depth overrides recency.

    Empirical reference points (from mechanism analysis):
      Group B (false warmth):  last_access_index ≈ current,  tree_depth median 664
      Group D (correctly warm): last_access_index ≈ current, tree_depth median 273
      Group A (wrongly evicted): last_access_index ≈ current-1, tree_depth median 145
      Group C (correctly evicted): last_access_index ≈ current, tree_depth median 654

    For alpha > 1/509 ≈ 0.002, shallow warm A nodes (depth=145, age=1) outscore
    deep dead C nodes (depth=654, age=0), reversing LRU's mistake.
    """

    def __init__(self, alpha: float = 0.01) -> None:
        self.alpha = alpha

    def get_priority(self, node) -> float:
        return node.last_access_index - self.alpha * node.depth

class Random(EvictionStrategy):
    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)

    def get_priority(self, node) -> float:
        return self._random.random()
