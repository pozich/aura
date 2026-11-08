from __future__ import annotations

from PySide6.QtWidgets import QListWidget, QVBoxLayout, QWidget


class ChatScreen(QWidget):
    """Только история сообщений — ввод живёт в ChatFooter (виден на всех экранах),
    дублировать поле ввода здесь не нужно."""

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self._state = state

        self.message_list = QListWidget()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.addWidget(self.message_list)

        self.refresh()

    def refresh(self):
        self.message_list.clear()
        for msg in self._state.msgs:
            prefix = "Вы: " if msg.get("me") else "ИИ: "
            self.message_list.addItem(prefix + msg["text"])
        if self.message_list.count():
            self.message_list.scrollToBottom()
