import pytest

import data.db as db
from core.expert_pipeline import run_evaluation
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

    book_a = add_alternative(session_id, "Книга А")
    book_b = add_alternative(session_id, "Книга Б")
    book_c = add_alternative(session_id, "Книга В")

    experts = [add_expert(session_id, f"Эксперт {i + 1}") for i in range(3)]

    for expert_id in experts:
        add_criteria_judgment(expert_id, quality, availability, 3.0)

    scores = {
        book_a: {quality: 9.0, availability: 7.0},
        book_b: {quality: 5.0, availability: 5.0},
        book_c: {quality: 2.0, availability: 3.0},
    }
    for expert_id in experts:
        for alt_id, by_criterion in scores.items():
            for criterion_id, score in by_criterion.items():
                add_alternative_score(expert_id, alt_id, criterion_id, score)

    result = run_evaluation(session_id)

    assert result["weights"]["качество"] > result["weights"]["доступность"]
    assert result["cr"] == pytest.approx(0.0, abs=1e-6)
    assert [name for name, _score in result["ranked"]] == ["Книга А", "Книга Б", "Книга В"]
    assert any("опережает" in rule for rule in result["fired_rules"])

    stored = list_results(session_id)
    assert [row["alternative_name"] for row in stored] == ["Книга А", "Книга Б", "Книга В"]
    assert [row["rank"] for row in stored] == [1, 2, 3]


def test_run_evaluation_disagreeing_experts_raise_cr_and_flag_it(expert_db):
    session_id = create_session("Спорная оценка", "Три эксперта расходятся во мнениях")

    a = add_criterion(session_id, "A")
    b = add_criterion(session_id, "B")
    c = add_criterion(session_id, "C")

    alt = add_alternative(session_id, "Единственная альтернатива")

    e1 = add_expert(session_id, "Эксперт 1")
    e2 = add_expert(session_id, "Эксперт 2")

    # Намеренно противоречивые попарные суждения (A>>B>>C, но C>>A) — высокий CR.
    add_criteria_judgment(e1, a, b, 9.0)
    add_criteria_judgment(e1, b, c, 9.0)
    add_criteria_judgment(e1, a, c, 1 / 9)
    add_criteria_judgment(e2, a, b, 9.0)
    add_criteria_judgment(e2, b, c, 9.0)
    add_criteria_judgment(e2, a, c, 1 / 9)

    for criterion in (a, b, c):
        add_alternative_score(e1, alt, criterion, 5.0)
        add_alternative_score(e2, alt, criterion, 5.0)

    result = run_evaluation(session_id)

    assert result["cr"] > 0.1
    assert any("CR" in rule for rule in result["fired_rules"])
