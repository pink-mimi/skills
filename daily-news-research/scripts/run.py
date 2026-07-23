from __future__ import annotations

import argparse, hashlib, html, json, re, shutil, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parent))
import pipeline as research

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

def collect_modern(config,run_at,categories=None):
    return research.collect_sources(config,run_at,categories=categories)
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

def merge_editorial_enrichment(raw, editorial):
    """Merge agent-verified editorial fields without replacing collection evidence."""
    allowed={"what_happened","why_it_matters","reader_action","editor_note","keywords","summary","verification_status","verified_at","primary_sources","background_sources","verification_notes","recheck_before_publish","china_relevance","china_relevance_reason","impact_level"}
    enriched={}
    for item in editorial.get("items",[]):
        keys=(str(item.get("event_id") or "").strip(),str(item.get("url") or "").strip(),str(item.get("title") or "").strip())
        for key in keys:
            if key: enriched[key]=item
    merged=dict(raw); merged["items"]=[]
    for source in raw.get("items",[]):
        row=dict(source)
        match=next((enriched.get(str(row.get(key) or "").strip()) for key in ("event_id","url","title") if enriched.get(str(row.get(key) or "").strip())),None)
        if match:
            for key in allowed:
                if key in match: row[key]=match[key]
        merged["items"].append(row)
    if editorial.get("editorial"): merged["editorial"]=dict(editorial["editorial"])
    return merged

def build_editorial_workbench(queue):
    required=("what_happened","why_it_matters","reader_action","editor_note","keywords")
    items=[]
    for value in queue:
        row={key:value.get(key) for key in ("event_id","title","url","category","verification_status","primary_sources","discovery_sources")}
        row.update({field:value.get(field) or ([] if field=="keywords" else "") for field in required})
        row["missing_fields"]=[field for field in required if not row.get(field)]
        items.append(row)
    return {"schema_version":1,"status":"awaiting_editorial_enrichment","instructions":"逐条打开原文核验，补齐编辑字段后使用 --editorial-input 重新 build。","items":items}
def build(raw, run_at, config):
    start,end=window(run_at,config); seen=set(); eligible=[]; review=[]
    for item in raw.get("items",[]):
        row=dict(item); row["url"]=str(row.get("url") or row.get("link") or "").strip(); row["category"]=str(row.get("category") or "general")
        published=parse_time(row.get("published_at")); key=re.sub(r"\W","",str(row.get("title","")).lower())
        if not key or not row["url"] or not published: review.append(row); continue
        if not start <= published < end or key in seen: continue
        if config.get("selection",{}).get("scope") in {"domestic","china-national"} and not domestic_relevant(row):
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
def target(root, run_at, fixture=False):
    namespace="test-fixtures/daily-news" if fixture else "daily-news"
    return Path(root)/namespace/run_at.astimezone(BJT).date().isoformat()
def source_report(raw,package):
    meta=raw.get("meta",{}); configured=int(meta.get("configured_sources",0)); successful=int(meta.get("successful_sources",0)); rate=f"{successful/configured:.1%}" if configured else "离线输入，未统计"
    source_counts={}; category_counts={}
    for row in raw.get("items",[]): source_counts[row.get("source","未知")]=source_counts.get(row.get("source","未知"),0)+1; category_counts[row.get("category","general")]=category_counts.get(row.get("category","general"),0)+1
    lines=["# 新闻来源与采集报告","",f"- 采集成功率：**{rate}**",f"- 配置来源：{configured}",f"- 成功来源：{successful}",f"- 失败来源：{int(meta.get('failed_sources',len(raw.get('errors',[]))))}",f"- 原始候选：{len(raw.get('items',[]))}",f"- 最终入选：{len(package.get('items',[]))}","","## 来源平台","","| 平台 | 候选数 |","|---|---:|"]
    lines += [f"| {name} | {count} |" for name,count in sorted(source_counts.items())]; lines += ["","## 类别分布","","| 类别 | 候选数 | 占比 |","|---|---:|---:|"]; total=max(1,len(raw.get("items",[]))); lines += [f"| {name} | {count} | {count/total:.1%} |" for name,count in sorted(category_counts.items())]
    if raw.get("errors"): lines += ["","## 失败来源","",*[f"- {x.get('source')}：{x.get('error')}" for x in raw["errors"]]]
    lines += ["","## 边界说明","","采集成功率只表示本次配置来源的请求结果，不代表新闻覆盖率或事实准确率达到 100%。发布前仍须打开原文进行人工核验。"]
    return "\n".join(lines)

