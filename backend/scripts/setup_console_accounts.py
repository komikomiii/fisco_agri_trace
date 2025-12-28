#!/usr/bin/env python3
"""
为所有用户生成 Console 兼容的账户文件
"""
import sys
sys.path.insert(0, '/home/pdm/DEV/komi-project/backend')

from app.database import SessionLocal
from app.models.user import User
from app.blockchain.wallet import wallet_manager
from eth_account import Account

def setup_console_accounts():
    """为所有用户生成 Console 账户"""
    db = SessionLocal()

    try:
        users = db.query(User).all()

        console_dir = "/home/pdm/fisco/console/account/ecdsa"

        print(f"找到 {len(users)} 个用户")
        print("=" * 60)

        for user in users:
            # 确保用户有账户
            account = wallet_manager.ensure_user_account(user.id, user.username)

            # 获取私钥
            private_key = account["private_key"]
            address = account["address"]

            # 使用 eth-account 生成 PEM 文件
            acc = Account.from_key(private_key)

            # 生成 PEM 格式的私钥
            pem_path = f"{console_dir}/{address}.pem"

            try:
                # 保存为 PEM 格式
                key_bytes = bytes.fromhex(private_key.replace('0x', ''))

                # 写入 PEM 格式
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.primitives.asymmetric import ec
                from cryptography.hazmat.backends import default_backend

                private_key_obj = ec.derive_private_key(
                    int.from_bytes(key_bytes, 'big'),
                    ec.SECP256K1(),
                    default_backend()
                )

                pem = private_key_obj.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                )

                with open(pem_path, 'wb') as f:
                    f.write(pem)

                print(f"✅ {user.username:15} | {address}")

            except Exception as e:
                print(f"❌ {user.username:15} | Failed: {e}")

        print("\n" + "=" * 60)
        print("✅ Console 账户文件生成完成！")
        print("\n使用方法:")
        print(f"  ./console.sh -s {console_dir}/<address>.pem call AgriTrace ...")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    setup_console_accounts()
