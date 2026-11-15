import sys
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from data.app_settings import load_settings
from data.db import init_db
from ui.main_window import MainWindow
from ui.styles import apply_theme

def main():
    init_db()
    app = QApplication(sys.argv)

    settings = load_settings()
    # QFontDatabase не переживает перезапуск процесса — свои шрифты, добавленные
    # в прошлый раз через Настройки → Шрифт интерфейса, нужно зарегистрировать заново.
    for font in settings["custom_fonts"]:
        QFontDatabase.addApplicationFont(font["path"])
    family = None if settings["font_family"] == "system" else settings["font_family"]
    apply_theme(app, settings["theme"], settings["font_size"], family)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
