"""הכלים שה-AI יכול להפעיל על המחשב. כל פעולה מבוצעת רק אחרי אישור של המשתמש."""
import os
import re
import shutil
import subprocess
import sys
import time
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
    "remember": ("שמירה בזיכרון", 0),
    "create_image": ("יצירת תמונה", 1),
}
AUTO_APPROVE = {"remember"}   # לא משנה שום דבר במחשב – לא צריך אישור

ATTR_NAMES = {
    "path": "נתיב", "shell": "סוג מסוף", "cwd": "תיקיית עבודה", "name": "שם",
    "windowed": "חלון גרפי", "icon": "אייקון", "out": "קובץ יעד", "target": "יעד", "text": "תוכן", "prompt": "תיאור",
}


def _parse_attrs(attr_text: str):
    """הראשון מבין name=... הוא שם הפעולה; name נוסף (למשל שם ה-EXE) נשאר כתכונה."""
    action, attrs = "", {}
    for k, v in ATTR_RE.findall(attr_text):
        if k == "name" and not action:
            action = v.strip()
        else:
            attrs[k] = v
    return action, attrs


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
        name, a = _parse_attrs(attrs)
        if name:
            actions.append(Action(name, a, _clean_body(body)))
    return actions


def split_for_display(text: str):
    """מחלק טקסט לחלקים רגילים ולבלוקי פעולה (כולל פעולה שעדיין נכתבת)."""
    parts, pos = [], 0
    for m in ACTION_RE.finditer(text):
        parts.append(("text", text[pos:m.start()]))
        name, a = _parse_attrs(m.group(1))
        parts.append(("action", Action(name or "?", a, _clean_body(m.group(2)))))
        pos = m.end()
    rest = text[pos:]
    m = OPEN_ACTION_RE.search(rest)
    if m and ">" in rest[m.start():]:
        parts.append(("text", rest[:m.start()]))
        name, a = _parse_attrs(m.group(1))
        parts.append(("action", Action(name or "?", a, _clean_body(m.group(2)))))
    else:
        parts.append(("text", re.sub(r"<action\b[^>]*$", "", rest)))
    return parts


# ---------- שכבת הגנה: פעולות שעלולות להרוס את המחשב נחסמות גם אם אישרת ----------
# שמירה על סינון האינטרנט: שינויי רשת/פרוקסי/DNS ותוכנות לעקיפת סינון נחסמים
FILTER_WORDS = r"(vpn|proxy|פרוקסי|tor\b|torbrowser|psiphon|ultrasurf|hotspot.?shield|windscribe|protonvpn|nordvpn|expressvpn|" \
               r"openvpn|wireguard|softether|zenmate|hola|freegate|lantern|v2ray|shadowsocks|cloudflare.?warp|1\.1\.1\.1|8\.8\.8\.8|" \
               r"netfree|נטפרי|net-free|netspark|נטספארק|rimon|רימון|etrog|אתרוג|yoshvim|יושבים|meshimer|משימר|koshernet|nativ|נתיב|internet.?rimon)"
FILTER_BLOCK = "עקיפה או שינוי של סינון האינטרנט"

