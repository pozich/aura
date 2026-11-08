from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from data.db import add_api_key, delete_api_key, list_api_keys, set_active_api_key
from data.keybindings import save_keybindings

# Навигация — общеприложенческие действия, одна колонка.
NAV_ACTIONS = ["nav_library", "nav_storage", "nav_settings", "tab_next", "tab_prev", "focus_chat"]

# Библиотека и Хранилище управляются одной и той же логикой курсора — влево/вправо/вверх/
# вниз/открыть. Таблица строит это явно: строка — роль действия, столбец — экран, а не
# два независимых списка с дублирующимися по сути пунктами.
SHARED_ROWS = [
    ("Влево", {"Библиотека": "library_prev_book", "Хранилище": "storage_left"}),
    ("Вправо", {"Библиотека": "library_next_book", "Хранилище": "storage_right"}),
    ("Вверх", {"Библиотека": "library_prev_category", "Хранилище": "storage_up"}),
    ("Вниз", {"Библиотека": "library_next_category", "Хранилище": "storage_down"}),
    ("Открыть", {"Библиотека": "library_open", "Хранилище": "storage_open"}),
    ("Удалить", {"Хранилище": "storage_delete"}),
]
SHARED_COLUMNS = ["Библиотека", "Хранилище"]

ROW_HEIGHT = 40


def _format_binding(binding: dict) -> str:
    mods = []
    if binding.get("ctrl"):
        mods.append("Ctrl")
    if binding.get("alt"):
        mods.append("Alt")
    if binding.get("shift"):
        mods.append("Shift")
    key_name = QKeySequence(binding["key"]).toString() or "?"
    return "+".join(mods + [key_name])


class KeyButton(QPushButton):
    """Кнопка-бинд: клик → "…" → следующее нажатие перезаписывает комбинацию.
    Esc во время записи отменяет, старое значение остаётся."""

    def __init__(self, action_id: str, binding: dict, on_change, parent=None):
        super().__init__(_format_binding(binding), parent)
        self.action_id = action_id
        self._binding = binding
        self._on_change = on_change
        self._recording = False
        self.clicked.connect(self._start_recording)

    def _start_recording(self):
        self._recording = True
        self.setText("…")
        self.setFocus()
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if self._recording and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            self.removeEventFilter(self)
            self._recording = False
            if key == Qt.Key.Key_Escape:
                self.setText(_format_binding(self._binding))
                return True
            ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            alt = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
            self._binding = {**self._binding, "key": key, "ctrl": ctrl, "shift": shift, "alt": alt}
            self.setText(_format_binding(self._binding))
            self._on_change(self.action_id, self._binding)
            return True
        return super().eventFilter(obj, event)


def _make_table(columns: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    table.setShowGrid(True)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return table


def _empty_cell() -> QLabel:
    label = QLabel("—")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setProperty("role", "muted")
    return label


class SettingsScreen(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self._state = state

        self.key_list = QListWidget()
        self.key_list.itemDoubleClicked.connect(self._on_activate)
        self.key_list.setMaximumHeight(120)

        self.label_input = QLineEdit()
        self.key_input = QLineEdit()
        form = QFormLayout()
        form.addRow("Название: ", self.label_input)
        form.addRow("Ключ: ", self.key_input)

        add_button = QPushButton("Добавить")
        add_button.clicked.connect(self._on_add)
        delete_button = QPushButton("Удалить")
        delete_button.clicked.connect(self._on_delete)

        api_card = QWidget()
        api_card.setMaximumWidth(420)
        api_card_layout = QVBoxLayout(api_card)
        api_card_layout.setContentsMargins(0, 0, 0, 0)
        api_card_layout.addWidget(self.key_list)
        api_card_layout.addLayout(form)
        buttons_row = QHBoxLayout()
        buttons_row.addWidget(add_button)
        buttons_row.addWidget(delete_button)
        api_card_layout.addLayout(buttons_row)

        api_header = QLabel("API-ключи")
        api_header.setProperty("role", "title")

        hotkeys_header = QLabel("Горячие клавиши")
        hotkeys_header.setProperty("role", "title")

        nav_subheader = QLabel("Навигация")
        self.nav_table = _make_table(["Клавиша"])
        self.nav_table.setMaximumWidth(360)
        self._fill_nav_table()

        shared_subheader = QLabel("Библиотека и Хранилище")
        self.shared_table = _make_table(SHARED_COLUMNS)
        self.shared_table.setMaximumWidth(520)
        self._fill_shared_table()

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.addWidget(api_header)
        content_layout.addWidget(api_card)
        content_layout.addSpacing(24)
        content_layout.addWidget(hotkeys_header)
        content_layout.addWidget(nav_subheader)
        content_layout.addWidget(self.nav_table)
        content_layout.addWidget(shared_subheader)
        content_layout.addWidget(self.shared_table)
        content_layout.addStretch()

        # контент выше по высоте, чем обычно нужно экрану — без скролл-области это тянуло
        # за собой QStackedWidget.sizeHint() (он берёт максимум среди ВСЕХ вложенных
        # экранов, даже скрытых), и всё окно раздувалось под Настройки.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

        self._reload()

    def _fill_nav_table(self):
        self.nav_table.setRowCount(len(NAV_ACTIONS))
        labels = [self._state.keys[action_id]["label"] for action_id in NAV_ACTIONS]
        self.nav_table.setVerticalHeaderLabels(labels)
        for row, action_id in enumerate(NAV_ACTIONS):
            button = KeyButton(action_id, self._state.keys[action_id], self._on_keybind_changed)
            self.nav_table.setCellWidget(row, 0, button)
        self.nav_table.setFixedHeight(
            self.nav_table.horizontalHeader().height() + len(NAV_ACTIONS) * ROW_HEIGHT + 2
        )

    def _fill_shared_table(self):
        self.shared_table.setRowCount(len(SHARED_ROWS))
        self.shared_table.setVerticalHeaderLabels([label for label, _ in SHARED_ROWS])
        for row, (_label, by_column) in enumerate(SHARED_ROWS):
            for col, column_name in enumerate(SHARED_COLUMNS):
                action_id = by_column.get(column_name)
                if action_id is None:
                    self.shared_table.setCellWidget(row, col, _empty_cell())
                else:
                    button = KeyButton(action_id, self._state.keys[action_id], self._on_keybind_changed)
                    self.shared_table.setCellWidget(row, col, button)
        self.shared_table.setFixedHeight(
            self.shared_table.horizontalHeader().height() + len(SHARED_ROWS) * ROW_HEIGHT + 2
        )

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

    def _on_keybind_changed(self, action_id: str, binding: dict):
        self._state.keys[action_id] = binding
        save_keybindings(self._state.keys)
