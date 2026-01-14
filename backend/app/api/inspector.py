"""
Inspector (质检员) API
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
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

router = APIRouter(prefix="/inspector", tags=["质检员"])


# Pydantic Models
class StartInspectRequest(BaseModel):
    """开始检测请求"""
    product_id: int
    inspect_type: str = "quality"  # 质检类型
    notes: Optional[str] = None


class InspectRequest(BaseModel):
    """完成检测请求"""
    product_id: int
    qualified: bool  # 是否合格
    quality_grade: str = "A"  # 质量等级 A/B/C
    inspect_result: str  # 检测结果描述
    issues: Optional[str] = None  # 存在的问题
    notes: Optional[str] = None
    # 不合格处理参数
    unqualified_action: Optional[str] = "reject"  # reject=退回, invalidate=作废
    reject_to_stage: Optional[str] = "processor"  # 退回到哪个阶段: processor/producer
    reject_reason: Optional[str] = None  # 退回/作废原因


def check_inspector_role(user: User):
    """检查是否为质检员"""
    if user.role != UserRole.INSPECTOR:
        raise HTTPException(status_code=403, detail="只有质检员可以执行此操作")


@router.get("/products/pending")
async def list_pending_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取待检测产品列表
    - 产品当前阶段为 INSPECTOR
    - 还没有检测记录，或最近的送检记录在最近的检测记录之后（重新送检的情况）
    """
    check_inspector_role(current_user)

    # 查询当前为质检阶段的产品（不限制holder，因为送检后可能已经转移）
    products = db.query(Product).filter(
        Product.current_stage == ProductStage.INSPECTOR
    ).all()

    # 筛选出待检测的产品
    result = []
    for product in products:
        # 获取最近的送检记录
        latest_send_inspect = db.query(ProductRecord).filter(
            ProductRecord.product_id == product.id,
            ProductRecord.action == RecordAction.SEND_INSPECT
        ).order_by(ProductRecord.created_at.desc()).first()

        if not latest_send_inspect:
            continue

        # 获取最近的检测记录
        latest_inspect = db.query(ProductRecord).filter(
            ProductRecord.product_id == product.id,
            ProductRecord.action == RecordAction.INSPECT
        ).order_by(ProductRecord.created_at.desc()).first()

        # 获取最近的开始检测记录
        latest_start_inspect = db.query(ProductRecord).filter(
            ProductRecord.product_id == product.id,
            ProductRecord.action == RecordAction.START_INSPECT
        ).order_by(ProductRecord.created_at.desc()).first()

        # 判断是否待检测：
        # 1. 没有检测记录，且没有开始检测记录
        # 2. 或者最近的送检在最近的检测之后（重新送检的情况）
        is_pending = False

        if not latest_inspect and not latest_start_inspect:
            # 从未检测过
            is_pending = True
        elif latest_inspect:
            # 有检测记录，检查是否在送检之后重新送检了
            if latest_send_inspect.created_at > latest_inspect.created_at:
                # 重新送检了，需要检查是否有新的开始检测记录
                if not latest_start_inspect or latest_start_inspect.created_at < latest_send_inspect.created_at:
                    is_pending = True
        elif latest_start_inspect:
            # 只有开始检测记录，检查是否在送检之后
            if latest_send_inspect.created_at > latest_start_inspect.created_at:
                is_pending = True

        if is_pending:
            # 从记录数据中获取加工信息
            process_info = {}
            if latest_send_inspect.data:
                try:
                    process_info = json.loads(latest_send_inspect.data) if isinstance(latest_send_inspect.data, str) else latest_send_inspect.data
                except:
                    process_info = {}

            result.append({
                "id": product.id,
                "trace_code": product.trace_code,
                "name": product.name,
                "quantity": product.quantity,
                "unit": product.unit,
                "status": product.status if product.status == ProductStatus.PENDING_CHAIN else "pending",
                "process_type": process_info.get("process_type", ""),
                "inspect_type": process_info.get("inspection_type", "quality")
            })

    return result


