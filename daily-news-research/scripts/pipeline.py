from __future__ import annotations

import hashlib
import re
import time
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from difflib import SequenceMatcher

import safe_fetch
import source_adapters


SUCCESS_STATUSES={"success_with_items","success_no_items"}


def _parse_time(value):
    if not value: return None
    try:
        parsed=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def filter_time_window(rows,start,end):
    accepted=[]; rejected=[]
    for value in rows:
        row=dict(value); published=_parse_time(row.get("published_at")); updated=_parse_time(row.get("updated_at"))
        basis="published" if published else "updated" if updated else "unknown"; moment=published or updated
        row["time_basis"]=basis
        if moment is None:
            row["exclusion_reason"]="invalid_time"; rejected.append(row)
        elif start<=moment.astimezone(start.tzinfo)<end:
            row["published_at"]=(published or moment).isoformat(); accepted.append(row)
        else:
            row["exclusion_reason"]="outside_time_window"; rejected.append(row)
    return accepted,rejected


NATIONAL_MARKERS=("全国","多省","多地","国务院","国家","长江中下游","京津冀","全国人大")
LOCAL_MARKERS=("县","区","镇","街道","当地")
MAJOR_LOCAL_MARKERS=("重大","特大","暴雨","洪水","地震","事故","公共安全","多人","伤亡","预警","响应")


def classify_scope(row):
    category=str(row.get("category") or "").lower(); text=" ".join(str(row.get(key) or "") for key in ("title","summary"))
    if category in {"world","international","国际"}: return "international","category"
    if any(marker in text for marker in NATIONAL_MARKERS): return "national","national_marker"
    if any(marker in text for marker in LOCAL_MARKERS): return "local","local_marker"
    return "national","default_domestic"


def local_is_newsworthy(row):
    text=" ".join(str(row.get(key) or "") for key in ("title","summary"))
    return any(marker in text for marker in MAJOR_LOCAL_MARKERS)


def international_is_relevant(row):
    reason=str(row.get("china_relevance_reason") or "").strip()
    pathways=("贸易","出口","进口","能源","油价","供应链","签证","出行","中国公民","人民币","金融市场","芯片","科技限制","公共卫生","外交")
    return len(reason)>=10 and any(marker in reason for marker in pathways)


def _action_domain(text):
    domains={
        "flood":("防汛","洪水","暴雨","汛情","降雨"),
        "accident":("事故","火灾","坍塌","伤亡","通报"),
        "policy":("政策","办法","条例","规定","部署"),
        "economy":("经济","收入","消费","投资","价格"),
    }
    return next((name for name,markers in domains.items() if any(marker in text for marker in markers)),"general")


def _normalized(value): return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]","",str(value or "")).lower()


def _same_event(left,right):
    left_text=_normalized(str(left.get("title") or "")+str(left.get("summary") or "")); right_text=_normalized(str(right.get("title") or "")+str(right.get("summary") or ""))
    if _action_domain(left_text)!=_action_domain(right_text): return False,0.0
    left_day=str(left.get("published_at") or "")[:10]; right_day=str(right.get("published_at") or "")[:10]
    if left_day and right_day and left_day!=right_day: return False,0.0
    ratio=SequenceMatcher(None,left_text,right_text).ratio()
    shared={left_text[index:index+4] for index in range(max(0,len(left_text)-3))}&{right_text[index:index+4] for index in range(max(0,len(right_text)-3))}
    confidence=max(ratio,0.75 if len(shared)>=2 else 0.0)
    return confidence>=0.7,confidence


def cluster_events(rows):
    clusters=[]
    for value in rows:
        row=dict(value); matched=None; confidence=1.0
        for cluster in clusters:
            same,score=_same_event(cluster["sources"][0],row)
            if same: matched=cluster; confidence=score; break
        if matched is None:
            seed=_normalized(str(row.get("title") or "")+str(row.get("published_at") or "")[:10]+_action_domain(str(row.get("title") or "")+str(row.get("summary") or "")))
            matched={"event_id":"evt-"+hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12],"sources":[],"cluster_confidence":1.0,"independent_organizations":[]}
            clusters.append(matched)
        else:
            matched["cluster_confidence"]=min(matched["cluster_confidence"],round(confidence,3))
        matched["sources"].append(row)
        organization=str(row.get("syndicated_from") or row.get("organization") or row.get("source") or "未知")
        if organization not in matched["independent_organizations"]: matched["independent_organizations"].append(organization)
    return clusters


