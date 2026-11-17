from __future__ import annotations

from PySide6.QtCore import QThread, Signal


class GeminiThread(QThread):
    succeeded = Signal(str, dict)
    failed = Signal(str)

    def __init__(self, prompt: str, model: str | None = None, api_key: str | None = None, parent=None):
        super().__init__(parent)
        self._prompt = prompt
        self._model = model
        self._api_key = api_key

    def run(self):
        from core.gemini_client import DEFAULT_MODEL, GeminiError, generate

        try:
            text, usage = generate(self._prompt, model=self._model or DEFAULT_MODEL, api_key=self._api_key)
        except GeminiError as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(text, usage)


def ask_gemini_async(prompt: str, on_success, on_error, model: str | None = None, api_key: str | None = None, parent=None):
    """Запускает запрос к Gemini в фоновом потоке — блокирующий сетевой вызов не должен
    морозить интерфейс на несколько секунд. on_success(text, usage) и on_error(message)
    вызываются уже в основном потоке (через сигналы Qt, это безопасно). Вызывающая
    сторона ОБЯЗАНА держать возвращённый QThread в поле экземпляра (не в локальной
    переменной) — иначе Python может собрать его сборщиком мусора до завершения потока.

    api_key — проверить конкретный ключ (например, ещё не сохранённый), а не тот,
    что сейчас активен в БД."""
    thread = GeminiThread(prompt, model, api_key, parent)
    thread.succeeded.connect(on_success)
    thread.failed.connect(on_error)
    thread.start()
    return thread


class MagicQueryThread(QThread):
    succeeded = Signal(list)
    failed = Signal(str)

    def __init__(self, query: str, parent=None):
        super().__init__(parent)
        self._query = query

    def run(self):
        from core.ahp_pipeline import magic_query

        try:
            results = magic_query(self._query)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(results)


def ask_magic_query_async(query: str, on_success, on_error, parent=None):
    """Как ask_gemini_async, но для core.ahp_pipeline.magic_query — подбора книг по
    АХП-критериям, извлечённым из свободного текста запроса. Пайплайн сам делает два
    последовательных сетевых вызова, поэтому целиком уходит в фоновый поток.
    on_success(results) получает список кандидатов (может быть пустым, если Gemini
    не дал разборчивого ответа), on_error(message) — только на неожиданный сбой."""
    thread = MagicQueryThread(query, parent)
    thread.succeeded.connect(on_success)
    thread.failed.connect(on_error)
    thread.start()
    return thread


class RecommendationsThread(QThread):
    succeeded = Signal(list)
    failed = Signal(str)

    def run(self):
        from core.recommendations import recompute_library_recommendations

        try:
            results = recompute_library_recommendations()
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(results)


def ask_recommendations_async(on_success, on_error, parent=None):
    """Пересчитывает блок "вам может понравиться" в фоне — вызывается при
    добавлении/удалении книги (ui/main_window.py), не при каждом открытии экрана
    Библиотеки. on_success(results) получает новый список (может быть пустым),
    on_error(message) — только на неожиданный сбой; обычные "нет ключа"/"Gemini не
    ответил" внутри core.recommendations просто дают пустой результат."""
    thread = RecommendationsThread(parent)
    thread.succeeded.connect(on_success)
    thread.failed.connect(on_error)
    thread.start()
    return thread
