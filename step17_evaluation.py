import sys
from dotenv import load_dotenv; load_dotenv()  # ★ 新增：读取 .env
import os  # ★ 新增
sys.stdout.reconfigure(encoding='utf-8')
import json
import httpx
from openai import OpenAI
import subprocess                         # ★ 补：run_command 手的司机
import time

def log(event):
    stamp = time.strftime("%H:%M:%S")
    line = f"[{stamp}] {event}"
    print(line)
    with open("logs/trace.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")

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
    return f"已在{path}末尾追加{len(content)}个字符"
def run_command(command):
    r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
    return f"退出码:{r.returncode}\n标准输出:{r.stdout}\n标准错误:{r.stderr}"

http_client = httpx.Client(proxy="http://127.0.0.1:10808")
client = OpenAI(
    api_key=os.environ.get("API_KEY"),  # ★ 安全改造：Key 改从 .env 读取
    base_url="https://openrouter.ai/api/v1",
    http_client=http_client
)

MODEL = "inclusionai/ling-3.0-flash-sante:free"

tools = [
    {
        "type": "function",
        "function":
        {
            "name":"add",
            "description":"计算两个数字的和",
            "parameters": 
            {
                "type":"object",
                "properties": {
                    "a": {
                        "type":"number",
                        "description":"第一个数字"
                    },
                    "b": {
                        "type":"number",
                        "description":"第二个数字"
                    }

                },
                # 规定这两个参数必须填写
                "required":["a","b"]
            }
        }
     },


    {
        "type": "function",                      # 固定写法，同前
        "function": {
            "name": "subtract",                  # ★ 手 2 的名字
            "description": "计算两个数字的差（用第一个数减第二个数）",  # ★ 你自己写的那句，直接复用
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "被减数（减号前面的数）"},  # ★ 描述越明白，模型摆数越准
                    "b": {"type": "number", "description": "减数（减号后面的数）"}
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type":"function",                      # 固定写法，同前
        "function": {
            "name":"read_file",                  # ★ 手 3 的名字
            "description":"读取指定路径的文件内容,返回文件内容",  # ★ 你自己写的那句，直接复用
            "parameters": {
                "type":"object",
                "properties": {
                    "path": {"type":"string", "description":"要读取的文件路径,step1_hello_llm.py"}
                },
                "required":["path"]
            }
        }
    },
    
    {
        "type":"function",                      # 固定写法，同前
        "function": {
            "name":"write_file",                  # ★ 手 3 的名字
            "description":"把指定内容写入指定路径的文本文件（会覆盖同名文件）",  # ★ 你自己写的那句，直接复用
            "parameters": {
                "type":"object",
                "properties":{
                    "path":{"type":"string","description":"要写入的文件路径,例如diary.txt"},
                    "content":{"type":"string","description":"要写入的内容"}
                },
                "required":["path","content"]


            }
        }
    },
    #菜单加第五块
    {
        "type":"function",                      # 固定写法，同前
        "function": {
            "name":"run_command",                  # ★ 手 3 的名字
            "description":"在当前目录执行一条 Windows 终端命令并返回退出码与输出。只限安全的只读命令，如 dir、python --version。",  # ★ 你自己写的那句，直接复用
            "parameters": {
                "type":"object",
                "properties":{
                    "command":{"type":"string","description":"要执行的命令,例如 dir"}
                },
                "required":["command"]


            }
        }
    }
]


TASKS = [                                   # 固定考卷：永远不变的 3 道题
    {"name": "算术",                        # 题目名（报告里显示用）
     "q": "帮我算一下 12345 + 67890 是多少？",
     "check": "80235"},                     # 判定关键词：答案里必须有它
    {"name": "写文件",
     "q": "在 playground/eval_out.txt 里写入：评测通过",
     "check_file": "playground/eval_out.txt",   # 判定文件：跑完后检查它
     "check": "评测通过"},                  # 文件里必须有这四个字
    {"name": "记忆",
     "q": "把'第 1 次评测完成'追加到 memory.txt",
     "check_file": "memory.txt",
     "check": "第 1 次评测完成"},
]

def run_agent(question):                     # Agent 从此是一个可调用的函数
    messages = [                             # ★ 档案从参数来——每次考试全新开局
        {"role": "user", "content": question}
    ]
    for attempt in range(1, 9):              # 保险丝 8 圈（for 版护栏）
        r = client.chat.completions.create(
            model=MODEL, messages=messages, tools=tools
        )
        messages.append(r.choices[0].message)
        if r.choices[0].finish_reason == "tool_calls":
            for tool_call in r.choices[0].message.tool_calls:
                log(f"评测工单 {tool_call.function.name}")     # 黑匣子随行
                args = json.loads(tool_call.function.arguments)
                if tool_call.function.name == "add":              # ★ 补：算术支
                    result = add(args["a"], args["b"])
                elif tool_call.function.name == "subtract":       # ★ 补：减法支
                    result = subtract(args["a"], args["b"])
                elif tool_call.function.name == "run_command":    # ★ 补：终端支
                    result = run_command(args["command"])
                elif tool_call.function.name == "read_file":
                    result = read_file(args["path"])
                elif tool_call.function.name == "write_file":
                    result = write_file(args["path"], args["content"])
                elif tool_call.function.name == "append_file":
                    result = append_file(args["path"], args["content"])
                messages.append({"role": "tool",
                                 "tool_call_id": tool_call.id,
                                 "content": str(result)})
            continue
        else:
            return r.choices[0].message.content   # ★ 最终答案交回去
    return None                              # 8 圈没完 = 失败

# 第 3 块：阅卷 + 报告

passed = 0                                   # 及格计数器
for t in TASKS:                              # 挨个考
    print(f"\n===== 考核：{t['name']} =====")
    answer = run_agent(t["q"])               # 考！
    answer_text = str(answer)                # 统一变文字条
    if t["check"] in answer_text:            # ★ 验收点在答案里吗
        print(f"PASS：找到 '{t['check']}'")
        passed += 1
    elif "check_file" in t:                  # 答案里没有 → 查文件
        f = open(t["check_file"], encoding="utf-8")
        content = f.read()
        f.close()
        if t["check"] in content:
            print(f"PASS：文件里找到 '{t['check']}'")
            passed += 1
        else:
            print("FAIL：文件里也没有")
    else:
        print("FAIL：验收点缺失")

print(f"\n===== 评测报告 =====")
print(f"通过 {passed} / {len(TASKS)}，成功率 {round(passed/len(TASKS)*100)}%")