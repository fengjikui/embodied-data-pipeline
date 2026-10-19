# 汇报材料使用说明

## 当前 G1 工业任务汇报（2026-10-14）

优先使用 [industrial-report.html](industrial-report.html)，下载后用浏览器直接打开。默认“汇报概览”，每章可单独展开；“技术详读”展开全部内容。场景选择解释固定站位装配、持工具移动与自造机械臂的不同数据要求。打印时自动展开技术正文，打印结束恢复阅读状态。

[7段讲稿与主管问答](../docs/23-supervisor-script.md) 可用于8–12分钟讲解；[逐条命令手册](../docs/22-command-learning-lab.md) 按关卡学习；[实测与边界](../reports/industrial-2026-10-14/acceptance.md) 区分教学运行、上游资料与真实工位待验收。

此文件由 `python scripts/build_industrial_report.py` 从 `docs/17–23` 和实际验收JSON生成，无额外Python依赖、无外部字体/脚本。运行来源的hash写入 `reports/industrial-2026-10-14/offline-report-build.json`。外部出处链接需要联网，正文可离线阅读。

## 原预研汇报（2026-09-12 快照）

建议先读 [主管摘要](../docs/06-supervisor-brief.md)，再按 [逐页讲稿](speaker-notes.md) 练习 10～15 分钟。PPTX 可编辑，PDF 保持已检查的版式，HTML 下载后可离线阅读。完整数据研究在 [技术报告](../docs/01-vla-data-research.md)。

| 文件 | 用途 |
|---|---|
| [VLA数据预研与管线验证-主管汇报.pptx](VLA数据预研与管线验证-主管汇报.pptx) | 16 页、可编辑文本与表格，附讲者备注 |
| [VLA数据预研与管线验证-主管汇报.pdf](VLA数据预研与管线验证-主管汇报.pdf) | 固定版式备用；中文可搜索与复制 |
| [offline-report.html](offline-report.html) | 三类来源图片、数据量、质量与小模型训练结果 |
| [speaker-notes.md](speaker-notes.md) | 逐页讲稿、3 分钟短版和会前检查 |
| [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) | 样本图片出处、许可和派生说明 |

## 重新生成

数据与训练报告更新后，先确保 `reports/acceptance.json` 与 `reports/training_probe.json` 的 release ID 一致，再运行 `scripts/build_offline_report.py`。它会读取本机已缓存原始视频，不需要重新下载全部数据。

`scripts/build_presentation.mjs` 是本次汇报制作脚本，使用独立制稿环境中的 `@oai/artifact-tool` 和演示文稿校验工具。它们**不是数据 Pipeline 的运行依赖**；公司服务器只需安装 `pyproject.toml` 指定的数据处理依赖。PPTX 可以直接用办公室软件编辑，无须安装报告制作工具。

若在具有同样制稿工具的环境重新生成，需要设置 `PROJECT_ROOT、PRESENTATIONS_SKILL、RUNTIME_PYTHON、RUNTIME_NODE_MODULES`，使 Node 能解析 `@oai/artifact-tool`。最终输出不能覆盖既有文件，重新生成前请另存旧稿，或通过 `DECK_FILENAME` 指定新名称。

`PROJECT_ROOT` 指向当前仓库根目录。移动或重命名项目目录后，应重新设置这个变量；不要复用旧终端中保存的绝对路径。制稿环境的其余变量继续指向各自工具的实际安装位置。

本次 PDF 使用 LibreOffice 导出，字体为 Arial Unicode MS。制稿环境需要能找到中文字体；缺字时修复字体配置后重新导出，不能仅凭 PDF 文件存在就认为成功。导出后逐页渲染、确认字形与换行，再交付。不要将本机字体文件直接复制到公司环境而忽略其使用条件。

主管看到的结论和数字来自 JSON 验收记录，不是手工编造的跑分。修改正文时，保持“数据工程／小模型接口验证”与“完整 VLA／机器人能力验证”的边界。
