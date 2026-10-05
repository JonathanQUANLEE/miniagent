# ============================================================
# step25_mcp_client.py — MCP 客户端：把 step22 注册表的"插座位"真插上
# ------------------------------------------------------------
# 上一步（step22）的结论：MCP 拉到远端菜单后挂进 TOOL_REGISTRY，
# 模型依旧只认菜单，点菜逻辑一行不改。今天验证这句话。
#
# 全流程四拍：
#   ① 握手 initialize        → 拿到 serverInfo（确认对面是谁、说什么版本）
#   ② 拉菜单 tools/list       → 远端工具三件套直接透传成 OpenAI tools 参数
#   ③ 注册 registry           → 菜单名字 → "转发到 tools/call" 的闭包
#   ④ 照常开 Agent 循环       → 模型开单 → 客户端转发 → 结果回喂档案
#
# 传输层：subprocess 启动 mini_mcp_server.py，stdin/stdout 各接一根管子，
# 一行一条 JSON——这和真实 MCP Host 的 stdio 传输是同一个形状。
# ============================================================
import os
import sys
import json
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

import httpx
from openai import OpenAI

# ---------- LLM 客户端（和 step1 同款，代理按 .env 可选）----------
PROXY = os.environ.get("HTTP_PROXY", "").strip()
HTTP_CLIENT = httpx.Client(proxy=PROXY, timeout=60) if PROXY else httpx.Client(timeout=60)
llm = OpenAI(
    api_key=os.environ.get("API_KEY") or "unset",
    base_url=os.environ.get("BASE_URL", "https://openrouter.ai/api/v1"),
    http_client=HTTP_CLIENT,
)
MODEL = os.environ.get("MODEL", "inclusionai/ling-3.0-flash-sante:free")

SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mini_mcp_server.py")


# ============================================================
# MCP 客户端：一根进水管、一根出水管、一个自增的请求编号
# ============================================================
class MCPClient:
    def __init__(self, server_path):
        # stderr 不接管 → 服务器的日志直接透到我们的控制台（协议走管子，日志走屏幕）
        self.proc = subprocess.Popen(
            [sys.executable, server_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            text=True, encoding="utf-8",
        )
        self._next_id = 0

    def _send(self, payload):
        self.proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def request(self, method, params=None):
        # 有 id 的叫请求：必须等回包；回包按 id 对账（和 tool_call_id 一个道理）
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params or {}})
        line = self.proc.stdout.readline()
        resp = json.loads(line)
        if "error" in resp:
            raise RuntimeError(f"MCP 错误：{resp['error']}")
        return resp["result"]

    def notify(self, method, params=None):
        # 没有 id 的叫通知：只管发，不等回包
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    # ---------- 协议三方法 ----------
    def initialize(self):
        result = self.request("initialize", {"protocolVersion": "2024-11-05",
                                             "capabilities": {}, "clientInfo": {"name": "miniagent"}})
        self.notify("notifications/initialized")   # 握手第二步：通知，不回包
        return result

    def list_tools(self):
        return self.request("tools/list")["tools"]

    def call_tool(self, name, arguments):
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        return result["content"][0]["text"]


# ============================================================
# ③ 注册：远端菜单 → 本地注册表
#    闭包把 name 提前装进去（default 参数防 late-binding 踩坑）
# ============================================================
def build_registry(client, tools):
    registry = {}
    for t in tools:
        def make_forwarder(tool_name):
            def forwarder(arguments):
                return client.call_tool(tool_name, arguments)
            return forwarder
        registry[t["name"]] = make_forwarder(t["name"])
    return registry


# ============================================================
# ④ Agent 循环：和 step3/step22 一模一样的舞步，工具换了供货渠道
# ============================================================
def run_agent(question, registry, tools_schema, max_steps=5):
    messages = [
        {"role": "system", "content": "你是一个助手，需要用时从工具菜单里选。"},
        {"role": "user", "content": question},
    ]
    for step in range(1, max_steps + 1):
        r = llm.chat.completions.create(
            model=MODEL, messages=messages, tools=tools_schema,
        )
        msg = r.choices[0].message
        if not msg.tool_calls:                      # 🟢 不开单 → 循环出口
            print(f"[第{step}轮 🟢] {msg.content}")
            return msg.content

        print(f"[第{step}轮 🔴] 模型开了 {len(msg.tool_calls)} 张工单")
        messages.append({"role": "assistant", "content": msg.content,
                         "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            print(f"  工单: {tc.function.name}({args})")
            try:
                result = registry[tc.function.name](args)      # ← 转发到 MCP tools/call
            except Exception as e:
                result = f"调用失败：{e}"
            print(f"  结果: {result}")
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
    return "已达最大轮数保险丝"


def main():
    client = MCPClient(SERVER_PATH)

    # ① 握手
    info = client.initialize()
    print(f"【握手】对面是 {info['serverInfo']['name']} v{info['serverInfo']['version']}，"
          f"协议版本 {info['protocolVersion']}")

    # ② 拉菜单（原样透传成 OpenAI tools 参数——inputSchema 就是 parameters）
    tools = client.list_tools()
    tools_schema = [{"type": "function",
                     "function": {"name": t["name"], "description": t["description"],
                                  "parameters": t["inputSchema"]}}
                    for t in tools]
    print(f"【菜单】{[t['name'] for t in tools]}")

    # ③ 注册
    registry = build_registry(client, tools)

    # ④ 跑两个问题：一个要用工具，一个不用
    run_agent("请用 word_count 工具统计这句话：The quick brown fox jumps over the lazy dog",
              registry, tools_schema)
    print()
    run_agent("现在几点了？", registry, tools_schema)

    client.proc.terminate()   # 收工关掉服务器进程（PID 把手，step15 老朋友）


if __name__ == "__main__":
    main()
