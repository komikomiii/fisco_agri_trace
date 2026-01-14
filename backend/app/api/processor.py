"""
Processor (加工商) API
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.database import get_db
from app.models.user import User, UserRole
from app.models.product import Product, ProductRecord, ProductStatus, ProductStage, RecordAction
from app.api.auth import get_current_user
from app.blockchain import blockchain_client

# 区块链操作线程池（避免阻塞事件循环）
blockchain_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="blockchain_")

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
    auto_send_inspect: Optional[bool] = None  # 是否自动送检（用于重新加工场景）


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
    - 公共池产品 或 指定给当前加工商的产品
    """
    check_processor_role(current_user)

    # 查询所有已上链（或正在同步中）且在原料商阶段的产品
    products = db.query(Product).filter(
        Product.status.in_([ProductStatus.ON_CHAIN, ProductStatus.PENDING_CHAIN]),
        Product.current_stage == ProductStage.PRODUCER,
        or_(
            Product.distribution_type == "pool",
            Product.distribution_type.is_(None),
            Product.assigned_processor_id == current_user.id
        )
    ).order_by(Product.created_at.desc()).all()

    # 手动序列化
    result = []
    for p in products:
        # 获取创建者信息
        creator = db.query(User).filter(User.id == p.creator_id).first()

        # 判断是公共池还是指定发送
        is_assigned = (p.distribution_type == "assigned" and p.assigned_processor_id == current_user.id)

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
            "distribution_type": p.distribution_type or "pool",
            "is_assigned_to_me": is_assigned,  # 是否指定给当前用户
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


def background_receive_product(product_id: int, user_id: int, user_address: str, operator_name: str, chain_data_str: str, quality: str):
    """后台处理原料接收"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return

        success, tx_hash, block_number = blockchain_client.transfer_product(
            trace_code=product.trace_code,
            new_holder=user_address,
            new_stage="processor",
            data=chain_data_str,
            remark=f"接收质检等级: {quality}",
            operator_name=operator_name
        )

        if success:
            product.current_holder_id = user_id
            product.current_stage = ProductStage.PROCESSOR
            product.status = ProductStatus.ON_CHAIN
            product.tx_hash = tx_hash
            product.block_number = block_number
            product.updated_at = datetime.now()

            record = ProductRecord(
                product_id=product.id,
                stage=ProductStage.PROCESSOR,
                action=RecordAction.RECEIVE,
                data=chain_data_str,
                remark=f"接收原料",
                operator_id=user_id,
                operator_name=operator_name,
                tx_hash=tx_hash,
                block_number=block_number
            )
            db.add(record)
            db.commit()
        else:
            product.status = ProductStatus.CHAIN_FAILED
            db.commit()
            print(f"❌ Background receive failed for product {product_id}")
    except Exception as e:
        print(f"❌ Background receive error: {e}")
        db.rollback()
    finally:
        db.close()


@router.post("/products/{product_id}/receive")
async def receive_product(
    product_id: int,
    receive_data: ReceiveRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """接收原料 (异步)"""
    check_processor_role(current_user)

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    if product.status != ProductStatus.ON_CHAIN:
        raise HTTPException(status_code=400, detail="产品未上链，无法接收")

    if product.current_stage != ProductStage.PRODUCER:
        raise HTTPException(status_code=400, detail="产品不在原料商阶段")

    # 预先确保地址
    if not current_user.blockchain_address:
        from app.blockchain.wallet import wallet_manager
        account = wallet_manager.ensure_user_account(current_user.id, current_user.username)
        current_user.blockchain_address = account["address"]
        db.commit()

    chain_data_str = json.dumps({
        "received_quantity": receive_data.received_quantity,
        "quality": receive_data.quality,
        "notes": receive_data.notes,
        "received_at": datetime.now().isoformat()
    }, default=str, ensure_ascii=False)

    # 设置状态为正在处理
    product.status = ProductStatus.PENDING_CHAIN
    db.commit()

    # 提交异步任务
    background_tasks.add_task(
        background_receive_product,
        product.id,
        current_user.id,
        current_user.blockchain_address,
        current_user.real_name or current_user.username,
        chain_data_str,
        receive_data.quality
    )

    return {"message": "接收请求已提交"}


def background_process_product(product_id: int, user_id: int, operator_name: str, chain_data_str: str, result_product: str, result_quantity: float, auto_send: bool):
    """后台处理加工"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product: return

        success, tx_hash, block_number = blockchain_client.add_record(
            trace_code=product.trace_code,
            stage=1, action=1, data=chain_data_str,
            remark=f"加工: {result_product}",
            operator_name=operator_name
        )

        if success:
            product.name = result_product
            product.quantity = result_quantity
            product.status = ProductStatus.ON_CHAIN
            product.tx_hash = tx_hash
            product.block_number = block_number
            product.updated_at = datetime.now()

            record = ProductRecord(
                product_id=product.id, stage=ProductStage.PROCESSOR, action=RecordAction.PROCESS,
                data=chain_data_str, remark=f"加工完成: {result_product}",
                operator_id=user_id, operator_name=operator_name,
                tx_hash=tx_hash, block_number=block_number
            )
            db.add(record)
            db.commit()

            if auto_send:
                background_send_inspect(product.id, user_id, operator_name, db)
        else:
            product.status = ProductStatus.CHAIN_FAILED
            db.commit()
    except Exception as e:
        print(f"❌ Background process error: {e}")
        db.rollback()
    finally:
        db.close()

