"""
Producer (原料商) API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import uuid

from app.database import get_db
from app.models.user import User, UserRole
from app.models.product import Product, ProductRecord, ProductStatus, ProductStage, RecordAction
from app.api.auth import get_current_user
from app.blockchain import blockchain_client

router = APIRouter(prefix="/producer", tags=["原料商"])


# Pydantic Models
class ProductCreate(BaseModel):
    name: str
    category: Optional[str] = None
    origin: Optional[str] = None
    batch_no: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    harvest_date: Optional[datetime] = None
    remark: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    origin: Optional[str] = None
    batch_no: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    harvest_date: Optional[datetime] = None


class AmendRequest(BaseModel):
    """修正记录请求"""
    field: str  # 修正的字段
    old_value: Optional[str] = None  # 原值
    new_value: str  # 新值
    reason: str  # 修正原因


class InvalidateRequest(BaseModel):
    """产品作废请求"""
    reason: str  # 作废原因


class ProductResponse(BaseModel):
    id: int
    trace_code: Optional[str]
    name: str
    category: Optional[str]
    origin: Optional[str]
    batch_no: Optional[str]
    quantity: Optional[float]
    unit: Optional[str]
    harvest_date: Optional[datetime]
    status: ProductStatus
    current_stage: ProductStage
    tx_hash: Optional[str]
    block_number: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecordResponse(BaseModel):
    id: int
    stage: ProductStage
    action: RecordAction
    data: Optional[str]
    remark: Optional[str]
    operator_name: Optional[str]
    tx_hash: Optional[str]
    block_number: Optional[int]
    amend_reason: Optional[str] = None  # 修正原因
    created_at: datetime

    class Config:
        from_attributes = True


def check_producer_role(user: User):
    """检查是否为原料商角色"""
    if user.role != UserRole.PRODUCER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅原料商可执行此操作"
        )


def generate_trace_code() -> str:
    """生成溯源码"""
    date_str = datetime.now().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:8].upper()
    return f"TRACE-{date_str}-{unique_id}"


@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    status: Optional[ProductStatus] = None,
    include_invalidated: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取原料列表
    - 默认不包含已作废产品
    - 使用 include_invalidated=true 可包含已作废产品
    """
    check_producer_role(current_user)

    query = db.query(Product).filter(Product.creator_id == current_user.id)

    # 默认排除已作废产品
    if not include_invalidated:
        query = query.filter(Product.status != ProductStatus.INVALIDATED)

    if status:
        query = query.filter(Product.status == status)

    products = query.order_by(Product.created_at.desc()).all()
    return products


