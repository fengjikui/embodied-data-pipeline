# 逐条命令学习：数据、训练、推理与工业接入

目标：每次执行后都知道输入、输出、关键字段与限制。第1–5关不需要机器人/权重/大数据；第6关使用官方 LeRobot ACT，但仍是合成教学；第7关展示真实上游路线的准备步骤，不冒充已执行的 VLA/行走实验。

## 0. 环境和资源

在仓库根目录，Python3.12；Linux 命令如下。Windows PowerShell 的 `uv run ...` 命令相同，虚拟环境路径 `bin/python` 改为 `Scripts/python.exe`。不要跨操作系统复制虚拟环境到服务器。

```bash
uv sync --frozen --extra dev --extra train
uv run --frozen python scripts/resource_status.py
```

Torch 软件包可能较大；仅CPU演示可按 [独立CPU环境](16-training-export.md#cpu-训练探针) 安装 CPU wheel，或者使用已安装环境的python执行下文脚本。`--offline` 只能使用已有缓存，不会补齐依赖。训练前后及期间查看内存/热压力，采用1线程与小批次；无温度读数时不声称具体温度。

Linux：

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export PYTHONUTF8=1
```

PowerShell：

```powershell
$env:OMP_NUM_THREADS="1"
$env:OPENBLAS_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
$env:PYTHONUTF8="1"
```

以下使用新目录 `data/learning-001`。若已存在，替换为`learning-002`并同步更改后续路径，不删除旧版本。

## 1. 看懂原始数据

```bash
uv run --frozen python scripts/generate_g1_demo.py --output data/learning-001
uv run --frozen python -c "import json; from pathlib import Path; d=json.loads(Path('data/learning-001/capture/demo_task/episode_0000/data.json').read_text(encoding='utf-8')); print(d['text']); print(d['data'][0]); print(d['data'][1])"
```

应看到8个episode，每条24个时刻；两维虚构state与action，还有图片路径。请回答：哪个字段是输入状态？哪个字段是监督标签？图片本身在哪里？本数据不是G1实采，也不是物理仿真。

## 2. 手动转换、注册、发布

```bash
uv run --frozen vla-pipeline import-unitree --source-dir data/learning-001/capture --mapping data/learning-001/mapping.json --output data/learning-001/prepared
uv run --frozen vla-pipeline register-local --source-dir data/learning-001/prepared --descriptor data/learning-001/prepared/source.json --root data/learning-001/store --output data/learning-001/sources.lock.json
uv run --frozen vla-pipeline run --lock data/learning-001/sources.lock.json --root data/learning-001/store --recipe configs/g1_edu_interface_recipe.json --offline
uv run --frozen python -c "import json; from pathlib import Path; print(json.loads(Path('data/learning-001/store/latest.json').read_text())['release_id'])"
```

记下实际打印的release，替换下文所有`<release_id>`，不能原样粘贴。应有8条accepted、192个时刻、32个窗口，train28/validation4个窗口。解释 `mapping` 决定了什么，为什么 `idx/fps` 是名义时间而非实测同步。

```bash
uv run --frozen vla-pipeline verify data/learning-001/store/releases/<release_id>
uv run --frozen python scripts/inspect_training_batch.py --release data/learning-001/store/releases/<release_id> --source g1_edu_synthetic
```

应有 image `[3,64,64]`、state `[2]`、actions/mask `[8,2]`，语言字符串。看 `canonical/` 原生动作与 `statistics.json`，解释NPZ为何归一化。完整中间产物逐项说明见 [旧手工教程](14-g1-edu-manual-reproduction.md)。

## 3. 从训练走到推理

```bash
uv run --frozen --extra train python -m vla_pipeline.training --release data/learning-001/store/releases/<release_id> --output data/learning-001/training --steps 20 --threads 1
uv run --frozen --extra train python scripts/infer_bc_offline.py --release data/learning-001/store/releases/<release_id> --source g1_edu_synthetic --checkpoint data/learning-001/training/g1_edu_synthetic.pt --output data/learning-001/prediction.json
uv run --frozen python -c "import json; from pathlib import Path; d=json.loads(Path('data/learning-001/prediction.json').read_text()); print('instruction:',d['language']); print('prediction:',d['native_prediction'][0]); print('label:',d['native_label'][0]); print('robot_command_sent:',d['robot_command_sent'])"
```

训练会保存模型/优化器以及数据/统计哈希，推理从validation取一个窗口、恢复模型、前向预测并逆归一化，输出`[8,2]`。应有`robot_command_sent=False`。**模型输出和真实标签不同是正常的**，20步接口探针不是学会工厂动作。

看代码顺序：`dataset.WindowDataset.__getitem__` → `training.TinyMultimodalBC.forward` → `training.masked_mse` → `loss.backward/optimizer.step` → `infer_bc_offline.py`。解释训练用target，而推理不应使用target；执行器为什么不能直接接这两维虚构动作。

## 4. 看异步数值流怎样对齐

```bash
uv run --frozen python scripts/align_numeric_streams.py --input configs/async_numeric_demo.json --output data/learning-001/aligned.json
uv run --frozen python -c "import json; from pathlib import Path; d=json.loads(Path('data/learning-001/aligned.json').read_text()); print(d['timestamps']); print(d['streams']['wrist_force']); print(d['all_streams_valid'])"
```

应有共享有效时刻`3/5`、mask `[false,true,true,false,true]`。在t=0不能读取0.01秒才发生的力数据；在t=0.15关节样本已经过旧，输出null，不用0.199秒未来值补它。

读`src/vla_pipeline/synchronize.py`：`searchsorted(...,side='right')-1` 找最近过去样本，`max_age_s`决定陈旧阈值。输入要求统一时钟；真实clock offset/drift未由脚本测量，也未把这些字段送入BC模型。帧率相同不能证明设备已同步。

## 5. PPO：检查rollout，再只用actor推理

```bash
uv run --frozen --extra train python scripts/ppo_position_lab.py train --output data/learning-ppo-001 --updates 60
uv run --frozen --extra train python scripts/ppo_position_lab.py play --checkpoint data/learning-ppo-001/ppo_actor_critic.pt --output data/learning-ppo-001/play.json
uv run --frozen python -c "import numpy as np; a=np.load('data/learning-ppo-001/first_rollout.npz'); print({k:a[k].shape for k in a.files}); print('r=',a['reward'][0,0],'V=',a['value'][0,0],'A=',a['advantage'][0,0],'return=',a['returns'][0,0]); print('last done=',a['done'][-1])"
```

应有obs `[48,16,4]`，action/reward/logprob/value/advantage `[48,16]`，48步末尾是真终止。这里16是并行的虚构数值环境，不是16个机器人。比较同一固定初始条件的前后平均回报；曲线不保证每次单调改善。

读`ActorCritic`、`transition`、GAE反向循环、ratio/clamp，再读`evaluate`。回答：奖励是什么？critic拟合什么？部署为什么只用actor输出动作？raw Gaussian action 与tanh后的实际动作是什么关系？该示例不是G1、不含接触物理、不是步态仿真。

## 6. 官方LeRobot：真的用框架训练，而不是只写训练命令

这是可选独立环境。**不要把官方SDK的依赖混进基础 `.venv`**。该步骤需要安装软件包，但不下载VLA权重或完整数据集。先看 [固定SDK桥](16-training-export.md#两条-g1-转换路线)；环境创建与导出命令在下面重列。

Linux示例，Windows路径和CPU wheel按对应平台准备：

```bash
uv venv .venv-sdk --python 3.12
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/huggingface/lerobot.git .build/learning-lerobot-sdk
git -C .build/learning-lerobot-sdk checkout ca69a2068462a37f7cdcb74180927a2f863d2bf7
uv pip install --python .venv-sdk/bin/python -e ".build/learning-lerobot-sdk[dataset]" -e . "accelerate==1.15.0"
uv pip freeze --python .venv-sdk/bin/python > data/sdk-environment.txt
```

PowerShell先设置`$env:GIT_LFS_SKIP_SMUDGE="1"`再运行不带前缀赋值的git clone。Linux基础Torch默认可能带CUDA软件包；CPU实验建议先装匹配Torch/torchvision CPU wheel再解析SDK。目标OS必须重建验证；本次实际官方训练证据是本机 ARM64，不是Windows/GPU/NPU认证。

导出train与validation两份独立数据，原生动作、完整帧与SDK统计：

```bash
.venv-sdk/bin/python scripts/verify_lerobot_export.py --release data/learning-001/store/releases/<release_id> --raw-root data/learning-001/store/raw --source g1_edu_synthetic --output-root data/learning-sdk-001 --report-dir reports/local-learning-sdk
.venv-sdk/bin/python scripts/run_act_interface_probe.py --dataset-root data/learning-sdk-001/train --repo-id local/g1_edu_synthetic-train --output data/learning-act-001 --report reports/local-learning-act.json
.venv-sdk/bin/python scripts/infer_act_offline.py --checkpoint data/learning-act-001/checkpoints/000005/pretrained_model --dataset-root data/learning-sdk-001/validation --repo-id local/g1_edu_synthetic-validation --output data/learning-act-001/prediction.json
```

应有168train/24validation帧，官方ACT完成5个更新，保存`safetensors`、config、训练前后processor及优化器运行状态；离线预测原生动作块`[2,8,2]`。ACT没有语言条件，此脚本不把字符串任务假装接进VLA。其随机初始化视觉骨干不下载权重，网络缩小只为教学；不是标准模型性能实验。

`run_act_interface_probe.py` 保存真实参数与loss日志摘要；内部本质是：

```bash
python -m lerobot.scripts.lerobot_train --dataset.repo_id=local/g1_edu_synthetic-train --dataset.root=data/learning-sdk-001/train --dataset.video_backend=pyav --policy.type=act --policy.device=cpu --policy.push_to_hub=false --policy.pretrained_backbone_weights=null --policy.chunk_size=8 --policy.n_action_steps=8 --policy.dim_model=64 --policy.n_heads=4 --policy.dim_feedforward=128 --policy.n_encoder_layers=1 --policy.n_decoder_layers=1 --policy.n_vae_encoder_layers=1 --policy.latent_dim=8 --batch_size=2 --num_workers=0 --steps=5 --save_freq=5 --log_freq=1 --env_eval_freq=0 --eval_steps=0 --wandb.enable=false --output_dir=data/learning-act-manual-001
```

这条命令只在上面SDK环境中执行，不能使用基础环境的python。内部将Hub/Transformers设为offline、防止意外下载；不要向内部工厂数据添加Hub上传参数。

## 7. 真实G1路线：哪些命令现在只是候选

### 7.1 宇树上肢IL

固定源码版本，自己的单独目录；不执行真机例子：

```bash
git clone https://github.com/unitreerobotics/unitree_lerobot.git
cd unitree_lerobot
git checkout 41c2805742de879ddab2d8d6beaeaf215f876395
```

阅读其README的转换、ACT/Diffusion/π/GR00T训练和回放。模型与数据的版本、手型/关节、动作含义和控制器匹配后才填写对应参数。旧名`unitree_IL_lerobot`目前重定向到该仓库；其子目录与本项目固定官方SDK并非同一个环境。**本次训练的是官方SDK的ACT教学，不是该宇树fork的真机训练。**

### 7.2 宇树UnifoLM-WLA

```bash
git clone https://github.com/unitreerobotics/unifolm-wla.git
cd unifolm-wla
git checkout 0a1aa87be8f775c7883fcd27216e3666ac18a8c5
```

先读`docs/robot_action_state_processing_en.md`和`docs/train_action_expert_en.md`，按54/60维槽位、mask、相对位姿和统计建立模型视图。上游微调入口为：

```bash
base_model_dir=/company/models/UnifoLM-WLA-1.0-Base bash examples/unifolm_wla/train_files/run_finetune_mmdit_frozen_vlm.sh
```

这是Linux候选命令，**本次未执行**。须先按上游安装环境、准备授权模型本地目录、配置数据路径/动作槽位/相机、训练预算与算子兼容性。不能把`/company/...`占位路径原样运行。上游默认冻结VLM、训练动作专家/状态投影，服务器当前Dex1接口的限制见 [来源与采购](21-ecosystem-data-hardware.md)。

### 7.3 行走RL

```bash
git clone https://github.com/unitreerobotics/unitree_rl_lab.git
cd unitree_rl_lab
git checkout 4960b84732b0c2ec593dccbfe963fda1bcd7b1e3
```

按官方README准备兼容的IsaacLab环境和目标G1模型，限制并行环境/渲染与资源后，可使用上游任务入口：

```bash
python scripts/rsl_rl/train.py --headless --task Unitree-G1-29dof-Velocity
python scripts/rsl_rl/play.py --task Unitree-G1-29dof-Velocity
```

这两条仅是核对的官方入口，**本次未安装IsaacLab或执行**。默认并行环境可能较大，不直接照搬到本机；实际参数以锁定任务配置/`--help`核对。actor观测、动作scale、default姿态、PD增益与训练机器人参数均需保留，实机还要sim2sim与合同核验。

### 7.4 全身路线

[GR00T-WBC/SONIC](https://github.com/NVlabs/GR00T-WholeBodyControl) 的锁定版本与文档见源码证据。它有独立数据采集、VLA训练、运动控制/部署环境，不能用上肢LeRobot动作代替SONIC的表示。克隆时Git LFS可能拉取大型二进制；研究源码可用`GIT_LFS_SKIP_SMUDGE=1`，运行时必须按所选模型清单显式补齐、校验资产，不能把LFS指针误作权重。此次未下载全身权重、未运行机器人。

## 8. 缺真实配置时让检查器明确失败

```bash
uv run --frozen python scripts/check_industrial_contract.py --contract configs/industrial_intake.template.json --evidence-root . --output data/learning-001/intake_audit.json
```

预期退出码 **2**，因为机器人配置、时钟、控制器、通道语义及附件未填写。Linux用`echo $?`，PowerShell用`$LASTEXITCODE`查看；不是意外运行失败。填好的资料检查通过也只代表字段/哈希齐全，不能授权实机动作。

## 9. 你能逐项说清楚就学到了

| 问题 | 达标答案 |
|---|---|
| 开放/遥操作/仿真/LeRobot关系？ | 获取权利、控制方式、环境与格式是不同维度 |
| BC的标签？ | 有明确物理含义的示范动作，不是success或视频 |
| PPO的标签？ | 根据rollout奖励构造优势/回报，无需每步专家动作 |
| 为什么不能直接把输出发G1？ | 虚构/来源动作需匹配本体、控制器、单位、时序与验证 |
| 上下身如何配合？ | 共享权限/时序/坐标，分阶段或统一全身控制器 |
| 做到哪一步？ | 小样本数据/训练/离线推理；尚无真实装配/行走验证 |

每次只学一关，先用自己的话解释，再看下一关。主管汇报按 [讲稿](23-supervisor-script.md) 的7段展开，不必在首次汇报展示全部公式。