def background_send_inspect(product_id: int, user_id: int, operator_name: str, db: Session = None):
    """后台处理送检逻辑"""
    is_internal_session = False
    if db is None:
        from app.database import SessionLocal
        db = SessionLocal()
        is_internal_session = True
        
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        inspector = db.query(User).filter(User.role == UserRole.INSPECTOR).first()
        if not product or not inspector: 
            if is_internal_session: db.close()
            return

        send_data = {"inspection_type": "quality", "send_date": datetime.now().isoformat()}
        s_success, s_tx, s_bn = blockchain_client.add_record(
            trace_code=product.trace_code, stage=1, action=2, 
            data=json.dumps(send_data), remark="送检: 质量检测", operator_name=operator_name
        )

        if s_success:
            t_success, t_tx, t_bn = blockchain_client.transfer_product(
                trace_code=product.trace_code, 
                new_holder=inspector.blockchain_address or inspector.username,
                new_stage="inspector", data=json.dumps({"action": "send_inspect"}),
                remark="加工商送检", operator_name=operator_name
            )
            if t_success:
                product.current_stage = ProductStage.INSPECTOR
                product.current_holder_id = inspector.id
                product.status = ProductStatus.ON_CHAIN
                product.tx_hash = t_tx
                product.block_number = t_bn
                db.add(ProductRecord(
                    product_id=product.id, stage=ProductStage.PROCESSOR, action=RecordAction.SEND_INSPECT,
                    data=json.dumps(send_data), remark="送检: 质量检测",
                    operator_id=user_id, operator_name=operator_name, tx_hash=t_tx, block_number=t_bn
                ))
                db.commit()
            else:
                product.status = ProductStatus.CHAIN_FAILED
                db.commit()
        else:
            product.status = ProductStatus.CHAIN_FAILED
            db.commit()
    except Exception as e:
        print(f"❌ Background send inspect error: {e}")
        db.rollback()
    finally:
        if is_internal_session:
            db.close()

@router.post("/products/{product_id}/process")
async def process_product(
    product_id: int,
    process_data: ProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """加工处理 (异步)"""
    check_processor_role(current_user)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product: raise HTTPException(status_code=404, detail="产品不存在")
    if product.current_stage != ProductStage.PROCESSOR: raise HTTPException(status_code=400, detail="产品不在加工商阶段")
    if product.current_holder_id != current_user.id: raise HTTPException(status_code=403, detail="非当前持有者")

    chain_data_str = json.dumps({
        "process_type": process_data.process_type,
        "result_product": process_data.result_product,
        "result_quantity": process_data.result_quantity,
        "process_date": process_data.process_date.isoformat() if process_data.process_date else datetime.now().isoformat(),
        "notes": process_data.notes
    }, default=str, ensure_ascii=False)

    auto_send = process_data.auto_send_inspect
    if auto_send is None:
        has_reject = db.query(ProductRecord).filter(ProductRecord.product_id == product.id, ProductRecord.action == RecordAction.REJECT).first()
        auto_send = has_reject is not None

    background_tasks.add_task(
        background_process_product,
        product.id, current_user.id, current_user.real_name or current_user.username,
        chain_data_str, process_data.result_product, process_data.result_quantity, auto_send
    )
    product.status = ProductStatus.PENDING_CHAIN
    db.commit()
    return {"message": "加工处理请求已提交"}

@router.post("/products/{product_id}/send-inspect")
async def send_inspect_product(
    product_id: int,
    inspect_data: SendInspectRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动送检 (异步)"""
    check_processor_role(current_user)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product: raise HTTPException(status_code=404, detail="产品不存在")
    if product.current_stage != ProductStage.PROCESSOR or product.current_holder_id != current_user.id:
        raise HTTPException(status_code=400, detail="无权操作或阶段错误")

    background_tasks.add_task(
        background_send_inspect,
        product.id, current_user.id, current_user.real_name or current_user.username
    )
    product.status = ProductStatus.PENDING_CHAIN
    db.commit()
    return {"message": "送检请求已提交"}


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
                "status": p.status if p.status == ProductStatus.PENDING_CHAIN else "pending"
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
    - 有加工记录
    - 且最近的加工记录在最近的送检记录之后（或没有送检记录）
    """
    check_processor_role(current_user)

    # 获取已接收的产品
    products = db.query(Product).filter(
        Product.current_holder_id == current_user.id,
        Product.current_stage == ProductStage.PROCESSOR
    ).all()

    # 筛选出有加工记录且未送检（或重新加工后未送检）的产品
    result = []
    for p in products:
        # 获取最近的加工记录
        latest_process_record = db.query(ProductRecord).filter(
            ProductRecord.product_id == p.id,
            ProductRecord.action == RecordAction.PROCESS
        ).order_by(ProductRecord.created_at.desc()).first()

        if not latest_process_record:
            continue

        # 获取最近的送检记录
        latest_send_inspect_record = db.query(ProductRecord).filter(
            ProductRecord.product_id == p.id,
            ProductRecord.action == RecordAction.SEND_INSPECT
        ).order_by(ProductRecord.created_at.desc()).first()

        # 如果有送检记录，检查最近的加工是否在送检之后（重新加工的情况）
        if latest_send_inspect_record:
            if latest_process_record.created_at <= latest_send_inspect_record.created_at:
                # 最近的加工在送检之前，说明还没有重新加工
                continue

        # 从记录数据中获取加工信息
        record_data = latest_process_record.data if isinstance(latest_process_record.data, dict) else json.loads(latest_process_record.data) if latest_process_record.data else {}

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
            "status": p.status if p.status == ProductStatus.PENDING_CHAIN else "processing"
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
                "status": p.status if p.status == ProductStatus.PENDING_CHAIN else "sent"
            })

    return result


