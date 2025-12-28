"""
Blockchain API - 区块链查询接口
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

from app.blockchain import blockchain_client

router = APIRouter(prefix="/blockchain", tags=["区块链"])


class ChainInfoResponse(BaseModel):
    """链信息响应"""
    block_number: int
    product_count: int
    rpc_url: str
    contract_address: str
    connected: bool


class TransactionResponse(BaseModel):
    """交易详情响应"""
    tx_hash: str
    block_number: Optional[int] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    input: Optional[str] = None
    timestamp: Optional[str] = None
    status: Optional[str] = None


class BlockResponse(BaseModel):
    """区块详情响应"""
    block_number: int
    block_hash: Optional[str] = None
    timestamp: Optional[str] = None
    transaction_count: int = 0
    sealer: Optional[str] = None


class VerifyResponse(BaseModel):
    """验证响应"""
    trace_code: str
    exists: bool
    on_chain: bool
    product_info: Optional[dict] = None


@router.get("/info", response_model=ChainInfoResponse)
async def get_chain_info():
    """
    获取区块链基本信息
    - 当前区块高度
    - 链上产品总数
    - 连接状态
    """
    try:
        info = blockchain_client.get_chain_info()
        return ChainInfoResponse(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取链信息失败: {str(e)}")


@router.get("/transaction/{tx_hash}")
async def get_transaction(tx_hash: str):
    """
    通过交易哈希查询交易详情
    """
    if not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash

    try:
        # 获取交易详情（使用 Console）
        tx = blockchain_client.get_transaction_by_hash(tx_hash)
        if not tx:
            raise HTTPException(status_code=404, detail="交易不存在")

        # 获取交易回执
        receipt = blockchain_client.get_transaction_receipt(tx_hash)

        # Console 返回的字段名是小驼峰格式
        input_data = tx.get("input", "")
        if input_data and len(input_data) > 200:
            input_data = input_data[:200] + "..."

        return {
            "tx_hash": tx.get("hash", tx_hash),
            "block_number": tx.get("blockLimit"),  # Console 返回 blockLimit
            "from_address": tx.get("from"),
            "to_address": tx.get("to"),
            "input": input_data,
            "status": receipt.get("status") if receipt else "0x0",  # 默认成功
            "gas_used": receipt.get("gasUsed") if receipt else None,
            "contract_address": tx.get("to"),
            "chain_id": tx.get("chainID"),
            "group_id": tx.get("groupID"),
            "import_time": tx.get("importTime"),
            "raw_transaction": tx,
            "raw_receipt": receipt
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询交易失败: {str(e)}")


@router.get("/block/{block_number}")
async def get_block(block_number: int):
    """
    通过区块号查询区块详情
    """
    try:
        block = blockchain_client.get_block_by_number(block_number)
        if not block:
            raise HTTPException(status_code=404, detail="区块不存在")

        return {
            "block_number": block_number,
            "block_hash": block.get("hash"),
            "parent_hash": block.get("parentHash"),
            "timestamp": block.get("timestamp"),
            "sealer": block.get("sealer"),
            "transaction_count": len(block.get("transactions", [])),
            "transactions": block.get("transactions", []),
            "raw_block": block
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询区块失败: {str(e)}")


@router.get("/verify/{trace_code}", response_model=VerifyResponse)
async def verify_trace_code(trace_code: str):
    """
    验证溯源码是否在链上存在
    """
    try:
        exists = blockchain_client.verify_trace_code(trace_code)

        product_info = None
        if exists:
            product_info = blockchain_client.get_product(trace_code)

        return VerifyResponse(
            trace_code=trace_code,
            exists=exists,
            on_chain=exists,
            product_info=product_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证失败: {str(e)}")


@router.get("/product/{trace_code}/chain-data")
async def get_product_chain_data(trace_code: str):
    """
    获取产品的链上原始数据（使用RPC直接调用，正确解码UTF-8中文）

    如果RPC调用失败，回退到数据库查询（数据已通过上链接口写入数据库）
    """
    from app.database import get_db
    from app.models.product import Product, ProductRecord
    from app.models.user import User
    from sqlalchemy.orm import Session

    # 获取数据库会话
    db = next(get_db())

    try:
        # 尝试使用 RPC 获取产品信息
        product_info = blockchain_client.get_product_rpc(trace_code)

        # 如果 RPC 失败，从数据库获取
        if not product_info:
            product = db.query(Product).filter(Product.trace_code == trace_code).first()
            if not product:
                raise HTTPException(status_code=404, detail="溯源码不存在")

            # 获取创建者和持有者的真实地址
            creator = db.query(User).filter(User.id == product.creator_id).first()
            holder = db.query(User).filter(User.id == product.current_holder_id).first()

            product_info = {
                "name": product.name or "",
                "category": product.category or "",
                "origin": product.origin or "",
                "quantity": int((product.quantity or 0) * 1000),  # 转换为整数
                "unit": product.unit or "",
                "currentStage": product.current_stage.value if product.current_stage else 0,
                "status": product.status.value if product.status else 0,
                "creator": creator.blockchain_address if creator and creator.blockchain_address else "0x0000000000000000000000000000000000000000",
                "currentHolder": holder.blockchain_address if holder and holder.blockchain_address else "0x0000000000000000000000000000000000000000",
                "createdAt": int(product.created_at.timestamp()),
                "recordCountNum": db.query(ProductRecord).filter(ProductRecord.product_id == product.id).count()
            }

        # 尝试使用 RPC 获取记录
        records = blockchain_client.get_product_records_rpc(trace_code)

        # 如果 RPC 失败，从数据库获取
        if not records:
            product = db.query(Product).filter(Product.trace_code == trace_code).first()
            if product:
                db_records = db.query(ProductRecord).filter(
                    ProductRecord.product_id == product.id
                ).order_by(ProductRecord.created_at.asc()).all()

                records = []
                for i, record in enumerate(db_records):
                    # 获取操作者的真实地址
                    operator = db.query(User).filter(User.id == record.operator_id).first()
                    operator_address = operator.blockchain_address if operator and operator.blockchain_address else "0x0000000000000000000000000000000000000000"

                    records.append({
                        "index": i,
                        "recordId": record.id,
                        "stage": record.stage.value if record.stage else 0,
                        "action": record.action.value if record.action else 0,
                        "data": record.data or "",
                        "remark": record.remark or "",
                        "operator": operator_address,
                        "operatorName": record.operator_name or "",
                        "timestamp": int(record.created_at.timestamp()),
                        "previousRecordId": record.previous_record_id or 0,
                        "amendReason": record.amend_reason or ""
                    })

        return {
            "trace_code": trace_code,
            "exists": True,
            "product_info": product_info,
            "chain_records": records,
            "record_count": len(records) if records else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取链上数据失败: {str(e)}")
    finally:
        db.close()


@router.get("/health")
async def blockchain_health():
    """
    检查区块链连接健康状态
    """
    try:
        connected = blockchain_client.is_connected()
        block_number = blockchain_client.get_block_number() if connected else 0

        return {
            "status": "healthy" if connected else "disconnected",
            "connected": connected,
            "block_number": block_number,
            "rpc_url": blockchain_client.rpc_url,
            "contract_address": blockchain_client.contract_address
        }
    except Exception as e:
        return {
            "status": "error",
            "connected": False,
            "error": str(e)
        }
