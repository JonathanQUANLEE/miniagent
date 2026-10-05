import sys
from dotenv import load_dotenv; load_dotenv()  # ★ 新增：读取 .env
import os  # ★ 新增
sys.stdout.reconfigure(encoding='utf-8')
import time                                 # 秒表
import threading                            # ★ 新：分身术
import httpx
from openai import OpenAI

http_client = httpx.Client(proxy="http://127.0.0.1:10808")
client = OpenAI(
    api_key=os.environ.get("API_KEY"),  # ★ 安全改造：Key 改从 .env 读取
    base_url="https://openrouter.ai/api/v1",
    http_client=http_client
)

MODEL = "inclusionai/ling-3.0-flash-sante:free"

def run_subagent(task):                     # 实习生（同前）
    messages = [{"role": "user", "content": task}]
    r = client.chat.completions.create(model=MODEL, messages=messages)
    return r.choices[0].message.content

TASKS = [
    "用一句话说明：什么是 Tool Calling？",
    "用一句话说明：什么是 Context Window？",
    "用一句话说明：为什么 Agent 需要 max_steps 保险丝？",
]

# ── 串行版：排队打饭 ──
t0 = time.time()                            # 秒表启动
r1 = run_subagent(TASKS[0])
r2 = run_subagent(TASKS[1])
r3 = run_subagent(TASKS[2])
print("串行总耗时：", round(time.time() - t0, 1), "秒")

# ── 并行版：三个窗口同时开 ──
results = {}                                # 结果登记簿：编号 → 报告

def worker(n, task):                        # 分身的任务：干完把报告存登记簿
    results[n] = run_subagent(task)

t0 = time.time()                            # 秒表再启动
threads = []
for i, task in enumerate(TASKS, 1):         # 雇三个分身
    th = threading.Thread(target=worker, args=(i, task))
    threads.append(th)
    th.start()                              # 分身出发（主程序不等待！）

for th in threads:                          # 主程序在终点线等全部分身
    th.join()

print("并行总耗时：", round(time.time() - t0, 1), "秒")
for n in sorted(results):                   # 按编号收报告
    print(f"报告{n}：", results[n][:60])