BLOCKED_COMMANDS = [
    (r"netsh\s+(winhttp\s+set\s+proxy|interface\s+(ip|ipv4|ipv6)\s+(set|add)\s+dns)", FILTER_BLOCK),
    (r"set-dnsclientserveraddress|set-netipinterface|set-netadapter|disable-netadapterbinding", FILTER_BLOCK),
    (r"proxyserver|proxyenable|proxyoverride|autoconfigurl|internet settings", FILTER_BLOCK),
    (r"drivers[\\/]+etc[\\/]+hosts", FILTER_BLOCK),
    (r"\bnetsh\b.*\b(advfirewall|firewall)\b", FILTER_BLOCK),
    (r"root[\\/]+certificates|import-certificate|certutil\s+.*-(addstore|delstore)", FILTER_BLOCK),
    (FILTER_WORDS, FILTER_BLOCK),
    (r"\bformat(-volume)?\s+[a-z]:", "פרמוט כונן"),
    (r"\bformat-volume\b|\bclear-disk\b|\binitialize-disk\b|\bremove-partition\b", "מחיקת דיסק/מחיצה"),
    (r"\bdiskpart\b", "diskpart"),
    (r"\bbcdedit\b|\bbootrec\b", "שינוי הגדרות אתחול"),
    (r"\bcipher\s+/w", "מחיקת נתונים לצמיתות"),
    (r"\bvssadmin\b.*\bdelete\b|\bwbadmin\b.*\bdelete\b", "מחיקת נקודות שחזור / גיבויים"),
    (r"\breg(\.exe)?\s+delete\s+(hklm|hkey_local_machine)", "מחיקה מהרישום של המערכת"),
    (r"(remove-item|\brd\b|\brmdir\b|\bdel\b|\berase\b|\brm\b).*(\\windows|system32|program files|\\boot)", "מחיקת קבצי מערכת"),
    (r"(remove-item|\brd\b|\brmdir\b|\bdel\b|\brm\b)[^|;&]*\s[a-z]:\\?\*?[\"']?\s*(-|/|$)", "מחיקת כונן שלם"),
    (r"set-mppreference\b.*-disable|\bsc(\.exe)?\s+(stop|config|delete)\s+windefend", "כיבוי האנטי-וירוס"),
    (r"netsh\s+advfirewall\s+set\s+\w+\s+state\s+off", "כיבוי חומת האש"),
    (r"\btakeown\b.*(windows|system32)|\bicacls\b.*(windows|system32)", "שינוי הרשאות של קבצי מערכת"),
]
WARN_COMMANDS = [
    (r"\bshutdown\b|\brestart-computer\b|\bstop-computer\b", "המחשב יכבה או יופעל מחדש"),
    (r"\breg(\.exe)?\s+add\s+(hklm|hkey_local_machine)|set-itemproperty\s+.*hklm:", "שינוי ברישום של המערכת"),
    (r"\bstop-process\b|\btaskkill\b", "סגירה בכוח של תוכנות"),
    (r"\bset-executionpolicy\b", "שינוי מדיניות הרצת סקריפטים"),
    (r"\bschtasks\b.*/create|\bregister-scheduledtask\b", "יצירת משימה מתוזמנת"),
    (r"\bsc(\.exe)?\s+(config|delete|create)\b", "שינוי שירותי מערכת"),
    (r"\buninstall|\bmsiexec\b.*/x", "הסרת תוכנה"),
    (r"remove-item\b.*-recurse|\brd\b\s+/s|\brmdir\b\s+/s|\bdel\b\s+/s", "מחיקה של תיקייה שלמה"),
]


def _protected_dirs():
    root = Path(os.environ.get("SystemDrive", "C:") + "\\")
    dirs = [Path(os.environ.get("SystemRoot", r"C:\Windows")),
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
            root / "ProgramData" / "Microsoft", root / "Boot", root / "Recovery"]
    return [d for d in dirs if str(d)]


def safety_check(a, resolve):
    """מחזיר (סיבת חסימה או None, אזהרה או None)."""
    if a.name == "run_command":
        cmd = a.body.lower()
        for pat, why in BLOCKED_COMMANDS:
            if re.search(pat, cmd):
                return f"הפקודה נחסמה להגנת המחשב: {why}.", None
        warns = [why for pat, why in WARN_COMMANDS if re.search(pat, cmd)]
        return None, ("שים לב: " + ", ".join(warns)) if warns else None
    if a.name == "create_image" and NO_PEOPLE_RE.search(a.attrs.get("prompt") or a.body):
        return "נחסם: גאון יוצר רק תמונות בלי אנשים.", None
    if a.name == "open":
        target = (a.attrs.get("target") or a.attrs.get("path") or a.body).lower()
        if re.search(FILTER_WORDS, target):
            return f"נחסם: {FILTER_BLOCK}.", None
    if a.name in ("write_file", "delete", "make_dir", "zip"):
        target = resolve(a.attrs.get("out") or a.attrs.get("path", "")) if a.name == "zip" else resolve(a.attrs.get("path", ""))
        try:
            t = target.resolve()
        except OSError:
            t = target
        for d in _protected_dirs():
            try:
                t.relative_to(d.resolve())
                return f"נחסם: אסור לשנות קבצים בתיקיית המערכת {d}.", None
            except (ValueError, OSError):
                continue
        if a.name == "delete":
            home = Path.home().resolve()
            if t == home or t.parent == home or len(t.parts) <= 2:
                return "נחסם: אסור למחוק תיקייה ראשית (כונן, תיקיית המשתמש, שולחן העבודה, המסמכים וכו').", None
    return None, None


