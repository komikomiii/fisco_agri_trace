#!/bin/bash

# 农产品溯源平台一键启动脚本
# 使用方法: ./start.sh

set -e

PROJECT_DIR="/home/pdm/DEV/komi-project"
FISCO_NODES_DIR="/home/pdm/fisco/nodes/127.0.0.1"

echo "=========================================="
echo "   农产品溯源平台 - 一键启动脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 启动 MySQL
echo -e "${YELLOW}[1/4] 检查 MySQL...${NC}"
if pgrep mysqld > /dev/null; then
    echo -e "${GREEN}  ✓ MySQL 已在运行${NC}"
else
    echo "  清理残留进程..."
    echo "123123" | sudo -S pkill -9 mysqld 2>/dev/null || true
    echo "123123" | sudo -S rm -f /var/run/mysqld/mysqld.pid 2>/dev/null || true
    sleep 1
    echo "  启动 MySQL..."
    echo "123123" | sudo -S service mysql start 2>/dev/null &
    sleep 5
    if pgrep mysqld > /dev/null; then
        echo -e "${GREEN}  ✓ MySQL 启动成功${NC}"
    else
        echo -e "${YELLOW}  ⚠ MySQL 启动中或失败，继续其他服务...${NC}"
    fi
fi

# 2. 启动 FISCO BCOS 区块链节点
echo ""
echo -e "${YELLOW}[2/4] 启动 FISCO BCOS 区块链节点...${NC}"
FISCO_COUNT=$(ps aux | grep fisco-bcos | grep -v grep | wc -l)
if [ "$FISCO_COUNT" -eq 4 ]; then
    echo -e "${GREEN}  ✓ 4个区块链节点已在运行${NC}"
else
    cd "$FISCO_NODES_DIR"
    bash stop_all.sh 2>/dev/null || true
    sleep 1
    bash start_all.sh
    sleep 2
    FISCO_COUNT=$(ps aux | grep fisco-bcos | grep -v grep | wc -l)
    echo -e "${GREEN}  ✓ 启动了 $FISCO_COUNT 个区块链节点${NC}"
fi

# 3. 启动后端 FastAPI
echo ""
echo -e "${YELLOW}[3/4] 启动后端 FastAPI 服务...${NC}"
if pgrep -f "uvicorn main:app" > /dev/null; then
    echo -e "${GREEN}  ✓ 后端服务已在运行${NC}"
else
    cd "$PROJECT_DIR/backend"
    source venv/bin/activate
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
    sleep 3
    if pgrep -f "uvicorn main:app" > /dev/null; then
        echo -e "${GREEN}  ✓ 后端服务启动成功 (http://localhost:8000)${NC}"
    else
        echo -e "${RED}  ✗ 后端启动失败，查看日志: /tmp/backend.log${NC}"
    fi
fi

# 4. 启动前端 Vue
echo ""
echo -e "${YELLOW}[4/4] 启动前端 Vue 服务...${NC}"
if pgrep -f "vite" > /dev/null; then
    echo -e "${GREEN}  ✓ 前端服务已在运行${NC}"
else
    cd "$PROJECT_DIR/frontend"
    nohup npm run dev > /tmp/frontend.log 2>&1 &
    sleep 3
    if pgrep -f "vite" > /dev/null; then
        echo -e "${GREEN}  ✓ 前端服务启动成功 (http://localhost:5173)${NC}"
    else
        echo -e "${RED}  ✗ 前端启动失败，查看日志: /tmp/frontend.log${NC}"
    fi
fi

# 状态汇总
echo ""
echo "=========================================="
echo "   启动完成 - 服务状态"
echo "=========================================="
echo ""
echo "  前端地址:    http://localhost:5173"
echo "  后端地址:    http://localhost:8000"
echo "  API文档:     http://localhost:8000/docs"
echo "  区块链RPC:   http://127.0.0.1:20200"
echo ""
echo "  日志文件:"
echo "    后端: /tmp/backend.log"
echo "    前端: /tmp/frontend.log"
echo ""
echo "=========================================="
