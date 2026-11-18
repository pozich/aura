from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QKeySequence, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from data.app_settings import load_settings, save_settings
from data.db import delete_api_key, get_api_key, set_api_key
from data.keybindings import save_keybindings
from ui.styles import THEME_LABELS, THEME_ORDER, apply_theme, resolve_font_family, text_secondary_for, theme_colors

NAV_ACTIONS = ["nav_library", "tab_next", "tab_prev", "nav_storage", "nav_settings", "focus_chat"]

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
FONT_SIZES = [14, 16, 18, 20]
FONT_PRESETS = [
    ("Roboto", "Roboto"),
    ("Georgia", "Georgia"),
    ("Verdana", "Verdana"),
    ("Times New Roman", "Times New Roman"),
    ("Open Sans", "Open Sans"),
    ("system", None),
]


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
    def __init__(self, action_id: str, binding: dict, on_change, parent=None):
        super().__init__(_format_binding(binding), parent)
        self.setFlat(True)
        self.setProperty("role", "table_cell")
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


def _section_label(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setProperty("role", "muted")
    label.setStyleSheet("font-weight: 600; font-size: 11px;")
    return label


def _short_reason(message: str) -> str:
    match = re.search(r'"message"\s*:\s*"((?:[^"\\]|\\.)*)"', message)
    if match:
        code_match = re.search(r"ошибку (\d+)", message)
        prefix = f"{code_match.group(1)}: " if code_match else ""
        short = prefix + match.group(1).replace("\\n", " ").strip()
    else:
        short = " ".join(message.split())
    return short if len(short) <= 100 else short[:97] + "…"


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px; border: none;")
    return line


class ThemeSwatch(QPushButton):
    SIZE = 56
    RING_GAP = 4
    RING_WIDTH = 2
    STRIP_HEIGHT = 6

    def __init__(self, theme_id: str, parent=None):
        super().__init__(parent)
        self.theme_id = theme_id
        self._selected = False
        total = self.SIZE + 2 * (self.RING_GAP + self.RING_WIDTH)
        self.setFixedSize(total, total)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")

    def set_selected(self, selected: bool):
        self._selected = selected
        self.update()

    def paintEvent(self, event):
        c = theme_colors(self.theme_id)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        total = self.width()
        inset = (total - self.SIZE) / 2

        if self._selected:
            half_pen = self.RING_WIDTH / 2
            ring_rect = QRectF(half_pen, half_pen, total - self.RING_WIDTH, total - self.RING_WIDTH)
            pen = QPen(QColor(c["accent"]))
            pen.setWidthF(self.RING_WIDTH)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(ring_rect, 9, 9)

        swatch_rect = QRectF(inset, inset, self.SIZE, self.SIZE)
        painter.setPen(QPen(QColor(255, 255, 255, 38), 1))
        painter.setBrush(QColor(c["bg"]))
        painter.drawRoundedRect(swatch_rect, 6, 6)

        strip_rect = QRectF(inset, inset + self.SIZE - self.STRIP_HEIGHT, self.SIZE, self.STRIP_HEIGHT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(c["accent"]))
        painter.drawRoundedRect(strip_rect, 2, 2)


class FontSizeTrack(QWidget):
    value_changed = Signal(int)

    DOT_RADIUS = 5
    ACTIVE_RADIUS = 7
    MARGIN = 16
    TRACK_HEIGHT = 22
    LABEL_HEIGHT = 16

    def __init__(self, sizes: list[int], parent=None):
        super().__init__(parent)
        self._sizes = sizes
        self._count = len(sizes)
        self._index = 0
        self._accent = "#60a5fa"
        self._muted = "#64748b"
        self.setFixedHeight(self.TRACK_HEIGHT + self.LABEL_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_index(self, index: int):
        index = max(0, min(self._count - 1, index))
        if index != self._index:
            self._index = index
            self.update()

    def set_colors(self, accent: str, muted: str):
        self._accent = accent
        self._muted = muted
        self.update()

    def _dot_x(self, i: int) -> float:
        usable = self.width() - 2 * self.MARGIN
        if self._count <= 1:
            return self.MARGIN
        return self.MARGIN + usable * i / (self._count - 1)

    def _nearest_index(self, x: float) -> int:
        return min(range(self._count), key=lambda i: abs(self._dot_x(i) - x))

    def _pick(self, x: float):
        index = self._nearest_index(x)
        if index != self._index:
            self._index = index
            self.update()
            self.value_changed.emit(index)

    def mousePressEvent(self, event):
        self._pick(event.position().x())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._pick(event.position().x())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        y = self.TRACK_HEIGHT / 2

        pen = QPen(QColor(self._muted))
        pen.setWidthF(2)
        painter.setPen(pen)
        for i in range(self._count - 1):
            painter.drawLine(QPointF(self._dot_x(i), y), QPointF(self._dot_x(i + 1), y))

        for i in range(self._count):
            x = self._dot_x(i)
            active = i == self._index
            radius = self.ACTIVE_RADIUS if active else self.DOT_RADIUS
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self._accent) if active else QColor(self._muted))
            painter.drawEllipse(QPointF(x, y), radius, radius)

        label_font = QFont()
        label_font.setPixelSize(11)
        painter.setFont(label_font)
        metrics = QFontMetrics(label_font)
        for i, size in enumerate(self._sizes):
            x = self._dot_x(i)
            text = f"{size}px"
            half_w = metrics.horizontalAdvance(text) / 2
            active = i == self._index
            painter.setPen(QColor(self._accent) if active else QColor(self._muted))
            painter.drawText(
                QRectF(x - half_w, self.TRACK_HEIGHT, half_w * 2, self.LABEL_HEIGHT),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                text,
            )


