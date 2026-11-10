from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt

KEYBINDINGS_PATH = Path(__file__).parent.parent / "keybindings.json"

DEFAULT_KEYS: dict[str, dict] = {
    "nav_library": {"key": Qt.Key.Key_Escape.value, "ctrl": False, "shift": False, "label": "Перейти в библиотеку"},
    "nav_storage": {"key": Qt.Key.Key_E.value, "ctrl": False, "shift": False, "label": "Перейти в хранилище"},
    "nav_settings": {"key": Qt.Key.Key_C.value, "ctrl": False, "shift": False, "label": "Перейти в настройки"},
    "library_prev_book": {"key": Qt.Key.Key_Left.value, "ctrl": False, "shift": False, "label": "Библиотека: предыдущая книга"},
    "library_next_book": {"key": Qt.Key.Key_Right.value, "ctrl": False, "shift": False, "label": "Библиотека: следующая книга"},
    "library_prev_category": {"key": Qt.Key.Key_Up.value, "ctrl": False, "shift": False, "label": "Библиотека: предыдущая категория"},
    "library_next_category": {"key": Qt.Key.Key_Down.value, "ctrl": False, "shift": False, "label": "Библиотека: следующая категория"},
    "library_open": {"key": Qt.Key.Key_Space.value, "ctrl": False, "shift": False, "label": "Библиотека: читать"},
    "storage_left": {"key": Qt.Key.Key_Left.value, "ctrl": False, "shift": False, "label": "Хранилище: курсор влево"},
    "storage_right": {"key": Qt.Key.Key_Right.value, "ctrl": False, "shift": False, "label": "Хранилище: курсор вправо"},
    "storage_up": {"key": Qt.Key.Key_Up.value, "ctrl": False, "shift": False, "label": "Хранилище: курсор вверх"},
    "storage_down": {"key": Qt.Key.Key_Down.value, "ctrl": False, "shift": False, "label": "Хранилище: курсор вниз"},
    "storage_open": {"key": Qt.Key.Key_Return.value, "ctrl": False, "shift": False, "label": "Хранилище: открыть"},
    "storage_delete": {"key": Qt.Key.Key_Delete.value, "ctrl": False, "shift": False, "label": "Хранилище: удалить заметку"},
    "tab_next": {"key": Qt.Key.Key_Right.value, "ctrl": False, "shift": False, "alt": True, "label": "Следующая вкладка"},
    "tab_prev": {"key": Qt.Key.Key_Left.value, "ctrl": False, "shift": False, "alt": True, "label": "Предыдущая вкладка"},
    "focus_chat": {"key": Qt.Key.Key_Slash.value, "ctrl": False, "shift": False, "label": "Фокус на поле ввода чата"},
}


def load_keybindings() -> dict[str, dict]:
    stored: dict = {}
    if KEYBINDINGS_PATH.exists():
        try:
            stored = json.loads(KEYBINDINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            stored = {}

    merged = {}
    for action_id, default in DEFAULT_KEYS.items():
        merged[action_id] = {**default, **stored.get(action_id, {})}
    return merged


def save_keybindings(keys: dict[str, dict]) -> None:
    KEYBINDINGS_PATH.write_text(
        json.dumps(keys, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def matches(event, action_id: str, keys: dict[str, dict]) -> bool:
    binding = keys.get(action_id)
    if not binding:
        return False
    if event.key() != binding["key"]:
        return False
    ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
    shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
    alt = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
    return (
        ctrl == binding.get("ctrl", False)
        and shift == binding.get("shift", False)
        and alt == binding.get("alt", False)
    )
