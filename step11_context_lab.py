import sys
from dotenv import load_dotenv; load_dotenv()  # ★ 新增：读取 .env
import os  # ★ 新增
sys.stdout.reconfigure(encoding='utf-8')
import httpx
from Openai import OpenAI

def read_file(path):
    f = open(path, 'r', encoding='utf-8')
    content = f.read()
    f.close()
    return content

http_client = httpx.Client(proxy="http://127.0.0.1:10808")
client = OpenAI(
    api_key=os.environ.get("API_KEY"),  # ★ 安全改造：Key 改从 .env 读取
    base_url="https://openrouter.ai/api/v1",
    http_client=http_client
)

MODEL = "inclusionai/ling-3.0-flash-sante:free"


def measure(name,messages):  #测量员：发一次，报一次账单
    r = client.chat.completions.create(
        model=MODEL,
        messages=messages)
    u = r.usage             #账单就藏在usage字段里
    print(f"{name} prompt :{u.prompt_tokens} tokens| 补全:{u.completion_tokens} | 总计:{u.total_tokens}")

    #---场景A ：空对话 （最小的档案） ————————
measure("A空对话", [
        {"role": "user", "content": "你好"}
])

#—————场景B带一个step文件，1.5 KB。
step1 = read_file("step1_hello_llm.py")
measure("B 带step1",[
    {"role":"user", "content": step1 + "\n\n 你好，看完回一句： 已读"}
])

#场景C带整个学习笔记，43 KB。
notes = read_file("LEARNING_NOTES.md")
measure("C 带笔记全文",[
    {"role":"user","content": notes + "\n\n 你好，看完会一句： 已读！！"}
])