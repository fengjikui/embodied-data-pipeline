# 厂商、开放数据与采购候选：哪些能用于我们自己的机器人

核查日期：2026-10-14。信息优先来自厂商、作者和官方仓库。厂商示范/自报能力不是本实验室验证，也不等于已证实能完成本集团螺丝工位。

## 1. “直接可用”必须分三层

1. **格式可用**：reader 能解析文件，字段/视频有版本和元信息。
2. **训练可用**：选定模型的视图、语言、mask、归一化和标签适配，训练更新确实执行。
3. **实机可用**：动作语义、手型、本体、传感器、控制器、时序和闭环评价一致。

本项目公开小样本已验证第一层，CPU BC/本次官方 ACT 教学验证训练接口的一部分；没有验证工厂能力。不同机器人的数据通常是预训练/迁移候选；**公开下载不能代替目标 G1 的工位示范**。

命名也要分清：宇树 G1、智元材料中的 AgiBot G1 和银河通用 Galbot G1 是不同厂商的本体，不能因为都叫“G1”就认为关节与控制接口相同。

## 2. 厂商方案与开放程度

| 厂商/路线 | 一手材料披露什么 | 本次实际可获取的入口 | 对我们的作用 | 不能据此承诺 |
|---|---|---|---|---|
| 宇树 G1 | 真机/仿真 XR、IL 框架、RL 仿真、UnifoLM 模型路线 | XR、unitree_lerobot、RL Lab、Dex1/WBT 数据和 UnifoLM-WLA | 最接近目标本体，先核对控制/数据契约 | 出厂内部算法、任意 EDU 配置通用、已会拧螺丝 |
| NVIDIA 与 G1 | GR00T 和全身控制配套 | G1 Teleop、Isaac-GR00T、GR00T-WBC/SONIC | 上肢与全身两套可读技术路线 | 所有 G1 动作表示可以混用 |
| 智元 | AgiBot World/GO-1、2026 分层/接触数据、Genie Sim | 数据、模型、采集/仿真研究入口 | 双臂、长任务、接管/失败标注与仿真 | 智元本体数据直接驱动宇树；NC 数据默认可做产线商业训练 |
| 银河通用 | 官网介绍 GraspVLA、运动跟踪与导航路线，SDK有导航/感知/抓放组合例子 | 作者 GraspVLA/SynGrasp-1B、官方开发平台与 HumanTracker | 抓取迁移、组合系统和全身评价参考 | 抓取/导航示范等于全流程装配/拧紧 |
| Figure | Helix 02 全身分层路线 | 官方架构文章与示范 | 全身协同技术参考 | 本次未确认公开可下载的完整 Helix 训练数据/权重 |
| Tesla Optimus | AI、感知、控制、导航与平衡的软件需求 | 官方 AI/Robotics 页面 | 理解系统需要多项能力 | 不能仅凭网页判定其统一 VLA、算法/数据配方 |
| 1X | 动作条件世界模型路线 | 官方模型研究说明 | 预测/规划方向参考 | 预测视频代替真实接触/质量验证 |
| UR/睿尔曼等机械臂 | 工业接口、控制器和具体机型 | 官方硬件/开发接口 | 固定工位装配对照平台 | 购买设备自动提供通用 VLA 或训练数据 |

