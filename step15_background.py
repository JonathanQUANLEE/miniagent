import sys
from dotenv import load_dotenv; load_dotenv()  # ★ 新增：读取 .env
sys.stdout.reconfigure(encoding='utf-8')
import subprocess                        # 还记得吗：司机
import time                              # 睡觉用的
import os                                # 新面孔：文件系统工具


p = subprocess.Popen(
    "python playground/slow_task.py",  # 慢任务道具
    shell=True
)
print("后台任务已启动，编号：", p.pid)     # pid = 后台进程的身份证号

# ── 主程序干别的（不等它！）──
print("等待期间，主程序先干点别的：数一下根目录有几个文件…")
import os
print("根目录条目数：", len(os.listdir(".")))   # os.listdir = 列出目录

# ── 轮询：每秒看一眼洗衣机转完没 ──
import os.path                           # os 的"路径检查"零件
for i in range(10):                      # 最多看 10 次
    if os.path.exists("playground/result.txt"):
        print("结果文件出现了！后台任务完成 ✅")
        break                            # 出现就别再看了
    print(f"还没好…（第 {i+1} 次查看）")
    time.sleep(1)

# ── 取衣服 ──
print("\n===== 读取后台任务的结果 =====")
print(open("playground/result.txt", encoding="utf-8").read())