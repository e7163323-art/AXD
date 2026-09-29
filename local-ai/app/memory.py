"""הזיכרון של גאון: דברים שהמשתמש לימד אותו, נשמרים בין שיחות."""
import datetime
import json
import re
from pathlib import Path

MAX_ITEMS = 60
TEACH_RE = re.compile(r"^\s*(?:תזכור|תזכרי|זכור|תלמד|תדע)\s*(?:ש|:|,|-)\s*(.+)$", re.S)


class Memory:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.items = []
        try:
            self.items = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.items = []

    def save(self):
        try:
            self.path.write_text(json.dumps(self.items, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass

    def add(self, text: str) -> str:
        text = " ".join(text.split()).strip(" .")
        if not text:
            return "אין מה לזכור."
        if any(i["text"] == text for i in self.items):
            return f"כבר זוכר: {text}"
        self.items.append({"text": text, "date": datetime.date.today().isoformat()})
        self.items = self.items[-MAX_ITEMS:]
        self.save()
        return f"✔ זכרתי: {text}"

    def remove(self, index: int):
        if 0 <= index < len(self.items):
            del self.items[index]
            self.save()

    def prompt_block(self) -> str:
        if not self.items:
            return ""
        lines = "\n".join(f"- {i['text']}" for i in self.items)
        return ("\n## What you remember about the user (learned in past chats – always take it into account)\n"
                + lines + "\n")
