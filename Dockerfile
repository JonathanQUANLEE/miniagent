FROM python:3.12-slim

WORKDIR /app

# 先装依赖（利用 Docker 层缓存：代码改动不用重装依赖）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷代码
COPY step*.py mini_mcp_server.py ./
COPY skills/ ./skills/
COPY docs/ ./docs/

# API_KEY / MODEL / HTTP_PROXY 运行时注入（docker run -e），绝不打进镜像
EXPOSE 8000
CMD ["uvicorn", "step26_api:app", "--host", "0.0.0.0", "--port", "8000"]
