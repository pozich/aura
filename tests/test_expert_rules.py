from core.expert_rules import RuleContext, evaluate_rules


def _context(**overrides) -> RuleContext:
    defaults = dict(
        ranked=[("Книга А", 8.0), ("Книга Б", 5.0), ("Книга В", 3.0)],
        criteria_weights={"качество": 0.6, "доступность": 0.4},
        cr=0.02,
        alternative_criterion_scores={
            "Книга А": {"качество": 9.0, "доступность": 7.0},
            "Книга Б": {"качество": 5.0, "доступность": 5.0},
            "Книга В": {"качество": 3.0, "доступность": 3.0},
        },
        alternative_criterion_raw={
            "Книга А": {"качество": [9.0, 9.0, 9.0], "доступность": [7.0, 7.0, 7.0]},
        },
    )
    defaults.update(overrides)
    return RuleContext(**defaults)


def test_clear_leader_rule_fires_on_big_gap():
    fired = evaluate_rules(_context())
    assert any("опережает" in r for r in fired)


def test_close_result_rule_fires_on_small_gap():
    ctx = _context(ranked=[("Книга А", 8.0), ("Книга Б", 7.8), ("Книга В", 3.0)])
    fired = evaluate_rules(ctx)
    assert any("равноценные" in r for r in fired)
    assert not any("опережает" in r for r in fired)


def test_inconsistent_experts_rule_fires_on_high_cr():
    ctx = _context(cr=0.35)
    fired = evaluate_rules(ctx)
    assert any("CR" in r for r in fired)


def test_inconsistent_experts_rule_silent_on_low_cr():
    ctx = _context(cr=0.02)
    fired = evaluate_rules(ctx)
    assert not any("CR" in r for r in fired)


def test_high_disagreement_rule_fires_on_spread():
    ctx = _context(
        alternative_criterion_raw={
            "Книга А": {"качество": [0.0, 10.0, 10.0]},
        }
    )
    fired = evaluate_rules(ctx)
    assert any("расход" in r for r in fired)


def test_weak_top_criterion_rule_fires_when_leader_weak_on_heaviest_criterion():
    ctx = _context(
        ranked=[("Книга А", 6.0), ("Книга Б", 5.0)],
        criteria_weights={"качество": 0.9, "доступность": 0.1},
        alternative_criterion_scores={
            "Книга А": {"качество": 2.0, "доступность": 10.0},
            "Книга Б": {"качество": 5.0, "доступность": 5.0},
        },
    )
    fired = evaluate_rules(ctx)
    assert any("слаб" in r for r in fired)


def test_all_weak_rule_fires_when_leader_score_is_low():
    ctx = _context(ranked=[("Книга А", 3.0), ("Книга Б", 2.0)])
    fired = evaluate_rules(ctx)
    assert any("не является сильным выбором" in r for r in fired)


def test_no_rules_fire_on_clean_middling_result():
    ctx = _context(
        ranked=[("Книга А", 7.0), ("Книга Б", 6.3), ("Книга В", 5.8)],
        cr=0.02,
        alternative_criterion_scores={
            "Книга А": {"качество": 6.5, "доступность": 7.0},
            "Книга Б": {"качество": 6.0, "доступность": 6.0},
            "Книга В": {"качество": 5.8, "доступность": 5.8},
        },
        alternative_criterion_raw={},
    )
    assert evaluate_rules(ctx) == []
