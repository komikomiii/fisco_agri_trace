"""
修复链上数据中的零地址问题

当智能合约使用 msg.sender 时，链上地址是 Console 的零地址。
我们在查询返回时，将这些地址替换为数据库中记录的真实用户地址。
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.product import Product


def fix_product_addresses(product_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    修复产品数据中的地址

    将链上的零地址或 Console 地址替换为数据库中的真实用户地址

    Args:
        product_data: 从区块链获取的产品数据
        db: 数据库会话

    Returns:
        修复后的产品数据
    """
    # 获取溯源码
    trace_code = product_data.get("trace_code") or product_data.get("traceCode")

    if not trace_code:
        return product_data

    # 从数据库查询产品信息
    product = db.query(Product).filter(Product.trace_code == trace_code).first()
    if not product:
        return product_data

    # 获取创建者信息
    creator = db.query(User).filter(User.id == product.creator_id).first()

    # 获取持有者信息
    holder = db.query(User).filter(User.id == product.current_holder_id).first()

    # 替换零地址
    result = product_data.copy()

    # 替换 creator 地址
    if product_data.get("creator") == "0x0000000000000000000000000000000000000000":
        if creator and creator.blockchain_address:
            result["creator"] = creator.blockchain_address

    # 替换 currentHolder 地址
    if product_data.get("currentHolder") == "0x0000000000000000000000000000000000000000":
        if holder and holder.blockchain_address:
            result["currentHolder"] = holder.blockchain_address

    # 同样修复记录中的 operator 地址
    if "chain_records" in result:
        records = result["chain_records"]
        fixed_records = []

        for record in records:
            fixed_record = record.copy()

            # 如果 operator 是零地址，尝试从数据库查找
            if record.get("operator") == "0x0000000000000000000000000000000000000000":
                # 通过记录中的 operator_name 查找用户
                operator_name = record.get("operatorName")
                if operator_name:
                    operator = db.query(User).filter(
                        (User.real_name == operator_name) | (User.username == operator_name)
                    ).first()

                    if operator and operator.blockchain_address:
                        fixed_record["operator"] = operator.blockchain_address

            fixed_records.append(fixed_record)

        result["chain_records"] = fixed_records

    return result


def fix_record_address(record_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    修复单条记录中的地址

    Args:
        record_data: 记录数据
        db: 数据库会话

    Returns:
        修复后的记录数据
    """
    result = record_data.copy()

    # 如果 operator 是零地址，尝试通过 operator_name 查找
    if record_data.get("operator") == "0x0000000000000000000000000000000000000000":
        operator_name = record_data.get("operatorName")
        if operator_name:
            operator = db.query(User).filter(
                (User.real_name == operator_name) | (User.username == operator_name)
            ).first()

            if operator and operator.blockchain_address:
                result["operator"] = operator.blockchain_address

    return result