@router.post("/products", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建原料（草稿）"""
    check_producer_role(current_user)

    product = Product(
        name=product_data.name,
        category=product_data.category,
        origin=product_data.origin,
        batch_no=product_data.batch_no,
        quantity=product_data.quantity,
        unit=product_data.unit,
        harvest_date=product_data.harvest_date,
        status=ProductStatus.DRAFT,
        current_stage=ProductStage.PRODUCER,
        creator_id=current_user.id,
        current_holder_id=current_user.id
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # 创建记录
    record = ProductRecord(
        product_id=product.id,
        stage=ProductStage.PRODUCER,
        action=RecordAction.CREATE,
        data=json.dumps(product_data.model_dump(), default=str, ensure_ascii=False),
        remark=product_data.remark,
        operator_id=current_user.id,
        operator_name=current_user.real_name or current_user.username
    )
    db.add(record)
    db.commit()

    return product


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取原料详情"""
    check_producer_role(current_user)

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.creator_id == current_user.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="原料不存在")

    return product


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新原料（仅草稿状态）"""
    check_producer_role(current_user)

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.creator_id == current_user.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="原料不存在")

    if product.status != ProductStatus.DRAFT:
        raise HTTPException(status_code=400, detail="仅草稿状态可编辑")

    # 更新字段
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.post("/products/{product_id}/submit", response_model=ProductResponse)
async def submit_to_chain(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """提交上链"""
    check_producer_role(current_user)

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.creator_id == current_user.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="原料不存在")

    if product.status != ProductStatus.DRAFT:
        raise HTTPException(status_code=400, detail="仅草稿状态可提交上链")

    # 生成溯源码
    product.trace_code = generate_trace_code()

    # 准备上链数据
    operator_name = current_user.real_name or current_user.username
    chain_data = json.dumps({
        "name": product.name,
        "category": product.category,
        "origin": product.origin,
        "batch_no": product.batch_no,
        "quantity": product.quantity,
        "unit": product.unit,
        "harvest_date": str(product.harvest_date) if product.harvest_date else None
    }, ensure_ascii=False)

    # 调用区块链上链
    quantity_int = int((product.quantity or 0) * 1000)  # 转换为整数，支持3位小数
    success, tx_hash, block_number = blockchain_client.create_product(
        trace_code=product.trace_code,
        name=product.name or "",
        category=product.category or "",
        origin=product.origin or "",
        quantity=quantity_int,
        unit=product.unit or "",
        data=chain_data,
        operator_name=operator_name
    )

    if not success:
        raise HTTPException(status_code=500, detail="区块链上链失败，请稍后重试")

    product.status = ProductStatus.ON_CHAIN
    product.tx_hash = tx_hash
    product.block_number = block_number

    # 创建上链记录
    record = ProductRecord(
        product_id=product.id,
        stage=ProductStage.PRODUCER,
        action=RecordAction.HARVEST,
        data=json.dumps({
            "trace_code": product.trace_code,
            "action": "submit_to_chain"
        }, ensure_ascii=False),
        operator_id=current_user.id,
        operator_name=operator_name,
        tx_hash=tx_hash,
        block_number=block_number
    )
    db.add(record)
    db.commit()
    db.refresh(product)

    return product


@router.get("/products/{product_id}/records", response_model=List[RecordResponse])
async def get_product_records(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取产品流转记录"""
    check_producer_role(current_user)

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.creator_id == current_user.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="原料不存在")

    records = db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id
    ).order_by(ProductRecord.created_at.asc()).all()

    return records


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除原料（仅草稿状态）"""
    check_producer_role(current_user)

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.creator_id == current_user.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="原料不存在")

    if product.status != ProductStatus.DRAFT:
        raise HTTPException(status_code=400, detail="仅草稿状态可删除")

    # 删除关联记录
    db.query(ProductRecord).filter(ProductRecord.product_id == product_id).delete()
    db.delete(product)
    db.commit()

    return {"message": "删除成功"}


@router.post("/products/{product_id}/invalidate")
async def invalidate_product(
    product_id: int,
    invalidate_data: InvalidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    作废产品
    - 草稿状态: 直接删除
    - 已上链状态: 标记为INVALIDATED，保留数据但不再显示在正常列表中
    注意: 链上数据无法删除，作废后溯源码永久失效
    """
    check_producer_role(current_user)

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.creator_id == current_user.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="原料不存在")

    if product.status == ProductStatus.INVALIDATED:
        raise HTTPException(status_code=400, detail="产品已作废")

    # 草稿状态直接删除
    if product.status == ProductStatus.DRAFT:
        db.query(ProductRecord).filter(ProductRecord.product_id == product_id).delete()
        db.delete(product)
        db.commit()
        return {
            "message": "草稿已删除",
            "deleted": True
        }

    # 已上链状态标记为作废
    product.status = ProductStatus.INVALIDATED
    product.invalidated_at = datetime.now()
    product.invalidated_by = current_user.id
    product.invalidated_reason = invalidate_data.reason

    # 添加作废记录
    record = ProductRecord(
        product_id=product.id,
        stage=product.current_stage,
        action=RecordAction.TERMINATE,
        data=json.dumps({
            "action": "invalidate",
            "reason": invalidate_data.reason
        }, ensure_ascii=False),
        remark=f"产品作废: {invalidate_data.reason}",
        operator_id=current_user.id,
        operator_name=current_user.real_name or current_user.username
    )
    db.add(record)
    db.commit()
    db.refresh(product)

    return {
        "message": "产品已作废（链上数据无法删除，溯源码已失效）",
        "deleted": False,
        "invalidated": True,
        "product": {
            "id": product.id,
            "trace_code": product.trace_code,
            "name": product.name,
            "invalidated_at": product.invalidated_at,
            "invalidated_reason": product.invalidated_reason
        }
    }


