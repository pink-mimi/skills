from __future__ import annotations

import base64
import difflib
import html
import io
import re
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ASSETS = Path(__file__).resolve().parents[1] / "assets"

PALETTES = {
    "news-blue": ("#EAF4FF", "#0B3154", "#1769E0", "#F3A33C"),
    "clean-news": ("#F4FBFC", "#123E4A", "#168B93", "#F2994A"),
    "warm-news": ("#FBF5EA", "#49372A", "#B45F35", "#DCA24D"),
    "open-coordinates": ("#F7F3E8", "#124F4B", "#15968A", "#F48632"),
    "code-archive": ("#F5F1E8", "#263E56", "#476D91", "#D89A35"),
    "field-notes": ("#F8F0DD", "#514936", "#927A4E", "#D3703A"),
    "clean-grid": ("#F5FBFC", "#173F49", "#2A8FA1", "#F1A23D"),
}

NEWS_REMINDER_RULES = (
    ("边界说明", ("争议", "传闻", "谣言", "辟谣", "数据存疑", "信息不完整", "尚未证实")),
    ("实用提醒", ("天气", "降雨", "暴雨", "台风", "灾害", "地震", "交通", "安全", "应急", "预警")),
    ("接下来关注", ("后续", "仍在", "持续", "进展", "通报", "待落地", "尚未公布")),
    ("与你有关", ("政策", "民生", "教育", "医疗", "消费", "就业", "社保", "公共服务")),
)

NEWS_NOTICE_RULES = (
    (
        ("weather", "天气", "降雨", "暴雨", "台风", "灾害", "地震", "交通", "安全", "应急", "预警"),
        "天气、灾害、交通和公共安全信息可能持续更新，请关注属地权威预警与最新通报。",
    ),
    (
        ("finance", "财经", "市场", "交易", "金融", "经济数据"),
        "市场数据可能随交易、统计周期和统计口径变化，请以权威机构最新数据为准。",
    ),
    (
        ("politics", "政策", "法规", "办法", "条例", "主管部门"),
        "政策内容及执行安排可能继续完善，请以主管部门正式文件和实际执行安排为准。",
    ),
    (
        ("争议", "传闻", "谣言", "辟谣", "数据存疑", "信息不完整", "尚未证实"),
        "争议和未证实信息仍可能变化，请关注后续权威核实。",
    ),
)


def choose_news_reminder_label(item: dict) -> str:
    fields = [
        item.get("category", ""),
        item.get("title", ""),
        item.get("summary", ""),
        *(item.get("keywords") or []),
    ]
    haystack = " ".join(str(value) for value in fields).lower()
    for label, terms in NEWS_REMINDER_RULES:
        if any(term.lower() in haystack for term in terms):
            return label
    return "值得留意"


def build_news_notice(items: list[dict]) -> str:
    fields = []
    for item in items:
        fields.extend((item.get("category", ""), item.get("title", ""), item.get("summary", "")))
        fields.extend(item.get("keywords") or [])
    haystack = " ".join(str(value) for value in fields).lower()
    notices = [notice for terms, notice in NEWS_NOTICE_RULES if any(term.lower() in haystack for term in terms)]
    if not notices:
        return "本文依据公开资料整理，相关信息请以原始来源最新内容为准。"
    return "本文依据公开资料整理。" + "".join(notices)


def normalize_news_text(value: str) -> str:
    return re.sub(r"[\W_]+", "", str(value).lower())


def filter_news_follow_up(points: list[str], titles: list[str]) -> list[str]:
    normalized_titles = [normalize_news_text(title) for title in titles if normalize_news_text(title)]
    kept = []
    seen = set()
    for point in points:
        normalized = normalize_news_text(point)
        if not normalized or normalized in seen:
            continue
        repeats_title = any(
            normalized in title
            or title in normalized
            or difflib.SequenceMatcher(None, normalized, title).ratio() >= 0.72
            for title in normalized_titles
        )
        if repeats_title:
            continue
        seen.add(normalized)
        kept.append(point)
    return kept


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


