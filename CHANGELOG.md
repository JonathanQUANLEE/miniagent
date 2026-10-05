# 更新日志（CHANGELOG）

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-10-05

首个正式版本。

### Added
- **核心运行时（step1~23）**：Agent Loop、工具调用、多工具分发、max_steps 保险丝、
  文件读写追加、终端命令、自我纠错循环、跨会话记忆、上下文测量与压缩、技能文件、
  退避重试、后台任务、Trace 黑匣子、自动评测、Subagent / Supervisor / 多智能体 /
  并行、工具注册表、权限三模式
- **产品化扩展（step24~26）**：RAG 全链路（切片 / Embedding 降级兜底 / 余弦检索 /
  引用回答）、MCP 协议双端实现（JSON-RPC 2.0 over stdio）、FastAPI 服务
  （REST + SSE 流式 + 单文件 Web 聊天页）、Dockerfile 一键部署
- **测试**：15 个离线单元测试（RAG / 权限 / MCP 协议分发），零 API 消耗，可挂 CI
- **文档**：README（中/英）、架构文档、贡献指南、安全政策

### Fixed
- 命令白名单只校验第一个词导致 `echo hello && del x` 链式注入穿透
  （现为两道闸：白名单 + 链式/注入符号全拦截，附回归测试）
- 评测考卷单题崩溃拖死整场（改为 try/except 单题故障隔离）
- 流式对话中模型调用失败导致 SSE 流静默悬挂（改为 `error` 事件礼貌失败）

### Security
- API Key 全面移出代码：统一走 `.env` + `python-dotenv`，仓库仅含模板
- Docker 运行时密钥经 `-e` 注入，绝不打进镜像层
