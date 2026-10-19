# G1 EDU 数据管线手工复现

适用：Ubuntu/Linux 优先，Windows 可运行基础数据处理。此教程不连接机器人、不发送动作、不下载大数据集。教学数据是合成的 XR 结构，2 个虚构通道，不代表 G1 的真实关节或运动。

全流程：生成小样本 → 保存原始与映射 → 转换 → 注册哈希 → 处理发布 → 查看 batch → 可选 CPU 训练 → 新版本与完整性检查。

## 0. 选好目录和运行环境

在仓库根目录运行，Python 3.12、uv；依赖须能安装或已经带入公司内网。**`--offline` 数据参数不会安装缺失的 Python 依赖**。内网 wheel 准备参见 [部署说明](10-linux-windows-offline-deployment.md)。Linux 与 Windows 的虚拟环境应在各自平台创建，不能跨操作系统复制 `.venv`。

```bash
git clone https://github.com/fengjikui/embodied-data-pipeline.git
cd embodied-data-pipeline
uv sync --frozen --extra dev
uv run --frozen vla-pipeline --help
uv run --frozen python scripts/resource_status.py
```

若已经 clone，本次不必重新 clone。先查看 `git status`，保留自己的修改。下载和安装步骤只在联网工作区完成；已有依赖时可以使用 `uv run --offline --frozen ...`。

Linux 限制数值库线程：

```bash
export PYTHONUTF8=1
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
```

Windows PowerShell 等效：

```powershell
$env:PYTHONUTF8="1"
$env:OMP_NUM_THREADS="1"
$env:OPENBLAS_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
```

以下 Python/CLI 命令为单行，PowerShell 可直接用；`<release_id>` 等占位符必须先替换，不能原样粘贴。目录选 `data/g1-demo`；如已存在，用 `data/g1-demo-002` 并同步替换后续路径，**无需删除旧数据来重跑**。

想先看一次自动验收，再逐步手工操作，可使用一个全新的工作目录：

```bash
uv run --frozen python scripts/verify_g1_engineering.py --workdir data/g1-one-command --report-dir reports/local-g1-check
```

安装了 train 依赖后加 `--train-steps 20` 并在 `uv run` 中加 `--extra train`，即可包括实际 CPU 探针。证据记录原始文件哈希、训练 batch、版本变化和资源快照；这条脚本不会执行官方 LeRobot 导出或连接机器人。下文将同一过程展开为手工步骤。

## 1. 生成不需要下载的教学来源

```bash
uv run --frozen python scripts/generate_g1_demo.py --output data/g1-demo
```

检查：

```bash
uv run --frozen python -c "import json; from pathlib import Path; p=Path('data/g1-demo/capture/demo_task/episode_0000/data.json'); d=json.loads(p.read_text(encoding='utf-8')); print(d['info']); print(d['text']); print(d['data'][0])"
```

应看到 `fps=20`、中文合成任务指令、`idx`、`colors.color_0`、两维 `states.left_arm.qpos` 与 `actions.left_arm.qpos`。生成 8 个 episode，每个 24 行和 24 张 64×64 图片，共 192 个原始时刻。

`data/g1-demo/mapping.json` 明确选择字段、相机、关节名称、单位声明和分组。示例中 `demo_0/demo_1` 和 `synthetic_unit` 只能用于教学。

## 2. 保存原始并转换成实验室入口格式

```bash
uv run --frozen vla-pipeline import-unitree --source-dir data/g1-demo/capture --mapping data/g1-demo/mapping.json --output data/g1-demo/prepared
```

输出：

```text
prepared/
  original/           完整原始 JSON、图片及其他文件
  mapping.json        此批采用的明确映射
  conversion.json     原始文件哈希、时间假设、转换记录
  source.json         来源描述与文件列表入口
  episodes/*.json     lab_json_v1 轨迹
  media/*.mp4         选定一路 RGB 的派生视频
```

检查转换凭据：

```bash
uv run --frozen python -c "import json; from pathlib import Path; d=json.loads(Path('data/g1-demo/prepared/conversion.json').read_text(encoding='utf-8')); print('episodes=',len(d['episodes'])); print(d['episodes'][0]); print('deployment_ready=',d['deployment_ready'])"
```

应看到 8 条轨迹，`timestamp_basis` 包含 `NOT_measured_hardware_time`，`success` 是 `None/null`，`deployment_ready=False`。原始图片保留，派生 MP4 使用有损 MPEG4；这里选择它是为了便携测试，不作为不可逆删除原始图像的理由。

输出目录已存在时，转换器会报错，要求新目录。缺图片、关节数不符、越界路径、idx 不连续、任务文本空白或不规则实测时间都会拒绝转换，不会默默填补数据。

## 3. 注册到版本化原始存储

```bash
uv run --frozen vla-pipeline register-local --source-dir data/g1-demo/prepared --descriptor data/g1-demo/prepared/source.json --root data/g1-demo/store --output data/g1-demo/sources.lock.json
```

检查来源锁：

