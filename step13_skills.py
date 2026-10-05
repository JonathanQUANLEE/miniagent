import sys
from dotenv import load_dotenv; load_dotenv()  # ★ 新增：读取 .env
import os  # ★ 新增
sys.stdout.reconfigure(encoding='utf-8')
import json
import httpx
from openai import OpenAI
import subprocess



def add(a, b):
    return a + b
def subtract(a, b): 
    return a - b

def read_file(path):
    f = open(path, 'r', encoding='utf-8')
    content = f.read()
    f.close()
    return content

def write_file(path, content):
    f = open(path, 'w', encoding ='utf-8')
    f.write(content)
    f.close()
    return f"已写入{len(content)}个字符到{path}"
def run_command(command):#第五只手终端
    r = subprocess.run(command,shell=True,# 交给系统终端执行
                        capture_output = True ,# 是否捕获输出
                           text=True ,# 以文本形式返回处理
                           timeout=30, # 30 秒干不完就掐（防卡死）
                       
                       )
    return f"退出码:{r.returncode}\n标准输出:{r.stdout}\n标准错误:{r.stderr}"
    
# 第六只手
def append_file(path,content):  #第六只手：往本子上末尾记账
    f = open(path, 'a', encoding ='utf-8')   #"a"=append模式，往末尾写入 不清空
    f.write(content + "\n")   #写完补个换行，下次接着记

    f.close()   
    return f"已在{path}末尾追加{len(content)}个字符"





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
    },
    {
        "type":"function",                      # 固定写法，同前
        "function": {
            "name":"read_file",                  # ★ 手 3 的名字
            "description":"读取指定路径的文件内容,返回文件内容",  # ★ 你自己写的那句，直接复用
            "parameters": {
                "type":"object",
                "properties": {
                    "path": {"type":"string", "description":"要读取的文件路径,step1_hello_llm.py"}
                },
                "required":["path"]
            }
        }
    },
    
    {
        "type":"function",                      # 固定写法，同前
        "function": {
            "name":"write_file",                  # ★ 手 3 的名字
            "description":"把指定内容写入指定路径的文本文件（会覆盖同名文件）",  # ★ 你自己写的那句，直接复用
            "parameters": {
                "type":"object",
                "properties":{
                    "path":{"type":"string","description":"要写入的文件路径,例如diary.txt"},
                    "content":{"type":"string","description":"要写入的内容"}
                },
                "required":["path","content"]


            }
        }
    },
    #菜单加第五块
    {
        "type":"function",                      # 固定写法，同前
        "function": {
            "name":"run_command",                  # ★ 手 3 的名字
            "description":"在当前目录执行一条 Windows 终端命令并返回退出码与输出。只限安全的只读命令，如 dir、python --version。",  # ★ 你自己写的那句，直接复用
            "parameters": {
                "type":"object",
                "properties":{
                    "command":{"type":"string","description":"要执行的命令,例如 dir"}
                },
                "required":["command"]


            }
        }
    },
    # 第六只手
    {
        "type":"function",                      # 固定写法，同前
        "function": {
            "name":"append_file",                  # ★ 手 3 的名字
            "description":"往指定路径的文本文件末尾追加内容（不会清空原文件）",  # ★ 你自己写的那句，直接复用
            "parameters": {
                "type":"object",
                "properties":{
                    "path":{"type":"string","description":"要追加的文件路径,例如memory.txt"},
                    "content":{"type":"string","description":"要追加的内容"}
                },
                "required":["path","content"]


            }
        }

    }
]


messages = [
    {"role": "user", "content": "先读取 skills/code-review.md 这个技能文件，记住里面的流程和报告格式。然后严格按该技能的四步流程，审查 playground/review_target.py，输出完整审查报告。"}
]
step = 0
while True:
    step += 1
    if step > 8:  # 设置最大对话轮数为8，# 原来是 5 —— 修 bug 要多转几圈，给足圈数
        print("已达到最大对话轮数，程序结束。")
        break
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
            print("工单", tool_call.function.name, tool_call.function.arguments[:120])
            if tool_call.function.name == "add":
                args = json.loads(tool_call.function.arguments)
                result = add(args["a"], args["b"])
           
            elif tool_call.function.name == "subtract":
                args = json.loads(tool_call.function.arguments)
                result = subtract(args["a"], args["b"])
            
            elif tool_call.function.name == "read_file":
                args = json.loads(tool_call.function.arguments)
                result = read_file(args["path"])
            
            elif tool_call.function.name == "write_file":
                args = json.loads(tool_call.function.arguments)
                result = write_file(args["path"], args["content"])
           
            #分发加第五支
            elif tool_call.function.name == "run_command":
                args = json.loads(tool_call.function.arguments)
                result = run_command(args["command"])
            
            #分发加第六支
            elif tool_call.function.name =="append_file":
                args = json.loads(tool_call.function.arguments)
                result = append_file(args["path"], args["content"])


            
            messages.append({"role":"tool",
                             "tool_call_id":tool_call.id,
                             "content":str(result)})
            
        continue
    else:
        print("答案是：\n", response.choices[0].message.content)
        break



























