from __future__ import annotations

import argparse, json, re, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BJT=timezone(timedelta(hours=8)); ROOT=Path(__file__).resolve().parents[1]
def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def save(path,value): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
def window(run_at,config): end=run_at.astimezone(BJT); return end-timedelta(days=int(config["window"]["duration_days"])),end
def collect(run_at):
    request=urllib.request.Request("https://github.com/trending?since=weekly",headers={"User-Agent":"github-hot-research/1.0"})
    try: page=urllib.request.urlopen(request,timeout=20).read().decode("utf-8","replace")
    except Exception as exc: return {"meta":{"rate_limited":True,"error":str(exc)},"items":[]}
    repos=[]
    for repo in re.findall(r'<h2[^>]*>[\s\S]*?href="/([^"?#]+/[^"?#]+)"',page):
        name=re.sub(r"\s","",repo)
        if name not in repos: repos.append(name)
    return {"meta":{"rate_limited":False,"fetched_at":run_at.isoformat()},"items":[{"repo":x,"official_url":f"https://github.com/{x}"} for x in repos[:20]]}
def valid(row):
    fields=("repo","description","license","last_commit","platform","install","audience","risks","category")
    return all(str(row.get(x) or "").strip() and not str(row.get(x)).startswith(("请","待")) for x in fields) and str(row.get("license")).upper() not in {"NOASSERTION","UNKNOWN","OTHER"}
def score(row): return float(row.get("weekly_stars") or 0)*1.5+min(float(row.get("stars") or 0),50000)/1000+(20 if row.get("latest_release") else 0)
def history(root,date,limit):
    base=Path(root)/"github-hot"; result=set()
    if not base.exists(): return result
    for path in sorted((x for x in base.glob("*/content-package.json") if x.parent.name<date),reverse=True)[:limit]:
        try: result.update(str(x.get("repo")) for x in load(path).get("items",[]) if x.get("repo"))
        except (OSError,json.JSONDecodeError): pass
    return result
def build(raw,run_at,config,output_root):
    start,end=window(run_at,config); rows=[]
    for value in raw.get("items",[]):
        row=dict(value); row["eligible"]=valid(row); row["score"]=score(row); row.setdefault("official_url",f"https://github.com/{row.get('repo','')}"); rows.append(row)
    past=history(output_root,run_at.astimezone(BJT).date().isoformat(),int(config["selection"]["history_lookback_weeks"])); selected=[]; ai=0; categories={}
    for row in sorted(rows,key=lambda x:x["score"],reverse=True):
        if not row["eligible"] or row.get("repo") in past and not row.get("significant_change"): continue
        if row.get("ai_related") and ai>=int(config["selection"]["maximum_ai"]): continue
        category=str(row.get("category"));
        if categories.get(category,0)>=int(config["selection"]["maximum_per_category"]): continue
        selected.append(row); categories[category]=categories.get(category,0)+1; ai+=int(bool(row.get("ai_related")))
        if len(selected)>=int(config["selection"]["maximum"]): break
    discovery=config["discovery"]; ready=not raw.get("meta",{}).get("rate_limited") and int(discovery["candidate_minimum"])<=len(rows)<=int(discovery["candidate_maximum"]) and sum(not x.get("ai_related") for x in rows)>=int(discovery["minimum_non_ai_candidates"]) and len(selected)>=int(config["selection"]["minimum"])
    return {"schema_version":1,"content_type":"github-hot","package_id":f"github-hot-{run_at.astimezone(BJT):%Y-%m-%d}","run_at":run_at.isoformat(),"status":"ready_for_human_review" if ready else "needs_review","window":{"start":start.isoformat(),"end":end.isoformat(),"boundary":"left_closed_right_open"},"items":selected,"sources":[{"name":x.get("repo"),"url":x.get("official_url")} for x in selected],"risks":["发布前复核 Star、许可证和最近维护状态"]+(["候选深度、非 AI 数量或核验完整度不足"] if not ready else []),"candidates":rows,"history_excluded":sorted(past)}
def target(root,run_at): return Path(root)/"github-hot"/run_at.astimezone(BJT).date().isoformat()
def main():
    p=argparse.ArgumentParser(); p.add_argument("command",choices=("collect","build","verify","all")); p.add_argument("--config",type=Path,default=ROOT/"assets/default-config.json"); p.add_argument("--input",type=Path); p.add_argument("--output-root",type=Path,default=Path.cwd()); p.add_argument("--run-at"); a=p.parse_args(); config=load(a.config); run_at=datetime.fromisoformat(a.run_at).astimezone(BJT) if a.run_at else datetime.now(BJT); out=target(a.output_root,run_at); raw_path=out/"raw-candidates.json"
    if a.command in ("collect","all"): save(raw_path,load(a.input) if a.input else collect(run_at))
    if a.command in ("build","all"): save(out/"content-package.json",build(load(a.input) if a.input and not raw_path.exists() else load(raw_path),run_at,config,a.output_root))
    if a.command in ("verify","all"):
        path=out/"content-package.json"
        if not path.exists(): raise SystemExit("缺少 content-package.json")
        payload=load(path); errors=[]
        if payload.get("schema_version")!=1: errors.append("不支持的 schema_version")
        if payload.get("content_type")!="github-hot": errors.append("content_type 错误")
        if not payload.get("items"): errors.append("没有入选项目")
        if errors: raise SystemExit("；".join(errors))
        print("OK")
if __name__=="__main__": main()
