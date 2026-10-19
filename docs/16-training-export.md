# 数据字段、训练张量与模型导出

本文解释“最终能送入训练的格式”究竟是什么。文件格式、模型输入张量和机器人动作语义是三层不同契约：Parquet/NPZ 管序列化，Dataset/transform 管张量，控制器契约管物理意义。三者都要正确。

## 1. 本项目的四种实际格式

### A. 宇树 XR 原始格式：JSON + 图片

上层通常是 `info/text/data`；每行 `idx/colors/states/actions`，具体部件在 `left_arm/right_arm/left_ee/right_ee/...` 中。目录和字段由官方版本及真实采集决定，不能仅按产品名推断。新 adapter 按 mapping 明确抽取字段并保留原始所有文件；不增加不存在的关节。

### B. 实验室入口 `lab_json_v1`

来源描述 `source.json`：

| 字段 | 含义 |
|---|---|
| `id/revision` | 来源及不可改写批次；跨设备、控制器或关节契约应隔离 |
| `embodiment` | 精确机器人/手型/控制配置描述；不是模型自动适配代码 |
| `origin_namespace` | 原始采集身份命名空间，防止多个派生集重复计数 |
| `license` | 已核对的使用/内部授权说明；不等于自动法律判定 |
| `episode_files` | 要处理的完整 episode JSON 相对路径 |
| `extra_files` | 原始快照、映射、标定等需一并锁定的其他文件 |
| `state_names/action_names` | 按向量顺序排列的通道名；提供时必须与维度一致且不重复 |
| `action_contract` | 动作类型、单位与控制器等声明；目前保留而不完成物理校验 |
| `semantics_status` | 当前 XR 转换保留 unknown；不允许以 importer 代替部署验证 |

每个 episode：

```json
{
  "episode_id": "example_001",
  "origin_group": "lab:session_001",
  "fps": 20,
  "video": "media/example_001.mp4",
  "video_offset": 0,
  "success": null,
  "timestamp_basis": "nominal_idx_over_fps_NOT_measured_hardware_time",
  "alignment_assumption": "请填写真实时钟与延迟说明",
  "steps": [
    {"timestamp": 0.0, "state": [0.1, 0.2], "action": [0.12, 0.22], "language": "教学指令"},
    {"timestamp": 0.05, "state": [0.11, 0.21], "action": [0.13, 0.23], "language": "教学指令"}
  ]
}
```

这段两维示例不是 G1 关节定义。`video_offset` 表示 episode 时钟到视频 PTS 的源内偏移；`timestamp` 是秒。即使偏移和 PTS 对齐，也不自动证明曝光/接收/决策/动作生效延迟正确。`success=null` 不进入专家成功标签。

### C. 完整轨迹 `canonical/*.parquet + *.json`

一个 episode 一个 Parquet，四列：

| 列 | 当前 Arrow 推断类型 | 每行含义 |
|---|---|---|
| `timestamp` | double | 原始轨迹中的秒数 |
| `state` | list<double> | Ds 个状态值，原生数值与顺序 |
| `action` | list<double> | Da 个动作值，原生数值与顺序 |
| `language` | string | 在该时刻可用的指令/文字 |

配套 JSON 保存来源、原始 episode、origin_group、split、embodiment、名称、fps、成功标签、语义状态、质量、同步假设、来源字段和数值 fingerprint。视频在锁定的 raw 中；canonical 没有把完整图像塞进 Parquet。

**这是本项目定义的中间轨迹格式，不是 LeRobot 的正式 schema。** 它保留所有接受轨迹的数值时刻，便于审计和重新生成训练视图。深度、IMU、力等目前保留在原始层，并不在这四列中；扩展时要增加具名字段与 schema 版本。

### D. 接口训练视图 `training_view_v1` / `interface_smoke`

每个 NPZ 含同一个 episode 的若干训练 anchors。定义：N=anchors 数，S=图片边长，H=动作 horizon，Ds=状态维度，Da=动作维度。

| NPZ 字段 | dtype / shape | 语义 |
|---|---|---|
| `image` | uint8 `[N,S,S,3]` | 选择源时钟上的过去 RGB 帧；当前 square resize，无相机标定修正 |
| `state` | float32 `[N,Ds]` | anchor 状态；使用该来源 train 统计归一化 |
| `actions` | float32 `[N,H,Da]` | 从 anchor 起的 H 个原生动作，归一化；越过 episode 末尾的部分为零 |
| `action_mask` | bool `[N,H,Da]` | 哪些动作元素真实存在；padding 不贡献 loss |
| `language` | NumPy Unicode `[N]` | anchor 当时的指令；不是某个模型的 tokenizer 输出 |
| `anchor_index` | int64 `[N]` | 原始完整轨迹中的行位置 |
| `timestamp` | float64 `[N]` | anchor 的 episode 秒数 |
| `video_pts` | float64 `[N]` | 实际选择的视频 PTS，用于检查对齐 |

