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

def run_subagent(task):                      # 实习生：插槽 task 等一张任务单
    messages = [                             # ★ 子 Agent 自己的小档案
        {"role": "user", "content": task}    #     只装他的任务，和主档案零共享
    ]
    r = client.chat.completions.create(      # 他自己发货（用自己的档案）
        model=MODEL,
        messages=messages
    )
    return r.choices[0].message.content      # 只交最终结果：
                                             # 草稿、失败、过程——全留在小隔间


report_A = run_subagent("用一句话说明：什么是 Tool Calling？")
report_B = run_subagent("用一句话说明：什么是 Context Window？")

print("研究员A的报告：", report_A)
print("研究员B的报告：", report_B)

# 经理合并
merge = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "user", "content":
            f"你是课程主编。研究员A说：{report_A}\n研究员B说：{report_B}\n"
            "请把两份研究合并成一段 100 字以内的课程笔记。"}
    ]
)
print("\n=== 经理的合并笔记 ===")
print(merge.choices[0].message.content)

