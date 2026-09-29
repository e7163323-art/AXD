"""הכלים שה-AI יכול להפעיל על המחשב. כל פעולה מבוצעת רק אחרי אישור של המשתמש."""
import os
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

ACTION_RE = re.compile(r"<action\b([^>]*)>(.*?)</action>", re.S)
OPEN_ACTION_RE = re.compile(r"<action\b([^>]*)>(.*)$", re.S)
ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')

# שם הכלי: (תיאור בעברית, רמת סיכון 0-2)
TOOLS = {
    "write_file": ("כתיבת קובץ", 1),
    "read_file": ("קריאת קובץ", 0),
    "list_dir": ("הצגת תוכן תיקייה", 0),
    "make_dir": ("יצירת תיקייה", 0),
    "delete": ("מחיקת קובץ/תיקייה", 2),
    "run_command": ("הרצת פקודה במחשב", 2),
    "open": ("פתיחת קובץ / תוכנה / אתר", 1),
    "build_python_exe": ("בניית EXE מקוד פייתון", 1),
    "build_csharp_exe": ("בניית EXE מקוד C#", 1),
    "zip": ("כיווץ תיקייה ל-ZIP", 0),
}

ATTR_NAMES = {
    "path": "נתיב", "shell": "סוג מסוף", "cwd": "תיקיית עבודה", "name": "שם",
    "windowed": "חלון גרפי", "icon": "אייקון", "out": "קובץ יעד", "target": "יעד",
}


@dataclass
class Action:
    name: str
    attrs: dict = field(default_factory=dict)
    body: str = ""

    @property
    def title(self):
        return TOOLS.get(self.name, (self.name, 2))[0]

    @property
    def risk(self):
        return TOOLS.get(self.name, (self.name, 2))[1]


def _clean_body(body: str) -> str:
    if body.startswith("\n"):
        body = body[1:]
    stripped = body.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        body = "\n".join(lines[1:-1]) + "\n"
    return body


def parse_actions(text: str):
    actions = []
    for attrs, body in ACTION_RE.findall(text):
        a = dict(ATTR_RE.findall(attrs))
        name = a.pop("name", "").strip()
        if name:
            actions.append(Action(name, a, _clean_body(body)))
    return actions


def split_for_display(text: str):
    """מחלק טקסט לחלקים רגילים ולבלוקי פעולה (כולל פעולה שעדיין נכתבת)."""
    parts, pos = [], 0
    for m in ACTION_RE.finditer(text):
        parts.append(("text", text[pos:m.start()]))
        a = dict(ATTR_RE.findall(m.group(1)))
        parts.append(("action", Action(a.pop("name", "?"), a, _clean_body(m.group(2)))))
        pos = m.end()
    rest = text[pos:]
    m = OPEN_ACTION_RE.search(rest)
    if m and ">" in rest[m.start():]:
        parts.append(("text", rest[:m.start()]))
        a = dict(ATTR_RE.findall(m.group(1)))
        parts.append(("action", Action(a.pop("name", "?"), a, _clean_body(m.group(2)))))
    else:
        parts.append(("text", re.sub(r"<action\b[^>]*$", "", rest)))
    return parts


