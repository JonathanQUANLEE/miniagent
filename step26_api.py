# ============================================================
# step26_api.py — 产品化总装：FastAPI + SSE 流式 + Web 聊天界面
# ------------------------------------------------------------
# 把 Agent 内核（loop + 注册表 + 权限 + 黑匣子）包成 HTTP 服务：
#   GET  /              → 聊天网页（单文件内嵌，无前端构建）
#   POST /chat          → 一次性回答（JSON）
#   GET  /chat/stream   → SSE 流式（打字机效果，浏览器 EventSource）
#
# 流式的关键坑（对应面试 Q23）：tool_calls 的 arguments 也是碎片，
# 必须按 index 聚合成完整 JSON 文字条才能 json.loads——
# 半截工单直接分发是 bug。
#
# 权限升级：step23 的白名单只看第一个词，`echo hi && del x` 会穿透；
# 本版的 command_allowed() 同时拒绝所有链式/重定向/命令替换符号。
# ============================================================
import os
import sys
import json
import time
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

import httpx
from openai import OpenAI
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

# ---------- 配置 ----------
MODEL = os.environ.get("MODEL", "inclusionai/ling-3.0-flash-sante:free")
PROXY = os.environ.get("HTTP_PROXY", "").strip()
HTTP_CLIENT = httpx.Client(proxy=PROXY, timeout=60) if PROXY else httpx.Client(timeout=60)
llm = OpenAI(
    api_key=os.environ.get("API_KEY") or "unset",
    base_url=os.environ.get("BASE_URL", "https://openrouter.ai/api/v1"),
    http_client=HTTP_CLIENT,
)
MAX_STEPS = 8            # 保险丝：单次对话最大循环轮数
SAFE_COMMANDS = {"dir", "ls", "echo", "python", "cat", "type"}
FORBIDDEN_CHARS = "&|;`$()<>"    # 链式 / 管道 / 命令替换 / 重定向，一律拒绝

# ---------- 黑匣子（step16 同款双写，API 版）----------
os.makedirs("logs", exist_ok=True)


