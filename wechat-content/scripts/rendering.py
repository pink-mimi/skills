from __future__ import annotations

import base64
import difflib
import html
import io
import re
import urllib.request
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ASSETS = Path(__file__).resolve().parents[1] / "assets"
MAX_REMOTE_IMAGE_BYTES = 8 * 1024 * 1024

PALETTES = {
    "news-blue": ("#EAF4FF", "#0B3154", "#1769E0", "#F3A33C"),
    "clean-news": ("#F4FBFC", "#123E4A", "#168B93", "#F2994A"),
    "warm-news": ("#FBF5EA", "#49372A", "#B45F35", "#DCA24D"),
    "open-coordinates": ("#F7F3E8", "#124F4B", "#15968A", "#F48632"),
    "code-archive": ("#F5F1E8", "#263E56", "#476D91", "#D89A35"),
    "field-notes": ("#F8F0DD", "#514936", "#927A4E", "#D3703A"),
    "clean-grid": ("#F5FBFC", "#173F49", "#2A8FA1", "#F1A23D"),
    "ai-lab": ("#F4FAFB", "#123E4A", "#168B9B", "#F28C45"),
    "signal-map": ("#F7F4EA", "#253D4C", "#3C7564", "#D99A2B"),
    "clear-circuit": ("#F4F7FF", "#29335C", "#5368C6", "#2A9D8F"),
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


def normalize_overview(value, fallback: list[str]) -> list[str]:
    if isinstance(value,list):
        rows=[str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value,str):
        rows=[item.strip() for item in re.split(r"[；;。！？!?\r\n]+",value) if item.strip()]
    else:
        rows=[]
    rows=[row for row in rows if not is_internal_review_text(row)]
    return (rows or fallback)[:6]


def is_internal_review_text(value: str) -> bool:
    text = str(value or "")
    blocked = (
        "\u53d1\u5e03\u524d\u590d\u6838",
        "\u4ec5\u6709\u6743\u5a01\u5a92\u4f53\u62a5\u9053",
        "\u5f85\u4eba\u5de5\u786e\u8ba4",
        "\u5c1a\u672a\u6838\u9a8c",
        "\u5185\u5bb9\u5f85\u8865\u5168",
        "\u9700\u4eba\u5de5\u8865\u5168",
        "\u590d\u5236\u540e\u8bf7",
        "\u4e0a\u6e38\u6ca1\u6709\u5165\u9009\u65b0\u95fb",
    )
    return any(phrase in text for phrase in blocked)


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


def fit_cover_title(draw, text: str, max_width: int, max_lines: int = 2, preferred_size: int = 39, minimum_size: int = 24):
    """Fit a complete cover title. Cover titles must never be silently ellipsized."""
    normalized=re.sub(r"\s+","",str(text or ""))
    for size in range(preferred_size,minimum_size-1,-1):
        title_font=font(size,True); lines=[]; current=""
        for character in normalized:
            candidate=current+character
            if current and draw.textbbox((0,0),candidate,font=title_font)[2]>max_width:
                lines.append(current); current=character
            else:
                current=candidate
        if current: lines.append(current)
        if len(lines)<=max_lines:
            return lines,title_font
    title_font=font(minimum_size,True)
    return [normalized],title_font


def draw_grid(draw, box, color, step=48):
    x0, y0, x1, y1 = box
    for x in range(x0, x1 + 1, step):
        draw.line((x, y0, x, y1), fill=color, width=1)
    for y in range(y0, y1 + 1, step):
        draw.line((x0, y, x1, y), fill=color, width=1)


def cover_panel(size, title, kicker, palette, square=False, base_path=None):
    bg, ink, primary, accent = palette
    github_cover = "GitHub" in str(kicker)
    ai_cover = "AI 新发现" in str(kicker)
    has_base = bool(base_path and Path(base_path).exists())
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
        image = Image.new("RGB", size, "#071827" if github_cover else bg)
    draw = ImageDraw.Draw(image)
    width, height = size
    if not has_base:
        if github_cover:
            draw_grid(draw, (0, 0, width, height), "#17324A", 54)
            for offset in range(-height, width, 90):
                draw.line((offset, height, offset + height, 0), fill="#0E2538", width=2)
            draw.rounded_rectangle((24, 24, width - 24, height - 24), 28, fill="#091E2F", outline=primary, width=2)
            draw.rounded_rectangle((42, 42, width - 42, height - 42), 22, outline="#1FB6C966", width=1)
        elif ai_cover:
            draw_grid(draw, (0, 0, width, height), "#DCEAEC", 54)
            draw.rounded_rectangle((24, 24, width - 24, height - 24), 28, fill="#FFFFFF", outline=primary, width=2)
            node_box = (width - 300, 78, width - 56, height - 72) if not square else (width - 185, 95, width - 10, height - 60)
            for inset in (0, 45, 90):
                box = (node_box[0] + inset, node_box[1] + inset, node_box[2] - inset, node_box[3] - inset)
                if box[0] < box[2] and box[1] < box[3]:
                    draw.arc(box, 205, 340, fill=f"{primary}66", width=3)
            points = (
                [(width - 250, 150), (width - 168, 105), (width - 85, 178), (width - 205, 255), (width - 92, 318)]
                if not square else
                [(width - 148, 155), (width - 88, 122), (width - 38, 190), (width - 128, 252), (width - 52, 318)]
            )
            for start, end in zip(points, points[1:]):
                draw.line((*start, *end), fill=accent, width=5)
            for x, y in points:
                draw.ellipse((x - 16, y - 16, x + 16, y + 16), fill="#FFFFFF", outline=primary, width=5)
        else:
            draw_grid(draw, (0, 0, width, height), "#DCEAEC", 54)
            draw.rounded_rectangle((24, 24, width - 24, height - 24), 28, fill="#FFFFFF", outline=primary, width=2)
    if github_cover and not has_base:
        nodes = (
            [(width - 245, 78), (width - 175, 118), (width - 100, 88), (width - 222, 182), (width - 142, 214),
             (width - 66, 174), (width - 246, 296), (width - 168, 322), (width - 88, 284), (width - 42, 332)]
            if not square else
            [(width - 93, 84), (width - 53, 126), (width - 132, 153), (width - 76, 196), (width - 148, 242),
             (width - 58, 274), (width - 132, 315), (width - 86, 340)]
        )
        radar = (width - 302, 40, width - 24, height - 42) if not square else (width - 210, 68, width + 28, height - 30)
        for expand in (0, 52, 104):
            box = (radar[0] + expand, radar[1] + expand, radar[2] - expand, radar[3] - expand)
            if box[0] < box[2] and box[1] < box[3]:
                draw.arc(box, 205, 345, fill="#1FB6C944", width=2)
        for start, end in zip(nodes, nodes[1:]):
            draw.line((*start, *end), fill=accent, width=4)
        for position, (x, y) in enumerate(nodes, 1):
            radius = 15 if position <= 3 else 11
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill="#082032", outline=primary, width=4)
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill="#EAFBFF")
            if not square and position <= 10:
                draw.text((x - 7, y - 9), str(position), font=font(12, True), fill="#EAFBFF")
        draw.arc((width - 310, 48, width - 28, height - 34), 205, 345, fill=primary, width=5)
    elif square and not has_base:
        draw.ellipse((width - 118, height - 122, width - 38, height - 42), fill=primary)
        draw.arc((width - 180, height - 190, width - 20, height - 30), 195, 340, fill=accent, width=8)
    elif not has_base:
        draw.ellipse((width - 205, -55, width + 55, 205), fill=primary)
        draw.arc((width - 260, 120, width - 25, 355), 200, 350, fill=accent, width=10)
        draw.line((width - 235, 265, width - 80, 215), fill=accent, width=8)
        draw.ellipse((width - 247, 255, width - 225, 277), fill="#FFFFFF", outline=accent, width=4)
    left = 54 if not square else 38
    display_kicker = kicker if not square else kicker.split("·")[0].strip()
    kicker_fill = accent if github_cover and not has_base else primary
    title_fill = "#EAFBFF" if github_cover and not has_base else ink
    draw.text((left, 58), display_kicker, font=font(24 if not square else 21, True), fill=kicker_fill)
    display_title = re.sub(r"\s+", "", title)
    panel_right = width - 42 if square else (int(width * 0.58) - 30 if has_base else width - 42)
    words,title_font = fit_cover_title(draw,display_title,panel_right-left,2,34 if square else 39,24)
    y = 112
    for line in words[:2]:
        draw.text((left, y), line, font=title_font, fill=title_fill)
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
    label = {"daily-news": "昨日坐标", "ai-discovery": "AI 坐标"}.get(content_type, "开源坐标")
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
    elif content_type == "ai-discovery":
        draw.rounded_rectangle((cx - 105, cy - 82, cx + 105, cy + 82), 30, fill=primary)
        draw.ellipse((cx - 38, cy - 38, cx + 38, cy + 38), fill="#FFFFFF")
        for angle, px, py in ((0, cx + 130, cy), (1, cx - 120, cy - 66), (2, cx - 96, cy + 92), (3, cx + 88, cy - 95), (4, cx + 118, cy + 78)):
            draw.line((cx, cy, px, py), fill=accent, width=6)
            draw.ellipse((px - 12, py - 12, px + 12, py + 12), fill="#FFFFFF", outline=accent, width=5)
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
    heading = {"daily-news": "明天，地图继续更新", "ai-discovery": "下次，继续观察 AI 坐标"}.get(content_type, "下周，继续寻找开源坐标")
    draw.text((500, 220), heading, font=font(42, True), fill=ink)
    draw.text((500, 298), "你最想继续追踪哪一条？", font=font(28), fill=primary)
    draw.rounded_rectangle((500, 375, 930, 430), 27, fill=primary)
    draw.text((535, 386), "留言告诉我们 · 未完地图", font=font(23, True), fill="#FFFFFF")
    return image


