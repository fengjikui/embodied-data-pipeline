# G1 EDU 数据工程验收 — 2026-10-08

本次交付包括数据来源与格式说明、存储和版本设计、XR 接入代码、训练读取与导出、逐条手工复现以及实际验收。**工程链路与官方格式互操作已验证；G1 EDU 真机、行走、导航、负载搬运及预训练 VLA 微调尚未验证。**

## 验收结果

| 项目 | 实际结果 | 证据 |
|---|---|---|
| 基础契约/集成测试 | 40 passed；0 failed / 0 skipped | `pytest -q`；包含异常、版本、原始保留、窗口、反归一化与锁覆盖 |
| wheel | `vla_data_pipeline-0.2.0-py3-none-any.whl` 构建成功 | 本机 dist（忽略目录）；跨平台 CI 单独记录 |
| 合成 XR 全链路 | 8 条、192 时刻、32 窗口；train 28 / validation 4 | [synthetic_acceptance.json](synthetic_acceptance.json) |
| 原始文件保留 | 200 个原始文件字节哈希一致；其他模态不丢弃 | 同上；这批仅合成 RGB/JSON，不是 G1 采集 |
| 版本变化 | 同锁/规则复用；规则变化新版本；旧发布校验通过 | 同上 |
| CPU 小模型训练 | 20 steps、1 thread；train MSE 1.11140 → 0.16033；检查点恢复误差 0.0 | [synthetic_training_probe.json](synthetic_training_probe.json) |
| 已有公开小样本 | 3 来源各 6 条：18 条、23,109 时刻、590 窗口；离线复核通过 | [real-sources/acceptance.json](real-sources/acceptance.json) |
| 异常派生测试 | 1 accepted、1 numeric duplicate、3 quarantined | 同上；是故意损坏的测试副本，不算新增真实示范 |
| 官方 LeRobot SDK | 合成 XR 与真实来源 G1 均实际导出为 v3.0，并由官方 loader / DataLoader 回读 | [SDK 记录目录](sdk/) |
| 本机资源 | 多次读取负载、内存压力和热状态，数值库/转码/CPU 探针保守线程 | [资源快照](resource_snapshots.json) 与 SDK 环境记录；无温度数值可报告 |

train loss 下降仅是接口验证，validation MSE 为 0.76562；不能由此声称模型已具备真实任务能力。

## 数据版本

- 合成教学 release：`97e4d6de14e3b78f25718b07`。
- 合成另一个 recipe release：`dd96bdf832a7910e61957802`。
- 已有公开小样本本次 release：`24de209e78beda531a6831a6`。
- 两者对应的数据包实现 SHA256：`e7ec3c69d8d855bea7dd8e7fd28464128cbb60e928a70de82813e31da812f274`。
- 旧 2026-09-12 的报告/PPT/HTML 和旧证据保留，没有混写成当前数据版本。

`raw_download_bytes` 在合成验收中是锁定文件字节数，合成过程没有网络数据下载。本次没有扩大公开原始数据采样；独立 SDK 环境安装了软件依赖，导出数据属于已有样本的派生产物。

## 官方 SDK 互操作细节

固定官方 LeRobot commit `ca69a2068462a37f7cdcb74180927a2f863d2bf7`，包版本 0.6.2；独立 Python 3.12.13 环境，Torch 2.11.0、NumPy 2.2.6、PyAV 15.1.0、PyArrow 25.0.1。源码 pin 与完整依赖/平台快照分开保存。

| 来源 | split | 完整原生帧 | 官方 DataLoader action shape | 全帧 native label 最大误差 |
|---|---|---:|---|---:|
| g1_edu_synthetic | train | 168 | `[2, 8, 2]` | 5.72e-08 |
| g1_edu_synthetic | validation | 24 | `[2, 8, 2]` | 5.72e-08 |
| g1_real | train | 443 | `[2, 8, 43]` | 5.87e-08 |
| g1_real | validation | 241 | `[2, 8, 43]` | 5.88e-08 |

每个 episode 验证：最后一个 anchor 仅首步有效，余下 7 步 `action_is_pad=True`，padding 不串到下一轨迹；DataLoader 使用 0 workers，batch 数值有限。逐 episode 全部动作标签与 canonical 对比通过；原始分辨率一路 RGB，而非 64 像素 smoke anchors（教学原图本身为 64×64）。

SDK 产物保留来源锁、recipe 和统计 sidecar；验收 JSON 含每个导出文件 SHA256。sidecar 是审计信息，不自动替换 SDK 的模型统计。缺失真实关节语义仍标未知；SDK 正式格式可读取不代表物理命令可执行。

官方 SDK 实际执行平台为 **本机 ARM64**；不声称已在 Linux/Windows 执行可选 SDK、GPU 或机器人环境。运行中观察到 PyAV 与系统 FFmpeg 重复动态库类的非致命告警，本次回读/窗口/标签检查通过；目标环境仍须单独验证。Ubuntu 24.04 与 Windows 各通过 40 项测试（0 skipped）、CLI 与 wheel 构建；[实际 CI 运行](https://github.com/fengjikui/embodied-data-pipeline/actions/runs/37755702032)，[运行及测试计数](ci.json)。验证代码 commit 为 `d9fff32d701ad001ce1517b36e61d928be38be4c`，之后文档证据归档不改变数据包代码哈希。

## 复现入口

- [完整手工教程](../../docs/14-g1-edu-manual-reproduction.md)：从生成 raw 到 batch，每一步有命令与预期结果。
- `scripts/verify_g1_engineering.py --workdir <fresh-dir> --report-dir <report-dir> [--train-steps 20]`：小样本自动复现。
- 独立 SDK 环境：`scripts/verify_lerobot_export.py --release ... --raw-root ... --source ... --output-root <fresh-dir> --report-dir ...`。
- `scripts/verify_delivery.py --report-dir <new-dir>`：复核既有 3 类公开小样本，默认使用仓库 data 根。

## 接下来需要真机确认的内容

具体自由度、双手类型、关节顺序/单位、控制方式与频率、摄像头及标定、采集/接收/决策/动作生效时间。以采集契约模板完成交接，然后补对应任务的真实示范/日志、模型专用变换、仿真和受控真机评测。当前未实现 MCAP/ROS2 行走 adapter、多相机/力/IMU 训练视图、自动重定向、分布式作业与对象存储。
