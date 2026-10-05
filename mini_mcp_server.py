# ============================================================
# mini_mcp_server.py — 一个说真 MCP 协议的最小工具服务器
# ------------------------------------------------------------
# 协议：JSON-RPC 2.0 over stdio，一行一条 JSON（新行分隔）
# 三个核心方法：
#   initialize  → 握手，交换协议版本与能力
#   tools/list  → 返回工具菜单（含 inputSchema，供模型点菜）
#   tools/call  → 执行工具，结果装进 content 数组
#
# 铁律：stdout 只走协议通道，日志一律走 stderr——
#       混进去一行打印，客户端 parse 就炸（和 step15 的输出隔离是同一个道理）
# ============================================================
import sys
import json
import time
from datetime import datetime

# ---------- 工具定义（name / description / inputSchema 三件套，和 step2 菜单同构）----------
TOOLS = [
    {
        "name": "word_count",
        "description": "统计一段文字的词数和字符数",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要统计的文字"}
            },
            "required": ["text"],
        },
    },
    {
        "name": "now",
        "description": "返回服务器当前时间（模型没有时钟，这是它知道时间的唯一方式）",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


# ---------- 工具实现（普通 Python 函数，和 step2 的 add 没有本质区别）----------
def tool_word_count(arguments):
    text = arguments.get("text", "")
    return f"words={len(text.split())}, chars={len(text)}"


def tool_now(arguments):
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


HANDLERS = {"word_count": tool_word_count, "now": tool_now}


# ---------- JSON-RPC 方法分发 ----------
def handle_request(req):
    method = req.get("method", "")

    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "mini-mcp-server", "version": "1.0.0"},
        }

    if method == "tools/list":
        return {"tools": TOOLS}

    if method == "tools/call":
        params = req.get("params", {})
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        if name not in HANDLERS:
            return {"content": [{"type": "text", "text": f"未知工具：{name}"}], "isError": True}
        try:
            text = HANDLERS[name](arguments)
            return {"content": [{"type": "text", "text": text}], "isError": False}
        except Exception as e:
            # 工具内部出错也按协议回包，不让服务器崩——调用方自己决定怎么办
            return {"content": [{"type": "text", "text": f"工具执行出错：{e}"}], "isError": True}

    raise KeyError(method)   # 未知方法 → 交给外层转成 JSON-RPC error


def main():
    print("[mini-mcp-server] 启动，等协议请求…（这行走 stderr，不污染协议通道）",
          file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"[mini-mcp-server] 收到非法 JSON：{e}", file=sys.stderr)
            continue

        # 没有 id 的是通知（notification）——按协议不回包，比如握手第二步 initialized
        if "id" not in req:
            print(f"[mini-mcp-server] 通知：{req.get('method')}", file=sys.stderr)
            continue

        rid = req["id"]
        try:
            resp = {"jsonrpc": "2.0", "id": rid, "result": handle_request(req)}
        except KeyError:
            resp = {"jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32601, "message": f"method not found: {req.get('method')}"}}
        except Exception as e:
            resp = {"jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32603, "message": f"internal error: {e}"}}

        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()   # 不 flush 客户端就一直堵在 read 上


if __name__ == "__main__":
    main()