```bash
uv run --frozen python -c "import json; from pathlib import Path; s=json.loads(Path('data/g1-demo/sources.lock.json').read_text(encoding='utf-8'))['sources'][0]; print(s['id'],s['revision'],s['format']); print('locked_files=',len(s['files'])); print(s['files'][0])"
```

此时文件在 `store/raw/g1_edu_synthetic/batch-001/`。锁中包括 episode、视频、原始快照、mapping、conversion 和 source 描述，逐文件有字节数与 SHA256。**同一批 revision 的内容或描述发生变化必须使用新 revision**。不要编辑 `store/raw/`；调整来源应在新接收/派生目录中完成。

## 4. 运行处理，形成不可变训练数据版本

```bash
uv run --frozen vla-pipeline run --lock data/g1-demo/sources.lock.json --root data/g1-demo/store --recipe configs/g1_edu_interface_recipe.json --offline
```

记下输出的 `release_id`。也可以查看：

```bash
uv run --frozen python -c "import json; from pathlib import Path; print(json.loads(Path('data/g1-demo/store/latest.json').read_text(encoding='utf-8'))['release_id'])"
```

应看到：8 accepted、0 quarantine、0 duplicate、192 numeric frames、32 windows；7 条 train、1 条 validation。`raw_download_bytes` 是兼容旧版保留的字段名，这个合成流程中它代表锁定文件字节数，**没有进行网络数据下载**。

产物：

```text
store/releases/<release_id>/
  manifest.json           发布清单与产物哈希
  source_lock.json        输入快照
  recipe.json             窗口、图片、切分等规则
  quality.json            成功解析、隔离、重复与时间检查
  statistics.json         仅 train 的每来源统计
  canonical/<source>/     完整数值轨迹 Parquet 与 JSON 元数据
  views/<source>/train/   训练 NPZ
  views/<source>/validation/
  previews/<source>/     快速检查图片
```

## 5. 检查文件完整性和模型输入

先替换 `<release_id>`：

```bash
uv run --frozen vla-pipeline verify data/g1-demo/store/releases/<release_id>
uv run --frozen python scripts/inspect_training_batch.py --release data/g1-demo/store/releases/<release_id> --source g1_edu_synthetic
```

应看到 28 个 train 样本；单个样本：`image float32 [3,64,64]`，`state float32 [2]`，`actions float32 [8,2]`，`action_mask bool [8,2]`，以及语言、时刻、原始 anchor_index。NPZ 文件内部 image 是 uint8 HWC；`WindowDataset` 才转为 float32 CHW 并除以 255。

想看 canonical 的一行：

```bash
uv run --frozen python -c "from pathlib import Path; import pyarrow.parquet as pq; r=Path('data/g1-demo/store/releases/<release_id>'); p=next((r/'canonical/g1_edu_synthetic').glob('*.parquet')); t=pq.read_table(p); print(t.schema); print(t.slice(0,1).to_pylist())"
```

这里 action 保持原生数值；训练 NPZ 才使用 train mean/std 归一化。完整说明见 [训练格式](16-training-export.md)。

## 6. 可选：真实运行一次 CPU 训练接口

