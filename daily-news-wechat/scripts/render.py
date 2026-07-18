from __future__ import annotations

import base64
import html
import re
import struct
import zlib
from datetime import datetime
from pathlib import Path

from core import BJT, NewsItem

THEMES = {
    "news-blue": ("#2563eb", "#102a43", "#eff6ff"),
    "teal": ("#0f766e", "#134e4a", "#f0fdfa"),
    "warm-orange": ("#ea580c", "#7c2d12", "#fff7ed"),
    "elegant-purple": ("#7c3aed", "#4c1d95", "#f5f3ff"),
    "deep-cyan": ("#0e7490", "#164e63", "#ecfeff"),
    "gold-blue": ("#b7791f", "#173b66", "#fffbeb"),
    "slate-blue": ("#475569", "#1e293b", "#f8fafc"),
}


def theme_for(day: datetime, names: list[str]) -> str:
    return names[day.astimezone(BJT).weekday() % len(names)]


def article_markdown(items: list[NewsItem], start: datetime, end: datetime) -> str:
    title = f"昨天，这{len(items)}件大事值得关注"
    lines = [f"# {title}", "", f"> 统计时段：北京时间 {start:%Y-%m-%d %H:%M}—{end:%Y-%m-%d %H:%M}。", "", "## 30秒速览", ""]
    lines.extend(f"- {item.title}" for item in items)
    for index, item in enumerate(items, 1):
        lines.extend([
            "", "---", "", f"## {index}、{item.title}", "",
            f"> **关键词：{item.category}｜{item.source}｜普通人视角**", "",
            "**发生了什么**", "", item.summary or "该事件摘要需要结合原文进一步核验。", "",
            "**为什么重要**", "", "这条新闻的影响范围、后续变化和与普通人的关系需要在发布前结合权威来源补充。", "",
            "**普通人需要注意什么**", "", "关注有关部门后续通报，不依据未经证实的片段信息作出重要决定。", "",
            "> **小清提醒：** 动态信息请以权威来源最新发布为准。",
        ])
    lines.extend(["", "---", "", "## 今天值得关注", "", "- 相关事件是否有新的官方进展。", "- 政策、灾情和市场数据是否更新口径。", "", "## 信息来源与动态说明", ""])
    lines.extend(f"{index}. {item.source}：[《{item.title}》]({item.url})" for index, item in enumerate(items, 1))
    lines.extend(["", "> 本文依据公开资料整理。动态信息请以有关部门最新通报为准；市场内容不构成投资建议。", ""])
    return "\n".join(lines)


def _inline(text: str, accent: str) -> str:
    links = []
    def stash(match: re.Match[str]) -> str:
        label, url = match.groups()
        links.append(f'<a href="{html.escape(url, quote=True)}" style="color:{accent};text-decoration:none;">{html.escape(label)}</a>')
        return f"@@LINK{len(links)-1}@@"
    escaped = html.escape(re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", stash, text))
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    for index, link in enumerate(links):
        escaped = escaped.replace(f"@@LINK{index}@@", link)
    return escaped


def markdown_to_html(markdown: str, theme_name: str) -> str:
    accent, dark, soft = THEMES[theme_name]
    blocks = []
    in_list = False
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            if in_list:
                blocks.append("</ul>")
                in_list = False
            continue
        if line == "---":
            blocks.append(f'<hr style="border:0;height:1px;background:{accent}22;margin:28px 12%;">')
        elif line.startswith("# "):
            blocks.append(f'<h1 style="color:{dark};font-size:27px;line-height:1.4;">{_inline(line[2:], accent)}</h1>')
        elif line.startswith("## "):
            blocks.append(f'<h2 style="margin-top:32px;padding-left:12px;border-left:4px solid {accent};color:{dark};font-size:20px;">{_inline(line[3:], accent)}</h2>')
        elif line.startswith("> "):
            blocks.append(f'<blockquote style="margin:18px 0;padding:13px 16px;border-left:4px solid {accent};background:{soft};line-height:1.8;">{_inline(line[2:], accent)}</blockquote>')
        elif line.startswith("- "):
            if not in_list:
                blocks.append('<ul style="padding-left:24px;line-height:1.9;">')
                in_list = True
            blocks.append(f"<li>{_inline(line[2:], accent)}</li>")
        else:
            blocks.append(f'<p style="color:#334e68;font-size:16px;line-height:1.9;text-align:justify;">{_inline(line, accent)}</p>')
    if in_list:
        blocks.append("</ul>")
    body = "\n".join(blocks)
    return f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><body style="margin:0;background:{soft};font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Microsoft YaHei,sans-serif"><article style="max-width:720px;margin:24px auto;padding:28px 24px;background:#fff">{body}</article></body></html>'


def cover_svg(title: str, subtitle: str, theme_name: str, width: int, height: int) -> str:
    accent, dark, soft = THEMES[theme_name]
    title = html.escape(title)
    subtitle = html.escape(subtitle)
    size = max(28, int(height * .12))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="{soft}"/><rect x="{int(width*.72)}" width="{int(width*.28)}" height="100%" fill="{accent}"/>
<circle cx="{int(width*.68)}" cy="{int(height*.5)}" r="{int(height*.27)}" fill="{accent}" opacity=".12"/>
<text x="{int(width*.08)}" y="{int(height*.45)}" font-family="Microsoft YaHei,sans-serif" font-size="{size}" font-weight="700" fill="{dark}">{title}</text>
<text x="{int(width*.08)}" y="{int(height*.68)}" font-family="Microsoft YaHei,sans-serif" font-size="{max(16,int(size*.45))}" fill="{dark}" opacity=".72">{subtitle}</text>
<text x="{int(width*.86)}" y="{int(height*.48)}" text-anchor="middle" font-family="Arial,sans-serif" font-size="{max(18,int(size*.5))}" font-weight="700" fill="#fff">NEWS</text>
</svg>'''


def cover_png(theme_name: str, width: int, height: int) -> bytes:
    """Create an uploadable, dependency-free PNG companion to the editable SVG."""
    accent, dark, soft = THEMES[theme_name]
    def rgb(value: str) -> tuple[int, int, int]:
        value = value.lstrip("#")
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))
    accent_rgb, dark_rgb, soft_rgb = rgb(accent), rgb(dark), rgb(soft)
    pixels = bytearray()
    panel_start = int(width * .72)
    circle_x, circle_y, radius = int(width * .68), height // 2, int(height * .22)
    for y in range(height):
        pixels.append(0)
        for x in range(width):
            if x >= panel_start:
                color = accent_rgb
            elif (x - circle_x) ** 2 + (y - circle_y) ** 2 <= radius ** 2:
                color = tuple((soft_rgb[i] * 3 + accent_rgb[i]) // 4 for i in range(3))
            elif int(height * .72) <= y <= int(height * .78) and int(width * .08) <= x <= int(width * .58):
                color = accent_rgb
            else:
                color = soft_rgb
            pixels.extend(color)
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(pixels), 9)) + chunk(b"IEND", b"")
