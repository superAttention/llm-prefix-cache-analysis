from src.belady import TreeConstrainedBelady
from src.eviction import LRU
from src.radix_tree import RadixTree


def test_tree_constrained_belady_beats_lru_on_small_trace():
    trace = [[1], [2], [3], [1], [2]]

    belady = TreeConstrainedBelady(token_budget=2)
    belady_results = belady.simulate(trace)

    lru_tree = RadixTree(token_budget=2, eviction_strategy=LRU())
    lru_hits = [lru_tree.access(tokens, access_index=index).hit_tokens for index, tokens in enumerate(trace)]

    assert sum(belady_results.hit_tokens) == 2
    assert sum(lru_hits) == 0
