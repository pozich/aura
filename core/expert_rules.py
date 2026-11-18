from __future__ import annotations

from dataclasses import dataclass, field

from core.expert_aggregation import stdev

CR_THRESHOLD = 0.1
CLOSE_RESULT_THRESHOLD = 0.05
CLEAR_LEADER_THRESHOLD = 0.15
WEAK_CRITERION_THRESHOLD = 4.0
WEAK_LEADER_OVERALL_THRESHOLD = 5.0
HIGH_DISAGREEMENT_THRESHOLD = 2.5


@dataclass
class RuleContext:
    ranked: list[tuple[str, float]]
    criteria_weights: dict[str, float]
    cr: float
    alternative_criterion_scores: dict[str, dict[str, float]]
    alternative_criterion_raw: dict[str, dict[str, list[float]]] = field(default_factory=dict)


def _rule_clear_leader(ctx: RuleContext) -> str | None:
    if len(ctx.ranked) < 2 or ctx.ranked[0][1] <= 0:
        return None
    top, second = ctx.ranked[0][1], ctx.ranked[1][1]
    if (top - second) / top >= CLEAR_LEADER_THRESHOLD:
        return (
            f'ЕСЛИ лидер опережает ближайшего конкурента больше чем на '
            f'{CLEAR_LEADER_THRESHOLD:.0%}, ТО рекомендовать его уверенно — '
            f'«{ctx.ranked[0][0]}» опережает на {(top - second) / top:.0%}.'
        )
    return None


def _rule_close_result(ctx: RuleContext) -> str | None:
    if len(ctx.ranked) < 2 or ctx.ranked[0][1] <= 0:
        return None
    top, second = ctx.ranked[0][1], ctx.ranked[1][1]
    if (top - second) / top < CLOSE_RESULT_THRESHOLD:
        return (
            f'ЕСЛИ разрыв между первым и вторым местом меньше {CLOSE_RESULT_THRESHOLD:.0%}, '
            f'ТО предложить обе альтернативы как равноценные — «{ctx.ranked[0][0]}» и '
            f'«{ctx.ranked[1][0]}» отличаются на {(top - second) / top:.0%}.'
        )
    return None


def _rule_inconsistent_experts(ctx: RuleContext) -> str | None:
    if ctx.cr > CR_THRESHOLD:
        return (
            f'ЕСЛИ коэффициент согласованности CR > {CR_THRESHOLD}, ТО веса критериев '
            f'считать ненадёжными и предложить экспертам повторить сравнение — '
            f'CR = {ctx.cr:.2f}.'
        )
    return None


def _rule_high_disagreement(ctx: RuleContext) -> str | None:
    messages = []
    for alt, criteria in ctx.alternative_criterion_raw.items():
        for criterion, raw_scores in criteria.items():
            spread = stdev(raw_scores)
            if spread > HIGH_DISAGREEMENT_THRESHOLD:
                messages.append(f'«{alt}» по критерию «{criterion}» (разброс {spread:.1f})')
    if not messages:
        return None
    return (
        f'ЕСЛИ оценки экспертов по альтернативе и критерию расходятся больше чем на '
        f'{HIGH_DISAGREEMENT_THRESHOLD}, ТО пометить оценку как спорную — это: '
        + '; '.join(messages) + '.'
    )


def _rule_weak_top_criterion(ctx: RuleContext) -> str | None:
    if not ctx.ranked or not ctx.criteria_weights:
        return None
    top_name = ctx.ranked[0][0]
    heaviest_criterion = max(ctx.criteria_weights, key=ctx.criteria_weights.get)
    score = ctx.alternative_criterion_scores.get(top_name, {}).get(heaviest_criterion)
    if score is not None and score < WEAK_CRITERION_THRESHOLD:
        return (
            f'ЕСЛИ лидер слаб (< {WEAK_CRITERION_THRESHOLD}/10) по самому весомому критерию, '
            f'ТО рекомендовать с оговоркой — «{top_name}» по критерию '
            f'«{heaviest_criterion}» набрал {score:.1f}/10.'
        )
    return None


def _rule_all_weak(ctx: RuleContext) -> str | None:
    if not ctx.ranked:
        return None
    if ctx.ranked[0][1] < WEAK_LEADER_OVERALL_THRESHOLD:
        return (
            f'ЕСЛИ даже лидер набрал меньше {WEAK_LEADER_OVERALL_THRESHOLD}/10, ТО ни одна '
            f'альтернатива не является сильным выбором — расширить список альтернатив.'
        )
    return None


RULES = [
    _rule_clear_leader,
    _rule_close_result,
    _rule_inconsistent_experts,
    _rule_high_disagreement,
    _rule_weak_top_criterion,
    _rule_all_weak,
]


def evaluate_rules(ctx: RuleContext) -> list[str]:
    fired = []
    for rule in RULES:
        message = rule(ctx)
        if message:
            fired.append(message)
    return fired
