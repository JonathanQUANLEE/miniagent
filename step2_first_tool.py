import sys
from dotenv import load_dotenv; load_dotenv()  # ★ 新增：读取 .env
import os  # ★ 新增
sys.stdout.reconfigure(encoding='utf-8')
import httpx
from openai import OpenAI
import json

def add(a, b):
    return a + b

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
     }
]
messages = [
    {"role": "user", "content": "帮我算一下 12345 加上 67890 是多少？"}
]

response = client.chat.completions.create(
    model="inclusionai/ling-3.0-flash-sante:free",
    messages=messages,
    tools=tools
)

print("\n\n模型回复：\n", response.choices[0].message.content  ,
      "\n\n模型回复2：\n",response.choices[0].finish_reason,
      "\n\n模型回复3：\n",response.choices[0].message.tool_calls,
      "\n\n模型回复4：\n",response.choices[0].message
      )
messages.append(response.choices[0].message)

tool_call = response.choices[0].message.tool_calls[0]
args = json.loads(tool_call.function.arguments)
result = add(args["a"], args["b"])
messages.append({
       "role": "tool",  
       "tool_call_id": tool_call.id,
       "content": str(result)
   })
response2 = client.chat.completions.create(
    model="inclusionai/ling-3.0-flash-sante:free",
    messages=messages,
    tools=tools
)
print("答案是：",response2.choices[0].message.content)
