#!/bin/bash

# 农产品溯源平台一键启动脚本
# 使用方法: ./start.sh

set -e

PROJECT_DIR="/home/pdm/DEV/komi-project"
FISCO_NODES_DIR="/home/pdm/fisco/nodes/127.0.0.1"
WEBASE_DIR="/home/pdm/webase-front"

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
echo -e "${YELLOW}[1/5] 检查 MySQL...${NC}"
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
echo -e "${YELLOW}[2/5] 启动 FISCO BCOS 区块链节点...${NC}"
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
echo -e "${YELLOW}[3/5] 启动后端 FastAPI 服务...${NC}"
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
echo -e "${YELLOW}[4/5] 启动前端 Vue 服务...${NC}"
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

# 5. 启动 WeBASE-Front 区块链浏览器
echo ""
echo -e "${YELLOW}[5/5] 启动 WeBASE-Front 区块链浏览器...${NC}"
if pgrep -f "webase.front" > /dev/null; then
    echo -e "${GREEN}  ✓ WeBASE-Front 已在运行${NC}"
else
    cd "$WEBASE_DIR"
    bash start.sh 2>/dev/null
    sleep 15
    if pgrep -f "webase.front" > /dev/null; then
        echo -e "${GREEN}  ✓ WeBASE-Front 启动成功 (http://localhost:5002/WeBASE-Front)${NC}"
    else
        echo -e "${YELLOW}  ⚠ WeBASE-Front 启动中，请稍后检查 (http://localhost:5002/WeBASE-Front)${NC}"
    fi
fi

# 状态汇总
echo ""
echo "=========================================="
echo "   启动完成 - 服务状态"
echo "=========================================="
echo ""
echo "  前端地址:       http://localhost:5173"
echo "  后端地址:       http://localhost:8000"
echo "  API文档:        http://localhost:8000/docs"
echo "  区块链RPC:      http://127.0.0.1:20200"
echo "  区块链浏览器:   http://localhost:5002/WeBASE-Front"
echo ""
echo "  日志文件:"
echo "    后端: /tmp/backend.log"
echo "    前端: /tmp/frontend.log"
echo "    WeBASE: $WEBASE_DIR/log/WeBASE-Front.log"
echo ""
echo "=========================================="
echo ""
echo "=========================================="
echo "   端口占用一览"
echo "=========================================="
echo ""
echo -e "  ${YELLOW}[数据库]${NC}"
echo "    MySQL              :3306     $(ss -tlnp 2>/dev/null | grep -q ':3306 ' && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo ""
echo -e "  ${YELLOW}[区块链节点]${NC}"
echo "    node0 RPC          :20200    $(ss -tlnp 2>/dev/null | grep -q ':20200 ' && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo "    node1 RPC          :20201    $(ss -tlnp 2>/dev/null | grep -q ':20201 ' && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo "    node2 RPC          :20202    $(ss -tlnp 2>/dev/null | grep -q ':20202 ' && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo "    node3 RPC          :20203    $(ss -tlnp 2>/dev/null | grep -q ':20203 ' && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo "    node0 P2P          :30300    $(ss -tlnp 2>/dev/null | grep -q ':30300 ' && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo "    node1 P2P          :30301    $(ss -tlnp 2>/dev/null | grep -q ':30301 ' && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo "    node2 P2P          :30302    $(ss -tlnp 2>/dev/null | grep -q ':30302 ' && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo "    node3 P2P          :30303    $(ss -tlnp 2>/dev/null | grep -q ':30303 ' && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo ""
echo -e "  ${YELLOW}[应用服务]${NC}"
echo "    FastAPI 后端       :8000     $(ss -tlnp 2>/dev/null | grep -q ':8000 ' && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo "    Vue 前端           :5173     $(ss -tlnp 2>/dev/null | grep -q ':5173 ' && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo "    WeBASE-Front       :5002     $(pgrep -f 'webase.front' > /dev/null && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo ""
echo "=========================================="
