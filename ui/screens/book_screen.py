from __future__ import annotations

import html

from PySide6.QtCore import Qt, Signal
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

from ui.widgets.icon_button import CircleIconButton


def _build_html(chapters, book_title: str, *, font_family: str, font_size: int, text_color: str) -> str:
    """Текст раньше растягивался на всю ширину окна тонкими строками без просветов
    между абзацами — выглядело как "полоски", а не страница книги. Тут: читаемая
    колонка по центру (а не во всю ширину), отступ между абзацами и увеличенный
    line-height для плотности, красная строка как в настоящей книге.

    font_family/font_size/text_color приходят из Настроек (а не прибиты гвоздями) —
    это единственное место, где выбор шрифта/темы реально что-то читает: в отличие
    от хрома приложения, текст книги верстается вручную через HTML, а не через общий
    QSS-каскад."""
    # Двойные кавычки вокруг имени шрифта обязательны: весь style — в одинарных
    # ('...'), и font-family:'Georgia' тут же обрывал бы style на первой же '.
    style = f'font-family:"{font_family}"; font-size:{font_size}px; line-height:1.8; color:{text_color};'
    if not chapters:
        title = html.escape(book_title)
        return (
            f"<div style='max-width:760px; margin:0 auto; padding:48px 24px 160px 24px; {style}'>"
            f"<h2>{title}</h2><p>(текст книги появится здесь, когда будет готов импорт)</p></div>"
        )

    parts = []
    for row in chapters:
        title = html.escape(row["title"] or "")
        parts.append(
            f"<h2 style='margin:40px 0 20px 0; font-size:{font_size + 6}px; font-weight:600;'>{title}</h2>"
        )
        for p in (row["text"] or "").split("\n\n"):
            p = p.strip()
            if not p:
                continue
            parts.append(f"<p style='margin:0 0 20px 0; text-indent:28px;'>{html.escape(p)}</p>")

    return (
        f"<div style='max-width:760px; margin:0 auto; padding:48px 24px 160px 24px; {style}'>"
        f"{''.join(parts)}</div>"
    )


class GradientFade(QWidget):
    """Текст не обрывается резкой границей под инфо-плашкой, а гаснет градиентом —
    чисто декоративный слой, клики должны проходить сквозь него к QTextEdit под ним.
    Цвет, в который гаснет текст, — фон ТЕКУЩЕЙ темы, а не прибитый гвоздями navy,
    иначе на светлой теме (Крем) затухание шло бы в чужой тёмный цвет."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bg = QColor("#000000")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_bg_color(self, bg_color: str):
        self._bg = QColor(bg_color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        transparent = QColor(self._bg)
        transparent.setAlpha(0)
        mid = QColor(self._bg)
        mid.setAlpha(180)
        solid = QColor(self._bg)
        solid.setAlpha(255)
        gradient.setColorAt(0.0, transparent)
        gradient.setColorAt(0.55, mid)
        gradient.setColorAt(1.0, solid)
        painter.fillRect(self.rect(), gradient)


class InfoPill(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoPill")

    def set_bg_color(self, bg_color: str):
        c = QColor(bg_color)
        r, g, b, _ = c.getRgb()
        self.setStyleSheet(
            f"QFrame#InfoPill {{ background-color: rgba({r}, {g}, {b}, 0.95);"
            " border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 18px; }"
        )


class BookScreen(QWidget):
    context_requested = Signal(str)

    def __init__(self, book, parent=None):
        super().__init__(parent)
        from data.db import get_reading_progress, set_reading_progress

        self.book = book
        self._set_reading_progress = set_reading_progress
        self.page = get_reading_progress(book.id) or 1

        self.book_content = QTextEdit(self)
        self.book_content.setReadOnly(True)
        self.book_content.setFrameShape(QFrame.Shape.NoFrame)
        self.gradient = GradientFade(self)
        self.pill = InfoPill(self)

        pill_layout = QHBoxLayout(self.pill)
        pill_layout.setContentsMargins(16, 8, 16, 8)
        pill_layout.setSpacing(8)

        prev_button = CircleIconButton("prev", size=32)
        prev_button.clicked.connect(self._on_prev)
        next_button = CircleIconButton("next", size=32)
        next_button.clicked.connect(self._on_next)

        self.page_label = QLabel()
        self.page_label.setProperty("role", "muted")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, max(book.pages or 1, 1))
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(80)

        ask_button = QPushButton("Спросить в чате")
        ask_button.clicked.connect(self._on_ask_in_chat)

        self.exit_button = QPushButton("Выйти")

        pill_layout.addWidget(prev_button)
        pill_layout.addWidget(self.page_label)
        pill_layout.addWidget(next_button)
        pill_layout.addWidget(self.progress_bar)
        pill_layout.addStretch()
        pill_layout.addWidget(ask_button)
        pill_layout.addWidget(self.exit_button)

        self._apply_appearance()
        self._refresh_page_label()

    def _apply_appearance(self):
        """Тема/шрифт книги — те же, что выбраны в Настройках. Раньше читались
        только один раз в __init__, и уже открытая вкладка книги не замечала смену
        настроек, пока её явно не закрыть и не открыть заново — теперь это же
        применяется и из refresh_appearance(), которую дёргает MainWindow по сигналу
        из Настроек, так что открытая вкладка обновляется сразу, без переоткрытия."""
        from data.app_settings import load_settings
        from data.db import list_chapters
        from ui.styles import resolve_font_family, text_primary_for, theme_colors

        settings = load_settings()
        bg_color = theme_colors(settings["theme"])["bg"]
        text_color = text_primary_for(settings["theme"])
        font_family = resolve_font_family(settings["font_family"])
        font_size = settings["font_size"]

        self.book_content.setStyleSheet(f"QTextEdit {{ background-color: {bg_color}; border: none; }}")
        chapters = list_chapters(self.book.id)
        # setHtml() сбросил бы скролл на начало книги — запоминаем позицию и
        # восстанавливаем её сразу после, иначе смена шрифта посреди чтения
        # перебрасывала бы читателя на первую страницу.
        scrollbar = self.book_content.verticalScrollBar()
        scroll_pos = scrollbar.value()
        self.book_content.setHtml(
            _build_html(chapters, self.book.title, font_family=font_family, font_size=font_size, text_color=text_color)
        )
        scrollbar.setValue(scroll_pos)
        self.gradient.set_bg_color(bg_color)
        self.pill.set_bg_color(bg_color)

    def refresh_appearance(self):
        self._apply_appearance()

    def set_exit_handler(self, handler):
        self.exit_button.clicked.connect(handler)

    def _on_ask_in_chat(self):
        selected = self.book_content.textCursor().selectedText()
        selected = selected.replace(" ", "\n").strip()  # QTextCursor хранит абзацы так
        if selected:
            self.context_requested.emit(selected)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()

        self.book_content.setGeometry(0, 0, w, h)

        pill_hint = self.pill.sizeHint()
        pill_w, pill_h = pill_hint.width(), pill_hint.height()
        margin_bottom = 20
        self.pill.setGeometry(
            w // 2 - pill_w // 2, h - pill_h - margin_bottom, pill_w, pill_h
        )

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
