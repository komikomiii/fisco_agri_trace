"""
FISCO BCOS 区块链客户端
使用 JSON-RPC 与 FISCO BCOS 3.0 节点交互
"""
import json
import subprocess
import os
from typing import Optional, Dict, Any, Tuple, List
import requests
from eth_abi import encode, decode
from eth_utils import function_signature_to_4byte_selector

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
        self._clean_problematic_pem_files()

    def _clean_problematic_pem_files(self):
        """
        清除 Console 自动生成的有问题的 PEM 文件
        这些文件会导致 Console 报错: "encoded key spec not recognized"
        """
        import glob
        ecdsa_dir = os.path.join("/home/pdm/fisco/console/account", "ecdsa")
        pattern = os.path.join(ecdsa_dir, "0x0000000000000000000000000000000000000*.pem")
        try:
            for pem_file in glob.glob(pattern):
                try:
                    os.remove(pem_file)
                    # 同时删除对应的 .pub 文件
                    pub_file = pem_file + ".pub"
                    if os.path.exists(pub_file):
                        os.remove(pub_file)
                except:
                    pass
        except:
            pass

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
        """获取交易回执（先尝试 RPC，失败则使用 Console）"""
        import json

        # 先尝试 RPC
        result = self._rpc_call("getTransactionReceipt", [self.group_id, tx_hash, True])
        if result.get("result"):
            return result.get("result")

        # RPC 失败，回退到 Console
        command = f'getTransactionReceipt {tx_hash}'
        success, stdout, stderr = self._run_console_command(command)
        if not success or not stdout:
            return None

        # Console 输出是 JSON 格式
        try:
            receipt = json.loads(stdout)
            return receipt
        except json.JSONDecodeError:
            # 如果 JSON 解析失败，尝试 key=value 格式（旧版本）
            receipt = {}
            lines = stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if '=' in line and not line.startswith('JsonTransactionResponse'):
                    if line.endswith(','):
                        line = line[:-1]
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().strip('"')
                        value = parts[1].strip().strip(',').strip("'").strip('"')
                        receipt[key] = value

            return receipt if receipt else None

    def _wait_for_transaction(self, tx_hash: str, timeout: int = 30, poll_interval: float = 1.0) -> Optional[int]:
        """
        等待交易被打包进区块，返回实际区块号
        """
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            receipt = self.get_transaction_receipt(tx_hash)
            if receipt and receipt.get("status") == "0x0":
                # 交易成功，获取区块号
                block_number = receipt.get("blockNumber")
                if block_number:
                    # 如果是十六进制字符串，转换为整数
                    if isinstance(block_number, str) and block_number.startswith("0x"):
                        return int(block_number, 16)
                    return int(block_number)
            time.sleep(poll_interval)

        # 超时返回当前区块号
        return self.get_block_number()

    def _run_console_command(self, command: str) -> Tuple[bool, str, str]:
        """
        执行 Console 命令
        返回: (成功标志, stdout, stderr)
        """
        # 每次执行命令前清理有问题的pem文件
        self._clean_problematic_pem_files()

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
            print(f"Console command failed!")
            print(f"STDERR: {stderr}")
            print(f"STDOUT: {stdout}")
            return False, None, None

        parsed = self._parse_console_output(stdout)

        if not parsed["success"]:
            print(f"Failed to parse console output")
            print(f"STDOUT: {stdout}")
            return False, None, None

        # 如果成功，获取区块号
        if parsed["success"] and parsed["tx_hash"]:
            tx_hash = parsed["tx_hash"]
            # 等待交易被打包并获取实际区块号
            block_number = self._wait_for_transaction(tx_hash)
            return True, tx_hash, block_number

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
            tx_hash = parsed["tx_hash"]
            # 等待交易被打包并获取实际区块号
            block_number = self._wait_for_transaction(tx_hash)
            return True, tx_hash, block_number

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
            tx_hash = parsed["tx_hash"]
            # 等待交易被打包并获取实际区块号
            block_number = self._wait_for_transaction(tx_hash)
            return True, tx_hash, block_number

        return False, None, None

    def transfer_product(
        self,
        trace_code: str,
        new_holder: str,
        new_stage: str,
        data: str,
        remark: str,
        operator_name: str
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        转移产品到下一阶段
        返回: (成功标志, 交易哈希, 区块号)
        """
        escaped_data = data.replace('"', '\\"')
        escaped_remark = remark.replace('"', '\\"')

        # Stage 映射: 字符串 -> 整数
        stage_map = {
            "producer": 0,
            "processor": 1,
            "inspector": 2,
            "seller": 3,
            "sold": 4
        }

        stage_int = stage_map.get(new_stage, 1)  # 默认为加工商阶段

        command = (
            f'call AgriTrace {self.contract_address} transferProduct '
            f'"{trace_code}" "{new_holder}" {stage_int} "{escaped_data}" "{escaped_remark}" "{operator_name}"'
        )

        success, stdout, stderr = self._run_console_command(command)

        if not success:
            print(f"Console error: {stderr}")
            return False, None, None

        parsed = self._parse_console_output(stdout)

        if parsed["success"] and parsed["tx_hash"]:
            tx_hash = parsed["tx_hash"]
            # 等待交易被打包并获取实际区块号
            block_number = self._wait_for_transaction(tx_hash)
            return True, tx_hash, block_number

        return False, None, None

    def _call_contract_rpc(self, function_signature: str, input_types: List[str], input_values: List[Any], output_types: List[str]) -> Optional[List[Any]]:
        """
        通过 RPC 调用合约 (view 函数)

        Args:
            function_signature: 函数签名，如 "getProduct(string)"
            input_types: 输入参数类型列表，如 ["string"]
            input_values: 输入参数值列表，如 ["TRACE-xxx"]
            output_types: 输出参数类型列表，如 ["string", "string", "uint256", ...]

        Returns:
            解码后的返回值列表，失败返回 None
        """
        try:
            # 1. 计算函数选择器 (前4字节)
            selector = function_signature_to_4byte_selector(function_signature)

            # 2. 编码输入参数
            if input_values:
                encoded_params = encode(input_types, input_values)
            else:
                encoded_params = b''

            # 3. 组合完整的 data: selector + encoded_params
            data = "0x" + (selector + encoded_params).hex()

            # 4. 调用 RPC 的 call 方法
            params = [
                self.group_id,
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": self.contract_address,
                    "data": data
                }
            ]

            result = self._rpc_call("call", params)

            if "result" in result and "output" in result["result"]:
                output_hex = result["result"]["output"]

                # 5. 解码返回值
                if output_hex and output_hex != "0x":
                    output_bytes = bytes.fromhex(output_hex[2:])  # 去掉 0x 前缀
                    decoded_values = decode(output_types, output_bytes)
                    return list(decoded_values)

            return None

        except Exception as e:
            print(f"RPC call error: {e}")
            import traceback
            traceback.print_exc()
            return None

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

    def get_product_rpc(self, trace_code: str) -> Optional[Dict]:
        """
        通过 RPC 直接调用查询产品信息（正确解码 UTF-8 中文）

        返回格式:
        {
            "name": "产品名称",
            "category": "产品类别",
            "origin": "产地",
            "quantity": 3000,  # 整数，已乘以1000
            "unit": "kg",
            "currentStage": 0,
            "status": 1,
            "creator": "0x...",
            "currentHolder": "0x...",
            "createdAt": 1234567890,
            "recordCountNum": 5
        }
        """
        # getProduct(string) returns (string, string, string, uint256, string, uint8, uint8, address, address, uint256, uint256)
        result = self._call_contract_rpc(
            function_signature="getProduct(string)",
            input_types=["string"],
            input_values=[trace_code],
            output_types=["string", "string", "string", "uint256", "string", "uint8", "uint8", "address", "address", "uint256", "uint256"]
        )

        if result and len(result) == 11:
            return {
                "name": result[0],
                "category": result[1],
                "origin": result[2],
                "quantity": result[3],  # 整数
                "unit": result[4],
                "currentStage": result[5],
                "status": result[6],
                "creator": result[7],
                "currentHolder": result[8],
                "createdAt": result[9],
                "recordCountNum": result[10]
            }

        # 如果 RPC 调用失败,返回 None(会触发API回退到使用数据库或显示错误)
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

    def get_transaction_by_hash(self, tx_hash: str) -> Optional[Dict]:
        """
        通过交易哈希获取交易详情（使用 Console）
        """
        command = f'getTransactionByHash {tx_hash}'
        success, stdout, stderr = self._run_console_command(command)

        if not success or not stdout:
            return None

        # 解析 Console 输出
        result = {}
        lines = stdout.strip().split('\n')
        for line in lines:
            line = line.strip()
            if '=' in line and not line.startswith('JsonTransactionResponse'):
                # 处理 key=value 格式
                if line.endswith(','):
                    line = line[:-1]
                parts = line.split('=', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().strip("'")
                    result[key] = value

        return result if result else None

    def get_block_by_number(self, block_number: int) -> Optional[Dict]:
        """
        通过区块号获取区块详情（使用 Console）
        """
        command = f'getBlockByNumber {block_number}'
        success, stdout, stderr = self._run_console_command(command)

        if not success or not stdout:
            return None

        # 解析关键字段
        result = {
            "number": block_number,
            "transactions": []
        }

        lines = stdout.strip().split('\n')
        for line in lines:
            line = line.strip()
            # 解析 hash
            if line.startswith("hash='"):
                result["hash"] = line.split("'")[1]
            # 解析 timestamp
            elif line.startswith("timestamp='"):
                result["timestamp"] = line.split("'")[1]
            # 解析 sealer
            elif line.startswith("sealer='"):
                result["sealer"] = line.split("'")[1]
            # 解析 gasUsed
            elif line.startswith("gasUsed='"):
                result["gasUsed"] = line.split("'")[1]
            # 统计交易数量
            elif "JsonTransactionResponse{" in line:
                result["transactions"].append({})

        return result if result.get("hash") else None

    def get_chain_info(self) -> Dict:
        """
        获取链的基本信息
        """
        block_number = self.get_block_number()
        product_count = self.get_product_count()

        return {
            "block_number": block_number,
            "product_count": product_count,
            "rpc_url": self.rpc_url,
            "contract_address": self.contract_address,
            "connected": self.is_connected()
        }

    def get_product_records_from_chain(self, trace_code: str) -> Optional[list]:
        """
        从链上获取产品的所有记录
        """
        command = f'call AgriTrace {self.contract_address} getRecordCount "{trace_code}"'
        success, stdout, stderr = self._run_console_command(command)

        if not success:
            return None

        parsed = self._parse_console_output(stdout)
        if not parsed["return_values"]:
            return None

        try:
            count = int(parsed["return_values"].strip("()"))
        except:
            return None

        records = []
        for i in range(count):
            command = f'call AgriTrace {self.contract_address} getRecord "{trace_code}" {i}'
            success, stdout, stderr = self._run_console_command(command)
            if success:
                parsed = self._parse_console_output(stdout)
                if parsed["return_values"]:
                    records.append({
                        "index": i,
                        "raw": parsed["return_values"]
                    })

        return records

    def get_product_records_rpc(self, trace_code: str) -> Optional[List[Dict]]:
        """
        通过 RPC 获取产品的所有记录（正确解码 UTF-8 中文）

        返回格式:
        [
            {
                "recordId": 1,
                "stage": 0,
                "action": 0,
                "data": "数据",
                "remark": "备注",
                "operator": "0x...",
                "operatorName": "操作人",
                "timestamp": 1234567890,
                "previousRecordId": 0,
                "amendReason": ""
            },
            ...
        ]
        """
        # 1. 获取记录数量
        count_result = self._call_contract_rpc(
            function_signature="getRecordCount(string)",
            input_types=["string"],
            input_values=[trace_code],
            output_types=["uint256"]
        )

        if not count_result or count_result[0] == 0:
            return []

        count = count_result[0]

        # 2. 逐个获取记录
        records = []
        for i in range(count):
            # getRecord(string,uint256) returns (uint256, uint8, uint8, string, string, address, string, uint256, uint256, string)
            record_result = self._call_contract_rpc(
                function_signature="getRecord(string,uint256)",
                input_types=["string", "uint256"],
                input_values=[trace_code, i],
                output_types=["uint256", "uint8", "uint8", "string", "string", "address", "string", "uint256", "uint256", "string"]
            )

            if record_result and len(record_result) == 10:
                records.append({
                    "index": i,
                    "recordId": record_result[0],
                    "stage": record_result[1],
                    "action": record_result[2],
                    "data": record_result[3],
                    "remark": record_result[4],
                    "operator": record_result[5],
                    "operatorName": record_result[6],
                    "timestamp": record_result[7],
                    "previousRecordId": record_result[8],
                    "amendReason": record_result[9]
                })

        return records


# 单例实例
blockchain_client = FiscoBcosClient()
