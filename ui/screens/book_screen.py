from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QWidget,
)


class GradientFade(QWidget):
    """Текст не обрывается резкой границей под инфо-плашкой, а гаснет градиентом —
    чисто декоративный слой, клики должны проходить сквозь него к QTextEdit под ним."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(15, 23, 42, 0))
        gradient.setColorAt(0.55, QColor(15, 23, 42, 180))
        gradient.setColorAt(1.0, QColor(15, 23, 42, 255))
        painter.fillRect(self.rect(), gradient)


class InfoPill(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoPill")
        self.setStyleSheet(
            "QFrame#InfoPill { background-color: rgba(15, 23, 42, 0.95);"
            " border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 18px; }"
        )


class BookScreen(QWidget):
    def __init__(self, book, parent=None):
        super().__init__(parent)
        from data.db import get_reading_progress, set_reading_progress

        self.book = book
        self._set_reading_progress = set_reading_progress
        self.page = get_reading_progress(book.id) or 1

        self.book_content = QTextEdit(self)
        self.book_content.setReadOnly(True)
        self.book_content.setFrameShape(QFrame.Shape.NoFrame)
        self.book_content.setStyleSheet(
            "QTextEdit { background-color: #0f172a; border: none;"
            " font-family: Georgia, serif; font-size: 17px; padding: 28px; }"
        )
        self.book_content.setPlainText(
            f"{book.title}\n\n(текст книги появится здесь, когда будет готов импорт)"
        )

        self.gradient = GradientFade(self)

        self.pill = InfoPill(self)
        pill_layout = QHBoxLayout(self.pill)
        pill_layout.setContentsMargins(16, 8, 16, 8)
        pill_layout.setSpacing(10)

        prev_button = QPushButton("←")
        prev_button.setFixedSize(32, 32)
        prev_button.clicked.connect(self._on_prev)
        next_button = QPushButton("→")
        next_button.setFixedSize(32, 32)
        next_button.clicked.connect(self._on_next)

        self.page_label = QLabel()
        self.page_label.setProperty("role", "muted")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, max(book.pages or 1, 1))
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(100)

        self.exit_button = QPushButton("Выйти")

        pill_layout.addWidget(prev_button)
        pill_layout.addWidget(self.page_label)
        pill_layout.addWidget(next_button)
        pill_layout.addWidget(self.progress_bar)
        pill_layout.addStretch()
        pill_layout.addWidget(self.exit_button)

        self._refresh_page_label()

    def set_exit_handler(self, handler):
        self.exit_button.clicked.connect(handler)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()

        self.book_content.setGeometry(0, 0, w, h)

        pill_w, pill_h = 440, 56
        margin_bottom = 20
        self.pill.setGeometry(w // 2 - pill_w // 2, h - pill_h - margin_bottom, pill_w, pill_h)

        gradient_h = 140
        self.gradient.setGeometry(0, h - gradient_h, w, gradient_h)

        self.gradient.raise_()
        self.pill.raise_()

    def _refresh_page_label(self):
        total = self.book.pages or "?"
        self.page_label.setText(f"стр. {self.page} из {total}")
        self.progress_bar.setValue(min(self.page, self.progress_bar.maximum()))

    def _on_prev(self):
        if self.page > 1:
            self.page -= 1
            self._set_reading_progress(self.book.id, self.page)
            self._refresh_page_label()

    def _on_next(self):
        self.page += 1
        self._set_reading_progress(self.book.id, self.page)
        self._refresh_page_label()