OFFICIAL_ROUTES={
    "politics":[("中国政府网",["gov.cn"])],
    "finance":[("中国人民银行",["pbc.gov.cn"]),("国家统计局",["stats.gov.cn"]),("财政部",["mof.gov.cn"]),("国家发展改革委",["ndrc.gov.cn"]),("海关总署",["customs.gov.cn"])],
    "education":[("教育部",["moe.gov.cn"])],
    "health":[("国家卫生健康委",["nhc.gov.cn"]),("中国疾控中心",["chinacdc.cn"])],
    "tech":[("工业和信息化部",["miit.gov.cn"]),("科技部",["most.gov.cn"]),("中央网信办",["cac.gov.cn"])],
    "public-safety":[("应急管理部",["mem.gov.cn"]),("中国气象局",["cma.gov.cn"]),("交通运输部",["mot.gov.cn"])],
    "legal":[("最高人民法院",["court.gov.cn"]),("最高人民检察院",["spp.gov.cn"]),("全国人大",["npc.gov.cn"])],
    "world":[("外交部",["fmprc.gov.cn"])],
}


def official_routes(category):
    category=str(category or "general").lower()
    aliases={"财经":"finance","科技":"tech","公共安全":"public-safety","时政":"politics","国际":"world","社会":"public-safety","民生":"health"}
    key=aliases.get(category,category)
    values=OFFICIAL_ROUTES.get(key,[("中国政府网",["gov.cn"])])
    return [{"organization":organization,"domains":domains} for organization,domains in values]


def build_verification_queue(clusters,config):
    maximum=int(config.get("verification",{}).get("maximum_queue",15))
    impact_score={"major":3,"medium":2,"limited":1}
    def score(cluster):
        lead=cluster.get("sources",[{}])[0]
        return (-impact_score.get(str(lead.get("impact_level") or "medium"),2),-len(cluster.get("independent_organizations",[])),cluster.get("event_id",""))
    queue=[]
    for cluster in sorted(clusters,key=score)[:maximum]:
        sources=cluster.get("sources",[]); lead=sources[0] if sources else {}; primary=[row for row in sources if row.get("source_role")=="primary"]
        status="verified" if primary else "unverified"
        queue.append({
            "event_id":cluster.get("event_id"),"title":lead.get("title",""),"category":lead.get("category","general"),
            "cluster_confidence":cluster.get("cluster_confidence",1.0),"discovery_sources":[row for row in sources if row.get("source_role")!="primary"],
            "primary_sources":primary,"recommended_official_sources":official_routes(lead.get("category")),
            "verification_status":status,"verified_at":lead.get("verified_at","") if primary else "",
            "verification_notes":[] if primary else ["尚未找到可核对核心事实的官方原文"],
        })
    return queue


def _editorial_complete(row,required):
    return all(row.get(field) and (not isinstance(row.get(field),list) or bool(row[field])) for field in required)


