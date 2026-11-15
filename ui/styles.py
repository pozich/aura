from __future__ import annotations

# bg/bg2 — основной фон и фон вторичных поверхностей (навбар, активная вкладка).
# accent/accent_hover — акцент (кнопки, прогресс-бар, выделение). light — тёмный или
# светлый текст/подложки карточек нужны поверх фона (сейчас это только "cream").
THEMES: dict[str, dict] = {
    "amoled": {"bg": "#000000", "bg2": "#111111", "accent": "#e5e5e5", "accent_hover": "#ffffff", "light": False},
    # bg чуть темнее/желтее чистого "почти белого" f5f0e6 — иначе на обычном
    # мониторе крем на глаз не отличить от белого фона.
    "cream": {"bg": "#efe3cc", "bg2": "#e4d4b4", "accent": "#8a6d3f", "accent_hover": "#a9875a", "light": True},
    "hunter": {"bg": "#16241c", "bg2": "#1d2f24", "accent": "#b89b5e", "accent_hover": "#cdb377", "light": False},
    "bordeaux": {"bg": "#2a1414", "bg2": "#341a1a", "accent": "#a97468", "accent_hover": "#c08e81", "light": False},
    "navy": {"bg": "#0f172a", "bg2": "#1e293b", "accent": "#2563eb", "accent_hover": "#3b82f6", "light": False},
    "tobacco": {"bg": "#241a10", "bg2": "#2e2216", "accent": "#b8905f", "accent_hover": "#cca677", "light": False},
    "graphite": {"bg": "#1c1c1c", "bg2": "#262626", "accent": "#9a9a9a", "accent_hover": "#b5b5b5", "light": False},
    "olive": {"bg": "#1f2416", "bg2": "#2a3120", "accent": "#a8a063", "accent_hover": "#bdb57c", "light": False},
}

THEME_LABELS: dict[str, str] = {
    "amoled": "AMOLED",
    "cream": "Крем",
    "hunter": "Хантер",
    "bordeaux": "Бордо",
    "navy": "Нэви",
    "tobacco": "Табак",
    "graphite": "Графит",
    "olive": "Олива",
}
THEME_ORDER = ["navy", "hunter", "bordeaux", "tobacco", "graphite", "olive", "cream", "amoled"]

DEFAULT_THEME = "navy"
ACCENT_LIGHT = "#60a5fa"  # акцент-на-светлом (подпись "выбран" и т.п.) — не меняется по теме

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


def _mix_channel(c: int, target: int, amount: float) -> int:
    return round(c + (target - c) * amount)


def _lighten(hex_color: str, amount: float = 0.35) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"#{_mix_channel(r, 255, amount):02x}{_mix_channel(g, 255, amount):02x}{_mix_channel(b, 255, amount):02x}"


def _darken(hex_color: str, amount: float = 0.35) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"#{_mix_channel(r, 0, amount):02x}{_mix_channel(g, 0, amount):02x}{_mix_channel(b, 0, amount):02x}"


def _relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def theme_colors(theme_id: str) -> dict:
    """Единый язык "выбрано" во всём приложении — кольцо/точка цвета accent темы,
    а подпись/текст выбранного пункта — accent_light, чтобы не сливаться с фоном и
    читаться как акцент, а не как сам элемент управления.

    На тёмном фоне "светлее" и правда значит заметнее. На светлом (Крем) всё
    наоборот — высветлять акцент значит делать его ЕЩЁ бледнее на и так светлом
    фоне, текст просто пропадает. Поэтому для светлых тем accent_light — это
    затемнённый акцент, а не высветленный.

    accent_light не хранится в THEMES, а считается от accent — чтобы не держать
    два согласованных значения вручную."""
    palette = dict(THEMES.get(theme_id, THEMES[DEFAULT_THEME]))
    palette["accent_light"] = _darken(palette["accent"], 0.3) if palette["light"] else _lighten(palette["accent"])
    # Текст поверх ЗАЛИТОЙ акцентом кнопки (role="accent") — акцент сам по себе
    # бывает и светлым (amoled: почти белый), и тёмным (navy: синий), поэтому ему
    # нужен свой контрастный цвет текста, а не общий text_primary темы: раньше
    # кнопка "Сохранить" на amoled красила почти белый текст на почти белый фон.
    palette["on_accent"] = "#141414" if _relative_luminance(palette["accent"]) > 150 else "#ffffff"
    return palette


def text_primary_for(theme_id: str) -> str:
    """Основной цвет текста темы — нужен не только внутри QSS (build_stylesheet), но
    и местам вроде текста книги, которые рисуются вручную через HTML/QPainter и не
    участвуют в каскаде стилей приложения."""
    return "#241f16" if theme_colors(theme_id)["light"] else "#f1f5f9"


def text_secondary_for(theme_id: str) -> str:
    """Второстепенный цвет текста (неактивные вкладки, подписи) — та же логика, что
    text_primary_for, но для мест вроде NavBar/вкладок категорий, где цвет задаётся
    вручную через setStyleSheet, а не каскадом build_stylesheet."""
    return "#6b5d4f" if theme_colors(theme_id)["light"] else "#94a3b8"


