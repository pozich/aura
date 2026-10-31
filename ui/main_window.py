import tomllib
from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QWidget

with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as f:
    APP_NAME = tomllib.load(f)["project"]["name"]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1160, 820)
        self.setCentralWidget(QWidget())
