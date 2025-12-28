#!/usr/bin/env python3
"""
区块链数据验证脚本
用于验证产品数据是否真实上链
"""

import sys
import os

# 添加backend路径以便导入模块
sys.path.insert(0, '/home/pdm/DEV/komi-project/backend')

from app.blockchain import blockchain_client


def print_header(text):
    print(f"\n{'='*70}")
    print(f"{text}")
    print(f"{'='*70}\n")


def verify_trace_code(trace_code):
    """验证溯源码"""
    print_header("🔍 区块链数据验证工具")

    print(f"📋 待验证溯源码: {trace_code}\n")

    # 1. 验证溯源码存在
    print("-" * 70)
    print("1️⃣  验证溯源码是否存在")
    print("-" * 70)

    exists = blockchain_client.verify_trace_code(trace_code)
    if exists:
        print(f"✅ 验证通过: 溯源码存在于区块链上\n")
    else:
        print(f"❌ 验证失败: 溯源码不存在\n")
        return False

    # 2. 查询产品总数
    print("-" * 70)
    print("2️⃣  查询链上产品总数")
    print("-" * 70)

    count = blockchain_client.get_product_count()
    print(f"链上产品总数: {count} 个\n")

    # 3. 当前区块高度
    print("-" * 70)
    print("3️⃣  当前区块高度")
    print("-" * 70)

    block_num = blockchain_client.get_block_number()
    print(f"当前区块: {block_num}\n")

    # 4. 连接状态
    print("-" * 70)
    print("4️⃣  区块链连接状态")
    print("-" * 70)

    connected = blockchain_client.is_connected()
    print(f"连接状态: {'✅ 已连接' if connected else '❌ 未连接'}")
    print(f"RPC 地址: {blockchain_client.rpc_url}")
    print(f"合约地址: {blockchain_client.contract_address}\n")

    print_header("✅ 验证完成")

    print("💡 提示:")
    print("  1. 想要交互式查询? 运行: cd /home/pdm/fisco/console && bash console.sh")
    print("  2. 在Console中执行:")
    print(f"     call AgriTrace {blockchain_client.contract_address} getProduct \"{trace_code}\"")
    print()

    return True


def list_all_products():
    """列出所有链上产品"""
    print_header("📋 链上产品列表")

    # 从数据库读取
    from app.database import SessionLocal
    from app.models.product import Product

    db = SessionLocal()
    products = db.query(Product).filter(Product.status == 'on_chain').all()

    print(f"共 {len(products)} 个已上链产品:\n")

    for i, p in enumerate(products, 1):
        print(f"{i}. {p.trace_code}")
        print(f"   名称: {p.name}")
        print(f"   产地: {p.origin}")
        print(f"   数量: {p.quantity} {p.unit}")
        print(f"   区块: #{p.block_number}")
        print(f"   交易哈希: {p.tx_hash}")
        print()

    db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  验证溯源码: python3 verify_chain.py <溯源码>")
        print("  列出所有产品: python3 verify_chain.py --list")
        print()
        print("示例:")
        print("  python3 verify_chain.py TRACE-20251226-E5DE1560")
        print("  python3 verify_chain.py --list")
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_all_products()
    else:
        verify_trace_code(sys.argv[1])
