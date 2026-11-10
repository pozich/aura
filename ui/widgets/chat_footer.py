from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from core.gemini_worker import ask_gemini_async

EXPANDED_LIST_HEIGHT = 220
HISTORY_LIMIT = 12
SYSTEM_PROMPT = (
    "Ты — ассистент по книгам в приложении для чтения. Отвечай на русском, кратко и по делу."
)


class ChatFooter(QFrame):
    """Футер чата — закреплён снизу ПОД областью экрана (не floating), во всю ширину окна,
    виден на любом экране. Свёрнут — одна строка ввода; разворачивается в короткую историю
    сообщений над ней. Делит state.msgs с полноценным экраном "Чат" — отправка здесь сразу
    видна там и наоборот. Реально дёргает Gemini в фоновом потоке и сохраняет переписку в БД."""

    message_sent = Signal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self._state = state
        self._expanded = False
        self._context: str | None = None
        self._thread = None
        self.setObjectName("ChatFooter")

        self.message_list = QListWidget()
        self.message_list.setVisible(False)
        self.message_list.setFixedHeight(EXPANDED_LIST_HEIGHT)
        self.message_list.setStyleSheet("background: transparent; border: none;")

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

        self.token_label = QLabel("Токенов за сессию: 0")
        self.token_label.setProperty("role", "muted")

        self.toggle_button = QPushButton("▴")
        self.toggle_button.setFixedSize(28, 28)
        self.toggle_button.clicked.connect(self._toggle)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Написать в чат…")
        self.input_field.returnPressed.connect(self._on_send)

        self.send_button = QPushButton("Отправить")
        self.send_button.setProperty("role", "accent")
        self.send_button.clicked.connect(self._on_send)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.addWidget(self.toggle_button)
        input_row.addWidget(self.input_field)
        input_row.addWidget(self.send_button)

        top_row = QHBoxLayout()
        top_row.addStretch()
        top_row.addWidget(self.token_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 6, 20, 10)
        layout.setSpacing(4)
        layout.addLayout(top_row)
        layout.addWidget(self.message_list)
        layout.addLayout(context_row)
        layout.addLayout(input_row)

        self._refresh()

    def _toggle(self):
        self._expanded = not self._expanded
        self.message_list.setVisible(self._expanded)
        self.toggle_button.setText("▾" if self._expanded else "▴")

    def attach_context(self, text: str):
        """Вызывается из экрана чтения при выделении текста — следующий вопрос
        в чате пойдёт вместе с этой цитатой."""
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
            return  # запрос уже летит, не дублируем
        text = self.input_field.text().strip()
        if not text:
            return

        from data.db import add_chat_message

        add_chat_message("user", text)
        self._state.msgs.append({"text": text, "me": True})
        self.input_field.clear()
        self._refresh()
        self.message_sent.emit()

        prompt = self._build_prompt(text)
        context = self._context
        self.clear_context()

        self.send_button.setEnabled(False)
        self.input_field.setEnabled(False)
        self._thinking_item = QListWidgetItem("ИИ печатает…")
        self.message_list.addItem(self._thinking_item)
        self.message_list.scrollToBottom()

        self._thread = ask_gemini_async(
            prompt, self._on_reply, self._on_error, parent=self
        )
        self._pending_context = context

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

    def _on_reply(self, text: str, usage: dict):
        self._thread = None
        self._remove_thinking_item()

        from data.db import add_chat_message

        reply = text.strip()
        add_chat_message("assistant", reply)
        self._state.msgs.append({"text": reply, "me": False})
        self._state.add_token_usage(usage.get("total_tokens", 0))
        self._refresh()
        self._update_token_label()
        self.message_sent.emit()

        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def _on_error(self, message: str):
        self._thread = None
        self._remove_thinking_item()
        self.message_list.addItem(f"⚠ {message}")
        self.message_list.scrollToBottom()
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)

    def _remove_thinking_item(self):
        item = getattr(self, "_thinking_item", None)
        if item is not None:
            row = self.message_list.row(item)
            if row != -1:
                self.message_list.takeItem(row)
            self._thinking_item = None

    def refresh(self):
        self._refresh()
        self._update_token_label()

    def _refresh(self):
        self.message_list.clear()
        for msg in self._state.msgs:
            prefix = "Вы: " if msg.get("me") else "ИИ: "
            self.message_list.addItem(prefix + msg["text"])
        if self.message_list.count():
            self.message_list.scrollToBottom()

    def _update_token_label(self):
        self.token_label.setText(f"Токенов за сессию: {self._state.token_usage}")

    def focus_input(self):
        self.input_field.setFocus()
