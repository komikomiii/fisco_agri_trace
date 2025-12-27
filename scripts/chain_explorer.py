#!/usr/bin/env python3
"""
FISCO BCOS 区块链数据浏览工具
可以查看产品、区块、交易等链上数据
"""

import sys
import subprocess
import json
import re
from datetime import datetime

CONSOLE_PATH = "/home/pdm/fisco/console"
CONTRACT_ADDR = "0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1"

def run_console_command(command):
    """执行 console 命令"""
    try:
        result = subprocess.run(
            ["bash", "-c", f"cd {CONSOLE_PATH} && ./console.sh {command}"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout
    except Exception as e:
        return f"Error: {str(e)}"

def parse_product_data(output):
    """解析产品数据"""
    match = re.search(r'Return values:\(([^)]+)\)', output)
    if not match:
        return None

    values_str = match.group(1)
    # 简单的分割（注意：地址中可能有逗号）
    parts = []
    current = ""
    paren_count = 0

    for char in values_str:
        if char == ',' and paren_count == 0:
            parts.append(current.strip())
            current = ""
        else:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            current += char

    if current:
        parts.append(current.strip())

    if len(parts) >= 11:
        return {
            "name": parts[0],
            "category": parts[1],
            "origin": parts[2],
            "quantity_raw": parts[3],
            "quantity": float(parts[3]) / 1000 if parts[3].isdigit() else parts[3],
            "unit": parts[4],
            "creator": parts[7],
            "current_holder": parts[8],
            "timestamp": int(parts[9]) if parts[9].isdigit() else parts[9],
            "timestamp_human": datetime.fromtimestamp(int(parts[9])/1000).strftime("%Y-%m-%d %H:%M:%S") if parts[9].isdigit() else "N/A",
            "record_count": parts[10]
        }
    return None

def query_product(trace_code):
    """查询产品信息"""
    print(f"\n{'='*60}")
    print(f"产品查询: {trace_code}")
    print('='*60)

    command = f'call AgriTrace {CONTRACT_ADDR} getProduct "{trace_code}"'
    output = run_console_command(command)

    if "does not exist" in output or "Return code: 0" not in output:
        print("❌ 产品不存在或查询失败")
        print(output)
        return

    data = parse_product_data(output)
    if data:
        print(f"\n📦 产品信息:")
        print(f"  名称:      {data['name']}")
        print(f"  类别:      {data['category']}")
        print(f"  产地:      {data['origin']}")
        print(f"  数量:      {data['quantity']} {data['unit']}")
        print(f"  数量(原始): {data['quantity_raw']} (链上存储的整数值)")
        print(f"  创建者:    {data['creator']}")
        print(f"  当前持有:  {data['current_holder']}")
        print(f"  创建时间:  {data['timestamp_human']}")
        print(f"  记录数:    {data['record_count']}")
        print(f"\n📋 原始数据:")
        print(output)
    else:
        print("⚠️  无法解析数据")
        print(output)

def query_block_height():
    """查询区块高度"""
    print(f"\n{'='*60}")
    print("区块链状态")
    print('='*60)

    output = run_console_command('getBlockNumber')
    print(output)

def query_block(block_number):
    """查询区块信息"""
    print(f"\n{'='*60}")
    print(f"区块查询: #{block_number}")
    print('='*60)

    output = run_console_command(f'getBlockByNumber {block_number}')
    print(output)

def query_tx(tx_hash):
    """查询交易信息"""
    print(f"\n{'='*60}")
    print(f"交易查询: {tx_hash}")
    print('='*60)

    output = run_console_command(f'getTransactionByHash {tx_hash}')
    print(output)

def query_product_count():
    """查询产品总数"""
    print(f"\n{'='*60}")
    print("产品统计")
    print('='*60)

    output = run_console_command(f'call AgriTrace {CONTRACT_ADDR} getProductCount')

    match = re.search(r'Return values:\((\d+)\)', output)
    if match:
        count = match.group(1)
        print(f"\n📊 链上产品总数: {count}")

    print(f"\n原始输出:\n{output}")

def show_help():
    """显示帮助信息"""
    print("""
╔════════════════════════════════════════════════════════════╗
║        FISCO BCOS 区块链数据浏览工具                      ║
╚════════════════════════════════════════════════════════════╝

用法:
  python3 chain_explorer.py <命令> [参数]

命令:
  product <溯源码>     查询产品详细信息
  block <区块号>       查询区块信息
  tx <交易哈希>        查询交易详情
  height               查询当前区块高度
  count                查询链上产品总数

示例:
  python3 chain_explorer.py product TRACE-20251226-D202763D
  python3 chain_explorer.py block 10
  python3 chain_explorer.py tx 0x7634ff391e44a3a69093d0e1c7bcba8f29ac850f6a71c27fcb91eadc2463f1d2
  python3 chain_explorer.py height
  python3 chain_explorer.py count
""")

def main():
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == "product":
        if len(sys.argv) < 3:
            print("❌ 错误: 请提供溯源码")
            print("用法: python3 chain_explorer.py product <溯源码>")
            return
        query_product(sys.argv[2])

    elif command == "block":
        if len(sys.argv) < 3:
            print("❌ 错误: 请提供区块号")
            print("用法: python3 chain_explorer.py block <区块号>")
            return
        query_block(sys.argv[2])

    elif command == "tx":
        if len(sys.argv) < 3:
            print("❌ 错误: 请提供交易哈希")
            print("用法: python3 chain_explorer.py tx <交易哈希>")
            return
        query_tx(sys.argv[2])

    elif command == "height":
        query_block_height()

    elif command == "count":
        query_product_count()

    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()
