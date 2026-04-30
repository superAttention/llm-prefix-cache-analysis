from src.lru_naive import NaiveLRU


def test_naive_lru_only_hits_full_prompts_and_respects_budget():
    cache = NaiveLRU(token_budget=5)

    assert cache.access([1, 2, 3], access_index=0).hit_tokens == 0
    assert cache.access([1, 2, 3], access_index=1).hit_tokens == 3
    assert cache.access([1, 2], access_index=2).hit_tokens == 0
    assert cache.cached_token_count == 5

    assert cache.access([9], access_index=3).hit_tokens == 0
    assert cache.cached_token_count <= 5
    assert cache.access([1, 2, 3], access_index=4).hit_tokens == 0
    assert cache.access([1, 2, 3], access_index=5).hit_tokens == 3
    assert cache.access([1, 2], access_index=6).hit_tokens == 0
