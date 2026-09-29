"""גאון – עוזר AI מקומי בעברית. נקודת הכניסה והממשק הגרפי."""
import datetime
import json
import os
import sys
import threading
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal  # noqa: E402
from PySide6.QtGui import QAction, QDesktopServices, QFont, QIcon, QKeySequence  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget, QFrame, QScrollArea,
)

import catalog  # noqa: E402
import config  # noqa: E402
import prompts  # noqa: E402
import render  # noqa: E402
from engine import BACKEND_NAMES, Engine, EngineError  # noqa: E402
from tools import Toolbox, parse_actions, ATTR_NAMES  # noqa: E402

STYLE = """
* { font-family:"Segoe UI","Arial"; }
QMainWindow, QDialog { background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0b0f24, stop:1 #140b2e); }
QWidget { color:#eef1ff; }
QWidget#side { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1b1f4b, stop:1 #120f2e);
  border-left:1px solid #2d2f6b; }
QWidget#mainArea { background:transparent; }
QLabel { background:transparent; }
QLabel#logo { font-size:22pt; font-weight:800; color:white; padding:14px 10px 2px 10px; }
QLabel#tagline { color:#a5b4fc; padding:0 10px 8px 10px; }
QLabel#section { color:#c4b5fd; font-weight:bold; padding:10px 4px 2px 4px; }
QLabel#title { font-size:16pt; font-weight:bold; color:#a78bfa; }
QLabel#muted { color:#9aa3c7; }
QFrame#header { border-radius:14px;
  background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7c3aed, stop:0.5 #4f46e5, stop:1 #0ea5e9); }
QLabel#headerTitle { font-size:16pt; font-weight:800; color:white; }
QLabel#headerSub { color:#e0e7ff; }
QTextBrowser { background:#0e1330; border:1px solid #2b3470; border-radius:14px; padding:10px; }
QPlainTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTableWidget, QListWidget {
  background:#141a3d; border:2px solid #2b3470; border-radius:12px; padding:8px; color:#eef1ff;
  selection-background-color:#7c3aed; }
QPlainTextEdit:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border:2px solid #8b5cf6; }
QPushButton { color:white; border:none; border-radius:12px; padding:10px 18px; font-weight:bold;
  background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7c3aed, stop:1 #2563eb); }
QPushButton:hover { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8b5cf6, stop:1 #3b82f6); }
QPushButton:pressed { background:#5b21b6; }
QPushButton:disabled { background:#2a2f55; color:#7b82a8; }
QPushButton#secondary { background:#232a5a; border:1px solid #39428a; }
QPushButton#secondary:hover { background:#2e3775; }
QPushButton#danger { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #e11d48, stop:1 #f97316); }
QPushButton#ok { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #059669, stop:1 #10b981); }
QPushButton#send { font-size:12pt; padding:12px 26px;
  background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ec4899, stop:0.5 #8b5cf6, stop:1 #3b82f6); }
QPushButton#send:hover { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #f472b6, stop:0.5 #a78bfa, stop:1 #60a5fa); }
QPushButton[tone] { text-align:right; padding:11px 14px; border-radius:12px; }
QPushButton[tone="1"] { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7c3aed, stop:1 #a855f7); }
QPushButton[tone="2"] { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2563eb, stop:1 #06b6d4); }
QPushButton[tone="3"] { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #059669, stop:1 #22c55e); }
QPushButton[tone="4"] { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ea580c, stop:1 #f59e0b); }
QPushButton[tone="5"] { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #db2777, stop:1 #f43f5e); }
QPushButton[tone]:hover { border:2px solid #ffffff; }
QScrollArea, QWidget#cards { background:transparent; border:none; }
QScrollBar:vertical { background:transparent; width:10px; margin:2px; }
QScrollBar::handle:vertical { background:#4c4f9e; border-radius:5px; min-height:30px; }
QScrollBar::handle:vertical:hover { background:#8b5cf6; }
QScrollBar::add-line, QScrollBar::sub-line { height:0; }
QScrollBar:horizontal { height:0; }
QSplitter::handle { background:#2d2f6b; width:1px; }
QMenuBar { background:#0b0f24; color:#c7d2fe; padding:2px; }
QMenuBar::item { padding:6px 14px; border-radius:8px; }
QMenuBar::item:selected { background:#312e81; }
QMenu { background:#141a3d; border:1px solid #39428a; border-radius:10px; padding:6px; }
QMenu::item { padding:8px 28px; border-radius:8px; }
QMenu::item:selected { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7c3aed, stop:1 #2563eb); }
QStatusBar { background:#0b0f24; color:#a5b4fc; }
QProgressBar { border:1px solid #39428a; border-radius:8px; text-align:center; background:#141a3d; color:white; }
QProgressBar::chunk { border-radius:8px; background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ec4899, stop:1 #8b5cf6); }
QHeaderView::section { background:#232a5a; color:#c7d2fe; padding:8px; border:none; }
QTableWidget::item:selected { background:#4c1d95; }
QCheckBox, QRadioButton { background:transparent; }
QToolTip { background:#1e1b4b; color:white; border:1px solid #7c3aed; border-radius:6px; padding:6px; }
"""

