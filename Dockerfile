# 城市空气质量分析系统 —— 后端 / 数据处理通用镜像
FROM python:3.12-slim

WORKDIR /app

# 报告脚本需要中文字体渲染 PNG：安装 Noto CJK 并清理 apt 缓存
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码（.dockerignore 已排除数据、虚拟环境与缓存）
COPY . .

EXPOSE 8000

# 默认作为 Web 服务启动；数据处理服务在 compose 中覆盖为 run_pipeline.py
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