class Toolbox:
    def __init__(self, settings, base: Path, memory=None):
        self.settings = settings
        self.base = Path(base)
        self.memory = memory

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
    def check(self, a: Action):
        return safety_check(a, self.resolve)

    def execute(self, a: Action) -> str:
        blocked, _ = self.check(a)
        if blocked:
            return blocked + " אל תנסה לעקוף את החסימה."
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

    def t_remember(self, a):
        if self.memory is None:
            return "אין זיכרון זמין."
        return self.memory.add(a.attrs.get("text") or a.body)

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
        target = (a.attrs.get("target") or a.attrs.get("path") or a.body).strip().strip('"')
        is_uri = re.match(r"^[a-z][a-z0-9+.-]+:", target, re.I) and not re.match(r"^[a-z]:[\\/]", target, re.I)
        if not is_uri:
            local = self.resolve(target)
            # שם של תוכנה (notepad.exe, calc) – ווינדוס ימצא אותה לבד
            if local.exists() or "\\" in target or "/" in target:
                target = str(local)
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


# ---------- זיהוי מהיר של בקשות פשוטות (בלי לחכות למודל) ----------
APPS = {
    "פנקס רשימות": "notepad.exe", "פנקס": "notepad.exe", "notepad": "notepad.exe", "נוטפד": "notepad.exe",
    "מחשבון": "calc.exe", "צייר": "mspaint.exe", "paint": "mspaint.exe",
    "סייר הקבצים": "explorer.exe", "סייר קבצים": "explorer.exe", "סייר": "explorer.exe",
    "כרום": "chrome.exe", "גוגל כרום": "chrome.exe", "chrome": "chrome.exe",
    "אדג": "msedge.exe", "אדג'": "msedge.exe", "edge": "msedge.exe",
    "מנהל המשימות": "taskmgr.exe", "מנהל משימות": "taskmgr.exe",
    "לוח הבקרה": "control.exe", "לוח בקרה": "control.exe",
    "הגדרות": "ms-settings:", "הגדרות המחשב": "ms-settings:", "הגדרות ווינדוס": "ms-settings:",
    "שורת הפקודה": "cmd.exe", "cmd": "cmd.exe", "פאוורשל": "powershell.exe", "powershell": "powershell.exe",
    "וורד": "winword.exe", "אקסל": "excel.exe", "פאוורפוינט": "powerpnt.exe",
    "מקלדת על המסך": "osk.exe", "כלי חיתוך": "snippingtool.exe", "מידע מערכת": "msinfo32.exe",
}
OPEN_RE = re.compile(r"^\s*(?:ת?פתח|תפתחי|ת?פעיל|תריץ|הרץ)\s+(?:לי\s+)?(?:את\s+)?(.+?)[\s.!?]*$")


def quick_intent(text: str, workspace: str = ""):
    """אם זו בקשה פשוטה (פתיחת תוכנה מוכרת / בניית EXE) – מחזיר תשובה מוכנה עם פעולה."""
    if workspace and BUILD_RE.match(text.strip()):
        py = latest_py(workspace)
        if py:
            return build_action_text(py, workspace)
    m = OPEN_RE.match(text.strip())
    if not m:
        return None
    name = m.group(1).strip().strip('"').lower()
    candidates = [name, name[1:] if name.startswith("ה") else name]
    if name in ("תיקיית הפרויקטים", "תיקיית פרויקטים", "הפרויקטים") and workspace:
        return f'פותח את תיקיית הפרויקטים.\n<action name="open" target="{workspace}"></action>'
    for c in candidates:
        if c in APPS:
            return f'פותח את {m.group(1).strip()}.\n<action name="open" target="{APPS[c]}"></action>'
    return None