这是随机初始化的小网络，不下载 VLA 权重，只验证多模态 batch、loss、梯度和 checkpoint。Torch 安装在 Linux 可能带来较大 CUDA 依赖；仅 CPU 演示可在独立环境安装 CPU wheel。详见 [CPU 环境](16-training-export.md#cpu-训练探针)。已有本项目 `train` 依赖时：

```bash
uv sync --frozen --extra train --extra dev
uv run --frozen python scripts/resource_status.py
uv run --frozen --extra train python -m vla_pipeline.training --release data/g1-demo/store/releases/<release_id> --output data/g1-demo/training --steps 20 --threads 1
```

开始前看内存压力与系统热状态；运行期间可另开终端再次执行资源检查。内存紧张、出现热告警或明显影响其他工作时，暂停/停止本任务后改少量数据重跑。不要结束其他用户进程。系统没有温度读数时只能报告“未取得温度读数”。

输出 `training/g1_edu_synthetic.pt` 和 `training_probe.json`。检查：

```bash
uv run --frozen python -c "import json; from pathlib import Path; d=json.loads(Path('data/g1-demo/training/training_probe.json').read_text(encoding='utf-8')); print(d['release_id'],d['device'],d['threads']); print(d['results'][0])"
```

应有有限 loss/梯度、检查点恢复误差检查以及明确的 release_id。训练 loss 不要求在每一个 step 都下降；下降也不能证明机器人能力。CPU 探针一次将一个来源的 smoke 样本读入内存；生产训练应使用逐 episode 缓存的 `WindowDataset` 或选定框架的流式后端。

## 7. 重跑、改变规则与新数据接入

重复步骤 4，锁、规则和代码均未改变时，应显示 `Reused immutable release: True`，版本号相同。

改变规则，新建一份 JSON：

```bash
uv run --frozen python -c "import json; from pathlib import Path; d=json.loads(Path('configs/g1_edu_interface_recipe.json').read_text(encoding='utf-8')); d['horizon']=4; d['anchor_stride']=4; Path('data/g1-demo/recipe-v2.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')"
uv run --frozen vla-pipeline run --lock data/g1-demo/sources.lock.json --root data/g1-demo/store --recipe data/g1-demo/recipe-v2.json --offline
```

应生成不同 release；新窗口 horizon 为 4，旧 release 仍可以 verify。改变规则不会覆盖旧产物。训练时传 `--release` 固定版本，避免 `latest.json` 后续变化。

新采集批次：新的 incoming/capture 目录 → 新 mapping（`revision=batch-002`，同采集 session 保留同 origin_group）→ 新 prepared → 注册 → 新来源锁 → 新 release。若想把 batch-001 与 batch-002 合并训练，当前一个 source 只指向一个 revision，**需明确生成累计 revision 并包含两批完整 episode**，不能直接把同 id 的两个 source 塞进锁。更大规模的无复制增量合并需要后续目录服务/CAS 后端；本次没有伪装成已实现。

工程失败用测试演示即可，无需损坏你的原始存储：

```bash
uv run --frozen --extra dev pytest -q
```

测试包含缺图、错时间、维度错、越界路径、raw 篡改、重复、不同 recipe、统计与动作还原。基础测试不要求安装 Torch 或官方 LeRobot。

## 8. 公司环境验证已有真实公开小样本

这个步骤另需约 212 MB 的锁定文件，**不必为了学习教程执行**。已缓存时加 `--offline`；公司联网电脑才执行首次获取：

```bash
uv run --frozen vla-pipeline run --lock configs/demo_sources.lock.json --root data
uv run --frozen python scripts/verify_delivery.py --report-dir reports/company-validation
```

验收脚本使用 `configs/demo_sources.lock.json` 和仓库 `data/`，不要把它理解成通用 G1 自采数据验收器。它应得到 18 个 accepted、23,109 个时刻、590 个窗口，并验证逆归一化和故意损坏的派生测试数据。`--report-dir` 使旧汇报证据保持原样。运行期间采用上述资源检查和单线程环境变量。

## 9. 替换为真实 G1 EDU 采集

1. 将采集器完整关闭/完成保存后的任务目录复制到接收区；得到采集配置、实际关节顺序、相机、时钟、控制器、操作人/session、结果、数据权限与标定。
2. 复制 [XR 映射空模板](../configs/g1_edu_xr_mapping.template.json) 到接收批次旁；填写 `names`、单位、实际手型、控制语义、来源许可。空模板故意不能通过验证。
3. 手部动作如需学习，显式追加 `states.left_ee.qpos`、`actions.left_ee.qpos` 等实际字段及名称。`G1 EDU` 字符串不会自动增加手部或全身关节。
4. 确认 `colors` 中相机 key。当前转换只选择一路 RGB；其他图片、深度、音频和 JSON 字段保留但不进入 smoke 训练视图。
5. 没有实测时间戳时保留 `nominal_index`；有时则使用 `measured_timestamp`、实际字段路径、`scale_to_seconds` 和 `clock_id`。当前 importer 只接收近似精确等间隔采样，拒绝隐式补帧/重采样；实际 jitter 较大时要另建记录修复规则的 adapter。
6. `origin_groups` 按同一原始 session/连续录制分组；从同一长任务切出的片段必须同组，防止切分泄漏。未标记 session 的默认 episode 划分仅是工程 holdout。
7. 从步骤 2 开始执行，使用新的 source id/revision 和输出目录。先人工回看图像、动作、语言与任务结果，再让数据进入真正的模型微调路线。

对于行走 DDS/ROS2 日志，不要强行伪装成两臂 XR 数据；按采集契约保留完整原始消息，然后实现相应 adapter 和仿真/控制模型训练接口。

## 10. 常见问题定位

| 现象 | 通常原因 | 处理 |
|---|---|---|
| `No XR data.json episodes found` | 目录层级错或采集未完成 | 找到任务下 episode 的真实 data.json，确认已保存结束 |
| `Field dimension ... mismatch` | 手型/关节数/字段顺序与 mapping 不同 | 查看实际 JSON 与控制器定义，修正新 mapping；不补零猜测 |
| `Non-contiguous XR idx` / `Irregular timing` | 丢记录或真实采样不等间隔 | 保留原始，确定显式修复/重采样策略；新派生版本 |
| `Raw revision ... new revision` | 原始内容或 source 描述改过 | 用新的 revision；不要修改 raw 来绕过 |
| `Hash mismatch in cache` | 传输损坏或已有文件被改 | 重新核对固定来源，仅重新获取损坏文件，不盲目换最新版 |
| 只有 canonical、没有 views | 该来源无 train，或全部媒体/质量失败 | 看 quality.json 和 sources.view_status；不要用 validation 拟合统计 |
| `Release corrupted` | 产物被改或移动不完整 | 从完整备份恢复；重新跑已锁定输入，不能忽略校验 |
| `No module named lerobot/torch` | 可选环境未安装 | 安装对应独立环境；基础管线不依赖这两个包 |
| `Unknown source` | 参数用了公开名称而非 source id | 用 source_lock.json 中的 id |
