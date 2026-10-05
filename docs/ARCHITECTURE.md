# 架构文档（ARCHITECTURE）

> 本文档面向想深入理解 Mini Agent 内部设计的读者。阅读前建议先跑通 [README](../README.md) 里的 Quick Start。

## 1. 项目定位

Mini Agent 是一个**零框架**的 LLM Agent 参考实现：不依赖 LangChain / LlamaIndex 等任何 Agent 框架，
仅使用 OpenAI 官方客户端，用 26 个自包含模块把一个 Agent 从第一次 LLM 调用做到可部署的 Web 服务。

它适合三类读者：

1. **想理解 Agent 原理的工程师**——每个零件都能对应到框架里"被藏起来"的那层；
2. **需要定制 Agent 的团队**—— fork 后改工具层即可，没有框架升级负担；
3. **教学场景**—— 26 个模块按演进顺序排列，每一步只引入一个新概念。

## 2. 设计原则

```text
设计原则
├── 零框架：循环、重试、注册表全部手写，理解先于封装
├── 故障驱动演进：每个模块都对应一类真实故障（失控→保险丝，429→退避，盲飞→黑匣子）
├── 可观察优先：屏幕实时输出 + trace.log 文件双写，行为永远可回放
├── 安全默认：命令白名单两道闸 + max_steps/timeout 双保险丝，拒绝信息回喂模型
└── 单文件可运行：每个 step 自包含，可独立 demo、可独立读
```

## 3. 分层架构

```text
Mini Agent Runtime
├── 大脑层    step1 / step14      LLM 调用 + 三段式退避重试（2^n 退避 → 换模型 → 上报）
├── 决策循环  step3 / step5       while + finish_reason 红绿灯 + max_steps 保险丝
├── 工具层    step2~8 / step22    六只手 + 注册表分发 + 未知工具优雅拒绝
├── 安全层    step23 / step26     白名单两道闸 + SAFE/ASK/AUTO 三模式
├── 记忆层    step10 / step12     memory.txt 跨会话 + Compaction 上下文压缩
├── 观测层    step16 / step26     trace.log 黑匣子（屏幕/文件双写，带时刻戳）
├── 评测层    step17              固定考卷 + 自动判分 + 单题故障隔离
├── 协作层    step18~21           Subagent 独立档案 / Supervisor 拆派收合 / 线程并行
├── 知识层    step24              RAG 五步：切片→向量化→入库→检索→引用生成
├── 协议层    step25              MCP 双端：JSON-RPC 2.0 over stdio
└── 服务层    step26              FastAPI + SSE 流式 + Web UI + Docker
```

## 4. 一次流式请求的生命周期

以 `GET /chat/stream?question=…` 为例：

```text
浏览器(EventSource)
   │  GET /chat/stream?question=…
   ▼
FastAPI 路由 ──► StreamingResponse(sse_chat(question))
   │
   ▼
sse_chat 生成器（每 yield 一条都是 data: {json}\n\n）
   │  ① event: start
   ▼
Agent Loop（最多 MAX_STEPS=8 轮）
   │  ② chat.completions.create(stream=True, tools=…)
   │
   │  ── 文字碎片 delta.content ──► event: delta（打字机效果）
   │  ── 工单碎片 delta.tool_calls ──► 按 index 聚合成完整 JSON 文字条
   │
   │  有工单 → ③ event: tool（名称+参数+结果预览）
   │            权限闸门 command_allowed() → 两道闸全过才 subprocess
   │            结果以 role=tool 回喂档案 → 下一轮
   │
   │  无工单 → ④ event: done（最终答案 + 轮数）
   ▼
连接关闭
   ※ 任何异常 → event: error（礼貌失败：浏览器显示错误并收尾，连接不悬挂）
```

## 5. 关键设计决策

### 5.1 决策循环：`while` + `finish_reason`，而不是状态机

Agent 的本质是"模型决策 → 代码执行 → 结果反馈"的闭环。`finish_reason == "tool_calls"`
即"模型还想动手"，否则即"模型开口交卷"。用一行红绿灯判断表达这个语义，比状态机
更贴近协议本身；`max_steps` 保险丝兜住一切失控场景。

### 5.2 流式下工具单碎片必须按 index 聚合

流式模式下 `tool_calls` 的 `arguments` 也是碎片，直接 `json.loads` 半截工单是 bug。
实现里维护 `index → {id, name, arguments}` 聚合槽，攒齐后再分发。这是 SSE + Function
Calling 组合最容易踩的坑（也是本项目的面试级考点之一）。

### 5.3 注册表：加工具零改分发

工具分发不用 `if/elif` 长链，而是 `名字 → 函数` 的字典注册表（step22）。
新增工具 = 注册一次，分发循环零修改——对扩展开放、对修改关闭。
**这个注册表同时是 MCP 的插座位**：step25 从远端拉回工具菜单后原样挂进注册表，
模型侧的点菜逻辑一行不改。

### 5.4 权限：两道闸，并诚实其边界

```text
命令进入
  │
  ├─ 第一道闸：第一个词 ∈ SAFE_COMMANDS 白名单？
  ├─ 第二道闸：整行含 & | ; ` $ ( ) < > 等链式/注入符号？
  ▼
  全过 → subprocess(timeout=30)     任一不过 → 拒绝文本回喂模型
```

诚实边界：符号拦截本质是黑名单思路的补强，不能承诺 100% 防御。
彻底方案是容器隔离（本项目 Dockerfile 即第四层防线）——白名单挡意外，沙盒挡恶意。

### 5.5 上下文管理：压缩实测

43KB 文档 = 15,512 tokens，摘要后 265 tokens（压缩 98.3%）。策略是"保结论、丢细节"，
细节留在硬盘按需 `read_file` 取回。RAG 与压缩是一对对偶：一个"按需取用"，一个"留结论"。

### 5.6 RAG：渐进升级路径

演示语料 <100 块，向量检索用纯 Python 余弦 + 普通列表排序即可；`embed()` 是单点函数，
配 `EMBEDD_MODEL` 环境变量即切换到真实 Embedding API，失败自动降级本地哈希向量
（crc32 稳定哈希——内置 `hash()` 每进程换盐，不能用于检索）。语料规模上来后，
换 Chroma/Milvus 只动 `build_index()/search()` 两个函数。

### 5.7 失败工程三段式

退避重试（`2**attempt`，实测 2→4 秒）→ Fallback（备用模型清单）→ 诚实上报用户。
全程程序不崩：错误要么被重试吸收，要么变成一条用户看得见的消息/SSE 事件。

### 5.8 评测先行

固定考卷（TASKS）+ 自动判定 + 成功率报告；改代码前跑一次存基准，改后重考对比。
单题崩溃只记 FAIL 不拖死整场（try/except 故障隔离）。`tests/` 中的单元测试
全部离线、零 API 消耗，可挂 CI。

## 6. 已知限制

- 单进程单循环，没有并发会话隔离（生产需按会话分档案）
- 评测是 smoke 级考卷，不是系统化评测平台（Roadmap 中的 AgentLab）
- 白名单是"防意外"强度，不是"防恶意"强度——面向互联网暴露前请加容器
- 免费模型有保质期，`MODEL` 需要随供应商现状更换

## 7. 升级路线图

见 [README · Roadmap](../README.md#-roadmap)：LangGraph 对照实现、向量库接入、
AgentLab 评测平台、多模态工具。
