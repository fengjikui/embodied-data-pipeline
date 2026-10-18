# L5：仿真和真机的接入步骤

本章将当前缺少的条件明确列出；不是已经执行的机器人操作记录。没有真机和头显不影响 L0–L3。

## A. 宇树采集与转换：先准备，后现场执行

1. 确认 G1 版本、手部、相机、PC2、开放控制模式和网络。
2. 分别建立 XR 采集、相机服务、手部服务环境，记录源码版本。
3. Host 与 PC2 分别启动官方对应服务，头显连接页面；先确认图像和跟踪，再验证控制与录制状态。
4. 在限定工位执行短示范，保存 episode；核对状态、命令、相机引用、时间来源与结果。
5. 根据实际本体配置选择转换器，不修改原始文件来伪装另一种手型。
6. 导出后用对应 SDK 读回，检查通道与图像，再构造批次和训练。

参考仓库：[xr_teleoperate](https://github.com/unitreerobotics/xr_teleoperate)、[unitree_lerobot](https://github.com/unitreerobotics/unitree_lerobot)。源码变化后先核对 README 与实际 `--help`；本手册未在新采购的 G1 上执行。

官方转换入口的形式如下，路径和本体类型必须在现场确认后填写：

```text
python unitree_lerobot/utils/convert_unitree_json_to_lerobot.py --raw-dir <采集根目录> --repo-id <本地数据标识> --robot_type <实际支持的本体配置>
```

尖括号是待填项，不能原样执行。先在固定上游代码中核对参数是否支持本地保存和关闭上传，且不附加上传开关；本手册 L2 使用的是独立教学适配器，不冒充执行了上述官方转换。

## B. 仿真遥操作

需要兼容 `unitree_sim_isaaclab` 的仿真环境，以及有渲染能力的 GPU。先选择与本体、手部、相机和控制协议一致的任务，验证虚拟相机和状态，再接 XR 控制并录制。

运行顺序：仿真启动 → 图像／状态可读 → 遥操作连接 → 短轨迹录制 → 文件检查 → 与真机同样的转换与训练检查。[宇树仿真项目](https://github.com/unitreerobotics/unitree_sim_isaaclab)

并非所有训练 GPU 都支持目标渲染环境。安装先以该上游要求选择 Isaac Sim、IsaacLab、Python、驱动与 OS，不把单个最新版本混搭进去。[IsaacLab 安装文档](https://isaac-sim.github.io/IsaacLab/develop/source/setup/installation/index.html)

## C. G1 行走强化学习

### C1. 独立的仿真环境

以下是与固定上游 README 对应的 **Isaac Sim 5.1.0＋IsaacLab 2.3.0** 准备路线，仅作为待远程验证命令。先确认 GPU、驱动和系统库条件；不在本机执行大规模安装。

它使用 Python **3.11**，与 L0 的 LeRobot Python 3.12 环境不同。在 Linux x86_64 服务器上，从本仓库根目录开始：

```bash
uv venv .venv-isaaclab --python 3.11
source .venv-isaaclab/bin/activate
uv pip install --python .venv-isaaclab "isaacsim[all,extscache]==5.1.0" --extra-index-url https://pypi.nvidia.com
uv pip install --python .venv-isaaclab torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cu128
git clone --branch v2.3.0 https://github.com/isaac-sim/IsaacLab.git .build/handbook-IsaacLab
cd .build/handbook-IsaacLab
./isaaclab.sh --install rsl_rl
./isaaclab.sh -p scripts/tutorials/00_sim/create_empty.py --headless
```

最后一条是空场景检查；确认应用初始化、没有 GPU／扩展错误后用 Ctrl+C 结束，再 `cd ../..` 回到本仓库。首次启动可能下载扩展并要求阅读接受软件许可；若环境、网络或授权不满足，记录并停止该步骤。

Ubuntu 系统库条件、Windows 操作及其他架构使用 [固定版本安装文档](https://isaac-sim.github.io/IsaacLab/v2.3.0/source/setup/installation/pip_installation.html)，不要把本命令照搬到 L0 的环境。

### C2. 接入宇树任务

无 GPU 时，先克隆源码做走读：

```bash
git clone https://github.com/unitreerobotics/unitree_rl_lab.git .build/handbook-unitree-rl
git -C .build/handbook-unitree-rl checkout 4960b84732b0c2ec593dccbfe963fda1bcd7b1e3
```

这是此前核对过的固定上游版本，未在本轮安装／运行。进入该目录，阅读目标 G1 任务的 observation、action、reward、termination、机器人模型和默认控制参数；记录它所依赖的 IsaacLab 组合。

具备 C1 环境后，进入 `.build/handbook-unitree-rl`，在仍激活的仿真环境安装项目并列任务：

```bash
uv pip install -e source/unitree_rl_lab
python scripts/list_envs.py
```

这里直接调用 Python，原因是该固定版本的 `unitree_rl_lab.sh` 对 Conda 环境和激活脚本有专门依赖；不在 uv 环境中照搬它的 `-i/-l` 包装命令。[固定包装脚本](https://github.com/unitreerobotics/unitree_rl_lab/blob/4960b84732b0c2ec593dccbfe963fda1bcd7b1e3/unitree_rl_lab.sh)

机器人资源还需按上游选择 USD 或 URDF。若选 URDF，将 `unitree_ros` 仓库放在单独目录，在 `source/unitree_rl_lab/unitree_rl_lab/assets/robots/unitree.py` 中填写实际 `UNITREE_ROS_DIR`，核对所需机器人模型和 spawn 配置。记录资源提交与路径；任务列表出现不代表资源已完整可加载。[固定宇树 README](https://github.com/unitreerobotics/unitree_rl_lab/blob/4960b84732b0c2ec593dccbfe963fda1bcd7b1e3/README.md)

在完成兼容环境、资源与任务核对后，候选训练入口是：

```bash
python scripts/rsl_rl/train.py --headless --task Unitree-G1-29dof-Velocity --num_envs 16
```

先以固定版本 `--help` 核对参数与实际注册的任务；若不存在则停止排查，不能凭同名猜测替换。16 是初次接口验证的保守环境数量，不是训练推荐规模。`headless` 表示不打开图形窗口，不等于绝无 GPU／渲染要求。

播放入口形式：

```bash
python scripts/rsl_rl/play.py --task Unitree-G1-29dof-Velocity --num_envs 1
```

检查点路径按该版本帮助和训练日志填写。需要保存 actor、训练配置、归一化、动作缩放及底层参数；仅保存权重不足以复现实机控制。

## D. 从训练到实际推理

操作策略：当前传感器输入 → 训练时预处理 → 策略动作块 → 后处理 → 本体／控制适配 → 执行与反馈。

行走策略：当前与历史状态、期望运动指令 → actor → 动作缩放与关节目标 → 底层控制 → 新状态。先做可行的仿真播放与跨仿真检查，再进入厂商支持的现场流程。

两者组合要明确控制权、频率、坐标、载荷与任务状态。现有公开全身系统可作为参考，但不能把两个检查点拼接就视为全身协同完成。

## 当前阻断项与需要提供的信息

物理采集缺 G1 与遥操作设备；真实装配缺工具／工位与工艺判定；GPU 仿真缺已确认的远程软硬件组合。需要执行这些步骤时，再按对应项提供配置与访问方式即可。

验收表应分别填写“已读代码”“安装通过”“仿真运行”“真机执行”“工艺质量通过”，不能用第一项代替最后一项。
