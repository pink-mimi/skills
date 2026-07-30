from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus
import urllib.request


BJT = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ITEM_FIELDS = (
    "name",
    "type",
    "official_url",
    "discovered_at",
    "official_sources",
    "use_case",
    "audience",
    "pricing",
    "requirements",
    "risks",
    "verification_status",
    "recommendation",
)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if clean_text(item)]
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[;；\n]+", value) if item.strip()]
    return [value]


def window(run_at, config):
    end = run_at.astimezone(BJT)
    return end - timedelta(days=int(config["window"]["duration_days"])), end


def collect(run_at):
    query = quote_plus("AI model product launch official blog OR paper OR Hugging Face")
    request = urllib.request.Request(
        f"https://www.bing.com/search?q={query}",
        headers={"User-Agent": "ai-discovery-research/1.0"},
    )
    try:
        page = urllib.request.urlopen(request, timeout=20).read().decode("utf-8", "replace")
    except Exception as exc:
        return {"meta": {"rate_limited": True, "error": str(exc), "fetched_at": run_at.isoformat()}, "items": []}
    titles = re.findall(r"<h2[^>]*>.*?<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>.*?</h2>", page, flags=re.S | re.I)
    items = []
    for index, (url, title_html) in enumerate(titles[:10], 1):
        title = re.sub(r"<[^>]+>", " ", title_html)
        items.append(
            {
                "name": clean_text(title)[:80] or f"AI 线索 {index}",
                "type": "application",
                "official_url": clean_text(url),
                "discovered_at": run_at.isoformat(),
                "official_sources": [{"name": "搜索结果", "url": clean_text(url), "verified_at": ""}],
                "use_case": "搜索发现的 AI 相关线索，需要回到官方来源继续核验。",
                "audience": ["AI 工具观察者"],
                "pricing": "待核验",
                "requirements": "待核验",
                "risks": ["来源和事实仍需人工核验"],
                "verification_status": "unverified",
                "recommendation": "作为候选线索保留，不直接推荐发布。",
            }
        )
    return {"meta": {"rate_limited": False, "fetched_at": run_at.isoformat(), "source": "web_search"}, "items": items}


def normalize_candidate(value, rank):
    row = deepcopy(value)
    row["rank"] = int(row.get("rank") or rank)
    row["name"] = clean_text(row.get("name") or row.get("title") or f"AI 新发现 {rank}")
    row["type"] = clean_text(row.get("type") or "application")
    row["official_url"] = clean_text(row.get("official_url") or row.get("url"))
    row["discovered_at"] = clean_text(row.get("discovered_at") or row.get("published_at"))
    row["official_sources"] = as_list(row.get("official_sources") or row.get("sources"))
    normalized_sources = []
    for source in row["official_sources"]:
        if isinstance(source, dict):
            normalized_sources.append(
                {
                    "name": clean_text(source.get("name") or "官方来源"),
                    "url": clean_text(source.get("url")),
                    "verified_at": clean_text(source.get("verified_at") or row.get("verified_at")),
                }
            )
        else:
            normalized_sources.append({"name": "官方来源", "url": clean_text(source), "verified_at": clean_text(row.get("verified_at"))})
    row["official_sources"] = normalized_sources
    row["use_case"] = clean_text(row.get("use_case") or row.get("summary"))
    row["audience"] = as_list(row.get("audience"))
    row["pricing"] = clean_text(row.get("pricing") or row.get("cost") or "待核验")
    row["requirements"] = clean_text(row.get("requirements") or row.get("access") or "待核验")
    row["risks"] = as_list(row.get("risks"))
    row["verification_status"] = clean_text(row.get("verification_status") or "unverified")
    row["recommendation"] = clean_text(row.get("recommendation") or row.get("why_selected"))
    row["tested"] = bool(row.get("tested", False))
    row["evidence"] = as_list(row.get("evidence"))
    row["rejection_reasons"] = rejection_reasons(row)
    row["eligible"] = not row["rejection_reasons"]
    row["selected"] = False
    return row


def rejection_reasons(row):
    reasons = []
    for field in REQUIRED_ITEM_FIELDS:
        if field == "official_sources":
            if not row.get(field):
                reasons.append("缺少官方来源")
        elif field in {"audience", "risks"}:
            if not row.get(field):
                reasons.append(f"缺少 {field}")
        elif not clean_text(row.get(field)):
            reasons.append(f"缺少 {field}")
    if not any(clean_text(source.get("url")) for source in row.get("official_sources") or []):
        reasons.append("官方来源缺少链接")
    if row.get("verification_status") in {"verified", "partial"} and not any(
        clean_text(source.get("verified_at")) for source in row.get("official_sources") or []
    ):
        reasons.append("官方来源缺少核验时间")
    if row.get("verification_status") not in {"verified", "partial"}:
        reasons.append("尚未完成官方来源核验")
    if "待核验" in f"{row.get('pricing')} {row.get('requirements')}":
        reasons.append("费用或使用门槛待核验")
    if row.get("tested") and not row.get("evidence"):
        reasons.append("实测声明缺少证据记录")
    return list(dict.fromkeys(reasons))


