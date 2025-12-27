#!/bin/bash
# 区块链数据查询脚本

CONSOLE_PATH="/home/pdm/fisco/console"
CONTRACT_ADDR="0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1"

echo "================================"
echo "FISCO BCOS 区块链数据查询工具"
echo "================================"
echo ""

# 检查参数
if [ "$1" == "product" ]; then
    if [ -z "$2" ]; then
        echo "用法: $0 product <溯源码>"
        echo "示例: $0 product TRACE-20251226-D202763D"
        exit 1
    fi

    echo "查询产品: $2"
    echo "---"
    cd $CONSOLE_PATH && bash console.sh call AgriTrace $CONTRACT_ADDR getProduct "\"$2\""

elif [ "$1" == "block" ]; then
    if [ -z "$2" ]; then
        echo "用法: $0 block <区块号>"
        echo "示例: $0 block 10"
        exit 1
    fi

    echo "查询区块: $2"
    echo "---"
    cd $CONSOLE_PATH && bash console.sh getBlockByNumber "$2"

elif [ "$1" == "tx" ]; then
    if [ -z "$2" ]; then
        echo "用法: $0 tx <交易哈希>"
        echo "示例: $0 tx 0x1234..."
        exit 1
    fi

    echo "查询交易: $2"
    echo "---"
    cd $CONSOLE_PATH && bash console.sh getTransactionByHash "$2"

elif [ "$1" == "height" ]; then
    echo "查询区块高度"
    echo "---"
    cd $CONSOLE_PATH && bash console.sh getBlockNumber

elif [ "$1" == "list" ]; then
    echo "查询所有已上链产品"
    echo "---"
    cd $CONSOLE_PATH && bash console.sh call AgriTrace $CONTRACT_ADDR getProductCount

else
    echo "用法:"
    echo "  $0 product <溯源码>    - 查询产品信息"
    echo "  $0 block <区块号>      - 查询区块信息"
    echo "  $0 tx <交易哈希>       - 查询交易信息"
    echo "  $0 height              - 查询当前区块高度"
    echo "  $0 list                - 查询产品总数"
    echo ""
    echo "示例:"
    echo "  $0 product TRACE-20251226-D202763D"
    echo "  $0 block 10"
    echo "  $0 height"
fi
