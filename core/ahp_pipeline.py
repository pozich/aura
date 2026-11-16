from __future__ import annotations

from core.ahp import compute_weights, rank_books
from core.ai_metadata import extract_criteria_and_judgments, suggest_book_recommendations


def magic_query(query: str, count: int = 5) -> list[dict]:
    """Разбирает свободный текстовый запрос пользователя на критерии и их попарную
    важность (АХП), просит Gemini предложить книги под эти критерии с оценкой по
    каждому и ранжирует кандидатов весами критериев. Возвращает [] если на любом
    шаге Gemini не дал разборчивого ответа — чат в этом случае просто сообщает,
    что подбор не удался."""
    extraction = extract_criteria_and_judgments(query)
    if extraction is None:
        return []

    names, judgments = extraction
    if not names:
        return []

    weights, _cr = compute_weights(names, judgments)

    candidates = suggest_book_recommendations(query, names, count)
    if not candidates:
        return []

    scores_by_index = {i: c["scores"] for i, c in enumerate(candidates)}
    ranked = rank_books(weights, scores_by_index)

    return [{**candidates[index], "score": score} for index, score in ranked]


if __name__ == "__main__":
    for book in magic_query("хочу про теорию эволюции, чтобы легко читалось"):
        print(f"{book['score']:.2f} — {book['title']} ({book['author']})")
