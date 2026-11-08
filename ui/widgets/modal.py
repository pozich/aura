from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

# Карточка модалки заметно светлее фона страницы — иначе на затемнённом фоне она
# сливается с ним и выглядит как дыра, а не отдельное окно (так и было: фон карточки
# совпадал с фоном приложения, #0f172a). Поля ввода внутри тоже контрастнее обычных —
# глобальные 5%-белые инпуты на тёмной подложке читались почти чёрными.
CARD_BG = "#1e293b"
CARD_BORDER = "rgba(255, 255, 255, 0.14)"
FIELD_BG = "rgba(255, 255, 255, 0.10)"
FIELD_BG_HOVER = "rgba(255, 255, 255, 0.16)"
FIELD_BORDER = "rgba(255, 255, 255, 0.22)"

MODAL_CARD_STYLESHEET = f"""
QFrame#ModalCard {{
    background-color: {CARD_BG};
    border: 1px solid {CARD_BORDER};
    border-radius: 16px;
}}

QFrame#ModalCard QLineEdit {{
    background-color: {FIELD_BG};
    border: 1px solid {FIELD_BORDER};
    border-radius: 8px;
    padding: 8px 10px;
}}

QFrame#ModalCard QPushButton {{
    background-color: {FIELD_BG};
    border: 1px solid {FIELD_BORDER};
}}

QFrame#ModalCard QPushButton:hover {{
    background-color: {FIELD_BG_HOVER};
}}

QFrame#ModalCard QLabel {{
    background: transparent;
}}
"""


class ModalOverlay(QWidget):
    """Затемнённый фон во весь родительский экран + контрастная карточка по центру —
    как Settings/AddModal в Figma. Клик по фону или кнопка "Закрыть" скрывают модалку."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.6);")

        self.card = QFrame(self)
        self.card.setObjectName("ModalCard")
        self.card.setStyleSheet(MODAL_CARD_STYLESHEET)
        self.card.setFixedWidth(420)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 16, 20, 20)

        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 18px;")
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.hide)
        header.addWidget(title_label)
        header.addStretch()
        header.addWidget(close_button)
        card_layout.addLayout(header)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 16, 0, 0)
        card_layout.addLayout(self.content_layout)

        self.hide()

    def mousePressEvent(self, event):
        if not self.card.geometry().contains(event.pos()):
            self.hide()
        super().mousePressEvent(event)

    def show_modal(self):
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        self.card.adjustSize()
        self.card.move(
            (self.width() - self.card.width()) // 2,
            (self.height() - self.card.height()) // 2,
        )
        self.raise_()
        self.show()
