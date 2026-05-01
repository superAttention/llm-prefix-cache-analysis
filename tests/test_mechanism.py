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
    # trace: [1],[2],[3],[1],[2] with cache_size=2
    # At the first eviction (access_index=2, round=0) all three nodes are candidates:
    #   LRU evicts (1,) — oldest; Belady oracle evicts (3,) — never accessed again (inf)
    #   → (1,)=A (LRU mistake), (3,)=B (Belady oracle choice), (2,)=D (both retain)
    trace = [[1], [2], [3], [1], [2]]

    frame = analyze_against_belady(trace, cache_size=2, strategy_name="lru")

    assert {"group", "prefix", "access_index", "tree_depth", "time_to_next_access", "lru_rank_at_evict"} <= set(frame.columns)
    assert "A" in set(frame["group"])
    assert "B" in set(frame["group"])

    first_eviction = frame[(frame["access_index"] == 2) & (frame["eviction_round"] == 0)]
    grouped = {tuple(row["prefix"]): row["group"] for row in first_eviction.to_dict("records")}
    assert grouped[(1,)] == "A"   # LRU evicts (1,); Belady would keep it (next access in 1 step)
    assert grouped[(3,)] == "B"   # Belady evicts (3,); LRU keeps it (most recent)
    assert grouped[(2,)] == "D"   # both retain


def test_analyze_against_belady_reports_progress():
    trace = [[1], [2], [3], [1], [2]]
    events = []
    stages = []

    analyze_against_belady(
        trace,
        cache_size=2,
        strategy_name="lru",
        progress_callback=lambda completed, total, records: events.append((completed, total, records)),
        status_callback=stages.append,
        progress_interval_seconds=0,
    )

    assert events
    assert events[-1][0:2] == (5, 5)
    assert events[-1][2] > 0
    assert any("building DataFrame" in stage for stage in stages)
    assert any("built DataFrame" in stage for stage in stages)
