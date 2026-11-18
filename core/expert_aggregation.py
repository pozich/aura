from __future__ import annotations

import math


def aggregate_pairwise_judgments(
    expert_judgments: list[dict[tuple[str, str], float]],
) -> dict[tuple[str, str], float]:
    pairs: dict[tuple[str, str], list[float]] = {}
    for judgments in expert_judgments:
        for pair, value in judgments.items():
            pairs.setdefault(pair, []).append(value)

    aggregated: dict[tuple[str, str], float] = {}
    for pair, values in pairs.items():
        product = 1.0
        for v in values:
            product *= v
        aggregated[pair] = product ** (1.0 / len(values))
    return aggregated


def aggregate_scores(expert_scores: list[dict[str, float]]) -> dict[str, float]:
    names: set[str] = set()
    for scores in expert_scores:
        names.update(scores)

    return {
        name: sum(s.get(name, 0.0) for s in expert_scores) / len(expert_scores)
        for name in names
    }


def stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)
