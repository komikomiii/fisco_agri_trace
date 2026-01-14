"""
FISCO BCOS 区块链客户端
混合模式：使用 RPC 进行快速查询，使用 Console 进行合约写入操作
"""
import json
import subprocess
import os
import time
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
        # 记录是否已经清理过 PEM
        self._pem_cleaned = False

    def _clean_problematic_pem_files(self):
        """
        清除 Console 自动生成的有问题的 PEM 文件
        """
        if self._pem_cleaned:
            return
        
        import glob
        ecdsa_dir = os.path.join("/home/pdm/fisco/console/account", "ecdsa")
        pattern = os.path.join(ecdsa_dir, "0x0000000000000000000000000000000000000*.pem")
        try:
            for pem_file in glob.glob(pattern):
                try:
                    os.remove(pem_file)
                    pub_file = pem_file + ".pub"
                    if os.path.exists(pub_file):
                        os.remove(pub_file)
                except:
                    pass
            self._pem_cleaned = True
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
        """获取当前区块高度 (使用 Console)"""
        success, stdout, stderr = self._run_console_command("getBlockNumber")
        if success and stdout:
            # Console 输出格式: 数字
            for line in stdout.strip().split("\n"):
                line = line.strip()
                if line.isdigit():
                    return int(line)
        return 0

    def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict]:
        """获取交易回执 (使用 Console)"""
        success, stdout, stderr = self._run_console_command(f"getTransactionReceipt {tx_hash}")
        if success and stdout:
            return self._parse_console_json_output(stdout)
        return None

    def get_transaction_by_hash(self, tx_hash: str) -> Optional[Dict]:
        """通过交易哈希获取交易详情 (使用 Console)"""
        success, stdout, stderr = self._run_console_command(f"getTransactionByHash {tx_hash}")
        if success and stdout:
            return self._parse_console_json_output(stdout)
        return None

    def get_block_by_number(self, block_number: int) -> Optional[Dict]:
        """通过区块号获取区块详情 (使用 Console)"""
        success, stdout, stderr = self._run_console_command(f"getBlockByNumber {block_number}")
        if success and stdout:
            return self._parse_console_json_output(stdout)
        return None

    def _run_console_command(self, command: str) -> Tuple[bool, str, str]:
        """执行 Console 命令"""
        self._clean_problematic_pem_files()
        try:
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

    def _parse_console_json_output(self, output: str) -> Optional[Dict]:
        """解析 Console 输出的 JSON 格式数据"""
        import re
        try:
            output = output.strip()

            # 查找 JSON 对象的开始
            if output.startswith("{"):
                try:
                    return json.loads(output)
                except:
                    pass

            # 解析 Java 风格的输出
            result = {}

            # 提取关键字段
            if "hash=" in output or "hash'" in output:
                match = re.search(r"hash='([^']+)'", output)
                if match:
                    result["hash"] = match.group(1)

            if "from=" in output:
                match = re.search(r"from='([^']*)'", output)
                if match:
                    result["from"] = match.group(1)

            if "to=" in output:
                match = re.search(r"to='([^']*)'", output)
                if match:
                    result["to"] = match.group(1)

            if "blockNumber=" in output:
                match = re.search(r"blockNumber=(\d+)", output)
                if match:
                    result["blockNumber"] = int(match.group(1))

            # 区块的 number 字段 (带引号)
            if "number=" in output:
                match = re.search(r"number='(\d+)'", output)
                if match:
                    result["number"] = int(match.group(1))

            if "timestamp=" in output:
                # 支持 timestamp='1766920466216' 或 timestamp=1766920466216 格式
                match = re.search(r"timestamp='?(\d+)'?", output)
                if match:
                    result["timestamp"] = int(match.group(1))

            if "sealer=" in output:
                match = re.search(r"sealer='([^']*)'", output)
                if match:
                    result["sealer"] = match.group(1)

            if "parentHash=" in output:
                match = re.search(r"parentHash='([^']*)'", output)
                if match:
                    result["parentHash"] = match.group(1)

            # 提取交易列表
            if "transactions=" in output:
                # 统计 JsonTransactionResponse 的数量
                tx_matches = re.findall(r"JsonTransactionResponse\{", output)
                result["transactions"] = ["tx"] * len(tx_matches) if tx_matches else []

            if "input=" in output:
                match = re.search(r"input='([^']*)'", output)
                if match:
                    result["input"] = match.group(1)

            if "status=" in output:
                match = re.search(r"status=(\d+)", output)
                if match:
                    result["status"] = int(match.group(1))

            if "gasUsed=" in output:
                match = re.search(r"gasUsed='?(\d+)'?", output)
                if match:
                    result["gasUsed"] = match.group(1)

            return result if result else None
        except Exception as e:
            print(f"Parse console output error: {e}")
            return None

    def _parse_console_output(self, output: str) -> Dict[str, Any]:
        """解析 Console 输出"""
        result = {"success": False, "tx_hash": None, "block_number": None, "return_values": None}
        lines = output.split("\n")
        for line in lines:
            line = line.strip()
            if "transaction hash:" in line:
                result["tx_hash"] = line.split(":", 1)[1].strip()
                result["success"] = True
            elif "Return code: 0" in line:
                result["success"] = True
            elif "Return values:" in line:
                result["return_values"] = line.split(":", 1)[1].strip()
            elif "blockNumber" in line:
                try:
                    # blockNumber: 123
                    parts = line.split(":")
                    if len(parts) > 1:
                        val = parts[1].strip().strip(",").strip("'")
                        result["block_number"] = int(val, 16) if val.startswith("0x") else int(val)
                except:
                    pass
        return result

    def _wait_for_transaction_rpc(self, tx_hash: str, timeout: int = 10) -> Optional[int]:
        """使用 RPC 轮询等待交易上链 (快速)"""
        start = time.time()
        while time.time() - start < timeout:
            receipt = self.get_transaction_receipt(tx_hash)
            if receipt:
                status = receipt.get("status")
                if status == 0 or status == "0x0" or status == "0":
                    bn = receipt.get("blockNumber")
                    return int(bn, 16) if isinstance(bn, str) and bn.startswith("0x") else int(bn)
            time.sleep(1)
        return self.get_block_number()

    # ==================== 合约写入方法 (使用 Console) ====================

    def _execute_write(self, command: str) -> Tuple[bool, Optional[str], Optional[int]]:
        """通用写入执行逻辑"""
        success, stdout, stderr = self._run_console_command(command)
        if not success:
            print(f"Console error: {stderr}")
            return False, None, None
        
        parsed = self._parse_console_output(stdout)
        if parsed["success"] and parsed["tx_hash"]:
            tx_hash = parsed["tx_hash"]
            # 这里的优化：缩短等待时间，甚至不等待
            # 我们等待最多 3 秒，如果没出来也返回，让前端轮询
            block_number = self._wait_for_transaction_rpc(tx_hash, timeout=3)
            return True, tx_hash, block_number
        
        return False, None, None

    def create_product(self, trace_code: str, name: str, category: str, origin: str, quantity: int, unit: str, data: str, operator_name: str) -> Tuple[bool, Optional[str], Optional[int]]:
        escaped_data = data.replace('"', '\\"')
        command = f'call AgriTrace {self.contract_address} createProduct "{trace_code}" "{name}" "{category}" "{origin}" {quantity} "{unit}" "{escaped_data}" "{operator_name}"'
        return self._execute_write(command)

    def add_amend_record(self, trace_code: str, stage: int, data: str, remark: str, operator_name: str, previous_record_id: int, amend_reason: str) -> Tuple[bool, Optional[str], Optional[int]]:
        escaped_data = data.replace('"', '\\"')
        escaped_remark = remark.replace('"', '\\"')
        escaped_reason = amend_reason.replace('"', '\\"')
        command = f'call AgriTrace {self.contract_address} addAmendRecord "{trace_code}" {stage} "{escaped_data}" "{escaped_remark}" "{operator_name}" {previous_record_id} "{escaped_reason}"'
        return self._execute_write(command)

    def add_record(self, trace_code: str, stage: int, action: int, data: str, remark: str, operator_name: str) -> Tuple[bool, Optional[str], Optional[int]]:
        escaped_data = data.replace('"', '\\"')
        escaped_remark = remark.replace('"', '\\"')
        command = f'call AgriTrace {self.contract_address} addRecord "{trace_code}" {stage} {action} "{escaped_data}" "{escaped_remark}" "{operator_name}"'
        return self._execute_write(command)

    def transfer_product(self, trace_code: str, new_holder: str, new_stage: str, data: str, remark: str, operator_name: str) -> Tuple[bool, Optional[str], Optional[int]]:
        escaped_data = data.replace('"', '\\"')
        escaped_remark = remark.replace('"', '\\"')
        stage_map = {"producer": 0, "processor": 1, "inspector": 2, "seller": 3, "sold": 4}
        stage_int = stage_map.get(new_stage, 1)
        command = f'call AgriTrace {self.contract_address} transferProduct "{trace_code}" "{new_holder}" {stage_int} "{escaped_data}" "{escaped_remark}" "{operator_name}"'
        return self._execute_write(command)

    # ==================== 合约查询方法 (使用 RPC, 极快) ====================

    def _call_contract_rpc(self, function_signature: str, input_types: List[str], input_values: List[Any], output_types: List[str]) -> Optional[List[Any]]:
        try:
            selector = function_signature_to_4byte_selector(function_signature)
            encoded_params = encode(input_types, input_values) if input_values else b''
            data = "0x" + (selector + encoded_params).hex()
            params = [self.group_id, {"from": "0x0000000000000000000000000000000000000000", "to": self.contract_address, "data": data}]
            result = self._rpc_call("call", params)
            if "result" in result and "output" in result["result"]:
                output_hex = result["result"]["output"]
                if output_hex and output_hex != "0x":
                    return list(decode(output_types, bytes.fromhex(output_hex[2:])))
            return None
        except Exception as e:
            print(f"RPC call error: {e}")
            return None

    def get_product_rpc(self, trace_code: str) -> Optional[Dict]:
        result = self._call_contract_rpc(
            "getProduct(string)", ["string"], [trace_code],
            ["string", "string", "string", "uint256", "string", "uint8", "uint8", "address", "address", "uint256", "uint256"]
        )
        if result and len(result) == 11:
            return {
                "name": result[0], "category": result[1], "origin": result[2], "quantity": result[3],
                "unit": result[4], "currentStage": result[5], "status": result[6], "creator": result[7],
                "currentHolder": result[8], "createdAt": result[9], "recordCountNum": result[10]
            }
        return None

    def get_product(self, trace_code: str) -> Optional[Dict]:
        return self.get_product_rpc(trace_code)

    def verify_trace_code(self, trace_code: str) -> bool:
        result = self._call_contract_rpc("verifyTraceCode(string)", ["string"], [trace_code], ["bool"])
        return result[0] if result else False

    def get_product_count(self) -> int:
        """获取链上产品总数 (使用 Console)"""
        import re
        command = f'call AgriTrace {self.contract_address} getProductCount'
        success, stdout, stderr = self._run_console_command(command)
        if success and stdout:
            # 解析 Return values:(27) 格式
            match = re.search(r'Return values:\((\d+)\)', stdout)
            if match:
                return int(match.group(1))
        return 0

    def is_connected(self) -> bool:
        return self.get_block_number() >= 0

    def get_chain_info(self) -> Dict:
        return {
            "block_number": self.get_block_number(), "product_count": self.get_product_count(),
            "rpc_url": self.rpc_url, "contract_address": self.contract_address, "connected": self.is_connected()
        }

    def get_product_records_rpc(self, trace_code: str) -> Optional[List[Dict]]:
        count_res = self._call_contract_rpc("getRecordCount(string)", ["string"], [trace_code], ["uint256"])
        if not count_res or count_res[0] == 0: return []
        records = []
        for i in range(count_res[0]):
            res = self._call_contract_rpc(
                "getRecord(string,uint256)", ["string", "uint256"], [trace_code, i],
                ["uint256", "uint8", "uint8", "string", "string", "address", "string", "uint256", "uint256", "string"]
            )
            if res:
                records.append({
                    "index": i, "recordId": res[0], "stage": res[1], "action": res[2], "data": res[3],
                    "remark": res[4], "operator": res[5], "operatorName": res[6], "timestamp": res[7],
                    "previousRecordId": res[8], "amendReason": res[9]
                })
        return records

# 单例实例
blockchain_client = FiscoBcosClient()
