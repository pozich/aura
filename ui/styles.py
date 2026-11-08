from __future__ import annotations

BG_PRIMARY = "#0f172a"
BG_SECONDARY = "#1e293b"
BORDER = "rgba(255, 255, 255, 0.10)"
CARD_BG = "rgba(255, 255, 255, 0.05)"
CARD_BG_HOVER = "rgba(255, 255, 255, 0.10)"

TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
TEXT_DIM = "#64748b"

ACCENT = "#2563eb"
ACCENT_HOVER = "#3b82f6"
ACCENT_LIGHT = "#60a5fa"

BOOK_HUES = [
    "#4c1d95",
    "#9f1239",
    "#155e75",
    "#854d0e",
    "#166534",
    "#6b21a8",
    "#9a3412",
    "#1e3a8a",
]


def hue_for(book_id: int) -> str:
    return BOOK_HUES[book_id % len(BOOK_HUES)]


APP_STYLESHEET = f"""
QWidget {{
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
    font-size: 14px;
}}

QLabel {{
    background: transparent;
}}

QLabel[role="title"] {{
    font-size: 20px;
    font-weight: 600;
}}

QLabel[role="muted"] {{
    color: {TEXT_SECONDARY};
}}

QPushButton {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 14px;
    color: {TEXT_PRIMARY};
}}

QPushButton:hover {{
    background-color: {CARD_BG_HOVER};
}}

QPushButton[role="accent"] {{
    background-color: {ACCENT};
    border: none;
}}

QPushButton[role="accent"]:hover {{
    background-color: {ACCENT_HOVER};
}}

QPushButton[role="chip"] {{
    border-radius: 14px;
    padding: 4px 14px;
    background-color: {CARD_BG};
    border: none;
    color: {TEXT_SECONDARY};
}}

QPushButton[role="chip"][active="true"] {{
    background-color: {CARD_BG_HOVER};
    color: {TEXT_PRIMARY};
}}

QPushButton[role="chip_add"] {{
    border-radius: 14px;
    padding: 4px 14px;
    background-color: transparent;
    border: 1px dashed {BORDER};
    color: {TEXT_DIM};
}}

QLineEdit, QTextEdit {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT};
}}

QListWidget {{
    background-color: transparent;
    border: none;
}}

QScrollArea {{
    border: none;
    background: transparent;
}}

QTableWidget {{
    background-color: transparent;
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

QTableWidget::item {{
    padding: 4px;
}}

QHeaderView::section {{
    background-color: rgba(255, 255, 255, 0.06);
    color: {TEXT_SECONDARY};
    padding: 6px;
    border: none;
    border-right: 1px solid {BORDER};
}}

QHeaderView {{
    background-color: transparent;
}}

QTableCornerButton::section {{
    background-color: rgba(255, 255, 255, 0.06);
    border: none;
}}

QProgressBar {{
    background-color: rgba(255, 255, 255, 0.10);
    border: none;
    border-radius: 3px;
    max-height: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {ACCENT_HOVER};
    border-radius: 3px;
}}

QWidget#NavBar {{
    background-color: rgba(0, 0, 0, 0.35);
    border-bottom: 1px solid {BORDER};
}}

QFrame#NavTab {{
    background: transparent;
    border: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}}

QFrame#NavTab QPushButton {{
    background: transparent;
    border: none;
    padding: 2px 4px;
    color: {TEXT_DIM};
}}

QFrame#NavTab QPushButton:hover {{
    background: transparent;
    color: {TEXT_SECONDARY};
}}

QFrame#NavTab[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {BG_SECONDARY}, stop:1 {BG_PRIMARY});
}}

QFrame#NavTab[active="true"] QPushButton {{
    color: {TEXT_PRIMARY};
    font-weight: 600;
}}
QWidget#StackBody {{
    background-color: {BG_PRIMARY};
}}
"""


def apply_theme(app):
    app.setStyleSheet(APP_STYLESHEET)
