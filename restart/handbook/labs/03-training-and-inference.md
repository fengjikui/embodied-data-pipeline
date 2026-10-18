# L3：官方 ACT 训练、检查点与离线推理

运行位置：L0 环境，CPU 足够。输入：L2 的官方格式教学数据。目标：观察真正的训练与预测链路，不是获得工业技能。

## 1. 再检查资源

```bash
python restart/handbook/lab.py doctor
```

固定使用 1 线程、小批量和 0 个数据加载子进程。保持系统监控可见，长任务压力升高时降低负载或暂停。

## 2. 运行五次参数更新

```bash
python restart/handbook/lab.py train --root .build/restart-lab-001/dataset --output .build/restart-lab-001/act --steps 5
```

程序调用固定 SDK 的官方 `lerobot_train`。模型是 ACT，动作块 8 步、Transformer 维度缩小、batch=2、随机初始化视觉骨干；不下载预训练权重、不上传、不进行机器人控制。

终端完成后打印检查点与日志路径：

```text
.build/restart-lab-001/act/checkpoints/000005/pretrained_model/
.build/restart-lab-001/act.log
```

`--steps 5` 是 5 次更新，不是 5 个完整 epoch。每次训练都使用全新输出目录；正式中断恢复应遵循固定 SDK 的检查点恢复机制，本包装器不自动猜测或覆盖。

## 3. 查看训练记录

```bash
python -c "from pathlib import Path; print('\n'.join(s for s in Path('.build/restart-lab-001/act.log').read_text().splitlines() if 'l1_loss:' in s))"
python -c "import json; from pathlib import Path; d=json.loads(Path('.build/restart-lab-001/act/checkpoints/000005/pretrained_model/config.json').read_text()); print(d)"
```

观察 total loss、L1、KL、学习率与步数。按本配置总损失由 L1 与 10 倍 KL 构成；日志有舍入，不用打印值要求精确等式。5 步损失可能波动，不能据此宣布模型优劣。

`model.safetensors` 是权重，config 是结构与特征约定，processor 文件保存预处理／后处理。数据快照、完整命令、资源记录和模型 SHA256 在 `lab_receipt.json` 等文件中。

## 4. 恢复模型并预测验证集

```bash
python restart/handbook/lab.py infer --root .build/restart-lab-001/dataset --checkpoint .build/restart-lab-001/act/checkpoints/000005/pretrained_model --output .build/restart-lab-001/prediction-verified.json
```

预期预测形状 `[2,8,28]`，`label_passed_as_input=false`，`robot_command_sent=false`。离线运行从验证集读取观测、恢复训练时保存的 processor，预测动作，再还原为原数值尺度；参考动作只用于事后展示。

`--output` 由程序写 UTF-8 JSON，避免 Windows 不同终端的重定向编码差异。输出已存在时换文件名，不静默覆盖。

离线预测不是闭环控制评估，也不会控制 G1。实际运行还需机器人观测接入、动作与控制器适配、频率、状态转换和任务验收。

## 5. 一行行看训练主链路

先读本项目 `lab.py` 的 `train`，看真实调用参数。再打开固定 SDK：

```text
src/lerobot/scripts/lerobot_train.py
src/lerobot/policies/act/modeling_act.py
src/lerobot/policies/act/configuration_act.py
```

查找数据加载、preprocessor、`policy.forward`、loss、`backward`、optimizer 更新和 checkpoint 保存。在 ACT 中跟踪 `batch['action']` 的用途，对照 T5 中重建与 KL；推理则看 `infer` 如何仅选 `input_features`。

## 6. 后续如何换成真实数据

先取得完整、合法、可加载的数据集；确认相机、状态与动作定义；按任务划分并核对统计；再选择模型大小、预训练权重和训练预算。可先用真实数据少步检查接口，再做有固定评估的长训练。

选择 ACT 不代表已经选择 VLA 大模型。想加入语言条件，需选择实际消费语言的策略和对应预处理。不要把 L1 的不完整下载目录直接替换到本命令。

验收记录：输入版本、SDK 提交、训练参数、检查点、预测形状、标签是否泄漏、为什么不能把预测直接发送给 G1。
