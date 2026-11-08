import tomllib
from pathlib import Path

from PySide6.QtWidgets import QGraphicsOpacityEffect, QMainWindow, QStackedWidget, QVBoxLayout, QWidget
from PySide6.QtCore import QPropertyAnimation

from core.app_state import AppState
from ui.screens.book_screen import BookScreen
from ui.screens.chat_screen import ChatScreen
from ui.screens.library_screen import LibraryScreen
from ui.screens.notes_screen import NotesScreen
from ui.screens.settings_screen import SettingsScreen
from ui.screens.storage_screen import StorageScreen
from ui.widgets.chat_footer import ChatFooter
from ui.widgets.nav_bar import NavBar

with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as f:
    APP_NAME = tomllib.load(f)["project"]["name"]

FADE_DURATION_MS = 180


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1600, 900)

        self.state = AppState()
        self.state.load_keybindings()
        self.state.load_categories()
        self.state.load_books()
        self.state.load_notebooks()

        self.nav = NavBar()
        self.nav.tab_selected.connect(self.show_screen)
        self.nav.tab_closed.connect(self.close_tab)

        self.stack = QStackedWidget()
        self.stack.setObjectName("StackBody")

        self.library_screen = LibraryScreen()
        self.library_screen.book_opened.connect(self.open_book_tab)

        self.storage_screen = StorageScreen()
        self.storage_screen.notebook_opened.connect(self.open_notes_tab)
        self.storage_screen.book_added.connect(
            lambda: self.library_screen.refresh(self.state)
        )

        self.chat_screen = ChatScreen(self.state)
        self.settings_screen = SettingsScreen(self.state)

        self.screens = {
            "library": self.library_screen,
            "storage": self.storage_screen,
            "chat": self.chat_screen,
            "settings": self.settings_screen,
        }
        for screen in self.screens.values():
            self.stack.addWidget(screen)

        self.library_screen.refresh(self.state)
        self.storage_screen.refresh(self.state)

        # чат — футер: всегда внизу, во всю ширину, виден на любом экране. ChatScreen —
        # только история, ввод только здесь (иначе было два поля ввода одновременно).
        self.chat_footer = ChatFooter(self.state)
        self.chat_footer.message_sent.connect(self.chat_screen.refresh)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.nav)          # header
        central_layout.addWidget(self.stack, 1)      # body
        central_layout.addWidget(self.chat_footer)   # footer
        self.setCentralWidget(central)

        self._fade_anim = None
        self.show_screen("library")

    def show_screen(self, name: str):
        widget = self.screens[name]
        self.stack.setCurrentWidget(widget)
        self.nav.set_active(name)
        self.state.current_screen = name
        widget.setFocus()
        self._fade_in(widget)

    def _fade_in(self, widget):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", widget)
        anim.setDuration(FADE_DURATION_MS)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._fade_anim = anim

    def open_book_tab(self, book_id: int):
        tab_id = self.state.open_book(book_id)
        if tab_id not in self.screens:
            book = self.state.book_by_id(book_id)
            screen = BookScreen(book)
            screen.set_exit_handler(lambda: self.show_screen("library"))
            self.screens[tab_id] = screen
            self.stack.addWidget(screen)
        book = self.state.book_by_id(book_id)
        self.nav.open_dynamic_tab(tab_id, book.title, "book")
        self.show_screen(tab_id)

    def open_notes_tab(self, notebook_id: int):
        tab_id = self.state.open_notes(notebook_id)
        if tab_id not in self.screens:
            notebook = self.state.notebook_by_id(notebook_id)
            screen = NotesScreen(notebook_id, notebook.title, notebook.text)
            self.screens[tab_id] = screen
            self.stack.addWidget(screen)
        notebook = self.state.notebook_by_id(notebook_id)
        self.nav.open_dynamic_tab(tab_id, notebook.title, "notes")
        self.show_screen(tab_id)

    def close_tab(self, tab_id: str):
        screen = self.screens.pop(tab_id, None)
        if screen is not None:
            self.stack.removeWidget(screen)
            screen.deleteLater()
        self.state.close_tab(tab_id)
        self.nav.close_dynamic_tab(tab_id)
        if self.state.current_screen == tab_id:
            self.show_screen("library")

    def cycle_tab(self, direction: int):
        ids = self.nav.tab_ids()
        if not ids:
            return
        current = self.state.current_screen
        index = ids.index(current) if current in ids else 0
        self.show_screen(ids[(index + direction) % len(ids)])

    def keyPressEvent(self, event):
        from data.keybindings import matches

        keys = self.state.keys
        if matches(event, "nav_library", keys):
            self.show_screen("library")
        elif matches(event, "nav_storage", keys):
            self.show_screen("storage")
        elif matches(event, "nav_settings", keys):
            self.show_screen("settings")
        elif matches(event, "tab_next", keys):
            self.cycle_tab(1)
        elif matches(event, "tab_prev", keys):
            self.cycle_tab(-1)
        elif matches(event, "focus_chat", keys):
            self.chat_footer.focus_input()
