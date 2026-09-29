"""בדיקה אוטומטית שהממשק עולה ושהכלים עובדים (רץ ב-CI)."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402
import main  # noqa: E402
import tools  # noqa: E402

app = QApplication([])
app.setStyleSheet(main.STYLE)
w = main.MainWindow()
w.settings["workspace"] = tempfile.mkdtemp()
text = 'קוד:\n```python\nprint("hi")\n```\n<action name="write_file" path="t/a.py">\nprint(1)\n</action>'
acts = tools.parse_actions(text)
assert acts and acts[0].name == "write_file", acts
print(w.toolbox.execute(acts[0]))
print(w.toolbox.execute(tools.Action("run_command", {}, "Write-Output 'שלום'")))
w._add("assistant", text)
w._render_if_dirty()
assert len(w.code_store) == 2
mm = main.ModelManager(w)
mm._refresh()
main.ConfirmDialog(w, acts[0])
main.SettingsDialog(w, w.settings)
print("backends:", w.engine.backends())
print("SMOKE OK")
os._exit(0)
