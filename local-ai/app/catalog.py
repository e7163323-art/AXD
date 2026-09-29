"""קטלוג מודלים והורדה עם המשך (resume)."""
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

MODELS = [
    {
        "id": "qwen-coder-32b-q5",
        "name": "Qwen2.5-Coder 32B – איכות מקסימלית (Q5_K_M)",
        "repo": "bartowski/Qwen2.5-Coder-32B-Instruct-GGUF",
        "file": "Qwen2.5-Coder-32B-Instruct-Q5_K_M.gguf",
        "size_gb": 23.3,
        "ram_gb": 32,
        "desc": "הרמה הגבוהה ביותר לכתיבת קוד. דורש מחשב חזק (32GB זיכרון ומעלה).",
    },
    {
        "id": "qwen-coder-32b-q4",
        "name": "Qwen2.5-Coder 32B – מומלץ (Q4_K_M)",
        "repo": "bartowski/Qwen2.5-Coder-32B-Instruct-GGUF",
        "file": "Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf",
        "size_gb": 19.9,
        "ram_gb": 24,
        "desc": "איזון מצוין בין איכות למהירות. רמת קוד גבוהה מאוד.",
    },
    {
        "id": "qwen-coder-14b-q8",
        "name": "Qwen2.5-Coder 14B – מהיר (Q8_0)",
        "repo": "bartowski/Qwen2.5-Coder-14B-Instruct-GGUF",
        "file": "Qwen2.5-Coder-14B-Instruct-Q8_0.gguf",
        "size_gb": 15.7,
        "ram_gb": 20,
        "desc": "מהיר יותר, מתאים ל-16-24GB זיכרון.",
    },
    {
        "id": "qwen-coder-14b-q3",
        "name": "Qwen2.5-Coder 14B – הכי חכם שנכנס ל-12GB (Q3_K_M)",
        "repo": "bartowski/Qwen2.5-Coder-14B-Instruct-GGUF",
        "file": "Qwen2.5-Coder-14B-Instruct-Q3_K_M.gguf",
        "size_gb": 7.3,
        "ram_gb": 12,
        "desc": "מודל גדול פי 2 מה-7B: עברית וקוד טובים יותר, אבל איטי יותר.",
    },
    {
        "id": "qwen-coder-7b-q8",
        "name": "Qwen2.5-Coder 7B – למחשבים חלשים (Q8_0)",
        "repo": "bartowski/Qwen2.5-Coder-7B-Instruct-GGUF",
        "file": "Qwen2.5-Coder-7B-Instruct-Q8_0.gguf",
        "size_gb": 8.1,
        "ram_gb": 16,
        "desc": "למחשבים עם 16GB זיכרון.",
    },
    {
        "id": "qwen-coder-7b-q5",
        "name": "Qwen2.5-Coder 7B – למחשבים עם 8-12GB (Q5_K_M)",
        "repo": "bartowski/Qwen2.5-Coder-7B-Instruct-GGUF",
        "file": "Qwen2.5-Coder-7B-Instruct-Q5_K_M.gguf",
        "size_gb": 5.4,
        "ram_gb": 8,
        "desc": "מתאים למחשבים עם 8-12GB זיכרון. כותב קוד טוב, קצת פחות חכם מהגדולים.",
    },
]


MIRRORS = [
    "https://huggingface.co/{repo}/resolve/main/{file}?download=true",
    "https://hf-mirror.com/{repo}/resolve/main/{file}?download=true",
]


def model_urls(m):
    """כמה אתרי הורדה – אם אחד חסום (למשל בסינון אינטרנט) עוברים לבא."""
    urls = [u.format(repo=m["repo"], file=m["file"]) for u in MIRRORS]
    official = m["repo"].replace("bartowski/", "Qwen/")
    urls.append(f"https://modelscope.cn/models/{official}/resolve/master/{m['file'].lower()}")
    return urls


def model_path(models_dir, m) -> Path:
    return Path(models_dir) / m["file"]


def is_downloaded(models_dir, m) -> bool:
    p = model_path(models_dir, m)
    return p.exists() and p.stat().st_size > m["size_gb"] * 0.9e9


def system_ram_gb() -> float:
    try:
        if sys.platform == "win32":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return stat.ullTotalPhys / 1024 ** 3
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 ** 3
    except (OSError, ValueError, AttributeError):
        return 0.0


def recommend(ram_gb: float):
    for m in MODELS:
        if ram_gb >= m["ram_gb"] and m["id"] != "qwen-coder-32b-q5":
            return m
    return MODELS[-1]


class Downloader:
    """הורדה ברקע לקובץ .part עם אפשרות המשך אחרי ניתוק."""

    def __init__(self, urls, dest: Path, on_progress, on_done):
        self.urls = list(urls)
        self.url = self.urls[0]
        self.dest = Path(dest)
        self.part = self.dest.with_suffix(self.dest.suffix + ".part")
        self.on_progress = on_progress
        self.on_done = on_done
        self._cancel = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def cancel(self):
        self._cancel.set()

    def _run(self):
        retries = 0
        while not self._cancel.is_set():
            try:
                if self._download_once():
                    return
                if self._cancel.is_set():
                    break
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 404, 451) and self.urls.index(self.url) + 1 < len(self.urls):
                    self.url = self.urls[self.urls.index(self.url) + 1]
                    continue
                if e.code in (401, 403, 404, 451):
                    self.on_done(False, f"ההורדה נחסמה ({e.code}). כנראה שסינון האינטרנט חוסם את אתרי המודלים.\n"
                                        "אפשר להוריד את הקובץ במחשב אחר ולבחור 'קובץ GGUF קיים'.")
                    return
                retries += 1
                time.sleep(min(30, 2 * retries))
            except Exception as e:  # noqa: BLE001 - רשת יכולה להיכשל בכל דרך
                retries += 1
                if retries > 20:
                    self.on_done(False, f"ההורדה נכשלה: {e}")
                    return
                time.sleep(min(30, 2 * retries))
        self.on_done(False, "ההורדה בוטלה. אפשר להמשיך מאותה נקודה בפעם הבאה.")

    def _download_once(self) -> bool:
        self.dest.parent.mkdir(parents=True, exist_ok=True)
        have = self.part.stat().st_size if self.part.exists() else 0
        req = urllib.request.Request(self.url, headers={"User-Agent": "Gaon-Local-AI/1.0"})
        if have:
            req.add_header("Range", f"bytes={have}-")
        with urllib.request.urlopen(req, timeout=60) as resp:
            if have and resp.status != 206:
                have = 0  # השרת לא תומך בהמשך – מתחילים מחדש
            length = int(resp.headers.get("Content-Length") or 0)
            total = have + length if length else 0
            mode = "ab" if have else "wb"
            done = have
            t0, d0 = time.time(), done
            with open(self.part, mode) as f:
                while not self._cancel.is_set():
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    now = time.time()
                    if now - t0 >= 0.5:
                        speed = (done - d0) / (now - t0)
                        t0, d0 = now, done
                        self.on_progress(done, total, speed)
        if self._cancel.is_set():
            return False
        if total and done < total:
            raise IOError("החיבור נקטע")
        os.replace(self.part, self.dest)
        self.on_progress(done, total or done, 0)
        self.on_done(True, "ההורדה הושלמה! מעכשיו הכל עובד 100% בלי אינטרנט.")
        return True
