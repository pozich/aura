from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.styles import hue_for
from ui.widgets.carousel import Carousel
from ui.widgets.icon_button import CircleIconButton


class CategoryStripItem(QPushButton):
    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(190)
        self._active = False
        self._apply_style()

    def set_active(self, active: bool):
        self._active = active
        self._apply_style()

    def _apply_style(self):
        if self._active:
            self.setStyleSheet(
                "QPushButton { background: transparent; border: none; color: white;"
                " font-family: Georgia, serif; font-size: 17px; }"
            )
        else:
            self.setStyleSheet(
                "QPushButton { background: transparent; border: none; color: #475569;"
                " font-family: Georgia, serif; font-size: 13px; }"
            )


class BookCard(QFrame):
    clicked = Signal(int)
    category_set = Signal(int, object)
    delete_requested = Signal(int)

    ACTIVE_SIZE = (190, 280)
    SIDE_SIZE = (150, 220)

    def __init__(self, book, categories: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.book_id = book.id
        self._categories = categories or []
        self._cover_path = book.cover_path
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.cover_label = QLabel(self)
        self.cover_label.setScaledContents(True)

        self.title_label = QLabel(book.title, self)
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(
            "font-family: Georgia, serif; font-size: 17px; color: white; background: transparent;"
        )

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.title_label)
        layout.addStretch()

        self.tag_button = CircleIconButton("tag", size=24, parent=self)
        self.tag_button.clicked.connect(self._open_category_menu)

        self.delete_button = CircleIconButton("close", size=22, parent=self)
        self.delete_button.clicked.connect(lambda: self.delete_requested.emit(self.book_id))

        self._active = False
        self._apply_style()

    def set_categories(self, categories: list[str]):
        self._categories = categories

    def set_active(self, active: bool):
        self._active = active
        self._apply_style()

    def _apply_style(self):
        size = self.ACTIVE_SIZE if self._active else self.SIDE_SIZE
        self.setFixedSize(*size)
        border = "border: 3px solid #60a5fa;" if self._active else "border: none;"

        has_cover = bool(self._cover_path) and Path(self._cover_path).exists()
        if has_cover:
            self.cover_label.setGeometry(0, 0, *size)
            self.cover_label.setPixmap(QPixmap(self._cover_path))
            self.cover_label.setStyleSheet(f"border-radius: 12px; {border}")
            self.cover_label.lower()
            self.title_label.setVisible(False)
            self.setStyleSheet(f"QFrame {{ border-radius: 12px; {border} }}")
        else:
            self.cover_label.clear()
            self.cover_label.setGeometry(0, 0, 0, 0)
            self.title_label.setVisible(True)
            self.setStyleSheet(
                f"QFrame {{ background-color: {hue_for(self.book_id)}; border-radius: 12px; {border} }}"
            )

        self.tag_button.move(8, size[1] - 32)
        self.delete_button.move(size[0] - 30, 8)

    def _open_category_menu(self):
        menu = QMenu(self)
        none_action = menu.addAction("Без категории")
        none_action.triggered.connect(lambda: self.category_set.emit(self.book_id, None))
        for name in self._categories:
            action = menu.addAction(name)
            action.triggered.connect(
                lambda checked=False, n=name: self.category_set.emit(self.book_id, n)
            )
        menu.exec(self.tag_button.mapToGlobal(self.tag_button.rect().bottomLeft()))

    def mousePressEvent(self, event):
        self.clicked.emit(self.book_id)
        super().mousePressEvent(event)


