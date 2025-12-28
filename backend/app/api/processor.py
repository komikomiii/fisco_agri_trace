"""
Processor (加工商) API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json

from app.database import get_db
from app.models.user import User, UserRole
from app.models.product import Product, ProductRecord, ProductStatus, ProductStage, RecordAction
from app.api.auth import get_current_user
from app.blockchain import blockchain_client

router = APIRouter(prefix="/processor", tags=["加工商"])

# 加工类型映射
PROCESS_TYPE_LABELS = {
    "wash": "清洗分拣",
    "cut": "切割加工",
    "juice": "榨汁加工",
    "pack": "包装封装",
    "freeze": "冷冻处理",
    "dry": "烘干处理"
}

# 质检类型映射
INSPECTION_TYPE_LABELS = {
    "quality": "质量检测",
    "safety": "安全检测",
    "appearance": "外观检测"
}

# Pydantic Models
class ReceiveRequest(BaseModel):
    """接收原料请求"""
    product_id: int
    received_quantity: float
    quality: str = "A"
    notes: Optional[str] = None


class ProcessRequest(BaseModel):
    """加工处理请求"""
    product_id: int
    process_type: str  # 加工类型
    result_product: str  # 加工后产品
    result_quantity: float  # 加工后数量
    process_date: Optional[datetime] = None
    notes: Optional[str] = None


class SendInspectRequest(BaseModel):
    """送检请求"""
    product_id: int
    inspection_type: str = "quality"  # 质检类型
    notes: Optional[str] = None


def check_processor_role(user: User):
    """检查是否为加工商角色"""
    if user.role != UserRole.PROCESSOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要加工商角色"
        )


@router.get("/products")
async def list_available_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取可接收的原料列表
    - 状态为已上链 (ON_CHAIN)
    - 当前阶段为原料商 (PRODUCER)
    """
    check_processor_role(current_user)

    # 查询所有已上链且在原料商阶段的产品
    products = db.query(Product).filter(
        Product.status == ProductStatus.ON_CHAIN,
        Product.current_stage == ProductStage.PRODUCER
    ).order_by(Product.created_at.desc()).all()

    # 手动序列化
    result = []
    for p in products:
        # 获取创建者信息
        creator = db.query(User).filter(User.id == p.creator_id).first()
        result.append({
            "id": p.id,
            "trace_code": p.trace_code,
            "name": p.name,
            "category": p.category,
            "origin": p.origin,
            "quantity": p.quantity,
            "unit": p.unit,
            "status": p.status.value,
            "current_stage": p.current_stage.value,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "creator_name": creator.real_name if creator else "-"
        })

    return result


@router.get("/products/received")
async def list_received_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取已接收的产品列表
    - 当前持有者为当前用户
    - 当前阶段为加工商 (PROCESSOR)
    """
    check_processor_role(current_user)

    products = db.query(Product).filter(
        Product.current_holder_id == current_user.id,
        Product.current_stage == ProductStage.PROCESSOR
    ).order_by(Product.updated_at.desc()).all()

    # 手动序列化
    result = []
    for p in products:
        result.append({
            "id": p.id,
            "trace_code": p.trace_code,
            "name": p.name,
            "category": p.category,
            "quantity": p.quantity,
            "unit": p.unit,
            "status": p.status.value,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        })

    return result


@router.post("/products/{product_id}/receive")
async def receive_product(
    product_id: int,
    receive_data: ReceiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    接收原料并上链

    流程:
    1. 验证产品存在且在正确阶段
    2. 调用智能合约 transferProduct 转移到加工商阶段
    3. 更新数据库中的 current_holder 和 current_stage
    4. 记录接收记录
    """
    check_processor_role(current_user)

    # 1. 查询产品
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    if product.status != ProductStatus.ON_CHAIN:
        raise HTTPException(status_code=400, detail="产品未上链，无法接收")

    if product.current_stage != ProductStage.PRODUCER:
        raise HTTPException(status_code=400, detail=f"产品不在原料商阶段，当前阶段: {product.current_stage.value}")

    # 2. 确保用户有区块链地址
    if not current_user.blockchain_address:
        from app.blockchain.wallet import wallet_manager
        account = wallet_manager.ensure_user_account(current_user.id, current_user.username)
        current_user.blockchain_address = account["address"]
        db.commit()

    # 3. 准备上链数据
    chain_data = {
        "received_quantity": receive_data.received_quantity,
        "quality": receive_data.quality,
        "notes": receive_data.notes,
        "received_at": datetime.now().isoformat()
    }

    # 4. 调用智能合约转移产品到加工商
    success, tx_hash, block_number = blockchain_client.transfer_product(
        trace_code=product.trace_code,
        new_holder=current_user.blockchain_address,
        new_stage="processor",  # PROCESSOR
        data=json.dumps(chain_data, default=str, ensure_ascii=False),
        remark=f"接收质检等级: {receive_data.quality}",
        operator_name=current_user.real_name or current_user.username
    )

    if not success:
        raise HTTPException(status_code=500, detail="区块链上链失败")

    # 4. 更新数据库
    product.current_holder_id = current_user.id
    product.current_stage = ProductStage.PROCESSOR
    product.tx_hash = tx_hash
    product.block_number = block_number
    product.updated_at = datetime.now()

    # 5. 创建接收记录
    record = ProductRecord(
        product_id=product.id,
        stage=ProductStage.PROCESSOR,
        action=RecordAction.RECEIVE,
        data=json.dumps(chain_data, default=str, ensure_ascii=False),
        remark=f"接收，质检等级: {receive_data.quality}",
        operator_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        tx_hash=tx_hash,
        block_number=block_number
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "原料接收成功",
        "product_id": product.id,
        "trace_code": product.trace_code,
        "tx_hash": tx_hash,
        "block_number": block_number,
        "record_id": record.id
    }


