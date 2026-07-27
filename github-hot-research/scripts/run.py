from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import urllib.request
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path


BJT = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[1]
LICENSE_UNKNOWN = {"", "NOASSERTION", "UNKNOWN", "OTHER", "未发现明确许可证"}
VISUAL_USAGE = {"approved", "review_required", "rejected"}
REQUIRED_AVOID = ("项目Logo", "虚构软件界面", "中文文字", "虚构数据")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def window(run_at, config):
    end = run_at.astimezone(BJT)
    return end - timedelta(days=int(config["window"]["duration_days"])), end


def collect(run_at):
    request = urllib.request.Request(
        "https://github.com/trending?since=weekly",
        headers={"User-Agent": "github-hot-research/2.0"},
    )
    try:
        page = urllib.request.urlopen(request, timeout=20).read().decode("utf-8", "replace")
    except Exception as exc:
        return {"meta": {"rate_limited": True, "error": str(exc)}, "items": []}
    repos = []
    for repo in re.findall(r'<h2[^>]*>[\s\S]*?href="/([^"?#]+/[^"?#]+)"', page):
        name = re.sub(r"\s", "", repo)
        if name not in repos:
            repos.append(name)
    return {
        "meta": {"rate_limited": False, "fetched_at": run_at.isoformat()},
        "items": [{"repo": repo, "official_url": f"https://github.com/{repo}"} for repo in repos[:20]],
    }


def clean_text(value):
    return str(value or "").strip()


def as_list(value):
    if isinstance(value, list):
        return [item for item in value if clean_text(item)]
    if clean_text(value):
        return [clean_text(value)]
    return []


def license_record(row):
    existing = deepcopy((row.get("verification") or {}).get("license") or {})
    raw_name = clean_text(existing.get("name") or row.get("license"))
    status = clean_text(existing.get("status"))
    if not status:
        status = "not_found" if raw_name.upper() in LICENSE_UNKNOWN else "verified"
    if status == "not_found":
        raw_name = ""
    return {
        "status": status,
        "name": raw_name,
        "spdx_id": clean_text(existing.get("spdx_id") or raw_name),
        "url": clean_text(existing.get("url")),
    }


def normalize_reader_card(row):
    existing = deepcopy(row.get("reader_card") or {})
    metrics = deepcopy(existing.get("metrics") or {})
    weekly = metrics.get("weekly_stars", row.get("weekly_stars"))
    if weekly in ("", "unknown", "UNKNOWN"):
        weekly = None
    highlights = as_list(existing.get("highlights") or row.get("highlights"))
    audience = as_list(existing.get("audience") or row.get("audience"))
    difficulty = deepcopy(existing.get("difficulty") or {})
    difficulty.setdefault("level", "medium")
    difficulty.setdefault("label", "中等")
    difficulty.setdefault("note", clean_text(row.get("install")))
    return {
        "category_label": clean_text(existing.get("category_label") or row.get("category")),
        "name": clean_text(existing.get("name") or clean_text(row.get("repo")).split("/")[-1]),
        "summary": clean_text(existing.get("summary") or row.get("description")),
        "recommendation": clean_text(existing.get("recommendation") or "用途明确，官方资料可追溯。"),
        "highlights": highlights,
        "audience": audience,
        "difficulty": difficulty,
        "metrics": {
            "language": clean_text(metrics.get("language") or row.get("language")),
            "stars": metrics.get("stars", row.get("stars")),
            "weekly_stars": weekly,
            "forks": metrics.get("forks", row.get("forks")),
            "verified_at": clean_text(
                metrics["verified_at"] if "verified_at" in metrics else row.get("metrics_verified_at")
            ),
        },
        "reader_warning": clean_text(existing.get("reader_warning")),
    }


def normalize_verification(row, license_info):
    existing = deepcopy(row.get("verification") or {})
    readme = deepcopy(existing.get("readme") or {})
    maintenance = deepcopy(existing.get("maintenance") or {})
    requirements = deepcopy(existing.get("requirements") or {})
    repo = clean_text(row.get("repo"))
    readme.setdefault("url", f"https://github.com/{repo}#readme" if repo else "")
    readme.setdefault("verified_at", clean_text(row.get("readme_verified_at") or row.get("metrics_verified_at")))
    maintenance.setdefault("status", "active" if clean_text(row.get("last_commit")) else "unknown")
    maintenance.setdefault("last_commit_at", clean_text(row.get("last_commit")))
    maintenance.setdefault("latest_release_at", clean_text(row.get("release_at")))
    maintenance.setdefault("evidence_urls", [])
    requirements.setdefault("platforms", as_list(row.get("platform")))
    requirements.setdefault("install", clean_text(row.get("install")))
    requirements.setdefault("command_line", "命令" in clean_text(row.get("install")).lower())
    requirements.setdefault("programming_required", False)
    requirements.setdefault("account_required", False)
    requirements.setdefault("api_key_required", "api key" in clean_text(row.get("risks")).lower())
    requirements.setdefault("paid_dependency", False)
    requirements.setdefault("special_hardware", False)
    risks = existing.get("risks")
    if not isinstance(risks, list):
        risks = []
    if clean_text(row.get("risks")) and not risks:
        risks = [
            {
                "type": "general",
                "severity": "medium",
                "summary": clean_text(row.get("risks")),
                "reader_visible": False,
                "source_url": clean_text(row.get("official_url")),
            }
        ]
    return {
        "readme": readme,
        "license": license_info,
        "maintenance": maintenance,
        "requirements": requirements,
        "risks": risks,
        "evidence": as_list(existing.get("evidence") or row.get("official_url")),
    }