@router.get("/products/testing")
async def list_testing_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取检测中的产品列表
    - 已开始检测但未完成
    - 支持重新送检的产品（最近的开始检测在最近的送检之后，且没有更新的完成检测记录）
    """
    check_inspector_role(current_user)

    # 查询有开始检测记录但没有完成检测记录的产品（不限制holder）
    products = db.query(Product).filter(
        Product.current_stage == ProductStage.INSPECTOR
    ).all()

    result = []
    for product in products:
        # 获取最近的送检记录
        latest_send_inspect = db.query(ProductRecord).filter(
            ProductRecord.product_id == product.id,
            ProductRecord.action == RecordAction.SEND_INSPECT
        ).order_by(ProductRecord.created_at.desc()).first()

        if not latest_send_inspect:
            continue

        # 获取最近的开始检测记录
        latest_start_inspect = db.query(ProductRecord).filter(
            ProductRecord.product_id == product.id,
            ProductRecord.action == RecordAction.START_INSPECT
        ).order_by(ProductRecord.created_at.desc()).first()

        # 获取最近的完成检测记录
        latest_inspect = db.query(ProductRecord).filter(
            ProductRecord.product_id == product.id,
            ProductRecord.action == RecordAction.INSPECT
        ).order_by(ProductRecord.created_at.desc()).first()

        # 判断是否检测中：
        # 1. 有开始检测记录，且在最近的送检之后
        # 2. 没有完成检测记录，或完成检测记录在开始检测之前
        is_testing = False

        if latest_start_inspect and latest_start_inspect.created_at >= latest_send_inspect.created_at:
            # 开始检测在送检之后
            if not latest_inspect or latest_inspect.created_at < latest_start_inspect.created_at:
                # 没有完成检测，或者完成检测在开始检测之前
                is_testing = True

        if is_testing:
            result.append({
                "id": product.id,
                "trace_code": product.trace_code,
                "name": product.name,
                "quantity": product.quantity,
                "unit": product.unit,
                "status": product.status if product.status == ProductStatus.PENDING_CHAIN else "testing",
                "start_time": latest_start_inspect.created_at.isoformat() if latest_start_inspect.created_at else None
            })

    return result


@router.get("/products/completed")
async def list_completed_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取已检测完成的产品列表
    - 有完成的检测记录
    """
    check_inspector_role(current_user)

    # 查询由我检测的产品
    inspect_records = db.query(ProductRecord).filter(
        ProductRecord.operator_id == current_user.id,
        ProductRecord.action == RecordAction.INSPECT
    ).all()

    result = []
    for record in inspect_records:
        product = db.query(Product).filter(Product.id == record.product_id).first()
        if product:
            # 从记录数据中获取检测结果
            inspect_info = {}
            if record.data:
                try:
                    inspect_info = json.loads(record.data) if isinstance(record.data, str) else record.data
                except:
                    inspect_info = {}

            result.append({
                "id": product.id,
                "trace_code": product.trace_code,
                "name": product.name,
                "quantity": product.quantity,
                "unit": product.unit,
                "status": "completed",
                "qualified": inspect_info.get("qualified", True),
                "quality_grade": inspect_info.get("quality_grade", "A"),
                "inspect_time": record.created_at.isoformat() if record.created_at else None
            })

    return result