@router.post("/products/{product_id}/process")
async def process_product(
    product_id: int,
    process_data: ProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    加工处理并上链

    流程:
    1. 验证产品在加工商阶段且由当前用户持有
    2. 调用智能合约添加加工记录
    3. 更新数据库中的产品信息
    """
    check_processor_role(current_user)

    # 1. 查询产品
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    if product.current_stage != ProductStage.PROCESSOR:
        raise HTTPException(status_code=400, detail="产品不在加工商阶段")

    if product.current_holder_id != current_user.id:
        raise HTTPException(status_code=403, detail="您不是该产品的当前持有者")

    # 2. 准备上链数据
    chain_data = {
        "process_type": process_data.process_type,
        "result_product": process_data.result_product,
        "result_quantity": process_data.result_quantity,
        "process_date": process_data.process_date.isoformat() if process_data.process_date else datetime.now().isoformat(),
        "notes": process_data.notes
    }

    # 3. 调用智能合约添加加工记录
    success, tx_hash, block_number = blockchain_client.add_record(
        trace_code=product.trace_code,
        stage=1,  # ProductStage.PROCESSOR
        action=1,  # RecordAction.PROCESS
        data=json.dumps(chain_data, default=str, ensure_ascii=False),
        remark=f"加工: {process_data.process_type} → {process_data.result_product}",
        operator_name=current_user.real_name or current_user.username
    )

    if not success:
        raise HTTPException(status_code=500, detail="区块链上链失败")

    # 4. 更新产品信息 (加工后的信息)
    product.name = process_data.result_product
    product.quantity = process_data.result_quantity
    product.tx_hash = tx_hash
    product.block_number = block_number
    product.updated_at = datetime.now()

    # 5. 创建加工记录
    process_type_label = PROCESS_TYPE_LABELS.get(process_data.process_type, process_data.process_type)
    record = ProductRecord(
        product_id=product.id,
        stage=ProductStage.PROCESSOR,
        action=RecordAction.PROCESS,
        data=json.dumps(chain_data, default=str, ensure_ascii=False),
        remark=f"加工: {process_type_label} → {process_data.result_product}",
        operator_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        tx_hash=tx_hash,
        block_number=block_number
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "加工处理成功",
        "product_id": product.id,
        "trace_code": product.trace_code,
        "result_product": process_data.result_product,
        "result_quantity": process_data.result_quantity,
        "tx_hash": tx_hash,
        "block_number": block_number,
        "record_id": record.id
    }


@router.post("/products/{product_id}/send-inspect")
async def send_inspect_product(
    product_id: int,
    inspect_data: SendInspectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    送检 - 将加工后的产品发送给质检员
    1. 验证产品在加工商阶段且已加工
    2. 调用智能合约添加送检记录
    3. 更新产品状态为质检阶段
    """
    check_processor_role(current_user)

    # 1. 查询产品
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    if product.current_stage != ProductStage.PROCESSOR:
        raise HTTPException(status_code=400, detail="产品不在加工商阶段")

    if product.current_holder_id != current_user.id:
        raise HTTPException(status_code=403, detail="您不是该产品的当前持有者")

    # 2. 检查是否已加工
    has_process_record = db.query(ProductRecord).filter(
        ProductRecord.product_id == product.id,
        ProductRecord.action == RecordAction.PROCESS
    ).first()

    if not has_process_record:
        raise HTTPException(status_code=400, detail="产品尚未加工，无法送检")

    # 3. 检查是否已送检
    has_send_inspect_record = db.query(ProductRecord).filter(
        ProductRecord.product_id == product.id,
        ProductRecord.action == RecordAction.SEND_INSPECT
    ).first()

    if has_send_inspect_record:
        raise HTTPException(status_code=400, detail="产品已送检，请勿重复操作")

    # 4. 准备上链数据
    chain_data = {
        "inspection_type": inspect_data.inspection_type,
        "send_date": datetime.now().isoformat(),
        "notes": inspect_data.notes or "加工完成，请求质检"
    }

    # 5. 调用智能合约添加送检记录
    success, tx_hash, block_number = blockchain_client.add_record(
        trace_code=product.trace_code,
        stage=1,  # ProductStage.PROCESSOR
        action=2,  # RecordAction.SEND_INSPECT
        data=json.dumps(chain_data, default=str, ensure_ascii=False),
        remark=f"送检: {inspect_data.inspection_type}",
        operator_name=current_user.real_name or current_user.username
    )

    if not success:
        raise HTTPException(status_code=500, detail="区块链上链失败")

    # 6. 转移产品到质检阶段 (使用 transfer_product)
    # 查找第一个质检员作为目标
    inspector = db.query(User).filter(User.role == UserRole.INSPECTOR).first()
    if not inspector:
        raise HTTPException(status_code=500, detail="系统中没有质检员账号")

    transfer_data = {
        "action": "send_inspect",
        "from_processor": current_user.username,
        "to_inspector": inspector.username
    }

    transfer_success, transfer_tx_hash, transfer_block = blockchain_client.transfer_product(
        trace_code=product.trace_code,
        new_holder=inspector.blockchain_address or inspector.username,
        new_stage="inspector",
        data=json.dumps(transfer_data, ensure_ascii=False),
        remark=f"加工商送检",
        operator_name=current_user.real_name or current_user.username
    )

    if not transfer_success:
        raise HTTPException(status_code=500, detail="转移产品到质检阶段失败")

    # 7. 更新产品状态
    product.current_stage = ProductStage.INSPECTOR
    product.current_holder_id = inspector.id
    product.tx_hash = transfer_tx_hash
    product.block_number = transfer_block
    product.updated_at = datetime.now()

    # 8. 创建送检记录
    inspection_type_label = INSPECTION_TYPE_LABELS.get(inspect_data.inspection_type, inspect_data.inspection_type)
    record = ProductRecord(
        product_id=product.id,
        stage=ProductStage.PROCESSOR,
        action=RecordAction.SEND_INSPECT,
        data=json.dumps(chain_data, default=str, ensure_ascii=False),
        remark=f"送检: {inspection_type_label}",
        operator_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        tx_hash=transfer_tx_hash,
        block_number=transfer_block
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "送检成功",
        "product_id": product.id,
        "trace_code": product.trace_code,
        "inspector": inspector.username,
        "tx_hash": transfer_tx_hash,
        "block_number": transfer_block,
        "record_id": record.id
    }


@router.get("/products/{product_id}/records")
async def get_product_records(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取产品的流转记录"""
    check_processor_role(current_user)

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    records = db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id
    ).order_by(ProductRecord.created_at.asc()).all()

    # 手动序列化
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "stage": r.stage.value,
            "action": r.action.value,
            "data": r.data,
            "remark": r.remark,
            "operator_name": r.operator_name,
            "tx_hash": r.tx_hash,
            "block_number": r.block_number,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })

    return result


@router.get("/statistics")
async def get_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取加工商统计数据"""
    check_processor_role(current_user)

    total = db.query(Product).filter(
        Product.current_holder_id == current_user.id,
        Product.current_stage == ProductStage.PROCESSOR
    ).count()

    return {
        "in_processing": total,
        "total_received": total
    }


@router.get("/products/pending")
async def list_pending_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取待加工产品列表
    - 当前持有者为当前用户
    - 当前阶段为加工商
    - 没有加工记录
    """
    check_processor_role(current_user)

    # 获取已接收的产品
    products = db.query(Product).filter(
        Product.current_holder_id == current_user.id,
        Product.current_stage == ProductStage.PROCESSOR
    ).all()

    # 筛选出没有加工记录的产品
    result = []
    for p in products:
        # 检查是否有加工记录
        has_process_record = db.query(ProductRecord).filter(
            ProductRecord.product_id == p.id,
            ProductRecord.action == RecordAction.PROCESS
        ).first()

        if not has_process_record:
            result.append({
                "id": p.id,
                "trace_code": p.trace_code,
                "name": p.name,
                "category": p.category,
                "origin": p.origin,
                "quantity": p.quantity,
                "unit": p.unit,
                "status": "pending"
            })

    return result


@router.get("/products/processing")
async def list_processing_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取加工中产品列表
    - 当前持有者为当前用户
    - 当前阶段为加工商
    - 有加工记录但没有送检记录
    """
    check_processor_role(current_user)

    # 获取已接收的产品
    products = db.query(Product).filter(
        Product.current_holder_id == current_user.id,
        Product.current_stage == ProductStage.PROCESSOR
    ).all()

    # 筛选出有加工记录但没有送检记录的产品
    result = []
    for p in products:
        # 检查是否有加工记录
        process_record = db.query(ProductRecord).filter(
            ProductRecord.product_id == p.id,
            ProductRecord.action == RecordAction.PROCESS
        ).first()

        # 检查是否有送检记录
        has_inspect_record = db.query(ProductRecord).filter(
            ProductRecord.product_id == p.id,
            ProductRecord.action.in_([RecordAction.SEND_INSPECT, RecordAction.INSPECT])
        ).first()

        if process_record and not has_inspect_record:
            # 从记录数据中获取加工信息
            record_data = process_record.data if isinstance(process_record.data, dict) else json.loads(process_record.data) if process_record.data else {}

            result.append({
                "id": p.id,
                "trace_code": p.trace_code,
                "name": p.name,  # 现在是成品名称(已被更新)
                "category": p.category,
                "quantity": p.quantity,  # 现在是成品数量
                "unit": p.unit,
                "process_type": record_data.get("process_type", ""),
                "output_product": record_data.get("result_product", ""),
                "output_quantity": record_data.get("result_quantity", 0),
                "status": "processing"
            })

    return result


@router.get("/products/sent")
async def list_sent_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取已送检产品列表
    - 有加工记录
    - 有送检或检测记录
    - 查询加工商操作过的产品（包括已转走的）
    """
    check_processor_role(current_user)

    # 查询加工商操作过的产品（通过记录表）
    sent_product_ids = db.query(ProductRecord.product_id).filter(
        ProductRecord.operator_id == current_user.id,
        ProductRecord.action == RecordAction.SEND_INSPECT
    ).distinct().all()

    product_ids = [p[0] for p in sent_product_ids]

    if not product_ids:
        return []

    # 获取这些产品
    products = db.query(Product).filter(
        Product.id.in_(product_ids)
    ).all()

    # 筛选出已送检的产品
    result = []
    for p in products:
        # 检查是否有送检记录
        inspect_record = db.query(ProductRecord).filter(
            ProductRecord.product_id == p.id,
            ProductRecord.action.in_([RecordAction.SEND_INSPECT, RecordAction.INSPECT])
        ).first()

        if inspect_record:
            # 获取加工信息
            process_record = db.query(ProductRecord).filter(
                ProductRecord.product_id == p.id,
                ProductRecord.action == RecordAction.PROCESS
            ).first()

            record_data = {}
            if process_record:
                record_data = process_record.data if isinstance(process_record.data, dict) else json.loads(process_record.data) if process_record.data else {}

            result.append({
                "id": p.id,
                "trace_code": p.trace_code,
                "name": p.name,
                "category": p.category,
                "quantity": p.quantity,
                "unit": p.unit,
                "process_type": record_data.get("process_type", ""),
                "output_product": record_data.get("result_product", ""),
                "output_quantity": record_data.get("result_quantity", 0),
                "status": "sent"
            })

    return result
