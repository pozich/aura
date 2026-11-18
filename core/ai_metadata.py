from __future__ import annotations

import json
import re

from core.gemini_client import GeminiError, generate


def analyze_book(title: str, author: str | None, excerpts: list[str]) -> dict | None:
    if not excerpts:
        return None

    excerpts_block = "\n\n".join(
        f"Отрывок {i + 1}:\n{excerpt[:2500]}" for i, excerpt in enumerate(excerpts)
    )
    prompt = (
        "Ниже несколько отрывков одной книги, взятых из начала, середины и конца — "
        "по ним нужно понять книгу целиком, а не только её начало.\n"
        "Определи: жанр одним-двумя словами, краткое summary в 2-3 предложения "
        "(без спойлера концовки) и список из 2-4 тем/мотивов книги.\n"
        "Ответь СТРОГО JSON без пояснений вокруг, формата: "
        '{"жанр": "...", "summary": "...", "темы": ["...", "..."]}\n\n'
        f"Название: {title}\n"
        f"Автор: {author or 'неизвестен'}\n\n"
        f"{excerpts_block}"
    )

    try:
        text, _usage = generate(prompt)
    except GeminiError as exc:
        print(f"[ai_metadata] профиль книги не получен: {exc}")
        return None

    payload = _extract_json(text)
    if payload is None:
        return None

    summary = str(payload.get("summary", "")).strip()
    if not summary:
        return None

    genre = str(payload.get("жанр", "")).strip() or None
    themes = [str(t).strip() for t in payload.get("темы", []) if str(t).strip()]
    return {"genre": genre, "summary": summary, "themes": themes}


def suggest_library_recommendations(profiles: list[dict], count: int = 5) -> list[dict] | None:
    if not profiles:
        return None

    lines = []
    for p in profiles:
        author_part = f" ({p['author']})" if p.get("author") else ""
        lines.append(f"- «{p['title']}»{author_part}: {p.get('genre') or ''}. {p.get('summary', '')}")
    library_block = "\n\n".join(lines)
    prompt = (
        f"Вот книги, которые уже есть в библиотеке читателя:\n{library_block}\n\n"
        f"Посоветуй {count} ДРУГИХ реальных книг (которых нет в этом списке), "
        "которые читателю тоже понравятся, опираясь на жанры и темы его библиотеки. "
        "Для каждой дай короткое описание в 1-2 предложения, почему она подходит.\n"
        "Ответь СТРОГО JSON-массивом без пояснений вокруг, формата: "
        '[{"название": "...", "автор": "...", "описание": "..."}, ...]'
    )

    try:
        text, _usage = generate(prompt)
    except GeminiError as exc:
        print(f"[ai_metadata] рекомендации для библиотеки не получены: {exc}")
        return None

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        print(f"[ai_metadata] не удалось найти JSON-массив в ответе: {text!r}")
        return None

    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        print(f"[ai_metadata] не удалось разобрать JSON ответа: {exc}")
        return None

    recommendations = []
    for item in items:
        title = str(item.get("название", "")).strip()
        if not title:
            continue
        recommendations.append(
            {
                "title": title,
                "author": str(item.get("автор", "")).strip() or None,
                "description": str(item.get("описание", "")).strip(),
            }
        )

    return recommendations or None