def normalize_project_image(source: Image.Image, size=(1200, 675)) -> Image.Image:
    canvas = Image.new("RGB", size, "#F5FAFD")
    image = source.convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def github_topic_card(size, payload, index, palette):
    bg, ink, primary, accent = palette
    width, height = size
    image = Image.new("RGB", size, "#071827")
    draw = ImageDraw.Draw(image)
    draw_grid(draw, (0, 0, width, height), "#17324A", 54)
    draw.rounded_rectangle((54, 52, width - 54, height - 52), 34, fill="#092033", outline=primary, width=3)
    draw.text((92, 96), "本周开源雷达", font=font(34, True), fill=accent)
    labels = []
    try:
        labels = [str(value) for value in (payload.get("editorial") or {}).get("visual_routes") or []]
    except AttributeError:
        labels = []
    if not labels:
        labels = [
            str((item.get("reader_card") or {}).get("category_label") or item.get("category") or "开源项目")
            for item in (payload.get("items") or [])[:5]
        ]
    labels = [value for value in labels if value][:5] or ["工具", "资料", "工作流"]
    subtitle = [
        "热榜只是入口，真正值得留下来的，",
        "是能在具体场景里少绕路的项目。",
        "先看用途，再决定收藏。",
    ][(index - 1) % 3]
    draw.text((92, 154), subtitle, font=font(24), fill="#CDE7F2")
    radar_box = (width - 460, 92, width - 88, height - 92)
    for inset in (0, 70, 140, 210):
        box = (radar_box[0] + inset, radar_box[1] + inset, radar_box[2] - inset, radar_box[3] - inset)
        if box[0] < box[2] and box[1] < box[3]:
            draw.arc(box, 205, 345, fill="#1FB6C955", width=3)
    node_positions = [(790, 190), (900, 136), (1028, 216), (842, 348), (1014, 424)]
    for start, end in zip(node_positions, node_positions[1:]):
        draw.line((*start, *end), fill=accent, width=5)
    for number, (x, y) in enumerate(node_positions, 1):
        draw.ellipse((x - 22, y - 22, x + 22, y + 22), fill="#082032", outline=primary, width=5)
        draw.text((x - 7, y - 12), str(number), font=font(18, True), fill="#EAFBFF")
    y = 260
    for offset, label in enumerate(labels[:4]):
        pill_y = y + offset * 62
        draw.rounded_rectangle((92, pill_y, 420, pill_y + 40), 20, fill="#0F3148", outline="#1FB6C966", width=2)
        draw.text((116, pill_y + 8), label[:18], font=font(20, True), fill="#EAFBFF")
    draw.text((92, height - 108), "未完地图 · GitHub 热门", font=font(24, True), fill=primary)
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


def render_images(
    directory: Path,
    payload: dict,
    theme: str,
    title: str,
    visual: dict | None = None,
    project_images: list[dict] | None = None,
    article_images: list[dict] | None = None,
):
    directory.mkdir(parents=True, exist_ok=True)
    palette = tuple(visual["palette"]) if visual else PALETTES[theme]
    kicker = {"daily-news": "昨日大事 · 每日观察", "ai-discovery": "AI 新发现 · 藏宝图"}.get(payload["content_type"], "GitHub 热门 · 每周精选")
    use_bundled_base = payload["content_type"] == "daily-news" and visual and Path(visual["cover_path"]).exists()
    use_github_cover_base = (
        payload["content_type"] == "github-hot"
        and visual
        and visual.get("cover_image_mode") == "live_image2"
        and Path(visual.get("cover_path") or "").exists()
    )
    cover_base = Path(visual["cover_path"]) if (use_bundled_base or use_github_cover_base) else None
    wide = cover_panel((900, 383), title, kicker, palette, base_path=cover_base)
    square = cover_panel((383, 383), title, kicker, palette, square=True, base_path=cover_base)
    combined = Image.new("RGB", (1283, 383), palette[0]); combined.paste(wide, (0, 0)); combined.paste(square, (900, 0))
    for name, image in (("横版封面.png", wide), ("方形封面.png", square), ("合并封面.png", combined)):
        image.save(directory / name, optimize=True)
    if payload["content_type"] == "daily-news":
        overview_base = Path(visual["overview_path"]) if visual and Path(visual["overview_path"]).exists() else None
        news_overview_card((1200, 675), payload["items"], palette, overview_base).save(directory / "新闻一日脉络.png", optimize=True)
    elif payload["content_type"] == "github-hot":
        choices = {int(entry["rank"]): entry for entry in (project_images or [])}
        for index, item in enumerate(payload["items"], 1):
            target = directory / f"项目-{index:02d}.png"
            choice = choices.get(index) or {}
            source_path = choice.get("source_path")
            if int(payload.get("schema_version", 1)) != 2:
                body_card((1200, 675), item, index, payload["content_type"], palette).save(target, optimize=True)
            elif choice.get("image_mode") in {"official_verified", "live_image2"} and source_path:
                with Image.open(source_path) as source:
                    normalize_project_image(source).save(target, optimize=True)
            elif choice.get("image_mode") == "official_verified" and choice.get("source_url"):
                try:
                    source_url = str(choice.get("source_url") or "")
                    if Path(source_url).is_file():
                        with Image.open(source_url) as source:
                            normalize_project_image(source).save(target, optimize=True)
                    else:
                        request = urllib.request.Request(
                            source_url,
                            headers={"User-Agent": "wechat-content/3.1"},
                        )
                        with urllib.request.urlopen(request, timeout=20) as response:
                            blob = response.read(MAX_REMOTE_IMAGE_BYTES + 1)
                        if len(blob) > MAX_REMOTE_IMAGE_BYTES:
                            raise OSError("remote image exceeds maximum size")
                        with Image.open(io.BytesIO(blob)) as source:
                            normalize_project_image(source).save(target, optimize=True)
                    choice["source_path"] = str(target)
                except Exception:
                    choice.update(
                        image_mode="omitted",
                        source_path="",
                        fallback_reason="official_image_download_failed",
                    )
        for index, record in enumerate(article_images or [], 1):
            source_path = record.get("source_path")
            if source_path:
                with Image.open(source_path) as source:
                    normalize_project_image(source).save(directory / f"主题插图-{index:02d}.png", optimize=True)
            else:
                github_topic_card((1200, 675), payload, index, palette).save(directory / f"主题插图-{index:02d}.png", optimize=True)
    else:
        for index, item in enumerate(payload["items"], 1):
            body_card((1200, 675), item, index, payload["content_type"], palette).save(directory / f"AI发现-{index:02d}.png", optimize=True)
    ending_card((1200, 675), payload["content_type"], palette).save(directory / "结尾图.png", optimize=True)
    if payload["content_type"] == "daily-news":
        return visual.get("image_mode", "weekday_fallback") if visual else "template"
    if payload["content_type"] == "ai-discovery":
        return "ai_discovery_template"
    return "template_fallback"


def is_internal_package_title(value: str) -> bool:
    title=str(value or "").strip()
    return (
        not title
        or any(token in title for token in ("内容包","新闻包","审核包","工作台"))
        or bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}\s*新闻",title))
    )


def resolve_article_title(editorial: dict, date_label: str, item_count: int) -> str:
    prefix=f"{date_label}国内要闻："
    explicit=str(editorial.get("article_title") or "").strip()
    if explicit:
        topic=re.sub(r"^\d{1,2}月\d{1,2}日国内要闻[：:]\s*","",explicit).strip()
        if topic == explicit and re.match(r"^[^：:]+[：:]",explicit):
            topic=re.split(r"[：:]",explicit,maxsplit=1)[1].strip()
        if topic:
            return f"{prefix}{topic}"
    return f"{prefix}{item_count}条变化值得关注"


DAILY_NEWS_V2_GROUPS = (
    ("国内动态", {"politics", "society", "education", "legal", "public-safety", "public-interest", "general", "时政", "社会", "教育", "法治", "公共安全", "公共服务"}),
    ("财经与产业", {"finance", "market", "industry", "consumer", "财经", "市场", "产业", "消费"}),
    ("科技与未来", {"tech", "technology", "research", "ai", "科技", "科研", "AI"}),
    ("世界现场", {"world", "international", "国际"}),
)


def publication_date_label(end: datetime) -> str:
    return f"{end.month}月{end.day}日"


def resolve_daily_news_v2_title(editorial: dict, end: datetime, items: list[dict]) -> str:
    explicit = str(editorial.get("article_title") or "").strip()
    if explicit:
        return explicit
    categories = {str(item.get("category") or "") for item in items}
    topic = []
    if categories & (DAILY_NEWS_V2_GROUPS[0][1]):
        topic.append("政策")
    if categories & (DAILY_NEWS_V2_GROUPS[1][1]):
        topic.append("产业")
    if categories & (DAILY_NEWS_V2_GROUPS[2][1]):
        topic.append("科技")
    if any(str(item.get("geographic_scope")) == "international" or str(item.get("category")).lower() in {"world", "international"} for item in items):
        topic.append("全球动态")
    return f"{publication_date_label(end)}今日简报：{'、'.join(topic[:3]) or '重要动态'}"


def daily_news_v2_group(item: dict) -> str:
    category = str(item.get("category") or "general")
    if str(item.get("geographic_scope") or "").lower() == "international":
        return "世界现场"
    for label, categories in DAILY_NEWS_V2_GROUPS:
        if category in categories or category.lower() in categories:
            return label
    return "国内动态"


def build_daily_news_v2_article(payload: dict):
    items = payload["items"]
    editorial = payload.get("editorial") or {}
    start = datetime.fromisoformat(payload["window"]["start"])
    end = datetime.fromisoformat(payload["window"]["end"])
    title = resolve_daily_news_v2_title(editorial, end, items)
    lead = str(editorial.get("lead") or "过去 24 小时，几条变化值得放在同一张简报里看。").strip()
    window_text = f"北京时间 {start.year}年{start.month}月{start.day}日{start:%H:%M}—{end.month}月{end.day}日{end:%H:%M}"
    weekday = "一二三四五六日"[end.weekday()]
    lines = [
        f"# {title}",
        "",
        f"{publication_date_label(end)}，星期{weekday}。",
        "",
        lead,
        "",
        "<!-- role:time-window -->",
        f"> 统计时段：{window_text}。",
        "",
        "## 今日速览",
        "",
    ]
    grouped = {label: [] for label, _ in DAILY_NEWS_V2_GROUPS}
    for item in items:
        grouped.setdefault(daily_news_v2_group(item), []).append(item)
    for label, _categories in DAILY_NEWS_V2_GROUPS:
        group_items = grouped.get(label) or []
        if not group_items:
            continue
        lines += [f"### {label}", ""]
        for item in group_items:
            source = str(item.get("source") or "来源机构").strip()
            lines.append(f"- **{item.get('title','')}**：{item.get('brief','')}（{source}）")
        lines.append("")
    focus_ids = list(editorial.get("focus_event_ids") or [])
    focus = [item for event_id in focus_ids for item in items if item.get("event_id") == event_id]
    if focus:
        lines += ["", "## 重点解读", ""]
        for index, item in enumerate(focus, 1):
            keywords = "｜".join(item.get("keywords") or [item.get("category", "新闻")])
            lines += [
                f"### {index:02d}｜{item.get('title','')}",
                "",
                "<!-- role:keywords -->",
                f"> 关键词：{keywords}",
                "",
                "<!-- role:section-label -->",
                "**发生了什么**",
                "",
                str(item.get("what_happened") or "").strip(),
            ]
            if item.get("why_it_matters"):
                lines += ["", "<!-- role:section-label -->", "**为什么重要**", "", str(item.get("why_it_matters")).strip()]
            if item.get("reader_action"):
                lines += ["", "<!-- role:section-label -->", "**普通人需要注意什么**", "", str(item.get("reader_action")).strip()]
            if publishable_reader_tip(item.get("reader_tip")):
                lines += ["", "<!-- role:reader-tip -->", f"> 读者提示：{str(item.get('reader_tip')).strip()}"]
            lines.append("")
    lines += ["", "## 参考来源", ""]
    for index, item in enumerate(items, 1):
        source_url = item.get("url", "")
        lines.append(f"{index}. [{item.get('source','原始来源')}：{item.get('title','')}]({source_url})\n   原文地址：{source_url}")
    lines += ["", f"> {build_news_notice(items)}", "", "![结尾图](images/结尾图.png)"]
    summary = f"今日简报整理 {len(items)} 条经核验新闻，重点展开 {len(focus)} 条。"
    return "\n".join(lines), title, summary


