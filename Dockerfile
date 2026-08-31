# 阶段 1：构建前端
FROM node:22-alpine AS frontend-builder
WORKDIR /build

# 使用国内 npm 镜像源加速（GitHub Actions 国际网络访问 npmjs.org 经常超时）
RUN npm config set registry https://registry.npmmirror.com

COPY frontend/package*.json ./
# 加超时和重试，避免网络问题导致失败
RUN npm install --no-audit --no-fund --fetch-timeout=600000 --fetch-retries=5
COPY frontend/ ./
# 确保 node_modules 里的可执行文件有执行权限（Docker COPY 默认不保留）
RUN chmod +x node_modules/.bin/* || true
RUN npm run build

# 阶段 2：构建后端镜像（集成前端 + FastAPI + Nginx）
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# 系统依赖：WeasyPrint 需要 cairo/pango/gobject
# 使用国内镜像源加速（GitHub Actions 国际网络访问 deb.debian.org 慢）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
        nginx \
        libpango-1.0-0 libpangoft2-1.0-0 \
        libcairo2 libgdk-pixbuf-xlib-2.0-0 \
        libffi-dev shared-mime-info \
        fonts-noto-cjk fonts-wqy-microhei \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 后端依赖
COPY backend/requirements.txt /app/requirements.txt
# 国内源（按需取消注释）
# RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install -r /app/requirements.txt

# 后端代码
COPY backend/ /app/

# 前端构建产物
COPY --from=frontend-builder /build/dist /app/static

# Nginx 配置（删除 Debian 默认 default server，避免冲突）
RUN rm -f /etc/nginx/sites-enabled/default
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# 启动脚本
COPY nginx/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 数据持久化目录
RUN mkdir -p /data/uploads /data/db
VOLUME ["/data"]

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]