import pytest

import data.db as db
from core.expert_pipeline import ExpertEvaluationError, run_evaluation
from data.expert_db import (
    add_alternative,
    add_alternative_score,
    add_criteria_judgment,
    add_criterion,
    add_expert,
    create_session,
    list_results,
)


@pytest.fixture
def expert_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test_aura.db")
    db.init_db()
    return db


def test_run_evaluation_ranks_by_weighted_score(expert_db):
    session_id = create_session("Что читать дальше", "Выбор книги из трёх вариантов")

    quality = add_criterion(session_id, "качество")
    availability = add_criterion(session_id, "доступность")
    relevance = add_criterion(session_id, "релевантность")
    actuality = add_criterion(session_id, "актуальность")

    book_a = add_alternative(session_id, "Книга А")
    book_b = add_alternative(session_id, "Книга Б")
    book_c = add_alternative(session_id, "Книга В")

    experts = [add_expert(session_id, f"Эксперт {i + 1}") for i in range(3)]

    for expert_id in experts:
        add_criteria_judgment(expert_id, quality, availability, 3.0)
        add_criteria_judgment(expert_id, quality, relevance, 1.0)
        add_criteria_judgment(expert_id, quality, actuality, 1.0)

    scores = {
        book_a: {quality: 9.0, availability: 7.0, relevance: 6.0, actuality: 6.0},
        book_b: {quality: 5.0, availability: 5.0, relevance: 6.0, actuality: 6.0},
        book_c: {quality: 2.0, availability: 3.0, relevance: 6.0, actuality: 6.0},
    }
    for expert_id in experts:
        for alt_id, by_criterion in scores.items():
            for criterion_id, score in by_criterion.items():
                add_alternative_score(expert_id, alt_id, criterion_id, score)

    result = run_evaluation(session_id)

    assert result["weights"]["качество"] > result["weights"]["доступность"]
    assert result["cr"] < 0.1
    assert [name for name, _score in result["ranked"]] == ["Книга А", "Книга Б", "Книга В"]
    assert any("опережает" in rule for rule in result["fired_rules"])

    stored = list_results(session_id)
    assert [row["alternative_name"] for row in stored] == ["Книга А", "Книга Б", "Книга В"]
    assert [row["rank"] for row in stored] == [1, 2, 3]


def test_run_evaluation_disagreeing_experts_raise_cr_and_flag_it(expert_db):
    session_id = create_session("Спорная оценка", "Эксперты расходятся во мнениях")

    a = add_criterion(session_id, "A")
    b = add_criterion(session_id, "B")
    c = add_criterion(session_id, "C")
    d = add_criterion(session_id, "D")

    alt1 = add_alternative(session_id, "Альтернатива 1")
    alt2 = add_alternative(session_id, "Альтернатива 2")
    alt3 = add_alternative(session_id, "Альтернатива 3")

    experts = [add_expert(session_id, f"Эксперт {i + 1}") for i in range(3)]

    for expert_id in experts:
        add_criteria_judgment(expert_id, a, b, 9.0)
        add_criteria_judgment(expert_id, b, c, 9.0)
        add_criteria_judgment(expert_id, a, c, 1 / 9)
        add_criteria_judgment(expert_id, a, d, 1.0)

    for expert_id in experts:
        for alt in (alt1, alt2, alt3):
            for criterion in (a, b, c, d):
                add_alternative_score(expert_id, alt, criterion, 5.0)

    result = run_evaluation(session_id)

    assert result["cr"] > 0.1
    assert any("CR" in rule for rule in result["fired_rules"])


def test_run_evaluation_requires_minimum_alternatives(expert_db):
    session_id = create_session("Мало альтернатив", "")
    for name in ("A", "B", "C", "D"):
        add_criterion(session_id, name)
    add_alternative(session_id, "Единственная")
    for i in range(3):
        add_expert(session_id, f"Эксперт {i + 1}")

    with pytest.raises(ExpertEvaluationError):
        run_evaluation(session_id)


def test_run_evaluation_requires_minimum_criteria(expert_db):
    session_id = create_session("Мало критериев", "")
    add_criterion(session_id, "A")
    for name in ("Альт 1", "Альт 2", "Альт 3"):
        add_alternative(session_id, name)
    for i in range(3):
        add_expert(session_id, f"Эксперт {i + 1}")

    with pytest.raises(ExpertEvaluationError):
        run_evaluation(session_id)


def test_run_evaluation_requires_minimum_experts(expert_db):
    session_id = create_session("Мало экспертов", "")
    for name in ("A", "B", "C", "D"):
        add_criterion(session_id, name)
    for name in ("Альт 1", "Альт 2", "Альт 3"):
        add_alternative(session_id, name)
    add_expert(session_id, "Единственный эксперт")

    with pytest.raises(ExpertEvaluationError):
        run_evaluation(session_id)
