from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTextEdit,
)


class BookScreen(QWidget):
    def __init__(self):
        super().__init__()

        content = QWidget()
        content_layout = QHBoxLayout(content)
        book_content = QTextEdit()
        book_content.setReadOnly(True)
        book_content.setFixedHeight(660)
        content_layout.addWidget(book_content)

        info = QWidget()
        info_layout = QHBoxLayout(info)
        book_chapter = QLabel("Глава")
        book_chapter.setFixedHeight(40)
        book_page = QLabel("Страница")
        book_page.setFixedHeight(40)
        info_layout.addWidget(book_chapter)
        info_layout.addStretch()
        info_layout.addWidget(book_page)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(content)
        main_layout.addWidget(info)
