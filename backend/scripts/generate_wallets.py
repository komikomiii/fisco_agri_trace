#!/usr/bin/env python3
"""
为现有用户生成区块链地址
扫库里的用户，给还没有 blockchain_address 的补生成钱包并写回数据库（相当于数据修复/批量补全）
"""
import sys
sys.path.insert(0, '/home/pdm/DEV/komi-project/backend')

from app.database import SessionLocal
from app.models.user import User
from app.blockchain.wallet import wallet_manager

def generate_wallets_for_users():
    """为所有没有地址的用户生成钱包"""
    db = SessionLocal()

    try:
        users = db.query(User).all()

        print(f"找到 {len(users)} 个用户")
        print("=" * 60)

        for user in users:
            if user.blockchain_address:
                print(f"✅ 用户 {user.username} (ID:{user.id}) 已有地址")
                print(f"   地址: {user.blockchain_address}")
                continue

            # 生成钱包
            print(f"\n📝 为用户 {user.username} (ID:{user.id}) 生成钱包...")

            account = wallet_manager.ensure_user_account(user.id, user.username)

            # 更新数据库
            user.blockchain_address = account["address"]
            db.commit()

            print(f"✅ 成功生成地址")
            print(f"   地址: {account['address']}")
            print(f"   密钥文件: {account.get('keystore_path', 'N/A')}")

        print("\n" + "=" * 60)
        print("✅ 所有用户钱包生成完成！")

        # 显示所有用户地址
        print("\n📋 用户地址列表:")
        print("-" * 60)
        users = db.query(User).all()
        for user in users:
            print(f"{user.username:15} | {user.blockchain_address}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    generate_wallets_for_users()
