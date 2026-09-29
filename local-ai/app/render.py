"""המרת טקסט (Markdown בסיסי + בלוקי פעולה) ל-HTML לתצוגת השיחה."""
import html
import re
from pathlib import Path

from tools import TOOLS, ATTR_NAMES, split_for_display

COLORS = {
    "user_bg": "#1c1f3a", "ai_bg": "#161a26", "tool_bg": "#14201b", "info_bg": "#221e14",
    "code_bg": "#0b0d14", "code_fg": "#e5e7eb", "accent": "#a5b4fc", "muted": "#8b93a7",
}
NAME_COLORS = {"user": "#a5b4fc", "assistant": "#e5e7eb", "tool": "#86efac", "info": "#fcd34d"}
BORDER = {"user": "#6366f1", "assistant": "#374151", "tool": "#16a34a", "info": "#b45309"}


def _inline(text: str) -> str:
    t = html.escape(text)
    t = re.sub(r"`([^`\n]+)`", r'<code style="background:#1f2335;color:#c7d2fe;">\1</code>', t)
    t = re.sub(r"\*\*([^*\n]+)\*\*", r"<b>\1</b>", t)
    return t


def _text_block(text: str) -> str:
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            out.append("<div style='height:6px'></div>")
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            size = {1: 17, 2: 15, 3: 14, 4: 13}[len(m.group(1))]
            out.append(f"<p dir='rtl' style='font-size:{size}pt;font-weight:bold;color:{COLORS['accent']};margin:4px 0'>{_inline(m.group(2))}</p>")
            continue
        m = re.match(r"^[-*•]\s+(.*)$", s)
        if m:
            out.append(f"<p dir='rtl' style='margin:1px 0 1px 0'>&nbsp;&nbsp;• {_inline(m.group(1))}</p>")
            continue
        out.append(f"<p dir='rtl' style='margin:2px 0'>{_inline(line)}</p>")
    return "".join(out)


def _code_block(code: str, lang: str, idx: int, header: str = "") -> str:
    label = header or (lang or "קוד")
    links = (f"<a href='copy:{idx}' style='color:{COLORS['accent']};text-decoration:none'>📋 העתק</a>"
             f"&nbsp;&nbsp;<a href='save:{idx}' style='color:{COLORS['accent']};text-decoration:none'>💾 שמור</a>")
    return (
        f"<table width='100%' cellspacing='0' cellpadding='8' style='background:{COLORS['code_bg']};margin:6px 0'>"
        f"<tr><td style='background:#161a26;color:#9ca3af'>{html.escape(label)}&nbsp;&nbsp;&nbsp;{links}</td></tr>"
        f"<tr><td><pre dir='ltr' style='color:{COLORS['code_fg']};font-family:Consolas,\"Cascadia Mono\",monospace;"
        f"font-size:10.5pt;margin:0'>{html.escape(code.rstrip())}</pre></td></tr></table>"
    )


def to_html(text: str, code_store: list) -> str:
    """מחזיר HTML ושומר כל בלוק קוד ב-code_store (להעתקה/שמירה)."""
    out = []
    for kind, part in split_for_display(text):
        if kind == "action":
            title, risk = TOOLS.get(part.name, (part.name, 2))
            color = ["#3fb950", "#d29922", "#f85149"][risk]
            details = " | ".join(f"{ATTR_NAMES.get(k, k)}: {v}" for k, v in part.attrs.items())
            out.append(f"<p dir='rtl' style='margin:6px 0 0 0'><span style='color:{color};font-weight:bold'>🛠 פעולה: {html.escape(title)}</span>"
                       f"&nbsp;<span style='color:{COLORS['muted']}'>{html.escape(details)}</span></p>")
            if part.body.strip():
                code_store.append((part.body, part.attrs.get("path", "")))
                out.append(_code_block(part.body, "", len(code_store) - 1, part.attrs.get("path", "") or title))
            continue
        segments = re.split(r"```", part)
        for i, seg in enumerate(segments):
            if i % 2 == 0:
                out.append(_text_block(seg))
            else:
                lang, _, code = seg.partition("\n")
                code_store.append((code, ""))
                out.append(_code_block(code, lang.strip(), len(code_store) - 1))
    return "".join(out)


