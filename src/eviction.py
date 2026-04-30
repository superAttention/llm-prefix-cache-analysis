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


class Random(EvictionStrategy):
    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)

    def get_priority(self, node) -> float:
        return self._random.random()
