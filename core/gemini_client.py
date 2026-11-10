from __future__ import annotations

import json
import urllib.error
import urllib.request

from data.db import list_api_keys

DEFAULT_MODEL = "gemini-3.1-flash-lite"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiError(Exception):
    """Понятное сообщение о том, что именно пошло не так — чтобы не гадать вслепую,
    как с жанром, который молча не определялся без единого следа ошибки."""


def active_api_key() -> str | None:
    for row in list_api_keys():
        if row["is_active"]:
            key = (row["key"] or "").strip()
            return key or None
    return None


def generate(prompt: str, model: str = DEFAULT_MODEL) -> tuple[str, dict]:
    """Единый вызов Gemini generateContent. Возвращает (текст_ответа, usage), где
    usage — {"prompt_tokens", "response_tokens", "total_tokens"} из самого ответа API
    (не оценка, а то, что реально посчитал Gemini). Бросает GeminiError с понятной
    причиной при любой проблеме — дальше решает вызывающий код: автотег жанра просто
    печатает причину в консоль и продолжает, чат — показывает ошибку пользователю."""
    api_key = active_api_key()
    if not api_key:
        raise GeminiError(
            "Нет активного API-ключа. Настройки → API-ключи → дважды кликни по нужному,"
            " чтобы сделать его активным."
        )

    url = f"{API_URL.format(model=model)}?key={api_key}"
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise GeminiError(f"Gemini вернул ошибку {exc.code}: {body[:300]}") from exc
    except urllib.error.URLError as exc:
        raise GeminiError(f"Не удалось связаться с Gemini: {exc.reason}") from exc
    except TimeoutError as exc:
        raise GeminiError("Gemini не ответил за 30 секунд (таймаут)") from exc
    except OSError as exc:
        raise GeminiError(f"Сетевая ошибка при обращении к Gemini: {exc}") from exc

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise GeminiError(f"Неожиданный ответ Gemini: {data}") from exc

    usage_meta = data.get("usageMetadata", {})
    usage = {
        "prompt_tokens": usage_meta.get("promptTokenCount", 0),
        "response_tokens": usage_meta.get("candidatesTokenCount", 0),
        "total_tokens": usage_meta.get("totalTokenCount", 0),
    }
    return text, usage