def tiered_report(raw,package,queue,excluded):
    health=raw.get("source_health",[]); meta=raw.get("meta",{}); total=max(1,len(package.get("items",[])))
    tier_counts={}; organizations=set()
    for row in health:
        tier_counts[row.get("tier","未标记")]=tier_counts.get(row.get("tier","未标记"),0)+1
        if row.get("status") in research.SUCCESS_STATUSES: organizations.add(row.get("organization"))
    primary=sum(1 for row in package.get("items",[]) if row.get("primary_sources") or row.get("source_role")=="primary")
    time_counts=meta.get("time_window_counts",{})
    lines=[source_report(raw,package),"","## 时间窗口诊断","",f"- 窗口内：{int(time_counts.get('in_window',0))} 条",f"- 晚于窗口：{int(time_counts.get('too_new',0))} 条",f"- 早于窗口：{int(time_counts.get('too_old',0))} 条",f"- 时间无效：{int(time_counts.get('invalid_time',0))} 条","","## 来源阶梯","",*[f"- 第 {tier} 阶梯：{count} 个配置来源" for tier,count in sorted(tier_counts.items(),key=lambda value:str(value[0]))],"","## 机构多样性","",f"- 成功机构：{int(meta.get('successful_organizations',len(organizations)))}",f"- 核验队列：{len(queue)} 个事件",f"- 排除记录：{len(excluded)} 条","","## 官方原文覆盖率","",f"- 入选新闻：{primary}/{len(package.get('items',[]))}（{primary/total:.1%}）"]
    return "\n".join(lines)

def prepare_research(raw,run_at,config):
    start,end=window(run_at,config); accepted,rejected=research.filter_time_window(raw.get("items",[]),start,end)
    enriched=[]
    for value in accepted:
        row=dict(value); scope,_=research.classify_scope(row); row["geographic_scope"]=row.get("geographic_scope",scope)
        row["verification_status"]=row.get("verification_status") or ("verified" if row.get("source_role")=="primary" else "unverified")
        enriched.append(row)
    clusters=research.cluster_events(enriched); queue=research.build_verification_queue(clusters,config)
    by_event={entry["event_id"]:entry for entry in queue}; candidates=[]
    for cluster in clusters:
        lead=dict(cluster["sources"][0]); verification=by_event.get(cluster["event_id"],{})
        existing_status=lead.get("verification_status")
        preserved_verified=existing_status=="verified" and bool(lead.get("primary_sources"))
        preserved_partial=existing_status=="partial" and bool(lead.get("verified_at")) and bool(lead.get("background_sources") or lead.get("discovery_sources"))
        lead.update({
            "event_id":cluster["event_id"],
            "verification_status":existing_status if (preserved_verified or preserved_partial) else verification.get("verification_status","unverified"),
            "primary_sources":lead.get("primary_sources") or verification.get("primary_sources",[]),
            "discovery_sources":lead.get("discovery_sources") or verification.get("discovery_sources",[]),
        })
        candidates.append(lead)
    selected=research.select_verified_items(candidates,config,raw.get("meta",{}),run_at)
    package=build({**raw,"items":selected["items"]},run_at,config)
    package["status"]=selected["status"]
    package["risks"]=list(dict.fromkeys(package.get("risks",[])+selected["risks"]))
    package["review_items"]=package.get("review_items",[])+rejected
    return package,queue,rejected+selected["excluded"]

def update_health_history(path,health,run_at):
    history=load(path) if path.exists() else {"schema_version":1,"sources":{}}
    for row in health:
        key=f"{row.get('organization','未知')}|{row.get('url','')}"; previous=history["sources"].get(key,{"runs":0,"successes":0,"failures":0,"consecutive_failures":0,"total_elapsed_ms":0})
        success=row.get("status") in research.SUCCESS_STATUSES
        previous["runs"]+=1; previous["successes"]+=int(success); previous["failures"]+=int(not success); previous["consecutive_failures"]=0 if success else previous["consecutive_failures"]+1; previous["total_elapsed_ms"]+=int(row.get("elapsed_ms",0)); previous["average_elapsed_ms"]=round(previous["total_elapsed_ms"]/previous["runs"]); previous["last_status"]=row.get("status"); previous["last_checked_at"]=run_at.isoformat()
        if success: previous["last_success_at"]=run_at.isoformat()
        if row.get("status") in {"success_with_items","success_no_items"}: previous["last_parse_success_at"]=run_at.isoformat()
        history["sources"][key]=previous
    history["updated_at"]=run_at.isoformat(); save(path,history); return history
def archive_revision(out, names):
    existing=[out/name for name in names if (out/name).exists()]
    if not existing: return None
    base=out/"revisions"; number=1
    while (base/f"revision-{number:02d}").exists(): number+=1
    revision=base/f"revision-{number:02d}"; revision.mkdir(parents=True,exist_ok=False)
    for path in existing: shutil.copy2(path,revision/path.name)
    return revision
