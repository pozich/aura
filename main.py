import sys
from PySide6.QtWidgets import QApplication

from data.db import init_db
from ui.main_window import MainWindow
from ui.styles import apply_theme

def main():
    init_db()
    app = QApplication(sys.argv)
    apply_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
