# Linux / Ubuntu、Windows 与内网部署

项目目录统一使用 `embodied-data-pipeline`。下文命令从仓库根目录执行；代码按文件位置或显式参数解析数据路径，不依赖某台开发电脑的绝对目录。

移动本地目录后，已打开的终端应重新进入新目录；已激活的环境先执行 `deactivate`，再从新目录激活。跨平台迁移仍须按本章重建环境，不能把本机目录改名后的验证结果视为任意系统可直接搬运虚拟环境。历史训练日志与检查点中的命令保留原始记录；重新运行时使用当前数据路径和新的输出目录，不照抄其中的旧绝对路径。

Python 包名 `vla_pipeline`、命令行 `vla-pipeline` 与现有 wheel 名称保留兼容，因此仓库目录改名后原有命令保持不变。

## 1. 目标环境与适配范围

生产研究环境建议优先按 **Ubuntu 24.04 / x86_64 / Python 3.12** 验证，兼容 Windows 的数据工程入口。Ubuntu 22.04、ARM Linux、WSL 和其他服务器组合应在对应环境跑同一验收，不能由本机结果直接外推。真实 VLA 的 CUDA、GPU 驱动与模型库应按所选模型单独固定。

本项目以 Python `pathlib` 管理路径，命令行入口使用跨平台 Python 实现。核心数据处理不需要 GPU，也不依赖桌面图形界面。汇报制作脚本使用另备的制稿工具，不属于公司服务器运行管线的依赖，见 `deliverables/README.md`。PyAV 在 Python 内读取视频，不调用系统 `ffmpeg` 命令。具体平台仍需安装可用的 PyAV 二进制包并验证所用编码。官方提供多平台 wheel，编解码支持以实际安装构建为准。[PyAV 安装说明](https://pyav.org/docs/stable/overview/installation.html)

`uv.lock` 记录跨平台依赖解析，不同操作系统之间不能直接复制 `.venv`。不同 OS、CPU 架构和 Python ABI 需要相应安装包。[uv 项目结构](https://docs.astral.sh/uv/concepts/projects/layout/)

## 2. 在线 Linux / Ubuntu 安装

先由公司允许的渠道准备 Git、uv 和 Python 3.12。以下命令在仓库根目录执行；不需要激活虚拟环境。

```bash
uv sync --frozen --extra dev
uv run --frozen --extra dev pytest -q
uv run --frozen vla-pipeline run --root /srv/vla-data
```

首条安装基础处理与测试依赖，不安装 Torch。最后一条仅下载锁清单中的约 212 MB 样本，随后解析发布。

本原型训练探针使用 CPU，无须 CUDA：

```bash
uv sync --frozen --extra dev --extra train
uv run --frozen --extra train python -m vla_pipeline.training --root /srv/vla-data --output /srv/vla-data/training
```

注意：默认 PyPI 的 Linux Torch 依赖可能包含 CUDA 运行库，安装体积会明显增大。若仅做 CPU 探针，应在公司环境用 PyTorch 官方 CPU 安装源生成并保存单独的部署锁文件。不要把 CPU 环境替换为 GPU 环境后继续声称使用完全相同的依赖锁。GPU 微调另按所选硬件和官方模型配方配置。[PyTorch 安装入口](https://pytorch.org/get-started/locally/)

## 3. Windows 安装

在 PowerShell 中使用相同入口，建议使用短数据路径，避免较深的来源目录触发系统路径限制。

```powershell
uv sync --frozen --extra dev
uv run --frozen --extra dev pytest -q
uv run --frozen vla-pipeline run --root D:\vla-data
```

不需要 `source .venv/bin/activate`、`chmod`、符号链接或 Bash。真实机器人 SDK、CUDA 训练器或模拟器对 Windows 的支持需另外确认，不能由本数据管线兼容推断其兼容。

## 4. 内网迁移应分别准备三种包

| 包 | 内容 | 是否跨平台 |
|---|---|---|
| 项目包 | 代码、配置、数据索引、报告、锁文件、测试 | 通常可跨平台，目标机重建环境 |
| 环境包 | Python/uv 安装包、wheelhouse、依赖清单、必要的系统库 | 必须匹配 OS、CPU 架构、Python 版本与 ABI |
| 数据／模型包 | 原始文件、SHA256、revision、许可与出处、模型权重及其配置 | 数据通常可移植，加载器和模型运行条件需匹配 |

不要把“代码能复制过去”理解成“网络与安装问题已经解决”。公司下载、扫描、审批、镜像和导入方式应按内部流程执行。

## 5. 无数据的轻量交付包

```bash
uv run python scripts/export_transfer_bundle.py --output data/transfer/vla-delivery.zip
```

默认不打包原始视频、训练数据或模型权重。ZIP 内有 `TRANSFER-MANIFEST.json`，包外有 SHA256。在 Linux 用 `sha256sum vla-delivery.zip`，在 Windows PowerShell 用 `Get-FileHash vla-delivery.zip -Algorithm SHA256`，与 `.sha256` 文件比较；复制后再次核对。若公司允许搬运本次代表样本，可显式加入已缓存原件，不发生额外下载：

```bash
uv run python scripts/export_transfer_bundle.py --include-samples --output data/transfer/vla-delivery-with-samples.zip
```

二者都不打包 `.venv`、本机凭据、Git 历史、GPU 驱动或平台依赖 wheel。公司要下载更多数据时，先看 `docs/11-download-priorities.md`，不要因已有索引就全部下载。

## 6. 环境包的准备方式

最可靠的办法是在**与公司目标机相同 OS / 架构 / Python 版本**的获准联网准备机上构建环境包。下例是基础数据处理包，不含 Torch，应在匹配目标平台的准备机上执行。

```bash
uv export --frozen --no-dev --no-emit-project --no-hashes --output-file requirements-base.txt
uv build --wheel
python -m pip download --only-binary=:all: --dest wheelhouse --requirement requirements-base.txt
python -m pip download --only-binary=:all: --dest wheelhouse pip
```

保留 `uv.lock` 与导出的安装清单。对 wheelhouse、项目 wheel、Python 安装包逐文件计算 SHA256。若某个依赖没有目标平台 wheel，停止并准备对应平台构建产物，不能用其他平台的 wheel 替代。离线依赖导出方式参见 [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)。

在内网目标机已有 Python 3.12 的前提下：

```bash
python -m venv .venv
```

Linux：

```bash
.venv/bin/python -m pip install --no-index --find-links wheelhouse -r requirements-base.txt
.venv/bin/python -m pip install --no-index --no-deps dist/vla_data_pipeline-0.2.0-py3-none-any.whl
.venv/bin/python -m vla_pipeline.cli run --root /srv/vla-data --offline
```

Windows：

```powershell
.venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse -r requirements-base.txt
.venv\Scripts\python.exe -m pip install --no-index --no-deps dist\vla_data_pipeline-0.2.0-py3-none-any.whl
.venv\Scripts\python.exe -m vla_pipeline.cli run --root D:\vla-data --offline
```

以上假定 Python 自带可用的 pip / ensurepip。Ubuntu 如缺少 venv 或 ensurepip，要在环境包中准备匹配系统版本的 `python3.12-venv` 等 OS 包，由管理员安装。不能指望进入内网后再访问外部 apt 源。

测试依赖与训练依赖可按同样方式另导出；CPU / CUDA Torch 的 wheelhouse 要分开，避免把本原型的 CPU 验证当成真实 VLA GPU 配方。

## 7. 数据如何在内网使用

原始目录约定：

```text
data-root/raw/{source_id}/{revision}/{原始相对路径}
```

将已校验的来源文件放到这个结构后，运行 `--offline`：缓存缺失或哈希不符会失败，不会偷偷联网或跳过。公开 URL 在离线模式只是来源记录。

如果公司有允许访问的内部对象存储镜像，可在**新的 lock 文件**中将各文件 URL 替换成镜像地址，保留来源信息、原始 revision 与 SHA256。不要将访问令牌写进 Git 配置或 URL。已有字节内容不变时，哈希应保持一致；修改锁配置会产生新的发布 ID。

自采数据通过 `register-local` 登记成本地锁文件，见演示手册。新增数据不需要暴露到外网或 Hugging Face。

## 8. 服务器运行建议

- 原始数据和发布版本放容量足够的持久卷，临时计算用本地 SSD；先按样包实测解码时间和峰值内存。
- 一个数据根目录同时只运行一个发布写入进程。当前 MVP 未实现多进程任务锁和分布式调度。
- 训练只读取已完成发布目录，保留旧 release 和统计量以复现检查点。
- 避免无上限保留中间版本。删除数据前核验哪些训练和检查点引用了它。
- 正式服务器接入采集或机器人前，补权限、备份、监控、资源配额与恢复流程。

## 9. 验证状态

本机 ARM64 已执行真实样本、图像解码、CPU 训练与离线重跑。GitHub Actions 已在 Ubuntu 24.04 和 Windows 分别通过 21 项测试、CLI 入口检查与 wheel 构建，包含合成视频解码及本地新增数据集成测试。[运行记录](https://github.com/fengjikui/embodied-data-pipeline/actions/runs/34678405092)，机器可读状态见 `reports/cross-platform-ci.json`。

CI 不下载全部公开样本，也不验证生产 GPU、公司内网、机器人 SDK 或真实 VLA 微调。这些需在公司目标环境按同一验收表补测。
