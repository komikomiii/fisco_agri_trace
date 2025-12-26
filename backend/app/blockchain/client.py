"""
FISCO BCOS 区块链客户端
使用 JSON-RPC 与 FISCO BCOS 3.0 节点交互
"""
import json
import subprocess
import os
from typing import Optional, Dict, Any, Tuple
import requests

from app.blockchain.config import (
    RPC_URL, GROUP_ID, CONTRACT_ADDRESS, CONSOLE_PATH
)


class FiscoBcosClient:
    """FISCO BCOS 区块链客户端"""

    def __init__(self):
        self.rpc_url = RPC_URL
        self.group_id = GROUP_ID
        self.contract_address = CONTRACT_ADDRESS
        self.console_path = CONSOLE_PATH
        self.session = requests.Session()

    def _rpc_call(self, method: str, params: list) -> Dict[str, Any]:
        """执行 RPC 调用"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        try:
            response = self.session.post(
                self.rpc_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def get_block_number(self) -> int:
        """获取当前区块高度"""
        result = self._rpc_call("getBlockNumber", [self.group_id])
        if "result" in result:
            return int(result["result"], 16) if isinstance(result["result"], str) else result["result"]
        return 0

    def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict]:
        """获取交易回执"""
        result = self._rpc_call("getTransactionReceipt", [self.group_id, tx_hash, True])
        return result.get("result")

    def _run_console_command(self, command: str) -> Tuple[bool, str, str]:
        """
        执行 Console 命令
        返回: (成功标志, stdout, stderr)
        """
        try:
            # 切换到 console 目录执行
            result = subprocess.run(
                ["bash", "-c", f"cd {self.console_path} && ./console.sh {command}"],
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ, "NO_PROXY": "*", "no_proxy": "*"}
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timeout"
        except Exception as e:
            return False, "", str(e)

    def _parse_console_output(self, output: str) -> Dict[str, Any]:
        """解析 Console 输出"""
        result = {
            "success": False,
            "tx_hash": None,
            "block_number": None,
            "return_values": None
        }

        lines = output.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("transaction hash:"):
                result["tx_hash"] = line.split(":", 1)[1].strip()
                result["success"] = True
            elif line.startswith("Return code: 0"):
                result["success"] = True
            elif line.startswith("Return values:"):
                result["return_values"] = line.split(":", 1)[1].strip()
            elif "blockNumber" in line.lower():
                try:
                    # 尝试提取区块号
                    parts = line.split(":")
                    if len(parts) > 1:
                        result["block_number"] = int(parts[1].strip())
                except:
                    pass

        return result

    # ==================== 合约调用方法 ====================

    def create_product(
        self,
        trace_code: str,
        name: str,
        category: str,
        origin: str,
        quantity: int,
        unit: str,
        data: str,
        operator_name: str
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        创建产品上链
        返回: (成功标志, 交易哈希, 区块号)
        """
        # 转义参数中的特殊字符
        escaped_data = data.replace('"', '\\"')

        command = (
            f'call AgriTrace {self.contract_address} createProduct '
            f'"{trace_code}" "{name}" "{category}" "{origin}" {quantity} "{unit}" '
            f'"{escaped_data}" "{operator_name}"'
        )

        success, stdout, stderr = self._run_console_command(command)

        if not success:
            print(f"Console error: {stderr}")
            return False, None, None

        parsed = self._parse_console_output(stdout)

        # 如果成功，获取区块号
        if parsed["success"] and parsed["tx_hash"]:
            block_number = self.get_block_number()
            return True, parsed["tx_hash"], block_number

        return False, None, None

    def add_amend_record(
        self,
        trace_code: str,
        stage: int,
        data: str,
        remark: str,
        operator_name: str,
        previous_record_id: int,
        amend_reason: str
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        添加修正记录
        返回: (成功标志, 交易哈希, 区块号)
        """
        escaped_data = data.replace('"', '\\"')
        escaped_remark = remark.replace('"', '\\"')
        escaped_reason = amend_reason.replace('"', '\\"')

        command = (
            f'call AgriTrace {self.contract_address} addAmendRecord '
            f'"{trace_code}" {stage} "{escaped_data}" "{escaped_remark}" '
            f'"{operator_name}" {previous_record_id} "{escaped_reason}"'
        )

        success, stdout, stderr = self._run_console_command(command)

        if not success:
            print(f"Console error: {stderr}")
            return False, None, None

        parsed = self._parse_console_output(stdout)

        if parsed["success"] and parsed["tx_hash"]:
            block_number = self.get_block_number()
            return True, parsed["tx_hash"], block_number

        return False, None, None

    def add_record(
        self,
        trace_code: str,
        stage: int,
        action: int,
        data: str,
        remark: str,
        operator_name: str
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        添加流转记录
        返回: (成功标志, 交易哈希, 区块号)
        """
        escaped_data = data.replace('"', '\\"')
        escaped_remark = remark.replace('"', '\\"')

        command = (
            f'call AgriTrace {self.contract_address} addRecord '
            f'"{trace_code}" {stage} {action} "{escaped_data}" "{escaped_remark}" "{operator_name}"'
        )

        success, stdout, stderr = self._run_console_command(command)

        if not success:
            print(f"Console error: {stderr}")
            return False, None, None

        parsed = self._parse_console_output(stdout)

        if parsed["success"] and parsed["tx_hash"]:
            block_number = self.get_block_number()
            return True, parsed["tx_hash"], block_number

        return False, None, None

    def get_product(self, trace_code: str) -> Optional[Dict]:
        """查询产品信息"""
        command = f'call AgriTrace {self.contract_address} getProduct "{trace_code}"'
        success, stdout, stderr = self._run_console_command(command)

        if not success:
            return None

        # 解析返回值
        # Console 返回格式: Return values:(value1, value2, ...)
        parsed = self._parse_console_output(stdout)
        if parsed["return_values"]:
            return {"raw": parsed["return_values"]}

        return None

    def verify_trace_code(self, trace_code: str) -> bool:
        """验证溯源码是否存在"""
        command = f'call AgriTrace {self.contract_address} verifyTraceCode "{trace_code}"'
        success, stdout, stderr = self._run_console_command(command)

        if not success:
            return False

        parsed = self._parse_console_output(stdout)
        if parsed["return_values"]:
            return "true" in parsed["return_values"].lower()

        return False

    def get_product_count(self) -> int:
        """获取产品总数"""
        command = f'call AgriTrace {self.contract_address} getProductCount'
        success, stdout, stderr = self._run_console_command(command)

        if not success:
            return 0

        parsed = self._parse_console_output(stdout)
        if parsed["return_values"]:
            try:
                # 解析 (0) 这样的格式
                value = parsed["return_values"].strip("()")
                return int(value)
            except:
                pass

        return 0

    def is_connected(self) -> bool:
        """检查区块链连接是否正常"""
        try:
            block_number = self.get_block_number()
            return block_number >= 0
        except:
            return False


# 单例实例
blockchain_client = FiscoBcosClient()
