#!/bin/bash
# DSB Tournament 启动脚本
# 用法: ./run.sh [端口号]

set -e

PORT="${1:-8000}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[DSB] 启动服务，端口: $PORT"
echo "[DSB] 工作目录: $SCRIPT_DIR"

cd "$SCRIPT_DIR"

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "[DSB] 使用虚拟环境 venv"
    source venv/bin/activate
fi

# 检查依赖
python3 -c "import fastapi" 2>/dev/null || {
    echo "[DSB] 安装依赖..."
    pip install -r requirements.txt
}

echo "[DSB] 服务已启动 -> http://127.0.0.1:$PORT"
exec python3 -m uvicorn src.main:app --host 0.0.0.0 --port "$PORT"