TEMPLATES = [
    ("💻 תוכנת EXE (פייתון)", "בנה לי תוכנת EXE עם ממשק גרפי יפה בעברית (customtkinter), שעושה את הדבר הבא:\n"),
    ("⚙️ תוכנת EXE (C#)", "בנה לי תוכנת EXE ב-C# עם WinForms וממשק בעברית (RightToLeft), שעושה את הדבר הבא:\n"),
    ("🧩 תוסף לגוגל כרום", "בנה לי תוסף לגוגל כרום (Manifest V3) עם חלון קופץ בעברית, שעושה את הדבר הבא:\n"),
    ("🌐 אתר אינטרנט", "בנה לי אתר מעוצב ומודרני בעברית (HTML/CSS/JS, מימין לשמאל) בנושא:\n"),
    ("🎮 משחק", "בנה לי משחק (פייתון עם pygame או HTML5) ותהפוך אותו לקובץ שאפשר להפעיל. המשחק:\n"),
    ("🤖 אוטומציה למחשב", "כתוב לי סקריפט אוטומציה (PowerShell או פייתון) שעושה את הדבר הבא במחשב:\n"),
    ("🛠️ בדיקת המחשב", "בדוק את מצב המחשב שלי: מעבד, זיכרון, דיסקים, תוכנות שעולות בהפעלה – ותן לי המלצות לשיפור."),
    ("📁 סידור קבצים", "עזור לי לסדר את הקבצים בתיקייה הבאה לפי סוג ותאריך:\n"),
    ("🐞 תיקון באג", "יש לי באג בקוד הבא. תמצא אותו ותתקן:\n"),
    ("📖 הסבר קוד", "תסביר לי בעברית פשוטה מה הקוד הזה עושה, שורה אחרי שורה:\n"),
]


class Bridge(QObject):
    token = Signal(str)
    assistant_start = Signal()
    tool_result = Signal(str)
    info = Signal(str)
    finished = Signal()
    confirm = Signal(object, object)            # (action, holder)
    engine_status = Signal(bool, str)
    dl_progress = Signal(int, int, float)
    dl_done = Signal(bool, str)


# ---------------------------------------------------------------- דיאלוגים
class ConfirmDialog(QDialog):
    def __init__(self, parent, action):
        super().__init__(parent)
        self.setWindowTitle("אישור פעולה")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(760, 560)
        lay = QVBoxLayout(self)
        color = ["#3fb950", "#d29922", "#f85149"][action.risk]
        risk = ["פעולה בטוחה", "פעולה שמשנה קבצים", "⚠ פעולה רגישה – תבדוק היטב!"][action.risk]
        head = QLabel(f"<span style='font-size:15pt;font-weight:bold'>🛠 {action.title}</span><br>"
                      f"<span style='color:{color};font-weight:bold'>{risk}</span>")
        lay.addWidget(head)
        lay.addWidget(QLabel("ה-AI מבקש לבצע את הפעולה הבאה במחשב שלך. שום דבר לא יקרה בלי האישור שלך."))
        for k, v in action.attrs.items():
            lbl = QLabel(f"<b>{ATTR_NAMES.get(k, k)}:</b> <span dir='ltr'>{v}</span>")
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lay.addWidget(lbl)
        if action.body.strip():
            body = QPlainTextEdit(action.body)
            body.setReadOnly(True)
            body.setLayoutDirection(Qt.LeftToRight)
            body.setFont(QFont("Consolas", 10))
            lay.addWidget(body, 1)
        row = QHBoxLayout()
        yes = QPushButton("✔ אשר ובצע")
        yes.setObjectName("ok")
        no = QPushButton("✖ דחה")
        no.setObjectName("danger")
        yes.clicked.connect(self.accept)
        no.clicked.connect(self.reject)
        row.addWidget(yes)
        row.addWidget(no)
        row.addStretch()
        lay.addLayout(row)
        no.setDefault(True)
        no.setFocus()


