from __future__ import annotations

from PySide6.QtCore import QThread, Signal


class GeminiThread(QThread):
    succeeded = Signal(str, dict)
    failed = Signal(str)

    def __init__(self, prompt: str, model: str | None = None, parent=None):
        super().__init__(parent)
        self._prompt = prompt
        self._model = model

    def run(self):
        from core.gemini_client import DEFAULT_MODEL, GeminiError, generate

        try:
            text, usage = generate(self._prompt, model=self._model or DEFAULT_MODEL)
        except GeminiError as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(text, usage)


def ask_gemini_async(prompt: str, on_success, on_error, model: str | None = None, parent=None):
    """Запускает запрос к Gemini в фоновом потоке — блокирующий сетевой вызов не должен
    морозить интерфейс на несколько секунд. on_success(text, usage) и on_error(message)
    вызываются уже в основном потоке (через сигналы Qt, это безопасно). Вызывающая
    сторона ОБЯЗАНА держать возвращённый QThread в поле экземпляра (не в локальной
    переменной) — иначе Python может собрать его сборщиком мусора до завершения потока."""
    thread = GeminiThread(prompt, model, parent)
    thread.succeeded.connect(on_success)
    thread.failed.connect(on_error)
    thread.start()
    return thread
