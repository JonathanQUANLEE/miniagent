import sys
from dotenv import load_dotenv; load_dotenv()  # ★ 新增：读取 .env
import os  # ★ 新增
sys.stdout.reconfigure(encoding='utf-8')
import json
import httpx
from openai import OpenAI

def add(a, b):
    return a + b
def subtract(a, b): 
    return a - b
# 2.配置代理
http_client = httpx.Client(proxy="http://127.0.0.1:10808")
#3. 初始化客户端
client = OpenAI(
    api_key=os.environ.get("API_KEY"),  # ★ 安全改造：Key 改从 .env 读取
    base_url="https://openrouter.ai/api/v1",
    http_client=http_client
)
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
    }
]

messages=[
    {"role":"user","content":"帮我算一下 12345 -67890 + 100  是多少？"}
]
step = 0
while True:
    step += 1
    print(f"\n\n\n第{step}轮对话：\n")
    response = client.chat.completions.create(
        model="inclusionai/ling-3.0-flash-sante:free",   
        messages=messages,
        tools=tools
    )
    # 把模型这条信息（含工单、记录在档案里）
    messages.append(response.choices[0].message)
    if response.choices[0].finish_reason == "tool_calls":
        for tool_call in response.choices[0].message.tool_calls:
            if tool_call.function.name == "add":
                args = json.loads(tool_call.function.arguments)
                result = add(args["a"], args["b"])
            elif tool_call.function.name == "subtract":
                args = json.loads(tool_call.function.arguments)
                result = subtract(args["a"], args["b"])
            messages.append({"role":"tool",
                             "tool_call_id":tool_call.id,
                             "content":str(result)})
        continue
    else:
        print("答案是：\n", response.choices[0].message.content)
        break

