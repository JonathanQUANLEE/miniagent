import sys
from dotenv import load_dotenv; load_dotenv()  # ★ 新增：读取 .env
import os  # ★ 新增
sys.stdout.reconfigure(encoding='utf-8')
import httpx
from openai import OpenAI

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

def measure(name, messages):
    r = client.chat.completions.create(
        model=MODEL,
        messages=messages
    )
    u = r.usage
    print(f"{name} prompt:{u.prompt_tokens} | 补全:{u.completion_tokens} | 总计:{u.total_tokens}")
    return r





# 第一幕：量术前
notes = read_file("LEARNING_NOTES.md")        # 拿出手术对象：43KB 笔记全文

before = [                                     # 术前档案：原文塞进 user 消息
    {"role": "user", "content": notes + "\n\n你好，看完回一句：已读"}
]

r_before = measure("① 术前（笔记全文）", before)   # 量一次，记录数



# 第二幕：动手术
summary_response = client.chat.completions.create(   # 手术：直发create
    model=MODEL,                            # 不套measure——这次目的是
    messages=[                              #   产出摘要，不是测量
        {"role": "user",
         "content":
            "请把下面这份学习笔记总结成 200 字以内。"     # 手术刀前半：
            "要求：保留全部核心结论，丢弃例子和对话细节。\n\n"   # 刀刃：没这句
                                            #   模型可能缩成三句话重点全丢
            + notes}                        # 手术台上的肉
    ]
)

summary = summary_response.choices[0].message.content
                                            # 从楼里取摘要文字：
                                            # 模型这次用嘴说（没开单），
                                            # 所以货在content里
print("\n【摘要原文】")                       # 人工质检：看它守没守
print(summary)                              #   "200字/留核心"的规矩

# 第三幕：量术后
after = [                                   # 术后档案
    {"role": "user",
     "content": summary + "\n\n请问：这门课的核心任务是什么？"}
]                                           # 43KB原文已换成200字摘要
                                            # 这就是"压缩后上线"的档案

r_after = measure("② 术后（摘要+新问题）", after)   # 量术后重量
# 出报告
print("\n===== 实验结论 =====")
print("术前 prompt tokens：", r_before.usage.prompt_tokens)
                                            # 从接住的response取数字——
                                            # 第3块return r的功劳
print("术后 prompt tokens：", r_after.usage.prompt_tokens)
print("压缩后占术前 ≈ ",
      round(r_after.usage.prompt_tokens
            / r_before.usage.prompt_tokens * 100, 1), "%")
                                            # round(x,1)：保留1位小数
                                            # 百分比比几千tokens直观