NPZ 使用 `allow_pickle=False` 读取，不存可执行 Python 对象。Unicode 指令跨平台以 Unicode 数组保存；JSON 显式 UTF-8。

默认 S=64、H=8、anchor stride=10、最多 64 anchors。这是节省资源的工程验证配置；不能直接当成 π0、GR00T 或其他预训练 VLA 的正确分辨率、图像数和 horizon。

## 2. 从一条轨迹到一个训练样本

假设某任务 T=100、20Hz，选择 t=90，H=8：

- 输入：不晚于该时刻的图像、`state[90]`、当前可用指令。
- 监督：`action[90:98]`，8 步均有效。
- 若 t=98：只有 `action[98:100]` 有效，其余 6 步 padding，mask 为 false。
- 不能为了凑齐 H 步而读取下一个 episode 的动作，也不能把 t+1 的状态/图像作为 t 的观察。

动作标签使用当前行开始的 source action。若目标框架要求下一控制周期开始的标签或已有延迟校正，必须显式声明新 recipe/adapter，不能悄悄移动一个时刻。

当前图像对齐允许最多 1 微秒的浮点 PTS 差异，拒绝超过 1.5 个采样周期的陈旧帧。这是源文件时钟的工程检查，物理可用时刻仍未实测。语言事件只使用 timestamp 不晚于 anchor 的标注；事后成功标签可用于筛选/评估，不应作为当前观察输入泄露未来结果。

## 3. 归一化与动作还原

每个来源，仅用 train 完整轨迹拟合：

`z = (x - mean_train) / max(std_train, 1e-6)`

训练和 validation 使用同一统计。动作 mask 无效部分在归一化后再次置零。

还原：

`native_action = predicted_z * std_train + mean_train`

还原得到的是**该 source 的原生动作单位/顺序**。它还不是可以发送给任意 G1 的合法命令。实际控制还需：名称映射、绝对/增量语义、单位、参考系、限位、夹爪/灵巧手、控制频率和延迟。生产 checkpoint 要携带或锁定统计和控制契约，不能误用另一份 statistics.json。

当前精确去重比较同 embodiment 的时间、state、action 数值，文字/视频重编码不能逃过数值去重。近重复尚未实现；origin_group 仍需要原始 session 信息。失败数据可以用于价值/恢复/RL 等目标，但本项目 smoke 视图没有成功筛选，不能默认是专家训练集。

## 4. 模型实际收到什么 batch

`WindowDataset` 返回图像 CHW float32 `[3,S,S]`、state `[Ds]`、actions `[H,Da]`、mask `[H,Da]`、语言字符串及定位信息。它一次缓存指定数量的 episode NPZ，默认 1；压缩 NPZ 仍会解压整个 episode 文件，尚不是十亿样本的流式存储。

使用 PyTorch DataLoader 的最小例子，`<release_id>` 先替换：

```python
from torch.utils.data import DataLoader
from vla_pipeline.dataset import WindowDataset
from vla_pipeline.training import TinyMultimodalBC, tokenize, masked_mse

rows = WindowDataset("data/g1-demo/store/releases/<release_id>", "g1_edu_synthetic", "train")
batch = next(iter(DataLoader(rows, batch_size=4, shuffle=False, num_workers=0)))
model = TinyMultimodalBC(state_dim=2, action_dim=2, horizon=8)  # 教学通道
prediction = model(batch["image"], batch["state"], tokenize(batch["language"]))
loss = masked_mse(prediction, batch["actions"], batch["action_mask"])
loss.backward()
```

实际 batch：image `[B,3,S,S]`、state `[B,Ds]`、actions/mask `[B,H,Da]`。训练探针使用 UTF-8 字节 toy tokenizer；真正 VLA 必须使用其预训练视觉处理、tokenizer、状态编码、动作头和 loss。

### CPU 训练探针

项目已有 train 依赖时，按手册运行 `python -m vla_pipeline.training --release ... --steps 20 --threads 1`。仅做 CPU 演示的 Linux/Windows 环境，可另建环境使用官方 CPU wheel，避免默认 CUDA 软件包：

