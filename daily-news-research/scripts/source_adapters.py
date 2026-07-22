from __future__ import annotations

import html
import re
from typing import NamedTuple
from urllib.parse import urljoin
from xml.etree import ElementTree as ET


class ParseResult(NamedTuple):
    status: str
    items: list
    error: str


def _clean(value):
    value=re.sub(r"<(script|style)\b[^>]*>[\s\S]*?</\1>","",value or "",flags=re.I)
    value=re.sub(r"<[^>]+>","",value)
    return re.sub(r"\s+"," ",html.unescape(value)).strip()


def _base_item(source,title,url,published_at="",updated_at="",summary=""):
    return {
        "title":_clean(title),
        "url":urljoin(source["url"],html.unescape(url)),
        "source":source["name"],
        "organization":source.get("organization",source["name"]),
        "source_role":source.get("role","discovery"),
        "source_tier":source.get("tier",2),
        "category":source.get("category","general"),
        "summary":_clean(summary),
        "published_at":published_at,
        "updated_at":updated_at,
    }


def _parse_feed(payload,source):
    try:
        root=ET.fromstring(payload)
    except ET.ParseError as exc:
        return ParseResult("parse_error",[],str(exc))
    rows=[]
    for node in root.iter("item"):
        get=lambda name:(node.findtext(name) or "").strip()
        title=get("title"); url=get("link")
        if title and url:
            rows.append(_base_item(source,title,url,get("pubDate") or get("date"),summary=get("description") or get("summary")))
    atom="{http://www.w3.org/2005/Atom}"
    if not rows:
        for node in root.iter(f"{atom}entry"):
            title=node.findtext(f"{atom}title") or ""; link=node.find(f"{atom}link"); url=link.get("href","") if link is not None else ""
            if title and url:
                rows.append(_base_item(source,title,url,node.findtext(f"{atom}published") or "",node.findtext(f"{atom}updated") or "",node.findtext(f"{atom}summary") or node.findtext(f"{atom}content") or ""))
    return ParseResult("success_with_items" if rows else "success_no_items",rows,"")


def _parse_html(payload,source):
    text=payload.decode("utf-8","replace")
    if not re.search(r"<html|<body|<a\b",text,re.I):
        return ParseResult("parse_error",[],"响应不像可解析的 HTML 页面")
    rows=[]; seen=set()
    pattern=re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>(?=([\s\S]{0,1200}))',re.I)
    for url,label,tail in pattern.findall(text):
        title=_clean(label)
        if len(title)<8 or title in seen or url.lower().startswith(("javascript:","mailto:","#")):
            continue
        match=re.search(r"(20\d{2})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})\s*日?(?:\s+(\d{1,2}):?(\d{2})?)?",_clean(tail))
        if not match:
            continue
        year,month,day,hour,minute=match.groups()
        published=f"{year}-{int(month):02d}-{int(day):02d}"
        if hour:
            published+=f"T{int(hour):02d}:{int(minute or 0):02d}:00+08:00"
        seen.add(title)
        rows.append(_base_item(source,title,url,published))
        if len(rows)>=50:
            break
    if rows: return ParseResult("success_with_items",rows,"")
    article_links=sum(1 for _,label,_ in pattern.findall(text) if len(_clean(label))>=8)
    if article_links: return ParseResult("parse_error",[],"发现文章链接，但未提取到可靠发布时间")
    recognized=bool(re.search(r"<ul\b|class=[\"'][^\"']*(?:list|news|content)",text,re.I))
    return ParseResult("success_no_items" if recognized else "parse_error",[],"" if recognized else "页面存在 HTML，但未识别到新闻列表结构")


PARSERS={
    "rss_atom":_parse_feed,
    "gov_policy":_parse_html,
    "stats_release":_parse_html,
    "miit_release":_parse_html,
    "mem_release":_parse_html,
    "cma_warning":_parse_html,
    "media_web":_parse_html,
}


def parse(payload,source):
    parser=PARSERS.get(source.get("parser"))
    if parser is None:
        return ParseResult("parse_error",[],f"未知解析器：{source.get('parser')}")
    try:
        return parser(payload,source)
    except Exception as exc:
        return ParseResult("parse_error",[],f"{type(exc).__name__}: {exc}")
