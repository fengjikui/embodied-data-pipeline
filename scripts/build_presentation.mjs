// Artifact authoring uses a separate presentation runtime. Production pipeline is independent.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const root=process.env.PROJECT_ROOT;
const skill=process.env.PRESENTATIONS_SKILL;
if(!root||!skill)throw new Error('Set PROJECT_ROOT and PRESENTATIONS_SKILL');
const build=path.join(root,'.build/slides');
const out=path.join(root,'deliverables');
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')));
const a=JSON.parse(await fs.readFile(path.join(root,'reports/acceptance.json'),'utf8'));
const training=JSON.parse(await fs.readFile(path.join(root,'reports/training_probe.json'),'utf8'));
if(a.release_id!==training.release_id)throw new Error('Evidence release mismatch');
const ci=JSON.parse(await fs.readFile(path.join(root,'reports/cross-platform-ci.json'),'utf8'));
if(ci.conclusion!=='success'||ci.jobs.some(j=>j.conclusion!=='success'))throw new Error('CI not passed');
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#21342D',muted:'#607069',paper:'#F5F3EC',accent:'#A14F2D',white:'#FFFDF7',line:'#CCD3C9'};
const font='Arial Unicode MS';
const slides=[];const nativeTables=[];
function text(s,txt,x,y,w,h,size=28,color=C.ink,bold=false){const q=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});q.text=txt;q.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none'};return q;}
function slide(title,note,dark=false){const s=p.slides.add();s.background.fill=dark?C.ink:C.paper;const n=slides.length+1;slides.push({title,note});if(title)text(s,title,66,48,1148,75,42,dark?C.white:C.ink,true);text(s,String(n).padStart(2,'0'),1168,664,50,25,16,dark?'#BEC9BB':C.muted);s.speakerNotes.textFrame.setText(note);return s;}
function para(s,heading,body,x,y,w=540,dark=false){text(s,heading,x,y,w,48,30,dark?C.white:C.ink,true);text(s,body,x,y+64,w,80,25,dark?'#DFE4D9':C.muted);}
function table(s,values,widths,{x=66,y=185,h=335,size=25}={}){const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:widths.reduce((a,b)=>a+b,0),height:h,columnWidths:widths,values});t.borders.assign({fill:C.line,width:1});for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){const cell=t.getCell(r,c);cell.fill=r===0?C.ink:C.paper;cell.text.style={typeface:font,fontSize:size,bold:r===0,color:r===0?C.white:C.ink};}nativeTables.push(slides.length);return t;}
async function image(s,name,x,y,w,h){s.images.add({blob:new Uint8Array(await fs.readFile(path.join(out,'assets',name+'.png'))),contentType:'image/png',alt:name+' 原始数据视频帧',fit:'contain',position:{left:x,top:y,width:w,height:h}});}
const notes={
cover:'建议用时 30 秒。今天汇报分三部分：对 VLA 数据的认识、我们已经跑通的数据工程验证，以及下一阶段需要的场景与资源。实验室还在探索工业具身智能，这次交付先建立可复用的数据基础。来源：docs/06-supervisor-brief.md。',
conclusion:'建议用时 50 秒。核心结论是，在机器人和任务尚未确定时，数据接入和验证仍能推进。我们已经完成真实数据到训练窗口和小模型反向传播的工程链路。还没有完成预训练 VLA 微调或机器人任务验证。后续最需要工厂入口与目标控制接口。来源：reports/acceptance.json；reports/training_probe.json。',
model:'建议用时 60 秒。我有 LLM 基础，可以把 VLA 理解为利用视觉、语言和状态来预测动作的模型。动作可用离散 token、连续回归或生成式动作头。机器人状态和动作需要单位、坐标、时间与控制器定义。本次小模型用来检查数据接口，没有预训练视觉语言骨干。来源：docs/01-vla-data-research.md；https://github.com/openvla/openvla；https://github.com/Physical-Intelligence/openpi。',
data:'建议用时 45 秒。不要把这四项视为互斥的桶。一个公开数据集可以是真实环境中遥操作采集、后来以商业授权形式提供。分类的目的，是判断获取条件和训练价值。来源：docs/01-vla-data-research.md。',
map:'建议用时 60 秒。已经整理 24 项数据条目及 57 项来源，其中有暂缓和排除项。对于后续下载，应先选任务、本体、动作和访问条件，再扩量。本页是代表入口，不是质量排名。完整的获取清单在 docs/11-download-priorities.md。来源：https://droid-dataset.github.io/；https://huggingface.co/datasets/lerobot/abc_130k_v3_smoke；https://github.com/OpenDriveLab/AgiBot-World；https://huggingface.co/datasets/unitreerobotics/G1_WBT_Brainco_Collect_Plates_Into_Dishwasher；https://github.com/RoboTwin-Platform/RoboTwin。',
sample:'建议用时 50 秒。本次只取每个来源 6 条轨迹、一路相机。真实双臂任务是卷领带，G1 是拿苹果，仿真是双臂穿引，它们用于验证文件与训练接口，不能代替集团工位。状态和动作维度不同，原型没有进行不可靠的跨本体转换。窗口数受采样间隔与数量上限影响，不能据此比较来源价值。来源：configs/demo_sources.lock.json；reports/acceptance.json。',
photos:'建议用时 40 秒。让主管看见数据中的真实图像，动作则在对应数值文件中。这里都是固定版本原始视频帧提取，没有生成式图像。G1 展示上身桌面操作，不是负载行走。图像出处与许可：reports/image_attribution.json；NVIDIA G1 和 X-Embodiment-Sim 为 CC-BY-4.0；ABC v3 smoke 为 Apache-2.0。',
pipeline:'建议用时 60 秒。原始层保存文件和哈希，规范层保存完整数字轨迹及来源，训练视图负责图像取样、语言、动作块、mask 和统计。输出是特定训练程序使用的接口视图。新格式第一次需要适配，同契约新批次可以复用。来源：src/vla_pipeline/pipeline.py；docs/03-pipeline-design.md。',
leak:'建议用时 60 秒。这是本次真实发现：ABC 一行存着整段语言标注，若直接拼接，会把未来阶段提前给模型。这是针对带生效时间的阶段标签；任务开始前本来已知的完整指令并不自动构成泄漏。现在只取当前时刻已经生效的阶段标注。图像也只选过去帧。这个验证依赖源时间，设备时钟与实际延迟仍需标定。来源：data/raw/abc_real 的固定版本 episode 0；src/vla_pipeline/readers.py；tests/test_contracts.py。',
quality:'建议用时 50 秒。原始样本 18 条均通过当前工程检查；我们另造了异常变体来测试规则：错误时间、NaN、缺少视频被隔离，重复副本被跳过。注入错误比例不代表原始数据质量。来源：reports/acceptance.json；scripts/verify_delivery.py。',
train:'建议用时 60 秒。每组单独训练一个随机初始化的小网络，实际输入图像、语言和状态，监督是 8 步动作。CPU 跑 120 步，有限梯度、检查点和优化器恢复通过。训练误差下降只说明拟合；仿真组验证误差仍高，提醒我们不能把训练链路正常等同于泛化或机器人成功。不同来源的归一化尺度不同，不能直接排优劣。来源：reports/training_probe.json；src/vla_pipeline/training.py。',
platform:'建议用时 45 秒。公司实际落地优先 Ubuntu 服务器，并兼容 Windows。代码和数据契约跨平台，运行库和 wheel 需要按系统准备。不同操作系统的虚拟环境不能直接复制。当前提供校验包和离线模式，两平台 CI 已实际通过 21 项测试；CI 是合成契约测试，真实服务器的编解码、GPU 和内网环境仍要复验。来源：docs/10-linux-windows-offline-deployment.md；https://docs.astral.sh/uv/concepts/projects/layout/。',
routes:'建议用时 60 秒。机械臂与人形保持同等研究深度，数据管理共用，控制适配分别做。机械臂先分拣和上下料，再讨论接触；人形先静止双臂，再增加移动、负载和稳定性验证。需要现场真实条件与控制接口参与，而不是只凭已有数据定采购。来源：docs/05-lab-roadmap.md。',
roadmap:'建议用时 60 秒。建议四周按检查点推进：任务与接口清楚、上游模型能够微调、固定任务有完整试验、数据增加有对照。资源和设备未确定，所以这是工作安排，不是工业达标日期。来源：docs/06-supervisor-brief.md。',
asks:'建议用时 45 秒。希望主管确认下一阶段先完成一个候选任务的模型和评测闭环，协调一到两个现场联系人，明确现有机器人、GPU 和人员资源，并设置两周复盘。我们负责形成技术证据，业务现场定义价值和合格标准，主管决定投入优先级。来源：docs/06-supervisor-brief.md。',
close:'建议用时 20 秒。交付包已经覆盖调研、可运行管线、实测记录和迁移说明。下一阶段用真实任务连接模型与机器人能力。可现场打开离线报告，或者运行演示手册中的缓存重跑命令。来源：README.md；docs/08-demo-runbook.md。'
};
let s=slide('',notes.cover,true);text(s,'工业具身智能',70,112,1100,80,58,C.white,true);text(s,'VLA 数据预研\n与管线工程验证',70,218,1090,170,68,C.white,true);text(s,'集团 AI 实验室 · 阶段交付',74,458,950,48,28,'#D0D9C9');text(s,'2026.09.14',76,578,600,40,24,'#D0D9C9');
s=slide('本次交付与阶段结论',notes.conclusion);text(s,'数据已进入可复现的训练工程链路',68,157,1140,65,36,C.accent,true);para(s,'已经完成','多来源接入、异常隔离、训练窗口\n以及小模型反向传播和检查点恢复',70,276,540);para(s,'下一阶段验证','目标工位、目标机器人、选定 VLA\n以及闭环执行与数据收益',680,276,510);text(s,'需要主管支持：现场入口、资源范围、阶段复盘',70,567,1130,50,27,C.ink,true);
s=slide('VLA 的输入、输出与数据监督',notes.model);table(s,[['模型所见','模型所学','新增约束'],['图像 + 语言 + 当前状态','当前条件下的动作','坐标、单位、控制接口'],['轨迹切出的观测与动作窗口','连续动作或动作 token','时间同步与 episode 边界'],['多条件示范与纠正片段','技能、适应与恢复','固定闭环评测验证收益']],[410,350,388],{h:330,size:27});text(s,'LLM 训练知识可以迁移，动作标签必须具有可解释的物理含义',70,566,1120,66,27,C.accent);
s=slide('数据分类的四个独立维度',notes.data);table(s,[['维度','典型取值','判断用途'],['获取权利','开放许可、限制访问、商业许可','能否获取和按目标用途使用'],['产生环境','真实环境、仿真环境','与目标工位差异在哪里'],['控制方式','遥操作、脚本、策略、人工接管','动作监督从哪里来'],['数据内容','视频、语言、状态、动作、接触','能支持哪类模型与训练目标']],[230,420,498],{h:380,size:25});
s=slide('数据资产清单与下载顺序',notes.map);text(s,'24 项条目 / 57 项来源',68,147,1120,60,36,C.accent,true);table(s,[['研究方向','优先核查的代表入口','获取策略'],['机械臂与双臂','DROID、Bridge、ABC、RoboMIND','先取任务与本体明确的样包'],['人形上身与全身','NVIDIA G1、宇树 Dex1 / WBT、AgiBot','区分手型、上身与移动操作'],['仿真与评测','X-Embodiment Sim、RoboTwin、LIBERO','锁定任务、控制器与评测版本']],[260,520,368],{y:245,h:292,size:25});text(s,'本机仅保留约 212 MB 原始验证样本；后续扩量在公司环境执行',70,575,1120,50,27,C.ink);
s=slide('三类数据的真实接入结果',notes.sample);table(s,[['来源','轨迹 / 时刻','状态 / 动作维度','训练窗口'],...a.sources.map(x=>[x.id==='g1_real'?'真实人形 G1':x.id==='abc_real'?'真实双臂 YAM':'仿真双臂 Panda',`${x.accepted} / ${x.frames.toLocaleString('en-US')}`,`${x.state_dim} / ${x.action_dim}`,String(x.training_windows)])],[340,260,300,248],{h:325,size:28});text(s,'18 条来源轨迹，23,109 个时刻，590 个训练窗口',70,559,1120,60,31,C.accent,true);
s=slide('图像与动作记录共同组成示范',notes.photos);await image(s,'abc_real',64,185,354,280);await image(s,'g1_real',463,185,354,280);await image(s,'panda_sim',862,185,354,280);text(s,'真实双臂：卷领带',76,488,340,42,27,C.ink,true);text(s,'真实人形：拿苹果',475,488,340,42,27,C.ink,true);text(s,'仿真双臂：穿引',874,488,340,42,27,C.ink,true);text(s,'原始视频帧提取。工程代表样本，尚未对应集团具体工位',76,580,1120,44,25,C.muted);
s=slide('数据管线的三个层次',notes.pipeline);para(s,'01  原始层','固定版本、逐文件哈希、不可覆盖原件\n新批次登记，损坏文件明确报错',70,170,1100);para(s,'02  规范层','完整数字轨迹、语言与媒体引用\n检查时间、维度、缺失、重复和来源关系',70,320,1100);para(s,'03  训练视图','按时间戳选取当前及过去观测、动作块和 mask\n按来源保留维度，发布可复现版本',70,470,1100);
s=slide('实际发现：一行数据包含未来语言',notes.leak);table(s,[['生效时间','原始子任务标注','在 1 秒时是否可见'],['0.0 秒','从料盒拿起领带','是'],['3.7 秒','将领带放到工作板中央','否'],['17.33 秒','在工作板上卷起领带','否']],[220,600,328],{h:310,size:27});text(s,'按当前时间选择有效标注，避免训练条件提前泄露后续步骤',70,543,1130,84,30,C.accent,true);
s=slide('异常隔离与数据发布验收',notes.quality);table(s,[['验证项','实际结果'],['错误时间、NaN、缺失视频','3 个注入变体隔离'],['完全重复的数值轨迹','1 个副本跳过'],['离线重跑、文件完整性','同一发布复用，输出哈希通过'],['统计与动作窗口','只用训练集；尾部 mask；不跨轨迹']],[610,538],{h:370,size:27});text(s,'异常是人为构造的测试样本，不用于估算原数据集缺陷率',70,595,1120,40,24,C.muted);
s=slide('小模型训练接口的实测结果',notes.train);table(s,[['来源','初始训练 MSE','结束训练 MSE','验证 MSE'],...training.results.map(r=>[r.source_id==='g1_real'?'真实人形':r.source_id==='abc_real'?'真实双臂':'仿真双臂',r.initial_train_masked_mse.toFixed(4),r.final_train_masked_mse.toFixed(4),r.validation_masked_mse.toFixed(4)])],[280,300,300,268],{h:295,size:27});text(s,'CPU / 每组 120 步 / 有限梯度 / 检查点恢复输出一致',70,518,1120,48,28,C.ink,true);text(s,'随机初始化小网络，用于工程验证。不能据此判断机器人能力或跨来源优劣',70,581,1120,60,23,C.accent);
s=slide('公司环境迁移与平台适配',notes.platform);para(s,'Linux / Ubuntu 优先','核心管线使用 Python 与相对路径\nWindows 使用相同命令入口',70,183,540);para(s,'内网准备分开管理','项目与数据包可校验迁移\nPython 运行库按 OS / 架构另备',680,183,500);table(s,[['已提供','仍需公司环境验证'],['版本锁、离线模式、本地数据登记','目标系统 wheel 与视频编码'],['Ubuntu / Windows 契约测试通过','GPU、机器人 SDK、内网镜像与权限']],[574,574],{y:429,h:173,size:25});
s=slide('机械臂与人形的并行验证路线',notes.routes);table(s,[['','机械臂','人形'],['候选起点','零件分拣、工位上下料','静止双臂整理、搬放'],['后续扩展','夹具交互、精细接触','移动到位、负载搬运'],['核心新增条件','工具、公差、力／触觉、联锁','全身控制、根部位姿、接触与负载'],['共同评价','合格率、干预、节拍、稳定性','合格率、干预、节拍、稳定性']],[205,472,471],{h:370,size:25});text(s,'共用数据工程，分别维护本体与控制适配',70,590,1120,50,28,C.accent,true);
s=slide('建议的四周检查点',notes.roadmap);table(s,[['周次','技术工作','应看到的证据'],['第 1 周','现场候选与动作接口，选择上游模型','任务卡、资源范围、接入清单'],['第 2 周','真实模型加载与小规模微调','真实 batch、梯度、检查点'],['第 3 周','固定任务基线，试采目标数据','全部试验记录、失败分桶'],['第 4 周','固定预算比较不同数据配方','成功数 / 总试验数、干预与节拍']],[155,505,488],{h:375,size:25});text(s,'安排以资源可用为前提，阶段结果决定继续扩展的方向',70,596,1120,44,24,C.muted);
s=slide('需要主管确认与协调的事项',notes.asks);para(s,'下一阶段优先成果','建议聚焦一个候选任务的模型与评测闭环',70,176,1120);para(s,'集团内部现场入口','协调 1～2 位联系人，共同定义价值与合格标准',70,316,1120);para(s,'资源范围与复盘机制','确认现有设备、GPU 与人员支持，两周复盘一次',70,456,1120);
s=slide('交付包与后续工作',notes.close,true);text(s,'调研可以查证\n管线可以运行\n结果可以复现',74,180,1050,250,55,C.white,true);text(s,'下一阶段：用真实工位检验模型与数据的价值',76,528,1120,60,32,'#D0D9C9');
await fs.mkdir(build,{recursive:true});
await fs.writeFile(path.join(root,'deliverables/slide-notes.json'),JSON.stringify(slides.map((x,i)=>({...x,title:x.title||'工业具身智能：VLA 数据预研与管线工程验证'})),null,2));
const candidate=path.join(build,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);
for(let i=0;i<p.slides.items.length;i++){const preview=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(path.join(build,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await preview.arrayBuffer()));}
const finalPath=path.join(out,process.env.DECK_FILENAME||'VLA数据预研与管线验证-主管汇报.pptx');
await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath,pythonExecutable:process.env.RUNTIME_PYTHON,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...nativeTables.flatMap(n=>['--require-native-table-slide',String(n)])],requiredNativeTableOwnerSlides:nativeTables,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:path.join(build,'validation-'+Date.now()+'.json')});
console.log(finalPath);
