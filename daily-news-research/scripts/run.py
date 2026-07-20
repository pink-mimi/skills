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
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(value.rstrip()+"\n",encoding="utf-8")
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
def parse_web(payload,source):
    text=payload.decode("utf-8","replace"); rows=[]; seen=set()
    for url,label in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',text,re.I):
        title=clean(label)
        if len(title)<8 or title in seen or not url.startswith("http"): continue
        seen.add(title); rows.append({"title":title,"url":url,"source":source["name"],"category":source["category"],"summary":"","published_at":""})
        if len(rows)>=50: break
    return rows
def collect(config,run_at,opener=urllib.request.urlopen,categories=None):
    sources=[x for x in config.get("sources",[]) if x.get("enabled",True) and ((x.get("category") in categories) if categories else x.get("daily_default",True))]; settings=config.get("collection",{}); timeout=int(settings.get("timeout_seconds",10)); workers=max(1,min(int(settings.get("max_workers",6)),len(sources) or 1))
    def fetch(index,source):
        try:
            request=urllib.request.Request(source["url"],headers={"User-Agent":"daily-news-research/1.1 (+https://github.com/pink-mimi/skills)"})
            with opener(request,timeout=timeout) as response:
                payload=response.read(); rows=parse_web(payload,source) if source.get("type","rss")=="web" else parse_feed(payload,source)
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
def query_items(items,category="hot",keyword=None,limit=10,detail=100):
    rows=[]; needle=(keyword or "").casefold()
    for value in items:
        row=dict(value); row["category"]=str(row.get("category") or "general"); summary=str(row.get("summary") or "")
        if category!="hot" and row["category"]!=category: continue
        if needle and needle not in (str(row.get("title") or "")+" "+summary).casefold(): continue
        if detail==0: row["summary"]=""
        elif detail>0 and len(summary)>detail: row["summary"]=summary[:detail]+"..."
        rows.append(row)
        if len(rows)>=limit: break
    return rows
def source_catalog(config):
    result={"hot":[]}
    for source in config.get("sources",[]):
        if not source.get("enabled",True): continue
        info={key:source.get(key) for key in ("name","url","type","daily_default")}; result.setdefault(source.get("category","general"),[]).append(info)
        if source.get("daily_default",True): result["hot"].append(info)
    return result
def format_query(rows):
    lines=[]
    for index,row in enumerate(rows,1):
        lines += [f"{index}. {row.get('title','')}",f"   来源：{row.get('source','未知')}｜类别：{row.get('category','general')}",f"   链接：{row.get('url') or row.get('link','')}"]
        if row.get("summary"): lines.append(f"   摘要：{row['summary']}")
    return "\n".join(lines) if lines else "没有找到符合条件的新闻。"
def domestic_relevant(row):
    if row.get("domestic_relevance") is True: return True
    if row.get("domestic_relevance") is False: return False
    category=str(row.get("category") or "").strip().lower()
    domestic_categories={"politics","finance","society","tech","technology","public-safety","culture","education","时政","财经","社会","科技","公共安全","文化","教育","民生"}
    if category in domestic_categories: return True
    text=" ".join(str(row.get(key) or "") for key in ("title","summary","source"))
    markers=("中国","国内","我国","北京","上海","天津","重庆","香港","澳门","台湾","国务院","国家统计局","水利部","应急管理部","教育部","工信部","国家卫健委","新华社","人民网","央视")
    return any(marker in text for marker in markers)
def editorial_complete(row,required):
    return all(row.get(field) and (not isinstance(row.get(field),list) or len(row[field])>0) for field in required)
