from src.eviction import LRU
from src.radix_tree import RadixTree


def test_radix_tree_reuses_shared_block_prefixes_and_counts_hit_tokens():
    tree = RadixTree(block_budget=8, eviction_strategy=LRU(), page_size=2)

    first = tree.access([1, 2, 3, 4], access_index=0)
    second = tree.access([1, 2, 5, 6], access_index=1)
    third = tree.access([1, 2, 3, 4, 7], access_index=2)

    assert first.hit_tokens == 0
    assert second.hit_tokens == 2
    assert third.hit_tokens == 4
    assert tree.cached_block_count == 4


def test_radix_tree_only_hits_full_blocks_under_page_splitting():
    tree = RadixTree(block_budget=4, eviction_strategy=LRU(), page_size=2)

    tree.access([1, 2, 3], access_index=0)

    assert tree.lookup([1, 2, 3, 4], access_index=1).hit_tokens == 2


def test_radix_tree_evicts_leaf_blocks_first_under_lru():
    tree = RadixTree(block_budget=2, eviction_strategy=LRU(), page_size=2)

    tree.access([1, 2, 3, 4], access_index=0)
    tree.access([1, 2, 5, 6], access_index=1)

    lookup_old = tree.lookup([1, 2, 3, 4], access_index=2)
    lookup_new = tree.lookup([1, 2, 5, 6], access_index=2)

    assert tree.cached_block_count == 2
    assert lookup_old.hit_tokens == 2
    assert lookup_new.hit_tokens == 4


def test_radix_tree_tracks_evictable_leaf_blocks_incrementally():
    tree = RadixTree(block_budget=8, eviction_strategy=LRU(), page_size=2)

    tree.access([1, 2, 3, 4], access_index=0)
    only_leaf = next(iter(tree.evictable_leaves))
    assert {leaf.prefix for leaf in tree.evictable_leaves} == {(1, 2, 3, 4)}

    tree.access([1, 2, 5, 6], access_index=1)
    assert {leaf.prefix for leaf in tree.evictable_leaves} == {(1, 2, 3, 4), (1, 2, 5, 6)}
    assert only_leaf in tree.evictable_leaves

    tree.remove_leaf(only_leaf)
    assert {leaf.prefix for leaf in tree.evictable_leaves} == {(1, 2, 5, 6)}

    remaining_leaf = next(iter(tree.evictable_leaves))
    tree.remove_leaf(remaining_leaf)
    assert {leaf.prefix for leaf in tree.evictable_leaves} == {(1, 2)}