@router.get("/invalidated")
async def get_invalidated_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取已作废产品列表"""
    check_producer_role(current_user)

    products = db.query(Product).filter(
        Product.creator_id == current_user.id,
        Product.status == ProductStatus.INVALIDATED
    ).order_by(Product.invalidated_at.desc()).all()

    # 手动序列化以避免Pydantic验证问题
    result = []
    for p in products:
        result.append({
            "id": p.id,
            "trace_code": p.trace_code,
            "name": p.name,
            "category": p.category,
            "origin": p.origin,
            "batch_no": p.batch_no,
            "quantity": p.quantity,
            "unit": p.unit,
            "harvest_date": p.harvest_date.isoformat() if p.harvest_date else None,
            "status": p.status.value if p.status else None,
            "current_stage": p.current_stage.value if p.current_stage else None,
            "tx_hash": p.tx_hash,
            "block_number": p.block_number,
            "invalidated_at": p.invalidated_at.isoformat() if p.invalidated_at else None,
            "invalidated_by": p.invalidated_by,
            "invalidated_reason": p.invalidated_reason,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        })

    return result


@router.post("/products/{product_id}/amend", response_model=RecordResponse)
async def amend_product(
    product_id: int,
    amend_data: AmendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """提交修正记录（仅已上链状态可修正）"""
    check_producer_role(current_user)

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.creator_id == current_user.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="原料不存在")

    if product.status != ProductStatus.ON_CHAIN:
        raise HTTPException(status_code=400, detail="仅已上链产品可提交修正")

    # 获取最后一条记录 ID
    last_record = db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id
    ).order_by(ProductRecord.id.desc()).first()

    # 准备修正数据
    operator_name = current_user.real_name or current_user.username
    amend_chain_data = json.dumps({
        "field": amend_data.field,
        "old_value": amend_data.old_value,
        "new_value": amend_data.new_value
    }, ensure_ascii=False)

    # 调用区块链添加修正记录
    # Stage.PRODUCER = 0
    success, tx_hash, block_number = blockchain_client.add_amend_record(
        trace_code=product.trace_code,
        stage=0,  # PRODUCER
        data=amend_chain_data,
        remark=amend_data.reason,
        operator_name=operator_name,
        previous_record_id=last_record.id if last_record else 0,
        amend_reason=amend_data.reason
    )

    if not success:
        raise HTTPException(status_code=500, detail="区块链修正记录提交失败，请稍后重试")

    # 同时更新产品表中的字段值（让前端显示最新数据）
    field_to_update = amend_data.field
    new_value = amend_data.new_value

    # 字段名映射（前端字段名 -> 数据库字段名）
    field_mapping = {
        'harvest_date': 'harvest_date',
        'harvestDate': 'harvest_date',
        'batch_no': 'batch_no',
        'batchNo': 'batch_no',
        'name': 'name',
        'category': 'category',
        'origin': 'origin',
        'quantity': 'quantity',
        'unit': 'unit'
    }

    db_field = field_mapping.get(field_to_update, field_to_update)

    # 根据字段类型转换值
    if hasattr(product, db_field):
        if db_field == 'quantity':
            try:
                setattr(product, db_field, float(new_value) if new_value else None)
            except (ValueError, TypeError):
                setattr(product, db_field, None)
        elif db_field == 'harvest_date':
            try:
                from datetime import datetime as dt
                setattr(product, db_field, dt.fromisoformat(new_value) if new_value else None)
            except (ValueError, TypeError):
                setattr(product, db_field, None)
        else:
            setattr(product, db_field, new_value if new_value else None)

    # 创建修正记录
    record = ProductRecord(
        product_id=product.id,
        stage=ProductStage.PRODUCER,
        action=RecordAction.AMEND,
        data=amend_chain_data,
        remark=amend_data.reason,
        operator_id=current_user.id,
        operator_name=operator_name,
        previous_record_id=last_record.id if last_record else None,
        amend_reason=amend_data.reason,
        tx_hash=tx_hash,
        block_number=block_number
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return record


@router.get("/statistics")
async def get_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取原料商统计数据"""
    check_producer_role(current_user)

    # 统计各状态产品数量
    total = db.query(Product).filter(Product.creator_id == current_user.id).count()
    draft_count = db.query(Product).filter(
        Product.creator_id == current_user.id,
        Product.status == ProductStatus.DRAFT
    ).count()
    on_chain_count = db.query(Product).filter(
        Product.creator_id == current_user.id,
        Product.status == ProductStatus.ON_CHAIN
    ).count()

    return {
        "total": total,
        "draft": draft_count,
        "on_chain": on_chain_count,
        "terminated": total - draft_count - on_chain_count
    }