@router.post("/products/{product_id}/start-inspect")
async def start_inspect(
    product_id: int,
    inspect_data: StartInspectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    开始检测
    1. 验证产品在质检员阶段
    2. 创建开始检测记录
    """
    check_inspector_role(current_user)

    # 1. 获取产品
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    # 2. 验证产品状态
    if product.current_stage != ProductStage.INSPECTOR:
        raise HTTPException(status_code=400, detail="产品不在质检阶段")

    # 3. 检查是否已经检测（需要考虑重新送检的情况）
    # 获取最新的送检记录
    latest_send_inspect = db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.action == RecordAction.SEND_INSPECT
    ).order_by(ProductRecord.created_at.desc()).first()

    # 获取最新的检测记录
    latest_inspect = db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.action == RecordAction.INSPECT
    ).order_by(ProductRecord.created_at.desc()).first()

    # 如果有检测记录，且在最新送检之后，说明已完成本轮检测
    if latest_inspect and latest_send_inspect:
        if latest_inspect.created_at > latest_send_inspect.created_at:
            raise HTTPException(status_code=400, detail="该产品已完成检测")

    # 4. 创建开始检测记录（不上链）
    record = ProductRecord(
        product_id=product.id,
        stage=ProductStage.INSPECTOR,
        action=RecordAction.START_INSPECT,
        data=json.dumps({
            "inspection_type": inspect_data.inspect_type,
            "notes": inspect_data.notes
        }, ensure_ascii=False),
        remark=f"开始检测: {inspect_data.inspect_type}",
        operator_id=current_user.id,
        operator_name=current_user.real_name or current_user.username
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "开始检测成功",
        "product_id": product.id,
        "record_id": record.id
    }


def background_inspect_product(product_id: int, user_id: int, operator_name: str, chain_data_str: str, inspect_data_dict: dict):
    """后台处理质检完成"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product: return

        # 1. 质检记录上链
        success, tx_hash, block_number = blockchain_client.add_record(
            trace_code=product.trace_code, stage=2, action=4, 
            data=chain_data_str, remark=f"质检: {'合格' if inspect_data_dict['qualified'] else '不合格'}",
            operator_name=operator_name
        )
        if not success: return

        final_tx, final_bn = tx_hash, block_number

        # 2. 根据结果处理转移或作废
        if inspect_data_dict['qualified']:
            seller = db.query(User).filter(User.role == UserRole.SELLER).first()
            if seller:
                t_success, t_tx, t_bn = blockchain_client.transfer_product(
                    trace_code=product.trace_code, new_holder=seller.blockchain_address or seller.username,
                    new_stage="seller", data=json.dumps({"action":"inspect_pass"}),
                    remark="质检合格转移", operator_name=operator_name
                )
                if t_success:
                    product.current_stage = ProductStage.SELLER
                    product.current_holder_id = seller.id
                    final_tx, final_bn = t_tx, t_bn
        elif inspect_data_dict['unqualified_action'] == "invalidate":
            product.status = ProductStatus.INVALIDATED
            product.invalidated_at = datetime.now()
            product.invalidated_by = user_id
            product.invalidated_reason = inspect_data_dict['reject_reason']
        else:
            # 退回逻辑 (简化处理，默认退回原阶段)
            target_stage = ProductStage.PROCESSOR if inspect_data_dict['reject_to_stage'] == "processor" else ProductStage.PRODUCER
            # ... 查找持有者并转移 ... (此处省略详细查找逻辑，保持核心流程)
            product.current_stage = target_stage

        product.tx_hash, product.block_number = final_tx, final_bn
        product.status = ProductStatus.ON_CHAIN
        product.updated_at = datetime.now()
        db.add(ProductRecord(
            product_id=product.id, stage=ProductStage.INSPECTOR, action=RecordAction.INSPECT,
            data=chain_data_str, remark="质检完成", operator_id=user_id, operator_name=operator_name,
            tx_hash=final_tx, block_number=final_bn
        ))
        db.commit()
    except Exception as e:
        print(f"❌ Background inspect error: {e}")
        db.rollback()
    finally:
        db.close()

@router.post("/products/{product_id}/inspect")
async def inspect_product(
    product_id: int,
    inspect_data: InspectRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """完成检测 (异步)"""
    check_inspector_role(current_user)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product: raise HTTPException(status_code=404, detail="产品不存在")
    
    chain_data_str = json.dumps({
        "trace_code": product.trace_code, "qualified": inspect_data.qualified,
        "quality_grade": inspect_data.quality_grade, "inspect_result": inspect_data.inspect_result
    }, ensure_ascii=False)

    background_tasks.add_task(
        background_inspect_product,
        product.id, current_user.id, current_user.real_name or current_user.username,
        chain_data_str, inspect_data.model_dump()
    )
    product.status = ProductStatus.PENDING_CHAIN
    db.commit()
    return {"message": "质检结果已提交，后台处理中"}


@router.get("/products/{product_id}/records")
async def get_product_records(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取产品流转记录
    """
    check_inspector_role(current_user)

    # 验证产品存在
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    # 获取所有记录
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
    """
    获取质检员统计数据
    """
    check_inspector_role(current_user)

    # 待检测数量
    pending_count = db.query(Product).filter(
        Product.current_stage == ProductStage.INSPECTOR,
        Product.current_holder_id == current_user.id
    ).count()

    # 已完成检测数量
    completed_count = db.query(ProductRecord).filter(
        ProductRecord.operator_id == current_user.id,
        ProductRecord.action == RecordAction.INSPECT
    ).count()

    # 合格率
    qualified_count = 0
    if completed_count > 0:
        qualified_records = db.query(ProductRecord).filter(
            ProductRecord.operator_id == current_user.id,
            ProductRecord.action == RecordAction.INSPECT
        ).all()

        for record in qualified_records:
            try:
                data = json.loads(record.data) if isinstance(record.data, str) else record.data
                if data.get("qualified"):
                    qualified_count += 1
            except:
                pass

    pass_rate = (qualified_count / completed_count * 100) if completed_count > 0 else 0

    return {
        "pending_count": pending_count,
        "completed_count": completed_count,
        "qualified_count": qualified_count,
        "pass_rate": round(pass_rate, 2)
    }
