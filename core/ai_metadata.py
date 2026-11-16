from __future__ import annotations

import json
import re

from core.gemini_client import GeminiError, generate


def suggest_category(title: str, author: str | None, sample_text: str) -> str | None:
    """Просит Gemini одним-двумя словами назвать жанр книги — используется, чтобы
    автоматически назначить категорию при импорте. Если активного ключа нет или
    запрос не удался — печатает причину в консоль и возвращает None, импорт книги
    при этом не падает."""
    if not sample_text:
        return None

    prompt = (
        "Определи жанр книги одним-двумя словами на русском (например: Классика, "
        "Фантастика, Детектив, Научпоп). Ответь ТОЛЬКО названием жанра, без пояснений "
        "и кавычек.\n\n"
        f"Название: {title}\n"
        f"Автор: {author or 'неизвестен'}\n"
        f"Отрывок текста:\n{sample_text[:3000]}"
    )

    try:
        text, _usage = generate(prompt)
    except GeminiError as exc:
        print(f"[ai_metadata] жанр не определён: {exc}")
        return None

    tag = text.strip().splitlines()[0].strip().strip(".")
    tag = re.sub(r'^["\'«]|["\'»]$', "", tag).strip()
    return tag or None


def suggest_criteria_scores(
    title: str, author: str | None, sample_text: str, criteria: list[str]
) -> tuple[dict[str, float], str] | None:
    """Просит Gemini оценить книгу по заданным критериям АХП (0-10 за каждый) —
    используется для автозаполнения book_scores перед core.ahp.rank_books, чтобы не
    выставлять оценки по каждой книге и критерию вручную. При отсутствии ключа или
    сбое/неразборчивом ответе возвращает None, ранжирование при этом не падает."""
    if not sample_text or not criteria:
        return None

    prompt = (
        "Оцени книгу по каждому из критериев числом от 0 до 10 "
        "(0 — совсем не соответствует, 10 — полностью соответствует). "
        f"Критерии: {', '.join(criteria)}.\n"
        "Ответь СТРОГО JSON-объектом без пояснений вокруг, с ключом \"объяснение\" — "
        "короткое обоснование одним предложением на русском. Пример формата: "
        '{"критерий1": 7, "критерий2": 4, "объяснение": "..."}\n\n'
        f"Название: {title}\n"
        f"Автор: {author or 'неизвестен'}\n"
        f"Отрывок текста:\n{sample_text[:3000]}"
    )

    try:
        text, _usage = generate(prompt)
    except GeminiError as exc:
        print(f"[ai_metadata] оценки по критериям не получены: {exc}")
        return None

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        print(f"[ai_metadata] не удалось найти JSON в ответе: {text!r}")
        return None

    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        print(f"[ai_metadata] не удалось разобрать JSON ответа: {exc}")
        return None

    explanation = str(payload.pop("объяснение", "")).strip()
    scores: dict[str, float] = {}
    for name in criteria:
        value = payload.get(name)
        if isinstance(value, (int, float)):
            scores[name] = max(0.0, min(10.0, float(value)))

    if not scores:
        return None
    return scores, explanation
