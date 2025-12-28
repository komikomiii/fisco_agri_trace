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
    - 还没有检测记录 (inspect action)
    """
    check_inspector_role(current_user)

    # 查询当前为质检阶段的产品（不限制holder，因为送检后可能已经转移）
    products = db.query(Product).filter(
        Product.current_stage == ProductStage.INSPECTOR
    ).all()

    # 筛选出还没有检测记录的产品
    result = []
    for product in products:
        # 检查是否有检测记录
        has_inspect = db.query(ProductRecord).filter(
            ProductRecord.product_id == product.id,
            ProductRecord.action == RecordAction.INSPECT
        ).first()

        # 也检查是否有开始检测记录
        has_start = db.query(ProductRecord).filter(
            ProductRecord.product_id == product.id,
            ProductRecord.action == RecordAction.START_INSPECT
        ).first()

        if not has_inspect and not has_start:
            # 获取送检记录
            send_inspect_record = db.query(ProductRecord).filter(
                ProductRecord.product_id == product.id,
                ProductRecord.action == RecordAction.SEND_INSPECT
            ).first()

            # 从记录数据中获取加工信息
            process_info = {}
            if send_inspect_record and send_inspect_record.data:
                try:
                    process_info = json.loads(send_inspect_record.data) if isinstance(send_inspect_record.data, str) else send_inspect_record.data
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
    """
    check_inspector_role(current_user)

    # 查询有开始检测记录但没有完成检测记录的产品（不限制holder）
    products = db.query(Product).filter(
        Product.current_stage == ProductStage.INSPECTOR
    ).all()

    result = []
    for product in products:
        # 检查是否有开始检测记录
        start_inspect = db.query(ProductRecord).filter(
            ProductRecord.product_id == product.id,
            ProductRecord.action == RecordAction.START_INSPECT
        ).first()

        # 检查是否已完成检测
        has_complete = db.query(ProductRecord).filter(
            ProductRecord.product_id == product.id,
            ProductRecord.action == RecordAction.INSPECT
        ).first()

        if start_inspect and not has_complete:
            result.append({
                "id": product.id,
                "trace_code": product.trace_code,
                "name": product.name,
                "quantity": product.quantity,
                "unit": product.unit,
                "status": "testing",
                "start_time": start_inspect.created_at.isoformat() if start_inspect.created_at else None
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

    # 3. 检查是否已经检测
    existing_inspect = db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.action == RecordAction.INSPECT
    ).first()

    if existing_inspect:
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

    # 3. 检查是否已经检测
    existing_inspect = db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.action == RecordAction.INSPECT
    ).first()

    if existing_inspect:
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

    # 6. 如果合格，准备转移到销售商；如果不合格，标记问题
    if inspect_data.qualified:
        # 查找销售商
        seller = db.query(User).filter(User.role == UserRole.SELLER).first()
        if not seller:
            raise HTTPException(status_code=500, detail="系统中没有销售商，无法转移产品")

        # 准备转移数据
        transfer_data = {
            "from_stage": "inspector",
            "to_stage": "seller",
            "reason": "质检合格，进入销售环节",
            "inspect_result": inspect_data.inspect_result
        }

        # 转移产品到销售商
        transfer_success, transfer_tx_hash, transfer_block = blockchain_client.transfer_product(
            trace_code=product.trace_code,
            new_holder=seller.blockchain_address or seller.username,
            new_stage="seller",
            data=json.dumps(transfer_data, ensure_ascii=False),
            remark=f"质检员转移产品",
            operator_name=current_user.real_name or current_user.username
        )

        if not transfer_success:
            raise HTTPException(status_code=500, detail="转移产品到销售阶段失败")

        # 更新产品状态
        product.current_stage = ProductStage.SELLER
        product.current_holder_id = seller.id
        product.tx_hash = transfer_tx_hash
        product.block_number = transfer_block

        # 保存转移记录的tx_hash
        final_tx_hash = transfer_tx_hash
        final_block_number = transfer_block
    else:
        # 不合格，保持在质检阶段
        final_tx_hash = tx_hash
        final_block_number = block_number

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
        tx_hash=final_tx_hash,
        block_number=final_block_number
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "检测完成",
        "product_id": product.id,
        "qualified": inspect_data.qualified,
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
