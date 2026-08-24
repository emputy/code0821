import json
from pathlib import Path

SETTINGS_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.json"

DEFAULTS = {
    "api_key": "",
    "ai_enabled": False,
    "translate_enabled": True,
    "model": "deepseek-chat",
    "schedule_interval_days": 14,
    "dark_theme": True,
    "last_run_at": "",
}


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            merged = dict(DEFAULTS)
            merged.update(data)
            return merged
        except Exception:
            pass
    return dict(DEFAULTS)


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