def normalize_visual_candidates(row):
    normalized = []
    for value in row.get("visual_candidates") or []:
        visual = deepcopy(value)
        usage = clean_text(visual.get("usage_status"))
        if usage not in VISUAL_USAGE:
            usage = "review_required"
        license_status = clean_text(visual.get("license_status"))
        if license_status != "verified" and usage == "approved":
            usage = "review_required"
        if clean_text(visual.get("type")) in {"logo", "social_preview"} and usage == "approved":
            usage = "review_required"
        visual["usage_status"] = usage
        visual.setdefault("source_page", "")
        visual.setdefault("verified_at", "")
        visual.setdefault("is_real_interface", visual.get("type") == "official_screenshot")
        visual.setdefault("attribution_required", False)
        normalized.append(visual)
    return normalized


def normalize_image2_brief(row, reader_card):
    existing = deepcopy(row.get("image2_brief") or {})
    verified_features = set(reader_card["highlights"])
    requested = as_list(existing.get("must_include"))
    must_include = [value for value in requested if value in verified_features]
    if not must_include:
        must_include = reader_card["highlights"][:2]
    must_avoid = list(dict.fromkeys(as_list(existing.get("must_avoid")) + list(REQUIRED_AVOID)))
    return {
        "subject": clean_text(existing.get("subject") or reader_card["summary"]),
        "scene": clean_text(existing.get("scene") or "项目用途与工作流程的抽象场景"),
        "must_include": must_include,
        "must_avoid": must_avoid,
    }


def rejection_reasons(row):
    card = row["reader_card"]
    verification = row["verification"]
    reasons = []
    if not clean_text(row.get("repo")) or not clean_text(row.get("official_url")):
        reasons.append("缺少仓库身份或官方地址")
    if not card["summary"] or not card["recommendation"]:
        reasons.append("读者用途或推荐理由不完整")
    if len(card["highlights"]) != 3:
        reasons.append("核心亮点必须恰好 3 条")
    if not card["audience"] or not card["difficulty"].get("label"):
        reasons.append("适合人群或上手难度不完整")
    if not verification["readme"].get("verified_at"):
        reasons.append("README 尚未核验")
    if verification["maintenance"].get("status") not in {"active", "maintained", "stable"}:
        reasons.append("维护状态无法确认")
    if not card["metrics"].get("verified_at"):
        reasons.append("动态指标缺少核验时间")
    return reasons


def normalize_candidate(value):
    row = deepcopy(value)
    row.setdefault("official_url", f"https://github.com/{clean_text(row.get('repo'))}")
    row["reader_card"] = normalize_reader_card(row)
    license_info = license_record(row)
    row["verification"] = normalize_verification(row, license_info)
    row["visual_candidates"] = normalize_visual_candidates(row)
    row["image2_brief"] = normalize_image2_brief(row, row["reader_card"])
    row["rejection_reasons"] = rejection_reasons(row)
    row["deep_verified"] = not row["rejection_reasons"]
    row["eligible"] = row["deep_verified"]
    row["score"] = score(row)
    return row


def score(row):
    metrics = (row.get("reader_card") or {}).get("metrics") or {}
    weekly = metrics.get("weekly_stars", row.get("weekly_stars"))
    stars = metrics.get("stars", row.get("stars"))
    return float(weekly or 0) * 1.5 + min(float(stars or 0), 50000) / 1000 + (
        20 if row.get("latest_release") or (row.get("verification") or {}).get("maintenance", {}).get("latest_release_at") else 0
    )


def history(root, date, limit):
    base = Path(root) / "github-hot"
    result = set()
    if not base.exists():
        return result
    paths = (path for path in base.glob("*/content-package.json") if path.parent.name < date)
    for path in sorted(paths, reverse=True)[:limit]:
        try:
            result.update(clean_text(item.get("repo")) for item in load(path).get("items", []) if item.get("repo"))
        except (OSError, json.JSONDecodeError):
            pass
    return result


