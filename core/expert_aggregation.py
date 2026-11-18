from __future__ import annotations

import math


def aggregate_pairwise_judgments(
    expert_judgments: list[dict[tuple[str, str], float]],
) -> dict[tuple[str, str], float]:
    """Групповой АХП: несколько экспертов независимо сравнивают одни и те же пары
    критериев — сводим в одну матрицу средним ГЕОМЕТРИЧЕСКИМ (стандартный способ
    агрегации попарных суждений нескольких экспертов, в отличие от среднего
    арифметического не ломает обратную симметричность a_ij = 1/a_ji: среднее
    геометрическое пары (2, 1/2) и (8, 1/8) всё ещё даёт обратные друг другу
    числа, среднее арифметическое — нет)."""
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
    """Оценки одной альтернативы по критериям от нескольких экспертов — это не
    отношения (как попарные суждения), а прямые баллы 0-10, для них обычное
    среднее арифметическое и есть стандартная агрегация."""
    names: set[str] = set()
    for scores in expert_scores:
        names.update(scores)

    return {
        name: sum(s.get(name, 0.0) for s in expert_scores) / len(expert_scores)
        for name in names
    }


def stdev(values: list[float]) -> float:
    """Выборочное стандартное отклонение — насколько эксперты расходятся в
    конкретной оценке. core.expert_rules использует это, чтобы находить
    "спорные" оценки по отдельной альтернативе/критерию."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)