class SettingsDialog(QDialog):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.s = settings
        self.setWindowTitle("הגדרות")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(640, 480)
        form = QFormLayout(self)

        self.workspace = QLineEdit(settings["workspace"])
        self.models_dir = QLineEdit(settings["models_dir"])
        form.addRow("תיקיית פרויקטים:", self._with_browse(self.workspace))
        form.addRow("תיקיית מודלים:", self._with_browse(self.models_dir))

        self.backend = QComboBox()
        self.backend.addItem("אוטומטי (הכי מהיר שיש)", "auto")
        for key, name in BACKEND_NAMES.items():
            self.backend.addItem(name, key)
        self.backend.setCurrentIndex(max(0, self.backend.findData(settings["backend"])))
        form.addRow("מנוע:", self.backend)

        self.gpu_layers = QSpinBox()
        self.gpu_layers.setRange(-1, 999)
        self.gpu_layers.setSpecialValueText("אוטומטי")
        self.gpu_layers.setValue(int(settings["gpu_layers"]))
        form.addRow("שכבות על כרטיס המסך:", self.gpu_layers)

        self.context = QComboBox()
        for v in (4096, 8192, 16384, 32768):
            self.context.addItem(f"{v:,} טוקנים", v)
        self.context.setCurrentIndex(max(0, self.context.findData(int(settings["context"]))))
        form.addRow("זיכרון שיחה:", self.context)

        self.threads = QSpinBox()
        self.threads.setRange(0, 256)
        self.threads.setSpecialValueText("אוטומטי")
        self.threads.setValue(int(settings["threads"]))
        form.addRow("ליבות מעבד:", self.threads)

        self.temp = QDoubleSpinBox()
        self.temp.setRange(0.0, 1.5)
        self.temp.setSingleStep(0.1)
        self.temp.setValue(float(settings["temperature"]))
        form.addRow("יצירתיות (טמפרטורה):", self.temp)

        self.timeout = QSpinBox()
        self.timeout.setRange(10, 7200)
        self.timeout.setSuffix(" שניות")
        self.timeout.setValue(int(settings["command_timeout"]))
        form.addRow("זמן מקסימלי לפקודה:", self.timeout)

        self.font_size = QSpinBox()
        self.font_size.setRange(9, 24)
        self.font_size.setValue(int(settings["font_size"]))
        form.addRow("גודל גופן:", self.font_size)

        form.addRow(QLabel("שינויים במנוע/זיכרון יחולו בטעינה הבאה של המודל."))
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Save).setText("שמור")
        bb.button(QDialogButtonBox.Cancel).setText("ביטול")
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def _with_browse(self, edit):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(edit, 1)
        b = QPushButton("עיון…")
        b.setObjectName("secondary")
        b.clicked.connect(lambda: self._browse(edit))
        h.addWidget(b)
        return w

    def _browse(self, edit):
        d = QFileDialog.getExistingDirectory(self, "בחר תיקייה", edit.text())
        if d:
            edit.setText(d)

    def _save(self):
        s = self.s
        s["workspace"] = self.workspace.text().strip()
        s["models_dir"] = self.models_dir.text().strip()
        s["backend"] = self.backend.currentData()
        s["gpu_layers"] = self.gpu_layers.value()
        s["context"] = self.context.currentData()
        s["threads"] = self.threads.value()
        s["temperature"] = self.temp.value()
        s["command_timeout"] = self.timeout.value()
        s["font_size"] = self.font_size.value()
        for key in ("workspace", "models_dir"):
            Path(s[key]).mkdir(parents=True, exist_ok=True)
        s.save()
        self.accept()


