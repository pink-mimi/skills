from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import html
import json
import re
import shutil
import sys
from urllib.parse import urljoin
import urllib.request
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from editorial import assess_heat, derive_weekly_editorial, project_editorial


BJT = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[1]
LICENSE_UNKNOWN = {"", "NOASSERTION", "UNKNOWN", "OTHER", "未发现明确许可证"}
VISUAL_USAGE = {"approved", "review_required", "rejected"}
REQUIRED_AVOID = ("项目Logo", "虚构软件界面", "中文文字", "虚构数据")
TRENDING_WEEKLY_URL = "https://github.com/trending?since=weekly"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_text(request, timeout=20, opener=urllib.request.urlopen):
    try:
        data = opener(request, timeout=timeout).read()
    except http.client.IncompleteRead as exc:
        data = exc.partial or b""
    return data.decode("utf-8", "replace")


def window(run_at, config):
    end = run_at.astimezone(BJT)
    return end - timedelta(days=int(config["window"]["duration_days"])), end


def collect(run_at):
    request = urllib.request.Request(
        TRENDING_WEEKLY_URL,
        headers={"User-Agent": "github-hot-research/2.0"},
    )
    try:
        page = fetch_text(request, timeout=20)
    except Exception as exc:
        return {"meta": {"rate_limited": True, "error": str(exc)}, "items": []}
    trending_rows = parse_trending_weekly_html(page, run_at)

    def api_json(path):
        req = urllib.request.Request(
            f"https://api.github.com{path}",
            headers={
                "User-Agent": "github-hot-research/2.0",
                "Accept": "application/vnd.github+json",
            },
        )
        return json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))

    def api_readme(repo):
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/readme",
            headers={
                "User-Agent": "github-hot-research/2.0",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
            if data.get("encoding") == "base64" and data.get("content"):
                return base64.b64decode(data["content"]).decode("utf-8", "replace")
        except Exception:
            return ""
        return ""

    return {
        "meta": {
            "rate_limited": False,
            "fetched_at": run_at.isoformat(),
            "source": "github_trending_weekly",
            "source_url": TRENDING_WEEKLY_URL,
        },
        "items": enrich_trending_rows(trending_rows, run_at, api_json=api_json, api_readme=api_readme),
    }


def enrich_trending_rows(rows, run_at, api_json, api_readme):
    return [
        enrich_trending_row(row, run_at, api_json=api_json, api_readme=api_readme)
        for row in rows
    ]


def enrich_trending_row(row, run_at, api_json, api_readme):
    row = deepcopy(row)
    repo = row["repo"]
    official_url = row.get("official_url") or f"https://github.com/{repo}"
    try:
        data = api_json(f"/repos/{repo}") or {}
    except Exception:
        data = {}
    license_info = data.get("license") or {}
    existing_license = clean_text(row.get("license"))
    api_spdx = clean_text(license_info.get("spdx_id"))
    license_status = (
        "verified"
        if api_spdx and api_spdx != "NOASSERTION"
        else ("not_found" if existing_license.upper() in LICENSE_UNKNOWN else "verified")
    )
    metrics = row.get("reader_card", {}).get("metrics", {})
    language = metrics.get("language") or data.get("language") or ""
    weekly = metrics.get("weekly_stars")
    description = row.get("description") or data.get("description") or f"{repo} 是本周进入 GitHub Trending 的开源项目。"
    original_description = clean_text(row.get("original_description") or description)
    translated_description = clean_text(row.get("translated_description") or translate_description(original_description))
    category_label = "AI 项目" if re.search(r"\b(ai|agent|llm|model)\b", description, re.I) else "开源项目"
    try:
        readme_text = api_readme(repo)
    except Exception:
        readme_text = ""
    official_url = data.get("html_url") or official_url
    license_record_value = {
        "status": license_status,
        "name": license_info.get("name") or ("" if license_status == "not_found" else existing_license),
        "spdx_id": api_spdx or ("" if license_status == "not_found" else existing_license),
        "url": f"{official_url}/blob/main/LICENSE",
    }
    existing_card = row.get("reader_card") or {}
    row.update({
        "repo": repo,
        "official_url": official_url,
        "homepage_url": data.get("homepage") or row.get("homepage_url") or "",
        "created_at": data.get("created_at") or row.get("created_at"),
        "category": "ai-automation" if category_label == "AI 项目" else row.get("category") or "developer-tools",
        "description": description,
        "original_description": original_description,
        "translated_description": translated_description,
        "reader_card": {
            "category_label": existing_card.get("category_label") or category_label,
            "name": data.get("name") or existing_card.get("name") or repo.split("/")[-1],
            "summary": existing_card.get("summary") or translated_description or description,
            "original_description": existing_card.get("original_description") or original_description,
            "translated_description": existing_card.get("translated_description") or translated_description,
            "recommendation": existing_card.get("recommendation") or "本周进入 GitHub Trending，适合先收藏并按需试用。",
            "highlights": existing_card.get("highlights") or ["进入本周 GitHub Trending", "官方仓库资料可追溯", "适合按 README 继续了解"],
            "audience": existing_card.get("audience") or ["开发者", "开源项目观察者"],
            "difficulty": existing_card.get("difficulty") or {
                "level": "medium",
                "label": "中等",
                "note": "以官方 README 的安装说明为准",
            },
            "metrics": {
                "language": language,
                "stars": metrics.get("stars") if metrics.get("stars") is not None else data.get("stargazers_count"),
                "weekly_stars": weekly,
                "forks": metrics.get("forks") if metrics.get("forks") is not None else data.get("forks_count"),
                "verified_at": metrics.get("verified_at") or run_at.isoformat(),
            },
            "reader_warning": existing_card.get("reader_warning") or "",
        },
        "verification": {
            "readme": {"url": f"{official_url}#readme", "verified_at": run_at.isoformat()},
            "license": {
                **license_record_value,
            },
            "maintenance": {
                "status": "active" if data.get("pushed_at") else "unknown",
                "last_commit_at": data.get("pushed_at") or "",
                "latest_release_at": "",
                "evidence_urls": [f"{official_url}/commits"],
            },
            "requirements": {
                "platforms": ["GitHub"],
                "install": "以官方 README 的安装说明为准",
                "command_line": True,
                "programming_required": True,
                "account_required": False,
                "api_key_required": False,
                "paid_dependency": False,
                "special_hardware": False,
            },
            "risks": [],
            "evidence": [official_url, f"{official_url}#readme"],
        },
        "visual_candidates": extract_readme_visual_candidates(
            readme_text,
            repo=repo,
            source_page=f"{official_url}#readme",
            license_info=license_record_value,
            verified_at=run_at.isoformat(),
        ) or row.get("visual_candidates") or [],
        "image2_brief": {
            "subject": description,
            "scene": "开源项目工作流与代码协作的抽象场景",
            "must_include": (existing_card.get("highlights") or ["进入本周 GitHub Trending", "官方仓库资料可追溯"])[:2],
            "must_avoid": ["项目Logo", "虚构软件界面", "中文文字", "虚构数据"],
        },
        "heat_evidence": [{
            "kind": "github_trending",
            "observed_at": run_at.isoformat(),
            "url": official_url,
            "summary": "项目进入 GitHub Trending weekly 榜单。",
        }],
        "hot_reason": "项目进入 GitHub Trending weekly 榜单，本周获得明显社区关注。",
        "use_case": description,
        "editorial_summary": description,
        "ai_related": category_label == "AI 项目",
    })
    return row


def number_from_text(value):
    text = re.sub(r"[^\d]", "", clean_text(value))
    return int(text) if text else None


def strip_tags(value):
    return html.unescape(re.sub(r"<[^>]+>", " ", value)).strip()


def contains_cjk(value):
    return bool(re.search(r"[\u4e00-\u9fff]", clean_text(value)))


def translate_description(value):
    text = clean_text(value)
    if not text or contains_cjk(text):
        return text
    lower = text.lower()
    if lower == "a hive mind communication platform":
        return "群体智能协作通信平台。"
    if "fastest browser for ai agents to run browser automation" in lower:
        return "面向 AI 智能体运行浏览器自动化的高速浏览器，可把已登录的浏览器状态安全分享给 Codex 或 Claude Code 等智能体，同时不打扰你的正常使用，零成本、零配置。"
    if "foundation model for the language of financial markets" in lower:
        return "Kronos 是面向金融市场语言的基础模型。"
    if "battle-tested at alibaba" in lower and "hybrid architecture code review tool" in lower:
        return "开源免费的混合架构代码审查工具，经过阿里巴巴规模场景验证，结合确定性流水线与 LLM Agent，支持精准行级评论、内置调优规则集，并兼容 OpenAI 与 Anthropic。"
    if "real-time global intelligence dashboard" in lower:
        return "实时全球情报看板。通过 AI 进行新闻聚合、地缘政治监测以及基础设施追踪，把信息集中到统一界面中，方便用户掌握事件情况。"
    if "stop it from burying the answer" in lower and "adhd-friendly output" in lower:
        return "一个帮助编码智能体不要把答案藏起来的技能，输出方式对 ADHD 用户更友好。"
    if "smart, flexible" in lower and "route optimization" in lower:
        return "智能、灵活且高度可定制的开源路线优化应用。"
    if "free mit ai gateway" in lower or "one endpoint, 290+ providers" in lower:
        return "免费的 MIT 许可 AI 网关，用一个端点连接数百个模型和服务提供商，并支持 Claude Code、Codex、Cursor 等工具链。"
    if "self-hosted deployment platform" in lower:
        return "自托管部署平台。"
    if "skills for real engineers" in lower:
        return "面向真实工程工作的技能集合，直接来自作者的 .agents 目录。"
    if "tree-of-thought with pruning" in lower:
        return "面向编码智能体的 ADHD 技能，基于 Claude 与 Codex Agent SDK 实现带剪枝的思维树流程。"
    if "web ui for the pi coding agent" in lower:
        return "Pi 编码智能体的 Web 用户界面。"
    if "turns commodity wifi signals into real-time spatial intelligence" in lower:
        return "把普通 WiFi 信号转化为实时空间智能、生命体征监测和存在检测能力，全程不需要视频画面。"
    if "ai agent toolkit" in lower and "unified llm api" in lower:
        return "AI 智能体工具包，包含统一 LLM API、智能体循环、终端界面和编码智能体命令行工具。"
    if "coding skills and prompts" in lower:
        return "一组面向 AI 辅助开发工作流的聚焦编码技能和提示词。"
    if "shipping and fulfillment workflows" in lower:
        return "面向发货与履约工作流的开源解决方案。"
    replacements = (
        ("open-source", "开源"),
        ("open source", "开源"),
        ("real-time", "实时"),
        ("dashboard", "看板"),
        ("developer", "开发者"),
        ("developers", "开发者"),
        ("workflow", "工作流"),
        ("workflows", "工作流"),
        ("tool", "工具"),
        ("tools", "工具"),
        ("application", "应用"),
        ("applications", "应用"),
        ("ai-powered", "AI 驱动"),
        ("news aggregation", "新闻聚合"),
        ("monitoring", "监测"),
        ("tracking", "追踪"),
        ("customizable", "可定制"),
        ("flexible", "灵活"),
    )
    translated = text
    for source, target in replacements:
        translated = re.sub(source, target, translated, flags=re.I)
    if translated != text and contains_cjk(translated):
        return translated
    return f"官方描述：{text}"


def infer_reader_profile(repo, description):
    text = f"{repo} {description}".lower()
    if "block/buzz" in text or "hive mind" in text:
        return {
            "category": "collaboration",
            "category_label": "协作通信",
            "recommendation": "它把“群体智能”放进通信平台里，适合观察多人协作和多 Agent 协同会往哪里走。",
            "highlights": ["面向群体智能协作", "强调沟通与协同组织", "适合观察多人/多 Agent 工作流"],
            "audience": ["协作工具开发者", "Agent 产品观察者", "开源项目研究者"],
        }
    if "ego-lite" in text or "browser automation" in text:
        return {
            "category": "ai-browser",
            "category_label": "Agent 浏览器",
            "recommendation": "它解决的是 AI 智能体接管浏览器自动化时的登录态共享和打扰问题，方向很实用。",
            "highlights": ["面向 AI Agent 浏览器自动化", "支持共享已登录浏览器状态", "强调零成本、零配置和低打扰"],
            "audience": ["Agent 工具开发者", "Codex/Claude Code 用户", "自动化工作流使用者"],
        }
    if "kronos" in text and "financial markets" in text:
        return {
            "category": "finance-ai",
            "category_label": "金融基础模型",
            "recommendation": "它把金融市场数据当成一种“语言”来建模，适合关注 AI 金融基础设施的人继续跟踪。",
            "highlights": ["面向金融市场数据建模", "以基础模型方式处理市场语言", "适合观察垂直领域模型落地"],
            "audience": ["量化研究者", "金融科技开发者", "垂直模型观察者"],
        }
    if "open-code-review" in text or "code review tool" in text:
        return {
            "category": "code-review",
            "category_label": "代码审查工具",
            "recommendation": "它把确定性规则和 LLM Agent 放在同一套代码审查流程里，适合团队评估自动 Review 的边界。",
            "highlights": ["结合规则流水线与 LLM Agent", "支持精准行级评论", "内置常见风险规则集"],
            "audience": ["研发团队", "代码质量负责人", "AI 工程化实践者"],
        }
    if "worldmonitor" in text or "intelligence dashboard" in text or "geopolitical" in text:
        return {
            "category": "ai-intelligence",
            "category_label": "AI 与情报看板",
            "recommendation": "如果你关注新闻、地缘事件或 OSINT 工作流，它像是一张可以继续深挖的实时观察地图。",
            "highlights": ["AI 辅助聚合新闻与事件线索", "把监测信息集中到统一界面", "适合观察态势感知类产品"],
            "audience": ["OSINT 观察者", "新闻研究者", "数据看板开发者"],
        }
    if "adhd" in text and ("coding agent" in text or "agent sdk" in text):
        return {
            "category": "ai-coding",
            "category_label": "AI 编码辅助",
            "recommendation": "它把编码助手的输出方式往前调了一步：少绕弯，先把答案亮出来。",
            "highlights": ["面向编码助手的输出习惯优化", "强调 ADHD 友好的信息呈现", "适合调教 Agent 工作流"],
            "audience": ["AI 编程用户", "Agent 工作流使用者", "关注 ADHD 友好输出的人"],
        }
    if "ai agent" in text and ("book" in text or "pdf" in text or "工程实践" in text):
        return {
            "category": "ai-learning",
            "category_label": "AI Agent 学习",
            "recommendation": "如果你想从会调用模型走到能设计 Agent 系统，它是值得系统收藏的学习资料。",
            "highlights": ["覆盖 AI Agent 原理与工程实践", "提供正文、PDF 和配套代码", "适合按章节持续学习"],
            "audience": ["AI Agent 学习者", "开发者", "技术写作者"],
        }
    if "gateway" in text or "models" in text or "claude code" in text or "codex" in text:
        return {
            "category": "ai-infra",
            "category_label": "AI 开发基础设施",
            "recommendation": "它适合想把多模型调用、额度和工具链统一管理的人继续研究。",
            "highlights": ["统一多模型和多服务提供商入口", "支持主流 AI 编码工具", "强调额度感知和自动回退"],
            "audience": ["AI 应用开发者", "Agent 工具用户", "基础设施维护者"],
        }
    if "deployment" in text or "shipping" in text or "fulfillment" in text:
        return {
            "category": "developer-tools",
            "category_label": "部署与履约工具",
            "recommendation": "它指向一个很实际的问题：把部署、发货或履约流程尽量放回自己可控的系统里。",
            "highlights": ["面向自托管部署或履约场景", "适合评估开源替代方案", "更关注业务流程落地"],
            "audience": ["独立开发者", "电商工具开发者", "自托管用户"],
        }
    if "skills" in text or ".agents" in text or "prompts" in text:
        return {
            "category": "ai-coding",
            "category_label": "AI 编程技能",
            "recommendation": "它更像一份可抄作业的 Agent 技能目录，适合拿来改造自己的编码工作流。",
            "highlights": ["整理可复用的 Agent 技能", "直接来自实际工程工作流", "适合按场景拆分提示和流程"],
            "audience": ["AI 编程用户", "提示词维护者", "工程团队"],
        }
    if "wifi" in text or "spatial intelligence" in text or "vital sign" in text:
        return {
            "category": "systems-data",
            "category_label": "空间感知",
            "recommendation": "它把普通 WiFi 信号变成空间感知线索，是值得观察的硬核技术项目。",
            "highlights": ["利用 WiFi 信号进行空间感知", "关注生命体征和存在检测", "不依赖视频画面"],
            "audience": ["物联网开发者", "信号处理研究者", "智能空间产品团队"],
        }
    if "pi" in text and ("agent" in text or "web ui" in text):
        return {
            "category": "ai-coding",
            "category_label": "AI Agent 工具",
            "recommendation": "它适合观察轻量 Agent 工具如何把模型接口、循环和命令行体验串起来。",
            "highlights": ["围绕 Pi 编码 Agent 展开", "覆盖 Web UI 或命令行体验", "适合源码阅读和对照试用"],
            "audience": ["Agent 工具开发者", "前端学习者", "开源观察者"],
        }
    return {
        "category": "developer-tools",
        "category_label": "开源项目",
        "recommendation": "项目用途明确，可以先按 README 判断是否值得收藏或试用。",
        "highlights": ["进入本周 GitHub Trending", "官方仓库资料可追溯", "适合按 README 继续了解"],
        "audience": ["开发者", "开源项目观察者"],
    }


def trending_reader_card(repo, description, translated_description, language, stars, weekly_stars, forks, run_at):
    profile = infer_reader_profile(repo, description)
    return {
        "category_label": profile["category_label"],
        "name": repo.split("/")[-1],
        "summary": translated_description or description,
        "original_description": description,
        "translated_description": translated_description,
        "recommendation": profile["recommendation"],
        "highlights": profile["highlights"],
        "audience": profile["audience"],
        "difficulty": {"level": "medium", "label": "中等", "note": "以官方 README 为准"},
        "metrics": {
            "language": language,
            "stars": stars,
            "weekly_stars": weekly_stars,
            "forks": forks,
            "verified_at": run_at.isoformat(),
        },
        "reader_warning": "",
    }


def parse_trending_weekly_html(page, run_at):
    rows = []
    for article in re.findall(r"<article[\s\S]*?</article>", page):
        match = re.search(r'<h2[^>]*>[\s\S]*?href="/([^"?#]+/[^"?#]+)"', article)
        if not match:
            continue
        repo = re.sub(r"\s", "", html.unescape(match.group(1)))
        if any(row["repo"] == repo for row in rows):
            continue
        description_area = article[match.end():]
        description_match = re.search(
            r"<p\b[^>]*\bcolor-fg-muted\b[^>]*>([\s\S]*?)</p>",
            description_area,
        ) or re.search(r"<p\b[^>]*>([\s\S]*?)</p>", description_area)
        description = strip_tags(description_match.group(1)) if description_match else f"{repo} 是本周进入 GitHub Trending 的开源项目。"
        language_match = re.search(r'itemprop="programmingLanguage"[^>]*>([\s\S]*?)</span>', article)
        language = strip_tags(language_match.group(1)) if language_match else ""
        star_match = re.search(rf'href="/{re.escape(repo)}/stargazers"[^>]*>([\s\S]*?)</a>', article)
        fork_match = re.search(rf'href="/{re.escape(repo)}/forks"[^>]*>([\s\S]*?)</a>', article)
        weekly_match = re.search(r"([\d,]+)\s+stars\s+this\s+week", article, re.I)
        rank = len(rows) + 1
        official_url = f"https://github.com/{repo}"
        translated_description = translate_description(description)
        stars = number_from_text(strip_tags(star_match.group(1))) if star_match else None
        weekly_stars = number_from_text(weekly_match.group(1)) if weekly_match else None
        forks = number_from_text(strip_tags(fork_match.group(1))) if fork_match else None
        reader_card = trending_reader_card(
            repo, description, translated_description, language, stars, weekly_stars, forks, run_at
        )
        profile = infer_reader_profile(repo, description)
        rows.append({
            "repo": repo,
            "official_url": official_url,
            "description": description,
            "original_description": description,
            "translated_description": translated_description,
            "category": profile["category"],
            "reader_card": reader_card,
            "trending": {
                "rank": rank,
                "period": "weekly",
                "url": TRENDING_WEEKLY_URL,
                "observed_at": run_at.isoformat(),
            },
            "heat_evidence": [{
                "kind": "github_trending",
                "observed_at": run_at.isoformat(),
                "url": official_url,
                "summary": "项目进入 GitHub Trending weekly 榜单。",
            }],
            "hot_reason": "项目进入 GitHub Trending weekly 榜单，本周获得明显社区关注。",
            "use_case": description,
            "editorial_summary": description,
            "visual_candidates": [],
        })
        if len(rows) >= 10:
            break
    return rows


def normalize_readme_image_url(url, repo):
    raw = html.unescape(clean_text(url))
    if not raw or raw.startswith("#") or raw.startswith("data:"):
        return ""
    if raw.startswith(("http://", "https://")):
        if "github.com" in raw and f"/{repo}/raw/" in raw:
            return raw.replace("https://github.com/", "https://raw.githubusercontent.com/").replace("/raw/", "/")
        if "github.com" in raw and f"/{repo}/blob/" in raw:
            return raw.replace("https://github.com/", "https://raw.githubusercontent.com/").replace("/blob/", "/")
        return raw
    return urljoin(f"https://raw.githubusercontent.com/{repo}/main/", raw)


def readme_image_type(url, alt):
    text = f"{url} {alt}".lower()
    if any(value in text for value in ("badge", "shield", "shields.io", "logo", "avatar", "icon", "social-preview", "social_preview")):
        return "rejected"
    if any(value in text for value in ("screenshot", "screen", "demo", "preview", "dashboard", "interface", "ui", "monitor")):
        return "official_screenshot"
    return "official_screenshot"


def extract_readme_visual_candidates(readme_text, repo, source_page, license_info, verified_at):
    candidates = []
    markdown_images = re.findall(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", readme_text or "")
    html_images = [
        (re.search(r'alt=["\']([^"\']*)["\']', tag, re.I).group(1) if re.search(r'alt=["\']([^"\']*)["\']', tag, re.I) else "",
         re.search(r'src=["\']([^"\']+)["\']', tag, re.I).group(1))
        for tag in re.findall(r"<img\b[^>]*>", readme_text or "", re.I)
        if re.search(r'src=["\']([^"\']+)["\']', tag, re.I)
    ]
    seen = set()
    for alt, raw_url in markdown_images + html_images:
        url = normalize_readme_image_url(raw_url, repo)
        if not url or url in seen:
            continue
        seen.add(url)
        image_type = readme_image_type(url, alt)
        if image_type == "rejected":
            continue
        repo_hosted = f"raw.githubusercontent.com/{repo}/" in url
        license_status = clean_text((license_info or {}).get("status"))
        usage_status = "approved" if repo_hosted else "review_required"
        usage_basis = "repo_hosted_readme_image" if repo_hosted else "external_image_review_required"
        candidates.append({
            "type": image_type,
            "url": url,
            "source_page": source_page,
            "description": clean_text(alt) or "README 中的项目图片",
            "alt": clean_text(alt),
            "is_repo_hosted": repo_hosted,
            "is_real_interface": True,
            "license_status": license_status or "unknown",
            "license_name": clean_text((license_info or {}).get("name")),
            "attribution_required": False,
            "usage_status": usage_status,
            "usage_basis": usage_basis,
            "verified_at": verified_at,
        })
    return candidates[:3]


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
    original_description = clean_text(
        existing.get("original_description") or row.get("original_description") or row.get("description")
    )
    translated_description = clean_text(
        existing.get("translated_description") or row.get("translated_description") or translate_description(original_description)
    )
    return {
        "category_label": clean_text(existing.get("category_label") or row.get("category")),
        "name": clean_text(existing.get("name") or clean_text(row.get("repo")).split("/")[-1]),
        "summary": clean_text(existing.get("summary") or translated_description or row.get("description")),
        "original_description": original_description,
        "translated_description": translated_description,
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
        repo_hosted = bool(visual.get("is_repo_hosted")) or (
            "raw.githubusercontent.com/" in clean_text(visual.get("url"))
            and "github.com/" in clean_text(visual.get("source_page"))
        )
        if (
            repo_hosted
            and clean_text(visual.get("type")) == "official_screenshot"
            and usage == "review_required"
        ):
            usage = "approved"
            visual.setdefault("usage_basis", "repo_hosted_readme_image")
        if license_status != "verified" and usage == "approved" and not repo_hosted:
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
    for row in rows:
        row["heat"] = assess_heat(row, start.isoformat(), end.isoformat())
        row["rejection_reasons"] = list(
            dict.fromkeys(row["rejection_reasons"] + row["heat"]["rejection_reasons"])
        )
        row["eligible"] = not row["rejection_reasons"]
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
    mature_count = 0
    categories = {}
    locked_trending = raw.get("meta", {}).get("source") == "github_trending_weekly" or all(
        (row.get("trending") or {}).get("period") == "weekly" for row in rows[:target_count]
    )
    if locked_trending:
        past = set()
    selection_rows = (
        sorted(rows, key=lambda item: int((item.get("trending") or {}).get("rank") or 9999))
        if locked_trending
        else sorted(rows, key=lambda item: item["score"], reverse=True)
    )
    for row in selection_rows:
        reasons = list(row["rejection_reasons"])
        if not locked_trending and row.get("repo") in past and not row.get("significant_change"):
            reasons.append("最近 8 期已经推荐且没有重大更新")
        if not locked_trending and row.get("ai_related") and ai_count >= int(selection_config["maximum_ai"]):
            reasons.append("AI 项目数量已达到上限")
        if (
            not locked_trending
            and
            row["heat"]["heat_class"] == "mature_resurgence"
            and mature_count >= int(config["weekly_heat"]["mature_resurgence_maximum"])
        ):
            reasons.append("成熟项目数量已达到上限")
        category = clean_text(row.get("category"))
        if not locked_trending and categories.get(category, 0) >= int(selection_config["maximum_per_category"]):
            reasons.append("同一类别数量已达到上限")
        row["rejection_reasons"] = list(dict.fromkeys(reasons))
        row["selected"] = (locked_trending or not row["rejection_reasons"]) and len(selected) < target_count
        if not row["selected"]:
            if not row["rejection_reasons"] and len(selected) >= target_count:
                row["rejection_reasons"].append("超过本期目标数量")
            continue
        row["rank"] = int((row.get("trending") or {}).get("rank") or len(selected) + 1)
        row["editorial"] = project_editorial(row, row["heat"])
        selected.append(row)
        ai_count += int(bool(row.get("ai_related")))
        mature_count += int(row["heat"]["heat_class"] == "mature_resurgence")
        categories[category] = categories.get(category, 0) + 1
    discovery = config["discovery"]
    candidate_minimum = int(discovery["candidate_minimum"])
    candidate_maximum = int(discovery["candidate_maximum"])
    deep_minimum = int(selection_config.get("deep_verified_minimum", 8))
    risks = package_risks(raw, rows, selected, candidate_minimum, deep_minimum)
    editorial = derive_weekly_editorial(selected)
    editorial_complete = all(
        item["editorial"]["hot_reason"]
        and item["editorial"]["hot_reason_evidence"]
        and item["editorial"]["use_case"]
        and len(item["editorial"]["summary"]) >= 40
        for item in selected
    )
    if not editorial_complete:
        risks.append("入选项目编辑素材不完整")
    ready = (
        not raw.get("meta", {}).get("rate_limited")
        and candidate_minimum <= len(rows) <= candidate_maximum
        and sum(bool(row["deep_verified"]) for row in rows) >= deep_minimum
        and minimum <= len(selected) <= maximum
        and not any(item["verification"]["license"]["status"] == "not_found" for item in selected)
        and all(item["reader_card"]["metrics"].get("verified_at") for item in selected)
        and editorial_complete
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
            "source_locked": locked_trending,
        },
        "items": selected,
        "editorial": editorial,
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
        "editorial",
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
            "heat",
            "editorial",
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
