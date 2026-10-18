# L1：读取少量真实宇树数据

目的：亲眼查看真实发布格式与真实记录。运行位置：完成 L0 的电脑；仅 CPU。

## 1. 下载固定的小量文件

```bash
python restart/handbook/lab.py fetch-real --output .build/restart-lab-001/real
```

脚本按照 `sources.lock.json` 下载 6 个文件，总计 **5,835,881 字节**，逐项检查大小和 SHA256。没有下载视频、权重或完整数据集，也不需要登录。

源数据：`unitreerobotics/G1_Dex3_ToastedBread_Dataset`，固定版本 `02cb29161f5adb2981a072aa35b408d82a556d07`。数据卡在查证时标注 Apache-2.0，保留原 README 与来源，不将其改标为本项目 MIT。[固定源目录](https://huggingface.co/datasets/unitreerobotics/G1_Dex3_ToastedBread_Dataset/tree/02cb29161f5adb2981a072aa35b408d82a556d07)

如果目录已存在，改为 `restart-lab-002` 并同步后续路径。下载失败时目录可能不完整；只有出现 `download_receipt.json` 才表示完成了清单下载。断网、401、版本缺失不应通过伪造数据补齐；保留失败记录，检查访问条件。

## 2. 先看元数据

```bash
python -c "import json; from pathlib import Path; d=json.loads(Path('.build/restart-lab-001/real/meta/info.json').read_text()); print(d['codebase_version'], d['robot_type'], d['fps']); print(d['features']['observation.state']); print(d['features']['action'])"
```

应看到 v3.0、Unitree_G1、30 Hz，以及 28 维状态／动作和通道名称。先按名称看双臂和手部，不能把这 28 维理解为整台 G1 全部关节。

## 3. 查看真实表格行

```bash
python restart/handbook/lab.py inspect-real --root .build/restart-lab-001/real
```

本次实际读到 `file-001.parquet` 有 **16,576 行**，状态与动作数组形状均为 `[16576,28]`。输出包括第一条完整记录、字段名、状态通道名和四个相机键。

请观察 `timestamp`、`frame_index`、`episode_index` 和 `task_index`。这是一个真实分片中的第一行，不保证是完整数据集或一条轨迹的起点。其余字段的值直接来自下载表格，不用教学数值替换。

这里未加载图片，输出明确有 `images_loaded=false` 和 `ready_for_training=false`。四个视频键存在于 metadata 不代表本机已经有这四段视频。

## 4. 查看任务文字

```bash
python -c "import pyarrow.parquet as pq; print(pq.read_table('.build/restart-lab-001/real/meta/tasks.parquet').to_pylist())"
```

任务文字用于描述或条件化，动作标签仍是 `action`。某个模型是否实际消费文字取决于实现。

## 5. 关键代码怎么读

在 `lab.py` 找 `fetch_real`：固定 URL → 有上限地读取 → 校验 → 保存回执。再找 `inspect_real`：校验文件 → Parquet 解码 → 检查形状与有限数值 → 输出一行。

本步骤没有实现格式转换、跨时钟同步或相机解码。它避免为了理解字段而下载数 GB 视频；后续完整真实训练需要按对应 SDK 的完整文件关系获取数据。

## 你可以怎样汇报

“我们实际读取了宇树发布版本的一份表格分片，核对了 28 维状态动作与相机字段。只下载了约 5.8 MB；该片段用于格式学习，尚不是本机完整训练集。”

操作记录：写下版本、通道维度、任务文字、缺失文件与不能据此确定的语义。下一步 L2 使用明确标注的合成数据跑通完整转换。
