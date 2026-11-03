import tomllib
from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtCore import Qt

from ui.screens.book_screen import BookScreen
from ui.screens.library_screen import LibraryScreen
from ui.screens.storage_screen import StorageScreen
from ui.widgets.chat_overlay import ChatOverlay

with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as f:
    APP_NAME = tomllib.load(f)["project"]["name"]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1600, 900)
        self.active_screen = 0

        self.stack = QStackedWidget()
        self.library_screen = LibraryScreen()
        self.book_screen = BookScreen()
        self.storage_screen = StorageScreen()

        self.stack.addWidget(self.library_screen)
        self.stack.addWidget(self.book_screen)
        self.stack.addWidget(self.storage_screen)

        self.stack.setFixedHeight(740)

        self.setCentralWidget(self.stack)

        self.chat_overlay = ChatOverlay(self)
        self.chat_overlay.setGeometry(0, 740, 1600, 160)

    def show_screen(self, name: str):
        screens = {
            "library": self.library_screen,
            "book": self.book_screen,
            "storage": self.storage_screen,
        }
        self.stack.setCurrentWidget(screens[name])

    def keyPressEvent(self, event):
        key_list = ["library", "book", "storage"]

        if event.key() == Qt.Key_Left:
            self.active_screen = (self.active_screen - 1) % len(key_list)
            self.show_screen(key_list[self.active_screen])
        elif event.key() == Qt.Key_Right:
            self.active_screen = (self.active_screen + 1) % len(key_list)
            self.show_screen(key_list[self.active_screen])
