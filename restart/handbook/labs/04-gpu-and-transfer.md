# L4：迁移到 Linux／AutoDL 和内网

本章为执行准备与条件化命令，本轮未租卡、未登录远程环境、未验证 CUDA／昇腾训练。CPU 小实验无需租 GPU。

## 1. 什么时候需要提供环境

若要验证 GPU 训练、较大的 VLA 微调或 IsaacLab，先提供匿名环境概况：GPU 型号与显存、驱动、OS、Python、可用内存／磁盘、网络与容器条件。登录信息采用私有远程连接方式提供，不提交到仓库。

此前记录有昇腾 A3 资源，但芯片、卡数、内存、软件和可用容量未确认。它可以列为后续算力候选；本章 CUDA 命令不能直接在 NPU 上执行，需另外验证 Torch-NPU、模型算子和训练框架。

## 2. 选择运行环境时看什么

先用单卡完成小实验。CUDA ACT 与有相机渲染的机器人仿真对硬件要求不同；能训练神经网络的 GPU 不一定满足 Isaac Sim 的图形／驱动要求。不要仅根据“显存大”选一台仿真机器。

本章不给价格与预计总训练费；先做小步运行，测峰值显存、吞吐和稳定性，再按实测估算预算。AutoDL 的登录、磁盘和迁移说明以其当前文档为准。[AutoDL 文档](https://www.autodl.com/docs/)

## 3. 在远程终端核对信息

```bash
nvidia-smi
python --version
df -h
free -h
```

`nvidia-smi` 显示的 CUDA 能力不是当前 Python 一定使用的 CUDA 运行库。随后验证 `torch.version.cuda` 和 `torch.cuda.is_available()`。

## 4. 复制代码并重建环境

在服务器新目录克隆本仓库，记下 `git rev-parse HEAD`；按 L0 创建独立 Python 3.12 环境和固定 SDK。不要上传本机 `.venv`，也不需要传 `.build` 中全部历史数据。

安装 PyTorch 的步骤替换为下面组合，**前提是驱动与所选 GPU 支持该 CUDA wheel**：

```bash
uv pip install --python .venv-handbook torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cu128
```

这是 PyTorch 官方提供的版本组合；本轮未在远端测试。如条件不匹配，按官方版本矩阵选择兼容组合并记录新环境，不静默改变源码版本。[官方组合表](https://pytorch.org/get-started/previous-versions/)

激活环境并执行：

```bash
python -c "import torch; print(torch.__version__,torch.version.cuda,torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO CUDA')"
```

应确认 CUDA 可用后再继续。

## 5. 先复现相同教学任务

按 L2 在远端重新生成 capture 和 dataset，使用全新目录。再执行：

```bash
python restart/handbook/lab.py train --root .build/restart-lab-001/dataset --output .build/restart-lab-001/act-cuda --device cuda --steps 5
python restart/handbook/lab.py infer --root .build/restart-lab-001/dataset --checkpoint .build/restart-lab-001/act-cuda/checkpoints/000005/pretrained_model
```

第二条仍将模型载入 CPU 做离线预测，以便核对模型格式。异平台浮点值不要求逐位相同；核对结构、语义、有限值、运行记录和结果范围。不要为了“loss 必须下降”任意重复筛选成功运行。

## 6. 然后才做较大 VLA 微调

例如 SmolVLA 有官方训练说明，但权重、处理器、任务语言、动作约定、相机与训练模式要一起配置。其官方示例时间是特定条件下的参考，不是我们的承诺。[SmolVLA 官方指南](https://huggingface.co/docs/lerobot/smolvla)

本阶段完成条件应包括：完整真实数据可加载、无泄漏划分、原模型基线、固定任务评估、小步显存测量、恢复与导出验证。缺这些条件时，不先启动昂贵长训练。

## 7. 内网转移

代码、固定源码、数据／模型许可与地址清单、同 OS／架构依赖包、环境清单、处理配置与文件校验一起准备。允许联网的机器先准备包缓存，内网新环境验证；软件可安装和模型／数据可使用是两件事。

下载字节、数据总量、模型权重和 Python 依赖分开统计。公司数据不添加 Hub 上传参数，公有云是否允许存放由实际授权确定。

交付前保存运行输出与必要日志，核对备份，再按平台操作停止租赁实例。停止实例和删除数据是不同动作，不能假定关机后文件一定保留。
