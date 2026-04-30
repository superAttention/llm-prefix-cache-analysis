from src.simulate import build_strategy_registry, run_suite


def test_run_suite_reports_both_metrics_for_each_cache_size():
    trace = [[1, 2, 3], [1, 2, 4], [1, 2, 3]]

    results = run_suite(trace, cache_sizes=[2, 3], strategy_names=["lru", "tc_belady", "naive_lru"])

    assert set(results) == {"lru", "tc_belady", "naive_lru"}
    assert [point["cache_size"] for point in results["lru"]] == [2, 3]
    assert all({"cache_size", "token_hit_rate", "request_hit_rate"} <= point.keys() for point in results["lru"])
    assert results["tc_belady"][-1]["token_hit_rate"] >= results["lru"][-1]["token_hit_rate"]


def test_strategy_registry_exposes_expected_baselines():
    registry = build_strategy_registry()

    assert {"lru", "lfu", "fifo", "mru", "filo", "slru", "priority", "random", "naive_lru", "tc_belady"} <= set(
        registry
    )
