from __future__ import annotations

RANDOM_INDEX = {
    1: 0.0,
    2: 0.0,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}


def build_pairwise_matrix(
    names: list[str], judgments: dict[tuple[str, str], float]
) -> list[list[float]]:
    n = len(names)
    matrix = [[1.0] * n for _ in range(n)]
    index = {name: i for i, name in enumerate(names)}
    for (a, b), value in judgments.items():
        i, j = index[a], index[b]
        matrix[i][j] = value
        matrix[j][i] = 1.0 / value
    return matrix


def principal_eigenvector(matrix: list[list[float]], iterations: int = 200) -> list[float]:
    n = len(matrix)
    vector = [1.0] * n
    for _ in range(iterations):
        product = [sum(matrix[i][j] * vector[j] for j in range(n)) for i in range(n)]
        total = sum(product)
        vector = [v / total for v in product]
    return vector


def consistency_ratio(matrix: list[list[float]], weights: list[float]) -> float:
    n = len(matrix)
    if n <= 2:
        return 0.0
    weighted_sum = [sum(matrix[i][j] * weights[j] for j in range(n)) for i in range(n)]
    lambda_max = sum(weighted_sum[i] / weights[i] for i in range(n)) / n
    ci = (lambda_max - n) / (n - 1)
    ri = RANDOM_INDEX.get(n, RANDOM_INDEX[10])
    return ci / ri if ri else 0.0


def compute_weights(
    names: list[str], judgments: dict[tuple[str, str], float]
) -> tuple[dict[str, float], float]:
    matrix = build_pairwise_matrix(names, judgments)
    weights = principal_eigenvector(matrix)
    cr = consistency_ratio(matrix, weights)
    return dict(zip(names, weights)), cr


def weighted_score(criteria_weights: dict[str, float], book_scores: dict[str, float]) -> float:
    return sum(weight * book_scores.get(name, 0.0) for name, weight in criteria_weights.items())


def rank_books(
    criteria_weights: dict[str, float], scores_by_book: dict[int, dict[str, float]]
) -> list[tuple[int, float]]:
    scored = [
        (book_id, weighted_score(criteria_weights, scores))
        for book_id, scores in scores_by_book.items()
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored
