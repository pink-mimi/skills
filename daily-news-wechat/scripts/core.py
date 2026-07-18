from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

BJT = timezone(timedelta(hours=8))

CATEGORY_KEYWORDS = {
    "public-safety": ("暴雨", "洪水", "地震", "台风", "救援", "事故", "应急", "预警", "灾害"),
    "finance": ("经济", "金融", "股市", "A股", "消费", "财政", "人民币", "银行", "证券"),
    "tech": ("科技", "人工智能", "机器人", "芯片", "航天", "卫星", "软件"),
    "politics": ("国务院", "政策", "条例", "办法", "外交", "会议"),
    "society": ("教育", "医疗", "交通", "就业", "养老", "民生", "社会"),
}


@dataclass
class NewsItem:
    title: str
    source: str
    url: str
    category: str
    summary: str = ""
    published_at: str | None = None
    fetched_at: str | None = None
    source_tier: int = 4
    time_confidence: str = "missing"
    score: float = 0.0


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_time(value: object, reference: datetime) -> tuple[datetime | None, str]:
    if value in (None, ""):
        return None, "missing"
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit() and len(value) >= 10):
        stamp = int(value)
        if stamp > 10_000_000_000:
            stamp //= 1000
        return datetime.fromtimestamp(stamp, BJT), "exact"
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=BJT)
        return parsed.astimezone(BJT), "exact"
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=BJT), "assumed_bjt"
        except ValueError:
            continue
    match = re.fullmatch(r"(\d{2})-(\d{2})\s+(\d{2}):(\d{2})", text)
    if match:
        month, day, hour, minute = map(int, match.groups())
        year = reference.astimezone(BJT).year
        result = datetime(year, month, day, hour, minute, tzinfo=BJT)
        if result - reference.astimezone(BJT) > timedelta(days=180):
            result = result.replace(year=year - 1)
        return result, "assumed_bjt"
    return None, "unparseable"


def window_for(run_at: datetime, config: dict) -> tuple[datetime, datetime]:
    hour, minute = map(int, config["window"]["end_time"].split(":"))
    end = run_at.astimezone(BJT).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return end - timedelta(hours=int(config["window"]["duration_hours"])), end


def source_tier(source: str, config: dict) -> int:
    for tier, names in config["source_tiers"].items():
        if any(name in source for name in names):
            return int(tier)
    return 4


def infer_category(title: str, summary: str, supplied: str) -> str:
    for category, words in CATEGORY_KEYWORDS.items():
        if any(word in title for word in words):
            return category
    return supplied or "general"


def normalize(raw: dict, fetched_at: datetime, config: dict) -> NewsItem:
    published, confidence = parse_time(
        raw.get("published_at") or raw.get("pubDate") or raw.get("ctime") or raw.get("time"), fetched_at
    )
    source = str(raw.get("source") or "未知来源").strip()
    title = re.sub(r"\s+", " ", str(raw.get("title") or "")).strip()
    summary = re.sub(r"\s+", " ", str(raw.get("summary") or "")).strip()
    return NewsItem(
        title=title,
        source=source,
        url=str(raw.get("url") or raw.get("link") or "").strip(),
        category=infer_category(title, summary, str(raw.get("category") or "general")),
        summary=summary,
        published_at=published.isoformat() if published else None,
        fetched_at=fetched_at.astimezone(BJT).isoformat(),
        source_tier=source_tier(source, config),
        time_confidence=confidence,
    )


def _title_key(title: str) -> str:
    return re.sub(r"[\W_]|最新|消息|现场|视频|权威发布", "", title).lower()


def duplicate(left: NewsItem, right: NewsItem) -> bool:
    a, b = _title_key(left.title), _title_key(right.title)
    if not a or not b:
        return False
    return (min(len(a), len(b)) >= 12 and (a in b or b in a)) or SequenceMatcher(None, a, b).ratio() >= 0.72


def deduplicate(items: Iterable[NewsItem]) -> list[NewsItem]:
    groups: list[list[NewsItem]] = []
    for item in items:
        group = next((candidate for candidate in groups if duplicate(candidate[0], item)), None)
        if group is None:
            groups.append([item])
        else:
            group.append(item)
    result = []
    for group in groups:
        group.sort(key=lambda row: (row.source_tier, -len(row.summary)))
        result.append(group[0])
    return result


def score(item: NewsItem) -> float:
    text = f"{item.title} {item.summary}"
    reliability = {1: 30, 2: 24, 3: 16, 4: 4}[item.source_tier]
    impact = min(24, 6 * sum(word in text for word in ("全国", "重大", "启动", "发布", "实施", "预警", "救援", "突破")))
    relevance = min(20, 5 * sum(word in text for word in ("安全", "出行", "消费", "就业", "教育", "医疗", "住房", "养老")))
    return float(reliability + impact + relevance + (12 if item.summary else 4) + (8 if item.category != "general" else 2))


def partition(items: Iterable[NewsItem], run_at: datetime, config: dict) -> tuple[list[NewsItem], list[NewsItem]]:
    start, end = window_for(run_at, config)
    eligible, review = [], []
    for item in items:
        if not item.title or not item.url or not item.published_at:
            review.append(item)
            continue
        published = datetime.fromisoformat(item.published_at).astimezone(BJT)
        if start <= published < end:
            item.score = score(item)
            eligible.append(item)
    return eligible, review


def select_diverse(items: Iterable[NewsItem], config: dict) -> list[NewsItem]:
    limits = config["selection"]
    minimum, maximum = int(limits["minimum"]), int(limits["maximum"])
    per_category = int(limits["maximum_per_category"])
    minimum_score = float(limits.get("minimum_score", 0))
    official_categories = set(limits.get("official_source_required", []))
    ranked = sorted(
        (row for row in items if row.score >= minimum_score and not (row.category in official_categories and row.source_tier > 1)),
        key=lambda row: row.score,
        reverse=True,
    )
    selected: list[NewsItem] = []
    counts: dict[str, int] = {}
    for item in ranked:
        if counts.get(item.category, 0) >= per_category:
            continue
        selected.append(item)
        counts[item.category] = counts.get(item.category, 0) + 1
        if len(selected) == maximum:
            break
    if len(selected) < minimum:
        for item in ranked:
            if item not in selected:
                selected.append(item)
                if len(selected) == minimum:
                    break
    return selected[:maximum]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def item_dicts(items: Iterable[NewsItem]) -> list[dict]:
    return [asdict(item) for item in items]
