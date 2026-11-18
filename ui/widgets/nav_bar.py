from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from data.app_settings import load_settings
from ui.styles import text_primary_for, text_secondary_for
from ui.widgets.icon_button import CircleIconButton

KIND_ICON = {
    "library": "📚",
    "storage": "📦",
    "chat": "💬",
    "settings": "⚙",
    "book": "📖",
    "notes": "✎",
}

WIDTH_PADDING = 16


class NavTab(QFrame):
    clicked = Signal(str)
    close_requested = Signal(str)

    def __init__(
        self,
        tab_id: str,
        label: str,
        kind: str,
        closable: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.tab_id = tab_id
        self.setObjectName("NavTab")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        self.icon_label = QLabel(KIND_ICON.get(kind, "•"))
        layout.addWidget(self.icon_label)

        self.text_label = QLabel(label)
        layout.addWidget(self.text_label)

        if closable:
            close_button = CircleIconButton("close", size=18)
            close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            close_button.clicked.connect(lambda: self.close_requested.emit(self.tab_id))
            layout.addWidget(close_button)

        self._active = False
        self._refresh_width()
        self._apply_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self.tab_id)
        super().mousePressEvent(event)

    def set_text(self, label: str):
        self.text_label.setText(label)
        self._refresh_width()

    def _bold_stable_width(self) -> int:
        normal_font = self.text_label.font()
        text = self.text_label.text()
        normal_width = QFontMetrics(normal_font).horizontalAdvance(text)
        bold_font = QFont(normal_font)
        bold_font.setBold(True)
        bold_width = QFontMetrics(bold_font).horizontalAdvance(text)
        return self.sizeHint().width() + max(bold_width - normal_width, 0) + WIDTH_PADDING

    def _refresh_width(self):
        self.setFixedWidth(self._bold_stable_width())

    def refresh_appearance(self):
        self._refresh_width()
        self._apply_style()

    def set_active(self, active: bool):
        self._active = active
        self._apply_style()

    def _apply_style(self):
        self.setProperty("active", self._active)
        self.style().unpolish(self)
        self.style().polish(self)

        theme_id = load_settings()["theme"]
        color = text_primary_for(theme_id) if self._active else text_secondary_for(theme_id)
        weight = "600" if self._active else "400"
        self.text_label.setStyleSheet(
            f"color: {color}; font-weight: {weight}; background: transparent;"
        )
        self.icon_label.setStyleSheet(f"color: {color}; background: transparent;")


class NavSeparator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 8)
        line = QFrame()
        line.setFixedWidth(1)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.15);")
        layout.addWidget(line)
        self.setVisible(False)


class NavBar(QWidget):
    tab_selected = Signal(str)
    tab_closed = Signal(str)

    FIXED_TABS = [
        ("chat", "Чат"),
        ("library", "Библиотека"),
        ("storage", "Хранилище"),
        ("settings", "Настройки"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavBar")
        self._tabs: dict[str, NavTab] = {}

        self.layout_ = QHBoxLayout(self)
        self.layout_.setContentsMargins(16, 4, 16, 0)
        self.layout_.setSpacing(4)

        tabs = [
            (tab_id, NavTab(tab_id, label, kind=tab_id, closable=False))
            for tab_id, label in self.FIXED_TABS
        ]

        for tab_id, tab in tabs:
            tab.clicked.connect(self.tab_selected.emit)
            tab.close_requested.connect(self.tab_closed.emit)
            self._tabs[tab_id] = tab
            self.layout_.addWidget(tab)

        self.separator = NavSeparator()
        self.layout_.addWidget(self.separator)

        self.layout_.addStretch()

    def _insert_tab(self, tab_id: str, label: str, kind: str, closable: bool) -> NavTab:
        tab = NavTab(tab_id, label, kind, closable)
        tab.clicked.connect(self.tab_selected.emit)
        tab.close_requested.connect(self.tab_closed.emit)
        self._tabs[tab_id] = tab
        insert_at = self.layout_.count() - 1 if self.layout_.count() > 0 else 0
        self.layout_.insertWidget(max(insert_at, 0), tab)
        return tab

    def open_dynamic_tab(self, tab_id: str, title: str, kind: str):
        if tab_id in self._tabs:
            self._tabs[tab_id].set_text(title)
            return
        self._insert_tab(tab_id, title, kind, closable=True)
        self._update_separator()

    def close_dynamic_tab(self, tab_id: str):
        tab = self._tabs.pop(tab_id, None)
        if tab:
            self.layout_.removeWidget(tab)
            tab.deleteLater()
        self._update_separator()

    def _update_separator(self):
        dynamic_count = len(self._tabs) - len(self.FIXED_TABS)
        self.separator.setVisible(dynamic_count > 0)

    def set_active(self, tab_id: str):
        for tid, tab in self._tabs.items():
            tab.set_active(tid == tab_id)

    def refresh_appearance(self):
        for tab in self._tabs.values():
            tab.refresh_appearance()

    def tab_ids(self) -> list[str]:
        return list(self._tabs.keys())