class ModelManager(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.s = win.settings
        self.dl = None
        self.setWindowTitle("מנהל מודלים")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(900, 560)
        lay = QVBoxLayout(self)

        ram = catalog.system_ram_gb()
        rec = catalog.recommend(ram)
        t = QLabel("🧠 מנהל המודלים")
        t.setObjectName("title")
        lay.addWidget(t)
        lay.addWidget(QLabel(f"זיכרון במחשב שלך: <b>{ram:.0f}GB</b> &nbsp;|&nbsp; מומלץ עבורך: <b>{rec['name']}</b>"))
        note = QLabel("המודל יורד פעם אחת בלבד (צריך אינטרנט רק להורדה). אחרי זה – הכל עובד 100% בלי אינטרנט. "
                      "אפשר לעצור ולהמשיך את ההורדה מאותה נקודה.")
        note.setWordWrap(True)
        note.setObjectName("muted")
        lay.addWidget(note)

        self.table = QTableWidget(len(catalog.MODELS), 4)
        self.table.setHorizontalHeaderLabels(["מודל", "גודל", "זיכרון נדרש", "מצב"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        lay.addWidget(self.table, 1)
        self.desc = QLabel()
        self.desc.setWordWrap(True)
        lay.addWidget(self.desc)
        self.table.itemSelectionChanged.connect(self._on_select)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        lay.addWidget(self.progress)
        self.plabel = QLabel()
        lay.addWidget(self.plabel)

        row = QHBoxLayout()
        self.btn_dl = QPushButton("⬇ הורד")
        self.btn_cancel = QPushButton("⏸ עצור הורדה")
        self.btn_cancel.setObjectName("danger")
        self.btn_cancel.setEnabled(False)
        self.btn_load = QPushButton("▶ טען מודל")
        self.btn_load.setObjectName("ok")
        btn_file = QPushButton("📂 קובץ GGUF קיים…")
        btn_file.setObjectName("secondary")
        btn_folder = QPushButton("פתח תיקיית מודלים")
        btn_folder.setObjectName("secondary")
        for b in (self.btn_dl, self.btn_cancel, self.btn_load, btn_file, btn_folder):
            row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)
        self.btn_dl.clicked.connect(self._download)
        self.btn_cancel.clicked.connect(self._cancel)
        self.btn_load.clicked.connect(self._load)
        btn_file.clicked.connect(self._pick_file)
        btn_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.s["models_dir"])))

        win.bridge.dl_progress.connect(self._on_progress)
        win.bridge.dl_done.connect(self._on_done)
        self._refresh()
        self.table.selectRow(catalog.MODELS.index(rec))

    def _refresh(self):
        for r, m in enumerate(catalog.MODELS):
            done = catalog.is_downloaded(self.s["models_dir"], m)
            part = catalog.model_path(self.s["models_dir"], m).with_suffix(".gguf.part")
            state = "✔ מוכן" if done else (f"⏸ הורד חלקית ({part.stat().st_size / 1e9:.1f}GB)" if part.exists() else "לא הורד")
            if str(catalog.model_path(self.s["models_dir"], m)) == self.s["model_file"] and done:
                state = "★ פעיל"
            for c, val in enumerate([m["name"], f"{m['size_gb']}GB", f"{m['ram_gb']}GB", state]):
                self.table.setItem(r, c, QTableWidgetItem(val))
        self._on_select()

    def _selected(self):
        rows = self.table.selectionModel().selectedRows()
        return catalog.MODELS[rows[0].row()] if rows else None

    def _on_select(self):
        m = self._selected()
        if not m:
            return
        self.desc.setText(m["desc"])
        done = catalog.is_downloaded(self.s["models_dir"], m)
        busy = self.dl is not None
        self.btn_dl.setEnabled(not done and not busy)
        self.btn_load.setEnabled(done and not busy)

    def _download(self):
        m = self._selected()
        if not m:
            return
        free = _free_gb(self.s["models_dir"])
        if free and free < m["size_gb"] + 1:
            QMessageBox.warning(self, "אין מספיק מקום", f"צריך לפחות {m['size_gb'] + 1:.0f}GB פנויים. יש רק {free:.0f}GB.")
            return
        self.current = m
        br = self.win.bridge
        self.dl = catalog.Downloader(catalog.model_urls(m), catalog.model_path(self.s["models_dir"], m),
                                     lambda d, t, sp: br.dl_progress.emit(int(d / 1e6), int(t / 1e6), sp),
                                     lambda ok, msg: br.dl_done.emit(ok, msg))
        self.progress.setVisible(True)
        self.btn_cancel.setEnabled(True)
        self.plabel.setText("מתחבר…")
        self.dl.start()
        self._on_select()

    def _cancel(self):
        if self.dl:
            self.dl.cancel()

    def _on_progress(self, done_mb, total_mb, speed):
        if total_mb:
            self.progress.setMaximum(total_mb)
            self.progress.setValue(done_mb)
        eta = ""
        if speed > 0 and total_mb:
            sec = (total_mb - done_mb) * 1e6 / speed
            eta = f" | נשאר בערך {int(sec // 3600)}:{int(sec % 3600 // 60):02d} שעות"
        self.plabel.setText(f"{done_mb / 1000:.2f}GB מתוך {total_mb / 1000:.2f}GB | {speed / 1e6:.1f}MB/s{eta}")

    def _on_done(self, ok, msg):
        self.dl = None
        self.btn_cancel.setEnabled(False)
        self.plabel.setText(msg)
        self._refresh()
        if ok and QMessageBox.question(self, "ההורדה הושלמה", msg + "\n\nלטעון את המודל עכשיו?") == QMessageBox.Yes:
            self._load()

    def _load(self):
        m = self._selected()
        if m:
            self.win.load_model(str(catalog.model_path(self.s["models_dir"], m)))
            self.accept()

    def _pick_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "בחר קובץ מודל", self.s["models_dir"], "GGUF (*.gguf)")
        if f:
            self.win.load_model(f)
            self.accept()

    def reject(self):
        if self.dl and QMessageBox.question(self, "הורדה פעילה", "לעצור את ההורדה? (אפשר להמשיך אחר כך)") != QMessageBox.Yes:
            return
        self._cancel()
        super().reject()


def _free_gb(path):
    try:
        import shutil
        return shutil.disk_usage(path).free / 1e9
    except OSError:
        return 0


