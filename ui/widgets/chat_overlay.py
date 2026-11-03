from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QLineEdit,
    QPushButton,
)


class ChatOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.context_label = QLabel("Контекст: -")
        self.message_list = QListWidget()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Напишите сообщение...")
        self.send_button = QPushButton("Отправить")

        input_row = QHBoxLayout()
        input_row.addWidget(self.input_field)
        input_row.addWidget(self.send_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.context_label)
        layout.addWidget(self.message_list)
        layout.addLayout(input_row)

        self.show()

    def set_context(self, text: str):
        self.context_label.setText(f"Контекст: {text}")