def _extract_json(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        print(f"[ai_metadata] не удалось найти JSON в ответе: {text!r}")
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        print(f"[ai_metadata] не удалось разобрать JSON ответа: {exc}")
        return None


def extract_criteria_and_judgments(
    query: str,
) -> tuple[list[str], dict[tuple[str, str], float]] | None:
    if not query.strip():
        return None

    prompt = (
        "Пользователь ищет книгу и описывает, что ему важно, свободным текстом. "
        "Выдели 2-4 критерия подбора (тема/жанр — всегда один из них, плюс явные "
        "пожелания вроде лёгкости чтения, объёма, настроения). Затем для каждой пары "
        "критериев оцени, какой важнее и во сколько раз, по шкале Саати 1-9 "
        "(1 — равны, 9 — значительно важнее), опираясь на то, как пользователь расставил "
        "акценты в своём запросе.\n"
        "Ответь СТРОГО JSON без пояснений вокруг, формата: "
        '{"критерии": ["тема: ...", "..."], '
        '"сравнения": [{"a": "критерий1", "b": "критерий2", "value": 3}, ...]}\n'
        "В \"сравнения\" value > 1 означает, что a важнее b во столько раз; value < 1 "
        "(например 1/3) — что b важнее. Названия критериев в \"сравнения\" должны "
        "буквально совпадать со строками из \"критерии\".\n\n"
        f"Запрос пользователя: {query}"
    )

    try:
        text, _usage = generate(prompt)
    except GeminiError as exc:
        print(f"[ai_metadata] критерии не получены: {exc}")
        return None

    payload = _extract_json(text)
    if payload is None:
        return None

    names = [str(name).strip() for name in payload.get("критерии", []) if str(name).strip()]
    if not names:
        return None

    valid = set(names)
    judgments: dict[tuple[str, str], float] = {}
    for item in payload.get("сравнения", []):
        a, b, value = item.get("a"), item.get("b"), item.get("value")
        if a in valid and b in valid and a != b and isinstance(value, (int, float)) and value > 0:
            judgments[(a, b)] = float(value)

    return names, judgments


def suggest_book_recommendations(
    query: str, criteria: list[str], count: int = 5
) -> list[dict] | None:
    if not query.strip() or not criteria:
        return None

    prompt = (
        f"Посоветуй {count} реальных существующих книг под запрос пользователя. "
        f"Для каждой книги оцени её по каждому из критериев числом от 0 до 10 "
        "(0 — совсем не соответствует, 10 — полностью соответствует) и дай короткое "
        "описание в 1-2 предложения, почему она подходит под запрос.\n"
        f"Критерии: {', '.join(criteria)}.\n"
        "Ответь СТРОГО JSON-массивом без пояснений вокруг, формата: "
        '[{"название": "...", "автор": "...", "описание": "...", '
        '"оценки": {"критерий1": 7, "критерий2": 4}}, ...]\n'
        "Ключи в \"оценки\" должны буквально совпадать с названиями критериев.\n\n"
        f"Запрос пользователя: {query}"
    )

    try:
        text, _usage = generate(prompt)
    except GeminiError as exc:
        print(f"[ai_metadata] рекомендации не получены: {exc}")
        return None

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        print(f"[ai_metadata] не удалось найти JSON-массив в ответе: {text!r}")
        return None

    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        print(f"[ai_metadata] не удалось разобрать JSON ответа: {exc}")
        return None

    candidates = []
    for item in items:
        title = str(item.get("название", "")).strip()
        if not title:
            continue
        scores = {
            name: max(0.0, min(10.0, float(value)))
            for name, value in item.get("оценки", {}).items()
            if name in criteria and isinstance(value, (int, float))
        }
        candidates.append(
            {
                "title": title,
                "author": str(item.get("автор", "")).strip() or None,
                "description": str(item.get("описание", "")).strip(),
                "scores": scores,
            }
        )

    return candidates or None


def expert_judgments_and_scores(
    criteria: list[str], alternatives: list[str], problem_statement: str
) -> dict | None:
    if not criteria or not alternatives:
        return None

    prompt = (
        f"Ты выступаешь экспертом при принятии решения: {problem_statement or 'выбор лучшей альтернативы'}.\n"
        f"Критерии: {', '.join(criteria)}.\n"
        f"Альтернативы: {', '.join(alternatives)}.\n"
        "Сначала сравни критерии попарно по шкале Саати 1-9 (1 — равны по важности, "
        "9 — значительно важнее), затем оцени каждую альтернативу по каждому критерию "
        "числом от 0 до 10.\n"
        "Ответь СТРОГО JSON без пояснений вокруг, формата: "
        '{"сравнения": [{"a": "критерий1", "b": "критерий2", "value": 3}, ...], '
        '"оценки": {"альтернатива1": {"критерий1": 7, "критерий2": 4}, ...}}\n'
        "Названия критериев и альтернатив должны буквально совпадать с переданными."
    )

    try:
        text, _usage = generate(prompt)
    except GeminiError as exc:
        print(f"[ai_metadata] Gemini-эксперт не ответил: {exc}")
        return None

    payload = _extract_json(text)
    if payload is None:
        return None

    valid_criteria = set(criteria)
    valid_alternatives = set(alternatives)

    judgments: dict[tuple[str, str], float] = {}
    for item in payload.get("сравнения", []):
        a, b, value = item.get("a"), item.get("b"), item.get("value")
        if a in valid_criteria and b in valid_criteria and a != b and isinstance(value, (int, float)) and value > 0:
            judgments[(a, b)] = float(value)

    scores: dict[str, dict[str, float]] = {}
    for alt, by_criterion in payload.get("оценки", {}).items():
        if alt not in valid_alternatives or not isinstance(by_criterion, dict):
            continue
        scores[alt] = {
            name: max(0.0, min(10.0, float(value)))
            for name, value in by_criterion.items()
            if name in valid_criteria and isinstance(value, (int, float))
        }

    if not judgments and not scores:
        return None
    return {"judgments": judgments, "scores": scores}
