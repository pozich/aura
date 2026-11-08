from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QListWidget, QPushButton, QVBoxLayout

EXPANDED_LIST_HEIGHT = 220


class ChatFooter(QFrame):
    """Футер чата — закреплён снизу ПОД областью экрана (не floating), во всю ширину окна,
    виден на любом экране. Свёрнут — одна строка ввода; разворачивается в короткую историю
    сообщений над ней. Делит state.msgs с полноценным экраном "Чат" — отправка здесь сразу
    видна там и наоборот."""

    message_sent = Signal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self._state = state
        self._expanded = False
        self.setObjectName("ChatFooter")

        self.message_list = QListWidget()
        self.message_list.setVisible(False)
        self.message_list.setFixedHeight(EXPANDED_LIST_HEIGHT)
        self.message_list.setStyleSheet("background: transparent; border: none;")

        self.toggle_button = QPushButton("▴")
        self.toggle_button.setFixedSize(28, 28)
        self.toggle_button.clicked.connect(self._toggle)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Написать в чат…")
        self.input_field.returnPressed.connect(self._on_send)

        send_button = QPushButton("Отправить")
        send_button.setProperty("role", "accent")
        send_button.clicked.connect(self._on_send)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.addWidget(self.toggle_button)
        input_row.addWidget(self.input_field)
        input_row.addWidget(send_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(8)
        layout.addWidget(self.message_list)
        layout.addLayout(input_row)

        self._refresh()

    def _toggle(self):
        self._expanded = not self._expanded
        self.message_list.setVisible(self._expanded)
        self.toggle_button.setText("▾" if self._expanded else "▴")

    def _on_send(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self._state.msgs.append({"text": text, "me": True})
        self.input_field.clear()
        self._refresh()
        self.message_sent.emit()

    def refresh(self):
        self._refresh()

    def _refresh(self):
        self.message_list.clear()
        for msg in self._state.msgs:
            prefix = "Вы: " if msg.get("me") else "ИИ: "
            self.message_list.addItem(prefix + msg["text"])
        if self.message_list.count():
            self.message_list.scrollToBottom()

    def focus_input(self):
        self.input_field.setFocus()
