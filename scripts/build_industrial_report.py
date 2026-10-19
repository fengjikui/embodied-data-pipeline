"""Build a standalone Chinese report from repository Markdown, no web assets."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import hashlib
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    ('17-industrial-screw-workflow.md', '任务与数据闭环', '先把“拧螺丝”定义成可测的完整任务。',
     '到工位、取料、双手对位、接触、拧紧、质量复核需要不同观测与验收。数据管线连接采集、训练与失败回流。'),
    ('18-models-objectives-inference.md', '模型如何训练与推理', '标签、损失与控制接口决定模型怎样使用数据。',
     'BC/ACT学习示范动作；token VLA、flow与diffusion采用不同动作生成目标；PPO从奖励学习。推理输出参考，再由控制器执行。'),
    ('19-whole-body-coordination.md', '行走、导航、操作与协同', '四项能力是功能划分，不是必须训练四个网络。',
     '先固定工位，再比较分层策略与全身控制器。共享的关节权限、坐标、时序、接触和负载使上下身不能直接拼接。'),
    ('20-industrial-pipeline-roadmap.md', '工业管线与验收差距', '生产可靠性需要服务与真实环境验收。',
     '当前原型已有本地数据工程。生产还需对象存储、目录事务、作业恢复、权限、备份、多传感接入与工位质量闭环。'),
    ('21-ecosystem-data-hardware.md', '厂商、数据、模型与采购', '格式可读、能够训练、实机可用是三个不同层次。',
     '优先目标G1自采与匹配手型的公开数据；跨本体数据用于迁移对照。采购比较简单夹持/固定工具和灵巧手，按接口与工艺验证。'),
    ('22-command-learning-lab.md', '逐条命令实操', '每关都能看到输入、输出和代码。',
     '合成原始数据、转换与版本、BC训练/预测、异步流对齐、PPO、官方ACT以及真实G1候选路线分开讲解。'),
    ('23-supervisor-script.md', '汇报讲稿与主管问答', '用7段讲清目标、系统、证据与需要协调的条件。',
     '先讲业务闭环，再讲训练与控制，最后展示实测和下一步工位、硬件、算力与运维要求。')
]
CHAPTERS = {name: f'chapter-{i+1}' for i, (name, *_rest) in enumerate(DOCS)}


def link_target(url):
    if url.startswith(('https://', 'http://', '#')):
        return url
    name = url.split('#')[0].split('/')[-1]
    if name in CHAPTERS:
        return '#' + CHAPTERS[name]
    if url.startswith('../'):
        target = url[3:]
    else:
        target = 'docs/' + url
    return 'https://github.com/fengjikui/embodied-data-pipeline/blob/main/' + target


def inline(text):
    slots = []
    def store(value):
        slots.append(value)
        return '\x00' + str(len(slots)-1) + '\x00'
    text = re.sub(r'`([^`]+)`', lambda m: store('<code>' + html.escape(m[1]) + '</code>'), text)
    text = re.sub(r'\[([^\]]+)\]\(([^\s)]+)\)',
                  lambda m: store('<a href="' + html.escape(link_target(m[2]), quote=True) + '">' + html.escape(m[1]) + '</a>'), text)
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    for i, value in enumerate(slots):
        text = text.replace('\x00' + str(i) + '\x00', value)
    return text


def render_markdown(source):
    """Small safe renderer for the explicit subset used by this report's docs."""
    lines = source.splitlines(); output = []; i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip(): i += 1; continue
        if line.startswith('```'):
            language = line[3:].strip(); block = []; i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                block.append(lines[i]); i += 1
            output.append('<pre><span class="code-label">' + html.escape(language or 'text') + '</span><code>' + html.escape('\n'.join(block)) + '</code></pre>')
            i += 1; continue
        heading = re.match(r'^(#{1,6}) (.+)', line)
        if heading:
            level = min(6, len(heading[1])+1)
            if len(heading[1]) != 1:
                output.append(f'<h{level}>' + inline(heading[2]) + f'</h{level}>')
            i += 1; continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', c) for c in cells): rows.append(cells)
                i += 1
            header = '<thead><tr>' + ''.join('<th scope="col">'+inline(c)+'</th>' for c in rows[0]) + '</tr></thead>'
            body = '<tbody>' + ''.join('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in row)+'</tr>' for row in rows[1:])+'</tbody>'
            output.append('<div class="table-wrap" tabindex="0" role="region" aria-label="技术比较表，可横向滚动"><table>'+header+body+'</table></div>')
            continue
        if re.match(r'^(\d+\. |[-*] )', line):
            ordered = bool(re.match(r'^\d+\. ', line)); tag = 'ol' if ordered else 'ul'; items=[]
            pattern = r'^\d+\. ' if ordered else r'^[-*] '
            while i < len(lines) and re.match(pattern, lines[i]):
                items.append('<li>'+inline(re.sub(pattern,'',lines[i]))+'</li>'); i += 1
            output.append('<'+tag+'>'+''.join(items)+'</'+tag+'>'); continue
        paragraph = [line]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#|```|\||\d+\. |[-*] )', lines[i]):
            paragraph.append(lines[i]); i += 1
        output.append('<p>'+inline('\n'.join(paragraph))+'</p>')
    return '\n'.join(output)


STYLE = r'''
:root{--paper:oklch(0.98 0.008 95);--ink:oklch(0.29 0.025 160);--muted:oklch(0.48 0.018 160);--accent:oklch(0.49 0.095 45);--wash:oklch(0.94 0.016 145);--line:oklch(0.84 0.012 145)}
*{box-sizing:border-box}html{scroll-behavior:auto}body{margin:0;background:var(--paper);color:var(--ink);font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif;line-height:1.85;font-size:17px}a{color:var(--accent);text-underline-offset:4px}button,select{font:inherit;color:inherit}button,select{border:1px solid var(--line);border-radius:4px;background:var(--paper);padding:8px 14px;cursor:pointer}button[aria-pressed=true]{background:var(--ink);color:var(--paper);border-color:var(--ink)}:focus-visible{outline:3px solid var(--accent);outline-offset:4px}.skip{position:absolute;top:-100px}.skip:focus{top:8px;left:8px;background:var(--paper);padding:8px;z-index:10}
.layout{display:grid;grid-template-columns:240px minmax(0,1fr);max-width:1450px;margin:auto}.sidebar{position:sticky;top:0;height:100vh;padding:34px 22px 26px;border-right:1px solid var(--line);overflow:auto}.brand{font-size:15px;font-weight:700;letter-spacing:.04em;margin-bottom:26px}.sidebar nav a{display:block;text-decoration:none;color:var(--muted);padding:9px 0;font-size:14px}.sidebar nav a:hover{color:var(--accent)}.sidebar .small{font-size:13px;margin-top:28px;color:var(--muted)}main{min-width:0;padding:58px clamp(24px,5vw,76px) 80px}.meta{color:var(--accent);font-size:14px;letter-spacing:.08em}h1{font-size:clamp(34px,4.2vw,59px);letter-spacing:-.04em;line-height:1.25;margin:20px 0 24px;max-width:16ch}h2{font-size:29px;line-height:1.45;letter-spacing:-.02em;margin:12px 0 20px}h3{font-size:24px;line-height:1.5;margin:40px 0 14px}h4{font-size:20px;margin-top:26px}p,li{max-width:76ch;overflow-wrap:anywhere}p{margin:16px 0}.lead{font-size:21px;line-height:1.75;max-width:46ch}.boundary{background:var(--wash);padding:20px 24px;margin:24px 0 32px;font-size:16px}.toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:28px 0}.toolbar label{font-size:14px;color:var(--muted)}.chapter{border-top:1px solid var(--line);padding-top:36px;margin-top:56px;scroll-margin-top:20px}.chapter-number{font-size:14px;color:var(--accent);letter-spacing:.1em}.takeaway{font-size:24px;font-weight:600;line-height:1.55;max-width:42ch}.chapter details{margin-top:24px;border-top:1px solid var(--line);padding-top:16px}summary{cursor:pointer;font-size:16px;font-weight:600;line-height:1.8}summary:hover{color:var(--accent)}.details-body{padding-top:12px}.table-wrap{overflow-x:auto;max-width:100%;margin:24px 0}table{border-collapse:collapse;width:100%;min-width:620px;font-size:14px;line-height:1.7}th,td{padding:13px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:var(--wash);font-weight:650}td:first-child{font-weight:550}code{font-family:ui-monospace,"SFMono-Regular",Consolas,monospace;font-size:.85em;overflow-wrap:anywhere}pre{background:var(--ink);color:var(--paper);padding:22px 24px;overflow:auto;border-radius:3px;line-height:1.65;max-width:100%;font-size:14px}pre code{font-size:inherit;white-space:pre;overflow-wrap:normal}.code-label{display:block;color:oklch(0.83 0.018 145);font-size:12px;margin-bottom:8px}.flow{list-style:none;padding:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0;border:1px solid var(--line);margin:28px 0}.flow li{padding:20px 18px;border-bottom:1px solid var(--line);border-right:1px solid var(--line);font-size:15px}.flow b{display:block;font-size:18px}.flow span{display:block;color:var(--muted);margin-top:8px;font-size:14px}.flow .n{color:var(--accent);font-size:12px;margin-bottom:6px}.control{display:grid;grid-template-columns:1fr 2fr;gap:24px;background:var(--wash);padding:26px;align-items:start}.control ul{margin:0;padding-left:20px}.control p{margin:0}.control strong{display:block;font-size:19px;margin-bottom:8px}.scene{padding:24px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.scene label{font-weight:600;margin-right:12px}.scene h3{margin:20px 0 6px;font-size:21px}.scene p{font-size:16px}.small{font-size:14px;color:var(--muted)}.evidence-list{padding-left:20px}.evidence-list li{margin:10px 0}footer{margin-top:70px;padding-top:25px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}.mode-live{font-size:14px;color:var(--muted)}
@media(max-width:1000px){.layout{grid-template-columns:190px minmax(0,1fr)}.sidebar{padding:24px 16px}main{padding:40px 30px 60px}.flow{grid-template-columns:repeat(2,minmax(0,1fr))}.control{grid-template-columns:1fr}h1{font-size:44px}}
@media(max-width:700px){body{font-size:16px}.layout{display:block}.sidebar{height:auto;position:static;border-right:0;border-bottom:1px solid var(--line);padding:20px}.brand{margin-bottom:12px}.sidebar nav{display:flex;gap:6px 16px;flex-wrap:wrap}.sidebar nav a{padding:3px 0;font-size:13px}.sidebar .small{display:none}main{padding:30px 20px 50px}h1{font-size:35px}h2{font-size:25px}.lead{font-size:19px}.takeaway{font-size:21px}.flow{grid-template-columns:1fr}.flow li{border-right:0}.chapter{margin-top:42px}.control{padding:20px}pre{padding:18px 15px}.boundary{padding:18px}}
@media print{body{background:var(--paper);font-size:11pt}.layout{display:block}.sidebar,.toolbar,.scene,.skip{display:none}main{padding:0}h1{font-size:30pt}h2{font-size:20pt}.chapter{margin-top:24px;break-before:page}.takeaway{font-size:15pt}summary{display:none}.details-body{display:block}pre{white-space:pre-wrap;overflow:visible;background:var(--wash);color:var(--ink)}pre code{white-space:pre-wrap}.table-wrap{overflow:visible}table{min-width:0;font-size:9pt}tr{break-inside:avoid}h2,h3,h4{break-after:avoid}.flow,.control,.boundary{break-inside:avoid}a{color:var(--ink)}}
'''

SCRIPT = r'''
const details = [...document.querySelectorAll('.chapter details')];
const mode = document.getElementById('mode-live');
function setMode(open) { details.forEach(d=>d.open=open); document.getElementById('brief').setAttribute('aria-pressed',String(!open)); document.getElementById('deep').setAttribute('aria-pressed',String(open)); mode.textContent=open?'已展开全部技术章节；可随时折叠单章。':'当前为汇报概览；每章可单独展开技术细节。'; }
document.getElementById('brief').addEventListener('click',()=>setMode(false));
document.getElementById('deep').addEventListener('click',()=>setMode(true));
let printState=[]; window.addEventListener('beforeprint',()=>{printState=details.map(d=>d.open);details.forEach(d=>d.open=true)});window.addEventListener('afterprint',()=>details.forEach((d,i)=>d.open=printState[i]));
document.getElementById('print').addEventListener('click',()=>window.print());
const scenes={station:['固定站位装配','先确认稳定站立与工位治具，让双臂完成取料、对位，再接入可读工具结果。','目标数据：双臂/手、头部/腕部相机、接触和拧紧曲线。','模型：传统伺服/ACT基线，再比较目标G1数据微调的小VLA或专门模型。'],moving:['持工具移动与操作','导航、运动控制、操作策略与全身控制器必须统一权限、时序与负载。','目标数据：全身状态、基座、足部接触、负载/惯量、双手参考和任务结果。','模型：配套全身控制路线，不能直接拼接上肢BC与行走PPO。'],diy:['自造机械臂研究','先构建可标定、可读状态、可执行明确命令的小型本体，再研究迁移。','目标数据：自造本体的关节/控制/相机契约、标定、真实示范与任务结果。','模型：简单BC/ACT起步；其他本体的数据须重定向和目标本体微调。']};
function scene(){const x=scenes[document.getElementById('scenario').value];document.getElementById('scene-title').textContent=x[0];document.getElementById('scene-body').textContent=x[1];document.getElementById('scene-data').textContent=x[2];document.getElementById('scene-model').textContent=x[3]}
document.getElementById('scenario').addEventListener('change',scene);scene();
'''


def build():
    sections=[]; hashes={}
    for i,(name,title,takeaway,summary) in enumerate(DOCS):
        path=ROOT/'docs'/name; raw=path.read_bytes(); hashes['docs/'+name]=hashlib.sha256(raw).hexdigest()
        body=render_markdown(raw.decode('utf-8'))
        sections.append(f'<section class="chapter" id="chapter-{i+1}" aria-labelledby="title-{i+1}"><div class="chapter-number">{i+1:02d} / {len(DOCS):02d}</div><h2 id="title-{i+1}">{html.escape(title)}</h2><p class="takeaway">{html.escape(takeaway)}</p><p>{html.escape(summary)}</p><details><summary>展开：原理、字段、方案与复现细节</summary><div class="details-body">{body}</div></details></section>')
    nav=''.join(f'<a href="#chapter-{i+1}">{i+1:02d}　{html.escape(title)}</a>' for i,(_name,title,*_) in enumerate(DOCS))
    report=ROOT/'reports/industrial-2026-10-14'
    act=json.loads((report/'act-training.json').read_text(encoding='utf-8'))
    acceptance=json.loads((report/'synthetic_acceptance.json').read_text(encoding='utf-8'))
    evidence=f'''<section class="chapter" id="evidence"><div class="chapter-number">实际运行 / 证据边界</div><h2>已经执行了什么</h2><ul class="evidence-list"><li>合成XR结构：{acceptance['counts']['episodes']}条轨迹、{acceptance['counts']['numeric_frames']}个时刻，保留原始文件与哈希，得到{acceptance['counts']['windows']}个训练窗口。</li><li>BC：CPU训练20步，恢复检查点，在持出窗口预测并还原动作。</li><li>官方LeRobot ACT：固定SDK {act['sdk_version']}，读取{act['dataset_frames']}帧训练数据，执行{act['steps']}次更新，保存模型和训练processor；离线持出预测动作块。</li><li>PPO：虚构一维有限时域环境，实际采集rollout、计算优势、更新actor/critic并执行actor推理。</li><li>异步数值流：保留过去样本与有效性，缺失/陈旧数据不会用未来值填补。</li><li>接入模板：由于实际配置与证据未填写，检查器按预期拒绝；文件检查不授权实机执行。</li></ul><p class="boundary">全部训练演示使用合成/虚构教学环境。未训练预训练VLA，未执行G1行走或螺丝装配，也未完成公司生产服务部署。<a href="https://github.com/fengjikui/embodied-data-pipeline/tree/main/reports/industrial-2026-10-14">验收记录与原始JSON证据</a></p></section>'''
    page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>G1工业具身研究 · 数据、训练与执行闭环</title><style>{STYLE}</style></head><body><a class="skip" href="#main">跳到报告正文</a><div class="layout"><aside class="sidebar"><div class="brand">EMBODIED DATA PIPELINE<br>实验室研究报告</div><nav aria-label="报告章节"><a href="#overview">总览与两种流程</a>{nav}<a href="#evidence">运行证据与边界</a></nav><p class="small">核查日期 2026-10-14<br>可离线阅读，无网络字体或脚本。<br><br>G1 EDU 已确定；具体手型、传感器与工艺待确认。</p></aside><main id="main"><header id="overview"><div class="meta">工业具身智能 / G1 EDU / 2026-10-14</div><h1>从一次示范<br>到一次合格装配</h1><p class="lead">把数据、模型和控制接口连起来，讲清机器人怎样学习、怎样执行，以及每一步用什么证据验收。</p><p>案例：双手配合完成螺丝装配。先从固定工位建立基线，再扩展全身与持工具移动。</p><div class="boundary"><strong>本次交付：</strong>系统研究、可执行学习流程与工业化方案。真实设备、工艺质量和生产可靠性另有验收门槛，不用教学演示代替。</div><div class="toolbar" aria-label="阅读模式"><button id="brief" aria-pressed="true">汇报概览</button><button id="deep" aria-pressed="false">技术详读</button><button id="print">打印 / 保存PDF</button></div><p id="mode-live" class="mode-live" aria-live="polite">当前为汇报概览；每章可单独展开技术细节。</p></header><h2>数据闭环：从经验生成训练输入</h2><ol class="flow"><li><span class="n">01 / 采集与获取</span><b>真机、仿真、公开来源</b><span>保留完整session、动作语义、时钟与权限。</span></li><li><span class="n">02 / 原始与接入</span><b>快照、哈希、解析</b><span>原始只追加，adapter按明确契约读取。</span></li><li><span class="n">03 / 质量与同步</span><b>时间、语义、任务标签</b><span>隔离异常，按session切分防止泄漏。</span></li><li><span class="n">04 / 模型视图</span><b>相机、状态、动作块</b><span>按模型生成格式，使用train-only统计。</span></li><li><span class="n">05 / 训练与评估</span><b>监督学习或强化学习</b><span>固定数据与配置，评价独立任务条件。</span></li><li><span class="n">06 / 执行与回流</span><b>闭环日志、质量、失败</b><span>回流新批次，为恢复与下一轮训练提供依据。</span></li></ol><h2>控制闭环：模型输出怎样成为动作</h2><div class="control"><p><strong>任务与模型</strong>选择技能并生成动作参考。模型输出不自动成为硬件命令。</p><ul><li>导航确定移动目标，运动控制器跟踪。</li><li>操作策略生成双手参考，全身控制协调平衡与负载。</li><li>工具控制器完成拧紧，工艺结果判定质量。</li><li>持续采集实际反馈，管理超时、接管和恢复。</li></ul></div><div class="scene"><label for="scenario">切换研究场景</label><select id="scenario"><option value="station">固定站位装配</option><option value="moving">持工具移动与操作</option><option value="diy">自造机械臂研究</option></select><div aria-live="polite"><h3 id="scene-title"></h3><p id="scene-body"></p><p id="scene-data"></p><p id="scene-model"></p></div><p class="small">场景切换展示设计建议，不表示这些任务已经验证。</p></div>{''.join(sections)}{evidence}<footer>内容源：docs/17–23，生成脚本：scripts/build_industrial_report.py。厂商一手出处在对应章节；原始数据、训练证据与公开素材各自保留许可。<br><a href="https://github.com/fengjikui/embodied-data-pipeline">公开仓库</a> · <a href="https://github.com/fengjikui/embodied-data-pipeline/blob/main/LICENSE">MIT（自有代码与原创文档）</a><br>此报告可下载后独立打开；外部出处链接需要联网。</footer></main></div><script>{SCRIPT}</script></body></html>'''
    output=ROOT/'deliverables/industrial-report.html'; output.write_text(page,encoding='utf-8')
    manifest={'checked_on':date.today().isoformat(),'schema':'offline_report_build_v1','markdown_sha256':hashes,
              'html_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'external_runtime_assets':False,
              'report_inputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (report/'act-training.json', report/'synthetic_acceptance.json')}}
    (report/'offline-report-build.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(output,output.stat().st_size,'bytes')


if __name__=='__main__':
    build()
