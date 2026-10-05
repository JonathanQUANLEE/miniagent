import sys
from dotenv import load_dotenv; load_dotenv()  # ★ 新增：读取 .env
import os  # ★ 新增
sys.stdout.reconfigure(encoding='utf-8')
import json
import httpx
import subprocess
from openai import OpenAI

# ═══ 六只手 def（从 step16 复制）═══

def add(a, b):
    return a + b
def subtract(a, b):
    return a - b
def read_file(path):
    f = open(path, 'r', encoding='utf-8')
    content = f.read()
    f.close()
    return content

def write_file(path, content):
    f = open(path, 'w', encoding='utf-8')
    f.write(content)
    f.close()
    return f"已写入{len(content)}个字符到{path}"

def append_file(path, content):
    f = open(path, 'a', encoding='utf-8')
    f.write(content + "\n")
    f.close()
    return f"已追加{len(content)}个字符到{path}"

http_client = httpx.Client(proxy="http://127.0.0.1:10808")
client = OpenAI(
    api_key=os.environ.get("API_KEY"),  # ★ 安全改造：Key 改从 .env 读取
    base_url="https://openrouter.ai/api/v1",
    http_client=http_client
)

MODEL = "inclusionai/ling-3.0-flash-sante:free"


# ═══ 新增 1：白名单集合 ═══
SAFE_COMMANDS = {"dir", "python", "echo"}    # 集合 = 无序不重复，in 检查最快

# ═══ 新增 2：三模式开关 ═══
PERMISSION_MODE = "SAFE"                     # SAFE / ASK / AUTO

# ═══ 新增 3：保安函数 ═══
def check_permission(command):
    first_word = command.split()[0]          # 取命令的第一个词
                                             # "dir /w" → "dir"
    if PERMISSION_MODE == "SAFE":            # 严格模式：白名单外全拦
        return first_word in SAFE_COMMANDS
    return True                              # 其他模式先放（进阶再细做）

# ═══ run_command 改造：先过保安 ═══
def run_command(command):
    if not check_permission(command):        # 不在白名单？
        return f"⛔ 权限拒绝：'{command}' 不是安全命令"
                                             # 返回拒绝信息（不是崩）
    r = subprocess.run(command, shell=True,
                       capture_output=True, text=True, timeout=30)
    return f"退出码:{r.returncode}\n标准输出:{r.stdout}\n标准错误:{r.stderr}"
# ═══ 本章核心：注册表 ═══

TOOL_REGISTRY = {}                            # 空注册表出生

TOOL_REGISTRY["add"] = add                    # 函数当值存进去（不加括号！）
TOOL_REGISTRY["subtract"] = subtract
TOOL_REGISTRY["read_file"] = read_file
TOOL_REGISTRY["write_file"] = write_file
TOOL_REGISTRY["append_file"] = append_file
TOOL_REGISTRY["run_command"] = run_command      # ★ 补注册：权限版终端手

# ═══ 按名分发（消灭 if/elif 长链）═══

def dispatch(name, args):
    handler = TOOL_REGISTRY.get(name)         # 按名字查：查到 = 函数，查不到 = None
    if handler is None:                       # 未知工具 → 优雅拒绝，不崩
        return f"未知工具：{name}"
    return handler(**args)                    # ** 解包：字典拆成关键字参数
# ═══ 直测四连（零额度，不调模型）═══

print(dispatch("add", {"a": 12, "b": 34}))          # → 46
print(dispatch("subtract", {"a": 10, "b": 3}))      # → 7
print(dispatch("read_file", {"path": "AGENT.md"}))  # → 文件全文
print(dispatch("不存在", {}))                        # → 未知工具：不存在
# ═══ 权限直测（SAFE 模式）═══
print(dispatch("run_command", {"command": "echo hello"}))     # echo 在白名单 → 放行执行
print(dispatch("run_command", {"command": "del diary.txt"}))  # del 不在白名单 → ⛔ 拒绝