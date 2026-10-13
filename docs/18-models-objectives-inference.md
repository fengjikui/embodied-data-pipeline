# 模型、标签、损失与推理：从 Transformer 到机器人

核查日期：2026-10-14。以下区分通用算法原理、上游实现与实验室选型。生产模型训练尚未在本仓库执行；现有真实训练是小型 BC 接口探针，本次新增 PPO 教学。

## 1. 先区分模型承担的工作

VLA 是用视觉 V、语言 L 和本体状态生成动作 A 的策略家族，不是固定一个 Transformer 结构。一个工程系统还可能包含视觉检测/几何、导航、任务状态机、力控、全身控制以及工具控制器。**ACT、Diffusion Policy 可以是没有语言输入的模仿学习策略，不应自动称为 VLA。**

共同形式是：`o_t = 图像历史 + 状态 + 可获得的指令`，策略输出 `A_t = [a_t, ..., a_(t+H-1)]`。同样是 action，可能表示关节目标、末端位姿增量、速度、力矩或某个全身控制器的运动 latent。输出维度相同也不代表动作含义相同。

## 2. 主要模型家族比较

| 家族/代表 | 核心结构 | 监督标签与目标 | 训练输入容器 | 推理方式 | 本项目定位 |
|---|---|---|---|---|---|
| BC MLP/CNN | 图像编码＋状态融合＋回归头 | 示范连续动作，MSE/L1 | 自定义张量/NPZ | 一次 forward | 理解数据接口与基线 |
| ACT | 图像骨干＋Transformer＋条件变分潜变量，输出动作块 | 示范动作块，重建＋KL | LeRobot 或原实现数据 | 生成块，可时间集成 | 固定工位第一组学习基线 |
| Diffusion Policy | 条件视觉/状态编码＋去噪网络 | 加噪动作的噪声/score | LeRobot/HDF5 adapter | 迭代去噪生成动作块 | 多峰动作，比较延迟与准确率 |
| 离散 token VLA / OpenVLA | 视觉编码接入 LLM，离散动作 token 自回归 | 动作 token 交叉熵 | 原版使用 RLDS＋动作处理 | 生成 token 后解码物理动作 | 学习 LLM 到 action 的联系 |
| 连续 flow VLA / SmolVLA、π 系列 | VLM 条件＋连续动作专家 | 含噪动作到示范的向量场 | LeRobot/模型指定视图 | 从噪声积分生成动作块 | 多任务、指令条件与迁移 |
| GR00T | 多模态语义编码＋动作生成，配置本体 | 连续动作，细节依版本 | GR00T 要求的 LeRobot＋modality config | 策略服务＋指定控制接口 | G1/全身路线重点候选 |
| 宇树 UnifoLM-WLA | 多模态/世界建模基础与动作专家 | 动作专家按其代码训练 | 其 action/state 规范 | 模型服务＋本体动作适配 | G1 专属规范优先核对 |
| RL actor/critic | actor 可用 MLP/循环网络；critic 估计价值 | rollout 奖励与回报，不是逐帧专家标签 | 环境生成观测/动作/奖励/终止 | actor 输出控制动作 | 行走或接触技能优化 |
| 世界模型＋规划 | 预测下一状态/latent/视频＋规划器 | 状态转移、视频/latent、奖励等 | 时间序列，动作条件按模型要求 | 预测/搜索/优化候选动作 | 辅助规划与训练，不能等价实机物理 |
| 智元 GO-1 | VLM＋latent planner＋动作专家，Air变体去掉planner | 原论文含latent计划标签与动作去噪目标 | 该版本LeRobot与具名通道配置 | 先预测latent计划，再生成动作块 | 双臂/跨本体对照，需目标数据与许可核查 |

不把不同版本“最新模型”排行当选型依据。此处引用核查的入口；准确依赖/算子和数据处理必须锁定 commit。

