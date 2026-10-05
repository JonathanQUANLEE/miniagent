# 贡献指南（CONTRIBUTING）

感谢你对 Mini Agent 的兴趣！这是一个教学取向的参考实现，欢迎 Issue 与 PR。

## 本地开发

```bash
git clone https://github.com/JonathanQUANLEE/miniagent.git
cd miniagent
pip install -r requirements-dev.txt

cp .env.example .env        # 填入你自己的 API Key（.env 已被 gitignore）
pytest tests/ -q            # 15 个测试，全部离线，零 API 消耗
```

## 提交规范

- 提交信息建议遵循 Conventional Commits（`feat:` / `fix:` / `docs:` / `test:`）。
- 涉网行为（真实 LLM 调用）请勿写进单元测试；离线可测的纯函数逻辑才进 `tests/`。
- 每个新能力优先保持"单文件自包含、可独立运行"的项目惯例。

## 代码风格

- 注释回答"为什么这么写"，不复述代码本身。
- 安全相关改动（权限、密钥、命令执行）必须附带对应的单元测试。
- 任何改动不得把密钥引入仓库；PR 前 `git grep sk-` 自查一遍。

## 报告问题

- Bug 请附：复现步骤、预期/实际行为、Python 版本、`.env` 中 `MODEL` 的值（**不要贴 API Key**）。
- 功能建议请说明使用场景与期望行为。