@router.get("/products/rejected")
async def list_rejected_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取被退回的产品列表
    - 当前持有者为当前用户
    - 当前阶段为加工商 (PROCESSOR)
    - 有退回记录
    - 且退回后没有新的加工记录（未重新加工）
    """
    check_processor_role(current_user)

    # 查询当前持有且有退回记录的产品
    products = db.query(Product).filter(
        Product.current_holder_id == current_user.id,
        Product.current_stage == ProductStage.PROCESSOR
    ).all()

    result = []
    for p in products:
        # 检查是否有退回记录
        reject_record = db.query(ProductRecord).filter(
            ProductRecord.product_id == p.id,
            ProductRecord.action == RecordAction.REJECT
        ).order_by(ProductRecord.created_at.desc()).first()

        if reject_record:
            # 检查退回后是否有新的加工记录（重新加工过）
            reprocess_record = db.query(ProductRecord).filter(
                ProductRecord.product_id == p.id,
                ProductRecord.action == RecordAction.PROCESS,
                ProductRecord.created_at > reject_record.created_at
            ).first()

            # 如果已经重新加工过，跳过这个产品
            if reprocess_record:
                continue

            # 解析退回信息
            reject_data = {}
            if reject_record.data:
                try:
                    reject_data = json.loads(reject_record.data) if isinstance(reject_record.data, str) else reject_record.data
                except:
                    reject_data = {}

            result.append({
                "id": p.id,
                "trace_code": p.trace_code,
                "name": p.name,
                "category": p.category,
                "quantity": p.quantity,
                "unit": p.unit,
                "reject_reason": reject_data.get("reason", reject_record.remark or ""),
                "reject_issues": reject_data.get("issues", ""),
                "rejected_at": reject_record.created_at.isoformat() if reject_record.created_at else None,
                "rejected_by": reject_record.operator_name,
                "status": "rejected"
            })

    return result


@router.get("/products/invalidated")
async def list_invalidated_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取已作废的产品列表（当前用户参与过的）
    """
    check_processor_role(current_user)

    # 查询当前用户参与过的已作废产品
    # 通过 ProductRecord 找出当前用户操作过的产品
    operated_product_ids = db.query(ProductRecord.product_id).filter(
        ProductRecord.operator_id == current_user.id
    ).distinct().all()

    product_ids = [p[0] for p in operated_product_ids]

    if not product_ids:
        return []

    # 查询这些产品中已作废的
    products = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.status == ProductStatus.INVALIDATED
    ).order_by(Product.invalidated_at.desc()).all()

    result = []
    for p in products:
        # 获取作废操作人
        invalidator = None
        if p.invalidated_by:
            invalidator = db.query(User).filter(User.id == p.invalidated_by).first()

        result.append({
            "id": p.id,
            "trace_code": p.trace_code,
            "name": p.name,
            "category": p.category,
            "quantity": p.quantity,
            "unit": p.unit,
            "invalidated_at": p.invalidated_at.isoformat() if p.invalidated_at else None,
            "invalidated_reason": p.invalidated_reason,
            "invalidated_by": invalidator.real_name if invalidator else None,
            "status": "invalidated"
        })

    return result