def select_verified_items(rows,config,collection_meta,run_at):
    selection=config.get("selection",{}); health=config.get("health",{})
    maximum=int(selection.get("maximum",8)); max_per_category=int(selection.get("maximum_per_category",2))
    max_scope={"local":int(selection.get("maximum_local",1)),"international":int(selection.get("maximum_international",1))}
    required=selection.get("required_editorial_fields",[])
    impact_score={"major":3,"medium":2,"limited":1}
    ordered=sorted((dict(row) for row in rows),key=lambda row:(-impact_score.get(row.get("impact_level","medium"),2),str(row.get("event_id",""))))
    chosen=[]; excluded=[]; categories={}; scopes={"local":0,"international":0}; risks=[]
    saw_unverified=False; stale_dynamic=False; incomplete=False
    for row in ordered:
        category=str(row.get("category") or "general"); scope=str(row.get("geographic_scope") or "national")
        if row.get("verification_status")!="verified": saw_unverified=True
        if not _editorial_complete(row,required): incomplete=True
        if row.get("recheck_before_publish"):
            verified=_parse_time(row.get("verified_at"))
            if verified is None or (run_at-verified.astimezone(run_at.tzinfo)).total_seconds()>6*3600: stale_dynamic=True
        exception_reason=str(row.get("quota_exception_reason") or "").strip()
        exception=bool(row.get("quota_exception")) and bool(exception_reason)
        if categories.get(category,0)>=max_per_category and not exception:
            row["exclusion_reason"]="category_quota"; excluded.append(row); continue
        if scope in max_scope and scopes[scope]>=max_scope[scope] and not exception:
            row["exclusion_reason"]="scope_quota"; excluded.append(row); continue
        if scope=="international" and not international_is_relevant(row):
            row["exclusion_reason"]="missing_china_relevance"; excluded.append(row); continue
        if len(chosen)>=maximum:
            row["exclusion_reason"]="selection_limit"; excluded.append(row); continue
        chosen.append(row); categories[category]=categories.get(category,0)+1
        if scope in scopes: scopes[scope]+=1
    if saw_unverified: risks.append("存在未核验新闻，不能作为确定性正文发布")
    if stale_dynamic: risks.append("动态事实距离上次核验过久，发布前需要重新核验")
    if incomplete: risks.append("部分新闻缺少必要编辑字段")
    organizations=int(collection_meta.get("successful_organizations",0))
    if organizations<int(health.get("minimum_successful_organizations",0)): risks.append("成功采集机构数量不足")
    if len(chosen)<int(selection.get("minimum",5)) or len(categories)<int(selection.get("minimum_categories",4)): risks.append("入选数量或类别覆盖不足")
    ready=not risks
    return {"status":"ready_for_human_review" if ready else "needs_review","items":chosen,"excluded":excluded,"risks":risks,"category_counts":categories,"scope_counts":scopes}


def collect_sources(config,run_at,fetcher=None,categories=None):
    sources=[source for source in config.get("sources",[]) if source.get("enabled",True) and ((source.get("category") in categories) if categories else source.get("daily_default",True))]
    settings=config.get("collection",{})
    maximum=int(settings.get("maximum_candidates",50))
    workers=max(1,min(int(settings.get("max_workers",6)),len(sources) or 1))
    timeout=int(settings.get("timeout_seconds",10))
    retry_count=max(0,int(settings.get("retry_count",0)))
    fetcher=fetcher or (lambda source:safe_fetch.fetch(source,timeout=timeout))

    def work(index,source):
        started=time.monotonic()
        attempts=0
        while True:
            attempts+=1; result=fetcher(source)
            if result.status not in {"timeout","fetch_error","rate_limited"} or attempts>retry_count: break
        status=result.status; items=[]; error=result.error
        if status=="success":
            parsed=source_adapters.parse(result.payload,source)
            status=parsed.status; items=parsed.items; error=parsed.error
        health={
            "name":source.get("name"),"organization":source.get("organization",source.get("name")),
            "url":source.get("url"),"tier":source.get("tier"),"role":source.get("role"),
            "status":status,"attempts":attempts,"elapsed_ms":round((time.monotonic()-started)*1000),"candidate_count":len(items),
        }
        if error: health["error"]=error
        return index,items,health

    results=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(work,index,source) for index,source in enumerate(sources)]
        for future in as_completed(futures): results.append(future.result())
    results.sort(key=lambda row:row[0])
    items=[]; health=[]; source_rows=[]
    for _,rows,state in results:
        health.append(state); source_rows.append(rows)
    position=0
    while len(items)<maximum:
        added=False
        for rows in source_rows:
            if position<len(rows):
                items.append(rows[position]); added=True
                if len(items)>=maximum: break
        if not added: break
        position+=1
    successful=[row for row in health if row["status"] in SUCCESS_STATUSES]
    organizations={row["organization"] for row in successful}
    errors=[{"source":row["name"],"url":row["url"],"status":row["status"],"error":row.get("error","")} for row in health if row["status"] not in SUCCESS_STATUSES]
    return {
        "fetched_at":run_at.isoformat(),
        "meta":{
            "configured_sources":len(sources),"successful_sources":len(successful),
            "successful_organizations":len(organizations),"failed_sources":len(errors),
            "candidate_limit_reached":sum(row["candidate_count"] for row in health)>maximum,
        },
        "items":items,"errors":errors,"source_health":health,
    }
