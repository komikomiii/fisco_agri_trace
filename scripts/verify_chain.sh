#!/bin/bash
# 区块链数据验证脚本
# 用于验证产品数据是否真实上链

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}🔍 区块链数据验证工具${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""

# 检查参数
if [ -z "$1" ]; then
    echo -e "${YELLOW}用法: ./verify_chain.sh <溯源码>${NC}"
    echo ""
    echo "示例:"
    echo "  ./verify_chain.sh TRACE-20251226-E5DE1560"
    echo ""
    exit 1
fi

TRACE_CODE=$1
CONSOLE_PATH="/home/pdm/fisco/console"
CONTRACT_ADDRESS="0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1"

echo -e "${YELLOW}📋 待验证溯源码: ${TRACE_CODE}${NC}"
echo ""
echo -e "${BLUE}----------------------------------------------------------------------${NC}"
echo -e "${BLUE}1️⃣  验证溯源码是否存在${NC}"
echo -e "${BLUE}----------------------------------------------------------------------${NC}"

cd ${CONSOLE_PATH}
RESULT=$(echo -e "call AgriTrace ${CONTRACT_ADDRESS} verifyTraceCode \"${TRACE_CODE}\"\nexit" | bash console.sh 2>&1 | grep -A 2 "Return values")

if echo "$RESULT" | grep -q "true"; then
    echo -e "${GREEN}✅ 验证通过: 溯源码存在于区块链上${NC}"
    VERIFIED=true
else
    echo -e "${RED}❌ 验证失败: 溯源码不存在${NC}"
    VERIFIED=false
fi

echo ""
echo -e "${BLUE}----------------------------------------------------------------------${NC}"
echo -e "${BLUE}2️⃣  查询链上产品总数${NC}"
echo -e "${BLUE}----------------------------------------------------------------------${NC}"

RESULT=$(echo -e "call AgriTrace ${CONTRACT_ADDRESS} getProductCount\nexit" | bash console.sh 2>&1 | grep -A 2 "Return values")
COUNT=$(echo "$RESULT" | grep -oP '\(\K[0-9]+(?=\))')
echo -e "${GREEN}链上产品总数: ${COUNT} 个${NC}"

echo ""
echo -e "${BLUE}----------------------------------------------------------------------${NC}"
echo -e "${BLUE}3️⃣  当前区块高度${NC}"
echo -e "${BLUE}----------------------------------------------------------------------${NC}"

RESULT=$(echo -e "getBlockNumber\nexit" | bash console.sh 2>&1 | grep -A 2 "Return values")
BLOCK_NUM=$(echo "$RESULT" | grep -oP '\(\K[0-9]+(?=\))')
echo -e "${GREEN}当前区块: ${BLOCK_NUM}${NC}"

echo ""

if [ "$VERIFIED" = true ]; then
    echo -e "${BLUE}----------------------------------------------------------------------${NC}"
    echo -e "${BLUE}4️⃣  查询产品详细信息${NC}"
    echo -e "${BLUE}----------------------------------------------------------------------${NC}"

    echo -e "${YELLOW}提示: 中文可能显示为乱码，这是Console编码问题，数据本身是正确的${NC}"
    echo ""
    echo -e "${BLUE}执行命令:${NC} call AgriTrace ${CONTRACT_ADDRESS} getProduct \"${TRACE_CODE}\""
    echo ""
    echo "请在Console中手动执行上述命令查看详细信息"
    echo ""
fi

echo -e "${BLUE}----------------------------------------------------------------------${NC}"
echo -e "${BLUE}✅ 验证完成${NC}"
echo -e "${BLUE}----------------------------------------------------------------------${NC}"
echo ""
echo -e "${GREEN}💡 提示:${NC}"
echo "  1. 想要交互式查询? 运行: cd ${CONSOLE_PATH} && bash console.sh"
echo "  2. 查看所有溯源码: 查看数据库 SELECT trace_code FROM products WHERE status='on_chain';"
echo ""