def log(event, detail=""):
    stamp = time.strftime("%H:%M:%S")
    line = f"[{stamp}] {event} {detail}".rstrip()
    print(line)
    with open(os.path.join("logs", "api_trace.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------- 权限闸门（step23 升级版，可单测）----------
def command_allowed(cmd):
    parts = cmd.split()
    if not parts:
        return False
    if parts[0].lower() not in SAFE_COMMANDS:     # 第一道：白名单看第一个词
        return False
    if any(ch in cmd for ch in FORBIDDEN_CHARS):  # 第二道：链式/注入符号全拦
        return False
    return True


# ---------- 四只手（step6/7/10/8 的签名原样搬来）----------
def read_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_file(args):
    with open(args["path"], "w", encoding="utf-8") as f:
        f.write(args["content"])
    return f"已写入 {len(args['content'])} 个字符到 {args['path']}"


def append_file(args):
    with open(args["path"], "a", encoding="utf-8") as f:
        f.write(args["content"])
    return f"已追加 {len(args['content'])} 个字符到 {args['path']}"


def run_command(args):
    cmd = args["command"]
    if not command_allowed(cmd):
        # 拒绝也是反馈：回喂给模型，它会自己换合规方法（step17 铁律）
        return f"权限拒绝：{cmd} 不在白名单或含链式符号。可用命令：{sorted(SAFE_COMMANDS)}"
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=30, encoding="utf-8", errors="replace")
    return f"退出码: {r.returncode}\n标准输出: {r.stdout}\n标准错误: {r.stderr}"


# ---------- 注册表（step22 同构）----------
TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "read_file", "description": "读取文件全文",
        "parameters": {"type": "object",
                       "properties": {"path": {"type": "string", "description": "文件路径"}},
                       "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file", "description": "把内容写入文件（覆盖）",
        "parameters": {"type": "object",
                       "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                       "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "append_file", "description": "把内容追加到文件末尾（不覆盖）",
        "parameters": {"type": "object",
                       "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                       "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "run_command", "description": "执行白名单内的终端命令",
        "parameters": {"type": "object",
                       "properties": {"command": {"type": "string", "description": "要执行的命令"}},
                       "required": ["command"]}}},
]


def execute_tool(name, args):
    dispatch = {"read_file": lambda a: read_file(a["path"]),
                "write_file": write_file,
                "append_file": append_file,
                "run_command": run_command}
    fn = dispatch.get(name)
    if fn is None:
        return f"未知工具：{name}"      # 优雅拒绝，不崩（step22 实测过的行为）
    try:
        return fn(args)
    except Exception as e:
        return f"工具执行出错：{type(e).__name__}: {e}"


# ---------- SSE 编码：一行 data: + 空行 ----------
def sse(obj):
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


# ---------- 流式循环（打字机版 Agent Loop）----------
def sse_chat(question, max_steps=MAX_STEPS):
    log("=== 任务开始 ===", question[:80])
    messages = [
        {"role": "system", "content": "你是 Mini Agent，一个能读写文件、执行白名单命令的助手。"
                                      "回答用中文，简洁。"},
        {"role": "user", "content": question},
    ]
    yield sse({"type": "start"})

    for step in range(1, max_steps + 1):
        stream = llm.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS_SCHEMA, stream=True,
        )
        content_parts = []
        tc_slots = {}                        # index → 半截工单聚合槽
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue
            if delta.content:                # 文字碎片 → 直接推给浏览器
                content_parts.append(delta.content)
                yield sse({"type": "delta", "text": delta.content})
            for tc in (delta.tool_calls or []):   # 工单碎片 → 按 index 聚合
                slot = tc_slots.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function and tc.function.name:
                    slot["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    slot["arguments"] += tc.function.arguments   # ← 拼回完整文字条

        if tc_slots:                         # 本轮有工单 → 执行 → 回喂 → 下一轮
            tool_calls = [{"id": s["id"], "type": "function",
                           "function": {"name": s["name"], "arguments": s["arguments"]}}
                          for s in tc_slots.values()]
            messages.append({"role": "assistant", "content": None, "tool_calls": tool_calls})
            for s in tc_slots.values():
                args = json.loads(s["arguments"] or "{}")
                log("工单", f"{s['name']} {str(args)[:100]}")
                result = execute_tool(s["name"], args)
                log("结果", str(result)[:100])
                yield sse({"type": "tool", "name": s["name"], "args": args,
                           "result": str(result)[:300]})
                messages.append({"role": "tool", "tool_call_id": s["id"], "content": str(result)})
            continue

        answer = "".join(content_parts)      # 无工单 → 🟢 出口
        log("=== 收官 ===", f"共 {step} 轮")
        yield sse({"type": "done", "answer": answer, "steps": step})
        return

    log("=== 保险丝 ===", f"超过 {max_steps} 轮强制停止")
    yield sse({"type": "done", "answer": "已达最大轮数保险丝，强制停止。", "steps": max_steps})


# ---------- 非流式循环（POST /chat 用，返回结构化结果）----------
def run_agent(question, max_steps=MAX_STEPS):
    started = time.time()
    messages = [
        {"role": "system", "content": "你是 Mini Agent，一个能读写文件、执行白名单命令的助手。"
                                      "回答用中文，简洁。"},
        {"role": "user", "content": question},
    ]
    steps_log = []
    for step in range(1, max_steps + 1):
        r = llm.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS_SCHEMA)
        msg = r.choices[0].message
        if not msg.tool_calls:
            return {"answer": msg.content, "steps": steps_log,
                    "rounds": step, "elapsed": round(time.time() - started, 1)}
        messages.append({"role": "assistant", "content": msg.content,
                         "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = execute_tool(tc.function.name, args)
            steps_log.append({"tool": tc.function.name, "args": args, "result": str(result)[:300]})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
    return {"answer": "已达最大轮数保险丝，强制停止。", "steps": steps_log,
            "rounds": max_steps, "elapsed": round(time.time() - started, 1)}


# ---------- FastAPI 应用 ----------
app = FastAPI(title="Mini Agent API", description="零框架手搓 Agent 的产品化外壳")


class ChatIn(BaseModel):
    question: str


@app.post("/chat")
def chat(body: ChatIn):
    return run_agent(body.question)


@app.get("/chat/stream")
def chat_stream(question: str):
    return StreamingResponse(sse_chat(question), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
def index():
    return CHAT_HTML


# ---------- 单文件聊天页：EventSource 收 SSE，无任何前端构建 ----------
CHAT_HTML = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>Mini Agent</title>
<style>
  body{background:#0f172a;color:#e2e8f0;font-family:system-ui;max-width:720px;
       margin:0 auto;padding:24px}
  h1{font-size:20px} h1 span{color:#38bdf8;font-size:12px}
  #log div{margin:8px 0;padding:10px 14px;border-radius:10px;white-space:pre-wrap}
  .user{background:#1e3a5f;margin-left:15%}
  .bot{background:#1e293b}
  .tool{background:#334155;color:#94a3b8;font-size:12px;font-family:monospace}
  form{display:flex;gap:8px;margin-top:16px}
  input{flex:1;padding:10px;border-radius:8px;border:1px solid #334155;
        background:#1e293b;color:#e2e8f0}
  button{padding:10px 18px;border-radius:8px;border:0;background:#38bdf8;
         color:#0f172a;font-weight:bold;cursor:pointer}
</style></head><body>
<h1>Mini Agent <span>· 零框架手搓 · FastAPI + SSE</span></h1>
<div id="log"></div>
<form onsubmit="send();return false">
  <input id="q" placeholder="让 Agent 干点活，比如：在 playground 里写一个 hi.py 并运行它" autofocus>
  <button>发送</button>
</form>
<script>
const log = document.getElementById('log');
function bubble(cls){const d=document.createElement('div');d.className=cls;
  log.appendChild(d);return d;}
let bot;
function send(){
  const q = document.getElementById('q').value.trim();
  if(!q) return;
  document.getElementById('q').value='';
  bubble('user').textContent = q;
  bot = bubble('bot'); bot.textContent = '';
  const es = new EventSource('/chat/stream?question=' + encodeURIComponent(q));
  es.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if(m.type === 'delta'){ bot.textContent += m.text; }
    else if(m.type === 'tool'){
      const t = bubble('tool');
      t.textContent = '🔧 ' + m.name + ' ' + JSON.stringify(m.args) + '\\n→ ' + m.result;
    }
    else if(m.type === 'done'){ es.close(); }
  };
  es.onerror = () => { es.close(); };
}
</script></body></html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