def bubble(kind: str, inner_html: str) -> str:
    who = {"user": "👤 אתה", "assistant": "🧠 גאון", "tool": "⚙️ תוצאת פעולה", "info": "💡 מערכת"}[kind]
    bg = {"user": COLORS["user_bg"], "assistant": COLORS["ai_bg"], "tool": COLORS["tool_bg"], "info": COLORS["info_bg"]}[kind]
    return (f"<table width='100%' cellspacing='0' cellpadding='0' style='margin:10px 0'>"
            f"<tr><td width='5' style='background:{BORDER[kind]}'></td>"
            f"<td dir='rtl' style='background:{bg};padding:12px 14px'>"
            f"<p dir='rtl' style='color:{NAME_COLORS[kind]};font-weight:bold;margin:0 0 6px 0'>{who}</p>"
            f"{inner_html}</td></tr></table>")


DESCRIPTIONS = [
    "ממשק גרפי בעברית + קובץ EXE", "WinForms מימין לשמאל", "Manifest V3 מוכן לטעינה",
    "מעוצב, מימין לשמאל", "pygame או HTML5", "סקריפטים שעושים עבודה במחשב",
    "מעבד, זיכרון, דיסקים והמלצות", "סידור לפי סוג ותאריך", "מוצא ומתקן שגיאות בקוד",
]


def welcome(templates) -> str:
    """מסך פתיחה: כרטיסי התחלה מהירה שאפשר ללחוץ עליהם."""
    cells = []
    for i, (name, _text) in enumerate(templates[:9]):
        icon, _, title = name.partition(" ")
        desc = DESCRIPTIONS[i] if i < len(DESCRIPTIONS) else ""
        cells.append(f"<td width='33%' style='background:#181c2a;padding:14px;border:1px solid #262b3d'>"
                     f"<p dir='rtl' style='font-size:17pt;margin:0'>{icon}</p>"
                     f"<p dir='rtl' style='font-size:12pt;font-weight:bold;margin:2px 0'>"
                     f"<a href='tpl:{i}' style='color:#e5e7eb;text-decoration:none'>{html.escape(title)}</a></p>"
                     f"<p dir='rtl' style='color:{COLORS['muted']};margin:0'>{desc}</p></td>")
    rows = "".join("<tr>" + "".join(cells[i:i + 3]) + "</tr>" for i in range(0, len(cells), 3))
    return (f"<p dir='rtl' align='center' style='font-size:24pt;font-weight:bold;color:#f3f4f6;margin:18px 0 0 0'>"
            f"שלום! אני גאון 👋</p>"
            f"<p dir='rtl' align='center' style='font-size:12pt;color:{COLORS['muted']};margin:4px 0 16px 0'>"
            f"עוזר AI שרץ כולו על המחשב שלך. לחץ על אחד הכרטיסים, או פשוט תכתוב למטה מה לבנות.</p>"
            f"<table width='100%' cellspacing='10' cellpadding='0'>{rows}</table>")


def tool_html(text: str) -> str:
    lines = html.escape(text[:4000]).split("\n")
    return "".join(f"<p dir='rtl' style='color:#b7f5d8;font-family:Consolas,monospace;font-size:10pt;margin:0'>"
                   f"{l or '&nbsp;'}</p>" for l in lines)


def step_html(i: int, d: dict) -> str:
    """שלב שבוצע – שורה מקופלת שאפשר לפתוח (כמו "Ran 4 commands")."""
    title = d.get("title") or d["text"].split("\n", 1)[0]
    ok = d.get("ok", True)
    icon, color = ("✔", "#4ade80") if ok else ("✖", "#f87171")
    arrow = "▾" if d.get("open") else "‹"
    head = (f"<table width='100%' cellspacing='0' cellpadding='0' style='margin:3px 0'><tr>"
            f"<td style='background:#141824;padding:7px 12px;border:1px solid #242938'>"
            f"<p dir='rtl' style='margin:0'><span style='color:{color};font-weight:bold'>{icon}</span>&nbsp; "
            f"<a href='toggle:{i}' style='color:#cbd5e1;text-decoration:none'>{html.escape(title)} "
            f"<span style='color:#6b7280'>{arrow}</span></a></p>")
    m = re.search(r"התמונה נוצרה: (.+\.png)", d.get("text", ""))
    if m and Path(m.group(1).strip()).exists():
        url = Path(m.group(1).strip()).resolve().as_uri()
        head += (f"<p align='center' style='margin:8px 0 2px 0'><a href='open:{html.escape(m.group(1).strip())}'>"
                 f"<img src='{url}' width='384'></a></p>")
    if d.get("open"):
        head += "<div style='margin-top:6px'>" + tool_html(d["text"]) + "</div>"
    return head + "</td></tr></table>"
