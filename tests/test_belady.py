from src.belady import TreeConstrainedBelady
from src.eviction import LRU
from src.radix_tree import RadixTree


def test_tree_constrained_belady_beats_lru_on_small_block_trace():
    trace = [[1, 2], [3, 4], [5, 6], [1, 2], [3, 4]]

    belady = TreeConstrainedBelady(block_budget=2, page_size=2)
    belady_results = belady.simulate(trace)

    lru_tree = RadixTree(block_budget=2, eviction_strategy=LRU(), page_size=2)
    lru_hits = [lru_tree.access(tokens, access_index=index).hit_tokens for index, tokens in enumerate(trace)]

    assert sum(belady_results.hit_tokens) == 4
    assert sum(lru_hits) == 0


def test_tree_constrained_belady_respects_page_boundaries_for_partial_tail_blocks():
    trace = [[1, 2, 3], [1, 2, 3, 4], [1, 2, 3]]

    belady = TreeConstrainedBelady(block_budget=2, page_size=2)
    belady_results = belady.simulate(trace)

    assert belady_results.hit_tokens == [0, 2, 3]


def test_tree_constrained_belady_reports_request_progress():
    trace = [[1, 2], [3, 4], [1, 2]]
    belady = TreeConstrainedBelady(block_budget=1, page_size=2)
    events = []

    belady.simulate(
        trace,
        progress_callback=lambda completed, total: events.append((completed, total)),
        progress_interval_seconds=0,
    )

    assert events == [(1, 3), (2, 3), (3, 3)]
