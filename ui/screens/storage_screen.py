from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class StorageScreen(QWidget):
    def __init__(self):
        super().__init__()

        books = QWidget()
        books_layout = QVBoxLayout(books)
        books_layout.addWidget(QLabel("Storage"))
