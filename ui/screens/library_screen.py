from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QProgressBar,
    QPushButton,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


class LibraryScreen(QWidget):
    def __init__(self):
        super().__init__()
        SIDE_SIZE = (220, 330)
        ACTIVE_SIZE = (300, 450)

        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.addWidget(
            QLabel("Название книги"), alignment=Qt.AlignmentFlag.AlignCenter
        )
        header_layout.addWidget(
            QLabel("Автор книги"), alignment=Qt.AlignmentFlag.AlignCenter
        )
        header.setFixedHeight(140)

        self.settings_button = QPushButton("⚙", self)
        self.settings_button.setFixedSize(32, 32)

        covers = QWidget()
        covers_layout = QHBoxLayout(covers)
        cover_paths = ["/home/pzch/raw/nov.jpg"] * 3
        covers_labels = []
        for i, path in enumerate(cover_paths):
            size = ACTIVE_SIZE if i == 1 else SIDE_SIZE
            label = QLabel()
            pixmap = QPixmap(path).scaled(
                *size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            label.setPixmap(pixmap)
            label.setFixedSize(*size)
            covers_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
            covers_labels.append(label)
        book_info = QWidget()
        book_info_layout = QVBoxLayout(book_info)
        book_info_layout.addWidget(
            QLabel("Страницы | Обработано | Озвучено"),
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        book_info.setFixedHeight(120)
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(67)
        progress.setTextVisible(False)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.addWidget(covers)
        body_layout.addWidget(book_info)
        body_layout.addWidget(progress)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(header)
        main_layout.addWidget(body)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        margin = 20
        self.settings_button.move(
            self.width() - self.settings_button.width() - margin, margin
        )
