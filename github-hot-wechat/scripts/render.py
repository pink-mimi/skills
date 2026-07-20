from __future__ import annotations
import html, math, re, struct, zlib
from datetime import datetime
from pathlib import Path
from core import BJT, Project

THEMES={
 "open-coordinates":{"accent":"#f28a36","dark":"#154f4b","soft":"#eef8f5","paper":"#f7f3e8"},
 "code-archive":{"accent":"#d49a3a","dark":"#30435a","soft":"#f0f3f6","paper":"#f5f1e8"},
 "field-notes":{"accent":"#c96f3b","dark":"#4f4a38","soft":"#f7f0df","paper":"#fbf5e8"},
 "clean-grid":{"accent":"#2b8ea3","dark":"#204b5a","soft":"#eef8fa","paper":"#ffffff"}}

def theme_for(run_at: datetime, requested: str) -> str:
    if requested != "auto":
        if requested not in THEMES: raise ValueError(f"unknown theme: {requested}")
        return requested
    names=list(THEMES); return names[run_at.astimezone(BJT).date().toordinal()//7%len(names)]

def article_markdown(items: list[Project], run_at: datetime) -> str:
    count=len(items)
    intro="这周 GitHub 热榜最值得注意的，不是某一种技术又多了几个项目，而是软件正在从不同方向重新安排人与工具的分工。有人把设计、学习和文档交给更主动的助手，也有人继续打磨通知、制图和本地工具。把这些项目放在一起看，热度只是入口，真正值得追踪的是它们准备替我们解决什么问题。"
    lines=[f"# 本周 GitHub 热门：{count} 个值得关注的开源项目","",f"> 未完地图｜GitHub 热门｜核验于 {run_at.astimezone(BJT):%Y-%m-%d %H:%M}（北京时间）","",intro]
    for i,p in enumerate(items,1):
        lines += ["","---","",f"## {i:02d}｜{p.repo}：{p.description}","",f"![{p.repo} 主题插图](images/项目-{i:02d}.png)","",f"**一句话说明：** {p.description}","","### 它解决什么问题","",f"它把“{p.description}”做成了一个可以检查、部署或继续修改的开源项目，重点在于让具体工作少一些重复步骤。","","### 值得注意的亮点",""]
        lines += [f"- {x}" for x in (p.highlights[:3] or ["官方资料完整","近期仍有维护记录"])]
        lines += ["",f"**适合谁：** {p.audience}","",f"**使用门槛：** {p.install}；平台为 {p.platform}。","",f"**维护与许可证：** 核验时 {p.stars:,} Star；最近提交 {p.last_commit}；最新版本 {p.latest_release or '未发现明确 Release'}；许可证 {p.license}。","",f"**先看限制：** {p.risks}","",f"**官方地址：** [{p.official_url}]({p.official_url})"]
    lines += ["","---","","## 最后：工具越来越主动，我们更需要选择权","","![结尾插图](images/结尾图.png)","","开源的价值从来不只是“免费”。它让我们有机会看见工具如何工作，也保留修改、拒绝和重新决定的权利。当软件越来越主动，这种权利反而更重要。","",f"今天这 {count} 个项目里，你最想试哪一个？或者，你最近遇到了哪个值得下期继续追踪的开源项目？欢迎留言，把下一张地图的坐标交给我们。","","> 本文仅作开源项目介绍。动态数据会变化，许可证、隐私与安全风险请在实际使用前再次核对。",""]
    return "\n".join(lines)

def _inline(value: str, accent: str) -> str:
    links=[]
    def stash(m):
        label,url=m.groups(); links.append(f'<a href="{html.escape(url,quote=True)}" style="color:{accent};text-decoration:none;word-break:break-all;">{html.escape(label)}</a>'); return f"@@LINK{len(links)-1}@@"
    escaped=html.escape(re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)",stash,value)); escaped=re.sub(r"\*\*(.+?)\*\*",r"<strong>\1</strong>",escaped)
    for i,link in enumerate(links): escaped=escaped.replace(f"@@LINK{i}@@",link)
    return escaped

def wechat_html(markdown: str, theme_name: str) -> str:
    t=THEMES[theme_name]; blocks=[]; in_list=False
    for raw in markdown.splitlines():
        line=raw.strip()
        if not line:
            if in_list: blocks.append("</ul>"); in_list=False
            continue
        image=re.match(r"!\[([^]]*)\]\(([^)]+)\)",line)
        if line=="---": blocks.append(f'<div style="height:1px;background:{t["accent"]}33;margin:34px 0;"></div>')
        elif image: blocks.append(f'<img src="{html.escape(image.group(2))}" alt="{html.escape(image.group(1))}" style="display:block;width:100%;height:auto;margin:18px auto 24px;border-radius:12px;">')
        elif line.startswith("# "): blocks.append(f'<h1 style="color:{t["dark"]};font-size:30px;line-height:1.4;">{_inline(line[2:],t["accent"])}</h1>')
        elif line.startswith("## "): blocks.append(f'<h2 style="margin:34px 0 16px;color:{t["dark"]};font-size:25px;line-height:1.45;">{_inline(line[3:],t["accent"])}</h2>')
        elif line.startswith("### "): blocks.append(f'<h3 style="margin:24px 0 8px;color:{t["accent"]};font-size:18px;">{_inline(line[4:],t["accent"])}</h3>')
        elif line.startswith("> "): blocks.append(f'<blockquote style="margin:18px 0;padding:13px 16px;border-left:4px solid {t["accent"]};background:{t["soft"]};line-height:1.8;">{_inline(line[2:],t["accent"])}</blockquote>')
        elif line.startswith("- "):
            if not in_list: blocks.append('<ul style="padding-left:24px;line-height:1.9;">'); in_list=True
            blocks.append(f'<li>{_inline(line[2:],t["accent"])}</li>')
        else: blocks.append(f'<p style="color:#304d49;font-size:16px;line-height:1.9;text-align:justify;">{_inline(line,t["accent"])}</p>')
    if in_list: blocks.append("</ul>")
    body="\n".join(blocks)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GitHub 热门公众号审核稿</title></head><body style="margin:0;background:{t['soft']};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;"><div id="copy-toolbar" style="position:sticky;top:0;z-index:20;background:{t['dark']};padding:15px 20px;"><button id="copy-wechat" type="button" style="border:0;border-radius:8px;background:#fff;color:{t['dark']};padding:13px 24px;font-size:17px;font-weight:700;cursor:pointer;">复制公众号正文</button><span id="copy-status" style="margin-left:16px;color:#fff;">复制后直接粘贴到微信公众号编辑器</span></div><div style="max-width:760px;margin:28px auto;padding:18px;background:#fff;border-radius:18px;"><img src="images/合并封面.png" alt="合并封面预览" style="display:block;width:100%;height:auto;border-radius:12px;"><main id="wechat-content" style="box-sizing:border-box;max-width:720px;margin:0 auto;padding:0 20px 42px;background:#fff;overflow-wrap:anywhere;">{body}</main></div><script>const button=document.getElementById('copy-wechat'),status=document.getElementById('copy-status'),content=document.getElementById('wechat-content');function selectionCopy(){{const s=window.getSelection(),r=document.createRange();r.selectNodeContents(content);s.removeAllRanges();s.addRange(r);const ok=document.execCommand('copy');s.removeAllRanges();return ok;}}async function clipboardItemCopy(){{const h=new Blob([content.innerHTML],{{type:'text/html'}}),p=new Blob([content.innerText],{{type:'text/plain'}});await navigator.clipboard.write([new ClipboardItem({{'text/html':h,'text/plain':p}})]);}}button.addEventListener('click',async()=>{{try{{if(!selectionCopy())await clipboardItemCopy();status.textContent='已复制正文';}}catch(e){{status.textContent='复制失败，请手动选择正文';}}}});</script></body></html>'''

def _png(path: Path,width:int,height:int,colors:tuple[str,str,str],seed:int=0)->None:
    def rgb(v): v=v.lstrip("#"); return tuple(int(v[i:i+2],16) for i in (0,2,4))
    a,b,c=map(rgb,colors); rows=bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            grid=((x+seed*17)//48+(y+seed*11)//48)%9==0; route=abs((y-height//2)-int(42*math.sin((x+seed*31)/85)))<3; dot=(x-width*(55+seed%20)//100)**2+(y-height//2)**2<100
            color=c if dot else b if route else tuple((a[i]*4+b[i])//5 for i in range(3)) if grid else a; rows.extend(color)
    def chunk(k,d): return struct.pack(">I",len(d))+k+d+struct.pack(">I",zlib.crc32(k+d)&0xffffffff)
    header=struct.pack(">IIBBBBB",width,height,8,2,0,0,0); path.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",header)+chunk(b"IDAT",zlib.compress(bytes(rows),9))+chunk(b"IEND",b""))

def _crop(source:Path,target:Path,box):
    try:
        from PIL import Image
        with Image.open(source) as im: im.crop(box).save(target,optimize=True)
    except ImportError: _png(target,box[2]-box[0],box[3]-box[1],("#f7f3e8","#4d9fd1","#f28a36"))

def fallback_images(directory:Path,theme_name:str,title:str,count:int)->None:
    directory.mkdir(parents=True,exist_ok=True); t=THEMES[theme_name]
    _png(directory/"合并封面.png",1283,383,(t["paper"],t["dark"],t["accent"])); _crop(directory/"合并封面.png",directory/"横版封面.png",(0,0,900,383)); _crop(directory/"合并封面.png",directory/"方形封面.png",(900,0,1283,383))
    for i in range(1,count+1): _png(directory/f"项目-{i:02d}.png",1200,675,(t["paper"],t["dark"],t["accent"]),i)
    _png(directory/"结尾图.png",1200,675,(t["paper"],t["dark"],t["accent"]),99)

def png_size(path:Path)->tuple[int,int]:
    data=path.read_bytes()[:24]
    if data[:8]!=b"\x89PNG\r\n\x1a\n": raise ValueError("not PNG")
    return struct.unpack(">II",data[16:24])