def package_risks(raw, rows, selected, candidate_minimum, deep_minimum):
    risks = ["发布前复核 Star、许可证、最近维护状态和图片授权"]
    if raw.get("meta", {}).get("rate_limited"):
        risks.append("GitHub 发现入口采集失败或受限")
    if len(rows) < candidate_minimum:
        risks.append(f"候选少于 {candidate_minimum} 个")
    deep_count = sum(bool(row["deep_verified"]) for row in rows)
    if deep_count < deep_minimum:
        risks.append(f"深度核验少于 {deep_minimum} 个")
    if any(item["verification"]["license"]["status"] == "not_found" for item in selected):
        risks.append("入选项目存在未发现许可证")
    if any(not item["reader_card"]["metrics"].get("verified_at") for item in selected):
        risks.append("入选项目动态指标缺少核验时间")
    return risks


def build(raw, run_at, config, output_root):
    start, end = window(run_at, config)
    rows = [normalize_candidate(value) for value in raw.get("items", [])]
    selection_config = config["selection"]
    minimum = int(selection_config["minimum"])
    maximum = int(selection_config["maximum"])
    target_count = min(maximum, int(selection_config.get("target", minimum)))
    past = history(
        output_root,
        run_at.astimezone(BJT).date().isoformat(),
        int(selection_config["history_lookback_weeks"]),
    )
    selected = []
    ai_count = 0
    categories = {}
    for row in sorted(rows, key=lambda item: item["score"], reverse=True):
        reasons = list(row["rejection_reasons"])
        if row.get("repo") in past and not row.get("significant_change"):
            reasons.append("最近 8 期已经推荐且没有重大更新")
        if row.get("ai_related") and ai_count >= int(selection_config["maximum_ai"]):
            reasons.append("AI 项目数量已达到上限")
        category = clean_text(row.get("category"))
        if categories.get(category, 0) >= int(selection_config["maximum_per_category"]):
            reasons.append("同一类别数量已达到上限")
        row["rejection_reasons"] = list(dict.fromkeys(reasons))
        row["selected"] = not row["rejection_reasons"] and len(selected) < target_count
        if not row["selected"]:
            if not row["rejection_reasons"] and len(selected) >= target_count:
                row["rejection_reasons"].append("超过本期目标数量")
            continue
        row["rank"] = len(selected) + 1
        selected.append(row)
        ai_count += int(bool(row.get("ai_related")))
        categories[category] = categories.get(category, 0) + 1
    discovery = config["discovery"]
    candidate_minimum = int(discovery["candidate_minimum"])
    candidate_maximum = int(discovery["candidate_maximum"])
    deep_minimum = int(selection_config.get("deep_verified_minimum", 8))
    risks = package_risks(raw, rows, selected, candidate_minimum, deep_minimum)
    ready = (
        not raw.get("meta", {}).get("rate_limited")
        and candidate_minimum <= len(rows) <= candidate_maximum
        and sum(bool(row["deep_verified"]) for row in rows) >= deep_minimum
        and minimum <= len(selected) <= maximum
        and not any(item["verification"]["license"]["status"] == "not_found" for item in selected)
        and all(item["reader_card"]["metrics"].get("verified_at") for item in selected)
    )
    return {
        "schema_version": 2,
        "content_type": "github-hot",
        "package_id": f"github-hot-{run_at.astimezone(BJT):%Y-%m-%d}",
        "run_at": run_at.isoformat(),
        "status": "ready_for_human_review" if ready else "needs_review",
        "window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "boundary": "left_closed_right_open",
        },
        "selection": {
            "candidate_count": len(rows),
            "deep_verified_count": sum(bool(row["deep_verified"]) for row in rows),
            "selected_count": len(selected),
            "minimum": minimum,
            "maximum": maximum,
            "target": target_count,
        },
        "items": selected,
        "candidates": rows,
        "sources": [
            {"name": item.get("repo"), "url": item.get("official_url")}
            for item in selected
        ],
        "risks": risks,
        "history_excluded": sorted(past),
    }


def validate_package(payload):
    errors = []
    required = (
        "schema_version",
        "content_type",
        "package_id",
        "run_at",
        "status",
        "window",
        "selection",
        "items",
        "candidates",
        "sources",
        "risks",
    )
    if payload.get("schema_version") != 2:
        errors.append("不支持的 schema_version")
    if payload.get("content_type") != "github-hot":
        errors.append("content_type 错误")
    for field in required:
        if field not in payload:
            errors.append(f"缺少 {field}")
    for item in payload.get("items", []):
        for field in (
            "rank",
            "repo",
            "official_url",
            "category",
            "reader_card",
            "verification",
            "visual_candidates",
            "image2_brief",
        ):
            if field not in item:
                errors.append(f"{item.get('repo', '未命名项目')} 缺少 {field}")
        if len((item.get("reader_card") or {}).get("highlights") or []) != 3:
            errors.append(f"{item.get('repo', '未命名项目')} 核心亮点不是 3 条")
    return errors


def target(root, run_at):
    return Path(root) / "github-hot" / run_at.astimezone(BJT).date().isoformat()


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
        package = build(load(raw_path), run_at, config, args.output_root)
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
