#!/bin/bash

# ============================================
#  流程文件智能评审系统 - 一键启动脚本
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# 修复双击 .command 文件时 PATH 不完整的问题
# 添加 node/npm 安装路径
export PATH="$HOME/.workbuddy/binaries/node/versions/20.18.0/bin:$PATH"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止所有服务...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        wait $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        wait $FRONTEND_PID 2>/dev/null
    fi
    echo -e "${GREEN}所有服务已停止。${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════╗"
echo "║     流程文件智能评审系统 - 启动中...         ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. 启动后端
echo -e "${YELLOW}[1/2] 启动后端服务 (FastAPI)...${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo -e "${GREEN}  后端服务已启动 (PID: $BACKEND_PID) → http://localhost:8000${NC}"

# 等待后端启动
sleep 2

# 验证数据库路径
PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
DB_PATH=$("$PYTHON_BIN" -c "
import sys; sys.path.insert(0, '$BACKEND_DIR')
from app.core.database import get_db_path
print(get_db_path())
" 2>/dev/null)
echo -e "  数据库路径: ${CYAN}${DB_PATH:-未知}${NC}"

# 检查数据库文件是否存在
if [ -f "$DB_PATH" ] && [ -s "$DB_PATH" ]; then
    TASK_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM review_tasks;" 2>/dev/null)
    echo -e "  现有任务数: ${TASK_COUNT:-0}"
elif [ -f "$DB_PATH" ]; then
    echo -e "  ${YELLOW}数据库文件为空，首次启动${NC}"
fi

# 2. 启动前端
echo -e "${YELLOW}[2/2] 启动前端服务 (React + Vite)...${NC}"
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}  前端服务已启动 (PID: $FRONTEND_PID) → http://localhost:5173${NC}"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  🚀 所有服务已启动成功！                      ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  前端页面: ${CYAN}http://localhost:5173${GREEN}              ║${NC}"
echo -e "${GREEN}║  后端 API: ${CYAN}http://localhost:8000${GREEN}               ║${NC}"
echo -e "${GREEN}║  API 文档: ${CYAN}http://localhost:8000/docs${GREEN}           ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  按 Ctrl+C 停止所有服务                       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"

# 等待任意子进程退出
wait
