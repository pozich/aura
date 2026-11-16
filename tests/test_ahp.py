import pytest

from core.ahp import compute_weights, rank_books, weighted_score


def test_compute_weights_equal_judgments_gives_equal_weights():
    names = ["A", "B", "C"]
    weights, cr = compute_weights(names, {})
    assert weights["A"] == pytest.approx(1 / 3, abs=1e-6)
    assert weights["B"] == pytest.approx(1 / 3, abs=1e-6)
    assert weights["C"] == pytest.approx(1 / 3, abs=1e-6)
    assert cr == pytest.approx(0.0, abs=1e-6)


def test_compute_weights_orders_by_judged_importance():
    names = ["A", "B", "C"]
    judgments = {("A", "B"): 2.0, ("B", "C"): 2.0, ("A", "C"): 4.0}
    weights, cr = compute_weights(names, judgments)

    assert weights["A"] > weights["B"] > weights["C"]
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)
    assert cr < 0.1


def test_compute_weights_inconsistent_matrix_has_high_cr():
    names = ["A", "B", "C"]
    judgments = {("A", "B"): 9.0, ("B", "C"): 9.0, ("A", "C"): 1 / 9}
    _weights, cr = compute_weights(names, judgments)

    assert cr > 0.1


def test_weighted_score_is_sum_of_weight_times_score():
    weights = {"readability": 0.5, "popularity": 0.3, "length": 0.2}
    scores = {"readability": 10.0, "popularity": 0.0, "length": 5.0}

    assert weighted_score(weights, scores) == pytest.approx(0.5 * 10 + 0.3 * 0 + 0.2 * 5)


def test_weighted_score_treats_missing_criterion_as_zero():
    weights = {"a": 0.5, "b": 0.5}
    scores = {"a": 8.0}

    assert weighted_score(weights, scores) == pytest.approx(0.5 * 8)


def test_rank_books_sorts_descending_by_score():
    weights = {"a": 1.0}
    scores_by_book = {1: {"a": 3.0}, 2: {"a": 9.0}, 3: {"a": 1.0}}

    ranked = rank_books(weights, scores_by_book)

    assert [book_id for book_id, _score in ranked] == [2, 1, 3]
