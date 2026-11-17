from __future__ import annotations

from PySide6.QtWidgets import QFrame, QTextEdit, QVBoxLayout, QWidget

from ui.widgets.chat_render import build_chat_html


class ChatScreen(QWidget):
    """Только история сообщений — ввод живёт в ChatFooter (виден на всех экранах),
    дублировать поле ввода здесь не нужно."""

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self._state = state

        self.message_view = QTextEdit()
        self.message_view.setReadOnly(True)
        self.message_view.setFrameStyle(QFrame.Shape.NoFrame)
        self.message_view.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.addWidget(self.message_view)

        self.refresh()

    def refresh(self):
        from data.app_settings import load_settings
        from ui.styles import resolve_font_family

        settings = load_settings()
        self.message_view.setHtml(
            build_chat_html(
                self._state.msgs,
                theme_id=settings["theme"],
                font_family=resolve_font_family(settings["font_family"]),
                font_size=settings["font_size"],
            )
        )
        scrollbar = self.message_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def refresh_appearance(self):
        self.refresh()