def format_metric(value) -> str:
    if value is None or value == "":
        return ""
    return f"{int(value):,}" if isinstance(value, (int, float)) else str(value)


def github_v2_reader_warning(item: dict) -> list[str]:
    verification = item.get("verification") or {}
    warnings = []
    license_info = verification.get("license") or {}
    if license_info.get("status") != "verified":
        warnings.append("未发现明确许可证，使用、修改或分发前请先向项目方确认授权边界。")
    for risk in verification.get("risks") or []:
        if risk.get("reader_visible") and risk.get("summary"):
            warnings.append(str(risk["summary"]).strip())
    explicit = (item.get("reader_card") or {}).get("reader_warning")
    if explicit:
        warnings.append(str(explicit).strip())
    return list(dict.fromkeys(warnings))


def build_github_v2_article(payload: dict):
    items = payload["items"]
    title = f"本周 GitHub 热门：{len(items)} 个值得关注的开源项目"
    lines = [
        f"# {title}",
        "",
        "热度让项目进入视野，能解决什么问题、适合谁用，以及使用前有哪些限制，才决定它是否值得收藏。",
    ]
    image_labels = {
        "official_verified": "项目官方截图",
        "live_image2": "项目用途示意图",
        "local_project_card": "项目用途卡片",
    }
    for index, item in enumerate(items, 1):
        card = item.get("reader_card") or {}
        difficulty = card.get("difficulty") or {}
        metrics = card.get("metrics") or {}
        image_info = item.get("_project_image") or {}
        image_label = image_labels.get(image_info.get("image_mode"), "项目用途卡片")
        heading = card.get("category_label") or item.get("category") or "开源项目"
        name = card.get("name") or item.get("repo") or f"项目 {index}"
        lines += [
            "",
            "---",
            "",
            f"## #{index}｜{heading}",
            "",
            f"![{image_label}](images/项目-{index:02d}.png)",
            "",
            f"### {name}",
            "",
            f"**一句话推荐：** {card.get('recommendation') or card.get('summary') or '用途待确认'}",
            "",
            card.get("summary") or "",
            "",
            "**它能做什么？**",
            "",
        ]
        lines += [f"- {value}" for value in (card.get("highlights") or [])]
        audience = "、".join(card.get("audience") or []) or "需要进一步确认"
        difficulty_text = difficulty.get("label") or difficulty.get("level") or "待确认"
        difficulty_note = difficulty.get("note")
        lines += ["", f"**适合谁？** {audience}", "", f"**上手难度：{difficulty_text}**"]
        if difficulty_note:
            lines += ["", str(difficulty_note)]
        metric_parts = []
        if metrics.get("language"):
            metric_parts.append(str(metrics["language"]))
        if metrics.get("stars") is not None:
            metric_parts.append(f"{format_metric(metrics['stars'])} Star")
        if metrics.get("weekly_stars") is not None:
            metric_parts.append(f"本周新增 {format_metric(metrics['weekly_stars'])} Star")
        if metrics.get("forks") is not None:
            metric_parts.append(f"{format_metric(metrics['forks'])} Fork")
        if metric_parts:
            lines += ["", f"**项目数据：** {'｜'.join(metric_parts)}"]
        warnings = github_v2_reader_warning(item)
        if warnings:
            lines += ["", "**使用前注意：**", "", *[f"- {warning}" for warning in warnings]]
        official_url = item.get("official_url") or ""
        lines += ["", f"**项目地址：** [{item.get('repo') or name}]({official_url})"]
    lines += [
        "",
        "---",
        "",
        "## 最后留一个坐标",
        "",
        "开源项目值得关注的不只是热度，还包括它解决问题的方式、维护状态和使用边界。使用前请继续核对项目官方说明。",
        "",
        "![结尾图](images/结尾图.png)",
    ]
    summary = f"本周精选 {len(items)} 个开源项目，用轻量卡片说明用途、亮点、适用人群、门槛与必要风险。"
    return "\n".join(lines), title, summary


def text_list(value, fallback=None) -> list[str]:
    if isinstance(value, list):
        rows = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str) and value.strip():
        rows = [item.strip() for item in re.split(r"[;；\n]+", value) if item.strip()]
    else:
        rows = []
    return rows or list(fallback or [])


def availability_text(item: dict) -> str:
    availability = item.get("mainland_availability") or {}
    if isinstance(availability, dict):
        status = availability.get("status") or "待核验"
        notes = availability.get("notes") or ""
        extras = []
        if availability.get("requires_special_network"):
            extras.append("可能需要特殊网络条件")
        if availability.get("requires_overseas_phone"):
            extras.append("可能需要海外手机号")
        if availability.get("requires_overseas_card"):
            extras.append("可能需要海外支付卡")
        tail = "；".join([part for part in [notes, *extras] if part])
        return f"{status}；{tail}" if tail else str(status)
    return str(availability or item.get("requirements") or "待核验")


def pricing_text(item: dict) -> str:
    details = item.get("pricing_details") or {}
    if not isinstance(details, dict):
        return str(item.get("pricing") or "待核验")
    parts = [
        details.get("free") or "",
        details.get("free_quota") or "",
        details.get("lowest_paid_price") or "",
        details.get("subscription") or "",
        details.get("auto_renewal") or "",
    ]
    paid_only = text_list(details.get("paid_only_features"))
    if paid_only:
        parts.append("付费功能：" + "、".join(paid_only))
    if details.get("verified_at"):
        parts.append(f"价格核验时间：{details.get('verified_at')}")
    return "；".join(str(part).strip() for part in parts if str(part).strip()) or str(item.get("pricing") or "待核验")


def verification_text(item: dict) -> str:
    grade = item.get("verification_grade") or "待分级"
    status = item.get("verification_status") or "unverified"
    feedback = text_list(item.get("public_feedback"))
    if grade == "A":
        return f"A 级：官方资料完整，并有公开反馈可参考；状态 {status}"
    if grade == "B":
        return f"B 级：主要依据官方资料，公开反馈仍有限；状态 {status}"
    return f"{grade} 级：资料仍需人工复核；状态 {status}"


def source_lines(item: dict) -> list[str]:
    sources = item.get("official_sources") or []
    if not sources and item.get("official_url"):
        sources = [{"name": "官方地址", "url": item.get("official_url")}]
    lines = []
    for index, source in enumerate(sources, 1):
        name = source.get("name") or f"资料来源 {index}"
        url = source.get("url") or item.get("official_url") or ""
        verified_at = source.get("verified_at") or "未记录核验时间"
        lines.append(f"{index}. [{name}]({url})\n   核验时间：{verified_at}")
    return lines


