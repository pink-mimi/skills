from __future__ import annotations

import argparse, hashlib, html, json, re, shutil, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

BJT = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[1]

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
def window(run_at, config):
    hour, minute = map(int, config["window"]["end_time"].split(":"))
    end = run_at.astimezone(BJT).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return end - timedelta(hours=int(config["window"]["duration_hours"])), end
def parse_time(value):
    if not value: return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        try: parsed = parsedate_to_datetime(str(value))
        except (TypeError, ValueError): return None
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=BJT)).astimezone(BJT)
def clean(value): return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>","",value or ""))).strip()
def parse_feed(payload,source):
    root=ET.fromstring(payload); rows=[]
    for node in root.iter("item"):
        get=lambda name:(node.findtext(name) or "").strip(); title=clean(get("title")); url=get("link")
        if title and url: rows.append({"title":title,"url":url,"source":source["name"],"category":source.get("category","general"),"summary":clean(get("description") or get("summary")),"published_at":get("pubDate") or get("date")})
    if rows: return rows
    atom="{http://www.w3.org/2005/Atom}"
    for node in root.iter(f"{atom}entry"):
        title=clean(node.findtext(f"{atom}title") or ""); link=node.find(f"{atom}link"); url=link.get("href","") if link is not None else ""
        if title and url: rows.append({"title":title,"url":url,"source":source["name"],"category":source.get("category","general"),"summary":clean(node.findtext(f"{atom}summary") or node.findtext(f"{atom}content") or ""),"published_at":node.findtext(f"{atom}published") or node.findtext(f"{atom}updated")})
    return rows
def collect(config,run_at,opener=urllib.request.urlopen):
    sources=[x for x in config.get("sources",[]) if x.get("enabled",True)]; settings=config.get("collection",{}); timeout=int(settings.get("timeout_seconds",10)); workers=max(1,min(int(settings.get("max_workers",6)),len(sources) or 1))
    def fetch(index,source):
        try:
            request=urllib.request.Request(source["url"],headers={"User-Agent":"daily-news-research/1.1 (+https://github.com/pink-mimi/skills)"})
            with opener(request,timeout=timeout) as response: rows=parse_feed(response.read(),source)
            return index,rows,None
        except Exception as exc: return index,[],{"source":source.get("name"),"url":source.get("url"),"error":f"{type(exc).__name__}: {exc}"}
    results=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(fetch,index,source) for index,source in enumerate(sources)]
        for future in as_completed(futures): results.append(future.result())
    results.sort(key=lambda value:value[0]); items=[]; errors=[]; successful=0
    for _,rows,error in results:
        items.extend(rows)
        if error: errors.append(error)
        else: successful+=1
    return {"fetched_at":run_at.isoformat(),"meta":{"configured_sources":len(sources),"successful_sources":successful,"failed_sources":len(errors)},"items":items,"errors":errors}
def build(raw, run_at, config):
    start,end=window(run_at,config); seen=set(); eligible=[]; review=[]
    for item in raw.get("items",[]):
        row=dict(item); row["url"]=str(row.get("url") or row.get("link") or "").strip(); row["category"]=str(row.get("category") or "general")
        published=parse_time(row.get("published_at")); key=re.sub(r"\W","",str(row.get("title","")).lower())
        if not key or not row["url"] or not published: review.append(row); continue
        if not start <= published < end or key in seen: continue
        seen.add(key); row["published_at"]=published.isoformat(); eligible.append(row)
    chosen=[]; counts={}; maximum=int(config["selection"]["maximum"])
    for row in eligible:
        category=row["category"]
        if counts.get(category,0)>=int(config["selection"]["maximum_per_category"]): continue
        chosen.append(row); counts[category]=counts.get(category,0)+1
        if len(chosen)>=maximum: break
    meta=raw.get("meta",{}); minimum_sources=int(config.get("collection",{}).get("minimum_successful_sources",0)); source_ok=not meta or int(meta.get("successful_sources",0))>=minimum_sources
    ready=len(chosen)>=int(config["selection"]["minimum"]) and len(counts)>=int(config["selection"]["minimum_categories"]) and source_ok
    risks=["发布前逐条打开原文复核"]
    if raw.get("errors"): risks.append(f"{len(raw['errors'])} 个来源采集失败，已保留错误记录")
    if not ready: risks.append("候选数量、类别覆盖或成功来源不足")
    return {"schema_version":1,"content_type":"daily-news","package_id":f"daily-news-{run_at.astimezone(BJT):%Y-%m-%d}","run_at":run_at.isoformat(),"status":"ready_for_human_review" if ready else "needs_review","window":{"start":start.isoformat(),"end":end.isoformat(),"boundary":"left_closed_right_open"},"collection":meta,"items":chosen,"sources":[{"name":x.get("source"),"url":x.get("url")} for x in chosen],"risks":risks,"review_items":review}
def target(root, run_at): return Path(root)/"daily-news"/run_at.astimezone(BJT).date().isoformat()
def archive_revision(out, names):
    existing=[out/name for name in names if (out/name).exists()]
    if not existing: return None
    base=out/"revisions"; number=1
    while (base/f"revision-{number:02d}").exists(): number+=1
    revision=base/f"revision-{number:02d}"; revision.mkdir(parents=True,exist_ok=False)
    for path in existing: shutil.copy2(path,revision/path.name)
    return revision
def main():
    p=argparse.ArgumentParser(); p.add_argument("command",choices=("collect","build","verify","all")); p.add_argument("--config",type=Path,default=ROOT/"assets/default-config.json"); p.add_argument("--input",type=Path); p.add_argument("--output-root",type=Path,default=Path.cwd()); p.add_argument("--run-at"); p.add_argument("--mode",choices=("stable","refresh","rebuild"),default="stable"); a=p.parse_args(); config=load(a.config); run_at=datetime.fromisoformat(a.run_at).astimezone(BJT) if a.run_at else datetime.now(BJT); out=target(a.output_root,run_at); raw_path=out/"raw-news.json"; package_path=out/"content-package.json"
    if a.mode=="rebuild" and not raw_path.exists(): raise SystemExit("rebuild 需要已有原始快照 raw-news.json")
    if a.mode=="refresh" and a.command in ("collect","build","all"): archive_revision(out,("raw-news.json","content-package.json"))
    if a.command in ("collect","all") and a.mode!="rebuild" and (a.mode=="refresh" or not raw_path.exists()): save(raw_path, load(a.input) if a.input else collect(config,run_at))
    if a.command in ("build","all"):
        if a.command=="build" and a.mode=="refresh" and a.input: save(raw_path,load(a.input))
        if not raw_path.exists() and a.input and a.mode!="rebuild": save(raw_path,load(a.input))
        if not raw_path.exists(): raise SystemExit("缺少原始快照 raw-news.json")
        package=build(load(raw_path),run_at,config); package["snapshot"]={"mode":a.mode,"file":raw_path.name,"sha256":hashlib.sha256(raw_path.read_bytes()).hexdigest()}; save(package_path,package)
    if a.command in ("verify","all"):
        path=package_path
        if not path.exists(): raise SystemExit("缺少 content-package.json")
        payload=load(path); errors=[]
        if payload.get("schema_version")!=1: errors.append("不支持的 schema_version")
        if payload.get("content_type")!="daily-news": errors.append("content_type 错误")
        if not payload.get("items"): errors.append("没有入选新闻")
        if errors: raise SystemExit("；".join(errors))
        print("OK")
if __name__=="__main__": main()
