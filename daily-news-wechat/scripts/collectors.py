from __future__ import annotations

import email.utils
import html
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

from core import BJT

UA = "daily-news-wechat/1.0 (+https://github.com/pink-mimi/skills)"


def _clean(value: str | None) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", "", value or ""))
    return re.sub(r"\s+", " ", value).strip()


def _child_text(element: ET.Element, names: tuple[str, ...]) -> str:
    for name in names:
        child = element.find(name)
        if child is not None and child.text:
            return child.text.strip()
    return ""


def _date(value: str) -> str | None:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=BJT)
        return parsed.astimezone(BJT).isoformat()
    except (TypeError, ValueError):
        return value


def parse_feed(payload: bytes, source: dict) -> list[dict]:
    root = ET.fromstring(payload)
    rows = []
    for item in root.iter("item"):
        title = _clean(_child_text(item, ("title",)))
        link = _child_text(item, ("link",))
        if title and link:
            rows.append({
                "title": title,
                "link": link,
                "source": source["name"],
                "category": source["category"],
                "published_at": _date(_child_text(item, ("pubDate", "date"))),
                "summary": _clean(_child_text(item, ("description", "summary"))),
                "region": source.get("region", "china"),
            })
    if rows:
        return rows
    atom = "{http://www.w3.org/2005/Atom}"
    for entry in root.iter(f"{atom}entry"):
        title = _clean(_child_text(entry, (f"{atom}title",)))
        link_node = entry.find(f"{atom}link")
        link = link_node.get("href", "") if link_node is not None else ""
        if title and link:
            rows.append({
                "title": title,
                "link": urljoin(source["url"], link),
                "source": source["name"],
                "category": source["category"],
                "published_at": _date(_child_text(entry, (f"{atom}published", f"{atom}updated"))),
                "summary": _clean(_child_text(entry, (f"{atom}summary", f"{atom}content"))),
                "region": source.get("region", "international"),
            })
    return rows


def collect(config: dict, timeout: int = 15) -> tuple[list[dict], list[dict]]:
    enabled_regions = set(config["regions"])
    rows, errors = [], []
    for source in config["sources"]:
        if not source.get("enabled", True) or source.get("region", "china") not in enabled_regions:
            continue
        try:
            request = urllib.request.Request(source["url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                rows.extend(parse_feed(response.read(), source))
        except Exception as exc:
            errors.append({"source": source["name"], "url": source["url"], "error": f"{type(exc).__name__}: {exc}"})
    return rows, errors


def collect_custom(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("items", payload) if isinstance(payload, dict) else payload
