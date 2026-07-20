from __future__ import annotations
import argparse, json, re, sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from collectors import collect, read_fixture
from core import BJT, load_config, normalize, package_status, project_dicts, scan_history, select_projects, window_for, write_json
from render import THEMES, article_markdown, fallback_images, png_size, theme_for, wechat_html

SKILL=Path(__file__).resolve().parents[1]; DEFAULT_CONFIG=SKILL/"assets"/"default-config.json"
REQUIRED=["raw-candidates.json","candidates.json","selected.json","执行信息.md","候选项目核验表.md","入选理由.md","公众号成稿.md","微信版.html","备选标题.txt","公众号摘要.txt","来源清单.md","淘汰项目及原因.md","风险和待人工确认项.md","人工审核清单.md","运行报告.md"]

def target_for(root:Path,run_at:datetime)->Path: return root/"github-hot"/run_at.astimezone(BJT).date().isoformat()
def write(path:Path,text:str): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text.rstrip()+"\n",encoding="utf-8")

def command_collect(args,config,run_at):
    target=target_for(args.output_root,run_at); payload=read_fixture(args.input) if args.input else collect(config,run_at); write_json(target/"raw-candidates.json",payload); print(target/"raw-candidates.json")

def _table(projects):
    lines=["# 候选项目核验表","","| 项目 | Star | 本周新增 | AI | 分类 | 许可证 | 最近提交 | 状态 |","|---|---:|---:|---|---|---|---|---|"]
    lines += [f"| [{p.repo}]({p.official_url}) | {p.stars:,} | {p.weekly_stars:,} | {'是' if p.ai_related else '否'} | {p.category} | {p.license or '未明确'} | {p.last_commit} | {'合格' if p.eligible else p.rejection_reason} |" for p in projects]
    return "\n".join(lines)

def _titles(n): return [f"本周 GitHub 热门：{n} 个值得关注的开源项目",f"AI 占了热榜，也没占满世界：本周 {n} 个开源项目",f"这周 GitHub，有 {n} 个项目值得多看一眼",f"从助手到本地工具：本周 GitHub 开源观察",f"本周开源坐标：{n} 个正在改变工具分工的项目"]

def command_build(args,config,run_at):
    target=target_for(args.output_root,run_at); raw=json.loads((target/"raw-candidates.json").read_text(encoding="utf-8")); projects=[normalize(x) for x in raw.get("items",[])]; history=scan_history(args.output_root,target.name,int(config["selection"]["history_lookback_weeks"])); selected=select_projects(projects,config,history); status=package_status(projects,selected,bool(raw.get("meta",{}).get("rate_limited")),config); theme=theme_for(run_at,args.theme)
    image_mode="template_fallback"
    if args.image_mode=="image2": image_mode="image2_requested_pending"
    fallback_images(target/"images",theme,"AI 占了热榜，也没占满世界",len(selected))
    start,end=window_for(run_at,config); meta={"status":status,"window_start":start.isoformat(),"window_end":end.isoformat(),"verified_at":run_at.isoformat(),"theme":theme,"image_mode":image_mode,"candidate_count":len(projects),"selected_count":len(selected),"history_excluded":sorted(history)}
    write_json(target/"candidates.json",{"meta":meta,"items":project_dicts(projects)}); write_json(target/"selected.json",{"meta":meta,"items":project_dicts(selected)})
    article=article_markdown(selected,run_at); write(target/"公众号成稿.md",article); write(target/"微信版.html",wechat_html(article,theme)); write(target/"备选标题.txt","\n".join(_titles(len(selected)))); write(target/"公众号摘要.txt",f"本周精选 {len(selected)} 个 GitHub 开源项目，覆盖不同工具方向，并说明安装门槛、许可证、维护状态与使用风险。")
    write(target/"候选项目核验表.md",_table(projects)); write(target/"执行信息.md",f"# 执行信息\n\n- 状态：`{status}`\n- 时间窗：{start.isoformat()}—{end.isoformat()}\n- 主题：`{theme}`\n- 图片模式：`{image_mode}`\n- 候选：{len(projects)}\n- 入选：{len(selected)}\n- 发布：仅供人工审核，不自动发布")
    write(target/"入选理由.md","# 入选理由\n\n"+"\n".join(f"- **{p.repo}**：普通读者用途明确，资料完整，综合评分 {p.score:.1f}。" for p in selected))
    rejected=[p for p in projects if p.repo not in {x.repo for x in selected}]; write(target/"淘汰项目及原因.md","# 淘汰项目及原因\n\n"+"\n".join(f"- **{p.repo}**：{p.rejection_reason or ('往期已介绍' if p.repo in history else '综合评分或多样性配额未进入前列')}。" for p in rejected))
    write(target/"来源清单.md","# 来源清单\n\n"+"\n".join(f"- [{p.repo}]({p.official_url})：仓库主页、README、LICENSE、Release、Commit、Issues 与安全政策需人工逐项复核。" for p in projects))
    issues=[]
    if raw.get("meta",{}).get("rate_limited"): issues.append("- GitHub API 发生限流，必须补充核验。")
    issues += [f"- {p.repo}：{p.rejection_reason}" for p in projects if not p.eligible]
    write(target/"风险和待人工确认项.md","# 风险和待人工确认项\n\n"+("\n".join(issues) if issues else "- 未发现阻止生成审核稿的自动检查问题；仍须人工打开官方来源复核。"))
    write(target/"人工审核清单.md","# 人工审核清单\n\n- [ ] 打开每个仓库、README、LICENSE、Release 与最近提交。\n- [ ] 复核 Star、版本、日期和许可证。\n- [ ] 检查横版与方形封面裁切。\n- [ ] 点击复制按钮并粘贴到公众号编辑器预览。\n- [ ] 最终发布必须由人工完成。")
    write(target/"运行报告.md",f"# 运行报告\n\n- status: `{status}`\n- theme: `{theme}`\n- image_mode: `{image_mode}`\n- candidates: {len(projects)}\n- selected: {len(selected)}\n- rate_limited: {bool(raw.get('meta',{}).get('rate_limited'))}\n- 未上传、未发布。")
    print(target)

