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


def test_radix_tree_splits_compressed_nodes_on_partial_prefix_overlap():
    tree = RadixTree(token_budget=16, eviction_strategy=LRU())

    tree.access([1, 2, 3, 4], access_index=0)
    tree.access([1, 2, 5], access_index=1)

    shared = tree.root.children[1]

    assert shared.key == (1, 2)
    assert set(shared.children) == {3, 5}
    assert shared.children[3].key == (3, 4)
    assert shared.children[5].key == (5,)
    assert tree.lookup([1, 2, 3, 4], access_index=2).hit_tokens == 4
    assert tree.lookup([1, 2, 5], access_index=2).hit_tokens == 3


def test_radix_tree_evicts_entire_leaf_segments_not_single_tokens():
    tree = RadixTree(token_budget=5, eviction_strategy=LRU())

    tree.access([1, 2, 3, 4], access_index=0)
    tree.access([1, 2, 5, 6], access_index=1)

    assert tree.cached_token_count == 4
    assert tree.lookup([1, 2, 3, 4], access_index=2).hit_tokens == 2
    assert tree.lookup([1, 2, 5, 6], access_index=2).hit_tokens == 4


def test_radix_tree_tracks_evictable_leaves_incrementally():
    tree = RadixTree(token_budget=16, eviction_strategy=LRU())

    tree.access([1, 2, 3, 4], access_index=0)
    only_leaf = next(iter(tree.evictable_leaves))
    assert {leaf.prefix for leaf in tree.evictable_leaves} == {(1, 2, 3, 4)}

    tree.access([1, 2, 5], access_index=1)
    assert {leaf.prefix for leaf in tree.evictable_leaves} == {(1, 2, 3, 4), (1, 2, 5)}
    assert only_leaf in tree.evictable_leaves

    tree.remove_leaf(only_leaf)
    assert {leaf.prefix for leaf in tree.evictable_leaves} == {(1, 2, 5)}

    remaining_leaf = next(iter(tree.evictable_leaves))
    tree.remove_leaf(remaining_leaf)
    assert {leaf.prefix for leaf in tree.evictable_leaves} == {(1, 2)}