class Toolbox:
    def __init__(self, settings, base: Path):
        self.settings = settings
        self.base = Path(base)

    # ---------- עזרים ----------
    def resolve(self, p: str) -> Path:
        p = os.path.expandvars(os.path.expanduser((p or "").strip().strip('"')))
        path = Path(p)
        if not path.is_absolute():
            path = Path(self.settings["workspace"]) / path
        return path

    def python_exe(self):
        bundled = self.base / "runtime" / "python" / ("python.exe" if sys.platform == "win32" else "bin/python3")
        if bundled.exists():
            return str(bundled)
        return shutil.which("python") or shutil.which("python3") or sys.executable

    @staticmethod
    def csc_exe():
        root = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Microsoft.NET"
        for fw in ("Framework64", "Framework"):
            c = root / fw / "v4.0.30319" / "csc.exe"
            if c.exists():
                return str(c)
        return shutil.which("csc")

    def _run(self, args, cwd=None, shell=False):
        timeout = int(self.settings["command_timeout"])
        try:
            r = subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout, shell=shell,
                               stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
        except subprocess.TimeoutExpired:
            return f"הפקודה נעצרה אחרי {timeout} שניות (חריגה מזמן)."
        except OSError as e:
            return f"שגיאה בהרצה: {e}"
        out = self._decode(r.stdout) + ("\n" + self._decode(r.stderr) if r.stderr else "")
        out = out.strip() or "(אין פלט)"
        if len(out) > 8000:
            out = out[:3000] + "\n...[קוצר]...\n" + out[-4500:]
        return f"קוד יציאה: {r.returncode}\n{out}"

    @staticmethod
    def _decode(b: bytes) -> str:
        for enc in ("utf-8", "cp1255", "cp862"):
            try:
                return b.decode(enc)
            except UnicodeDecodeError:
                continue
        return b.decode("utf-8", errors="replace")

    # ---------- ביצוע ----------
    def execute(self, a: Action) -> str:
        fn = getattr(self, "t_" + a.name, None)
        if fn is None:
            return f"כלי לא מוכר: {a.name}. הכלים הזמינים: {', '.join(TOOLS)}"
        try:
            return fn(a)
        except Exception as e:  # noqa: BLE001 - מחזירים את השגיאה למודל כדי שיתקן
            return f"שגיאה: {type(e).__name__}: {e}"

    def t_write_file(self, a):
        p = self.resolve(a.attrs.get("path", ""))
        p.parent.mkdir(parents=True, exist_ok=True)
        encoding = "utf-8-sig" if p.suffix.lower() in (".ps1", ".cs") else "utf-8"
        p.write_text(a.body, encoding=encoding, newline="\r\n" if p.suffix.lower() in (".bat", ".cmd") else None)
        return f"הקובץ נשמר: {p} ({len(a.body.splitlines())} שורות)"

    def t_read_file(self, a):
        p = self.resolve(a.attrs.get("path", ""))
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) > 20000:
            text = text[:20000] + "\n...[הקובץ קוצר]"
        return f"תוכן {p}:\n{text}"

    def t_list_dir(self, a):
        p = self.resolve(a.attrs.get("path", "."))
        rows = []
        for i, e in enumerate(sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))):
            if i >= 300:
                rows.append("...")
                break
            rows.append(f"[תיקייה] {e.name}" if e.is_dir() else f"{e.name}  ({e.stat().st_size:,} בתים)")
        return f"תוכן {p}:\n" + ("\n".join(rows) or "(ריקה)")

    def t_make_dir(self, a):
        p = self.resolve(a.attrs.get("path", ""))
        p.mkdir(parents=True, exist_ok=True)
        return f"התיקייה נוצרה: {p}"

    def t_delete(self, a):
        p = self.resolve(a.attrs.get("path", ""))
        if len(p.parts) <= 2:
            return "סירוב: לא מוחקים תיקיית שורש או כונן שלם."
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        return f"נמחק: {p}"

    def t_run_command(self, a):
        cmd = a.body.strip()
        cwd = str(self.resolve(a.attrs["cwd"])) if a.attrs.get("cwd") else self.settings["workspace"]
        Path(cwd).mkdir(parents=True, exist_ok=True)
        shell = a.attrs.get("shell", "powershell").lower()
        if sys.platform != "win32":
            return self._run(cmd, cwd=cwd, shell=True)
        if shell == "cmd":
            return self._run(["cmd", "/d", "/c", "chcp 65001>nul & " + cmd], cwd=cwd)
        ps = "[Console]::OutputEncoding=[Text.Encoding]::UTF8; $ProgressPreference='SilentlyContinue'; " + cmd
        return self._run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], cwd=cwd)

    def t_open(self, a):
        target = (a.attrs.get("target") or a.attrs.get("path") or a.body).strip()
        if not re.match(r"^[a-z]+://", target, re.I):
            target = str(self.resolve(target))
        if sys.platform == "win32":
            os.startfile(target)  # noqa: S606 - המשתמש אישר
        else:
            subprocess.Popen(["xdg-open", target])
        return f"נפתח: {target}"

    def t_build_python_exe(self, a):
        src = self.resolve(a.attrs.get("path", ""))
        name = a.attrs.get("name") or src.stem
        out = self.resolve(a.attrs["out"]) if a.attrs.get("out") else src.parent / "dist"
        work = src.parent / "build"
        args = [self.python_exe(), "-m", "PyInstaller", "--noconfirm", "--onefile", "--clean",
                "--name", name, "--distpath", str(out), "--workpath", str(work), "--specpath", str(work)]
        if a.attrs.get("windowed", "true").lower() in ("true", "1", "yes", "כן"):
            args.append("--windowed")
        if a.attrs.get("icon"):
            args += ["--icon", str(self.resolve(a.attrs["icon"]))]
        args.append(str(src))
        result = self._run(args, cwd=str(src.parent))
        exe = out / (name + (".exe" if sys.platform == "win32" else ""))
        if exe.exists():
            return f"✔ קובץ EXE נבנה בהצלחה: {exe}\n\n{result[-1500:]}"
        return f"✖ הבנייה נכשלה.\n{result}"

    def t_build_csharp_exe(self, a):
        csc = self.csc_exe()
        if not csc:
            return "לא נמצא מהדר C# (csc.exe) במחשב."
        src = self.resolve(a.attrs.get("path", ""))
        out = self.resolve(a.attrs["out"]) if a.attrs.get("out") else src.with_suffix(".exe")
        out.parent.mkdir(parents=True, exist_ok=True)
        target = "winexe" if a.attrs.get("windowed", "true").lower() in ("true", "1", "yes", "כן") else "exe"
        args = [csc, "/nologo", "/utf8output", "/codepage:65001", "/optimize+", f"/target:{target}",
                f"/out:{out}", "/r:System.Windows.Forms.dll", "/r:System.Drawing.dll"]
        if a.attrs.get("icon"):
            args.append(f"/win32icon:{self.resolve(a.attrs['icon'])}")
        args.append(str(src))
        result = self._run(args, cwd=str(src.parent))
        if out.exists():
            return f"✔ קובץ EXE נבנה בהצלחה: {out}\n{result}"
        return f"✖ הבנייה נכשלה.\n{result}"

    def t_zip(self, a):
        src = self.resolve(a.attrs.get("path", ""))
        out = self.resolve(a.attrs["out"]) if a.attrs.get("out") else src.with_suffix(".zip")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for f in src.rglob("*"):
                if f.is_file():
                    z.write(f, f.relative_to(src))
        return f"נוצר קובץ ZIP: {out}"
