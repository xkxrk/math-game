# ===== 阶段1：构建前端 =====
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ===== 阶段2：后端运行 =====
FROM python:3.11-slim
WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 后端代码
COPY backend/ /app/backend/

# 前端构建产物
COPY --from=frontend-build /build/dist /app/frontend/dist

# 数据目录
RUN mkdir -p /app/data
ENV DB_PATH=/app/data/dlt.db
ENV TZ=Asia/Shanghai

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8888/api/health || exit 1

WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8888"]