def wrap_by_width(draw, text: str, text_font, max_width: int, max_lines: int = 2) -> list[str]:
    text = re.sub(r"\s+", "", str(text or ""))
    lines, current = [], ""
    for character in text:
        candidate = current + character
        if current and draw.textbbox((0, 0), candidate, font=text_font)[2] > max_width:
            lines.append(current)
            current = character
            if len(lines) == max_lines - 1:
                break
        else:
            current = candidate
    remainder_start = sum(len(line) for line in lines)
    remainder = text[remainder_start:]
    if len(lines) < max_lines and remainder:
        current = ""
        for character in remainder:
            candidate = current + character
            if current and draw.textbbox((0, 0), candidate + "…", font=text_font)[2] > max_width:
                current = current.rstrip("，。；、") + "…"
                break
            current = candidate
        lines.append(current)
    return lines[:max_lines]


def draw_grid(draw, box, color, step=48):
    x0, y0, x1, y1 = box
    for x in range(x0, x1 + 1, step):
        draw.line((x, y0, x, y1), fill=color, width=1)
    for y in range(y0, y1 + 1, step):
        draw.line((x0, y, x1, y), fill=color, width=1)


def cover_panel(size, title, kicker, palette, square=False, base_path=None):
    bg, ink, primary, accent = palette
    if base_path and Path(base_path).exists():
        centering = (0.34, 0.5) if square else (0.5, 0.5)
        with Image.open(base_path) as source:
            image = ImageOps.fit(source.convert("RGB"), size, method=Image.Resampling.LANCZOS, centering=centering)
        veil = Image.new("RGBA", size, (0, 0, 0, 0))
        veil_draw = ImageDraw.Draw(veil)
        width, height = size
        panel_right = width - 28 if square else int(width * 0.58)
        veil_draw.rounded_rectangle((22, 24, panel_right, height - 24), 26, fill=(255, 255, 255, 238), outline=primary, width=2)
        image = Image.alpha_composite(image.convert("RGBA"), veil).convert("RGB")
    else:
        image = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(image)
    width, height = size
    if not (base_path and Path(base_path).exists()):
        draw_grid(draw, (0, 0, width, height), "#DCEAEC", 54)
        draw.rounded_rectangle((24, 24, width - 24, height - 24), 28, fill="#FFFFFF", outline=primary, width=2)
    if square and not (base_path and Path(base_path).exists()):
        draw.ellipse((width - 118, height - 122, width - 38, height - 42), fill=primary)
        draw.arc((width - 180, height - 190, width - 20, height - 30), 195, 340, fill=accent, width=8)
    elif not (base_path and Path(base_path).exists()):
        draw.ellipse((width - 205, -55, width + 55, 205), fill=primary)
        draw.arc((width - 260, 120, width - 25, 355), 200, 350, fill=accent, width=10)
        draw.line((width - 235, 265, width - 80, 215), fill=accent, width=8)
        draw.ellipse((width - 247, 255, width - 225, 277), fill="#FFFFFF", outline=accent, width=4)
    left = 54 if not square else 38
    display_kicker = kicker if not square else kicker.split("·")[0].strip()
    draw.text((left, 58), display_kicker, font=font(24 if not square else 21, True), fill=primary)
    display_title = re.sub(r"\s+", "", title)
    title_font = font(39 if not square else 34, True)
    panel_right = width - 42 if square else (int(width * 0.58) - 30 if base_path and Path(base_path).exists() else width - 42)
    words = wrap_by_width(draw, display_title, title_font, panel_right - left, 2)
    y = 112
    for line in words[:2]:
        draw.text((left, y), line, font=title_font, fill=ink)
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


