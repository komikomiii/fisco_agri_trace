"""
区块链钱包管理
为用户生成和管理区块链账户（私钥、地址）
"""
import os
import json
from eth_account import Account
from pathlib import Path
from typing import Dict, Optional

# 启用 HD 钱包功能（需要额外库）
# Account.enable_unaudited_hdwallet_features()


class WalletManager:
    """区块链钱包管理器"""

    def __init__(self, keystore_dir: str = "/home/pdm/DEV/komi-project/keystore"):
        """
        初始化钱包管理器

        Args:
            keystore_dir: 密钥存储目录
        """
        self.keystore_dir = Path(keystore_dir)
        self.keystore_dir.mkdir(parents=True, exist_ok=True)
        self.account_file = self.keystore_dir / "accounts.json"

        # 加载已有账户
        self.accounts = self._load_accounts()

    def _load_accounts(self) -> Dict:
        """从文件加载账户映射"""
        if self.account_file.exists():
            with open(self.account_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_accounts(self):
        """保存账户映射到文件"""
        with open(self.account_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, indent=2, ensure_ascii=False)

    def create_account(self, user_id: int, username: str) -> Dict[str, str]:
        """
        为用户创建新的区块链账户

        Args:
            user_id: 用户ID
            username: 用户名（用于标识）

        Returns:
            {
                "address": "0x...",
                "private_key": "0x...",
                "keystore_path": "/path/to/keystore"
            }
        """
        # 生成新账户
        account = Account.create()

        # 准备返回数据
        result = {
            "address": account.address,
            "private_key": account.key.hex(),
            "keystore_path": str(self.keystore_dir / f"user_{user_id}.json")
        }

        # 保存为 keystore 文件（加密存储）
        keystore_path = self.keystore_dir / f"user_{user_id}.json"
        encrypted = Account.encrypt(account.key, password=str(user_id))  # 使用用户ID作为密码

        with open(keystore_path, 'w', encoding='utf-8') as f:
            json.dump(encrypted, f)

        # 更新账户映射
        self.accounts[str(user_id)] = {
            "username": username,
            "address": account.address,
            "keystore": str(keystore_path)
        }
        self._save_accounts()

        return result

    def get_account(self, user_id: int) -> Optional[Dict]:
        """
        获取用户账户信息

        Args:
            user_id: 用户ID

        Returns:
            账户信息字典，如果不存在返回 None
        """
        user_key = str(user_id)
        if user_key not in self.accounts:
            return None

        account_info = self.accounts[user_key]
        keystore_path = Path(account_info["keystore"])

        if not keystore_path.exists():
            return None

        # 从 keystore 解密私钥
        with open(keystore_path, 'r', encoding='utf-8') as f:
            encrypted = json.load(f)

        private_key = Account.decrypt(encrypted, password=str(user_id))
        account = Account.from_key(private_key)

        return {
            "address": account.address,
            "private_key": private_key.hex(),
            "username": account_info["username"]
        }

    def import_account(self, user_id: int, username: str, private_key: str) -> Dict[str, str]:
        """
        导入已有私钥

        Args:
            user_id: 用户ID
            username: 用户名
            private_key: 私钥（hex格式）

        Returns:
            账户信息
        """
        account = Account.from_key(private_key)

        # 保存为 keystore
        keystore_path = self.keystore_dir / f"user_{user_id}.json"
        encrypted = Account.encrypt(account.key, password=str(user_id))

        with open(keystore_path, 'w', encoding='utf-8') as f:
            json.dump(encrypted, f)

        # 更新映射
        self.accounts[str(user_id)] = {
            "username": username,
            "address": account.address,
            "keystore": str(keystore_path)
        }
        self._save_accounts()

        return {
            "address": account.address,
            "private_key": private_key,
            "keystore_path": str(keystore_path)
        }

    def ensure_user_account(self, user_id: int, username: str) -> Dict[str, str]:
        """
        确保用户有账户，如果没有则创建

        Args:
            user_id: 用户ID
            username: 用户名

        Returns:
            账户信息
        """
        account = self.get_account(user_id)
        if account:
            return {
                "address": account["address"],
                "private_key": account["private_key"],
                "exists": True
            }

        # 不存在则创建
        new_account = self.create_account(user_id, username)

        # 同时为 Console 创建账户文件（PEM 格式）
        self._create_console_pem(user_id, new_account["private_key"])

        return {
            "address": new_account["address"],
            "private_key": new_account["private_key"],
            "exists": False
        }

    def _create_console_pem(self, user_id: int, private_key: str):
        """
        为 Console 创建 PEM 格式的账户文件

        Args:
            user_id: 用户ID
            private_key: 私钥 (hex格式)
        """
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.backends import default_backend

        try:
            # 将 hex 私钥转换为 bytes
            private_key_bytes = bytes.fromhex(private_key.replace('0x', ''))

            # 创建私钥对象
            private_key_obj = ec.derive_private_key(int.from_bytes(private_key_bytes, 'big'), ec.SECP256K1(), default_backend())

            # 序列化为 PEM 格式
            pem = private_key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )

            # 保存 PEM 文件
            console_account_dir = "/home/pdm/fisco/console/account/ecdsa"
            pem_path = f"{console_account_dir}/0x{user_id:040x}.pem"

            with open(pem_path, 'wb') as f:
                f.write(pem)

            print(f"✅ Created Console account: {pem_path}")

        except Exception as e:
            print(f"⚠️  Failed to create Console PEM: {e}")


# 全局单例
wallet_manager = WalletManager()
