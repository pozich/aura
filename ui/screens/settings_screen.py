from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
)

from data.db import delete_api_key, list_api_keys, add_api_key, set_active_api_key


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки API")
        self.key_list = QListWidget()
        self.key_list.itemDoubleClicked.connect(self._on_activate)

        self.label_input = QLineEdit()
        self.key_input = QLineEdit()
        form = QFormLayout()
        form.addRow("Название: ", self.label_input)
        form.addRow("Ключ: ", self.key_input)

        add_button = QPushButton("Добавить")
        add_button.clicked.connect(self._on_add)
        delete_button = QPushButton("Удалить")
        delete_button.clicked.connect(self._on_delete)

        layout = QVBoxLayout(self)
        layout.addWidget(self.key_list)
        layout.addLayout(form)
        layout.addWidget(add_button)
        layout.addWidget(delete_button)

        self._reload()

    def _reload(self):
        self.key_list.clear()
        for row in list_api_keys():
            mark = "● " if row["is_active"] else " "
            item = QListWidgetItem(mark + row["label"])
            item.setData(1, row["id"])
            self.key_list.addItem(item)

    def _on_add(self):
        add_api_key(self.label_input.text(), self.key_input.text())
        self.label_input.clear()
        self.key_input.clear()
        self._reload()

    def _on_activate(self, item):
        set_active_api_key(item.data(1))
        self._reload()

    def _on_delete(self):
        delete_api_key(self.key_list.currentItem().data(1))
        self._reload()
