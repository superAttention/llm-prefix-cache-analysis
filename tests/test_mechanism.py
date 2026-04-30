from src.mechanism import analyze_against_belady, select_peak_gap_cache_size


def test_select_peak_gap_cache_size_uses_relative_gap_to_belady():
    results = {
        "tc_belady": [
            {"cache_size": 2, "token_hit_rate": 0.5},
            {"cache_size": 4, "token_hit_rate": 0.8},
        ],
        "lru": [
            {"cache_size": 2, "token_hit_rate": 0.2},
            {"cache_size": 4, "token_hit_rate": 0.7},
        ],
    }

    assert select_peak_gap_cache_size(results, baseline_name="lru") == 2


def test_analyze_against_belady_labels_shared_candidates_by_group():
    trace = [[1], [2], [3], [1], [2]]

    frame = analyze_against_belady(trace, cache_size=2, strategy_name="lru")

    assert {"group", "prefix", "access_index", "tree_depth", "time_to_next_access", "lru_rank_at_evict"} <= set(frame.columns)
    assert set(frame["group"]) == {"A", "B", "D"}

    grouped = {tuple(row["prefix"]): row["group"] for row in frame.to_dict("records")}
    assert grouped[(1,)] == "A"
    assert grouped[(3,)] == "B"
    assert grouped[(2,)] == "D"
