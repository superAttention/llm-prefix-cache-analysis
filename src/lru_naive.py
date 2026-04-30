from __future__ import annotations

from collections import OrderedDict

from src.radix_tree import AccessResult


class NaiveLRU:
    def __init__(self, token_budget: int) -> None:
        self.token_budget = token_budget
        self.cached_token_count = 0
        self._entries: OrderedDict[tuple[int, ...], int] = OrderedDict()

    def access(self, tokens: list[int], access_index: int) -> AccessResult:
        key = tuple(tokens)
        token_count = len(tokens)

        if key in self._entries:
            self._entries.move_to_end(key)
            return AccessResult(hit_tokens=token_count, inserted_tokens=0)

        if token_count > self.token_budget:
            return AccessResult(hit_tokens=0, inserted_tokens=token_count)

        while self.cached_token_count + token_count > self.token_budget and self._entries:
            _, evicted_tokens = self._entries.popitem(last=False)
            self.cached_token_count -= evicted_tokens

        self._entries[key] = token_count
        self.cached_token_count += token_count
        return AccessResult(hit_tokens=0, inserted_tokens=token_count)
