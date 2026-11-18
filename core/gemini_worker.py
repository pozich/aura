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
    thread = RecommendationsThread(parent)
    thread.succeeded.connect(on_success)
    thread.failed.connect(on_error)
    thread.start()
    return thread


class ExpertJudgmentThread(QThread):
    succeeded = Signal(dict)
    failed = Signal(str)

    def __init__(self, criteria: list[str], alternatives: list[str], problem_statement: str, parent=None):
        super().__init__(parent)
        self._criteria = criteria
        self._alternatives = alternatives
        self._problem_statement = problem_statement

    def run(self):
        from core.ai_metadata import expert_judgments_and_scores

        try:
            result = expert_judgments_and_scores(self._criteria, self._alternatives, self._problem_statement)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result or {})


def ask_expert_judgment_async(
    criteria: list[str], alternatives: list[str], problem_statement: str, on_success, on_error, parent=None
):
    thread = ExpertJudgmentThread(criteria, alternatives, problem_statement, parent)
    thread.succeeded.connect(on_success)
    thread.failed.connect(on_error)
    thread.start()
    return thread
