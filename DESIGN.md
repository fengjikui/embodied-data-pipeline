# Design

## Scene and theme

研究人员在明亮办公室阅读，主管在会议室观看投屏。浅色纸面与深色字使表格、公式和出处清楚；不是监控大屏。

## Color

沿用原离线报告的暖纸与绿色墨色，转为 OKLCH：paper `oklch(0.98 0.008 95)`，ink `oklch(0.29 0.025 160)`，muted `oklch(0.48 0.018 160)`，accent `oklch(0.49 0.095 45)`。克制配色，状态同时用文字表达。

## Typography

使用本机 PingFang SC、Microsoft YaHei 与系统 sans，离线无字体下载。标题约 40–64px，章节 28px，正文 17–19px，注释 14px。技术代码使用系统 monospace。中文正文行宽限制约 38 个汉字。

## Structure

固定章节目录、左对齐标题、分步骤流程带、横向表格与原生 details。摘要展示和详细阅读共享内容。窄屏目录回到文档顶部，表格在独立容器横向滚动，正文不溢出。

## Interaction and print

章节锚点、场景选择、学习/汇报模式、键盘 focus-visible、打印按钮。禁止外部脚本、字体、自动播放动画。打印展开细节、保留来源、隐藏操作按钮。
