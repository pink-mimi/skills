from __future__ import annotations

import base64
import html
import io
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PALETTES = {
    "news-blue": ("#EAF4FF", "#0B3154", "#1769E0", "#F3A33C"),
    "clean-news": ("#F4FBFC", "#123E4A", "#168B93", "#F2994A"),
    "warm-news": ("#FBF5EA", "#49372A", "#B45F35", "#DCA24D"),
    "open-coordinates": ("#F7F3E8", "#124F4B", "#15968A", "#F48632"),
    "code-archive": ("#F5F1E8", "#263E56", "#476D91", "#D89A35"),
    "field-notes": ("#F8F0DD", "#514936", "#927A4E", "#D3703A"),
    "clean-grid": ("#F5FBFC", "#173F49", "#2A8FA1", "#F1A23D"),
}


def font(size: int, bold: bool = False):
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def shorten(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def draw_grid(draw, box, color, step=48):
    x0, y0, x1, y1 = box
    for x in range(x0, x1 + 1, step):
        draw.line((x, y0, x, y1), fill=color, width=1)
    for y in range(y0, y1 + 1, step):
        draw.line((x0, y, x1, y), fill=color, width=1)


def cover_panel(size, title, kicker, palette, square=False):
    bg, ink, primary, accent = palette
    image = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(image)
    width, height = size
    draw_grid(draw, (0, 0, width, height), "#DCEAEC", 54)
    draw.rounded_rectangle((24, 24, width - 24, height - 24), 28, fill="#FFFFFF", outline=primary, width=2)
    if square:
        draw.ellipse((width - 118, height - 122, width - 38, height - 42), fill=primary)
        draw.arc((width - 180, height - 190, width - 20, height - 30), 195, 340, fill=accent, width=8)
    else:
        draw.ellipse((width - 205, -55, width + 55, 205), fill=primary)
        draw.arc((width - 260, 120, width - 25, 355), 200, 350, fill=accent, width=10)
        draw.line((width - 235, 265, width - 80, 215), fill=accent, width=8)
        draw.ellipse((width - 247, 255, width - 225, 277), fill="#FFFFFF", outline=accent, width=4)
    left = 54 if not square else 38
    display_kicker = kicker if not square else kicker.split("·")[0].strip()
    draw.text((left, 58), display_kicker, font=font(24 if not square else 21, True), fill=primary)
    display_title = re.sub(r"\s+", "", title) if square else title
    max_chars = 16 if not square else 8
    words = [shorten(display_title, max_chars)] if len(display_title) <= max_chars else [display_title[:max_chars], shorten(display_title[max_chars:], max_chars)]
    y = 112
    for line in words[:2]:
        draw.text((left, y), line, font=font(43 if not square else 34, True), fill=ink)
        y += 58 if not square else 50
    draw.rounded_rectangle((left, height - 72, min(width - 40, left + 220), height - 42), 15, fill=accent)
    draw.text((left + 16, height - 69), "未完地图 · 保持好奇", font=font(17, True), fill="#FFFFFF")
    return image


def body_card(size, item, index, content_type, palette):
    bg, ink, primary, accent = palette
    image = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(image)
    width, height = size
    draw_grid(draw, (0, 0, width, height), "#DCEAEC", 64)
    draw.rounded_rectangle((42, 42, width - 42, height - 42), 32, fill="#FFFFFF", outline=primary, width=3)
    draw.rounded_rectangle((76, 74, 205, 132), 28, fill=primary)
    label = "昨日坐标" if content_type == "daily-news" else "开源坐标"
    draw.text((96, 86), f"{index:02d}", font=font(25, True), fill="#FFFFFF")
    draw.text((234, 84), label, font=font(27, True), fill=primary)
    title = item.get("title") or item.get("repo") or "待确认内容"
    subtitle = item.get("summary") or item.get("description") or ""
    draw.text((76, 182), shorten(title, 27), font=font(42, True), fill=ink)
    draw.multiline_text((76, 255), shorten(subtitle, 58), font=font(25), fill="#536871", spacing=12)
    cx, cy = width - 230, 395
    if content_type == "daily-news":
        draw.ellipse((cx - 92, cy - 92, cx + 92, cy + 92), outline=primary, width=10)
        draw.line((cx - 125, cy + 85, cx - 20, cy + 10, cx + 68, cy + 45, cx + 135, cy - 72), fill=accent, width=14, joint="curve")
        for px, py in ((cx - 125, cy + 85), (cx - 20, cy + 10), (cx + 68, cy + 45), (cx + 135, cy - 72)):
            draw.ellipse((px - 10, py - 10, px + 10, py + 10), fill="#FFFFFF", outline=accent, width=5)
    else:
        draw.rounded_rectangle((cx - 110, cy - 96, cx + 110, cy + 96), 24, fill=primary)
        draw.text((cx - 72, cy - 61), "</>", font=font(58, True), fill="#FFFFFF")
        for offset in (-140, -70, 0, 70, 140):
            draw.line((cx + offset // 2, cy + 125, cx + offset, cy + 175), fill=accent, width=7)
            draw.ellipse((cx + offset - 9, cy + 166, cx + offset + 9, cy + 184), fill=accent)
    category_names = {"society": "社会民生", "politics": "时政", "finance": "财经", "technology": "科技", "international": "国际", "sports": "体育", "culture": "文化"}
    category = category_names.get(item.get("category"), item.get("category")) or (item.get("license") if content_type == "github-hot" else "值得继续关注")
    draw.rounded_rectangle((76, height - 117, 420, height - 72), 22, fill="#EDF6F7")
    draw.text((96, height - 108), shorten(category, 18), font=font(20, True), fill=primary)
    return image


def ending_card(size, content_type, palette):
    bg, ink, primary, accent = palette
    image = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(image)
    width, height = size
    draw_grid(draw, (0, 0, width, height), "#DCEAEC", 60)
    draw.ellipse((90, 120, 390, 420), outline=primary, width=12)
    draw.arc((165, 195, 630, 605), 195, 342, fill=accent, width=15)
    draw.ellipse((565, 500, 599, 534), fill="#FFFFFF", outline=accent, width=7)
    heading = "明天，地图继续更新" if content_type == "daily-news" else "下周，继续寻找开源坐标"
    draw.text((500, 220), heading, font=font(42, True), fill=ink)
    draw.text((500, 298), "你最想继续追踪哪一条？", font=font(28), fill=primary)
    draw.rounded_rectangle((500, 375, 930, 430), 27, fill=primary)
    draw.text((535, 386), "留言告诉我们 · 未完地图", font=font(23, True), fill="#FFFFFF")
    return image


def render_images(directory: Path, payload: dict, theme: str, title: str):
    directory.mkdir(parents=True, exist_ok=True)
    palette = PALETTES[theme]
    kicker = "昨日大事 · 每日观察" if payload["content_type"] == "daily-news" else "GitHub 热门 · 每周精选"
    wide = cover_panel((900, 383), title, kicker, palette)
    square = cover_panel((383, 383), title, kicker, palette, square=True)
    combined = Image.new("RGB", (1283, 383), palette[0]); combined.paste(wide, (0, 0)); combined.paste(square, (900, 0))
    for name, image in (("横版封面.png", wide), ("方形封面.png", square), ("合并封面.png", combined)):
        image.save(directory / name, optimize=True)
    prefix = "新闻" if payload["content_type"] == "daily-news" else "项目"
    for index, item in enumerate(payload["items"], 1):
        body_card((1200, 675), item, index, payload["content_type"], palette).save(directory / f"{prefix}-{index:02d}.png", optimize=True)
    ending_card((1200, 675), payload["content_type"], palette).save(directory / "结尾图.png", optimize=True)


def build_article(payload: dict):
    items = payload["items"]
    if payload["content_type"] == "daily-news":
        title = f"昨天，这 {len(items)} 件事值得关注"
        intro = "真正影响生活的变化，往往不会只停留在热搜里。它可能藏在一项新安排、一组数字，或一项刚刚落地的技术中。今天沿着几条不同的线索回看昨天：哪些已经抵达日常，哪些还需要继续观察。"
        lines = [f"# {title}", "", intro, "", "> 昨日坐标｜把重要变化放回它真实发生的位置"]
        for index, item in enumerate(items, 1):
            lines += ["", "---", "", f"## {index:02d}｜{item.get('title','')}", "", f"![{item.get('title','')}](images/新闻-{index:02d}.png)", "", item.get("summary") or "原文未提供摘要，请人工补充。", "", f"**发生时间**　{item.get('published_at','待确认')}", "", f"**信息来源**　[{item.get('source','原始来源')}]({item.get('url','')})"]
        lines += ["", "---", "", "## 地图之外，再多看一步", "", "一条新闻的意义，不只在它昨天有没有登上热搜，而在它接下来会不会改变我们的选择。你最想继续追踪哪一件事？也欢迎留下你看到的线索，我们明天接着核对。", "", "![结尾图](images/结尾图.png)"]
        summary = f"回看昨天值得继续关注的 {len(items)} 条变化：不追逐热闹，只梳理事实、影响与后续线索。"
    else:
        title = f"本周 GitHub 热门：{len(items)} 个值得关注的开源项目"
        intro = "一个项目登上热榜，可能是踩中了当下的需求；一个项目值得留下，则要看它能否真正解决问题。本周从热度之外再走一步：看看这些开源工具在做什么、适合谁，以及开始使用前有哪些门槛需要知道。"
        lines = [f"# {title}", "", intro, "", "> 开源坐标｜热度负责把项目推到眼前，价值决定它能走多远"]
        for index, item in enumerate(items, 1):
            highlights = "、".join(item.get("highlights") or []) or "用途明确、资料可查"
            lines += ["", "---", "", f"## {index:02d}｜{item.get('repo','')}", "", f"![{item.get('repo','')}](images/项目-{index:02d}.png)", "", item.get("description", ""), "", f"**解决什么问题**　{item.get('description','待确认')}", "", f"**值得注意**　{highlights}", "", f"**适合谁**　{item.get('audience','待确认')}", "", f"**使用门槛**　{item.get('install','待确认')}；平台：{item.get('platform','待确认')}", "", f"**维护与许可证**　最近提交 {item.get('last_commit','待确认')}；许可证 {item.get('license','未发现明确许可证')}", "", f"**风险与限制**　{item.get('risks','发布前需要人工复核')}", "", f"**官方地址**　[{item.get('repo','GitHub 仓库')}]({item.get('official_url','')})"]
        lines += ["", "---", "", "## 最后留一个坐标", "", "开源真正有趣的地方，不是项目数量又增加了，而是有人把一个反复出现的问题做成了所有人都能继续改进的答案。这里面你最想试哪一个？也欢迎推荐下周值得沿线寻找的项目。", "", "![结尾图](images/结尾图.png)"]
        summary = f"本周精选 {len(items)} 个值得普通读者关注的开源项目，说明用途、门槛、维护状态、许可证与风险。"
    return "\n".join(lines), title, summary


def inline(text: str, primary: str):
    links = []
    def repl(match):
        links.append((match.group(1), match.group(2))); return f"@@LINK{len(links)-1}@@"
    escaped = html.escape(re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)", repl, text))
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    for index, (label, url) in enumerate(links):
        escaped = escaped.replace(f"@@LINK{index}@@", f'<a href="{html.escape(url)}" style="color:{primary};text-decoration:none;overflow-wrap:anywhere">{html.escape(label)}</a>')
    return escaped


def data_uri(path: Path):
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def build_html(markdown: str, image_dir: Path, payload: dict, theme: str):
    bg, ink, primary, accent = PALETTES[theme]
    label = "昨日坐标" if payload["content_type"] == "daily-news" else "开源坐标"
    blocks = [f'<section style="margin:0 0 26px;padding:18px 20px;background:{bg};border-left:5px solid {primary};border-radius:4px"><strong style="color:{primary};font-size:15px;letter-spacing:1px">{label}</strong><div style="margin-top:6px;color:#64747a;font-size:13px">未完地图 · 记录正在发生的世界</div></section>']
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line: continue
        if line.startswith("!["):
            match = re.match(r"!\[([^]]*)\]\(([^)]+)\)", line)
            src = data_uri(image_dir / Path(match.group(2)).name)
            blocks.append(f'<img src="{src}" alt="{html.escape(match.group(1))}" style="display:block;width:100%;height:auto;margin:24px 0;border-radius:10px">'); continue
        if line == "---": blocks.append(f'<div style="height:1px;background:{primary}22;margin:34px 0"></div>'); continue
        if line.startswith("# "): blocks.append(f'<h1 style="font-size:29px;line-height:1.45;color:{ink};margin:0 0 20px;font-weight:800">{inline(line[2:],primary)}</h1>'); continue
        if line.startswith("## "): blocks.append(f'<section style="margin:30px 0 16px"><div style="display:inline-block;padding:3px 10px;background:{accent};color:#fff;border-radius:14px;font-size:13px;font-weight:700">{label}</div><h2 style="font-size:22px;line-height:1.5;color:{ink};margin:10px 0 0;font-weight:800">{inline(line[3:],primary)}</h2></section>'); continue
        if line.startswith("> "): blocks.append(f'<blockquote style="margin:20px 0;padding:16px 18px;background:{bg};border:0;border-radius:8px;color:{primary};font-size:15px;line-height:1.8">{inline(line[2:],primary)}</blockquote>'); continue
        if line.startswith("**"):
            blocks.append(f'<p style="font-size:15px;line-height:1.85;color:#465C63;margin:7px 0;padding:8px 12px;background:{bg};border-radius:6px;overflow-wrap:anywhere">{inline(line,primary)}</p>'); continue
        blocks.append(f'<p style="font-size:16px;line-height:1.95;color:#31474F;margin:12px 0;text-align:justify;overflow-wrap:anywhere">{inline(line,primary)}</p>')
    notice = "" if payload["status"] == "ready_for_human_review" else '<div style="max-width:740px;margin:18px auto;padding:12px;background:#FFF2CC;color:#6B5415">输入内容仍需人工核验，请勿直接发布。</div>'
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>微信公众号审核包</title></head><body style="margin:0;background:#EAF1F4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif"><div style="position:sticky;top:0;background:#102F49;padding:15px;text-align:center;z-index:9"><button id="copy-wechat" style="padding:12px 24px;border:0;border-radius:7px;background:#fff;color:#1769E0;font-size:17px;font-weight:700;cursor:pointer" onclick="copyWechat()">一键复制公众号正文</button><span id="copy-status" style="color:white;margin-left:14px">复制后粘贴到微信公众号编辑器</span></div>{notice}<main style="max-width:740px;margin:24px auto;background:#fff;padding:34px 38px;box-sizing:border-box;border-radius:14px"><section id="wechat-content">{''.join(blocks)}</section></main><script>async function copyWechat(){{const node=document.getElementById('wechat-content');try{{const htmlBlob=new Blob([node.innerHTML],{{type:'text/html'}});const textBlob=new Blob([node.innerText],{{type:'text/plain'}});await navigator.clipboard.write([new ClipboardItem({{'text/html':htmlBlob,'text/plain':textBlob}})]);document.getElementById('copy-status').textContent='复制成功，请到公众号编辑器粘贴';}}catch(error){{const range=document.createRange();range.selectNodeContents(node);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);document.execCommand('copy');selection.removeAllRanges();document.getElementById('copy-status').textContent='已复制，请粘贴后检查图片';}}}}</script></body></html>'''
