"""ניהול מנוע ה-AI המקומי (llama.cpp llama-server) ושיחה איתו."""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
EXE = "llama-server.exe" if sys.platform == "win32" else "llama-server"

class EngineError(Exception):
    """שגיאה ידידותית בעברית מהמנוע."""


BACKEND_NAMES = {
    "cuda": "כרטיס מסך NVIDIA (CUDA)",
    "vulkan": "כרטיס מסך (Vulkan)",
    "cpu": "מעבד בלבד (CPU)",
}


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _has_nvidia():
    if shutil.which("nvidia-smi"):
        return True
    return Path(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "nvcuda.dll").exists()


class Engine:
    def __init__(self, base: Path, log_path: Path):
        self.base = Path(base)
        self.log_path = Path(log_path)
        self.proc = None
        self.port = None
        self.backend = None
        self.model = None
        self.ready = False
        self._gpu_names = None

    # ---------- גילוי מנועים ----------
    def gpu_names(self):
        """שמות כרטיסי המסך במחשב (נבדק פעם אחת)."""
        if self._gpu_names is None:
            self._gpu_names = []
            if sys.platform == "win32":
                try:
                    out = subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         "(Get-CimInstance Win32_VideoController).Name"],
                        capture_output=True, text=True, timeout=20, creationflags=NO_WINDOW).stdout
                    self._gpu_names = [l.strip() for l in out.splitlines() if l.strip()]
                except (OSError, subprocess.TimeoutExpired):
                    pass
        return self._gpu_names

    def _has_real_gpu(self):
        """כרטיס מסך אמיתי (NVIDIA/AMD). כרטיס מובנה של אינטל איטי יותר מהמעבד."""
        names = " ".join(self.gpu_names()).lower()
        return any(k in names for k in ("nvidia", "geforce", "rtx", "radeon", "amd", "arc"))
    def backends(self):
        """רשימת (שם, נתיב) של מנועים שקיימים, מהמהיר לאיטי."""
        found = []
        for name in ("cuda", "vulkan", "cpu"):
            exe = self.base / "engine" / name / EXE
            if exe.exists():
                if name == "cuda" and not _has_nvidia():
                    continue
                found.append((name, exe))
        if not found and shutil.which("llama-server"):
            found.append(("cpu", Path(shutil.which("llama-server"))))
        return found

    # ---------- הפעלה ----------
    def start(self, model_path, settings, status_cb):
        self.stop()
        backends = self.backends()
        if not backends:
            return False, "לא נמצא מנוע AI בתיקייה engine. התקן מחדש את התוכנה."
        wanted = settings["backend"]
        if wanted == "auto" and not self._has_real_gpu():
            backends = [b for b in backends if b[0] == "cpu"] or backends
        if wanted != "auto":
            backends = [b for b in backends if b[0] == wanted] + [b for b in backends if b[0] == "cpu" and wanted != "cpu"]
        last_err = ""
        for name, exe in backends:
            if name == "cpu":
                layer_opts = [0]
            elif int(settings["gpu_layers"]) >= 0:
                layer_opts = [int(settings["gpu_layers"])]
            else:
                layer_opts = [999, 48, 32, 20, 10]
            for ngl in layer_opts:
                status_cb(f"טוען מודל על {BACKEND_NAMES[name]}" + (f" ({ngl} שכבות)" if name != "cpu" else "") + "…")
                ok, err = self._launch(exe, name, model_path, settings, ngl)
                if ok:
                    return True, f"המודל פועל על {BACKEND_NAMES[name]}"
                last_err = err
        return False, "המנוע לא הצליח לעלות.\n" + last_err

    def _launch(self, exe, name, model_path, settings, ngl):
        self.port = _free_port()
        ctx = int(settings["context"])
        try:
            # מודל גדול במחשב עם מעט זיכרון – מקטינים את זיכרון השיחה כדי שייכנס
            from catalog import system_ram_gb
            if Path(model_path).stat().st_size > 6.5e9 and 0 < system_ram_gb() < 20:
                ctx = min(ctx, 8192)
        except OSError:
            pass
        args = [str(exe), "-m", str(model_path), "--host", "127.0.0.1", "--port", str(self.port),
                "-c", str(ctx), "-np", "1", "-ngl", str(ngl)]
        if int(settings["threads"]) > 0:
            args += ["-t", str(int(settings["threads"]))]
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        log = open(self.log_path, "w", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                     cwd=str(Path(exe).parent), creationflags=NO_WINDOW)
        deadline = time.time() + 20 * 60
        while time.time() < deadline:
            if self.proc.poll() is not None:
                log.close()
                self.proc = None
                return False, self._log_tail()
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=3) as r:
                    if r.status == 200:
                        self.backend, self.model = name, str(model_path)
                        self.ready = True
                        return True, ""
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(1)
        self.stop()
        return False, "תם הזמן לטעינת המודל."

    def _log_tail(self, n=15):
        try:
            lines = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(lines[-n:])
        except OSError:
            return ""

    def is_running(self):
        """המודל טעון ומוכן לשיחה (לא רק שהתהליך התחיל)."""
        return self.ready and self.proc is not None and self.proc.poll() is None

    def is_loading(self):
        return not self.ready and self.proc is not None and self.proc.poll() is None

    def stop(self):
        self.ready = False
        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    self.proc.kill()
                except OSError:
                    pass
        self.proc = None
        self.backend = None

    # ---------- שיחה ----------
    def chat_stream(self, messages, settings, stop_event):
        """מחזיר חלקי טקסט תוך כדי כתיבה. עוצר אחרי </action> כדי לחכות לאישור."""
        body = {
            "messages": messages,
            "stream": True,
            "temperature": float(settings["temperature"]),
            "top_p": 0.8,
            "top_k": 20,
            "repeat_penalty": 1.05,
            "max_tokens": int(settings["max_tokens"]),
            "stop": ["</action>"],
        }
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        resp = None
        for _ in range(90):  # 503 = המנוע עדיין טוען או עסוק – מחכים עד 3 דקות
            try:
                resp = urllib.request.urlopen(req, timeout=600)
                break
            except urllib.error.HTTPError as e:
                if e.code != 503 or stop_event.is_set():
                    raise EngineError(f"המנוע החזיר שגיאה {e.code}: {e.read()[:300].decode('utf-8', 'replace')}")
                time.sleep(2)
            except (urllib.error.URLError, ConnectionError) as e:
                self.ready = False
                raise EngineError("המנוע הפסיק לעבוד (כנראה נגמר הזיכרון). טען את המודל מחדש מתפריט מודל.") from e
        if resp is None:
            raise EngineError("המנוע עסוק יותר מדי זמן. נסה שוב בעוד רגע.")
        with resp:
            for raw in resp:
                if stop_event.is_set():
                    break
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0].get("delta", {}).get("content")
                except (ValueError, KeyError, IndexError):
                    continue
                if delta:
                    yield delta
