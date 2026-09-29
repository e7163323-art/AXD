"""המרת טקסט (Markdown בסיסי + בלוקי פעולה) ל-HTML לתצוגת השיחה."""
import html
import re

from tools import TOOLS, ATTR_NAMES, split_for_display

COLORS = {
    "user_bg": "#3b1f7a", "ai_bg": "#151c45", "tool_bg": "#0b3b2e", "info_bg": "#3f2a0a",
    "code_bg": "#070a1c", "code_fg": "#e2e8ff", "accent": "#a78bfa", "muted": "#9aa3c7",
}
NAME_COLORS = {"user": "#f0abfc", "assistant": "#67e8f9", "tool": "#6ee7b7", "info": "#fcd34d"}
BORDER = {"user": "#a855f7", "assistant": "#3b82f6", "tool": "#10b981", "info": "#f59e0b"}


def _inline(text: str) -> str:
    t = html.escape(text)
    t = re.sub(r"`([^`\n]+)`", r'<code style="background:#2a2458;color:#fcd34d;">\1</code>', t)
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
        f"<tr><td style='background:#1e2552;color:#c7d2fe'>{html.escape(label)}&nbsp;&nbsp;&nbsp;{links}</td></tr>"
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


def welcome() -> str:
    """מסך פתיחה צבעוני כשהשיחה ריקה."""
    cards = [
        ("💻", "תוכנות EXE", "בפייתון או C#, עם ממשק בעברית", "#7c3aed"),
        ("🧩", "תוספים לכרום", "Manifest V3 מוכן לטעינה", "#2563eb"),
        ("🌐", "אתרים", "מעוצבים, מימין לשמאל", "#059669"),
        ("🎮", "משחקים", "pygame או HTML5", "#ea580c"),
        ("🤖", "אוטומציה", "סקריפטים שעושים עבודה במחשב", "#db2777"),
        ("🔒", "רק באישור שלך", "כל פעולה מחכה לאישור", "#0891b2"),
    ]
    cells = []
    for icon, title, text, color in cards:
        cells.append(f"<td width='33%' style='background:{color};padding:14px'>"
                     f"<p dir='rtl' style='font-size:20pt;margin:0'>{icon}</p>"
                     f"<p dir='rtl' style='font-size:13pt;font-weight:bold;color:white;margin:2px 0'>{title}</p>"
                     f"<p dir='rtl' style='color:#eef2ff;margin:0'>{text}</p></td>")
    rows = "".join("<tr>" + "".join(cells[i:i + 3]) + "</tr>" for i in (0, 3))
    return (f"<p dir='rtl' align='center' style='font-size:26pt;font-weight:bold;color:#c4b5fd;margin:18px 0 0 0'>"
            f"שלום! אני גאון 👋</p>"
            f"<p dir='rtl' align='center' style='font-size:12pt;color:{COLORS['muted']};margin:4px 0 16px 0'>"
            f"עוזר AI שרץ כולו על המחשב שלך. בחר משהו מימין או פשוט תכתוב למטה מה לבנות.</p>"
            f"<table width='100%' cellspacing='10' cellpadding='0'>{rows}</table>")


def tool_html(text: str) -> str:
    lines = html.escape(text[:4000]).split("\n")
    return "".join(f"<p dir='rtl' style='color:#b7f5d8;font-family:Consolas,monospace;font-size:10pt;margin:0'>"
                   f"{l or '&nbsp;'}</p>" for l in lines)