def build(raw, run_at, config):
    start, end = window(run_at, config)
    rows = [normalize_candidate(value, index) for index, value in enumerate(raw.get("items", []), 1)]
    target_count = int(config["selection"]["target"])
    selected = []
    for row in rows:
        if row["eligible"] and len(selected) < target_count:
            row["selected"] = True
            selected.append(row)
        elif not row["rejection_reasons"] and len(selected) >= target_count:
            row["rejection_reasons"].append("超过本期目标数量")
    risks = ["禁止自动发布；发布前人工复核官方来源、费用限制、隐私安全和版权边界"]
    candidate_minimum = int(config["discovery"]["candidate_minimum"])
    verified_minimum = int(config["selection"]["verified_minimum"])
    if raw.get("meta", {}).get("rate_limited"):
        risks.append("发现入口采集失败或受限")
    if len(rows) < candidate_minimum:
        risks.append(f"候选少于 {candidate_minimum} 个")
    if len(selected) < int(config["selection"]["minimum"]):
        risks.append("入选数量不足")
    if sum(row["verification_status"] == "verified" for row in selected) < verified_minimum:
        risks.append(f"完全核验条目少于 {verified_minimum} 个")
    ready = (
        not raw.get("meta", {}).get("rate_limited")
        and len(rows) >= candidate_minimum
        and len(selected) == target_count
        and int(config["selection"]["minimum"]) <= len(selected) <= int(config["selection"]["maximum"])
        and sum(row["verification_status"] == "verified" for row in selected) >= verified_minimum
    )
    return {
        "schema_version": 1,
        "content_type": "ai-discovery",
        "package_id": f"ai-discovery-{run_at.astimezone(BJT):%Y-%m-%d}",
        "run_at": run_at.isoformat(),
        "status": "ready_for_human_review" if ready else "needs_review",
        "window": {"start": start.isoformat(), "end": end.isoformat(), "boundary": "left_closed_right_open"},
        "selection": {
            "candidate_count": len(rows),
            "selected_count": len(selected),
            "verified_count": sum(row["verification_status"] == "verified" for row in selected),
            "minimum": int(config["selection"]["minimum"]),
            "maximum": int(config["selection"]["maximum"]),
            "target": target_count,
        },
        "items": selected,
        "candidates": rows,
        "sources": [{"name": item["name"], "url": item["official_url"]} for item in selected],
        "risks": risks,
        "editorial": {
            "title": f"AI 新发现：{len(selected)} 个值得留意的新坐标",
            "summary": f"整理 {len(selected)} 个近期 AI 模型、产品或应用，重点看用途、门槛和风险。",
            "overview": [item["recommendation"] for item in selected[:5]],
        },
    }


def validate_package(payload):
    errors = []
    if payload.get("schema_version") != 1:
        errors.append("不支持的 schema_version")
    if payload.get("content_type") != "ai-discovery":
        errors.append("content_type 错误")
    for field in ("package_id", "run_at", "status", "window", "selection", "items", "candidates", "sources", "risks"):
        if field not in payload:
            errors.append(f"缺少 {field}")
    for item in payload.get("items", []):
        for field in REQUIRED_ITEM_FIELDS:
            if field not in item:
                errors.append(f"{item.get('name', '未命名')} 缺少 {field}")
    forbidden = json.dumps(payload, ensure_ascii=False)
    for token in ("wechat_html", "微信版.html", "合并封面.png"):
        if token in forbidden:
            errors.append(f"研究层包含平台输出字段 {token}")
    return errors


def target(root, run_at):
    return Path(root) / "ai-discovery" / run_at.astimezone(BJT).date().isoformat()


def archive_revision(out, names):
    existing = [out / name for name in names if (out / name).exists()]
    if not existing:
        return None
    base = out / "revisions"
    number = 1
    while (base / f"revision-{number:02d}").exists():
        number += 1
    revision = base / f"revision-{number:02d}"
    revision.mkdir(parents=True, exist_ok=False)
    for path in existing:
        shutil.copy2(path, revision / path.name)
    return revision


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("collect", "build", "verify", "all"))
    parser.add_argument("--config", type=Path, default=ROOT / "assets/default-config.json")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path.cwd())
    parser.add_argument("--run-at")
    parser.add_argument("--mode", choices=("stable", "refresh", "rebuild"), default="stable")
    args = parser.parse_args()
    config = load(args.config)
    run_at = datetime.fromisoformat(args.run_at).astimezone(BJT) if args.run_at else datetime.now(BJT)
    out = target(args.output_root, run_at)
    raw_path = out / "raw-candidates.json"
    package_path = out / "content-package.json"
    if args.mode == "rebuild" and not raw_path.exists():
        raise SystemExit("rebuild 需要已有原始快照 raw-candidates.json")
    if args.mode == "refresh" and args.command in ("collect", "build", "all"):
        archive_revision(out, ("raw-candidates.json", "content-package.json"))
    if args.command in ("collect", "all") and args.mode != "rebuild" and (
        args.mode == "refresh" or not raw_path.exists()
    ):
        save(raw_path, load(args.input) if args.input else collect(run_at))
    if args.command in ("build", "all"):
        if args.command == "build" and args.mode == "refresh" and args.input:
            save(raw_path, load(args.input))
        if not raw_path.exists() and args.input and args.mode != "rebuild":
            save(raw_path, load(args.input))
        if not raw_path.exists():
            raise SystemExit("缺少原始快照 raw-candidates.json")
        package = build(load(raw_path), run_at, config)
        package["snapshot"] = {
            "mode": args.mode,
            "file": raw_path.name,
            "sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        }
        save(package_path, package)
    if args.command in ("verify", "all"):
        if not package_path.exists():
            raise SystemExit("缺少 content-package.json")
        errors = validate_package(load(package_path))
        if errors:
            raise SystemExit("；".join(errors))
        print("OK")


if __name__ == "__main__":
    main()
