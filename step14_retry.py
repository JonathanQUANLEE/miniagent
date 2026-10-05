import sys
from dotenv import load_dotenv; load_dotenv()  # ★ 新增：读取 .env
import os  # ★ 新增
sys.stdout.reconfigure(encoding='utf-8')
import time                                 # ★ 新：时间模块（sleep 用）
import httpx
from openai import OpenAI

http_client = httpx.Client(proxy="http://127.0.0.1:10808")
client = OpenAI(
    api_key=os.environ.get("API_KEY"),  # ★ 安全改造：Key 改从 .env 读取
    base_url="https://openrouter.ai/api/v1",
    http_client=http_client
)

MODEL = "inclusionai/ling-3.0-flash-sante:free"    # 把坏名字改回这个    # ★ 故意写错：制造必然失败
                                            #（实验后改回 sante:free）

def ask_model(messages,model=MODEL,max_retries=3): # 带保险的请求函数：
                                            # max_retries = 最多试 3 次
    for attempt in range(1,max_retries + 1):
        #attempt 会是1，2，3
        print(f"--- 第{attempt}次尝试 ----")
        try: #试着发货
            r = client.chat.completions.create(
                model =model,
                messages=messages
            )
            return r
        # 成功：直接把包裹交回去
                                            #（成功就不需要重试了）
        except Exception as e :# 炸了 → 接住，程序不崩
            print("失败原因：",e)
            if attempt < max_retries:# 还有机会 → 睡一觉再试
                wait = 2 ** attempt  # 幂运算：2 → 4 → 8
                # 间隔越拉越长 = 退避

                print(f"等待{wait}秒后重试...")
                time.sleep(wait)     #原地睡觉
    return None                      #三次全炸：交回空包裹
                                    #None = "失败，没有结果"
#=====主程序====
result = ask_model([{"role":"user","content":"你好"}])
if result is None:                          # 空包裹 = 全失败
    print("【上报用户】模型当前不可用，请稍后再试或更换模型。")
else:                                       # 拿到真包裹
    print("成功：", result.choices[0].message.content)