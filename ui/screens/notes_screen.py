from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


class NotesScreen(QWidget):
    def __init__(self, notebook_id: int, title: str, text: str | None, parent=None):
        super().__init__(parent)
        self.notebook_id = notebook_id

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-family: Georgia, serif; font-size: 22px;")

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(text or "")
        self.text_edit.setStyleSheet(
            "QTextEdit { background-color: rgba(255,255,255,0.04);"
            " border: 1px solid rgba(255,255,255,0.10); border-radius: 12px;"
            " padding: 16px; font-size: 15px; }"
        )

        self.save_button = QPushButton("Сохранить")
        self.save_button.setProperty("role", "accent")
        self.save_button.clicked.connect(self._on_save)

        save_row = QHBoxLayout()
        save_row.addStretch()
        save_row.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(self.title_label)
        layout.addWidget(self.text_edit)
        layout.addLayout(save_row)

    def _on_save(self):
        from data.db import update_notebook

        update_notebook(self.notebook_id, text=self.text_edit.toPlainText())