def build_ai_discovery_article(payload: dict):
    item = (payload.get("items") or [{}])[0]
    editorial = payload.get("editorial") or {}
    name = item.get("name") or "本期 AI 新发现"
    title = editorial.get("title") or f"AI 新发现：{name} 能帮谁少绕路？"
    audience = text_list(item.get("audience"), ["对 AI 工具有实际需求的读者"])
    not_for = text_list(item.get("not_for"), ["暂时没有相关场景的读者"])
    scenarios = text_list(item.get("scenarios"), ["资料整理", "流程拆解", "重复任务辅助"])[:3]
    risks = text_list(item.get("risks"), ["发布前继续复核隐私、费用、版权和可用地区"])
    privacy = text_list(item.get("privacy_and_rights"), risks)
    feedback = text_list(item.get("public_feedback"), ["公开反馈有限，本文主要依据官方资料整理"])
    has_test_evidence = bool(item.get("tested") and (item.get("experience_notes") or item.get("test_notes") or item.get("evidence")))
    if has_test_evidence:
        test_boundary = "已有可追溯的试用记录，但本文仍按资料核验口径写作，发布前请人工复核。"
    elif item.get("tested"):
        test_boundary = "内容包标记为已测试，但未提供可追溯的实测记录；正文只按公开资料整理，不写亲身体验。"
    else:
        test_boundary = "未做亲身体验；本文依据公开资料整理，未进行完整实测，以下只写资料核验和可试用路径。"
    lines = [
        f"# {title}",
        "",
        "有些 AI 工具看起来像“又一个发布页”，真正需要判断的是：它能不能帮普通人少走一点具体的弯路。本期只看一个对象，不做榜单，也不把官方宣传写成实际体验。",
        "",
        f"> {test_boundary}",
        "",
        "## 30 秒速览",
        "",
        f"- 本期发现：{name}",
        f"- 它是什么：{item.get('use_case') or '一个待核验的 AI 工具或模型'}",
        f"- 适合谁：{'、'.join(audience[:3])}",
        f"- 主要用途：{item.get('recommendation') or item.get('use_case') or '发布前继续核验'}",
        f"- 使用门槛：{item.get('requirements') or '待核验'}",
        f"- 国内可用性：{availability_text(item)}",
        f"- 价格：{pricing_text(item)}",
        f"- 核验状态：{verification_text(item)}",
        "",
        f"![{name} 使用场景示意图](images/AI发现-01.png)",
        "",
        "## 一、它解决什么问题",
        "",
        item.get("use_case") or "这个条目的用途仍需补充官方资料后再判断。",
        "",
        "它值得被单独拿出来看，是因为它不是只给技术圈看的新鲜名词，而是尝试把 AI 能力放进一个更具体的任务里。",
        "",
        "## 二、它具体能做什么",
        "",
        f"{name} 目前公开资料显示的核心能力，是围绕“{item.get('use_case') or '待核验用途'}”展开。它更像一个可试用路径，而不是一个可以直接下结论的成品体验。",
        "",
        "## 三、三个普通人能理解的使用场景",
        "",
    ]
    lines += [f"- {scenario}" for scenario in scenarios]
    lines += [
        "",
        "## 四、谁适合用，谁暂时不需要",
        "",
        f"适合：{'、'.join(audience)}。",
        "",
        f"暂时不需要：{'、'.join(not_for)}。",
        "",
        "## 五、注册、地区、语言和设备门槛",
        "",
        f"平台：{'、'.join(text_list(item.get('platforms'), ['待核验']))}。中文支持：{item.get('supports_chinese') or '待核验'}。",
        "",
        f"大陆可用性：{availability_text(item)}",
        "",
        f"开始使用前需要注意：{item.get('requirements') or '注册、账号地区、设备要求和 API 条件仍需人工核验。'}",
        "",
        "## 六、免费额度和付费价格",
        "",
        pricing_text(item),
        "",
        "价格、免费额度、自动续费和地区币种都可能变化，发布前请重新打开官方价格页确认。",
        "",
        "## 七、目前的限制与风险",
        "",
    ]
    lines += [f"- {risk}" for risk in risks]
    lines += [
        "",
        "隐私与版权边界：",
        "",
        *[f"- {entry}" for entry in privacy],
        "",
        "## 八、值不值得关注",
        "",
        f"如果你的工作里已经出现了类似场景，{name} 值得加入待试用清单；如果只是被发布声量吸引，可以先收藏官方文档，等价格、地区和稳定性信息更清楚后再决定。",
        "",
        f"本期推荐理由：{item.get('recommendation') or '用途明确，但仍需人工复核后再发布。'}",
        "",
        "公开反馈摘录口径：",
        "",
        *[f"- {entry}" for entry in feedback],
        "",
        "## 九、官方地址和资料来源",
        "",
        *source_lines(item),
        "",
        "---",
        "",
        "## 最后留一个路标",
        "",
        "AI 新发现不负责制造焦虑，只负责把“听起来很厉害”的东西放回现实问题里：谁能用、怎么开始、要花多少钱、风险在哪里。发布前请继续人工核验官方链接和价格地区信息。",
        "",
        "![结尾图](images/结尾图.png)",
    ]
    summary = editorial.get("summary") or f"本期聚焦 {name}，依据公开资料核验用途、门槛、价格和风险边界。"
    return "\n".join(lines), title, summary