def news_overview_card(size, items, palette, base_path=None):
    bg, ink, primary, accent = palette
    if base_path and Path(base_path).exists():
        with Image.open(base_path) as source:
            image = ImageOps.fit(source.convert("RGB"), size, method=Image.Resampling.LANCZOS)
        shade = Image.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(shade).rounded_rectangle((34, 30, 1166, 158), 28, fill=(255, 255, 255, 230))
        image = Image.alpha_composite(image.convert("RGBA"), shade).convert("RGB")
    else:
        image = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(image)
    width, height = size
    if not (base_path and Path(base_path).exists()):
        draw_grid(draw, (0, 0, width, height), "#D9E8F3", 64)
        draw.rounded_rectangle((35, 35, width-35, height-35), 30, fill="#FFFFFF", outline=primary, width=3)
    draw.text((68, 62), "昨日新闻 · 一日脉络", font=font(38, True), fill=ink)
    draw.text((70, 118), "从事实出发，看见变化之间的联系", font=font(22), fill=primary)
    if base_path and Path(base_path).exists():
        return image
    usable=items[:6]; start_x=115; end_x=width-115; y=375
    draw.line((start_x,y,end_x,y),fill=primary,width=12)
    gap=(end_x-start_x)//max(1,len(usable)-1) if len(usable)>1 else 0
    for index,item in enumerate(usable):
        x=start_x+index*gap
        draw.ellipse((x-34,y-34,x+34,y+34),fill="#FFFFFF",outline=primary,width=8)
        draw.ellipse((x-12,y-12,x+12,y+12),fill=accent)
        title=shorten(item.get("title",""),10)
        category_names = {"society": "社会民生", "politics": "时政", "finance": "财经", "technology": "科技", "international": "国际", "sports": "体育", "culture": "文化"}
        category=shorten(category_names.get(item.get("category"), item.get("category","新闻")),6)
        ty=220 if index%2==0 else 465
        draw.rounded_rectangle((x-76,ty-18,x+76,ty+82),18,fill=bg)
        draw.text((x-58,ty-6),category,font=font(18,True),fill=primary)
        draw.multiline_text((x-58,ty+23),title,font=font(17),fill=ink,spacing=5)
        draw.line((x,ty+82 if index%2==0 else ty-18,x,y-38 if index%2==0 else y+38),fill="#A9C7D9",width=3)
    return image


def render_images(directory: Path, payload: dict, theme: str, title: str, visual: dict | None = None):
    directory.mkdir(parents=True, exist_ok=True)
    palette = tuple(visual["palette"]) if visual else PALETTES[theme]
    kicker = "昨日大事 · 每日观察" if payload["content_type"] == "daily-news" else "GitHub 热门 · 每周精选"
    use_bundled_base = payload["content_type"] == "daily-news" and visual and Path(visual["cover_path"]).exists()
    cover_base = Path(visual["cover_path"]) if use_bundled_base else None
    wide = cover_panel((900, 383), title, kicker, palette, base_path=cover_base)
    square = cover_panel((383, 383), title, kicker, palette, square=True, base_path=cover_base)
    combined = Image.new("RGB", (1283, 383), palette[0]); combined.paste(wide, (0, 0)); combined.paste(square, (900, 0))
    for name, image in (("横版封面.png", wide), ("方形封面.png", square), ("合并封面.png", combined)):
        image.save(directory / name, optimize=True)
    if payload["content_type"] == "daily-news":
        overview_base = Path(visual["overview_path"]) if visual and Path(visual["overview_path"]).exists() else None
        news_overview_card((1200, 675), payload["items"], palette, overview_base).save(directory / "新闻一日脉络.png", optimize=True)
    else:
        for index, item in enumerate(payload["items"], 1):
            body_card((1200, 675), item, index, payload["content_type"], palette).save(directory / f"项目-{index:02d}.png", optimize=True)
    ending_card((1200, 675), payload["content_type"], palette).save(directory / "结尾图.png", optimize=True)
    return visual.get("image_mode", "weekday_fallback") if use_bundled_base else "template_fallback"