```bash
uv venv .venv-cpu --python 3.12
uv pip install --python .venv-cpu/bin/python -e .
uv pip install --python .venv-cpu/bin/python torch --index-url https://download.pytorch.org/whl/cpu
uv pip freeze --python .venv-cpu/bin/python > data/cpu-environment.txt
.venv-cpu/bin/python -m vla_pipeline.training --release data/g1-demo/store/releases/<release_id> --output data/g1-demo/training-cpu --steps 20 --threads 1
```

Windows 将 `.venv-cpu/bin/python` 换成 `.venv-cpu/Scripts/python.exe`。上述 CPU 安装源面向 Linux／Windows；其他平台应按官方支持选择安装源与对应 wheel。此独立 CPU 环境不是本项目 uv.lock 的完全重现，首次验收后保存其 freeze、Python 和平台记录；严格内网复现应使用这份独立环境的固定依赖/wheel 清单。

## 5. LeRobot 是另一种正式训练数据布局

典型 v2.1：每条 episode 一个 Parquet/视频，JSON/JSONL 元数据；v3：多个 episode 可共享 Parquet/视频，元数据记录 episode 的文件编号、偏移和长度。来源的 `meta/info.json` 中版本和 path 模板才是解析依据，不能只看文件后缀。

[官方 LeRobot v3 说明](https://huggingface.co/docs/lerobot/lerobot-dataset-v3) 描述了新布局。当前核心 reader 已验证固定 v2/v3 小样本，**不是全版本读取器**。新的最新 SDK 包括不同元数据布局，扩展需按 pinned 实际样包验证。

### 两条 G1 转换路线

**路线 1：宇树官方工具。** 按固定版本的 [unitree_IL_lerobot](https://github.com/unitreerobotics/unitree_IL_lerobot) 配置 G1 与实际手型，在该工具自己的环境转换原始 XR 数据。这有官方机器人配置和训练范例。注意：本次核查版本的 `json_to_lerobot` 在目标 `HF_LEROBOT_HOME/repo_id` 已存在时会删除它，默认转码并行度也较高；必须使用新的 repo_id/缓存目录，先降低 image_writer 配置，并在副本上运行。不要把 `--push_to_hub` 添加到内部数据命令中。该路线本次只核对源码，没有连接 G1 或执行官方训练。

**路线 2：本项目可选官方 SDK 桥。** 已接受来源的完整原始 RGB、未归一化 state/action 和逐时刻语言，调用官方 `LeRobotDataset.create/add_frame/save_episode/finalize` 以单线程 H.264 写入，随后用官方 reader 核对帧数、首尾 batch。它不会把 smoke 的 64 像素 anchors 假装成完整 VLA 数据。

桥固定 SDK commit：`ca69a2068462a37f7cdcb74180927a2f863d2bf7`。这与宇树 fork 的 SDK 不是同一个版本。需要单独 Python 3.12 环境；该上游源码约束 Torch <2.12、NumPy <2.3 和 dataset 的 PyAV <16，因此不要直接覆盖已有 `.venv`。

安装示例，需联网下载依赖，但不下载数据或模型；在公司 Linux 环境首次执行并保存独立锁/freeze：

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/huggingface/lerobot.git .build/lerobot-sdk
git -C .build/lerobot-sdk checkout ca69a2068462a37f7cdcb74180927a2f863d2bf7
uv venv .venv-lerobot --python 3.12
uv pip install --python .venv-lerobot/bin/python -e ".build/lerobot-sdk[dataset]" -e .
uv pip freeze --python .venv-lerobot/bin/python > data/lerobot-environment.txt
```

Linux 若只验证格式，可先安装匹配该 SDK 的 CPU Torch/torchvision wheels，再安装其他依赖；真实 VLA 训练则按选定 CUDA/NPU 框架配置。Windows clone 前设置 `$env:GIT_LFS_SKIP_SMUDGE="1"`，然后执行不带前置环境赋值的 git clone；Python 路径换成 `Scripts/python.exe`；可选桥的各平台真实执行情况与核心 CI 分开记录。

只导出一个来源和一个 split：

```bash
.venv-lerobot/bin/python -m vla_pipeline.cli export-lerobot --release data/g1-demo/store/releases/<release_id> --raw-root data/g1-demo/store/raw --source g1_edu_synthetic --split train --output data/g1-demo/lerobot-train --repo-id local/g1-edu-demo-train
```

validation 使用不同目录和 repo_id 单独导出。`repo-id` 是本地 SDK 的标識参数，这个命令没有上传步骤。output 已存在会拒绝覆盖；未写出 `pipeline_export_receipt.json` 的半成品不能视作成功导出。若 SDK 原始读取失败，保留错误证据，检查该固定版本的 video backend、依赖、文件和编码器，而不是绕过回读。

桥限制：一路 RGB、整数 fps、零起点等间隔轨迹；无隐式重采样/关节重定向；未自动把失败筛成专家；缺少真实关节名时输出 `unverified_action_i` 名称并保留未知语义。LeRobot 原始 action 不做本项目 z-score，正式训练框架应使用自己的 train 统计。SDK 数据文件不直接携带每个 NPZ 的 action_mask，后续窗口由框架生成 padding；本次官方 SDK 的末尾窗口重复该 episode 最后一个动作，并标记 `action_is_pad`；这与 smoke NPZ 的零 padding 不同。验证框架的 loss 是否使用 pad mask。

导出训练集的 SDK meta 统计仅来自训练集。validation 独立包可能也生成自己的 meta 统计，训练时**不可用 validation 的统计替换训练统计**。框架支持显式 episodes 划分时，也可以设计一个联合导出并固定 splits；这不是当前桥的实现。

### 官方 SDK 自动验收脚本

在上述独立 SDK 环境中，还可以一次导出 train/validation，并检查每个 episode 末尾的 8 步动作窗口 padding、全部帧的 canonical 动作标签及导出文件哈希：

```bash
.venv-lerobot/bin/python scripts/verify_lerobot_export.py --release data/g1-demo/store/releases/<release_id> --raw-root data/g1-demo/store/raw --source g1_edu_synthetic --output-root data/g1-demo/lerobot-acceptance --report-dir reports/local-sdk-check
```

本次已经在本机 ARM64 的独立官方 SDK 环境执行；结果和版本见 [验收记录](../reports/g1-edu-2026-10-08/acceptance.md)。基础 CI 与 SDK 的跨平台情况分别说明。本机环境出现 PyAV/系统 FFmpeg 动态库重复类的非致命告警；本次回读与窗口检查通过，但这仍是平台兼容性事项，不能扩展为全部环境已验证。

## 6. “格式可读取”之后，如何进入选定模型

| 训练路线 | 需要再明确的内容 | 当前状态 |
|---|---|---|
| 本项目 Tiny BC | NPZ、归一化 state/action、字节 tokenizer、masked MSE | 小型 CPU 工程验证可运行 |
| LeRobot ACT / diffusion 等 | 正式 dataset key、相机、state/action 维度、chunk/pad mask、checkpoint配置 | 官方 SDK 桥后还需模型专用配置与训练验收 |
| π 系列 / openpi | checkpoint 对应的数据 transform、图像名/尺寸、动作空间、horizon、统计、框架环境 | 已有研究说明；未运行预训练微调 |
| Isaac GR00T | 模型版本的 modality/embodiment 配置、state/action 索引、图像/语言、数据格式版本 | 需按具体 checkpoint 官方要求适配；不能把 43 维 G1 数据当本机默认 |
| G1 行走 RL | 仿真环境、observation/action/reward/done、控制频率、URDF、随机化 | 当前仅需求与官方工具索引；不通过操作 NPZ 直接训练 |
| 导航 | 地图/视觉、位姿、目标、策略/规划、碰撞/接管日志 | 当前仅采集设计；待任务和传感器确认 |
| 世界模型 | 动作条件状态/视频序列、未来监督、时间跨度和评测 | 可复用原始数据管理；专用 exporter 未实现 |

正式微调至少要完成：选定机器人任务与验收 → 确认动作/时钟契约 → 选定模型和固定 checkpoint → 使用模型官方加载器核对一个 batch → loss/梯度/checkpoint 小试 → 固定 holdout 的离线与仿真评测 → 受控真机闭环。训练框架可能已有脚本，不需要从零写 optimizer，但 robot adapter、数据 transform 和能力评测仍是实验室的工作。

## 7. 格式验收清单

- 原始文件锁、图像/数值行数、episode 边界与 frame_index 对应。
- 输入时刻上的图像/语言可用性，缺失时间和实际延迟假设明确。
- 每个数值通道的名称、单位、参考系、绝对/增量动作、手部定义。
- 训练/验证 origin_group 无交叉，统计只来自 train。
- window 不跨轨迹，mask 正确，反归一化能还原原始标签。
- 官方模型 loader 真正成功读取，不以 JSON/Parquet 可打开代替。
- checkpoint 绑定数据/统计/代码版本，恢复训练/推理结果可检查。
- 实际机器人任务成功率、接管/失败、控制延迟等单独验收。

前几项属于本次数据工程，最后几项必须随确定的模型、计算设备和真机任务继续完成；二者不能混成一项“已经能搬东西”。
