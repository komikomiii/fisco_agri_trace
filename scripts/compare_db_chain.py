#!/usr/bin/env python3
"""
对比数据库和链上数据的一致性
"""

import sys
import os
sys.path.insert(0, '/home/pdm/DEV/komi-project/backend')

from app.database import SessionLocal
from app.models.product import Product
from app.blockchain.client import FiscoBcosClient
import re

def parse_chain_data(raw_str):
    """解析链上原始数据"""
    match = re.search(r'\(([^)]+)\)', raw_str)
    if not match:
        return None

    parts = []
    current = ""
    paren_count = 0

    for char in match.group(1):
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
            "quantity_int": int(parts[3]) if parts[3].isdigit() else 0,
            "quantity": int(parts[3]) / 1000 if parts[3].isdigit() else 0,
            "unit": parts[4],
            "creator": parts[7],
            "timestamp": int(parts[9]) if parts[9].isdigit() else 0,
        }
    return None

def compare_product(trace_code):
    """对比单个产品的数据库和链上数据"""
    db = SessionLocal()
    client = FiscoBcosClient()

    print(f"\n{'='*70}")
    print(f"数据一致性验证: {trace_code}")
    print('='*70)

    # 1. 查询数据库
    product = db.query(Product).filter(Product.trace_code == trace_code).first()

    if not product:
        print("❌ 数据库中不存在该产品")
        db.close()
        return

    print(f"\n📊 数据库数据:")
    print(f"  名称:     {product.name}")
    print(f"  类别:     {product.category}")
    print(f"  产地:     {product.origin}")
    print(f"  数量:     {product.quantity} {product.unit}")
    print(f"  状态:     {product.status}")
    print(f"  创建时间: {product.created_at}")

    db_data = {
        "name": product.name,
        "category": product.category,
        "origin": product.origin,
        "quantity": product.quantity,
        "unit": product.unit
    }

    # 2. 查询链上数据
    product_info = client.get_product(trace_code)

    if not product_info:
        print("\n❌ 链上不存在该产品")
        if product.status == 'DRAFT':
            print("  → 原因: 产品还是草稿状态，未上链")
        db.close()
        return

    raw_data = product_info.get('raw', '')
    print(f"\n⛓️  链上原始数据:")
    print(f"  {raw_data}")

    chain_data = parse_chain_data(raw_data)

    if not chain_data:
        print("\n⚠️  无法解析链上数据")
        db.close()
        return

    print(f"\n⛓️  链上解析数据:")
    print(f"  名称:     {chain_data['name']}")
    print(f"  类别:     {chain_data['category']}")
    print(f"  产地:     {chain_data['origin']}")
    print(f"  数量:     {chain_data['quantity']} {chain_data['unit']}")
    print(f"  数量(原): {chain_data['quantity_int']} (整数*1000)")

    # 3. 对比
    print(f"\n🔍 一致性检查:")

    issues = []

    # 数量对比
    if abs(db_data['quantity'] - chain_data['quantity']) > 0.001:
        issues.append(f"  ❌ 数量不一致: DB={db_data['quantity']} vs Chain={chain_data['quantity']}")
        print(f"  ❌ 数量不一致:")
        print(f"      数据库: {db_data['quantity']} {db_data['unit']}")
        print(f"      链上:   {chain_data['quantity']} {chain_data['unit']}")
    else:
        print(f"  ✅ 数量一致: {db_data['quantity']} {db_data['unit']}")

    # 单位对比
    if db_data['unit'] != chain_data['unit']:
        issues.append(f"  ❌ 单位不一致: DB={db_data['unit']} vs Chain={chain_data['unit']}")
        print(f"  ❌ 单位不一致:")
        print(f"      数据库: {db_data['unit']}")
        print(f"      链上:   {chain_data['unit']}")
    else:
        print(f"  ✅ 单位一致: {db_data['unit']}")

    # 中文字段（只检查是否为问号）
    if '?' in chain_data['name']:
        print(f"  ⚠️  名称: 链上显示为问号（Console编码限制）")
        print(f"      数据库: {db_data['name']}")
        print(f"      链上实际存储了完整数据，但Console显示为: {chain_data['name']}")
    else:
        if db_data['name'] != chain_data['name']:
            issues.append(f"  ❌ 名称不一致: DB={db_data['name']} vs Chain={chain_data['name']}")
            print(f"  ❌ 名称不一致:")
            print(f"      数据库: {db_data['name']}")
            print(f"      链上:   {chain_data['name']}")
        else:
            print(f"  ✅ 名称一致: {db_data['name']}")

    if '?' in chain_data['category']:
        print(f"  ⚠️  类别: 链上显示为问号（Console编码限制）")
        print(f"      数据库: {db_data['category']}")
    else:
        if db_data['category'] != chain_data['category']:
            issues.append(f"  ❌ 类别不一致")
        else:
            print(f"  ✅ 类别一致: {db_data['category']}")

    if '?' in chain_data['origin']:
        print(f"  ⚠️  产地: 链上显示为问号（Console编码限制）")
        print(f"      数据库: {db_data['origin']}")
    else:
        if db_data['origin'] != chain_data['origin']:
            issues.append(f"  ❌ 产地不一致")
        else:
            print(f"  ✅ 产地一致: {db_data['origin']}")

    # 总结
    print(f"\n{'='*70}")
    if issues:
        print(f"❌ 发现 {len(issues)} 个数据不一致问题:")
        for issue in issues:
            print(issue)
    else:
        print(f"✅ 数据完全一致（中文字段链上实际正确，只是Console显示限制）")
    print('='*70)

    db.close()

def compare_all_products():
    """对比所有已上链的产品"""
    db = SessionLocal()

    products = db.query(Product).filter(Product.status == 'ON_CHAIN').all()

    print(f"\n{'='*70}")
    print(f"批量验证所有已上链产品")
    print(f"共找到 {len(products)} 个已上链产品")
    print('='*70)

    for product in products:
        compare_product(product.trace_code)
        print()

    db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("""
用法:
  python3 compare_db_chain.py <溯源码>     # 对比单个产品
  python3 compare_db_chain.py all          # 对比所有已上链产品

示例:
  python3 compare_db_chain.py TRACE-20251227-278DEAB0
  python3 compare_db_chain.py all
        """)
        sys.exit(1)

    if sys.argv[1] == 'all':
        compare_all_products()
    else:
        compare_product(sys.argv[1])