def build_article(payload: dict):
    items = payload["items"]
    if payload["content_type"] == "daily-news":
        editorial=payload.get("editorial") or {}
        start=datetime.fromisoformat(payload["window"]["start"]); end=datetime.fromisoformat(payload["window"]["end"])
        date_label=f"{start.month}月{start.day}日"
        title = editorial.get("title") or f"{date_label}国内新闻梳理：{len(items)}条变化值得继续关注"
        overview=editorial.get("overview") or [item.get("summary") or item.get("title","") for item in items]
        window_text=f"北京时间 {start.year}年{start.month}月{start.day}日{start:%H:%M}—{end.month}月{end.day}日{end:%H:%M}"
        lines = [f"# {title}", "", "<!-- role:time-window -->", f"> 统计时段：{window_text}。", "", "## 30秒速览", ""]
        lines += [f"- {text}" for text in overview]
        lines += ["", "![国内新闻一日脉络](images/新闻一日脉络.png)"]
        numerals="一二三四五六七八九十"
        for index, item in enumerate(items, 1):
            keywords="｜".join(item.get("keywords") or [item.get("category","新闻")])
            reminder_label=choose_news_reminder_label(item)
            lines += ["", "---", "", f"## {numerals[index-1] if index<=len(numerals) else index}、{item.get('title','')}", "", "<!-- role:keywords -->", f"> **关键词：{keywords}**"]
            sections = (
                ("发生了什么", item.get("what_happened") or item.get("summary")),
                ("为什么重要", item.get("why_it_matters")),
                ("普通人需要注意什么", item.get("reader_action")),
            )
            for section_label, section_text in sections:
                if section_text:
                    lines += ["", "<!-- role:section-label -->", f"**{section_label}**", "", section_text]
            if item.get("editor_note"):
                lines += ["", "<!-- role:editor-note -->", f"> **{reminder_label}：** {item['editor_note']}"]
        follow_up=filter_news_follow_up(editorial.get("follow_up") or [], [item.get("title","") for item in items])
        if follow_up:
            lines += ["", "## 今天值得关注", "", *[f"- {text}" for text in follow_up]]
        lines += ["", "## 参考来源", ""]
        for index,item in enumerate(items,1):
            source_url=item.get("url","")
            lines.append(f"{index}. [{item.get('source','原始来源')}：{item.get('title','')}]({source_url})\n   原文地址：{source_url}")
        lines += ["", f"> {build_news_notice(items)}", "", "![结尾图](images/结尾图.png)"]
        summary = editorial.get("summary") or f"梳理{date_label}值得继续关注的 {len(items)} 条国内新闻，说明发生了什么、为什么重要，以及普通人需要留意什么。"
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


