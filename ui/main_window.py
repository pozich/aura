import tomllib
from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtCore import Qt

from ui.screens.book_screen import BookScreen
from ui.screens.library_screen import LibraryScreen
from ui.screens.storage_screen import StorageScreen

with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as f:
    APP_NAME = tomllib.load(f)["project"]["name"]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1160, 820)

        self.stack = QStackedWidget()
        self.library_screen = LibraryScreen()
        self.book_screen = BookScreen()
        self.storage_screen = StorageScreen()

        self.stack.addWidget(self.library_screen)
        self.stack.addWidget(self.book_screen)
        self.stack.addWidget(self.storage_screen)

        self.setCentralWidget(self.stack)

    def show_screen(self, name: str):
        screens = {
                "library": self.library_screen,
                "book": self.book_screen,
                "storage": self.storage_screen,
                }
        self.stack.setCurrentWidget(screens[name])

    def keyPressEvent(self, event):
        key_map = {
                Qt.Key_1: "library",
                Qt.Key_2: "book",
                Qt.Key_3: "storage",
                }
        if event.key() in key_map:
            self.show_screen(key_map[event.key()])
        super().keyPressEvent(event)
