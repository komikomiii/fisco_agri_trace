"""
FISCO BCOS Console 账户管理工具
自动检测和修复损坏的账户文件
"""
import os
import time
import subprocess
from pathlib import Path
from typing import Tuple, Optional


class AccountManager:
    """Console 账户管理器"""

    def __init__(self, console_path: str = "/home/pdm/fisco/console"):
        self.console_path = console_path
        self.account_dir = Path(console_path) / "account" / "ecdsa"

    def check_account_health(self) -> Tuple[bool, Optional[str]]:
        """
        检查账户文件是否健康
        返回: (是否健康, 错误信息)
        """
        try:
            # 检查账户目录是否存在
            if not self.account_dir.exists():
                return False, "账户目录不存在"

            # 查找 PEM 文件
            pem_files = list(self.account_dir.glob("*.pem"))
            if not pem_files:
                return False, "没有找到账户文件"

            # 测试第一个账户文件
            test_account = pem_files[0]
            result = self._test_account(test_account)

            if not result[0]:
                return False, f"账户文件损坏: {test_account.name}"

            return True, None

        except Exception as e:
            return False, f"检查失败: {str(e)}"

    def _test_account(self, account_path: Path) -> Tuple[bool, Optional[str]]:
        """
        测试单个账户文件是否可用
        运行 getAccount 命令测试
        """
        try:
            command = f"cd {self.console_path} && ./console.sh getAccount"
            result = subprocess.run(
                ["bash", "-c", command],
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, "NO_PROXY": "*", "no_proxy": "*"}
            )

            # 检查输出是否包含错误信息
            error_indicators = [
                "Failed to load the account",
                "error info",
                "encoded key spec not recognized",
                "unknown object in getInstance"
            ]

            stdout_lower = result.stdout.lower()
            stderr_lower = result.stderr.lower()

            for indicator in error_indicators:
                if indicator.lower() in stdout_lower or indicator.lower() in stderr_lower:
                    return False, f"账户加载失败: {indicator}"

            return True, None

        except subprocess.TimeoutExpired:
            return False, "命令超时"
        except Exception as e:
            return False, str(e)

    def repair_account(self) -> Tuple[bool, Optional[str]]:
        """
        修复账户文件
        策略: 删除损坏的文件并创建新账户
        返回: (是否成功, 新账户地址/错误信息)
        """
        try:
            print("开始修复账户文件...")

            # 1. 备份现有账户
            backup_dir = self.account_dir.parent / f"account.backup.{int(time.time())}"
            if self.account_dir.exists():
                import shutil
                shutil.copytree(self.account_dir, backup_dir)
                print(f"已备份到: {backup_dir}")

            # 2. 删除所有旧的账户文件
            for pem_file in self.account_dir.glob("*.pem"):
                pem_file.unlink()
                print(f"已删除损坏的账户: {pem_file.name}")

            # 3. 创建新账户
            command = f"cd {self.console_path} && ./console.sh newAccount"
            result = subprocess.run(
                ["bash", "-c", command],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "NO_PROXY": "*", "no_proxy": "*"}
            )

            if result.returncode != 0:
                return False, f"创建账户失败: {result.stderr}"

            # 4. 提取新账户地址
            new_address = None
            for line in result.stdout.split('\n'):
                if line.startswith("newAccount:"):
                    new_address = line.split(':')[1].strip()
                    break

            if not new_address:
                return False, "无法获取新账户地址"

            # 5. 验证新账户
            test_result = self._test_account(self.account_dir / f"{new_address}.pem")
            if not test_result[0]:
                return False, f"新账户验证失败: {test_result[1]}"

            print(f"✓ 账户修复成功: {new_address}")
            return True, new_address

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"修复失败: {str(e)}"

    def ensure_healthy_account(self) -> Tuple[bool, Optional[str]]:
        """
        确保账户文件健康
        如果损坏则自动修复
        返回: (是否健康, 账户地址/错误信息)
        """
        is_healthy, error = self.check_account_health()

        if is_healthy:
            # 获取当前账户地址
            pem_files = list(self.account_dir.glob("*.pem"))
            if pem_files:
                account_name = pem_files[0].stem  # 文件名不含扩展名
                return True, account_name
            return True, None

        # 账户损坏，自动修复
        print(f"⚠️  账户文件损坏: {error}")
        print("正在自动修复...")

        success, address = self.repair_account()

        if success:
            print("✓ 自动修复完成")
            return True, address
        else:
            print(f"✗ 自动修复失败: {address}")
            return False, address


# 全局实例
account_manager = AccountManager()


def auto_fix_account() -> bool:
    """
    自动修复账户文件（便捷函数）
    返回: 是否成功
    """
    success, _ = account_manager.ensure_healthy_account()
    return success


if __name__ == "__main__":
    """测试账户管理器"""
    import sys

    print("=== FISCO BCOS 账户管理器 ===\n")

    # 检查健康状态
    print("1. 检查账户健康状态")
    is_healthy, error = account_manager.check_account_health()

    if is_healthy:
        print("✓ 账户文件健康\n")
        sys.exit(0)

    print(f"✗ 账户文件损坏: {error}\n")

    # 修复账户
    print("2. 修复账户文件")
    success, result = account_manager.ensure_healthy_account()

    if success:
        print(f"✓ 修复成功，新账户: {result}")
        sys.exit(0)
    else:
        print(f"✗ 修复失败: {result}")
        sys.exit(1)