def build_html(markdown: str, image_dir: Path, payload: dict, theme: str, visual: dict | None = None):
    bg, ink, primary, accent = tuple(visual["palette"]) if visual else PALETTES[theme]
    label = "昨日坐标" if payload["content_type"] == "daily-news" else "开源坐标"
    title=next((line[2:].strip() for line in markdown.splitlines() if line.startswith("# ")),"微信公众号审核包")
    blocks = []
    pending_role = None
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line: continue
        role_match = re.fullmatch(r"<!-- role:([a-z-]+) -->", line)
        if role_match:
            pending_role = role_match.group(1)
            continue
        if line.startswith("!["):
            match = re.match(r"!\[([^]]*)\]\(([^)]+)\)", line)
            src = data_uri(image_dir / Path(match.group(2)).name)
            blocks.append(f'<img src="{src}" alt="{html.escape(match.group(1))}" style="display:block;width:100%;height:auto;margin:24px 0;border-radius:10px">'); continue
        if line == "---": blocks.append(f'<div style="height:1px;background:{primary}22;margin:34px 0"></div>'); continue
        if line.startswith("# "): continue
        if line.startswith("## "): blocks.append(f'<section style="margin:30px 0 16px"><div style="width:36px;height:4px;margin-bottom:10px;border-radius:2px;background:{primary}"></div><h2 style="font-size:22px;line-height:1.5;color:{ink};margin:0;font-weight:800">{inline(line[3:],primary)}</h2></section>'); continue
        if line.startswith("> "):
            content=inline(line[2:],primary)
            if pending_role == "time-window": blocks.append(f'<blockquote data-role="time-window" style="margin:18px 0;padding:14px 16px;border-left:4px solid {primary};background:{bg};border-radius:0 7px 7px 0;color:{ink};font-size:15px;line-height:1.8">{content}</blockquote>')
            elif pending_role == "keywords": blocks.append(f'<p data-role="keywords" style="margin:10px 0 18px;padding:11px 14px;background:{bg};color:{primary};border-radius:6px;font-size:15px;line-height:1.7;font-weight:700">{content}</p>')
            elif pending_role == "editor-note": blocks.append(f'<blockquote data-role="editor-note" style="margin:18px 0;padding:14px 16px;background:{bg};border:0;border-radius:7px;color:{ink};font-size:15px;line-height:1.8">{content}</blockquote>')
            else: blocks.append(f'<blockquote style="margin:20px 0;padding:16px 18px;background:{bg};border:0;border-radius:8px;color:{primary};font-size:15px;line-height:1.8">{content}</blockquote>')
            pending_role=None; continue
        if line.startswith("原文地址："):
            blocks.append(f'<p data-role="source-url" style="font-size:14px;line-height:1.75;color:#536875;margin:2px 0 14px;text-align:left;word-break:break-all;overflow-wrap:anywhere">{inline(line,primary)}</p>'); continue
        if line.startswith("- "): blocks.append(f'<p style="font-size:16px;line-height:1.75;color:#334E68;margin:6px 0 6px 18px;text-indent:-18px">•　{inline(line[2:],primary)}</p>'); continue
        if re.match(r"^\d+\. ",line): blocks.append(f'<p style="font-size:14px;line-height:1.8;color:#536875;margin:8px 0;overflow-wrap:anywhere">{inline(line,primary)}</p>'); continue
        if line.startswith("**"):
            if pending_role == "section-label": blocks.append(f'<p data-role="section-label" style="margin:18px 0 6px;color:{ink};font-size:17px;line-height:1.7;font-weight:800;overflow-wrap:anywhere">{inline(line,primary)}</p>')
            else: blocks.append(f'<p style="font-size:15px;line-height:1.85;color:#465C63;margin:7px 0;padding:8px 12px;background:{bg};border-radius:6px;overflow-wrap:anywhere">{inline(line,primary)}</p>')
            pending_role=None; continue
        blocks.append(f'<p style="font-size:16px;line-height:1.95;color:#31474F;margin:12px 0;text-align:justify;overflow-wrap:anywhere">{inline(line,primary)}</p>')
    ready_to_copy = payload["status"] == "ready_for_human_review"
    if ready_to_copy:
        button_attributes = 'style="padding:12px 24px;border:0;border-radius:7px;background:#fff;color:#2563EB;font-size:17px;font-weight:700;cursor:pointer" onclick="copyWechat()"'
        button_label = "一键复制公众号正文"
        notice = ""
    else:
        button_attributes = 'disabled aria-disabled="true" style="padding:12px 24px;border:0;border-radius:7px;background:#CBD5E1;color:#64748B;font-size:17px;font-weight:700;cursor:not-allowed"'
        button_label = "内容待补全，暂不可复制"
        notice = '<div data-role="review-notice" style="max-width:740px;margin:18px auto;padding:12px;background:#FFF2CC;color:#6B5415">输入内容缺少发布所需字段，请先完成人工补全和核验。</div>'
    cover=data_uri(image_dir/"横版封面.png")
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}｜微信排版预览</title></head><body style="margin:0;background:#EFF6FF;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif"><div style="position:sticky;top:0;background:#102A43;padding:15px;text-align:center;z-index:9"><button id="copy-wechat" {button_attributes}>{button_label}</button><span id="copy-status" style="color:#DBEAFE;margin-left:14px">复制后粘贴到微信公众号编辑器</span></div>{notice}<main style="max-width:760px;margin:24px auto;padding:0 16px 40px;box-sizing:border-box"><section id="cover-preview" style="margin-bottom:18px;padding:18px;background:#fff;border-radius:12px;box-shadow:0 4px 18px rgba(30,64,175,.08)"><img src="{cover}" alt="横版封面" style="display:block;width:100%;height:auto;border-radius:8px"><h1 style="margin:20px 0 8px;color:#102A43;font-size:27px;line-height:1.4">{html.escape(title)}</h1><p style="margin:0;color:#64748B;font-size:14px">封面和标题不包含在复制区域，请在公众号后台分别填写。</p></section><article id="wechat-content" style="padding:28px 24px;border-radius:12px;background:#fff;box-shadow:0 4px 18px rgba(30,64,175,.08)">{''.join(blocks)}</article></main><script>async function copyWechat(){{const node=document.getElementById('wechat-content');try{{const htmlBlob=new Blob([node.innerHTML],{{type:'text/html'}});const textBlob=new Blob([node.innerText],{{type:'text/plain'}});await navigator.clipboard.write([new ClipboardItem({{'text/html':htmlBlob,'text/plain':textBlob}})]);document.getElementById('copy-status').textContent='复制成功，请到公众号编辑器粘贴';}}catch(error){{const range=document.createRange();range.selectNodeContents(node);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);document.execCommand('copy');selection.removeAllRanges();document.getElementById('copy-status').textContent='已复制，请粘贴后检查图片';}}}}</script></body></html>'''