def overlay_tint(theme_id: str, opacity: float) -> str:
    """rgba-подложка "на фоне фона" (активная кнопка-переключатель и т.п.). На тёмных
    темах светлая полупрозрачная заливка белым читается как подсветка; на светлых
    темах то же самое белым почти не отличимо от фона — там нужна тёмная заливка."""
    base = "0, 0, 0" if theme_colors(theme_id)["light"] else "255, 255, 255"
    return f"rgba({base}, {opacity})"


def resolve_font_family(font_family: str | None) -> str:
    """"system"/None → настоящее имя системного шрифта (а не выдуманное слово
    "Системный"), иначе — имя как есть: пресет или свой загруженный через
    QFontDatabase.addApplicationFont шрифт."""
    if not font_family or font_family == "system":
        from PySide6.QtGui import QFontDatabase

        return QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()
    return font_family


def build_stylesheet(theme_id: str = DEFAULT_THEME, font_size: int = 14, font_family: str | None = None) -> str:
    palette = theme_colors(theme_id)
    bg, bg2, accent, accent_hover = palette["bg"], palette["bg2"], palette["accent"], palette["accent_hover"]
    accent_light = palette["accent_light"]
    on_accent = palette["on_accent"]

    if palette["light"]:
        text_primary, text_secondary, text_dim = "#241f16", "#6b5d4f", "#8a7a68"
        border = "rgba(0, 0, 0, 0.12)"
        card_bg, card_bg_hover = "rgba(0, 0, 0, 0.05)", "rgba(0, 0, 0, 0.10)"
        header_bg = "rgba(0, 0, 0, 0.05)"
    else:
        text_primary, text_secondary, text_dim = "#f1f5f9", "#94a3b8", "#64748b"
        border = "rgba(255, 255, 255, 0.10)"
        card_bg, card_bg_hover = "rgba(255, 255, 255, 0.05)", "rgba(255, 255, 255, 0.10)"
        header_bg = "rgba(255, 255, 255, 0.06)"

    font_rule = f'font-family: "{font_family}";' if font_family and font_family != "system" else ""

    return f"""
QWidget {{
    background-color: {bg};
    color: {text_primary};
    font-size: {font_size}px;
    {font_rule}
}}

QLabel {{
    background: transparent;
}}

QLabel[role="title"] {{
    font-size: {font_size + 6}px;
    font-weight: 600;
}}

QLabel[role="muted"] {{
    color: {text_secondary};
}}

QPushButton {{
    background-color: {card_bg};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 14px;
    color: {text_primary};
}}

QPushButton:hover {{
    background-color: {card_bg_hover};
}}

QPushButton[role="accent"] {{
    background-color: {accent};
    color: {on_accent};
    border: none;
}}

QPushButton[role="accent"]:hover {{
    background-color: {accent_hover};
    color: {on_accent};
}}

QPushButton[role="chip_add"] {{
    border-style: dashed;
    border-width: 1px;
    border-color: {border};
    border-radius: 14px;
    padding: 4px 14px;
    background-color: transparent;
    color: {text_dim};
}}

QPushButton[role="chip_add"]:hover {{
    background-color: transparent;
    border-color: {accent_light};
    color: {accent_light};
}}

QPushButton[role="table_cell"] {{
    border-radius: 0px;
    border: none;
    background-color: transparent;
    color: {text_primary};
}}

QPushButton[role="table_cell"]:hover {{
    background-color: {card_bg_hover};
}}

QPushButton[role="font_row"] {{
    text-align: left;
    border: none;
    background: transparent;
    padding: 4px 8px;
    color: {text_primary};
}}

QPushButton[role="font_row"]:hover {{
    background-color: {card_bg};
}}

QPushButton[role="font_row"][active="true"] {{
    color: {accent_light};
}}

QLabel[role="theme_selected"] {{
    color: {accent_light};
}}

QLineEdit, QTextEdit {{
    background-color: {card_bg};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 10px;
    color: {text_primary};
    selection-background-color: {accent};
}}

QLineEdit:disabled, QTextEdit:disabled {{
    color: {text_dim};
    background-color: transparent;
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
    gridline-color: {border};
    border: 1px solid {border};
    border-radius: 8px;
}}

QTableWidget::item {{
    padding: 4px;
}}

QHeaderView::section {{
    background-color: {header_bg};
    color: {text_secondary};
    padding: 6px;
    border: none;
    border-right: 1px solid {border};
}}

QHeaderView {{
    background-color: transparent;
}}

QTableCornerButton::section {{
    background-color: {header_bg};
    border: none;
}}

QProgressBar {{
    background-color: {border};
    border: none;
    border-radius: 3px;
    max-height: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {accent_hover};
    border-radius: 3px;
}}

QWidget#NavBar {{
    background-color: rgba(0, 0, 0, 0.35);
    border-bottom: 1px solid {border};
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
    color: {text_dim};
}}

QFrame#NavTab QPushButton:hover {{
    background: transparent;
    color: {text_secondary};
}}

QFrame#NavTab[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {bg2}, stop:1 {bg});
}}

QFrame#NavTab[active="true"] QPushButton {{
    color: {text_primary};
    font-weight: 600;
}}
QWidget#StackBody {{
    background-color: {bg};
}}
"""


def apply_theme(app, theme_id: str = DEFAULT_THEME, font_size: int = 14, font_family: str | None = None) -> None:
    app.setStyleSheet(build_stylesheet(theme_id, font_size, font_family))
