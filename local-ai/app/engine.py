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

    # ---------- גילוי מנועים ----------
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
        args = [str(exe), "-m", str(model_path), "--host", "127.0.0.1", "--port", str(self.port),
                "-c", str(int(settings["context"])), "-np", "1", "-ngl", str(ngl)]
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
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
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
            "top_p": 0.9,
            "max_tokens": int(settings["max_tokens"]),
            "stop": ["</action>"],
        }
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=600) as resp:
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