# ---------------------------------------------------------------- חלון ראשי
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.base = config.base_dir()
        self.settings = config.Settings()
        self.data = config.data_dir()
        self.engine = Engine(self.base, self.data / "engine.log")
        self.toolbox = Toolbox(self.settings, self.base)
        self.bridge = Bridge()
        self.messages = []       # מה שנשלח למודל
        self.display = []        # מה שמוצג: dict(kind, text)
        self.code_store = []
        self.stop_event = threading.Event()
        self.busy = False
        self.loading = False
        self.dirty = False

        self.setWindowTitle(config.APP_TITLE)
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1320, 860)
        icon = self.base / "assets" / "gaon.ico"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self._build_ui()
        self._build_menu()
        self._connect()
        self.apply_font()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._render_if_dirty)
        self.timer.start(120)

        self.new_chat()
        QTimer.singleShot(300, self._startup)

    # ---------- בניית ממשק ----------
    def _build_ui(self):
        split = QSplitter(Qt.Horizontal)
        side = QWidget()
        side.setObjectName("side")
        sl = QVBoxLayout(side)
        sl.setContentsMargins(12, 8, 12, 12)
        sl.setSpacing(7)
        t = QLabel(f"🧠 {config.APP_NAME}")
        t.setObjectName("logo")
        sl.addWidget(t)
        sub = QLabel("עוזר AI מקומי • 100% אופליין")
        sub.setObjectName("tagline")
        sl.addWidget(sub)
        new_btn = QPushButton("✨ שיחה חדשה")
        new_btn.setObjectName("send")
        new_btn.clicked.connect(self.new_chat)
        sl.addWidget(new_btn)
        lbl = QLabel("⚡ התחלה מהירה")
        lbl.setObjectName("section")
        sl.addWidget(lbl)
        cards = QWidget()
        cl = QVBoxLayout(cards)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(6)
        for i, (name, text) in enumerate(TEMPLATES):
            b = QPushButton(name)
            b.setProperty("tone", str(i % 5 + 1))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, tx=text: self._use_template_text(tx))
            cl.addWidget(b)
        cl.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(cards)
        cards.setObjectName("cards")
        sl.addWidget(scroll, 1)
        for text, slot in (("🧠 מנהל מודלים", self.open_models), ("📁 תיקיית הפרויקטים", self.open_workspace),
                           ("⚙️ הגדרות", self.open_settings)):
            b = QPushButton(text)
            b.setObjectName("secondary")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(slot)
            sl.addWidget(b)
        side.setMinimumWidth(260)
        side.setMaximumWidth(340)

        main = QWidget()
        main.setObjectName("mainArea")
        ml = QVBoxLayout(main)
        ml.setContentsMargins(14, 12, 14, 12)
        ml.setSpacing(10)
        header = QFrame()
        header.setObjectName("header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 10, 18, 10)
        ht = QVBoxLayout()
        h1 = QLabel("מה נבנה היום? 🚀")
        h1.setObjectName("headerTitle")
        h2 = QLabel("תוכנות EXE • תוספים לכרום • אתרים • משחקים • אוטומציה – וכל פעולה רק באישור שלך")
        h2.setObjectName("headerSub")
        ht.addWidget(h1)
        ht.addWidget(h2)
        hl.addLayout(ht, 1)
        ml.addWidget(header)

        self.view = QTextBrowser()
        self.view.setOpenLinks(False)
        self.view.setLayoutDirection(Qt.RightToLeft)
        self.view.anchorClicked.connect(self._on_link)
        ml.addWidget(self.view, 1)

        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("✍️ כתוב כאן מה לבנות… (Enter לשליחה, Shift+Enter לשורה חדשה)")
        self.input.setFixedHeight(110)
        self.input.installEventFilter(self)
        ml.addWidget(self.input)
        row = QHBoxLayout()
        self.send_btn = QPushButton("שלח ➤")
        self.send_btn.setObjectName("send")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn = QPushButton("⏹ עצור")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.state_lbl = QLabel()
        self.state_lbl.setObjectName("muted")
        row.addWidget(self.send_btn)
        row.addWidget(self.stop_btn)
        row.addWidget(self.state_lbl, 1)
        ml.addLayout(row)

        split.addWidget(side)
        split.addWidget(main)
        split.setStretchFactor(1, 1)
        self.setCentralWidget(split)
        self.status = self.statusBar()
        self.engine_lbl = QLabel("המודל לא טעון")
        self.status.addPermanentWidget(self.engine_lbl)

    def _build_menu(self):
        mb = self.menuBar()

        def add(menu, text, slot, shortcut=None):
            a = QAction(text, self)
            a.triggered.connect(slot)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            menu.addAction(a)
            return a

        f = mb.addMenu("קובץ")
        add(f, "שיחה חדשה", self.new_chat, "Ctrl+N")
        add(f, "שמור שיחה…", self.save_chat, "Ctrl+S")
        add(f, "פתח שיחה…", self.load_chat, "Ctrl+O")
        add(f, "ייצא שיחה לקובץ טקסט…", self.export_chat)
        f.addSeparator()
        add(f, "פתח תיקיית פרויקטים", self.open_workspace)
        f.addSeparator()
        add(f, "יציאה", self.close, "Ctrl+Q")
        m = mb.addMenu("מודל")
        add(m, "מנהל מודלים והורדה…", self.open_models, "Ctrl+M")
        add(m, "טען מחדש", lambda: self.load_model(self.settings["model_file"]))
        add(m, "עצור מנוע", self.stop_engine)
        add(m, "יומן מנוע", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.data / "engine.log"))))
        t = mb.addMenu("כלים")
        add(t, "הגדרות…", self.open_settings, "Ctrl+,")
        add(t, "הגדל גופן", lambda: self._font_delta(1), "Ctrl++")
        add(t, "הקטן גופן", lambda: self._font_delta(-1), "Ctrl+-")
        h = mb.addMenu("עזרה")
        add(h, "מדריך", self.show_help, "F1")
        add(h, "אודות", self.show_about)

    def _connect(self):
        b = self.bridge
        b.token.connect(self._on_token)
        b.assistant_start.connect(lambda: self._add("assistant", ""))
        b.tool_result.connect(lambda t: self._add("tool", t))
        b.info.connect(lambda t: self._add("info", t))
        b.finished.connect(self._on_finished)
        b.confirm.connect(self._on_confirm)
        b.engine_status.connect(self._on_engine_status)
        self.send_btn.clicked.connect(self.send)
        self.stop_btn.clicked.connect(self.stop)

    def eventFilter(self, obj, ev):
        if obj is self.input and ev.type() == ev.Type.KeyPress:
            if ev.key() in (Qt.Key_Return, Qt.Key_Enter) and not (ev.modifiers() & Qt.ShiftModifier):
                self.send()
                return True
        return super().eventFilter(obj, ev)

    def apply_font(self):
        size = int(self.settings["font_size"])
        f = QFont("Segoe UI", size)
        QApplication.instance().setFont(f)
        self.view.setFont(f)
        self.input.setFont(f)
        self.dirty = True

    def _font_delta(self, d):
        self.settings["font_size"] = max(9, min(24, int(self.settings["font_size"]) + d))
        self.settings.save()
        self.apply_font()

    # ---------- תצוגה ----------
    def _add(self, kind, text):
        self.display.append({"kind": kind, "text": text})
        self.dirty = True

    def _render_if_dirty(self):
        if not self.dirty:
            return
        self.dirty = False
        sb = self.view.verticalScrollBar()
        at_bottom = sb.value() >= sb.maximum() - 40
        pos = sb.value()
        self.code_store = []
        parts = []
        for d in self.display:
            if d["kind"] == "tool":
                parts.append(render.bubble("tool", render.tool_html(d["text"])))
            else:
                inner = render.to_html(d["text"], self.code_store) if d["text"] else "<p>…</p>"
                parts.append(render.bubble(d["kind"], inner))
        body = "".join(parts) if parts else render.welcome()
        self.view.setHtml("<html><body dir='rtl'>" + body + "</body></html>")
        sb.setValue(sb.maximum() if at_bottom else pos)

    def _on_token(self, t):
        if self.display and self.display[-1]["kind"] == "assistant":
            self.display[-1]["text"] += t
            self.dirty = True

    def _on_link(self, url: QUrl):
        s = url.toString()
        kind, _, idx = s.partition(":")
        if kind in ("copy", "save") and idx.isdigit() and int(idx) < len(self.code_store):
            code, path = self.code_store[int(idx)]
            if kind == "copy":
                QApplication.clipboard().setText(code)
                self.status.showMessage("הקוד הועתק ✔", 3000)
            else:
                start = str(Path(self.settings["workspace"]) / (Path(path).name if path else "code.txt"))
                f, _ = QFileDialog.getSaveFileName(self, "שמור קוד", start)
                if f:
                    Path(f).write_text(code, encoding="utf-8")
                    self.status.showMessage(f"נשמר: {f}", 4000)
        else:
            QDesktopServices.openUrl(url)

    def _use_template_text(self, text):
        self.input.setPlainText(text)
        self.input.setFocus()
        c = self.input.textCursor()
        c.movePosition(c.MoveOperation.End)
        self.input.setTextCursor(c)

    def _set_busy(self, busy, text=""):
        self.busy = busy
        self.send_btn.setEnabled(not busy)
        self.stop_btn.setEnabled(busy)
        self.state_lbl.setText(text)

    # ---------- מודל ----------
    def _startup(self):
        mf = self.settings["model_file"]
        if mf and Path(mf).exists() and self.settings["autoload"]:
            self.load_model(mf)
            return
        for m in catalog.MODELS:
            if catalog.is_downloaded(self.settings["models_dir"], m):
                self.load_model(str(catalog.model_path(self.settings["models_dir"], m)))
                return
        self._add("info", "## ברוך הבא לגאון! 👋\nכדי להתחיל צריך להוריד מודל AI **פעם אחת בלבד**. "
                          "אחרי זה הכל עובד **100% בלי אינטרנט**.\nפותח את מנהל המודלים…")
        QTimer.singleShot(600, self.open_models)

    def load_model(self, path):
        if not path or not Path(path).exists():
            QMessageBox.warning(self, "אין מודל", "לא נבחר מודל. פתח את מנהל המודלים.")
            return
        if self.busy or self.loading:
            QMessageBox.information(self, "רגע", "המתן לסיום הפעולה הנוכחית.")
            return
        self.settings["model_file"] = path
        self.settings.save()
        self.loading = True
        self.engine_lbl.setText("⏳ טוען מודל… (בפעם הראשונה זה יכול לקחת כמה דקות)")
        self.send_btn.setEnabled(False)

        def work():
            try:
                ok, msg = self.engine.start(path, self.settings,
                                            lambda s: self.bridge.engine_status.emit(False, "⏳ " + s))
            except Exception as e:  # noqa: BLE001
                ok, msg = False, str(e)
            self.bridge.engine_status.emit(ok, "DONE:" + msg)

        threading.Thread(target=work, daemon=True).start()

    def _on_engine_status(self, ok, msg):
        if not msg.startswith("DONE:"):
            self.engine_lbl.setText(msg)
            return
        msg = msg[5:]
        self.loading = False
        self.send_btn.setEnabled(not self.busy)
        if ok:
            self.engine_lbl.setText(f"🟢 {Path(self.settings['model_file']).stem} | {msg}")
            self.status.showMessage("המודל מוכן! אפשר לכתוב.", 5000)
        else:
            self.engine_lbl.setText("🔴 המודל לא טעון")
            self._add("info", "**טעינת המודל נכשלה.**\n" + msg +
                      "\n\nטיפים: בחר מודל קטן יותר במנהל המודלים, או שנה ל'מעבד בלבד' בהגדרות.")

    def stop_engine(self):
        self.engine.stop()
        self.engine_lbl.setText("⚪ המנוע נעצר")

    # ---------- שיחה ----------
    def new_chat(self):
        if self.busy:
            return
        self.messages = [{"role": "system", "content": prompts.system_prompt(self.settings, self.toolbox)}]
        self.display = []
        self.dirty = True

    def send(self):
        text = self.input.toPlainText().strip()
        if not text or self.busy:
            return
        if self.loading or self.engine.is_loading():
            QMessageBox.information(self, "רגע…", "המודל עדיין נטען. חכה שבשורה למטה יופיע 🟢 ואז שלח.")
            return
        if not self.engine.is_running():
            QMessageBox.information(self, "המודל לא טעון", "צריך לטעון מודל קודם (תפריט מודל ← מנהל מודלים).")
            return
        self.input.clear()
        self.messages[0]["content"] = prompts.system_prompt(self.settings, self.toolbox)
        self.messages.append({"role": "user", "content": text})
        self._add("user", text)
        self.stop_event.clear()
        self._set_busy(True, "🧠 חושב…")
        threading.Thread(target=self._agent_loop, daemon=True).start()

    def stop(self):
        self.stop_event.set()
        self.state_lbl.setText("עוצר…")

    def _trim_history(self):
        budget = int(self.settings["context"]) * 2.5 - int(self.settings["max_tokens"]) * 2.5
        while len(self.messages) > 3 and sum(len(m["content"]) for m in self.messages) > max(budget, 6000):
            del self.messages[1]

    def _agent_loop(self):
        b = self.bridge
        try:
            for _step in range(int(self.settings["max_steps"])):
                self._trim_history()
                b.assistant_start.emit()
                text = ""
                for piece in self.engine.chat_stream(self.messages, self.settings, self.stop_event):
                    text += piece
                    b.token.emit(piece)
                if text.count("<action") > text.count("</action>"):
                    text += "</action>"
                    b.token.emit("</action>")
                self.messages.append({"role": "assistant", "content": text or "(ריק)"})
                if self.stop_event.is_set():
                    b.info.emit("נעצר על ידי המשתמש.")
                    break
                actions = parse_actions(text)
                if not actions:
                    break
                results = []
                rejected = False
                for a in actions:
                    holder = {"event": threading.Event(), "ok": False}
                    b.confirm.emit(a, holder)
                    holder["event"].wait()
                    if not holder["ok"]:
                        results.append(f"המשתמש דחה את הפעולה '{a.title}'. אל תבצע אותה שוב – שאל אותו מה הוא מעדיף.")
                        rejected = True
                        break
                    res = self.toolbox.execute(a)
                    results.append(f"[{a.title}]\n{res}")
                    b.tool_result.emit(f"{a.title}:\n{res}")
                if rejected:
                    b.tool_result.emit("✖ הפעולה נדחתה.")
                self.messages.append({"role": "user", "content": "תוצאת הפעולה:\n" + "\n\n".join(results)[:8000]})
                if self.stop_event.is_set():
                    break
        except EngineError as e:
            b.info.emit(f"**⚠ {e}**")
        except Exception as e:  # noqa: BLE001
            b.info.emit(f"**שגיאה לא צפויה:** {e}\n\n```\n{traceback.format_exc()[-1500:]}\n```")
        b.finished.emit()

    def _on_confirm(self, action, holder):
        self.state_lbl.setText("⏳ ממתין לאישור שלך…")
        QApplication.alert(self)
        self.raise_()
        self.activateWindow()
        dlg = ConfirmDialog(self, action)
        holder["ok"] = dlg.exec() == QDialog.Accepted
        self.state_lbl.setText("⚙️ מבצע…" if holder["ok"] else "")
        holder["event"].set()

    def _on_finished(self):
        self._set_busy(False, "")
        self.dirty = True
        self.input.setFocus()

    # ---------- שמירה ----------
    def save_chat(self):
        d = self.data / "שיחות"
        d.mkdir(parents=True, exist_ok=True)
        name = datetime.datetime.now().strftime("שיחה_%Y-%m-%d_%H-%M.json")
        f, _ = QFileDialog.getSaveFileName(self, "שמור שיחה", str(d / name), "JSON (*.json)")
        if f:
            Path(f).write_text(json.dumps({"messages": self.messages, "display": self.display},
                                          ensure_ascii=False, indent=1), encoding="utf-8")

    def load_chat(self):
        f, _ = QFileDialog.getOpenFileName(self, "פתח שיחה", str(self.data / "שיחות"), "JSON (*.json)")
        if f and not self.busy:
            data = json.loads(Path(f).read_text(encoding="utf-8"))
            self.messages, self.display = data["messages"], data["display"]
            self.dirty = True

    def export_chat(self):
        f, _ = QFileDialog.getSaveFileName(self, "ייצוא", str(Path(self.settings["workspace"]) / "שיחה.md"), "Markdown (*.md)")
        if f:
            names = {"user": "אתה", "assistant": "גאון", "tool": "תוצאה", "info": "מערכת"}
            Path(f).write_text("\n\n".join(f"### {names[d['kind']]}\n{d['text']}" for d in self.display), encoding="utf-8")

    # ---------- חלונות ----------
    def open_models(self):
        ModelManager(self).exec()

    def open_settings(self):
        if SettingsDialog(self, self.settings).exec():
            self.apply_font()

    def open_workspace(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.settings["workspace"]))

    def show_help(self):
        self._add("info", HELP)

    def show_about(self):
        QMessageBox.about(self, "אודות", f"<h2>{config.APP_TITLE}</h2><p>גרסה {config.APP_VERSION}</p>"
                          "<p>עוזר AI שרץ כולו על המחשב שלך, בלי אינטרנט ובלי לשלוח מידע לשום מקום.</p>"
                          "<p>מנוע: llama.cpp &nbsp;|&nbsp; מודל: Qwen2.5-Coder</p>")

    def closeEvent(self, ev):
        self.stop_event.set()
        self.engine.stop()
        self.settings.save()
        super().closeEvent(ev)


HELP = """## מדריך מהיר
- **כותבים בקשה** בתיבה למטה (או בוחרים "התחלה מהירה" מימין) ולוחצים Enter.
- גאון כותב את הקוד, ו**כל פעולה על המחשב** (כתיבת קובץ, הרצת פקודה, בניית EXE) **מחכה לאישור שלך**. בלי אישור לא קורה כלום.
- הקבצים נשמרים ב**תיקיית הפרויקטים** (תפריט קובץ ← פתח תיקיית פרויקטים).
- **תוסף לכרום:** אחרי שגאון בונה אותו – פותחים chrome://extensions, מפעילים "מצב מפתח", ולוחצים "טען פריט לא ארוז".
- **EXE:** גאון בונה EXE מפייתון (PyInstaller מובנה) או מ-C# (המהדר של ווינדוס) – בלי אינטרנט.
- **איטי?** במנהל המודלים בחר מודל קטן יותר. יש כרטיס מסך? ההגדרות ← מנוע.
- קיצורים: Ctrl+N שיחה חדשה | Ctrl+S שמירה | Ctrl+M מודלים | Ctrl +/- גופן | F1 מדריך"""


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Gaon.LocalAI")
        except (OSError, AttributeError):
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