class LibraryScreen(QWidget):

    book_opened = Signal(int)
    book_deleted = Signal(int)

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._state = None
        self._active_category: str | None = None
        self._books: list = []

        self.category_carousel = Carousel(slot_width=190, height=44)
        self.category_carousel.setVisible(False)

        self.book_carousel = Carousel(slot_width=230, height=300)

        self.author_label = QLabel()
        self.author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.author_label.setProperty("role", "muted")

        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-family: Georgia, serif; font-size: 22px;")

        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setProperty("role", "muted")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(360)

        self.read_button = QPushButton("Читать")
        self.read_button.setProperty("role", "accent")
        self.read_button.clicked.connect(self._on_read_clicked)

        progress_row = QHBoxLayout()
        progress_row.addStretch()
        progress_row.addWidget(self.progress_bar)
        progress_row.addStretch()

        read_row = QHBoxLayout()
        read_row.addStretch()
        read_row.addWidget(self.read_button)
        read_row.addStretch()

        info_panel = QVBoxLayout()
        info_panel.setSpacing(6)
        info_panel.addWidget(self.author_label)
        info_panel.addWidget(self.title_label)
        info_panel.addWidget(self.info_label)
        info_panel.addLayout(progress_row)
        info_panel.addLayout(read_row)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 16, 0, 0)
        main_layout.addWidget(self.category_carousel)
        main_layout.addWidget(self.book_carousel)
        main_layout.addLayout(info_panel)
        main_layout.addStretch()

    def refresh(self, state):
        self._state = state
        self._rebuild_categories()
        self._rebuild_cards()

    def _rebuild_categories(self):
        names = self._state.all_category_names()
        show_strip = len(names) > 1
        self.category_carousel.setVisible(show_strip)

        if not show_strip:
            self._active_category = None
            return

        if self._active_category not in names:
            self._active_category = names[0]

        items = []
        for name in names:
            item = CategoryStripItem(name)
            item.set_active(name == self._active_category)
            item.clicked.connect(lambda _checked=False, n=name: self._on_category_selected(n))
            items.append(item)
        self.category_carousel.set_items(items)
        self.category_carousel.set_index(names.index(self._active_category), animate=False)

    def _on_category_selected(self, name: str):
        if name == self._active_category:
            return
        self._active_category = name
        self._rebuild_categories()
        self._rebuild_cards()

    def _visible_books(self):
        if self._active_category is None:
            return list(self._state.books)
        return self._state.books_in_category(self._active_category)

    def _rebuild_cards(self):
        self._books = self._visible_books()
        categories = self._state.all_category_names()

        cards = []
        for book in self._books:
            card = BookCard(book, categories)
            card.clicked.connect(self._on_card_clicked)
            card.category_set.connect(self._on_category_set)
            card.delete_requested.connect(self._on_delete_book)
            cards.append(card)
        self.book_carousel.set_items(cards)
        self._update_selection_style()
        self._update_info_panel()

    def _on_card_clicked(self, book_id: int):
        index = next((k for k, b in enumerate(self._books) if b.id == book_id), None)
        if index is None:
            return
        if index == self.book_carousel.index():
            self.book_opened.emit(book_id)
            return
        self.book_carousel.set_index(index)
        self._update_selection_style()
        self._update_info_panel()

    def _on_category_set(self, book_id: int, category_name: str | None):
        category_id = None
        if category_name is not None:
            category = next((c for c in self._state.categories if c.name == category_name), None)
            category_id = category.id if category else None
        self._state.set_book_category(book_id, category_id)
        self._rebuild_categories()
        self._rebuild_cards()

    def _on_delete_book(self, book_id: int):
        from PySide6.QtWidgets import QMessageBox
        from data.db import delete_book

        book = self._state.book_by_id(book_id)
        title = book.title if book else "эту книгу"
        reply = QMessageBox.question(
            self,
            "Удалить книгу?",
            f'"{title}" и весь прогресс чтения будут удалены без возможности восстановления. Продолжить?',
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        delete_book(book_id)
        self._state.load_books()
        self.book_deleted.emit(book_id)
        self._rebuild_cards()

    def _update_selection_style(self):
        active_index = self.book_carousel.index()
        for k, card in enumerate(self.book_carousel.items()):
            card.set_active(k == active_index)

    def _update_info_panel(self):
        index = self.book_carousel.index()
        book = self._books[index] if self._books else None
        if book is None:
            self.author_label.setText("")
            self.title_label.setText("Библиотека пуста")
            self.info_label.setText("Добавь книгу в Хранилище")
            self.progress_bar.setValue(0)
            return

        from data.db import get_reading_progress

        self.author_label.setText(book.author or "")
        self.title_label.setText(book.title)
        pages = book.pages or 0
        page = get_reading_progress(book.id) or 0
        percent = int(100 * page / pages) if pages else 0
        pages_text = f"{pages} стр." if pages else "страниц не указано"
        self.info_label.setText(f"{pages_text} · прочитано {page} ({percent}%)")
        self.progress_bar.setValue(percent)

    def _on_read_clicked(self):
        if self._books:
            self.book_opened.emit(self._books[self.book_carousel.index()].id)

    def keyPressEvent(self, event):
        from data.keybindings import matches

        keys = self._state.keys if self._state else {}
        names = self._state.all_category_names() if self._state else []

        if matches(event, "library_prev_book", keys):
            self.book_carousel.set_index(self.book_carousel.index() - 1)
            self._update_selection_style()
            self._update_info_panel()
        elif matches(event, "library_next_book", keys):
            self.book_carousel.set_index(self.book_carousel.index() + 1)
            self._update_selection_style()
            self._update_info_panel()
        elif matches(event, "library_prev_category", keys) and self._active_category in names:
            idx = max(0, names.index(self._active_category) - 1)
            self._on_category_selected(names[idx])
        elif matches(event, "library_next_category", keys) and self._active_category in names:
            idx = min(len(names) - 1, names.index(self._active_category) + 1)
            self._on_category_selected(names[idx])
        elif matches(event, "library_open", keys):
            self._on_read_clicked()
        else:
            super().keyPressEvent(event)