def command_verify(args,config,run_at)->int:
    target=target_for(args.output_root,run_at); errors=[f"缺少 {name}" for name in REQUIRED if not (target/name).exists()]
    if errors: print("; ".join(errors)); return 1
    selected=json.loads((target/"selected.json").read_text(encoding="utf-8")); html=(target/"微信版.html").read_text(encoding="utf-8"); article=(target/"公众号成稿.md").read_text(encoding="utf-8")
    if selected["meta"]["status"]!="ready_for_human_review": errors.append("status is needs_review")
    if selected["meta"].get("image_mode")=="image2_requested_pending": errors.append("Image 2 图片尚未替换")
    for token in ('id="copy-wechat"','id="wechat-content"','ClipboardItem','overflow-wrap:anywhere'):
        if token not in html: errors.append(f"HTML 缺少 {token}")
    intro=article.split("---",1)[0].strip().splitlines()[-1].strip()
    if not 100<=len(re.sub(r"\s","",intro))<=180: errors.append("开头不是 100—180 字")
    images={"合并封面.png":(1283,383),"横版封面.png":(900,383),"方形封面.png":(383,383),"结尾图.png":(1200,675)}
    for i in range(1,len(selected["items"])+1): images[f"项目-{i:02d}.png"]=(1200,675)
    for name,size in images.items():
        path=target/"images"/name
        if not path.exists() or png_size(path)!=size: errors.append(f"图片异常 {name}")
        elif path.stat().st_size>=int(config["images"]["maximum_bytes"]): errors.append(f"图片超过限制 {name}")
    if errors: print("; ".join(errors)); return 2
    print("OK"); return 0

def main():
    parser=argparse.ArgumentParser(description="Weekly GitHub hot projects to WeChat review package"); parser.add_argument("command",choices=("collect","build","verify","all")); parser.add_argument("--config",type=Path,default=DEFAULT_CONFIG); parser.add_argument("--output-root",type=Path,default=Path.cwd()); parser.add_argument("--input",type=Path); parser.add_argument("--run-at"); parser.add_argument("--theme",default="auto",choices=("auto",*THEMES)); parser.add_argument("--image-mode",default="auto",choices=("auto","image2","template")); args=parser.parse_args(); config=load_config(args.config); run_at=datetime.fromisoformat(args.run_at).astimezone(BJT) if args.run_at else datetime.now(BJT)
    if args.command in ("collect","all"): command_collect(args,config,run_at)
    if args.command in ("build","all"): command_build(args,config,run_at)
    if args.command in ("verify","all"): raise SystemExit(command_verify(args,config,run_at))
if __name__=="__main__": main()