def main():
    p=argparse.ArgumentParser(); p.add_argument("command",choices=("collect","build","verify","all","query","sources")); p.add_argument("--config",type=Path,default=ROOT/"assets/default-config.json"); p.add_argument("--input",type=Path,help="仅供 query 读取离线查询数据"); p.add_argument("--editorial-input",type=Path,help="经原文核验后补齐的编辑字段 JSON，仅供 build/all"); p.add_argument("--fixture-input",type=Path,help="仅供测试，输出隔离到 test-fixtures"); p.add_argument("--output-root",type=Path,default=Path.cwd()); p.add_argument("--run-at"); p.add_argument("--mode",choices=("stable","refresh","rebuild"),default="stable"); p.add_argument("--category",default="hot"); p.add_argument("--keyword"); p.add_argument("--limit",type=int,default=10); p.add_argument("--detail",type=int,default=100); p.add_argument("--format",dest="output_format",choices=("text","json"),default="text"); a=p.parse_args(); config=load(a.config); run_at=datetime.fromisoformat(a.run_at).astimezone(BJT) if a.run_at else datetime.now(BJT)
    if a.command!="query" and a.input:
        raise SystemExit("--input 仅供 query；正式 collect/build/all 不接受外部输入，请使用联网 refresh 或已有快照 rebuild")
    if a.fixture_input and a.command in ("query","sources","verify"):
        raise SystemExit("--fixture-input 仅供 collect/build/all/rebuild 测试")
    if a.fixture_input and a.mode=="refresh":
        raise SystemExit("refresh 必须联网采集，不能与 --fixture-input 同时使用")
    if a.editorial_input and a.command not in ("build","all"):
        raise SystemExit("--editorial-input 仅供 build/all 使用")
    fixture=bool(a.fixture_input); out=target(a.output_root,run_at,fixture=fixture); raw_path=out/"raw-news.json"; package_path=out/"content-package.json"
    if a.command=="sources":
        catalog=source_catalog(config); print(json.dumps(catalog,ensure_ascii=False,indent=2) if a.output_format=="json" else "\n".join(f"{category}: {', '.join(x['name'] for x in sources)}" for category,sources in catalog.items())); return
    if a.command=="query":
        catalog=source_catalog(config)
        if a.category not in catalog: raise SystemExit(f"不支持的类别：{a.category}")
        raw=load(a.input) if a.input else collect_modern(config,run_at,categories=None if a.category=="hot" else {a.category}); rows=query_items(raw.get("items",raw if isinstance(raw,list) else []),a.category,a.keyword,max(1,a.limit),a.detail); print(json.dumps(rows,ensure_ascii=False,indent=2) if a.output_format=="json" else format_query(rows)); return
    if a.mode=="rebuild" and not raw_path.exists(): raise SystemExit("rebuild 需要已有原始快照 raw-news.json")
    if a.mode=="refresh" and a.command in ("collect","build","all"): archive_revision(out,("raw-news.json","content-package.json"))
    if a.command in ("collect","all") and a.mode!="rebuild" and (a.mode=="refresh" or not raw_path.exists()): save(raw_path, load(a.fixture_input) if a.fixture_input else collect_modern(config,run_at))
    if a.command in ("build","all"):
        if not raw_path.exists() and a.fixture_input and a.mode!="rebuild": save(raw_path,load(a.fixture_input))
        if not raw_path.exists(): raise SystemExit("缺少原始快照 raw-news.json")
        raw=load(raw_path)
        if a.editorial_input:
            raw=merge_editorial_enrichment(raw,load(a.editorial_input))
        package,queue,excluded=prepare_research(raw,run_at,config); package["snapshot"]={"mode":a.mode,"file":raw_path.name,"sha256":hashlib.sha256(raw_path.read_bytes()).hexdigest(),"refresh_recommended":a.mode=="rebuild" or bool(raw.get("errors"))}
        package["execution"]={"kind":"test_fixture" if fixture else "production","external_input_used":fixture}
        if fixture:
            package["status"]="needs_review"
            package["risks"].append("本次使用测试 fixture，不得作为正式新闻审核包")
        if a.mode=="rebuild": package["risks"].append("本次为离线重建，未重新联网核验，发布前建议 refresh")
        save(package_path,package); save(out/"verification-queue.json",queue); save(out/"editorial-workbench.json",build_editorial_workbench(queue)); save(out/"source-health.json",{"meta":raw.get("meta",{}),"sources":raw.get("source_health",[])}); save(out/"excluded-news.json",excluded); write(out/"source-report.md",tiered_report(raw,package,queue,excluded)); history_root=Path(a.output_root)/("test-fixtures/daily-news" if fixture else "daily-news"); update_health_history(history_root/"source-health-history.json",raw.get("source_health",[]),run_at)
    if a.command in ("verify","all"):
        path=package_path
        if not path.exists(): raise SystemExit("缺少 content-package.json")
        payload=load(path); errors=[]
        if payload.get("schema_version")!=1: errors.append("不支持的 schema_version")
        if payload.get("content_type")!="daily-news": errors.append("content_type 错误")
        if not payload.get("items"): errors.append("没有入选新闻")
        for required in ("source-report.md","verification-queue.json","editorial-workbench.json","source-health.json","excluded-news.json"):
            if not (out/required).exists(): errors.append(f"缺少 {required}")
        if errors: raise SystemExit("；".join(errors))
        print("OK")
if __name__=="__main__": main()
