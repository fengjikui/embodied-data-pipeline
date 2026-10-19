# 本轮验证记录与交付边界

日期：2026-10-18。这里记录本轮实际执行结果，不沿用旧报告的通过数字。

## 实际执行

| 项目 | 输入与结果 | 证据范围 |
| --- | --- | --- |
| 真实公开数据下载 | 固定宇树版本，6 个文件，5,835,881 字节，逐文件 SHA256 一致 | 只有元数据与一份数值分片；无视频 |
| 真实表格检查 | 16,576 行，状态与动作均 `[16576,28]`，数值有限 | 不推断控制单位、同步质量或装配适用性 |
| 教学采集 | 4 段 × 20 帧，单相机、28 维教学信号 | 无物理引擎、无真实机器人记录 |
| 官方 SDK 导出与读回 | v3.0；train 60 帧，validation 20 帧；逐帧动作读回一致 | 本项目适配器＋固定官方 SDK |
| 训练批次 | 图像 `[2,3,64,64]`、状态 `[2,28]`、动作 `[2,8,28]` | 当前观测与未来动作标签 |
| 轨迹尾部 | 最后样本填充标记为 false 后跟 7 个 true | 正确跨边界标记，未跨 episode 偷取动作 |
| 官方 ACT 训练 | CPU、1 线程、小网络、seed=1000、5 次更新 | 真实参数更新，随机视觉骨干，无预训练权重下载 |
| 检查点恢复 | 仅传图像与状态，输出 `[2,8,28]`，数值有限 | 标签未作为输入，无机器人命令 |
| 快照与拒绝行为 | 原始／训练快照验证，缺图片、路径越界、NaN、错维度、重复索引等被拒绝 | 10 项独立单元测试；不代表生产管线完整验收 |

最后一次训练日志总损失：10.569、11.877、10.348、8.971、9.604。短训练存在波动；该记录不作为学习到工业技能的证据。

机器可读证据：[local-run-2026-10-18.json](evidence/local-run-2026-10-18.json)。包含源码哈希、SDK 提交、环境版本、来源版本、形状、损失、模型哈希及未验证项。

## 平台与资源

实际官方 SDK／ACT 执行环境为本机 ARM64、Python 3.12.13、Torch 2.11.0、torchvision 0.26.0、LeRobot 源码自报 0.6.2；SDK 提交固定。

训练／编码采用保守线程数。训练前后查看负载、内存与可取得的系统热状态，记录未出现系统热／性能告警；没有测得具体温度。实际训练很短，未运行持续高负载任务。

本机的 PyAV／OpenCV／系统 FFmpeg 组合出现重复 Objective-C 类警告，本次任务仍成功完成；这不是其他平台或任意视频编码组合的兼容认证。若出现崩溃，应在独立环境定位依赖，不能忽略退出码或删除系统库碰运气。

## 怎样复核

在已完成 L0–L3 的环境中，按实际输出目录执行：

```bash
python -m unittest discover -s restart/handbook/tests -v
python restart/handbook/check_docs.py
python restart/handbook/verify_run.py --root .build/restart-lab-001 --training-name act --prediction prediction-verified.json --output .build/restart-lab-001/audit.json
```

最后一条需要先按 L3 保存推理输出为 `prediction-verified.json`。若已经执行 L3，无需重复生成；若未执行，运行：

```bash
python restart/handbook/lab.py infer --root .build/restart-lab-001/dataset --checkpoint .build/restart-lab-001/act/checkpoints/000005/pretrained_model --output .build/restart-lab-001/prediction-verified.json
```

审计核对训练记录、当前代码、源文件、模型及边界掩码。应在同一次固定代码实验后执行；代码改变后不以旧回执冒充新代码已验证。文件快照提供一致性检查，不是不可伪造签名或工艺质量认证。

本轮最终完整复验在新目录 `.build/restart-lab-002/` 完成，训练目录为 `act`、预测文件为 `prediction-verified.json`；通用教程默认使用 `restart-lab-001`。代码、结构与步骤相同。

## 还没有执行的事项

- 新 Ubuntu／Windows 环境的全套 SDK 安装、CUDA 或昇腾训练。
- 完整真实数据＋视频的正式模型训练与泛化评估。
- 其他 VLA、世界模型、IsaacLab 物理仿真或 G1 步态训练。
- G1 真机、头显遥操作、工艺工具接入和装配质量验收。
- 可视化产品、分布式生产数据服务及真实工站运行。

L4–L5 给出准备、版本与条件化操作。拿到对应资源后逐项运行与更新证据即可；当前没有要求租卡或提供远程登录。
