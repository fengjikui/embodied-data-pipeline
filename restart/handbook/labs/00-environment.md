# L0：准备独立环境

本章运行位置：Windows 电脑或普通 Linux 服务器。无需机器人、头显、GPU 或 Hugging Face 登录。需要网络下载代码与软件包；本轮验证复用了已有开发环境，没有重新安装全套依赖。

## 0. 先准备目录

需要 Git、Python 3.12 和 `uv`（Python 环境／包管理工具）。已有仓库直接进入根目录；新机器可执行：

```bash
git clone https://github.com/fengjikui/embodied-data-pipeline.git
cd embodied-data-pipeline
python --version
git --version
uv --version
```

Python 命令的具体名称由安装方式决定；创建环境使用 `uv --python 3.12` 时可按其机制获取对应 Python。Windows 可在 PowerShell 中使用下述通用单行命令。

## 1. 建立环境并激活

```bash
uv venv .venv-handbook --python 3.12
```

Linux：

```bash
source .venv-handbook/bin/activate
```

Windows PowerShell：

```powershell
.\.venv-handbook\Scripts\Activate.ps1
```

若 PowerShell 禁止激活脚本，可以使用该环境的 `Scripts/python.exe` 替代后文 `python`，不要误用系统 Python。通过 `uv pip install --python .venv-handbook ...` 安装包，不依赖激活。

```bash
python -c "import sys; print(sys.executable); print(sys.version)"
```

应显示 `.venv-handbook` 中的 Python 3.12。后面的依赖安装均通过 `uv pip --python` 指定该环境。

## 2. 安装 CPU 版 PyTorch

Linux／Windows：

```bash
uv pip install --python .venv-handbook torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cpu
```

这是固定教学组合，不是自动选择最新版本。CUDA 版另见 L4，不能在已有 CPU 环境里只把参数改成 `cuda` 就得到 GPU 支持。[PyTorch 官方版本组合](https://pytorch.org/get-started/previous-versions/)

## 3. 固定官方 LeRobot 源码

```bash
git clone https://github.com/huggingface/lerobot.git .build/handbook-lerobot
git -C .build/handbook-lerobot checkout ca69a2068462a37f7cdcb74180927a2f863d2bf7
uv pip install --python .venv-handbook -e ".build/handbook-lerobot[dataset]" accelerate==1.15.0 pyarrow==25.0.1 numpy==2.2.6 pillow==12.3.0 av==15.1.0
```

SDK 的完整依赖可能较多，空间需求远大于本次数据下载；公司内网环境要按目标 OS、Python 和架构准备依赖包，不能跨操作系统复制虚拟环境。

若 `.build/handbook-lerobot` 已存在，先检查当前提交和本地改动，再决定复用；不要覆盖其他工作。SDK 环境与宇树 `unitree_lerobot`、IsaacLab 分开安装。

## 4. 限制线程并查看资源

Linux：

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
```

PowerShell：

```powershell
$env:OMP_NUM_THREADS="1"
$env:OPENBLAS_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
```

这里 offline 限制 SDK／模型的隐式下载；L1 的明确 URL 下载仍会联网。

```bash
python restart/handbook/lab.py doctor
```

预期：打印解释器、平台、软件版本和资源状态。资源字段随平台而异；Linux 可读取内存和可用的热区信息，Windows 可读取可用内存，GPU 可再用 `nvidia-smi`。没有温度读数不代表温度为零。长时间任务运行期间也要监控，压力升高时降低本任务负载。

## 5. 保存环境

```bash
uv pip freeze --python .venv-handbook > handbook-environment.txt
```

将该文件连同代码提交、操作系统和 GPU 驱动信息保存到实验记录；它描述当前环境，不是跨平台通用锁文件。

本机已有已验证 SDK 环境时，可以直接用它的 Python 执行后续脚本；本轮验证使用 `.build/lerobot-env/bin/python`。教程通用写 `python`，以便换到 Linux／Windows。

验收：能执行 doctor，SDK 是固定提交，模型／数据未自动上传，后续输出使用全新目录。