证据：[宇树 XR](https://github.com/unitreerobotics/xr_teleoperate)、[宇树 IL](https://github.com/unitreerobotics/unitree_lerobot)、[宇树 RL](https://github.com/unitreerobotics/unitree_rl_lab)、[UnifoLM-WLA](https://github.com/unitreerobotics/unifolm-wla)、[NVIDIA GR00T](https://github.com/NVIDIA/Isaac-GR00T)、[全身控制](https://github.com/NVlabs/GR00T-WholeBodyControl)、[智元/GO-1](https://github.com/OpenDriveLab/AgiBot-World)、[Genie Sim](https://github.com/AgibotTech/genie_sim)、[GraspVLA](https://github.com/PKU-EPIC/GraspVLA)、[Figure](https://www.figure.ai/news/helix-02)、[Tesla](https://www.tesla.com/AI)、[1X](https://www.1x.tech/discover/redwood-ai-world-model)、[UR](https://www.universal-robots.com/products/)、[睿尔曼开发](https://develop.realman-robotics.com/en/robot/apic/classes/force/)。

银河通用的厂商关联与接口依据：[官网介绍](https://www.galbot.com/about/)、[官方任务教程](https://developer.galbot.com/docs/SDK/1.10.0/s1/en/tutorials/)。官网能力描述属于厂商声明。

## 3. 值得列入内网下载计划的数据

| 优先级与来源 | 格式/内容 | 怎么帮 G1 EDU | 下载与适配策略 |
|---|---|---|---|
| P0 · 目标 G1 自采 | 原始 XR/传感/工具日志 | 工位动作、手型和质量的直接监督 | 先10完整episode试采；采集实际关节/控制器契约 |
| P0 · [NVIDIA G1 Teleop](https://huggingface.co/datasets/nvidia/PhysicalAI-Robotics-GR00T-Teleop-G1) | LeRobot，G1上肢操作 | 格式和目标本体参考，已有6条小样本 | 复用锁定小样本；验证实际手型与控制含义 |
| P0 · [宇树 Dex1](https://huggingface.co/datasets/unitreerobotics/G1_Dex1_Clean_Table) | 旧快照已抽查任务为LeRobot v2.1；本次API返回401 | 简单夹爪上肢参考 | 当前访问状态需确认；如采购Dex1，先metadata＋10完整episode；不代表装配 |
| P1 · [宇树 WBT](https://huggingface.co/collections/unitreerobotics/unifolm-wbt-dataset) | 所选任务已抽查LeRobot v3.0，全身/手的字段 | 全身动作契约研究 | 选实际手型对应任务；每条task单独锁revision |
| P1 · [AgiBot World 2026](https://huggingface.co/datasets/agibot-world/AgiBotWorld2026) | Parquet＋视频，层级步骤、错误/接管标注 | 长任务分段、恢复与数据治理 | 先一条完整长任务及其标注；CC-BY-NC-SA，生产用途先确认授权 |
| P1 · [AgiBot World/GO-1](https://github.com/OpenDriveLab/AgiBot-World) | 智元双臂数据＋模型生态 | 迁移/数据多样性对照 | 本体不同，需adapter和目标数据；许可同上游声明 |
| P1 · [SynGrasp-1B](https://huggingface.co/datasets/vegebirrd/SynGrasp-1B) | 仿真抓取轨迹，作者训练器有LeRobot Franka loader | 研究仿真视觉/抓取泛化 | 先schema和单批，非G1/非拧紧；模型/数据许可分别核查 |
| P1 · [Genie Sim](https://github.com/AgibotTech/genie_sim) | 仿真任务/生成工具与数据入口 | 生成可控任务变化和评估 | 工具不是现成真机示范，先验证仿真机器人/输出格式 |
| P2 · [Open X-Embodiment](https://github.com/google-deepmind/open_x_embodiment) / [DROID](https://droid-dataset.github.io/) | 多本体RLDS/机器人操作轨迹 | 通用操作预训练与迁移 | 需RLDS adapter；每来源许可和动作都分开 |
| P2 · 人体动作/运动跟踪 | 动捕/retargeted动作、控制器指定motion library | 行走/全身参考跟踪RL | 有参考不等于有稳定控制，需机器人模型与奖励 |
| P1 · [HumanTracker](https://github.com/GalaxyGeneralRobotics/HumanTracker) | 人动作/机器人参考轨迹、运动跟踪评价及偏好对 | 全身跟踪与奖励模型研究 | 有G1版本约束；参考轨迹/偏好标签不等于本工位动作示范；仅核查README |

本次只抓取 metadata、README 和规范，不下载这些完整数据集/大模型；固定 revision 与字段见 [数据快照](../evidence/industrial-datasets-2026-10-14.json)、[代码快照](../evidence/industrial-upstreams-2026-10-14.json)。旧24项目录继续保留在 [数据集索引](02-dataset-catalog.md)，不把新核查状态追溯成旧报告的实测。

## 4. 一个具体例子：宇树 WLA 并不只读“关节向量”

核查的 `unifolm-wla` 规范提供统一的 **54维动作、60维状态** 与有效性 mask；状态与mask拼接后投影器输入120维。末端/基座位姿使用相对当前状态的 SE(3) 表示，其余通道保留来源控制语义。规范示例的动作块是30个动作点。**这些是该版本模型表示，不是 G1 拥有54个电机。**

更关键的限制：核查版本的 WBC msgpack action server 默认 adapter 只覆盖 Dex1 槽位；Dex5/WBT 客户端与协议需扩展。能训练某种手型不代表现有服务已可执行该手型。来源：[动作/状态规范](https://github.com/unitreerobotics/unifolm-wla/blob/0a1aa87be8f7/docs/robot_action_state_processing_en.md)、[训练与服务规范](https://github.com/unitreerobotics/unifolm-wla/blob/0a1aa87be8f7/docs/train_action_expert_en.md)。完整revision/hash见代码快照。

我们的 NPZ 是本来源原生维度＋mean/std；直接送给这个54/60维模型会错。需按上游 slot、SE(3)、统计与mask重新派生视图，不能简单补零猜缺失维度。官方 LeRobot 导出只解决存储，不自动做该模型 adapter。

## 5. 手部/传感/工具采购怎么比较

以下是候选类别与工程建议，不是采购承诺。价格、交期、G1安装、控制授权与可读数据均需供应商书面确认。本次不采用经销商价格或未经验证的兼容声明。

| 候选 | 适用与优势 | 对数据的要求 | 决策条件 |
|---|---|---|---|
| 宇树 [Dex1-1](https://www.unitree.com/Dex1-1/) 类简单夹持 | 状态/动作简单，适合早期取放和固定治具 | 开合/夹持命令、实际状态、抓到/掉落结果 | 螺丝尺寸/指尖、防滑、工具固定方式是否满足 |
| 宇树 [Dex3-1](https://www.unitree.com/Dex3-1/) | 更丰富接触与握持，官方生态入口 | 实际手指顺序、力/触觉读数、手臂同步 | 是否真能读需要的数据，重复握持工具的稳定性 |
| 宇树 [Dex5-1](https://www.unitree.com/Dex5-1/)／其他五指手 | 研究复杂人类工具与手内操作 | 高维手指、触觉、retargeting、接触标注 | 功能是否确有必要、接口覆盖、寿命/维护与样本成本 |
| [Robotiq Hand-E/2F](https://robotiq.com/products/adaptive-grippers) 类工业夹爪 | 固定机械臂装配对照、产业集成生态 | 位置/速度/夹持力/物体检测 | 并非默认G1即插即用，核验安装/重量/协议 |
| [ATI 六维 F/T](https://ati-ia.com/products/ft/sensors.aspx)／[睿尔曼内置六维力](https://develop.realman-robotics.com/en/robot/apic/classes/force/) | 接触、反力矩、工具过程研究 | 六维数值、坐标、零偏、时间、采样/滤波 | 量程/噪声/过载、零点与重力补偿、驱动时延 |
| 头部＋腕部 RGB／深度 | 大范围定位与近距离精细对位互补 | 内外参、曝光时间、帧率、同步/丢帧 | 小螺丝成像、遮挡、反光、安装稳定性 |
| [工业拧紧模组/控制器](https://www.atlascopco.com/content/dam/atlas-copco/industrial-technique/general/documents/brochures-leaflets/electric-assembly-tools-and-systems/Smart%20Tightening%20Strategies%20Leaflet.pdf) | 可读扭矩/角度与质量结果，适合可测闭环 | 程序/周期ID、曲线、OK/NOK、时间、故障 | 工艺范围、反扭矩、通讯、供料、追溯与安装 |

实验室起点建议：**先验证简单夹持/固定工具＋可读工艺结果，再为明确需要的手内操作升级灵巧手。** 若研究目标本身是手持工具泛化，可并行保留灵巧手方案。用同一工件完成抓取/对位/拧紧试验，再比较复杂度与可靠性。

## 6. 买电机构造自己的机器人是否可行

可以把 [SO-101](https://github.com/huggingface/lerobot/blob/main/docs/source/so101.mdx) 等开源机械臂作为数据/BC教学基线；[ROBOTIS DYNAMIXEL](https://emanual.robotis.com/docs/en/dxl/x/) 提供带反馈的执行器生态。它们有利于理解标定、主从示教、关节命令和训练，**不代表能承受产线电批反扭矩或达到装配工艺指标**。

自造本体需要机械设计、驱动、编码器零点、减速器/背隙、刚度/热/制动、控制带宽、URDF/惯量、供电/通讯、标定与安全机制。电机规格不等于整机能力。动作先在该本体验证，再映射世界/工具空间，并通过IK/可达性/碰撞与目标数据适配。不能复用另一台机器人同维度关节向量。

建议用小臂验证算法、用购买的工业臂做固定工位对照、用G1研究移动与全身协作。是否另买臂由预算和工艺需求决定，不自动采购。

## 7. 商业数据与服务

[Scale Physical AI](https://scale.com/physical-ai) 等提供机器人数据采集/整理服务。把它作为候选供应商，不认为存在现成可用于本工位的货架数据包。本次未取得报价或采购样本。

采购清单应明确：本体/手型/控制器、原始图像与动作、实测捕获时间、双手/力/工具字段、原始session分组、失败/接管、标定、权限范围、完整数据交付与重复率。先采购/验收10条完整样本，验证能进我们的adapter再讨论规模。只交视频或模型归一化后的向量可能无法恢复动作物理含义。

## 8. 如何选模型与数据组合

最接近本体的数据优先用作语义/接口参考；目标任务自采优先用于任务能力；跨本体公开数据用于预训练/迁移对照；仿真用于可控变化与RL；商业服务补采集/整理产能。模型按动作接口、训练资源、推理周期与任务成功选择，不能按厂商演示或参数数量排名。
