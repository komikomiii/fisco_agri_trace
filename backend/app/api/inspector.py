"""
Inspector (质检员) API
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
                "status": "pending",
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
                "status": "testing",
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


@router.post("/products/{product_id}/inspect")
async def inspect_product(
    product_id: int,
    inspect_data: InspectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    完成检测
    1. 验证产品在质检员阶段
    2. 调用智能合约记录检测结果
    3. 更新产品状态
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

    # 4. 准备链上数据
    chain_data = {
        "trace_code": product.trace_code,
        "action": "inspect",
        "qualified": inspect_data.qualified,
        "quality_grade": inspect_data.quality_grade,
        "inspect_result": inspect_data.inspect_result,
        "inspector": current_user.real_name or current_user.username,
        "issues": inspect_data.issues,
        "timestamp": datetime.now().isoformat()
    }

    # 5. 调用智能合约
    success, tx_hash, block_number = blockchain_client.add_record(
        trace_code=product.trace_code,
        stage=2,  # ProductStage.INSPECTOR
        action=4,  # RecordAction.INSPECT
        data=json.dumps(chain_data, ensure_ascii=False),
        remark=f"质检: {'合格' if inspect_data.qualified else '不合格'} - {inspect_data.quality_grade}级",
        operator_name=current_user.real_name or current_user.username
    )

    if not success:
        raise HTTPException(status_code=500, detail="区块链上链失败")

    # 6. 根据检测结果处理产品
    action_result = None  # 记录处理结果类型
    reject_to_stage_result = None  # 记录退回阶段

    if inspect_data.qualified:
        # ========== 合格：转移到销售商 ==========
        seller = db.query(User).filter(User.role == UserRole.SELLER).first()
        if not seller:
            raise HTTPException(status_code=500, detail="系统中没有销售商，无法转移产品")

        transfer_data = {
            "from_stage": "inspector",
            "to_stage": "seller",
            "reason": "质检合格，进入销售环节",
            "inspect_result": inspect_data.inspect_result
        }

        transfer_success, transfer_tx_hash, transfer_block = blockchain_client.transfer_product(
            trace_code=product.trace_code,
            new_holder=seller.blockchain_address or seller.username,
            new_stage="seller",
            data=json.dumps(transfer_data, ensure_ascii=False),
            remark="质检员转移产品",
            operator_name=current_user.real_name or current_user.username
        )

        if not transfer_success:
            raise HTTPException(status_code=500, detail="转移产品到销售阶段失败")

        product.current_stage = ProductStage.SELLER
        product.current_holder_id = seller.id
        product.tx_hash = transfer_tx_hash
        product.block_number = transfer_block
        final_tx_hash = transfer_tx_hash
        final_block_number = transfer_block

    elif inspect_data.unqualified_action == "invalidate":
        # ========== 不合格 - 作废产品 ==========
        action_result = "invalidate"

        # 更新链上数据，添加作废信息
        chain_data["unqualified_action"] = "invalidate"
        chain_data["invalidate_reason"] = inspect_data.reject_reason

        # 记录作废操作到链上
        invalidate_success, invalidate_tx_hash, invalidate_block = blockchain_client.add_record(
            trace_code=product.trace_code,
            stage=2,  # INSPECTOR
            action=6,  # TERMINATE (用于作废)
            data=json.dumps({
                "action": "invalidate",
                "reason": inspect_data.reject_reason,
                "inspector": current_user.real_name or current_user.username,
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False),
            remark=f"产品作废: {inspect_data.reject_reason}",
            operator_name=current_user.real_name or current_user.username
        )

        if not invalidate_success:
            raise HTTPException(status_code=500, detail="作废记录上链失败")

        # 更新产品状态为已作废
        product.status = ProductStatus.INVALIDATED
        product.invalidated_at = datetime.now()
        product.invalidated_by = current_user.id
        product.invalidated_reason = inspect_data.reject_reason
        product.tx_hash = invalidate_tx_hash
        product.block_number = invalidate_block
        final_tx_hash = invalidate_tx_hash
        final_block_number = invalidate_block

    else:
        # ========== 不合格 - 退回 ==========
        action_result = "reject"
        reject_to_stage_result = inspect_data.reject_to_stage

        # 确定退回的阶段和持有者
        if inspect_data.reject_to_stage == "producer":
            # 退回原料商
            target_stage = ProductStage.PRODUCER
            # 查找原创建者
            target_holder = db.query(User).filter(User.id == product.creator_id).first()
            stage_label = "原料商"
        else:
            # 退回加工商
            target_stage = ProductStage.PROCESSOR
            # 查找最近的加工记录获取加工商
            process_record = db.query(ProductRecord).filter(
                ProductRecord.product_id == product.id,
                ProductRecord.action == RecordAction.PROCESS
            ).order_by(ProductRecord.created_at.desc()).first()

            if process_record and process_record.operator_id:
                target_holder = db.query(User).filter(User.id == process_record.operator_id).first()
            else:
                # 找不到加工商，默认找一个加工商
                target_holder = db.query(User).filter(User.role == UserRole.PROCESSOR).first()
            stage_label = "加工商"

        if not target_holder:
            raise HTTPException(status_code=500, detail=f"找不到{stage_label}，无法退回")

        # 记录退回操作到链上
        reject_data = {
            "action": "reject",
            "from_stage": "inspector",
            "to_stage": inspect_data.reject_to_stage,
            "reason": inspect_data.reject_reason,
            "issues": inspect_data.issues,
            "inspector": current_user.real_name or current_user.username,
            "timestamp": datetime.now().isoformat()
        }

        reject_success, reject_tx_hash, reject_block = blockchain_client.add_record(
            trace_code=product.trace_code,
            stage=2,  # INSPECTOR
            action=5,  # REJECT
            data=json.dumps(reject_data, ensure_ascii=False),
            remark=f"退回{stage_label}: {inspect_data.reject_reason}",
            operator_name=current_user.real_name or current_user.username
        )

        if not reject_success:
            raise HTTPException(status_code=500, detail="退回记录上链失败")

        # 更新产品状态
        product.current_stage = target_stage
        product.current_holder_id = target_holder.id
        product.tx_hash = reject_tx_hash
        product.block_number = reject_block
        final_tx_hash = reject_tx_hash
        final_block_number = reject_block

        # 创建退回记录
        reject_record = ProductRecord(
            product_id=product.id,
            stage=ProductStage.INSPECTOR,
            action=RecordAction.REJECT,
            data=json.dumps(reject_data, ensure_ascii=False),
            remark=f"退回{stage_label}: {inspect_data.reject_reason}",
            operator_id=current_user.id,
            operator_name=current_user.real_name or current_user.username,
            tx_hash=reject_tx_hash,
            block_number=reject_block
        )
        db.add(reject_record)

    product.updated_at = datetime.now()

    # 7. 创建检测记录
    record = ProductRecord(
        product_id=product.id,
        stage=ProductStage.INSPECTOR,
        action=RecordAction.INSPECT,
        data=json.dumps(chain_data, default=str, ensure_ascii=False),
        remark=f"质检: {'合格' if inspect_data.qualified else '不合格'} - {inspect_data.quality_grade}级",
        operator_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        tx_hash=tx_hash,  # 检测记录使用检测时的tx_hash
        block_number=block_number
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "检测完成",
        "product_id": product.id,
        "qualified": inspect_data.qualified,
        "action": action_result,
        "reject_to_stage": reject_to_stage_result,
        "trace_code": product.trace_code,
        "tx_hash": final_tx_hash,
        "block_number": final_block_number
    }


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