class SettingsScreen(QWidget):
    appearance_changed = Signal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self._state = state
        self._settings = load_settings()
        self._theme_buttons: dict[str, ThemeSwatch] = {}

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        title = QLabel("Настройки")
        title.setProperty("role", "title")
        content_layout.addWidget(title)

        content_layout.addWidget(self._build_api_section())
        content_layout.addWidget(_separator())

        columns = QHBoxLayout()
        columns.setSpacing(32)
        columns.addLayout(self._build_font_column(), 1)
        columns.addLayout(self._build_nav_column(), 1)
        columns.addLayout(self._build_shared_column(), 1)
        content_layout.addLayout(columns, 1)

        content_layout.addWidget(_separator())
        content_layout.addLayout(self._build_theme_row())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

        self._reload_api_keys()

    def _build_api_section(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(_section_label("Gemini API"))

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("AIza…")

        input_row = QHBoxLayout()
        input_row.addWidget(self.key_input, 1)
        self._save_key_button = QPushButton("Сохранить")
        self._save_key_button.setFlat(True)
        self._save_key_button.setProperty("role", "accent")
        self._save_key_button.clicked.connect(self._on_save_key)
        input_row.addWidget(self._save_key_button)
        delete_button = QPushButton("Удалить")
        delete_button.setFlat(True)
        delete_button.clicked.connect(self._on_delete_key)
        input_row.addWidget(delete_button)

        layout.addLayout(input_row)

        usage_row = QHBoxLayout()
        self._usage_label = QLabel()
        self._usage_label.setProperty("role", "muted")
        usage_row.addWidget(self._usage_label, 1)
        self._validity_label = QLabel()
        self._validity_label.setProperty("role", "muted")
        usage_row.addWidget(self._validity_label)
        layout.addLayout(usage_row)

        self._refresh_usage_label()
        return section

    def _refresh_usage_label(self):
        if not get_api_key():
            self._usage_label.setText("")
            return

        from core.usage_tracker import seconds_until_reset, tokens_today

        secs = seconds_until_reset()
        hours, minutes = secs // 3600, (secs % 3600) // 60
        self._usage_label.setText(f"Токенов сегодня: {tokens_today()} · сброс через {hours}ч {minutes}м")

    def _reload_api_keys(self):
        key = get_api_key()
        self._editing_key = not bool(key)
        self.key_input.setText(key or "")
        self.key_input.setEnabled(self._editing_key)
        self._save_key_button.setText("Сохранить" if self._editing_key else "Изменить")
        self._save_key_button.setEnabled(True)

    def _on_save_key(self):
        if not self._editing_key:
            self._editing_key = True
            self.key_input.setEnabled(True)
            self.key_input.setFocus()
            self.key_input.selectAll()
            self._save_key_button.setText("Сохранить")
            return

        key = self.key_input.text().strip()
        if not key:
            return

        from core.gemini_worker import ask_gemini_async

        self.key_input.setEnabled(False)
        self._save_key_button.setEnabled(False)
        self._save_key_button.setText("Проверка…")
        self._validity_label.setText("")
        self._save_check_thread = ask_gemini_async(
            "Ответь одним словом: ок",
            on_success=lambda _text, usage, k=key: self._on_save_check_success(k, usage),
            on_error=self._on_save_check_error,
            api_key=key,
            parent=self,
        )

    def _on_save_check_success(self, key: str, _usage: dict):
        set_api_key(key)
        self._editing_key = False
        self.key_input.setText(key)
        self.key_input.setEnabled(False)
        self._save_key_button.setText("Сохранено ✓")
        self._validity_label.setText("✓ работает")
        self._refresh_usage_label()
        QTimer.singleShot(1200, self._reset_save_key_button)

    def _on_save_check_error(self, message: str):
        self.key_input.setEnabled(True)
        self._save_key_button.setEnabled(True)
        self._save_key_button.setText("Сохранить")
        self._validity_label.setText(f"✗ {_short_reason(message)}")
        self.key_input.setFocus()
        self.key_input.selectAll()

    def _reset_save_key_button(self):
        self._save_key_button.setText("Изменить")
        self._save_key_button.setEnabled(True)

    def _on_delete_key(self):
        delete_api_key()
        self._reload_api_keys()
        self._validity_label.setText("")
        self._refresh_usage_label()

    def _build_font_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(10)
        col.addWidget(_section_label("Настройки шрифта"))

        size_block = QVBoxLayout()
        size_block.setSpacing(4)
        size_block.addWidget(QLabel("Размер шрифта"))

        start_index = FONT_SIZES.index(self._settings["font_size"]) if self._settings["font_size"] in FONT_SIZES else 0
        self.size_track = FontSizeTrack(FONT_SIZES)
        self.size_track.set_index(start_index)
        self.size_track.set_colors(*self._current_track_colors())
        self.size_track.value_changed.connect(self._on_size_track_changed)
        size_block.addWidget(self.size_track)
        col.addLayout(size_block)

        col.addWidget(QLabel("Шрифт интерфейса"))
        add_font_btn = QPushButton("+ Добавить свой")
        add_font_btn.setFlat(True)
        add_font_btn.setProperty("role", "chip_add")
        add_font_btn.clicked.connect(self._on_add_font)
        col.addWidget(add_font_btn)

        self.font_table = QTableWidget(0, 1)
        self.font_table.horizontalHeader().setVisible(False)
        self.font_table.verticalHeader().setVisible(False)
        self.font_table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.font_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.font_table.setShowGrid(False)
        self.font_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.font_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.font_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.font_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.font_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        col.addWidget(self.font_table, 1)
        self._rebuild_font_list()

        return col

    def _rebuild_font_list(self):
        for row in range(self.font_table.rowCount()):
            old = self.font_table.cellWidget(row, 0)
            if old:
                self.font_table.removeCellWidget(row, 0)
                old.setParent(None)
                old.deleteLater()

        entries = [
            (font_id, label if label is not None else resolve_font_family(None))
            for font_id, label in FONT_PRESETS
        ] + [(f["id"], f["id"]) for f in self._settings["custom_fonts"]]
        custom_ids = {f["id"] for f in self._settings["custom_fonts"]}

        self.font_table.setRowCount(len(entries))
        for row, (font_id, label) in enumerate(entries):
            is_active = font_id == self._settings["font_family"]
            text = ("● " if is_active else "○ ") + label
            btn = QPushButton(text)
            btn.setFlat(True)
            btn.setFont(QFont(label, 13))
            btn.setProperty("role", "font_row")
            btn.setProperty("active", is_active)
            btn.clicked.connect(lambda _checked=False, f=font_id: self._on_font_family(f))

            if font_id in custom_ids:
                cell = QWidget()
                cell_layout = QHBoxLayout(cell)
                cell_layout.setContentsMargins(0, 0, 0, 0)
                cell_layout.setSpacing(4)
                cell_layout.addWidget(btn, 1)
                remove_btn = QPushButton("✕")
                remove_btn.setFlat(True)
                remove_btn.setFixedWidth(28)
                remove_btn.clicked.connect(lambda _checked=False, f=font_id: self._on_remove_font(f))
                cell_layout.addWidget(remove_btn)
                self.font_table.setCellWidget(row, 0, cell)
            else:
                self.font_table.setCellWidget(row, 0, btn)

    def _current_track_colors(self) -> tuple[str, str]:
        palette = theme_colors(self._settings["theme"])
        return palette["accent"], text_secondary_for(self._settings["theme"])

    def _on_size_track_changed(self, index: int):
        self._settings["font_size"] = FONT_SIZES[index]
        self._persist_and_apply()

    def _on_font_family(self, font_id: str):
        self._settings["font_family"] = font_id
        self._rebuild_font_list()
        self._persist_and_apply()

    def _on_add_font(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать файл шрифта", "", "Шрифты (*.ttf *.otf)")
        if not path:
            return
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id == -1:
            QMessageBox.warning(self, "Не удалось загрузить шрифт", "Файл повреждён или формат не поддерживается.")
            return
        families = QFontDatabase.applicationFontFamilies(font_id)
        family = families[0] if families else Path(path).stem
        self._settings["custom_fonts"].append({"id": family, "path": path})
        self._settings["font_family"] = family
        self._rebuild_font_list()
        self._persist_and_apply()

    def _on_remove_font(self, font_id: str):
        self._settings["custom_fonts"] = [f for f in self._settings["custom_fonts"] if f["id"] != font_id]
        if self._settings["font_family"] == font_id:
            self._settings["font_family"] = "system"
        self._rebuild_font_list()
        self._persist_and_apply()

    def _build_nav_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(10)
        col.addWidget(_section_label("Общая навигация"))

        self.nav_table = _make_table(["Клавиша"])
        self.nav_table.setRowCount(len(NAV_ACTIONS))
        labels = [self._state.keys[action_id]["label"] for action_id in NAV_ACTIONS]
        self.nav_table.setVerticalHeaderLabels(labels)
        for row, action_id in enumerate(NAV_ACTIONS):
            button = KeyButton(action_id, self._state.keys[action_id], self._on_keybind_changed)
            self.nav_table.setCellWidget(row, 0, button)
        self.nav_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        col.addWidget(self.nav_table, 1)
        return col

    def _build_shared_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(10)
        col.addWidget(_section_label("Навигация внутри окон"))

        self.shared_table = _make_table(SHARED_COLUMNS)
        self.shared_table.setRowCount(len(SHARED_ROWS))
        self.shared_table.setVerticalHeaderLabels([label for label, _ in SHARED_ROWS])
        for row, (_label, by_column) in enumerate(SHARED_ROWS):
            for col_idx, column_name in enumerate(SHARED_COLUMNS):
                action_id = by_column.get(column_name)
                if action_id is None:
                    self.shared_table.setCellWidget(row, col_idx, _empty_cell())
                else:
                    button = KeyButton(action_id, self._state.keys[action_id], self._on_keybind_changed)
                    self.shared_table.setCellWidget(row, col_idx, button)
        self.shared_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        col.addWidget(self.shared_table, 1)
        return col

    def _on_keybind_changed(self, action_id: str, binding: dict):
        self._state.keys[action_id] = binding
        save_keybindings(self._state.keys)

    def _build_theme_row(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(10)
        header = _section_label("Тема")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(header)
        col.addSpacing(18)

        row = QHBoxLayout()
        row.addStretch()
        self._theme_labels: dict[str, QLabel] = {}
        for theme_id in THEME_ORDER:
            swatch_col = QVBoxLayout()
            swatch_col.setSpacing(4)
            btn = ThemeSwatch(theme_id)
            is_active = theme_id == self._settings["theme"]
            btn.set_selected(is_active)
            btn.clicked.connect(lambda _checked=False, t=theme_id: self._on_theme(t))
            self._theme_buttons[theme_id] = btn
            label = QLabel(THEME_LABELS[theme_id])
            label.setProperty("role", "theme_selected" if is_active else "muted")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 11px;")
            self._theme_labels[theme_id] = label
            swatch_col.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            swatch_col.addWidget(label)
            row.addLayout(swatch_col)
            row.addSpacing(16)
        row.addStretch()
        col.addLayout(row)
        return col

    def _on_theme(self, theme_id: str):
        self._settings["theme"] = theme_id
        for t, btn in self._theme_buttons.items():
            btn.set_selected(t == theme_id)
        for t, label in self._theme_labels.items():
            label.setProperty("role", "theme_selected" if t == theme_id else "muted")
            label.style().unpolish(label)
            label.style().polish(label)
        self.size_track.set_colors(*self._current_track_colors())
        self._persist_and_apply()

    def _persist_and_apply(self):
        save_settings(self._settings)
        app = QApplication.instance()
        if app is not None:
            family = None if self._settings["font_family"] == "system" else self._settings["font_family"]
            apply_theme(app, self._settings["theme"], self._settings["font_size"], family)
        self.appearance_changed.emit()
