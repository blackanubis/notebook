#!/bin/bash
set -e

echo "[entrypoint] 启动错题本服务..."

# 数据目录
mkdir -p /data/db /data/uploads
chmod -R 755 /data

# 初始化 SQLite 数据库（首次启动会建表）
if [ ! -f /data/db/app.db ]; then
    echo "[entrypoint] 首次启动，初始化数据库..."
    cd /app
    python -c "from app.database import init_db; init_db()"
fi

# 启动 Nginx（前台）
echo "[entrypoint] 启动 Nginx..."
nginx -g "daemon off;" &

# 启动 FastAPI（前台）
echo "[entrypoint] 启动 FastAPI (uvicorn)..."
cd /app
exec uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1 --log-level info