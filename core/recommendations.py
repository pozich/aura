from __future__ import annotations

from data.db import (
    get_book_profile,
    list_books,
    list_segments,
    replace_recommendations,
    set_book_profile,
)


def _ensure_profile(book_id: int, title: str, author: str | None) -> dict | None:
    """Профиль уже закэширован (обычная ситуация для книг, импортированных через
    core.chapter_pipeline) — просто читаем его. Для книг, добавленных до этой фичи
    (сегменты ещё не кэшированы), достраиваем профиль один раз здесь же и тоже
    кэшируем — дальше для них это уже не повторится."""
    row = get_book_profile(book_id)
    if row is not None:
        return {"title": title, "author": author, "genre": None, "summary": row["summary"]}

    segments = list_segments(book_id)
    if not segments:
        return None

    from core.ai_metadata import analyze_book
    from core.chapter_pipeline import _representative_excerpts

    profile = analyze_book(title, author, _representative_excerpts([s["text"] for s in segments]))
    if profile is None:
        return None

    set_book_profile(book_id, profile["summary"], ", ".join(profile["themes"]) or None)
    return {"title": title, "author": author, "genre": profile["genre"], "summary": profile["summary"]}


def recompute_library_recommendations(count: int = 5) -> list[dict]:
    """Пересчитывает блок "вам также могут понравиться" на экране Библиотеки —
    вызывается при добавлении/удалении книги (core.gemini_worker.ask_recommendations_async),
    не при каждом открытии экрана. Читает только закэшированные профили книг
    (жанр/summary/темы), а не сырой текст — экономия токенов и есть весь смысл
    сегментов и профилей, которые кэширует core.chapter_pipeline при импорте."""
    books = list_books()
    profiles = []
    for book in books:
        profile = _ensure_profile(book["id"], book["title"], book["author"])
        if profile is not None:
            profiles.append(profile)

    if not profiles:
        replace_recommendations([])
        return []

    from core.ai_metadata import suggest_library_recommendations

    recommendations = suggest_library_recommendations(profiles, count) or []
    replace_recommendations(recommendations)
    return recommendations
