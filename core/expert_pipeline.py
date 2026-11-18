from __future__ import annotations

from core.ahp import compute_weights, weighted_score
from core.expert_aggregation import aggregate_pairwise_judgments, aggregate_scores
from core.expert_rules import RuleContext, evaluate_rules
from data.expert_db import (
    list_alternative_scores,
    list_alternatives,
    list_criteria,
    list_criteria_judgments,
    replace_results,
    set_criteria_weights,
)


def _group_judgments_by_expert(rows) -> list[dict[tuple[str, str], float]]:
    by_expert: dict[int, dict[tuple[str, str], float]] = {}
    for row in rows:
        by_expert.setdefault(row["expert_id"], {})[(row["criterion_a"], row["criterion_b"])] = row["value"]
    return list(by_expert.values())


def _group_scores_by_alternative(rows) -> dict[str, list[dict[str, float]]]:
    by_alt_expert: dict[str, dict[int, dict[str, float]]] = {}
    for row in rows:
        per_expert = by_alt_expert.setdefault(row["alternative"], {})
        per_expert.setdefault(row["expert_id"], {})[row["criterion"]] = row["score"]
    return {alt: list(per_expert.values()) for alt, per_expert in by_alt_expert.items()}


def _raw_scores_by_alternative_criterion(rows) -> dict[str, dict[str, list[float]]]:
    raw: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        raw.setdefault(row["alternative"], {}).setdefault(row["criterion"], []).append(row["score"])
    return raw


def run_evaluation(session_id: int) -> dict:
    criteria_rows = list_criteria(session_id)
    criteria_names = [row["name"] for row in criteria_rows]
    name_to_criterion_id = {row["name"]: row["id"] for row in criteria_rows}

    alternative_rows = list_alternatives(session_id)
    name_to_alternative_id = {row["name"]: row["id"] for row in alternative_rows}

    judgment_rows = list_criteria_judgments(session_id)
    aggregated_judgments = aggregate_pairwise_judgments(_group_judgments_by_expert(judgment_rows))
    weights, cr = compute_weights(criteria_names, aggregated_judgments)
    set_criteria_weights({name_to_criterion_id[name]: weight for name, weight in weights.items()})

    score_rows = list_alternative_scores(session_id)
    scores_by_alternative = _group_scores_by_alternative(score_rows)
    aggregated_scores_by_alternative = {
        alt: aggregate_scores(expert_scores) for alt, expert_scores in scores_by_alternative.items()
    }

    ranked = sorted(
        (
            (alt, weighted_score(weights, scores))
            for alt, scores in aggregated_scores_by_alternative.items()
        ),
        key=lambda pair: pair[1],
        reverse=True,
    )

    context = RuleContext(
        ranked=ranked,
        criteria_weights=weights,
        cr=cr,
        alternative_criterion_scores=aggregated_scores_by_alternative,
        alternative_criterion_raw=_raw_scores_by_alternative_criterion(score_rows),
    )
    fired_rules = evaluate_rules(context)
    triggered_text = "\n".join(fired_rules) or None

    replace_results(
        session_id,
        [
            {
                "alternative_id": name_to_alternative_id[alt],
                "score": score,
                "rank": rank,
                "triggered_rules": triggered_text,
            }
            for rank, (alt, score) in enumerate(ranked, start=1)
        ],
    )

    return {
        "weights": weights,
        "cr": cr,
        "ranked": ranked,
        "fired_rules": fired_rules,
    }
