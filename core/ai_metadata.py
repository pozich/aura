from __future__ import annotations

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
