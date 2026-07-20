from __future__ import annotations

import argparse, html, json, re, struct, zlib
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PALETTES={
 "news-blue":((239,246,255),(27,91,164),(242,140,69)),"clean-news":((250,252,255),(42,112,145),(71,184,173)),"warm-news":((252,247,238),(154,83,45),(224,158,72)),
 "open-coordinates":((247,244,235),(20,94,88),(242,126,46)),"code-archive":((244,240,230),(48,73,99),(213,148,43)),"field-notes":((248,240,221),(88,79,58),(211,112,58)),"clean-grid":((248,252,253),(43,142,163),(34,85,101))}

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def write(path,text): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text.rstrip()+"\n",encoding="utf-8")
def choose_theme(content_type,requested,config,run_at):
    names=config["themes"][content_type]
    if requested!="auto":
        if requested not in names: raise SystemExit(f"主题 {requested} 不适用于 {content_type}")
        return requested
    return names[run_at.date().toordinal()//7%len(names)]
def png(path,width,height,palette,variant=0):
    paper,dark,accent=palette; rows=[]
    for y in range(height):
        row=bytearray()
        for x in range(width):
            color=paper
            if (x+y+variant*37)%257<6: color=accent
            if x>width*0.70 and (x-width*.83)**2+(y-height*.48)**2<(min(width,height)*.21)**2: color=dark
            row.extend(color)
        rows.append(b"\x00"+bytes(row))
    raw=b"".join(rows)
    def chunk(kind,data): return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw,9))+chunk(b"IEND",b""))
def render_images(directory,theme,count):
    palette=PALETTES[theme]; png(directory/"合并封面.png",1283,383,palette); png(directory/"横版封面.png",900,383,palette,1); png(directory/"方形封面.png",383,383,palette,2)
    for index in range(1,count+1): png(directory/f"项目-{index:02d}.png",1200,675,palette,index+2)
    png(directory/"结尾图.png",1200,675,palette,count+3)
def news_article(payload):
    items=payload["items"]; lines=[f"# 昨天，这 {len(items)} 件事值得关注","","有些变化并不会在发生时发出很大的声响，却会沿着政策、技术和日常生活慢慢抵达每个人。本期把值得继续关注的事件放在一起：它们重要的不只是标题，而是接下来可能改变什么，以及我们应该留意哪些边界。"]
    for i,row in enumerate(items,1):
        lines += ["","---","",f"## {i:02d}｜{row.get('title','')}","",f"![{row.get('title','')}](images/项目-{i:02d}.png)","",row.get("summary") or "原文未提供摘要，请人工补充。","",f"**时间：** {row.get('published_at','待确认')}","",f"**来源：** [{row.get('source','原始来源')}]({row.get('url','')})"]
    lines += ["","---","","## 地图还在继续展开","","一条新闻真正产生影响，往往是在热度过去之后。你最关心其中哪一项变化？也欢迎把你认为值得追踪的线索留给我们，下期继续核对。","","![结尾图](images/结尾图.png)"]
    return "\n".join(lines)
def github_article(payload):
    items=payload["items"]; lines=[f"# 本周 GitHub 热门：{len(items)} 个值得关注的开源项目","","热榜给出的只是速度，真正值得留下的是方向。本周这些项目分别在整理信息、改造工作流和降低工具门槛上继续向前。把它们放在一起看，比起追逐同一种技术，更有意思的是开发者正在重新划分哪些工作应该交给软件。"]
    for i,row in enumerate(items,1):
        highlights="、".join(row.get("highlights") or []) or "用途明确、资料可查"
        lines += ["","---","",f"## {i:02d}｜{row.get('repo','')}：{row.get('description','')}","",f"![{row.get('repo','')}](images/项目-{i:02d}.png)","",f"**一句话说明：** {row.get('description','')}","",f"**值得注意：** {highlights}","",f"**适合谁：** {row.get('audience','待确认')}","",f"**使用门槛：** {row.get('install','待确认')}；平台：{row.get('platform','待确认')}","",f"**维护与许可证：** 最近提交 {row.get('last_commit','待确认')}；许可证 {row.get('license','未发现明确许可证')}","",f"**风险与限制：** {row.get('risks','发布前需要人工复核')}","",f"**官方地址：** [{row.get('repo','GitHub 仓库')}]({row.get('official_url','')})"]
    lines += ["","---","","## 最后留一个坐标","","开源项目的价值不只在 Star 数，而在它是否真的进入了某个人的工作和生活。这里面你最想试哪一个？也欢迎推荐你最近发现的项目，我们下周继续沿着线索往前走。","","![结尾图](images/结尾图.png)"]
    return "\n".join(lines)
def inline(text):
    links=[]
    def repl(match): links.append((match.group(1),match.group(2))); return f"@@LINK{len(links)-1}@@"
    escaped=html.escape(re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)",repl,text))
    escaped=re.sub(r"\*\*([^*]+)\*\*",r"<strong>\1</strong>",escaped)
    for i,(label,url) in enumerate(links): escaped=escaped.replace(f"@@LINK{i}@@",f'<a href="{html.escape(url)}" style="color:#176f88;text-decoration:none;overflow-wrap:anywhere">{html.escape(label)}</a>')
    return escaped
