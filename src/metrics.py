from __future__ import annotations


def token_hit_rate(accesses: list[list[int]], hit_tokens: list[int]) -> float:
    total_requested = sum(len(access) for access in accesses)
    if total_requested == 0:
        return 0.0
    return sum(hit_tokens) / total_requested


def request_hit_rate(accesses: list[list[int]], hit_tokens: list[int]) -> float:
    if not accesses:
        return 0.0
    full_hits = sum(1 for access, hits in zip(accesses, hit_tokens, strict=True) if len(access) == hits)
    return full_hits / len(accesses)


def relative_gap(optimal_hit_rate: float, baseline_hit_rate: float) -> float:
    if optimal_hit_rate == 0:
        return 0.0
    return (optimal_hit_rate - baseline_hit_rate) / optimal_hit_rate