def build_article(payload: dict):
    items = payload["items"]
    if payload["content_type"] == "github-hot" and int(payload.get("schema_version", 1)) == 2:
        return build_github_v2_article(payload)
    if payload["content_type"] == "ai-discovery":
        return build_ai_discovery_article(payload)
    if payload["content_type"] == "ai-discovery":
        editorial = payload.get("editorial") or {}
        title = editorial.get("title") or f"AI 新发现：{len(items)} 个值得留意的新坐标"
        overview = normalize_overview(editorial.get("overview"), [item.get("recommendation") or item.get("use_case", "") for item in items])
        lines = [
            f"# {title}",
            "",
            "这期不做玄学预测，只把近期值得打开看看的 AI 新东西放到一张小地图上：它能做什么，适合谁，开始前有哪些门槛和风险。",
            "",
            "> AI 坐标｜先看用途，再决定要不要试。",
            "",
            "## 30 秒速览",
            "",
        ]
        lines += [f"- {text}" for text in overview[:5]]
        for index, item in enumerate(items, 1):
            risks = "；".join(item.get("risks") or ["发布前继续核验官方说明"])
            sources = item.get("official_sources") or []
            source = sources[0] if sources else {"name": "官方来源", "url": item.get("official_url", "")}
            has_test_evidence = bool(item.get("tested") and (item.get("experience_notes") or item.get("test_notes") or item.get("evidence")))
            if has_test_evidence:
                tested_line = "已记录可追溯的实际试用信息，但发布前仍需人工复核。"
            elif item.get("tested"):
                tested_line = "标记为已测试，但未提供可追溯的实测记录；正文仅按公开资料整理。"
            else:
                tested_line = "未做亲身体验，以下为公开资料核验和可试用路径整理。"
            lines += [
                "",
                "---",
                "",
                f"## {index:02d}｜{item.get('name', 'AI 新发现')}",
                "",
                f"![{item.get('name', 'AI 新发现')}](images/AI发现-{index:02d}.png)",
                "",
                f"**类型**　{item.get('type', 'AI 应用')}",
                "",
                f"**能做什么**　{item.get('use_case', '用途待确认')}",
                "",
                f"**适合谁**　{'、'.join(item.get('audience') or ['AI 工具观察者'])}",
                "",
                f"**怎么开始**　{item.get('requirements', '以官方说明为准')}；费用/限制：{item.get('pricing', '待核验')}",
                "",
                f"**值得留意**　{item.get('recommendation', '用途明确，但仍需人工复核推荐价值。')}",
                "",
                f"**限制提醒**　{risks}",
                "",
                f"**资料边界**　{tested_line}",
                "",
                f"**官方地址**　[{source.get('name', '官方来源')}]({source.get('url') or item.get('official_url', '')})",
            ]
        lines += [
            "",
            "---",
            "",
            "## 最后留一个坐标",
            "",
            "AI 新东西很多，真正值得留下来的，通常不是“又会了一个炫技动作”，而是能不能在具体场景里少绕一点路。发布前请继续打开官方链接，确认费用、隐私和可用性。",
            "",
            "![结尾图](images/结尾图.png)",
        ]
        summary = editorial.get("summary") or f"整理 {len(items)} 个近期 AI 模型、产品或应用，说明用途、适合人群、费用门槛和风险。"
        return "\n".join(lines), title, summary
    if payload["content_type"] == "daily-news":
        if int(payload.get("schema_version", 1)) == 2:
            return build_daily_news_v2_article(payload)
        editorial=payload.get("editorial") or {}
        start=datetime.fromisoformat(payload["window"]["start"]); end=datetime.fromisoformat(payload["window"]["end"])
        date_label=f"{start.month}月{start.day}日"
        title = resolve_article_title(editorial,date_label,len(items))
        overview=normalize_overview(editorial.get("overview"),[item.get("summary") or item.get("title","") for item in items])
        window_text=f"北京时间 {start.year}年{start.month}月{start.day}日{start:%H:%M}—{end.month}月{end.day}日{end:%H:%M}"
        lines = [f"# {title}", "", "<!-- role:time-window -->", f"> 统计时段：{window_text}。", "", "## 30秒速览", ""]
        lines += [f"- {text}" for text in overview]
        lines += ["", "![国内新闻一日脉络](images/新闻一日脉络.png)"]
        numerals="一二三四五六七八九十"
        for index, item in enumerate(items, 1):
            keywords="｜".join(item.get("keywords") or [item.get("category","新闻")])
            lines += ["", "---", "", f"## {numerals[index-1] if index<=len(numerals) else index}、{item.get('title','')}", "", "<!-- role:keywords -->", f"> **关键词：{keywords}**"]
            sections = (
                ("发生了什么", item.get("what_happened") or item.get("summary")),
                ("为什么重要", item.get("why_it_matters")),
                ("普通人需要注意什么", item.get("reader_action")),
            )
            for section_label, section_text in sections:
                if section_text:
                    lines += ["", "<!-- role:section-label -->", f"**{section_label}**", "", section_text]
            reader_tip=item.get("reader_tip")
            if publishable_reader_tip(reader_tip):
                lines += ["", "<!-- role:reader-tip -->", f"> **读者提示：** {reader_tip.strip()}"]
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


OPERATOR_TIP_MARKERS=("发布前","待核验","补原文","运营者","编辑核对","复核数字")


def publishable_reader_tip(value):
    return (
        isinstance(value,str)
        and bool(value.strip())
        and not any(marker in value for marker in OPERATOR_TIP_MARKERS)
    )


def build_editor_review_panel(payload: dict, copy_state: dict) -> str:
    if payload.get("content_type") == "ai-discovery":
        rows = []
        for item in payload.get("items") or []:
            sources = item.get("official_sources") or []
            rows.append(
                '<section style="margin:10px 0;padding:12px;border-top:1px solid #E2E8F0">'
                f'<strong>{html.escape(item.get("name") or "未命名 AI 条目")}</strong>'
                f'<p>核验状态：{html.escape(str(item.get("verification_status") or "unverified"))}；'
                f'实际体验：{html.escape("是" if item.get("tested") else "否")}</p>'
                f'<p>费用/限制：{html.escape(str(item.get("pricing") or "待核验"))}</p>'
                f'<p>使用门槛：{html.escape(str(item.get("requirements") or "待核验"))}</p>'
                f'<p>风险：{html.escape("；".join(map(str, item.get("risks") or [])) or "无记录")}</p>'
                f'<p>官方来源：{html.escape("；".join(str(source.get("url") or "") for source in sources) or str(item.get("official_url") or ""))}</p>'
                '</section>'
            )
        counts = copy_state["review_counts"]
        return (
            '<aside data-role="editor-review-panel" style="max-width:740px;margin:18px auto;'
            'padding:16px;background:#FFF7D6;color:#5F4B12;border-radius:10px;box-sizing:border-box">'
            '<strong>AI 新发现审核台（不会复制到公众号正文）</strong>'
            f'<p>已核验 {counts["verified"]} 条，部分核验 {counts["partial"]} 条，未核验 {counts["unverified"]} 条。</p>'
            '<p>发布前请人工打开官方链接，确认费用、隐私、安全、版权和可用地区。</p>'
            f'{"".join(rows)}</aside>'
        )
    if payload.get("content_type") == "github-hot" and int(payload.get("schema_version", 1)) == 2:
        selection = payload.get("selection") or {}
        project_rows = []
        for item in payload.get("items") or []:
            verification = item.get("verification") or {}
            maintenance = verification.get("maintenance") or {}
            license_info = verification.get("license") or {}
            metrics = (item.get("reader_card") or {}).get("metrics") or {}
            risks = verification.get("risks") or []
            evidence = verification.get("evidence") or []
            image_info = item.get("_project_image") or {}
            project_rows.append(
                '<section style="margin:10px 0;padding:12px;border-top:1px solid #E2E8F0">'
                f'<strong>{html.escape(item.get("repo") or "未命名项目")}</strong>'
                f'<p>README：{html.escape(str((verification.get("readme") or {}).get("url") or "未核验"))}</p>'
                f'<p>许可证核验：{html.escape(str(license_info.get("status") or "unknown"))}'
                f' {html.escape(str(license_info.get("name") or ""))}</p>'
                f'<p>最近提交：{html.escape(str(maintenance.get("last_commit_at") or "未核验"))}；'
                f'最近发布：{html.escape(str(maintenance.get("latest_release_at") or "未核验"))}；'
                f'维护状态：{html.escape(str(maintenance.get("status") or "unknown"))}</p>'
                f'<p>指标核验时间：{html.escape(str(metrics.get("verified_at") or "未核验"))}</p>'
                f'<p>风险：{html.escape("；".join(str(r.get("summary") or "") for r in risks) or "无记录")}</p>'
                f'<p>证据：{html.escape("；".join(map(str, evidence)) or "无记录")}</p>'
                f'<p>图片审核：image_mode={html.escape(str(image_info.get("image_mode") or "local_project_card"))}；'
                f'license_status={html.escape(str(image_info.get("license_status") or "unknown"))}；'
                f'usage_status={html.escape(str(image_info.get("usage_status") or "not_applicable"))}</p>'
                '</section>'
            )
        rejected = [
            f'{entry.get("repo", "未命名")}：{"；".join(entry.get("rejection_reasons") or ["未记录"])}'
            for entry in payload.get("candidates") or []
            if not entry.get("selected", False)
        ]
        theme = payload.get("editorial") or {}
        theme_evidence = "；".join(
            f'{row.get("repo", "未命名")}：{row.get("hot_reason", "未记录")}'
            for row in theme.get("theme_evidence") or []
        ) or "本期采用多路线结构，无强制共同主题"
        return (
            '<aside data-role="editor-review-panel" style="max-width:740px;margin:18px auto;'
            'padding:16px;background:#FFF7D6;color:#5F4B12;border-radius:10px;box-sizing:border-box">'
            '<strong>GitHub 热门审核台（不会复制到公众号正文）</strong>'
            f'<p>候选 {selection.get("candidate_count", 0)} 个；深度核验 '
            f'{selection.get("deep_verified_count", 0)} 个；入选 {selection.get("selected_count", len(project_rows))} 个。</p>'
            f'<p><strong>本期主题证据：</strong>{html.escape(theme_evidence)}</p>'
            f'{"".join(project_rows)}'
            f'<p><strong>未入选项目：</strong>{html.escape("；".join(rejected) or "无记录")}</p>'
            '</aside>'
        )
    if payload.get("content_type") != "daily-news":
        return ""
    rows=[]
    for item in payload.get("items") or []:
        status=str(item.get("verification_status") or "unverified")
        note=str(item.get("editor_note") or "").strip()
        reader_tip=str(item.get("reader_tip") or "").strip()
        rejected_tip=reader_tip if reader_tip and not publishable_reader_tip(reader_tip) else ""
        if status=="verified" and not note and not rejected_tip:
            continue
        note_html=f'<p style="margin:6px 0 0">{html.escape(note)}</p>' if note else ""
        tip_html=f'<p style="margin:6px 0 0">未进入正文的审核提示：{html.escape(rejected_tip)}</p>' if rejected_tip else ""
        rows.append(
            f'<section style="margin:10px 0;padding:12px;border-top:1px solid #E2E8F0">'
            f'<strong>{html.escape(item.get("title") or "未命名新闻")}</strong>'
            f'<p style="margin:6px 0 0">状态：{html.escape(status)}</p>'
            f'{note_html}{tip_html}</section>'
        )
    if not rows:
        return ""
    counts=copy_state["review_counts"]
    return (
        '<aside data-role="editor-review-panel" style="max-width:740px;margin:18px auto;'
        'padding:16px;background:#FFF7D6;color:#5F4B12;border-radius:10px;box-sizing:border-box">'
        f'<strong>发布审核：{counts["unverified"]} 条未核验，{counts["partial"]} 条部分核验</strong>'
        '<p style="margin:8px 0">以下内容仅供运营者审核，不会被复制到公众号正文。</p>'
        f'{"".join(rows)}</aside>'
    )


