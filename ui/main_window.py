import tomllib
from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtCore import Qt

from ui.screens.book_screen import BookScreen
from ui.screens.library_screen import LibraryScreen
from ui.screens.storage_screen import StorageScreen
from ui.screens.settings_screen import SettingsDialog
from ui.widgets.chat_overlay import ChatOverlay

with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as f:
    APP_NAME = tomllib.load(f)["project"]["name"]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1600, 900)

        self.stack = QStackedWidget()
        self.library_screen = LibraryScreen()
        self.library_screen.settings_requested.connect(
            lambda: SettingsDialog(self).exec()
        )
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

        if event.key() == Qt.Key_Space:
            self.show_screen("book")
        elif event.key() == Qt.Key_Escape:
            self.show_screen("library")
        elif event.key() == Qt.Key_E:
            self.show_screen("storage")
        elif event.key() == Qt.Key_C:
            SettingsDialog(self).exec()
