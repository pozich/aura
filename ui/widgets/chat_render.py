from __future__ import annotations

import html
import re

from ui.styles import text_primary_for, text_secondary_for, theme_colors

BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
BUBBLE_WIDTH_PX = 460


def _format_body(text: str) -> str:
    escaped = html.escape(text)
    escaped = BOLD_RE.sub(r"<b>\1</b>", escaped)
    paragraphs = escaped.split("\n\n")
    return "<br><br>".join(p.replace("\n", "<br>") for p in paragraphs)


def _bubble(body: str, *, align: str, bg: str, color: str) -> str:
    return (
        f'<table align="{align}" width="{BUBBLE_WIDTH_PX}" cellspacing="0" cellpadding="10">'
        f'<tr><td style="background-color:{bg}; color:{color};">{body}</td></tr>'
        f"</table><br>"
    )


def build_chat_html(
    msgs: list[dict],
    *,
    theme_id: str,
    font_family: str,
    font_size: int,
    status: str | None = None,
    status_is_error: bool = False,
) -> str:
    palette = theme_colors(theme_id)
    text_color = text_primary_for(theme_id)
    muted_color = text_secondary_for(theme_id)

    rows = []
    for msg in msgs:
        is_me = bool(msg.get("me"))
        body = _format_body(msg["text"])
        if is_me:
            rows.append(_bubble(body, align="right", bg=palette["accent"], color=palette["on_accent"]))
        else:
            rows.append(_bubble(body, align="left", bg=palette["bg2"], color=text_color))

    if status:
        color = "#e07a5f" if status_is_error else muted_color
        rows.append(
            f'<p style="margin:0 0 12px 0; color:{color}; font-style:italic;">{html.escape(status)}</p>'
        )

    style = f'font-family:"{font_family}"; font-size:{font_size}px; color:{text_color};'
    return f"<div style='{style}'>{''.join(rows)}</div>"
