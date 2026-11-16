from __future__ import annotations

from core.ahp import weighted_score
from core.ai_metadata import suggest_criteria_scores
from data.db import add_ahp_result, list_ahp_criteria, list_books, list_chapters


def _sample_text_for_book(book_id: int, max_chars: int = 3000) -> str:
    for chapter in list_chapters(book_id):
        text = chapter["text"]
        if text and text.strip():
            return text[:max_chars]
    return ""


def rank_all_books() -> list[tuple[int, float]]:
    criteria_rows = list_ahp_criteria()
    if not criteria_rows:
        return []

    criteria_weights = {row["name"]: row["weight"] for row in criteria_rows}
    criteria_names = list(criteria_weights)

    results: list[tuple[int, float]] = []
    for book in list_books():
        book_id = book["id"]
        sample_text = _sample_text_for_book(book_id)
        if not sample_text:
            print(f"[ahp_pipeline] книга {book_id} ({book['title']}) пропущена — нет текста глав")
            continue

        suggestion = suggest_criteria_scores(
            book["title"], book["author"], sample_text, criteria_names
        )
        if suggestion is None:
            print(f"[ahp_pipeline] книга {book_id} ({book['title']}) пропущена — Gemini не дал оценку")
            continue

        scores, explanation = suggestion
        score = weighted_score(criteria_weights, scores)
        add_ahp_result(book_id, score, explanation)
        results.append((book_id, score))

    results.sort(key=lambda pair: pair[1], reverse=True)
    return results


if __name__ == "__main__":
    for book_id, score in rank_all_books():
        print(f"{book_id}: {score:.2f}")
