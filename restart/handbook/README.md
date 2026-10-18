# 具身智能数据管线：理论与手动实操手册

编写日期：2026-10-18。面向集团 AI 实验室的前期研究。读者已有 Transformer／LLM 训练基础，机器人经验不限。

本手册从 `restart/` 的需求重新组织，不依赖旧项目的 `src/` 或训练脚本。它交付学习文档、独立实验代码和验证记录；可视化生产产品仍需按专章分阶段开发。

## 怎样使用

每次只读一章，按对应实验操作，保存输出，再用自己的话回答章末问题。无真机也能完成 L0–L3；L4 是 GPU 迁移步骤；L5 是仿真与真机的条件化接入手册。运行状态与证据见 [验证记录](verification.md)。

| 顺序 | 理论文档 | 配套操作／成果 |
| --- | --- | --- |
| 1 | [T1 完整系统与两个工序](theory/01-system-and-tasks.md) | 画出“执行任务”与“开发模型”两条流程 |
| 2 | [T2 设备、人员与遥操作](theory/02-capture-and-devices.md) | 标出 Host、PC2、头显、仿真和训练服务器的程序位置 |
| 3 | [T3 真实格式与训练样本](theory/03-formats-and-samples.md) | [L1 少量真实 G1 数据](labs/01-real-g1-data.md) |
| 4 | [T4 处理、质量、存储与版本](theory/04-pipeline-and-versioning.md) | [L2 采集文件、转换、划分与快照](labs/02-conversion-and-versioning.md) |
| 5 | [T5 五条策略路线与训练目标](theory/05-models-and-losses.md) | [L3 官方 ACT 训练与离线推理](labs/03-training-and-inference.md) |
| 6 | [T6 行走、全身控制与世界模型](theory/06-rl-whole-body-world-models.md) | [L5 仿真／真机接入条件与步骤](labs/05-simulation-and-hardware.md) |
| 7 | [T7 数据集与厂商证据](theory/07-datasets-and-vendors.md) | 形成“什么数据被什么模型消费”的索引 |
| 8 | [T8 可视化产品与异构设备](theory/08-product-and-custom-robots.md) | 分阶段产品任务与界面验收流程 |

开始执行前先完成 [L0 环境搭建](labs/00-environment.md)。以后使用租赁计算机时看 [L4 Linux／AutoDL 迁移](labs/04-gpu-and-transfer.md)。名词随用随解释，另有 [术语与复述卡](glossary-and-review.md)。主管汇报顺序沿用 [汇报大纲](../03-report-outline.md)。

专题补充：[手术机器人：精细操作、医生遥操作与自主研究的边界](topics/01-surgical-robots.md)（2026-10-19）。

## 必须分清的三种“真实”

- **真实公开数据**：L1 下载宇树发布版本的小量元数据和表格。未下载视频，下载目录不是完整 LeRobot 数据集。
- **真实框架格式与执行**：L2–L3 使用官方 LeRobot SDK 写入、读取、训练和预测，数据内容明确为程序合成。
- **真实机器人能力**：需要具体本体、传感器、工具、控制器及现场评估。本手册的 CPU 实验不证明 G1 学会装配或行走。

原先 `learning/01-hole-alignment` 的二维 JSON 只保留为概念示意，不是宇树或 LeRobot 协议。本实验生成的 Unitree 风格采集文件同样标注为教学子集；转换后才由官方 SDK 产生实际 LeRobotDataset。

## 本轮代码和版本

- 独立入口：[lab.py](lab.py)。不连接机器人，不上传数据或模型。
- 官方 LeRobot 固定提交：`ca69a2068462a37f7cdcb74180927a2f863d2bf7`，该提交软件包自报 `0.6.2`，不等同于宣称它是最新稳定版。
- 真实数据固定版本、文件大小与 SHA256：[sources.lock.json](sources.lock.json)。全量视频不在下载列表。
- 各实验输出默认放在仓库 `.build/restart-lab-001/`，被 Git 忽略；换环境后必须重新安装依赖，不能复制虚拟环境。
- 本项目原创代码／文档沿用仓库 MIT。第三方 SDK、数据、权重分别遵循其原许可；下载到本机不改变许可。

## 完成后，你应能讲清什么

1. 一个动作从操作者或策略出发，怎样经过控制器到达设备。
2. 一条记录怎样从采集文件变成图像、状态、动作块和有效位掩码。
3. 模型在拟合什么，训练标签与推理输入为什么不同。
4. 哪些数据、代码和能力可跨本体复用，哪些条件需要重新验证。
5. 怎样把处理步骤做成普通人可操作的产品，实际支持到哪一步。

还需要逐项补齐的物理条件包括 G1 手型、相机安装、工具与力传感器、开放控制接口、操作工位和工艺验收人。现在无需为阅读和 CPU 实验提供远程账号。
