from __future__ import annotations

import json
from pathlib import Path

SETTINGS_PATH = Path(__file__).parent.parent / "app_settings.json"

DEFAULT_SETTINGS: dict = {
    "theme": "navy",
    "font_size": 16,
    "font_family": "Roboto",
    "custom_fonts": [],
}


def load_settings() -> dict:
    stored: dict = {}
    if SETTINGS_PATH.exists():
        try:
            stored = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            stored = {}
    return {**DEFAULT_SETTINGS, **stored}


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