BUILD_RE = re.compile(r"^\s*(?:ת?בנה|תבני|ת?הפוך|תמיר|תעשה|תייצר)\s+(?:לי\s+)?(?:את\s+)?(?:זה|הקובץ|אותו|אותה|התוכנה|ממנו|מזה)?\s*"
                      r"(?:ל-?|ל)?\s*(?:קובץ\s+)?(?:exe|אקסה)\s*[.!?]*$", re.I)


def latest_py(workspace: str):
    """קובץ הפייתון האחרון שנכתב בתיקיית הפרויקטים."""
    files = [f for f in Path(workspace).rglob("*.py")
             if f.is_file() and "build" not in f.parts and "dist" not in f.parts]
    return max(files, key=lambda f: f.stat().st_mtime) if files else None


def build_action_text(py: Path, workspace: str):
    try:
        rel = py.relative_to(workspace).as_posix()
    except ValueError:
        rel = str(py)
    name = py.parent.name if py.stem.lower() in ("main", "app") and py.parent != Path(workspace) else py.stem
    name = re.sub(r"[^\w\-]", "_", name) or "MyApp"
    return (f'בונה קובץ EXE מ-{rel}.\n'
            f'<action name="build_python_exe" path="{rel}" name="{name}" windowed="true"></action>')


# ---------- יצירת תמונות (נוף, חפצים, אייקונים, רקעים – בלי אנשים) ----------
IMAGE_MODEL = "gaon-sd-turbo-q8_0.gguf"
NO_PEOPLE_RE = re.compile(
    r"\b(people|person|persons|human|humans|man|men|woman|women|girl|girls|boy|boys|child|children|kid|kids|baby|"
    r"lady|ladies|guy|face|faces|portrait|selfie|body|bodies|model|models|bride|figure|character|crowd|family|"
    r"couple|actor|actress|dancer|nude|naked|bikini)\b|"
    r"אנשים|אדם|בן אדם|בני אדם|איש|אישה|אשה|נשים|גבר|גברים|בחור|בחורה|ילד|ילדה|ילדים|תינוק|פנים|דיוקן|גוף|"
    r"דמות|דמויות|כלה|משפחה|זוג|שחקן|שחקנית|רקדן|רקדנית", re.I)
NEGATIVE = ("people, person, human, man, woman, girl, boy, child, face, body, hands, crowd, figure, "
            "text, watermark, blurry, low quality")


def _t_create_image(self, a):
    prompt = (a.attrs.get("prompt") or a.body).strip()
    if not prompt:
        return "חסר תיאור לתמונה."
    if NO_PEOPLE_RE.search(prompt):
        return "✖ נחסם: גאון יוצר רק תמונות בלי אנשים – נופים, חפצים, בעלי חיים, אייקונים ורקעים."
    sd_dir = self.base / "engine" / "sd"
    exe = next((sd_dir / n for n in ("sd-cli.exe", "sd.exe", "sd-cli", "sd") if (sd_dir / n).exists()), None)
    model = Path(self.settings["models_dir"]) / IMAGE_MODEL
    if exe is None or not model.exists():
        return ("✖ יצירת תמונות עוד לא מותקנת. הפעל את INSTALL.bat, סמן \"יצירת תמונות\" ולחץ התקן.")
    out = self.resolve(a.attrs["out"]) if a.attrs.get("out") else \
        Path(self.settings["workspace"]) / "תמונות" / time.strftime("תמונה_%Y%m%d_%H%M%S.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    size = a.attrs.get("size", "512")
    size = size if size in ("256", "384", "512", "640", "768") else "512"
    args = [str(exe), "-m", str(model), "-p", prompt, "-n", NEGATIVE, "--steps", "2", "--cfg-scale", "1.0",
            "-W", size, "-H", size, "-o", str(out)]
    result = self._run(args, cwd=str(sd_dir))
    if out.exists():
        return f"✔ התמונה נוצרה: {out}"
    return f"✖ יצירת התמונה נכשלה.\n{result[-1500:]}"


Toolbox.t_create_image = _t_create_image