def build(raw, run_at, config):
    start,end=window(run_at,config); seen=set(); eligible=[]; review=[]
    for item in raw.get("items",[]):
        row=dict(item); row["url"]=str(row.get("url") or row.get("link") or "").strip(); row["category"]=str(row.get("category") or "general")
        published=parse_time(row.get("published_at")); key=re.sub(r"\W","",str(row.get("title","")).lower())
        if not key or not row["url"] or not published: review.append(row); continue
        if not start <= published < end or key in seen: continue
        if config.get("selection",{}).get("scope")=="domestic" and not domestic_relevant(row):
            row["review_reason"]="与国内日报定位缺少直接关联"
            review.append(row); continue
        seen.add(key); row["published_at"]=published.isoformat(); eligible.append(row)
    chosen=[]; counts={}; maximum=int(config["selection"]["maximum"])
    for row in eligible:
        category=row["category"]
        if counts.get(category,0)>=int(config["selection"]["maximum_per_category"]): continue
        chosen.append(row); counts[category]=counts.get(category,0)+1
        if len(chosen)>=maximum: break
    meta=raw.get("meta",{}); minimum_sources=int(config.get("collection",{}).get("minimum_successful_sources",0)); source_ok=not meta or int(meta.get("successful_sources",0))>=minimum_sources
    required=config.get("selection",{}).get("required_editorial_fields",[])
    incomplete=[row for row in chosen if not editorial_complete(row,required)]
    base_ready=len(chosen)>=int(config["selection"]["minimum"]) and len(counts)>=int(config["selection"]["minimum_categories"]) and source_ok
    ready=base_ready and not incomplete
    risks=["发布前逐条打开原文复核"]
    if raw.get("errors"): risks.append(f"{len(raw['errors'])} 个来源采集失败，已保留错误记录")
    if not base_ready: risks.append("候选数量、类别覆盖或成功来源不足")
    if incomplete: risks.append(f"{len(incomplete)} 条新闻缺少发生了什么、为什么重要、读者行动或提醒等深度字段")
    return {"schema_version":1,"content_type":"daily-news","package_id":f"daily-news-{run_at.astimezone(BJT):%Y-%m-%d}","run_at":run_at.isoformat(),"status":"ready_for_human_review" if ready else "needs_review","window":{"start":start.isoformat(),"end":end.isoformat(),"boundary":"left_closed_right_open"},"collection":meta,"editorial":raw.get("editorial",{}),"items":chosen,"sources":[{"name":x.get("source"),"url":x.get("url")} for x in chosen],"risks":risks,"review_items":review}
def target(root, run_at): return Path(root)/"daily-news"/run_at.astimezone(BJT).date().isoformat()
def source_report(raw,package):
    meta=raw.get("meta",{}); configured=int(meta.get("configured_sources",0)); successful=int(meta.get("successful_sources",0)); rate=f"{successful/configured:.1%}" if configured else "离线输入，未统计"
    source_counts={}; category_counts={}
    for row in raw.get("items",[]): source_counts[row.get("source","未知")]=source_counts.get(row.get("source","未知"),0)+1; category_counts[row.get("category","general")]=category_counts.get(row.get("category","general"),0)+1
    lines=["# 新闻来源与采集报告","",f"- 采集成功率：**{rate}**",f"- 配置来源：{configured}",f"- 成功来源：{successful}",f"- 失败来源：{int(meta.get('failed_sources',len(raw.get('errors',[]))))}",f"- 原始候选：{len(raw.get('items',[]))}",f"- 最终入选：{len(package.get('items',[]))}","","## 来源平台","","| 平台 | 候选数 |","|---|---:|"]
    lines += [f"| {name} | {count} |" for name,count in sorted(source_counts.items())]; lines += ["","## 类别分布","","| 类别 | 候选数 | 占比 |","|---|---:|---:|"]; total=max(1,len(raw.get("items",[]))); lines += [f"| {name} | {count} | {count/total:.1%} |" for name,count in sorted(category_counts.items())]
    if raw.get("errors"): lines += ["","## 失败来源","",*[f"- {x.get('source')}：{x.get('error')}" for x in raw["errors"]]]
    lines += ["","## 边界说明","","采集成功率只表示本次配置来源的请求结果，不代表新闻覆盖率或事实准确率达到 100%。发布前仍须打开原文进行人工核验。"]
    return "\n".join(lines)
