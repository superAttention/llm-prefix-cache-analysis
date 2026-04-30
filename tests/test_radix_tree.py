from src.eviction import LRU
from src.radix_tree import RadixTree


def test_radix_tree_reuses_shared_prefixes_and_counts_hit_tokens():
    tree = RadixTree(token_budget=16, eviction_strategy=LRU())

    first = tree.access([1, 2, 3], access_index=0)
    second = tree.access([1, 2, 4], access_index=1)
    third = tree.access([1, 2, 3, 5], access_index=2)

    assert first.hit_tokens == 0
    assert second.hit_tokens == 2
    assert third.hit_tokens == 3
    assert tree.cached_token_count == 5


def test_radix_tree_evicts_leaves_first_under_lru():
    tree = RadixTree(token_budget=3, eviction_strategy=LRU())

    tree.access([1, 2, 3], access_index=0)
    tree.access([1, 2, 4], access_index=1)

    lookup_old = tree.lookup([1, 2, 3], access_index=2)
    lookup_new = tree.lookup([1, 2, 4], access_index=2)

    assert tree.cached_token_count == 3
    assert lookup_old.hit_tokens == 2
    assert lookup_new.hit_tokens == 3
