import sys
from dotenv import load_dotenv; load_dotenv()  # ★ 新增：读取 .env
import os  # ★ 新增
sys.stdout.reconfigure(encoding='utf-8')
import httpx
from openai import OpenAI

http_client = httpx.Client(proxy="http://127.0.0.1:10808")
client = OpenAI(
    api_key=os.environ.get("API_KEY"),  # ★ 安全改造：Key 改从 .env 读取
    base_url="https://openrouter.ai/api/v1",
    http_client=http_client
)

MODEL = "inclusionai/ling-3.0-flash-sante:free"

def run_subagent(task):                      # 实习生（同 step18，原样复用）
    messages = [
        {"role": "user", "content": task}
    ]
    r = client.chat.completions.create(
        model=MODEL,
        messages=messages
    )
    return r.choices[0].message.content

# Supervisor 四拍

SUBTASKS = [                                 # 拍1 拆：经理把大活拆成清单
    "写一句课程开场白（主题：Agent 会自己修 bug）",
    "写一句课程要点（主题：Agent Loop 的红绿灯）",
    "写一句课程收尾（主题：下一步学多 Agent）",
]

reports = []                                 # 报告收集篮（空列表等报告）

n = 0
for subtask in SUBTASKS:                     # 拍2 派：挨个派
    n += 1
    print(f"经理派活 {n}/{len(SUBTASKS)}：{subtask}")
                                             # len(清单) = 数出共几件活
    report = run_subagent(subtask)           # 实习生干活
    reports.append(report)                   # 报告进收集篮
    print(f"收货：{report[:50]}")             # 切片防刷屏（老规矩）

merged = ""                                  # 拍3 收齐后拼总素材
for r in reports:
    merged = merged + r + "\n"               # 每段报告一行，垒起来

final = client.chat.completions.create(      # 拍4 合：交主编终审合并
    model=MODEL,
    messages=[
        {"role": "user", "content":
            f"你是课程主编。以下是几段研究素材：\n{merged}\n"
            "请合并成一段 150 字以内的完整课程介绍。"}
    ]
)
print("\n=== 经理的最终交付 ===")
print(final.choices[0].message.content)