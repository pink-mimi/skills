from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

BJT = timezone(timedelta(hours=8))

@dataclass
class Project:
    repo: str; description: str; stars: int; weekly_stars: int; license: str; last_commit: str
    latest_release: str; release_at: str; platform: str; install: str; audience: str; risks: str
    ai_related: bool; category: str; highlights: list[str] = field(default_factory=list); official_url: str = ""
    significant_change: bool = False; eligible: bool = True; rejection_reason: str = ""; score: float = 0.0

def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def window_for(run_at: datetime, config: dict) -> tuple[datetime, datetime]:
    end = run_at.astimezone(BJT)
    return end - timedelta(days=int(config["window"]["duration_days"])), end

def in_window(value: str, start: datetime, end: datetime) -> bool:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(BJT)
    return start <= parsed < end

def normalize(raw: dict) -> Project:
    required = ("repo", "description", "license", "last_commit", "platform", "install", "audience", "risks", "category")
    placeholder_prefixes = ("请", "待核验", "待确认", "unknown", "tbd")
    missing = [key for key in required if not str(raw.get(key, "")).strip() or str(raw.get(key, "")).strip().lower().startswith(placeholder_prefixes)]
    license_name = str(raw.get("license") or "").strip()
    if license_name.upper() in {"NOASSERTION", "OTHER", "UNKNOWN"}: missing.append("license")
    score = float(raw.get("weekly_stars") or 0) * 1.5 + min(float(raw.get("stars") or 0), 50000) / 1000
    score += 20 if raw.get("latest_release") else 0
    score += min(len(raw.get("highlights") or []), 3) * 5
    return Project(
        repo=str(raw.get("repo") or "").strip(), description=str(raw.get("description") or "").strip(),
        stars=int(raw.get("stars") or 0), weekly_stars=int(raw.get("weekly_stars") or 0), license=license_name,
        last_commit=str(raw.get("last_commit") or "").strip(), latest_release=str(raw.get("latest_release") or "").strip(),
        release_at=str(raw.get("release_at") or "").strip(), platform=str(raw.get("platform") or "").strip(),
        install=str(raw.get("install") or "").strip(), audience=str(raw.get("audience") or "").strip(),
        risks=str(raw.get("risks") or "").strip(), ai_related=bool(raw.get("ai_related")),
        category=str(raw.get("category") or "general").strip(),
        highlights=[str(x).strip() for x in raw.get("highlights") or [] if str(x).strip()],
        official_url=str(raw.get("official_url") or f"https://github.com/{raw.get('repo','')}").strip(),
        significant_change=bool(raw.get("significant_change")), eligible=not missing,
        rejection_reason=("关键字段缺失或许可证不明确：" + "、".join(sorted(set(missing)))) if missing else "", score=score)

def select_projects(projects: Iterable[Project], config: dict, history: set[str]) -> list[Project]:
    limits = config["selection"]
    ranked = sorted((p for p in projects if p.eligible and (p.repo not in history or p.significant_change)), key=lambda p: p.score, reverse=True)
    selected=[]; categories={}; ai_count=0
    for project in ranked:
        if project.ai_related and ai_count >= int(limits["maximum_ai"]): continue
        if categories.get(project.category, 0) >= int(limits["maximum_per_category"]): continue
        selected.append(project); categories[project.category]=categories.get(project.category,0)+1; ai_count += int(project.ai_related)
        if len(selected) >= int(limits["maximum"]): break
    return selected

def package_status(projects: list[Project], selected: list[Project], rate_limited: bool, config: dict) -> str:
    discovery, limits = config["discovery"], config["selection"]
    ready = (not rate_limited and int(discovery["candidate_minimum"]) <= len(projects) <= int(discovery["candidate_maximum"])
             and sum(not p.ai_related for p in projects) >= int(discovery["minimum_non_ai_candidates"])
             and sum(p.eligible for p in projects) >= int(limits["minimum"])
             and len(selected) >= int(limits["minimum"]))
    return "ready_for_human_review" if ready else "needs_review"

def scan_history(output_root: Path, run_date: str, lookback: int) -> set[str]:
    base=output_root/"github-hot"
    if not base.exists(): return set()
    files=sorted((p for p in base.glob("*/selected.json") if p.parent.name < run_date), reverse=True)[:lookback]
    repos=set()
    for path in files:
        try:
            repos.update(str(item.get("repo")) for item in json.loads(path.read_text(encoding="utf-8")).get("items",[]) if item.get("repo"))
        except (OSError,json.JSONDecodeError): pass
    return repos

def project_dicts(projects: Iterable[Project]) -> list[dict]: return [asdict(p) for p in projects]
def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
