"""המרת טקסט (Markdown בסיסי + בלוקי פעולה) ל-HTML לתצוגת השיחה."""
import html
import re

from tools import TOOLS, ATTR_NAMES, split_for_display

COLORS = {
    "user_bg": "#243b6b", "ai_bg": "#1f232b", "tool_bg": "#1a2b22", "info_bg": "#2b2616",
    "code_bg": "#0f1115", "code_fg": "#d7dae0", "accent": "#5b9bff", "muted": "#8a93a3",
}


def _inline(text: str) -> str:
    t = html.escape(text)
    t = re.sub(r"`([^`\n]+)`", r'<code style="background:#2a2f3a;color:#ffd580;">\1</code>', t)
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
        f"<tr><td style='background:#20242d;color:{COLORS['muted']}'>{html.escape(label)}&nbsp;&nbsp;&nbsp;{links}</td></tr>"
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
    who = {"user": "👤 אתה", "assistant": "🧠 גאון", "tool": "⚙️ תוצאת פעולה", "info": "ℹ️ מערכת"}[kind]
    bg = {"user": COLORS["user_bg"], "assistant": COLORS["ai_bg"], "tool": COLORS["tool_bg"], "info": COLORS["info_bg"]}[kind]
    return (f"<table width='100%' cellspacing='0' cellpadding='10' style='margin:8px 0;background:{bg}'>"
            f"<tr><td dir='rtl'><p dir='rtl' style='color:{COLORS['muted']};font-weight:bold;margin:0 0 4px 0'>{who}</p>"
            f"{inner_html}</td></tr></table>")


def tool_html(text: str) -> str:
    return (f"<pre dir='ltr' style='color:#b8e6c4;font-family:Consolas,monospace;font-size:10pt;margin:0'>"
            f"{html.escape(text[:4000])}</pre>")
