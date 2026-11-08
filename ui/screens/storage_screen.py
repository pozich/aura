from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.flow_layout import FlowLayout
from ui.widgets.modal import ModalOverlay

CELL_SIZE = 190
CELL_HEIGHT = 220
CELL_GAP = 20


class CategoryChip(QPushButton):
    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setProperty("role", "chip")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_active(self, active: bool):
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)


class AddTile(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(CELL_SIZE, CELL_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("AddTile")
        self._focused = False
        self._apply_style()

        label = QLabel("+", self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setGeometry(0, 0, CELL_SIZE, CELL_HEIGHT)
        label.setStyleSheet("font-size: 48px; color: rgba(255,255,255,0.4); background: transparent;")

    def set_focused(self, focused: bool):
        self._focused = focused
        self._apply_style()

    def _apply_style(self):
        border = "2px solid #60a5fa" if self._focused else "1px dashed rgba(255,255,255,0.30)"
        self.setStyleSheet(f"QFrame#AddTile {{ border: {border}; border-radius: 12px; }}")

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class NotebookCard(QFrame):
    clicked = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, notebook, parent=None):
        super().__init__(parent)
        self.notebook_id = notebook.id
        self.setObjectName("NotebookCard")
        self.setFixedSize(CELL_SIZE, CELL_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._focused = False
        self._apply_style()

        accent = QFrame(self)
        accent.setGeometry(10, 10, 3, CELL_HEIGHT - 20)
        accent.setStyleSheet("background-color: rgba(244, 114, 182, 0.5); border-radius: 1px;")

        title = QLabel(notebook.title, self)
        title.setWordWrap(True)
        title.setGeometry(22, 14, CELL_SIZE - 48, CELL_HEIGHT - 60)
        title.setStyleSheet("font-family: Georgia, serif; font-size: 16px; background: transparent;")

        hint = QLabel("✎ заметки", self)
        hint.setGeometry(22, CELL_HEIGHT - 32, CELL_SIZE - 48, 20)
        hint.setProperty("role", "muted")
        hint.setStyleSheet("background: transparent;")

        delete_button = QPushButton("✕", self)
        delete_button.setGeometry(CELL_SIZE - 32, 6, 24, 24)
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self.notebook_id))

    def set_focused(self, focused: bool):
        self._focused = focused
        self._apply_style()

    def _apply_style(self):
        border = "2px solid #60a5fa" if self._focused else "1px solid rgba(255,255,255,0.12)"
        self.setStyleSheet(
            f"QFrame#NotebookCard {{ background-color: rgba(255,255,255,0.06); border: {border}; border-radius: 12px; }}"
        )

    def mousePressEvent(self, event):
        self.clicked.emit(self.notebook_id)
        super().mousePressEvent(event)


class AddItemModal(ModalOverlay):
    book_created = Signal()
    note_created = Signal()

    def __init__(self, parent=None):
        super().__init__("Добавить", parent)

        tab_row = QHBoxLayout()
        self.book_tab = QPushButton("Книга")
        self.note_tab = QPushButton("Заметка")
        self.book_tab.clicked.connect(lambda: self._switch_tab("book"))
        self.note_tab.clicked.connect(lambda: self._switch_tab("note"))
        tab_row.addWidget(self.book_tab)
        tab_row.addWidget(self.note_tab)
        self.content_layout.addLayout(tab_row)

        self.book_panel = QWidget()
        book_layout = QVBoxLayout(self.book_panel)
        book_layout.setContentsMargins(0, 12, 0, 0)
        book_layout.setSpacing(8)

        self._book_source_path: str | None = None
        file_button = QPushButton("Выбрать файл…")
        file_button.clicked.connect(self._on_pick_file)
        self.file_label = QLabel("Файл не выбран")
        self.file_label.setProperty("role", "muted")

        self.book_title_input = QLineEdit()
        self.book_title_input.setPlaceholderText("Название книги")
        self.book_author_input = QLineEdit()
        self.book_author_input.setPlaceholderText("Автор")
        book_create = QPushButton("Создать")
        book_create.setProperty("role", "accent")
        book_create.clicked.connect(self._on_create_book)

        book_layout.addWidget(file_button)
        book_layout.addWidget(self.file_label)
        book_layout.addWidget(self.book_title_input)
        book_layout.addWidget(self.book_author_input)
        book_layout.addWidget(book_create)

        self.note_panel = QWidget()
        note_layout = QVBoxLayout(self.note_panel)
        note_layout.setContentsMargins(0, 12, 0, 0)
        self.note_title_input = QLineEdit()
        self.note_title_input.setPlaceholderText("Название заметки")
        note_create = QPushButton("Создать")
        note_create.setProperty("role", "accent")
        note_create.clicked.connect(self._on_create_note)
        note_layout.addWidget(self.note_title_input)
        note_layout.addWidget(note_create)

        self.content_layout.addWidget(self.book_panel)
        self.content_layout.addWidget(self.note_panel)
        self._switch_tab("book")

    def _switch_tab(self, tab: str):
        self.book_panel.setVisible(tab == "book")
        self.note_panel.setVisible(tab == "note")
        for button, active in ((self.book_tab, tab == "book"), (self.note_tab, tab == "note")):
            if active:
                button.setStyleSheet(
                    "QPushButton { background-color: rgba(255,255,255,0.16);"
                    " border: 1px solid rgba(255,255,255,0.26); color: white; font-weight: 600; }"
                )
            else:
                button.setStyleSheet(
                    "QPushButton { background-color: rgba(255,255,255,0.06);"
                    " border: 1px solid rgba(255,255,255,0.14); color: #94a3b8; font-weight: 400; }"
                )

    def _on_pick_file(self):
        path, _filter = QFileDialog.getOpenFileName(
            self, "Выбрать файл книги", "", "Книги (*.epub *.fb2 *.pdf);;Все файлы (*)"
        )
        if not path:
            return
        self._book_source_path = path
        self.file_label.setText(Path(path).name)
        if not self.book_title_input.text().strip():
            self.book_title_input.setText(Path(path).stem)

    def _on_create_book(self):
        title = self.book_title_input.text().strip()
        if not title:
            return
        from data.db import add_book

        add_book(
            title,
            self.book_author_input.text().strip() or None,
            source_path=self._book_source_path,
        )
        self.book_title_input.clear()
        self.book_author_input.clear()
        self._book_source_path = None
        self.file_label.setText("Файл не выбран")
        self.hide()
        self.book_created.emit()

    def _on_create_note(self):
        title = self.note_title_input.text().strip()
        if not title:
            return
        from data.db import add_notebook

        add_notebook(title)
        self.note_title_input.clear()
        self.hide()
        self.note_created.emit()


class StorageScreen(QWidget):

    notebook_opened = Signal(int)
    book_added = Signal()

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._state = None
        self._active_filter = "Заметки"
        self._cells: list[QWidget] = []
        self._cursor = 0

        self.filter_row = QHBoxLayout()
        self.filter_row.setSpacing(6)
        filter_strip = QWidget()
        filter_strip.setLayout(self.filter_row)

        self.grid_container = QWidget()
        self.grid_layout = FlowLayout(self.grid_container, margin=4, h_spacing=CELL_GAP, v_spacing=CELL_GAP)

        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setWidget(self.grid_container)

        self.add_modal = AddItemModal(self)
        self.add_modal.book_created.connect(self._on_book_created)
        self.add_modal.note_created.connect(self._on_note_created)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 16, 0, 0)
        main_layout.addWidget(filter_strip)
        main_layout.addWidget(self.grid_scroll)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.add_modal.isVisible():
            self.add_modal.show_modal()

    def refresh(self, state):
        self._state = state
        self._rebuild_filters()
        self._rebuild_grid()

    def _rebuild_filters(self):
        while self.filter_row.count():
            item = self.filter_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        names = ["Заметки", "Без категории"] + self._state.all_category_names()
        if self._active_filter not in names:
            self._active_filter = "Заметки"

        for name in names:
            chip = CategoryChip(name)
            chip.set_active(name == self._active_filter)
            chip.clicked.connect(lambda _checked=False, n=name: self._on_filter_selected(n))
            self.filter_row.addWidget(chip)

            if name not in ("Заметки", "Без категории"):
                remove_button = QPushButton("✕")
                remove_button.setFixedSize(22, 22)
                remove_button.clicked.connect(lambda _checked=False, n=name: self._on_remove_category(n))
                self.filter_row.addWidget(remove_button)

        add_chip = QPushButton("+ категория")
        add_chip.setProperty("role", "chip_add")
        add_chip.clicked.connect(self._on_add_category)
        self.filter_row.addWidget(add_chip)
        self.filter_row.addStretch()

    def _on_filter_selected(self, name: str):
        self._active_filter = name
        self._cursor = 0
        self._rebuild_filters()
        self._rebuild_grid()

    def _on_add_category(self):
        name, ok = QInputDialog.getText(self, "Новая категория", "Название:")
        if ok and name.strip():
            self._state.add_category(name.strip())
            self._rebuild_filters()

    def _on_remove_category(self, name: str):
        category = next((c for c in self._state.categories if c.name == name), None)
        if category is None:
            return
        self._state.remove_category(category.id)
        if self._active_filter == name:
            self._active_filter = "Заметки"
        self._rebuild_filters()
        self._rebuild_grid()

    def _rebuild_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cells = []

        add_tile = AddTile()
        add_tile.clicked.connect(self._open_add_modal)
        self.grid_layout.addWidget(add_tile)
        self._cells.append(add_tile)

        if self._active_filter == "Заметки":
            for notebook in self._state.notebooks:
                card = NotebookCard(notebook)
                card.clicked.connect(self.notebook_opened.emit)
                card.delete_requested.connect(self._on_delete_notebook)
                self.grid_layout.addWidget(card)
                self._cells.append(card)
        else:
            from ui.screens.library_screen import BookCard

            target = None if self._active_filter == "Без категории" else self._active_filter
            category_names = self._state.all_category_names()
            for book in self._state.books:
                name = self._state.category_of(book)
                matches = (target is None and name == "Без категории") or name == target
                if matches:
                    card = BookCard(book, category_names)
                    card.category_set.connect(self._on_book_category_set)
                    self.grid_layout.addWidget(card)
                    self._cells.append(card)

        self._cursor = min(self._cursor, len(self._cells) - 1)
        self._update_cursor_style()

    def _open_add_modal(self):
        self.add_modal.show_modal()

    def _on_book_created(self):
        self._state.load_books()
        self.book_added.emit()
        self._rebuild_grid()

    def _on_note_created(self):
        self._state.load_notebooks()
        self._rebuild_grid()

    def _on_book_category_set(self, book_id: int, category_name: str | None):
        category_id = None
        if category_name is not None:
            category = next((c for c in self._state.categories if c.name == category_name), None)
            category_id = category.id if category else None
        self._state.set_book_category(book_id, category_id)
        self._rebuild_filters()
        self._rebuild_grid()

    def _on_delete_notebook(self, notebook_id: int):
        from data.db import delete_notebook

        delete_notebook(notebook_id)
        self._state.load_notebooks()
        self._rebuild_grid()

    def _columns(self) -> int:
        width = self.grid_scroll.viewport().width() or self.width()
        return max(1, (width + CELL_GAP) // (CELL_SIZE + CELL_GAP))

    def _update_cursor_style(self):
        for k, cell in enumerate(self._cells):
            if hasattr(cell, "set_focused"):
                cell.set_focused(k == self._cursor)

    def _activate_cursor(self):
        if not self._cells:
            return
        cell = self._cells[self._cursor]
        if isinstance(cell, AddTile):
            self._open_add_modal()
        elif isinstance(cell, NotebookCard):
            self.notebook_opened.emit(cell.notebook_id)
        else:
            from ui.screens.library_screen import BookCard

            if isinstance(cell, BookCard):
                cell.clicked.emit(cell.book_id)

    def _delete_cursor(self):
        if not self._cells or self._cursor == 0:
            return
        cell = self._cells[self._cursor]
        if isinstance(cell, NotebookCard):
            self._on_delete_notebook(cell.notebook_id)

    def keyPressEvent(self, event):
        from data.keybindings import matches as key_matches

        if not self._cells or not self._state:
            super().keyPressEvent(event)
            return
        cols = self._columns()
        keys = self._state.keys
        if key_matches(event, "storage_left", keys):
            self._cursor = max(0, self._cursor - 1)
        elif key_matches(event, "storage_right", keys):
            self._cursor = min(len(self._cells) - 1, self._cursor + 1)
        elif key_matches(event, "storage_up", keys):
            self._cursor = max(0, self._cursor - cols)
        elif key_matches(event, "storage_down", keys):
            self._cursor = min(len(self._cells) - 1, self._cursor + cols)
        elif key_matches(event, "storage_open", keys):
            self._activate_cursor()
        elif key_matches(event, "storage_delete", keys):
            self._delete_cursor()
        else:
            super().keyPressEvent(event)
            return
        self._update_cursor_style()
