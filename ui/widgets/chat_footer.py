from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from core.gemini_worker import ask_gemini_async, ask_magic_query_async
from ui.widgets.chat_render import build_chat_html

EXPANDED_LIST_HEIGHT = 220
HISTORY_LIMIT = 12
SYSTEM_PROMPT = (
    "Ты — ассистент по книгам в приложении для чтения. Отвечай на русском, кратко и по делу."
)


class ChatFooter(QFrame):
    message_sent = Signal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self._state = state
        self._expanded = False
        self._context: str | None = None
        self._thread = None
        self._status: str | None = None
        self._status_is_error = False
        self.setObjectName("ChatFooter")

        self.message_view = QTextEdit()
        self.message_view.setReadOnly(True)
        self.message_view.setVisible(False)
        self.message_view.setFixedHeight(EXPANDED_LIST_HEIGHT)
        self.message_view.setFrameStyle(QFrame.Shape.NoFrame)
        self.message_view.setStyleSheet("background: transparent; border: none;")

        self.context_label = QLabel()
        self.context_label.setProperty("role", "muted")
        self.context_label.setWordWrap(True)
        self.context_label.setVisible(False)

        clear_context_button = QPushButton("✕ контекст")
        clear_context_button.clicked.connect(self.clear_context)
        clear_context_button.setVisible(False)
        self._clear_context_button = clear_context_button

        context_row = QHBoxLayout()
        context_row.addWidget(self.context_label, 1)
        context_row.addWidget(clear_context_button)

        self.toggle_button = QPushButton("▴")
        self.toggle_button.setFixedSize(28, 28)
        self.toggle_button.clicked.connect(self._toggle)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Написать в чат…")
        self.input_field.returnPressed.connect(self._on_send)

        self.send_button = QPushButton("Отправить")
        self.send_button.setProperty("role", "accent")
        self.send_button.clicked.connect(self._on_send)

        self.magic_button = QPushButton("🔍 Подобрать книги")
        self.magic_button.setToolTip(
            "Описать, что хочется почитать, и получить подборку с объяснением от ИИ"
        )
        self.magic_button.clicked.connect(self._on_magic_send)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.addWidget(self.toggle_button)
        input_row.addWidget(self.input_field)
        input_row.addWidget(self.magic_button)
        input_row.addWidget(self.send_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 6, 20, 10)
        layout.setSpacing(4)
        layout.addWidget(self.message_view)
        layout.addLayout(context_row)
        layout.addLayout(input_row)

        self._refresh()

    def _toggle(self):
        self._expanded = not self._expanded
        self.message_view.setVisible(self._expanded)
        self.toggle_button.setText("▾" if self._expanded else "▴")

    def attach_context(self, text: str):
        text = text.strip()
        if not text:
            return
        self._context = text
        preview = text if len(text) <= 160 else text[:157] + "…"
        self.context_label.setText(f"Контекст: «{preview}»")
        self.context_label.setVisible(True)
        self._clear_context_button.setVisible(True)
        self.input_field.setFocus()

    def clear_context(self):
        self._context = None
        self.context_label.setVisible(False)
        self._clear_context_button.setVisible(False)

    def _on_send(self):
        if self._thread is not None:
            return
        text = self.input_field.text().strip()
        if not text:
            return

        from data.db import add_chat_message

        add_chat_message("user", text)
        self._state.msgs.append({"text": text, "me": True})
        self.input_field.clear()
        self.message_sent.emit()

        prompt = self._build_prompt(text)
        context = self._context
        self.clear_context()

        self._begin_request("ИИ печатает…")
        self._thread = ask_gemini_async(
            prompt, self._on_reply, self._on_error, parent=self
        )
        self._pending_context = context

    def _on_magic_send(self):
        if self._thread is not None:
            return
        text = self.input_field.text().strip()
        if not text:
            return

        from data.db import add_chat_message

        add_chat_message("user", text)
        self._state.msgs.append({"text": text, "me": True})
        self.input_field.clear()
        self.message_sent.emit()

        self._begin_request("ИИ подбирает книги…")
        self._thread = ask_magic_query_async(text, self._on_magic_reply, self._on_error, parent=self)

    def _on_magic_reply(self, results: list[dict]):
        self._thread = None

        from data.db import add_chat_message

        reply = self._format_magic_results(results)
        add_chat_message("assistant", reply)
        self._state.msgs.append({"text": reply, "me": False})
        self._end_request()

    @staticmethod
    def _format_magic_results(results: list[dict]) -> str:
        if not results:
            return (
                "Не удалось подобрать книги под этот запрос — попробуйте переформулировать "
                "или проверьте API-ключ в настройках."
            )

        lines = []
        for i, book in enumerate(results, start=1):
            header = f"{i}. **«{book['title']}»**"
            if book.get("author"):
                header += f" — {book['author']}"
            lines.append(header)
            if book.get("description"):
                lines.append(book["description"])
        return "\n\n".join(lines)

    def _build_prompt(self, new_message: str) -> str:
        parts = [SYSTEM_PROMPT]
        if self._context:
            parts.append(f"Цитата из книги, о которой спрашивает пользователь:\n«{self._context}»")

        history = self._state.msgs[-HISTORY_LIMIT:]
        if history:
            lines = [("Пользователь: " if m.get("me") else "Ассистент: ") + m["text"] for m in history]
            parts.append("История переписки:\n" + "\n".join(lines))

        parts.append(f"Пользователь: {new_message}")
        return "\n\n".join(parts)

    def _on_reply(self, text: str, _usage: dict):
        self._thread = None

        from data.db import add_chat_message

        reply = text.strip()
        add_chat_message("assistant", reply)
        self._state.msgs.append({"text": reply, "me": False})
        self._end_request()

    def _on_error(self, message: str):
        self._thread = None
        self._status = message
        self._status_is_error = True
        self._refresh()
        self.send_button.setEnabled(True)
        self.magic_button.setEnabled(True)
        self.input_field.setEnabled(True)

    def _begin_request(self, status: str):
        self._status = status
        self._status_is_error = False
        self._refresh()
        self.send_button.setEnabled(False)
        self.magic_button.setEnabled(False)
        self.input_field.setEnabled(False)

    def _end_request(self):
        self._status = None
        self._refresh()
        self.message_sent.emit()
        self.send_button.setEnabled(True)
        self.magic_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def _refresh(self):
        from data.app_settings import load_settings
        from ui.styles import resolve_font_family

        settings = load_settings()
        self.message_view.setHtml(
            build_chat_html(
                self._state.msgs,
                theme_id=settings["theme"],
                font_family=resolve_font_family(settings["font_family"]),
                font_size=settings["font_size"],
                status=self._status,
                status_is_error=self._status_is_error,
            )
        )
        scrollbar = self.message_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def refresh_appearance(self):
        self._refresh()

    def focus_input(self):
        self.input_field.setFocus()
