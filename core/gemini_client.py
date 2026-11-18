from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from data.db import list_api_keys

DEFAULT_MODEL = "gemini-3.1-flash-lite"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiError(Exception):
    pass


def active_api_key() -> str | None:
    for row in list_api_keys():
        if row["is_active"]:
            key = (row["key"] or "").strip()
            return key or None
    return None


def generate(prompt: str, model: str = DEFAULT_MODEL, api_key: str | None = None) -> tuple[str, dict]:
    api_key = api_key or active_api_key()
    if not api_key:
        raise GeminiError(
            "Нет активного API-ключа. Настройки → API-ключи → дважды кликни по нужному,"
            " чтобы сделать его активным."
        )
    if not api_key.isascii():
        raise GeminiError("Ключ содержит недопустимые символы — это не похоже на настоящий ключ Gemini.")

    url = f"{API_URL.format(model=model)}?key={urllib.parse.quote(api_key, safe='')}"
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
    except (UnicodeError, ValueError) as exc:
        raise GeminiError(f"Некорректный ключ или запрос: {exc}") from exc
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

    from core.usage_tracker import log_call

    log_call(model, tokens=usage["total_tokens"])

    return text, usage