def archive_revision(out, names):
    existing=[out/name for name in names if (out/name).exists()]
    if not existing: return None
    base=out/"revisions"; number=1
    while (base/f"revision-{number:02d}").exists(): number+=1
    revision=base/f"revision-{number:02d}"; revision.mkdir(parents=True,exist_ok=False)
    for path in existing: shutil.copy2(path,revision/path.name)
    return revision
def main():
    p=argparse.ArgumentParser(); p.add_argument("command",choices=("collect","build","verify","all","query","sources")); p.add_argument("--config",type=Path,default=ROOT/"assets/default-config.json"); p.add_argument("--input",type=Path); p.add_argument("--output-root",type=Path,default=Path.cwd()); p.add_argument("--run-at"); p.add_argument("--mode",choices=("stable","refresh","rebuild"),default="stable"); p.add_argument("--category",default="hot"); p.add_argument("--keyword"); p.add_argument("--limit",type=int,default=10); p.add_argument("--detail",type=int,default=100); p.add_argument("--format",dest="output_format",choices=("text","json"),default="text"); a=p.parse_args(); config=load(a.config); run_at=datetime.fromisoformat(a.run_at).astimezone(BJT) if a.run_at else datetime.now(BJT); out=target(a.output_root,run_at); raw_path=out/"raw-news.json"; package_path=out/"content-package.json"
    if a.command=="sources":
        catalog=source_catalog(config); print(json.dumps(catalog,ensure_ascii=False,indent=2) if a.output_format=="json" else "\n".join(f"{category}: {', '.join(x['name'] for x in sources)}" for category,sources in catalog.items())); return
    if a.command=="query":
        catalog=source_catalog(config)
        if a.category not in catalog: raise SystemExit(f"不支持的类别：{a.category}")
        raw=load(a.input) if a.input else collect(config,run_at,categories=None if a.category=="hot" else {a.category}); rows=query_items(raw.get("items",raw if isinstance(raw,list) else []),a.category,a.keyword,max(1,a.limit),a.detail); print(json.dumps(rows,ensure_ascii=False,indent=2) if a.output_format=="json" else format_query(rows)); return
    if a.mode=="rebuild" and not raw_path.exists(): raise SystemExit("rebuild 需要已有原始快照 raw-news.json")
    if a.mode=="refresh" and a.command in ("collect","build","all"): archive_revision(out,("raw-news.json","content-package.json"))
    if a.command in ("collect","all") and a.mode!="rebuild" and (a.mode=="refresh" or not raw_path.exists()): save(raw_path, load(a.input) if a.input else collect(config,run_at))
    if a.command in ("build","all"):
        if a.command=="build" and a.mode=="refresh" and a.input: save(raw_path,load(a.input))
        if not raw_path.exists() and a.input and a.mode!="rebuild": save(raw_path,load(a.input))
        if not raw_path.exists(): raise SystemExit("缺少原始快照 raw-news.json")
        raw=load(raw_path); package=build(raw,run_at,config); package["snapshot"]={"mode":a.mode,"file":raw_path.name,"sha256":hashlib.sha256(raw_path.read_bytes()).hexdigest()}; save(package_path,package); write(out/"source-report.md",source_report(raw,package))
    if a.command in ("verify","all"):
        path=package_path
        if not path.exists(): raise SystemExit("缺少 content-package.json")
        payload=load(path); errors=[]
        if payload.get("schema_version")!=1: errors.append("不支持的 schema_version")
        if payload.get("content_type")!="daily-news": errors.append("content_type 错误")
        if not payload.get("items"): errors.append("没有入选新闻")
        if not (out/"source-report.md").exists(): errors.append("缺少 source-report.md")
        if errors: raise SystemExit("；".join(errors))
        print("OK")
if __name__=="__main__": main()
