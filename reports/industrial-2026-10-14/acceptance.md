# G1 工业数据与训练流程交付验收

日期：2026-10-14。实际执行平台：macOS arm64、Python3.12。基础数据契约的跨平台 CI 单独记录；官方SDK/ACT、本机Torch教学未据此推断GPU/NPU/机器人或生产环境兼容性。

## 本次交付

- `docs/17–23`：任务闭环、模型与损失、四项能力、工业服务架构、厂商/数据/采购、命令学习与主管问答。
- `deliverables/industrial-report.html`：与上述Markdown同源的离线报告，概览/详读、场景切换、章节导航与打印状态恢复。
- `catalog/industrial_training_routes.json`、`catalog/industrial_hardware_candidates.json`、`evidence/industrial-*.json`：候选路线、接口限制与一手版本/字段证据。
- `synchronize.py`、`industrial_contract.py` 与脚本：因果数值流对齐、接入资料检查、BC/ACT离线推理、PPO教学。

## 实际运行与证据

| 环节 | 实际结果 | 证据 | 边界 |
|---|---|---|---|
| XR形状数据工程 | 8条episode、192时刻、32窗口；原始200文件保留 | `synthetic_acceptance.json`、`synthetic_manifest.json` | 2个虚构通道，不是G1实采或物理仿真 |
| BC CPU训练 | 20步，训练MSE 1.1114→0.1603，检查点恢复误差0 | `synthetic_training_probe.json` | 随机小网络，不是VLA微调；不能据loss证明能力 |
| BC离线推理 | validation窗口预测 `[8,2]` 并逆归一化 | `offline_prediction.json` | 不发送机器人命令 |
| 官方LeRobot导出 | 168train＋24validation帧，动作标签全部往返检查，尾部pad | `sdk/` | 一路相机、整数FPS，SDK固定commit |
| 官方ACT训练 | CPU实际5次更新，L1＋KL，保存权重、config与processor | `act-training.json` | 缩小网络、随机视觉骨干、合成数据，无权重下载 |
| 官方ACT推理 | 使用保存的训练processor，validation预测 `[2,8,2]` | `act-inference.json` | 未把label作为输入；未连接G1 |
| PPO教学 | 60次更新，actor/critic与GAE，固定初始条件平均回报 -34.0066→-2.1380 | `ppo_report.json`、`actor_play.json` | 虚构一维48步有限时域，不含真实接触/步态 |
| 数值时序对齐 | 5个锚点中3个共同有效，缺失/过旧保留invalid | `aligned.json` | 校准统一时钟由外部提供，不自动校时 |
| 工业资料检查 | 缺硬件/时钟/控制器/证据模板按预期拒绝，CLI退出2 | `intake_audit.json` | 文件齐全也不能授权实机或认证工艺 |
| 浏览器检查 | 桌面1440×1100与窄屏390×844，模式/场景/锚点/打印恢复通过 | `browser-qa.json` | 展示与交互验证，不是机器人验证 |
| 核心测试 | 本机52项通过，0失败/错误/跳过 | `tests.json` | 包含时序、伪造哈希、越界路径、名义时间等拒绝用例 |
| 跨平台CI | Ubuntu24.04和Windows各52项通过，CLI与wheel构建成功 | `ci.json` | 基础环境不安装Torch或官方SDK，不能据此声称这些可选路线跨平台通过 |

报告/代码/本地产物一致性检查由 `scripts/verify_industrial_evidence.py` 执行，结果见 `evidence-audit.json`。输出仅表示这些教学记录一致，不将字段齐全或曲线改善解释成工业能力。

[本轮CI实际运行](https://github.com/fengjikui/vla_data_pipeline/actions/runs/38437117883) 对应代码commit `cd193ac8fb5c1e49647362cfab3dab0da3842589`；两个下载的JUnit记录均为52 tests、0 failures/errors/skipped，hash已归档。本机SDK出现重复FFmpeg动态库类的非致命告警；本次回读/训练/推理成功，目标公司平台仍需独立验证。

## 复现

从 [逐条命令手册](../../docs/22-command-learning-lab.md) 第1关开始。基础环境仅看报告一致性：

```bash
uv run --frozen python scripts/verify_industrial_evidence.py
```

这条命令核对已归档JSON与文档hash，不重新训练。只有保留本次本机scratch目录时，加`--check-local-artifacts`核对真实release、checkpoint与全部SDK导出文件。新实验请使用手册的新目录，避免覆盖证据。

重新生成展示页：

```bash
python scripts/build_industrial_report.py
```

可选浏览器QA使用已安装的Playwright，设置`PLAYWRIGHT_MODULE`；如默认Chromium未安装，可通过`REPORT_BROWSER_EXECUTABLE`选择已安装浏览器。执行`node scripts/verify_industrial_report.mjs .build/report-qa`，结果与截图保存在指定目录。

## 实机与工业部署还缺什么

工艺负责人定义螺丝/孔/质量/节拍；确认G1手型、传感/力/工具与控制模式；测量物理同步；实现多传感和工具数据adapter；配置目标模型动作表示；真实固定工位、负载/全身与持出工件试验；公司对象存储、目录事务、权限、重试、监控、备份恢复与SLA。

此次没有采购设备，没有扩大下载公开数据，没有下载预训练VLA权重，没有训练G1行走或执行真机动作。上游候选命令已注明未执行。
