# Mini Agent · 从零手搓的 LLM Agent

> **零框架**、23 个渐进式 step，从第一次 LLM 调用一路手搓到完整 Agent Runtime。
> 每一步都能跑、每一行都能讲清楚为什么这么写。

A from-scratch LLM Agent built in 23 progressive steps — no agent framework, only the official OpenAI client.

---

## 为什么从零手搓

框架（LangChain / LlamaIndex 等）把决策藏了起来：用它们的人知道**怎么调**，
手写过的人知道**为什么**。本项目从 `hello LLM` 开始，把 Agent 的每一个零件亲手造一遍：

```text
Mini Agent Runtime（step23 总装形态）
├── 大脑层：LLM 调用 + 三段式退避重试（step1 / step14）
├── 决策循环：while + finish_reason 红绿灯 + max_steps 保险丝（step3 / step5）
├── 工具层：六只手（读写/追加/终端/算术）+ 注册表分发 + 未知工具优雅拒绝（step2~8 / step22）
├── 安全层：命令白名单 + SAFE/ASK/AUTO 三模式（step23）
├── 记忆层：memory.txt 跨会话记忆 + 上下文压缩（step10 / step12）
├── 观测层：trace.log 黑匣子，屏幕/文件双写（step16）
├── 评测层：固定考卷 + 自动判分 + 成功率报告（step17）
└── 协作层：Subagent 独立档案 / Supervisor 拆派收合 / 多线程并行（step18~21）
```

## 23 个 Step 的演进路径

| Step | 文件 | 学到什么 |
| :--- | :--- | :--- |
| 1 | `step1_hello_llm.py` | 第一次 LLM 调用：messages、role、代理配置 |
| 2 | `step2_first_tool.py` | 第一个工具：tool calling 的本质（模型开单，Python 干活） |
| 3 | `step3_agent_loop.py` | Agent Loop：while + finish_reason 红绿灯 |
| 4 | `step4_multi_tool.py` | 多工具分发、链式串联 |
| 5 | `step5_max_steps.py` | 护栏：max_steps 防失控 |
| 6 | `step6_file_reader.py` | read_file：让 Agent 读懂文件 |
| 7 | `step7_file_writer.py` | write_file：'w' 清空风险、落盘验证 |
| 8 | `step8_terminal.py` | run_command：subprocess 四参数、退出码 |
| 9 | `step9_self_fix.py` | **自我纠错循环**：写→跑→读报错→改→重跑 |
| 10 | `step10_memory.py` | 跨会话记忆：先回忆再记账 |
| 11 | `step11_context_lab.py` | 上下文测量实验台：token 账单 |
| 12 | `step12_compaction.py` | **上下文压缩手术**：摘要替换原文 |
| 13 | `step13_skills.py` | 技能文件：稳定 > 偶尔聪明（A/B 实验） |
| 14 | `step14_retry.py` | 失败工程：退避重试 2→4s + 上报用户 |
| 15 | `step15_background.py` | 后台任务：Popen 双房间 + 轮询 |
| 16 | `step16_observability.py` | 黑匣子：trace.log 全程可回放 |
| 17 | `step17_evaluation.py` | **评测**：固定考卷 + 自动判分 |
| 18 | `step18_subagent.py` | 子 Agent：独立档案、只交结果 |
| 19 | `step19_supervisor.py` | Supervisor 四拍：拆→派→收→合 |
| 20 | `step20_telephone.py` | 反面教材：传话链 3 手衰减 60% |
| 21 | `step21_parallel.py` | 并行：线程池提速实测 |
| 22 | `step22_registry.py` | 工具注册表：MCP 要插进去的位置 |
| 23 | `step23_permissions.py` | 权限：白名单 + SAFE/ASK/AUTO 三模式 |

## 实测数据（不是估算，是跑出来的）

- **上下文压缩**：43KB 文档 15,512 tokens → 摘要 265 tokens，压掉 **98.3%**
- **自我纠错**：代码埋雷（`prnt` 拼写错误），Agent **5 轮自愈**（写→炸→读 stderr→修→重跑→总结）
- **失败工程**：坏模型名三连 400，退避 2→4 秒后诚实上报，**程序全程不崩**
- **并行提速**：4 个任务串行 10.0s → 并行 7.1s（**省 29%**，省排队不省网络）
- **传话链衰减**：多 Agent 串联传 3 手，专业词汇全部磨平、内容缩水 60% → 因此改用 Supervisor 分工制
- **评测首考**：固定考卷 3 题 **3/3 = 100%**
- **权限拦截**：`del` 类危险命令被白名单拦下，拒绝信息回喂模型换方法

## 快速开始

```bash
# 环境要求：Python 3.10+（开发环境 3.12）
pip install -r requirements.txt

# 配置密钥：复制 .env.example 为 .env，填入你的 OpenRouter API Key
cp .env.example .env

# 跑几个有代表性的 step（按 1~23 顺序是完整学习路径）
python step9_self_fix.py       # 看自我纠错循环：Agent 自己把写错的代码改对
python step12_compaction.py    # 看上下文压缩：15512 → 265 tokens
python step17_evaluation.py    # 看自动评测：三题考卷跑分
python step23_permissions.py   # 看权限系统：危险命令被拦下
```

> ⚠️ 免费模型有保质期，若报 404 换 `.env` 里的 `MODEL` 即可；所有 step 依赖 `.env` 中的 `API_KEY`，请勿将真实 Key 提交进仓库。

## 目录结构

```text
miniagent/
├── step1~23_*.py     # 23 个渐进式实现（每个自包含，可直接运行）
├── skills/           # Agent 技能文件（如 code-review.md）
├── requirements.txt
├── .env.example      # 配置模板（真实 .env 不入库）
└── README.md
```

## 安全设计

- **密钥不入库**：API Key 走 `.env` + `python-dotenv`，仓库里只有模板
- **命令白名单**：`SAFE_COMMANDS` 集合 + SAFE/ASK/AUTO 三模式，危险命令直接拒绝
- **双保险丝**：`max_steps` 防循环失控，`timeout=30` 防命令卡死
- **拒绝也是反馈**：权限拒绝信息回喂模型，它会自己换合规的方法

## License

MIT
