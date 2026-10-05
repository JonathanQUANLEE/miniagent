# 1.安装依赖
import os   
from dotenv import load_dotenv; load_dotenv()  # ★ 新增：读取 .env
import httpx
from openai import OpenAI  
import sys
sys.stdout.reconfigure(encoding='utf-8')
# 2.配置代理
http_client = httpx.Client(proxy="http://127.0.0.1:10808")
#3. 初始化客户端
client = OpenAI(
    api_key=os.environ.get("API_KEY"),  # ★ 安全改造：Key 改从 .env 读取
    base_url="https://openrouter.ai/api/v1",
    http_client=http_client
)

# 4.组装messages列表，给一个system角色定设定，给一个user提问
messages = [
    {"role":"system","content":"你是一个有帮助的助手"},
    {"role":"user","content":"你好，帮我翻译一下embedding这个词，翻译成中文"},
  
    
    
]

# 5. 调用chat.completions.create接口，传入messages列表，获取返回结果
response = client.chat.completions.create(
    model="inclusionai/ling-3.0-flash-fin:free",
    messages=messages
   
)

# 6.把模型回复打印出来。
# 首先呢，我只是会一个print()  然后至于里面括号里面怎么打印，我不会写。
reply1 = response.choices[0].message.content
print("\n\n模型回复：\n", reply1)
messages.append({"role":"assistant","content":reply1})

messages.append({"role":"user","content":"请用一句话举例说明它在中文里的用法"})
# 7第二次调用
response2 = client.chat.completions.create(
    model="inclusionai/ling-3.0-flash-fin:free",
    messages=messages
)
reply2 = response2.choices[0].message.content
print("\n\n\n\n模型回复：\n", reply2)