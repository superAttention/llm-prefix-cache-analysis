import pytest

from src.metrics import relative_gap, request_hit_rate, token_hit_rate


def test_metrics_capture_token_and_request_level_divergence():
    accesses = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]
    hit_tokens = [5, 3]

    assert token_hit_rate(accesses, hit_tokens) == 0.8
    assert request_hit_rate(accesses, hit_tokens) == 0.5


def test_relative_gap_uses_optimal_as_denominator():
    assert relative_gap(optimal_hit_rate=0.8, baseline_hit_rate=0.6) == pytest.approx(0.25)
    assert relative_gap(optimal_hit_rate=0.0, baseline_hit_rate=0.0) == 0.0