def build_html(markdown: str, image_dir: Path, payload: dict, theme: str, visual: dict | None = None, copy_state: dict | None = None):
    bg, ink, primary, accent = tuple(visual["palette"]) if visual else PALETTES[theme]
    label = {"daily-news": "昨日坐标", "ai-discovery": "AI 坐标"}.get(payload["content_type"], "开源坐标")
    title=next((line[2:].strip() for line in markdown.splitlines() if line.startswith("# ")),"微信公众号审核包")
    blocks = []
    pending_role = None
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line: continue
        github_marker = re.fullmatch(
            r"<!-- github-(?:opening|project|closing):(?:start|end) -->",
            line,
        )
        if github_marker:
            continue
        github_metrics = re.fullmatch(r"<!-- github-metrics:(.+) -->", line)
        if github_metrics:
            badges = "".join(
                f'<span style="display:inline-block;margin:0 8px 8px 0;padding:5px 10px;'
                f'border:1px solid {primary}2E;border-radius:999px;background:{bg};'
                f'color:{ink};font-size:13px;line-height:1.5">{html.escape(metric.strip())}</span>'
                for metric in github_metrics.group(1).split("|")
                if metric.strip()
            )
            blocks.append(
                f'<section data-role="github-metrics" style="margin:12px 0 18px;'
                f'font-size:0">{badges}</section>'
            )
            continue
        github_tags = re.fullmatch(r"<!-- github-tags:(.+) -->", line)
        if github_tags:
            tags = "".join(
                f'<span style="display:inline-block;margin:0 8px 8px 0;padding:4px 10px;'
                f'border:1px solid {primary}33;border-radius:999px;background:{bg};'
                f'color:{primary};font-size:13px;line-height:1.45;font-weight:700">{html.escape(tag.strip())}</span>'
                for tag in github_tags.group(1).split("|")
                if tag.strip()
            )
            blocks.append(
                f'<section data-role="github-tags" style="margin:2px 0 16px;'
                f'font-size:0">{tags}</section>'
            )
            continue
        github_highlight_row = re.fullmatch(r"<!-- github-highlight-row:(.+) -->", line)
        if github_highlight_row:
            chips = "".join(
                f'<span data-role="github-highlight-chip" style="display:inline-block;vertical-align:top;'
                f'margin:0 8px 8px 0;padding:8px 14px;min-width:112px;text-align:center;'
                f'border-radius:8px;background:{bg};color:{primary};font-size:14px;line-height:1.55;'
                f'font-weight:700;box-sizing:border-box;overflow-wrap:anywhere">{inline(chip.strip(),primary)}</span>'
                for chip in github_highlight_row.group(1).split("|")
                if chip.strip()
            )
            blocks.append(
                f'<section data-role="github-highlight-row" style="margin:8px 0 14px;font-size:0">'
                f'{chips}</section>'
            )
            continue
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
        if line.startswith("## "):
            project_role = ' data-role="github-project-name"' if payload.get("content_type") == "github-hot" and " · " in line else ""
            blocks.append(f'<section style="margin:30px 0 16px"><div style="width:36px;height:4px;margin-bottom:10px;border-radius:2px;background:{primary}"></div><h2{project_role} style="font-size:22px;line-height:1.5;color:{ink};margin:0;font-weight:800">{inline(line[3:],primary)}</h2></section>'); continue
        if line.startswith("### "): blocks.append(f'<h3 data-role="github-project-name" style="margin:6px 0 12px;color:{ink};font-size:25px;line-height:1.35;font-weight:850;letter-spacing:-.02em">{inline(line[4:],primary)}</h3>'); continue
        if line.startswith("> "):
            content=inline(line[2:],primary)
            if payload.get("content_type") == "github-hot" and line[2:].startswith("**一句话推荐**"):
                blocks.append(f'<blockquote data-role="github-recommendation" style="margin:18px 0 18px;padding:15px 18px;border:0;border-left:4px solid {primary};background:{bg};border-radius:8px;color:{primary};font-size:15px;line-height:1.85;box-sizing:border-box">{content}</blockquote>')
            elif pending_role == "time-window": blocks.append(f'<blockquote data-role="time-window" style="margin:18px 0;padding:14px 16px;border:1px solid {primary}2E;border-left:4px solid {primary};background:{bg};border-radius:10px;box-shadow:0 4px 12px {primary}12;color:{ink};font-size:15px;line-height:1.8">{content}</blockquote>')
            elif pending_role == "keywords": blocks.append(f'<p data-role="keywords" style="margin:10px 0 20px;padding:12px 15px;border-left:4px solid {primary};border-radius:8px;background:{bg};color:{ink};font-size:14px;line-height:1.8;overflow-wrap:anywhere">{content}</p>')
            elif pending_role == "reader-tip": blocks.append(f'<blockquote data-role="reader-tip" style="margin:18px 0;padding:14px 16px;background:{bg};border:1px solid {primary}26;border-left:4px solid {accent};border-radius:10px;box-shadow:0 4px 12px {primary}0D;color:{ink};font-size:15px;line-height:1.8">{content}</blockquote>')
            else: blocks.append(f'<blockquote style="margin:20px 0;padding:16px 18px;background:{bg};border:0;border-radius:8px;color:{primary};font-size:15px;line-height:1.8">{content}</blockquote>')
            pending_role=None; continue
        if line.startswith("原文地址："):
            blocks.append(f'<p data-role="source-url" style="font-size:14px;line-height:1.75;color:#536875;margin:2px 0 14px;text-align:left;word-break:break-all;overflow-wrap:anywhere">{inline(line,primary)}</p>'); continue
        if line.startswith("- "): blocks.append(f'<p style="font-size:16px;line-height:1.75;color:#334E68;margin:6px 0 6px 18px;text-indent:-18px">•　{inline(line[2:],primary)}</p>'); continue
        if re.match(r"^\d+\. ",line): blocks.append(f'<p style="font-size:14px;line-height:1.8;color:#536875;margin:8px 0;overflow-wrap:anywhere">{inline(line,primary)}</p>'); continue
        if line.startswith("**"):
            if payload.get("content_type") == "github-hot" and line.startswith("**适合谁？**"):
                audience_text = re.sub(r"^\*\*适合谁？\*\*\s*", "", line).strip("　 ")
                audience_line = " · ".join(
                    person.strip()
                    for person in re.split(r"[、,，]+", audience_text)
                    if person.strip()
                )
                blocks.append(
                    f'<section data-role="github-audience" style="margin:18px 0 10px">'
                    f'<p data-role="github-section-title" style="margin:0 0 8px;color:{ink};font-size:18px;line-height:1.6;font-weight:850;overflow-wrap:anywhere">适合谁？</p>'
                    f'<p style="margin:0;color:#465C63;font-size:15px;line-height:1.85;overflow-wrap:anywhere">{html.escape(audience_line)}</p>'
                    f'</section>'
                )
            elif payload.get("content_type") == "github-hot" and line.startswith("**项目地址：**"):
                link_match = re.search(r"\[([^]]+)\]\((https?://[^)]+)\)", line)
                url = link_match.group(2) if link_match else re.sub(r"^\*\*项目地址：\*\*\s*", "", line).strip()
                blocks.append(
                    f'<p data-role="github-project-link" style="margin:8px 0 20px;color:#31474F;'
                    f'font-size:15px;line-height:1.8;overflow-wrap:anywhere"><strong>项目地址</strong>：'
                    f'<a href="{html.escape(url)}" style="color:{primary};text-decoration:none;'
                    f'word-break:break-all;overflow-wrap:anywhere">{html.escape(url)}</a></p>'
                )
            elif payload.get("content_type") == "github-hot" and line in {"**它是什么**", "**为什么值得看**"}:
                label = line.strip("*")
                blocks.append(f'<p data-role="github-section-title" style="margin:22px 0 8px;color:{ink};font-size:18px;line-height:1.6;font-weight:850;overflow-wrap:anywhere">{html.escape(label)}</p>')
                pending_role = "github-description-card" if label == "它是什么" else None
            elif pending_role == "section-label": blocks.append(f'<p data-role="section-label" style="margin:18px 0 6px;color:{ink};font-size:17px;line-height:1.7;font-weight:800;overflow-wrap:anywhere">{inline(line,primary)}</p>')
            else: blocks.append(f'<p style="font-size:15px;line-height:1.85;color:#465C63;margin:7px 0;padding:8px 12px;background:{bg};border-radius:6px;overflow-wrap:anywhere">{inline(line,primary)}</p>')
            if pending_role != "github-description-card":
                pending_role=None
            continue
        if pending_role == "github-description-card":
            blocks.append(f'<p data-role="github-description-card" style="font-size:15px;line-height:1.9;color:#31474F;margin:8px 0 18px;padding:14px 18px;background:{bg};border-radius:8px;text-align:justify;overflow-wrap:anywhere">{inline(line,primary)}</p>')
            pending_role=None
            continue
        blocks.append(f'<p style="font-size:16px;line-height:1.95;color:#31474F;margin:12px 0;text-align:justify;overflow-wrap:anywhere">{inline(line,primary)}</p>')
    legacy_allowed=payload["status"]=="ready_for_human_review"
    copy_state=copy_state or {"allowed":legacy_allowed,"reason":"legacy","publish_ready":legacy_allowed,"review_counts":{"verified":0,"partial":0,"unverified":0}}
    ready_to_copy = bool(copy_state["allowed"])
    if ready_to_copy:
        button_attributes = 'style="padding:12px 24px;border:0;border-radius:7px;background:#fff;color:#2563EB;font-size:17px;font-weight:700;cursor:pointer" onclick="copyWechat()"'
        button_label = "复制正文，可发布" if copy_state["publish_ready"] else "复制正文（发布前需核验）"
        notice = "" if copy_state["publish_ready"] else '<div data-role="review-notice" style="max-width:740px;margin:18px auto;padding:12px;background:#FFF2CC;color:#6B5415;box-sizing:border-box">正文可以复制排版，但仍有内容未完成核验，请勿直接发布。</div>'
    else:
        button_attributes = 'disabled aria-disabled="true" style="padding:12px 24px;border:0;border-radius:7px;background:#CBD5E1;color:#64748B;font-size:17px;font-weight:700;cursor:not-allowed"'
        button_label = "正文待补全，暂不可复制"
        notice = f'<div data-role="review-notice" style="max-width:740px;margin:18px auto;padding:12px;background:#FFF2CC;color:#6B5415;box-sizing:border-box">{html.escape(copy_state.get("reason") or "正文尚未达到复制条件")}，请先补全正文。</div>'
    review_panel=build_editor_review_panel(payload,copy_state)
    cover=data_uri(image_dir/"横版封面.png")
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}｜微信排版预览</title></head><body style="margin:0;background:#EFF6FF;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif"><div style="position:sticky;top:0;background:#102A43;padding:15px;text-align:center;z-index:9"><button id="copy-wechat" {button_attributes}>{button_label}</button><span id="copy-status" style="color:#DBEAFE;margin-left:14px">复制后粘贴到微信公众号编辑器</span></div>{notice}{review_panel}<main style="max-width:760px;margin:24px auto;padding:0 16px 40px;box-sizing:border-box"><section id="cover-preview" style="margin-bottom:18px;padding:18px;background:#fff;border-radius:12px;box-shadow:0 4px 18px rgba(30,64,175,.08)"><img src="{cover}" alt="横版封面" style="display:block;width:100%;height:auto;border-radius:8px"><h1 style="margin:20px 0 8px;color:#102A43;font-size:27px;line-height:1.4">{html.escape(title)}</h1><p style="margin:0;color:#64748B;font-size:14px">封面和标题不包含在复制区域，请在公众号后台分别填写。</p></section><article id="wechat-content" style="padding:28px 24px;border-radius:12px;background:#fff;box-shadow:0 4px 18px rgba(30,64,175,.08)">{''.join(blocks)}</article></main><script>async function copyWechat(){{const node=document.getElementById('wechat-content');try{{const htmlBlob=new Blob([node.innerHTML],{{type:'text/html'}});const textBlob=new Blob([node.innerText],{{type:'text/plain'}});await navigator.clipboard.write([new ClipboardItem({{'text/html':htmlBlob,'text/plain':textBlob}})]);document.getElementById('copy-status').textContent='复制成功，请到公众号编辑器粘贴';}}catch(error){{const range=document.createRange();range.selectNodeContents(node);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);document.execCommand('copy');selection.removeAllRanges();document.getElementById('copy-status').textContent='已复制，请粘贴后检查图片';}}}}</script></body></html>'''
