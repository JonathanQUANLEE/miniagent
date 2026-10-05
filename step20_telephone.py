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

def run_subagent(task):                      # 实习生（复用，同 step18/19）
    messages = [
        {"role": "user", "content": task}
    ]
    r = client.chat.completions.create(model=MODEL, messages=messages)
    return r.choices[0].message.content

original = ("Agent = LLM + Tools + Loop + State + Environment。"
            "模型负责思考决策，Python 负责动手执行，"
            "循环负责把结果喂回去，State 负责记住现在在哪。")

t1 = run_subagent(f"用一句话复述下面这段话：{original}")
t2 = run_subagent(f"用一句话复述下面这段话：{t1}")
t3 = run_subagent(f"用一句话复述下面这段话：{t2}")

print("原文　　：", original)
print("传 1 手：", t1)
print("传 2 手：", t2)
print("传 3 手：", t3)