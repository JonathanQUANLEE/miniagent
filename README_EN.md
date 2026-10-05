<div align="center">

# Mini Agent

**A from-scratch LLM Agent in 26 progressive modules — no agent framework, only the official OpenAI client.**

*零框架从零手搓的 LLM Agent —— 从第一次 LLM 调用到完整产品化 Runtime 的 26 个渐进模块。*

[简体中文](README.md) | English

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![CI](https://github.com/JonathanQUANLEE/miniagent/actions/workflows/tests.yml/badge.svg)
![Tests](https://img.shields.io/badge/tests-15%20passed-brightgreen)
![Framework](https://img.shields.io/badge/agent%20framework-zero-orange)

<img src="docs/assets/web-ui.png" alt="Mini Agent Web UI" width="720">

</div>

---

## Why from scratch?

Frameworks (LangChain, LlamaIndex, …) hide the decisions: **users of a framework know how
to call it; people who built one from scratch know why.** This project hand-builds every
part of an agent — the loop, tools, memory, compaction, retries, multi-agent, permissions,
registry — then adds the production layer (RAG / MCP / streaming API) on top.

```text
Mini Agent Runtime
├── Brain        step1 / step14     LLM calls + exponential backoff retry
├── Loop         step3 / step5      while + finish_reason gate + max_steps fuse
├── Tools        step2~8 / step22   six built-in tools + registry dispatch
├── Safety       step23 / step26    command whitelist (two gates) + SAFE/ASK/AUTO
├── Memory       step10 / step12    cross-session memory + context compaction
├── Telemetry    step16 / step26    trace.log black box (console + file dual write)
├── Evaluation   step17             fixed test set + auto scoring + fault isolation
├── Multi-agent  step18~21          subagents / supervisor / parallel threads
├── Knowledge    step24             full RAG pipeline: chunk→embed→index→retrieve→cite
├── Protocol     step25             MCP both ends: JSON-RPC 2.0 over stdio
└── Service      step26             FastAPI + SSE streaming + web UI + Docker
```

## ✨ Features

| Capability | Notes | Module |
| :--- | :--- | :--- |
| 🔁 Agent Loop | `while` + `finish_reason` gate + `max_steps` fuse | step3 / 5 |
| 🛠️ Tool Calling | model emits `tool_calls` → `json.loads` → registry dispatch → feed back | step2~8 / 22 |
| 🩹 Self-repair | write→run→read stderr→fix→rerun; heals in 5 rounds in the recorded demo | step9 |
| 🧠 Memory & Compaction | cross-session memory; compaction shrinks context by 98.3% | step10 / 12 |
| 📚 RAG pipeline | chunking → embedding (API with local-hash fallback) → cosine Top-K → cited answers | step24 |
| 🔌 MCP, both ends | full handshake (`initialize` / `tools/list` / `tools/call`); remote menu plugs into the registry | step25 |
| ⚡ Streaming API | SSE typewriter; tool-call fragments aggregated by index before parsing | step26 |
| 🖥️ Web UI | single-file chat page via EventSource, zero frontend build | step26 |
| 🛡️ Safety | whitelist + chained-injection rejection (fixes `echo && del` bypass), with regression tests | step23 / 26 |
| 🧪 Testing | 15 offline unit tests, zero API cost, CI-ready | tests/ |
| 🐳 Deployment | one-command Docker; secrets injected at runtime | Dockerfile |

## 🚀 Quick Start

```bash
# Requires Python 3.10+ (developed on 3.12)
pip install -r requirements.txt

# Configure: copy the template and fill in your OpenAI-compatible API key
cp .env.example .env

# Run representative modules (step1~26 in order is the full learning path)
python step9_self_fix.py       # self-repair loop
python step17_evaluation.py    # automated evaluation
python step24_rag.py           # RAG with cited answers
python step25_mcp_client.py    # MCP handshake → list tools → invoke

# Open the streaming web chat
python step26_api.py           # visit http://127.0.0.1:8000
```

> 💡 Free models expire: on 404, just change `MODEL` in `.env`.
> RAG runs offline without `EMBEDD_MODEL` — it falls back to local hash embeddings.

## 🐳 Docker

```bash
docker build -t miniagent .
docker run -p 8000:8000 -e API_KEY=sk-... -e MODEL=your-model miniagent
# The container itself is the sandbox (third defense layer). Open http://localhost:8000
```

## 🔌 API

Start `step26_api.py`, then (auto docs at `/docs`):

| Method | Path | Description |
| :--- | :--- | :--- |
| GET | `/` | Web chat UI (SSE streaming) |
| POST | `/chat` | One-shot Q&A, returns `{answer, steps, rounds, elapsed}` |
| GET | `/chat/stream?question=…` | SSE event stream: `start → delta… / tool… → done / error` |

```text
data: {"type": "start"}
data: {"type": "delta", "text": "Let me"}
data: {"type": "tool", "name": "run_command", "args": {"command": "dir"}, "result": "exit code: 0…"}
data: {"type": "done", "answer": "……", "steps": 3}
```

## 📚 The 26 modules

<details>
<summary><b>Core (step1~23)</b></summary>

| Step | File | What it teaches |
| :--- | :--- | :--- |
| 1 | `step1_hello_llm.py` | First LLM call: messages, roles, proxy |
| 2 | `step2_first_tool.py` | First tool: what tool calling really is |
| 3 | `step3_agent_loop.py` | Agent loop: while + finish_reason gate |
| 4 | `step4_multi_tool.py` | Multi-tool dispatch, chaining |
| 5 | `step5_max_steps.py` | The max_steps fuse |
| 6 | `step6_file_reader.py` | read_file |
| 7 | `step7_file_writer.py` | write_file ('w' truncation risks) |
| 8 | `step8_terminal.py` | run_command: subprocess, exit codes |
| 9 | `step9_self_fix.py` | **Self-repair loop** |
| 10 | `step10_memory.py` | Cross-session memory |
| 11 | `step11_context_lab.py` | Token metering bench |
| 12 | `step12_compaction.py` | **Context compaction surgery** |
| 13 | `step13_skills.py` | Skill files: consistency > luck (A/B test) |
| 14 | `step14_retry.py` | Failure engineering: backoff + escalate |
| 15 | `step15_background.py` | Background tasks: Popen + polling |
| 16 | `step16_observability.py` | Black box: replayable trace.log |
| 17 | `step17_evaluation.py` | **Evaluation**: fixed test set + scoring |
| 18 | `step18_subagent.py` | Subagent: isolated transcript |
| 19 | `step19_supervisor.py` | Supervisor: split→dispatch→collect→merge |
| 20 | `step20_telephone.py` | Anti-pattern: chain-of-relays decays 60% |
| 21 | `step21_parallel.py` | Parallelism with threads |
| 22 | `step22_registry.py` | Tool registry: the MCP plug-in slot |
| 23 | `step23_permissions.py` | Permissions: whitelist + three modes |

</details>

| Step | File | Production extension |
| :--- | :--- | :--- |
| 24 | `step24_rag.py` | **Full RAG**: chunk / embed (with offline fallback) / cosine retrieval / citations |
| 25 | `step25_mcp_client.py` + `mini_mcp_server.py` | **MCP both ends**: server speaks JSON-RPC 2.0 (stdout = protocol, stderr = logs); client registers the remote menu — model-side code unchanged |
| 26 | `step26_api.py` | **Productization**: FastAPI REST + SSE (tool-call fragment aggregation by index) + single-file web UI + Docker |

## 📊 Measured results (not estimates)

- **Context compaction**: 43KB doc = 15,512 tokens → 265-token summary (**98.3% saved**)
- **Self-repair**: seeded typo (`prnt`) — agent heals in **5 rounds** (write→fail→read stderr→fix→rerun)
- **Failure engineering**: invalid model name → three 400s with 2→4s backoff → honest escalation, **no crash**
- **Parallel speedup**: 4 tasks, serial 10.0s → parallel 7.1s (**29% faster**)
- **Chain-of-relays decay**: 3 relays erode domain vocabulary, content shrinks 60% → supervisor pattern instead
- **Evaluation**: 3/3 = **100%** on the fixed test set
- **Permission gates**: `del` and `echo hello && del` both blocked (regression-tested)

## 📁 Project structure

```text
miniagent/
├── step1~23_*.py          # core 23 modules (self-contained, runnable)
├── step24_rag.py          # RAG pipeline
├── step25_mcp_client.py   # MCP client
├── mini_mcp_server.py     # MCP server (JSON-RPC 2.0 over stdio)
├── step26_api.py          # FastAPI + SSE + web UI
├── docs/                  # ARCHITECTURE.md, RAG knowledge base, assets
├── skills/                # agent skill files
├── tests/                 # 15 offline unit tests
├── requirements.txt       # runtime deps
├── requirements-dev.txt   # dev deps (pytest)
├── Dockerfile             # one-command deploy
└── .env.example           # config template (.env never committed)
```

## 🔒 Security

- **Secrets never committed**: keys live in `.env` via `python-dotenv`; only the template is in the repo
- **Two-gate command whitelist**: first-token whitelist + rejection of `& | ; ` ` $ ( ) < >` — fixes the "first token only" bypass, regression-tested
- **Double fuses**: `max_steps` against runaway loops, `timeout=30` against stuck commands
- **Rejection is feedback**: denied commands are fed back so the model retries compliantly
- **Docker sandbox**: container isolation is the third defense layer

## 🧪 Testing

```bash
pip install -r requirements-dev.txt
pytest tests/ -q        # 15 tests, fully offline, zero API cost
```

## 📖 Documentation

- [Architecture deep-dive](docs/ARCHITECTURE.md) — design decisions & trade-offs
- [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security policy](SECURITY.md)

## ❓ FAQ

**Why not LangChain?**
Frameworks hide decisions. Every "framework feature" here — loop, retry, registry,
permissions — was hand-written against a real failure. Users of LangChain know how to
call it; builders know why. (The roadmap includes a LangGraph re-implementation for comparison.)

**Why a local hash vector instead of a vector DB?**
Demo corpus < 100 chunks — a sort is enough. `embed()` is a single function; upgrading to
a real embedding API (set `EMBEDD_MODEL`) or Chroma/Milvus touches nothing else.

**Why one file per step?**
This is a progressive learning archive: every file runs standalone, so you can see exactly
where and why each part was added. `step26_api.py` shows how the parts assemble into a service.

## 🗺️ Roadmap

- [ ] LangGraph re-implementation of the core loop, module-by-module comparison
- [ ] Vector DB integration (Chroma / Milvus)
- [ ] AgentLab: dataset + runner + judge + reporter evaluation platform
- [ ] Multimodal tools (screenshot understanding)

## License

[MIT](LICENSE) © 2026 JonathanQUANLEE
