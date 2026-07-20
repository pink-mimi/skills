from __future__ import annotations
import json, os, re, time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

UA="github-hot-wechat/1.0"

def _get(url:str, token:str|None=None)->tuple[object|None,bool,str|None]:
    headers={"User-Agent":UA,"Accept":"application/vnd.github+json"}
    if token: headers["Authorization"]=f"Bearer {token}"
    try:
        with urlopen(Request(url,headers=headers),timeout=25) as response:
            raw=response.read(); ctype=response.headers.get("Content-Type","")
            return (json.loads(raw) if "json" in ctype else raw.decode("utf-8","replace")),False,None
    except HTTPError as exc:
        return None,exc.code in (403,429),f"HTTP {exc.code}: {url}"
    except (URLError,TimeoutError,OSError) as exc:
        return None,False,f"{type(exc).__name__}: {url}"

def _trending(html_text:str)->list[dict]:
    rows=[]
    for article in re.findall(r"<article[^>]*Box-row[^>]*>(.*?)</article>",html_text,re.S|re.I):
        match=re.search(r'href="/([^"?#]+/[^"?#]+)"',article)
        if not match: continue
        repo=match.group(1).strip(); weekly=re.search(r"([\d,]+)\s+stars\s+this\s+week",re.sub(r"<[^>]+>"," ",article),re.I)
        rows.append({"repo":repo,"weekly_stars":int(weekly.group(1).replace(",","")) if weekly else 0})
    return rows

def collect(config:dict, fetched_at:datetime)->dict:
    token=os.environ.get("GITHUB_TOKEN"); found={}; errors=[]; rate_limited=False
    for language in config["discovery"]["languages"]:
        suffix=f"/{language}" if language else ""
        page,limited,error=_get(f"https://github.com/trending{suffix}?since=weekly",token)
        rate_limited |= limited
        if error: errors.append(error); continue
        for row in _trending(str(page)): found.setdefault(row["repo"],row)
    items=[]
    for seed in list(found.values())[:int(config["discovery"]["candidate_maximum"])]:
        repo=seed["repo"]
        data,limited,error=_get(f"https://api.github.com/repos/{repo}",token); rate_limited |= limited
        if error or not isinstance(data,dict): errors.append(error or f"invalid API response: {repo}"); continue
        license_data=data.get("license") or {}; topics=data.get("topics") or []; text=(str(data.get("description") or "")+" "+" ".join(topics)).lower()
        item={**seed,"description":data.get("description") or "","stars":data.get("stargazers_count") or 0,"license":license_data.get("spdx_id") or "","last_commit":data.get("pushed_at") or "","latest_release":"","release_at":"","platform":"请根据 README 核验","install":"请根据 README 核验","audience":"请人工确认","risks":"请人工确认","ai_related":any(k in text for k in (" ai ","llm","agent","machine learning","artificial intelligence")),"category":(topics[0] if topics else data.get("language") or "general").lower(),"highlights":[],"official_url":data.get("html_url") or f"https://github.com/{repo}"}
        release,limited,_=_get(f"https://api.github.com/repos/{repo}/releases/latest",token); rate_limited |= limited
        if isinstance(release,dict): item["latest_release"]=release.get("tag_name") or ""; item["release_at"]=release.get("published_at") or ""
        items.append(item); time.sleep(.05)
    return {"meta":{"fetched_at":fetched_at.isoformat(),"rate_limited":rate_limited,"errors":errors,"sources":["GitHub Trending weekly","GitHub REST API"]},"items":items}

def read_fixture(path:Path)->dict: return json.loads(path.read_text(encoding="utf-8"))
