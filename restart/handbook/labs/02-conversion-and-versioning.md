# L2：采集文件、格式转换、划分和版本

运行位置：L0 环境。这个实验的数据完全合成；图像和 28 维数值不表示真实 G1 物理状态。Unitree 风格的 JSON 是教学子集，转换器是本项目代码；最终 LeRobot 文件由固定官方 SDK 写入。

## 1. 生成一个可重复查看的采集目录

```bash
python restart/handbook/lab.py make-capture --output .build/restart-lab-001/capture
```

输出 4 段轨迹，每段 20 帧，名义 10 Hz。每段有 `colors/` 和 `data.json`，根目录有 `capture_contract.json` 描述来源、通道顺序、划分和非物理属性。

```bash
python -c "import json; from pathlib import Path; d=json.loads(Path('.build/restart-lab-001/capture/episode_0000/data.json').read_text()); print(d['data'][0])"
```

依次看 `idx`、图片路径、`states` 和 `actions`。每部分 7 维，展开顺序为左臂、右臂、左手、右手。真实宇树的展开配置应读取官方 `ROBOT_CONFIGS`，不能用此教学顺序替代所有手型。

## 2. 生成并验证原始文件快照

```bash
python restart/handbook/lab.py snapshot --root .build/restart-lab-001/capture --output .build/restart-lab-001/capture-snapshot.json
python restart/handbook/lab.py verify --root .build/restart-lab-001/capture --manifest .build/restart-lab-001/capture-snapshot.json
```

两次应得到一致的快照 ID。快照放在被检查目录之外，避免自身改变快照。它记录文件相对路径、大小和 SHA256；任何原始文件新增、删除或改变，验证应失败。

## 3. 执行检查与官方格式导出

```bash
python restart/handbook/lab.py export --capture .build/restart-lab-001/capture --output .build/restart-lab-001/dataset
```

步骤：验证契约 → 检查维度、有限值、序号、图片引用 → 按整条轨迹划分 → 定义 SDK features → 逐帧 `add_frame` → 每段 `save_episode` → `finalize` → 用官方 reader 读回。

预期输出：

| 集合 | 原始轨迹 | 帧数 | 状态／动作 | 图像 |
| --- | --- | --- | --- | --- |
| train | 0、1、2 | 60 | `[28]` | `[3,64,64]` |
| validation | 3 | 20 | `[28]` | `[3,64,64]` |

本程序逐行核对导出动作与采集动作相同。`export_receipt.json` 存在才表示此教学导出完成；失败后新建输出目录重试，不沿用半成品。

train 和 validation 各是官方 SDK 创建的数据集，使用各自 episode 编号；回执保留了与原始轨迹的关系。训练预处理使用训练集统计，推理不重新拟合验证集统计。

## 4. 看最终文件

```bash
python -c "from pathlib import Path; print('\n'.join(str(p) for p in Path('.build/restart-lab-001/dataset/train').rglob('*') if p.is_file()))"
```

能看到 meta、Parquet、视频等产物。SDK 负责具体路径布局；不要手写一个类似目录就宣称兼容。这里没有上传 Hub。

## 5. 构造训练批次

```bash
python restart/handbook/lab.py batch --root .build/restart-lab-001/dataset
```

预期图像 `[2,3,64,64]`、状态 `[2,28]`、动作 `[2,8,28]`、`action_is_pad` 为 `[2,8]`。代码用 action 的 `delta_timestamps=[0,0.1,...,0.7]` 索引当前及之后 7 帧，是动作块标签；没有读取未来图像作为当前观测。

## 6. 关键代码走读

- `parse_capture`：决定能接受哪些输入，哪些问题立即拒绝。
- `export_capture`：字段展开与图像读取、按轨迹划分、官方写入和回读。
- `batch`：把一帧索引扩展为动作时间窗口，DataLoader 再组合批次。
- `snapshot/verify`：处理文件字节一致性，不能代替任务质量检查。

正式工业输入要增加真实时钟、标定、设备与工艺质量检查，不把本教学的 `idx/fps` 当作同步算法。这里也没有实现把深度、力或工具结果送进 ACT。

复述：原始 JSON 里的一组数值如何进入 `[2,8,28]`？动作单位在哪定义？为什么整段划分后仍需要更严格的现场测试条件？