def html_page(markdown,theme,status):
    blocks=[]
    for part in markdown.splitlines():
        line=part.strip()
        if not line: continue
        if line.startswith("!["):
            match=re.match(r"!\[([^]]*)\]\(([^)]+)\)",line); blocks.append(f'<img src="{html.escape(match.group(2))}" alt="{html.escape(match.group(1))}" style="display:block;width:100%;height:auto;margin:22px 0;border-radius:12px">'); continue
        if line=="---": blocks.append('<div style="height:1px;background:#dce8e6;margin:30px 0"></div>'); continue
        if line.startswith("# "): blocks.append(f'<h1 style="font-size:28px;line-height:1.4;color:#173f46;margin:0 0 22px">{inline(line[2:])}</h1>'); continue
        if line.startswith("## "): blocks.append(f'<h2 style="font-size:22px;line-height:1.5;color:#164f4b;margin:28px 0 14px">{inline(line[3:])}</h2>'); continue
        blocks.append(f'<p style="font-size:16px;line-height:1.9;color:#334e52;margin:10px 0;overflow-wrap:anywhere">{inline(line)}</p>')
    notice='' if status=="ready_for_human_review" else '<div style="background:#fff3cd;padding:12px;margin-bottom:18px">输入内容仍需人工核验，请勿直接发布。</div>'
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>微信公众号审核包</title><body style="margin:0;background:#eef4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif"><div style="position:sticky;top:0;background:#12324a;padding:16px;text-align:center;z-index:9"><button id="copy-wechat" style="padding:12px 24px;border:0;border-radius:8px;color:#1760cf;font-size:17px;font-weight:700" onclick="copyWechat()">一键复制公众号正文</button><span id="copy-status" style="color:white;margin-left:14px">复制后粘贴到微信公众号编辑器</span></div><main style="max-width:720px;margin:24px auto;background:#fff;padding:28px;box-sizing:border-box">{notice}<section id="wechat-content">{''.join(blocks)}</section></main><script>async function copyWechat(){{const node=document.getElementById('wechat-content');try{{const blob=new Blob([node.innerHTML],{{type:'text/html'}});await navigator.clipboard.write([new ClipboardItem({{'text/html':blob,'text/plain':new Blob([node.innerText],{{type:'text/plain'}})}})]);document.getElementById('copy-status').textContent='复制成功';}}catch(e){{const range=document.createRange();range.selectNodeContents(node);const s=getSelection();s.removeAllRanges();s.addRange(range);document.execCommand('copy');document.getElementById('copy-status').textContent='已尝试复制，请粘贴检查';}}}}</script></body></html>'''
def output(root,payload):
    parts=payload["package_id"].split("-")
    return Path(root)/"wechat"/payload["content_type"]/("-".join(parts[-3:]))
def png_size(path):
    data=path.read_bytes(); return struct.unpack(">II",data[16:24]) if data[:8]==b"\x89PNG\r\n\x1a\n" else None
def main():
    p=argparse.ArgumentParser(); p.add_argument("command",choices=("build","verify","all")); p.add_argument("--input",type=Path,required=True); p.add_argument("--output-root",type=Path,default=Path.cwd()); p.add_argument("--config",type=Path,default=ROOT/"assets/default-config.json"); p.add_argument("--theme",default="auto"); a=p.parse_args(); payload=load(a.input); config=load(a.config)
    if payload.get("schema_version")!=1 or payload.get("content_type") not in ("daily-news","github-hot"): raise SystemExit("不支持的标准内容包")
    run_at=datetime.fromisoformat(payload["run_at"]); out=output(a.output_root,payload); theme=choose_theme(payload["content_type"],a.theme,config,run_at)
    if a.command in ("build","all"):
        article=news_article(payload) if payload["content_type"]=="daily-news" else github_article(payload); render_images(out/"images",theme,len(payload["items"])); write(out/"公众号成稿.md",article); write(out/"微信版.html",html_page(article,theme,payload["status"])); title=article.splitlines()[0].removeprefix("# "); write(out/"备选标题.txt","\n".join([title,f"未完地图｜{title}",f"这一次，我们关注 {len(payload['items'])} 个新坐标",f"值得继续追踪的 {len(payload['items'])} 条线索",f"本期观察：{len(payload['items'])} 个变化"])); write(out/"公众号摘要.txt",f"本期整理 {len(payload['items'])} 条经过筛选的内容，保留来源、限制和人工审核提示，帮助普通读者快速理解值得继续关注的变化。"); write(out/"运行报告.md",f"# 运行报告\n\n- content_type: `{payload['content_type']}`\n- input_status: `{payload['status']}`\n- theme: `{theme}`\n- 发布：仅生成审核包，未上传、未发布。")
    if a.command in ("verify","all"):
        errors=[]
        for name in ("公众号成稿.md","微信版.html","备选标题.txt","公众号摘要.txt","运行报告.md"):
            if not (out/name).exists(): errors.append(f"缺少 {name}")
        for name,size in (("合并封面.png",(1283,383)),("横版封面.png",(900,383)),("方形封面.png",(383,383))):
            path=out/"images"/name
            if not path.exists() or png_size(path)!=size: errors.append(f"图片异常 {name}")
        page=(out/"微信版.html").read_text(encoding="utf-8") if (out/"微信版.html").exists() else ""
        for token in ('id="copy-wechat"','id="wechat-content"','ClipboardItem'):
            if token not in page: errors.append(f"HTML 缺少 {token}")
        if errors: raise SystemExit("；".join(errors))
        print("OK")
if __name__=="__main__": main()