GO-1的latent planner表示“下一阶段应怎样变化”，不是直接可执行的电机命令；动作专家再根据观测/状态生成本体动作。训练latent表示可以利用前后图像对，但部署输入仍只能是当前可得观测。原论文与开源版本/GO-1 Air的配置需分开核对。[GO-1原报告](https://agibot-world.com/blog/agibot_go1.pdf)、[开源入口](https://github.com/OpenDriveLab/AgiBot-World)。

## 3. 监督学习的标签到底是什么

LLM SFT 的 label 是目标 token；机器人 BC 的 label 通常是人示范时**发出的动作目标**。当前状态是输入，接下来的动作块是监督标签。视频中的对象位置不是默认动作标签；任务成功 `success=true` 也不是动作向量。

例如观测 batch：`images [B,K,3,h,w]`，`state [B,D_s]`，`language token IDs [B,L]`；标签：`actions [B,H,D_a]`；有效性：`mask [B,H,D_a]` 或框架规定的逐时刻 pad mask。K 是相机数，H 是预测步数。我们的已有 NPZ 接口只有一路相机；下文多相机是模型契约示例。

训练期动作未来 H 步作为**标签**合法，未来图像/终局结果作为当前**输入**则泄漏。跨 episode 的末尾用 padding 与 mask，不从下一次尝试取标签。原生动作先保留，再按 train-only 统计处理；部署使用训练时相同统计，不能随现场新样本改均值。

## 4. 损失函数对照

### 4.1 连续 BC

`L_MSE = sum(mask * (pred_action - demo_action)^2) / sum(mask)`。

这是仓库 `training.masked_mse` 的真实目标。动作归一化改变各维损失权重；物理误差仍需逆归一化后按单位报告。虚构两维合成数据上的 loss 不能用来衡量 G1 扭矩或定位精度。

### 4.2 ACT

`L_ACT = L_reconstruction(pred_chunk, demo_chunk, pad_mask) + beta * KL(q(z|state,demo_chunk) || N(0,I))`。

训练时 encoder 用示范动作估计 latent，decoder 用观测和 latent 预测块；推理不能把真实未来动作送 encoder，通常使用先验 latent 的指定值。锁定 SDK 的 ACT 使用 L1 重建和 KL，而不是本仓库探针的 MSE。具体 padding 归约规则以代码为准。[ACT 官方说明](https://huggingface.co/docs/lerobot/en/act)、[原论文与实现](https://github.com/tonyzhaozh/act)。

### 4.3 Diffusion Policy

示例 DDPM 目标：`a_k = sqrt(alpha_bar_k)*a_demo + sqrt(1-alpha_bar_k)*epsilon`，`L = E[||epsilon_theta(a_k,k,o)-epsilon||²]`。噪声是训练目标，背后仍由示范动作生成训练样本。推理从随机噪声反复去噪，得到动作块。该路线能表示多种合理动作，采样次数影响延迟。[作者项目](https://diffusion-policy.cs.columbia.edu/)。

### 4.4 自回归动作 token

将物理动作按指定 tokenizer 离散化，`L_CE = -sum log p(action_token_i | o, instruction, previous_tokens)`。OpenVLA 原版是这一路线；tokenizer、bin 范围与归一化要一同部署。训练 token 准确不等于闭环成功；某些后续变体的动作头不同，不混写成原版行为。[OpenVLA](https://github.com/openvla/openvla)。

### 4.5 Flow matching

取噪声 `z~N(0,I)` 和示范 `a`，一种约定为 `x_tau=(1-tau)z+tau*a`；目标速度 `v*=a-z`，`L=E[||v_theta(x_tau,tau,o,l)-v*||²]`。推理从 tau=0 的噪声积分到 tau=1 的动作。不同实现可反向定义 tau，因此不能直接拷贝符号而忘记路径约定。[SmolVLA](https://huggingface.co/docs/lerobot/en/smolvla)、[openpi](https://github.com/physical-intelligence/openpi)。

## 5. 训练后怎么用

1. 加载模型、数据统计、相机顺序/预处理、动作契约与控制器版本。
2. 读取新图像与关节/接触状态，校验捕获时间与延迟；构造和训练一致的输入。
3. 推理得到动作块，逆归一化，再按已确认的单位、关节/坐标顺序转换。
4. 按任务选择执行前 k 步后重新观测；H 是预测长度，k 是实际开环执行长度，两者不必相同。
5. 控制器插值/跟踪并处理接触/平衡，工具控制器完成拧紧；监督程序监视状态、超时、接管和质量。
6. 保存预测、实际命令、实测状态与结果。模型对“已拧紧”的语言判断不能替代工具曲线/工艺检验。

简单闭环示意：

```python
while task_is_active:
    observation = synchronized_capture()
    predicted_chunk = policy(observation, current_instruction)
    native_chunk = training_statistics.inverse(predicted_chunk)
    reference = validated_action_adapter(native_chunk[:execute_steps])
    controller.track(reference)  # controller owns hardware execution
    log_prediction_command_measurement_and_tool_result()
```

这些函数是结构示意，**不是本仓库的真机 API**。本次 `infer_bc_offline.py` 实际运行的是已保存 validation 窗口的离线预测，不是闭环 G1 执行。

## 6. PPO 用什么数据、什么模型、什么目标

机器人行走常用仿真中的 on-policy PPO。actor 输入 deploy-time 可得的关节、IMU、运动命令与历史，输出关节目标偏移或控制动作；critic 训练时可以额外用地形/真实速度/物理参数等 privileged state。是否采用非对称 actor-critic 要查具体任务实现；不能把训练才有的信息误接进部署 actor。

环境每步输出 `o_t,a_t,r_t,o_(t+1),terminated,truncated`。还记录旧策略 log probability 与价值。标签不是“正确脚步”，而是奖励定义下的优势/回报。奖励可能包括速度跟踪、平衡、能耗、姿态、接触、碰撞；**奖励设错也会训练出投机策略**。

PPO 核心：`ratio=exp(new_log_prob-old_log_prob)`；最大化 `mean(min(ratio*A, clip(ratio,1-eps,1+eps)*A))`。最小化时取负号。critic 拟合回报，常加价值损失和 entropy 项；GAE 用 TD 残差构造优势。真正终止通常不 bootstrap；时间上限截断若对应 continuing task 应用终止前观测 bootstrap，不能用 reset 后观测。代码实现要区分这两种 done。

推理时通常只需 actor 和观测归一化/历史栈，不需要计算 PPO loss、GAE 或运行 critic。仿真训练还需机器人模型、关节限制、PD 增益、延迟和动力学；sim2sim 验证，再依据实机合同做 sim2real。见 [宇树 RL](https://github.com/unitreerobotics/unitree_rl_lab)、[rsl_rl](https://github.com/leggedrobotics/rsl_rl)、[PPO 原论文](https://arxiv.org/abs/1707.06347)。

本次 PPO 代码是一个虚构的一维有限时域环境，actor/critic 都是小 MLP，观测含剩余时间，最后一步是真正终止。它让你逐项检查 rollout、优势、ratio、checkpoint 与 actor 推理；没有机器人接触物理或步态，不证明行走能力。

## 7. RLHF 知识怎样迁移过来

PPO 的概率比、优势与 clipping 和你熟悉的 LLM PPO 共通，但机器人“环境反馈”是接触、运动与工具结果，不是文本偏好；actor 常输出连续分布，不是 token。GRPO/DPO 并不是走路的默认训练方法。接触技能也可能使用离策略 actor-critic，例如 SAC，或人接管辅助 RL；这通常需要在线 replay buffer、奖励/重置机制与控制接口。[SERL](https://github.com/rail-berkeley/serl)。先做好可重复的 BC 基线，再决定是否需要 RL。

## 8. 训练设备与选型顺序

数据接收、哈希、Parquet 质检通常是 CPU＋存储 I/O；模型训练依模型/分辨率/H/batch 选择加速器；大量物理仿真有其独立 GPU/驱动需求；实机推理需满足端到端周期和时延，训练服务器不必放在机器人上。

实验室可规划使用昇腾 A3 资源，但具体型号/内存/CANN、PyTorch/torch_npu、占用与访问尚未核实。不能因为“有 A3”就声称 Isaac Sim、TensorRT、JAX 或上游 CUDA 算子能直接运行。先做算子、精度、小 batch、保存/恢复与速度验证；NVIDIA 仿真/部署部分可能需要独立兼容节点。基础数据工程仍保持 Python/Parquet 的平台可移植性。

建议顺序：固定工位传统伺服/ACT → 需要语言、多任务时比较 SmolVLA → 用目标 G1 数据比较 UnifoLM-WLA/GR00T；π 系列作为强连续 VLA 候选。行走单独评估已有控制器与 RL；需要连续行走操作时再选择全身路线。选型表是实验室建议，不是未经试验的性能排名。
