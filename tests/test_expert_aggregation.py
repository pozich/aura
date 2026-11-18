import pytest

from core.expert_aggregation import aggregate_pairwise_judgments, aggregate_scores, stdev


def test_aggregate_pairwise_judgments_geometric_mean():
    judgments = [
        {("A", "B"): 2.0},
        {("A", "B"): 8.0},
    ]
    aggregated = aggregate_pairwise_judgments(judgments)
    assert aggregated[("A", "B")] == pytest.approx(4.0)


def test_aggregate_pairwise_judgments_preserves_reciprocal_symmetry():
    judgments = [
        {("A", "B"): 2.0, ("B", "A"): 0.5},
        {("A", "B"): 8.0, ("B", "A"): 1 / 8},
    ]
    aggregated = aggregate_pairwise_judgments(judgments)
    assert aggregated[("A", "B")] * aggregated[("B", "A")] == pytest.approx(1.0)


def test_aggregate_pairwise_judgments_merges_missing_pairs_across_experts():
    judgments = [{("A", "B"): 3.0}, {("B", "C"): 2.0}]
    aggregated = aggregate_pairwise_judgments(judgments)
    assert aggregated == {("A", "B"): 3.0, ("B", "C"): 2.0}


def test_aggregate_scores_is_arithmetic_mean():
    scores = [{"a": 8.0, "b": 4.0}, {"a": 6.0, "b": 6.0}, {"a": 4.0, "b": 8.0}]
    aggregated = aggregate_scores(scores)
    assert aggregated == {"a": pytest.approx(6.0), "b": pytest.approx(6.0)}


def test_aggregate_scores_missing_criterion_treated_as_zero():
    scores = [{"a": 10.0}, {"a": 10.0, "b": 10.0}]
    aggregated = aggregate_scores(scores)
    assert aggregated["b"] == pytest.approx(5.0)


def test_stdev_single_value_is_zero():
    assert stdev([5.0]) == 0.0


def test_stdev_identical_values_is_zero():
    assert stdev([7.0, 7.0, 7.0]) == pytest.approx(0.0)


def test_stdev_detects_spread():
    assert stdev([0.0, 10.0]) == pytest.approx(7.0710678, abs=1e-5)
