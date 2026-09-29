"""הגדרות ונתיבים של האפליקציה."""
import json
import os
import sys
from pathlib import Path

APP_NAME = "גאון"
APP_TITLE = "גאון – עוזר AI מקומי"
APP_VERSION = "1.1.0"
DEVELOPER = "יהודי פשוט"
DEVELOPER_PHONE = "058-3283388"


def base_dir() -> Path:
    """התיקייה שבה נמצאת התוכנה (ליד Gaon.exe)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def data_dir() -> Path:
    """תיקיית הנתונים: ליד התוכנה אם אפשר לכתוב שם, אחרת ב-LocalAppData."""
    local = base_dir()
    if _is_writable(local / "data"):
        return local / "data"
    fallback = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Gaon"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _default_models_dir() -> str:
    local = base_dir() / "models"
    if _is_writable(local):
        return str(local)
    return str(data_dir() / "models")


def _default_workspace() -> str:
    local = base_dir() / "פרויקטים"
    if _is_writable(local):
        return str(local)
    return str(Path.home() / "Documents" / "גאון-פרויקטים")


DEFAULTS = {
    "models_dir": "",
    "workspace": "",
    "model_file": "",          # נתיב מלא לקובץ GGUF הפעיל
    "backend": "auto",         # auto / cuda / vulkan / cpu
    "gpu_layers": -1,          # -1 = אוטומטי
    "context": 16384,
    "threads": 0,              # 0 = אוטומטי
    "temperature": 0.15,
    "max_tokens": 8192,
    "command_timeout": 600,
    "max_steps": 30,
    "font_size": 12,
    "autoload": True,
}


class Settings:
    def __init__(self):
        self.path = data_dir() / "settings.json"
        self.values = dict(DEFAULTS)
        try:
            if self.path.exists():
                self.values.update(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
        # גרסה 2: טמפרטורה נמוכה יותר = פחות שגיאות כתיב בעברית
        if self.values.get("settings_version", 1) < 2:
            if float(self.values.get("temperature", 0.15)) >= 0.3:
                self.values["temperature"] = 0.15
            self.values["settings_version"] = 2
        if not self.values["models_dir"]:
            self.values["models_dir"] = _default_models_dir()
        if not self.values["workspace"]:
            self.values["workspace"] = _default_workspace()
        Path(self.values["models_dir"]).mkdir(parents=True, exist_ok=True)
        Path(self.values["workspace"]).mkdir(parents=True, exist_ok=True)

    def __getitem__(self, key):
        return self.values.get(key, DEFAULTS.get(key))

    def __setitem__(self, key, value):
        self.values[key] = value

    def save(self):
        try:
            self.path.write_text(json.dumps(self.values, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
