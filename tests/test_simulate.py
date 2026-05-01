from src.eviction import DepthLRU
from src.eviction import LRU
from src.radix_tree import RadixTree
from src.simulate import build_strategy_registry, no_eviction_hit_tokens, run_strategy, run_suite


def test_run_suite_reports_both_metrics_for_each_cache_size():
    trace = [[1, 2, 3], [1, 2, 4], [1, 2, 3]]

    results = run_suite(trace, cache_sizes=[2, 3], strategy_names=["lru", "tc_belady"], page_size=2)

    assert set(results) == {"lru", "tc_belady"}
    assert [point["cache_size"] for point in results["lru"]] == [2, 3]
    assert all({"cache_size", "token_hit_rate", "request_hit_rate"} <= point.keys() for point in results["lru"])
    assert results["tc_belady"][-1]["token_hit_rate"] >= results["lru"][-1]["token_hit_rate"]


def test_strategy_registry_exposes_expected_baselines():
    registry = build_strategy_registry(page_size=2)

    assert {"lru", "lfu", "fifo", "mru", "filo", "slru", "priority", "random", "tc_belady"} <= set(registry)
    assert "naive_lru" not in registry


def test_depth_lru_scales_alpha_with_page_size():
    registry = build_strategy_registry(page_size=32)

    simulator = registry["depth_lru"](budget=10)

    assert isinstance(simulator.eviction_strategy, DepthLRU)
    assert simulator.eviction_strategy.alpha == 0.32


def test_run_suite_derives_cache_sizes_from_unique_blocks():
    trace = [[1, 2, 3], [1, 2, 4]]

    results = run_suite(trace, cache_sizes=[3], strategy_names=["lru"], page_size=2)

    assert results["lru"][0]["cache_size"] == 3


def test_no_eviction_hit_tokens_matches_full_radix_tree_cache():
    trace = [[1, 2, 3], [1, 2, 4], [1, 2, 3, 5]]
    page_size = 2
    unique_blocks = 4

    tree = RadixTree(block_budget=unique_blocks, eviction_strategy=LRU(), page_size=page_size)
    tree_hits = [tree.access(tokens, access_index=index).hit_tokens for index, tokens in enumerate(trace)]

    assert no_eviction_hit_tokens(trace, page_size=page_size) == tree_hits


def test_run_strategy_reports_request_progress():
    trace = [[1, 2], [1, 3], [1, 2]]
    simulator = RadixTree(block_budget=2, eviction_strategy=LRU(), page_size=1)
    events = []

    run_strategy(
        trace,
        simulator,
        progress_callback=lambda completed, total: events.append((completed, total)),
        progress_interval_seconds=0,
    )

    assert events == [(1, 3), (2, 3), (3, 3)]
