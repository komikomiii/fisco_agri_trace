"""
Producer (原料商) API
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.database import get_db
from app.models.user import User, UserRole
from app.models.product import Product, ProductRecord, ProductStatus, ProductStage, RecordAction
from app.api.auth import get_current_user
from app.blockchain import blockchain_client

# 区块链操作线程池（避免阻塞事件循环）
blockchain_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="blockchain_")

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
    distribution_type: Optional[str] = "pool"  # pool=公共池, assigned=指定发送
    assigned_processor_id: Optional[int] = None  # 指定的加工商ID


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    origin: Optional[str] = None
    batch_no: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    harvest_date: Optional[datetime] = None
    distribution_type: Optional[str] = None
    assigned_processor_id: Optional[int] = None


class AmendRequest(BaseModel):
    """修正记录请求"""
    field: str  # 修正的字段
    old_value: Optional[str] = None  # 原值
    new_value: str  # 新值
    reason: str  # 修正原因


class InvalidateRequest(BaseModel):
    """产品作废请求"""
    reason: str  # 作废原因


class ResubmitRequest(BaseModel):
    """重新提交请求"""
    name: Optional[str] = None
    category: Optional[str] = None
    origin: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    remark: Optional[str] = None


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
    distribution_type: Optional[str] = "pool"
    assigned_processor_id: Optional[int] = None
    assigned_processor_name: Optional[str] = None  # 加工商名称
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


@router.get("/processors")
async def get_processors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取加工商列表（用于指定发送）"""
    check_producer_role(current_user)

    processors = db.query(User).filter(User.role == UserRole.PROCESSOR).all()
    return [
        {
            "id": p.id,
            "name": p.real_name or p.username,
            "company": p.company
        }
        for p in processors
    ]


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

    # 获取所有指定的加工商ID
    processor_ids = [p.assigned_processor_id for p in products if p.assigned_processor_id]
    processors_map = {}
    if processor_ids:
        processors = db.query(User).filter(User.id.in_(processor_ids)).all()
        processors_map = {p.id: p.real_name or p.username for p in processors}

    # 为每个产品添加加工商名称
    result = []
    for p in products:
        product_dict = {
            "id": p.id,
            "trace_code": p.trace_code,
            "name": p.name,
            "category": p.category,
            "origin": p.origin,
            "batch_no": p.batch_no,
            "quantity": p.quantity,
            "unit": p.unit,
            "harvest_date": p.harvest_date,
            "status": p.status,
            "current_stage": p.current_stage,
            "distribution_type": p.distribution_type or "pool",
            "assigned_processor_id": p.assigned_processor_id,
            "assigned_processor_name": processors_map.get(p.assigned_processor_id) if p.assigned_processor_id else None,
            "tx_hash": p.tx_hash,
            "block_number": p.block_number,
            "created_at": p.created_at,
            "updated_at": p.updated_at
        }
        result.append(product_dict)

    return result


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
        distribution_type=product_data.distribution_type or "pool",
        assigned_processor_id=product_data.assigned_processor_id if product_data.distribution_type == "assigned" else None,
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


def background_submit_to_chain(product_id: int, creator_id: int, operator_name: str, chain_data_str: str, quantity_int: int):
    """后台异步执行上链任务"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return

        # 调用区块链上链
        # 注意：这里在后台线程运行，不需要 loop.run_in_executor，直接调用同步方法即可
        # 或者继续使用 executor 也可以，但 BackgroundTasks 本身就在不同线程/进程（取决于实现）
        success, tx_hash, block_number = blockchain_client.create_product(
            trace_code=product.trace_code,
            name=product.name or "",
            category=product.category or "",
            origin=product.origin or "",
            quantity=quantity_int,
            unit=product.unit or "",
            data=chain_data_str,
            operator_name=operator_name
        )

        if success:
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
                operator_id=creator_id,
                operator_name=operator_name,
                tx_hash=tx_hash,
                block_number=block_number
            )
            db.add(record)
            db.commit()
        else:
            # 上链失败
            product.status = ProductStatus.CHAIN_FAILED
            db.commit()
            print(f"❌ Background chain submission failed for product {product_id}")
            
    except Exception as e:
        print(f"❌ Background task error: {e}")
        db.rollback()
    finally:
        db.close()


@router.post("/products/{product_id}/submit", response_model=ProductResponse)
async def submit_to_chain(
    product_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """提交上链 (异步版本)"""
    check_producer_role(current_user)

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.creator_id == current_user.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="原料不存在")

    if product.status != ProductStatus.DRAFT:
        raise HTTPException(status_code=400, detail="仅草稿状态可提交上链")

    # 生成溯源码并设置状态为“待上链”
    product.trace_code = generate_trace_code()
    product.status = ProductStatus.PENDING_CHAIN
    db.commit()
    db.refresh(product)

    # 准备上链数据
    operator_name = current_user.real_name or current_user.username
    chain_data_str = json.dumps({
        "name": product.name,
        "category": product.category,
        "origin": product.origin,
        "batch_no": product.batch_no,
        "quantity": product.quantity,
        "unit": product.unit,
        "harvest_date": str(product.harvest_date) if product.harvest_date else None
    }, ensure_ascii=False)
    
    quantity_int = int((product.quantity or 0) * 1000)

    # 添加后台任务
    background_tasks.add_task(
        background_submit_to_chain,
        product.id,
        current_user.id,
        operator_name,
        chain_data_str,
        quantity_int
    )

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


def background_amend_product(product_id: int, user_id: int, operator_name: str, amend_chain_data: str, reason: str, last_record_id: int, db_field: str, new_value: any):
    """后台处理修正记录"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product: return

        success, tx_hash, block_number = blockchain_client.add_amend_record(
            trace_code=product.trace_code, stage=0, data=amend_chain_data,
            remark=reason, operator_name=operator_name,
            previous_record_id=last_record_id, amend_reason=reason
        )

        if success:
            # 更新产品表中的字段值
            if hasattr(product, db_field):
                if db_field == 'quantity':
                    try: setattr(product, db_field, float(new_value) if new_value else None)
                    except: pass
                elif db_field == 'harvest_date':
                    try:
                        from datetime import datetime as dt
                        setattr(product, db_field, dt.fromisoformat(new_value) if new_value else None)
                    except: pass
                else:
                    setattr(product, db_field, new_value if new_value else None)

            record = ProductRecord(
                product_id=product.id, stage=ProductStage.PRODUCER, action=RecordAction.AMEND,
                data=amend_chain_data, remark=reason, operator_id=user_id, operator_name=operator_name,
                previous_record_id=last_record_id if last_record_id > 0 else None,
                amend_reason=reason, tx_hash=tx_hash, block_number=block_number
            )
            product.status = ProductStatus.ON_CHAIN
            db.add(record)
            db.commit()
        else:
            product.status = ProductStatus.CHAIN_FAILED
            db.commit()
    except Exception as e:
        print(f"❌ Background amend error: {e}")
        db.rollback()
    finally:
        db.close()

@router.post("/products/{product_id}/amend", response_model=RecordResponse)
async def amend_product(
    product_id: int,
    amend_data: AmendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """提交修正记录 (异步)"""
    check_producer_role(current_user)
    product = db.query(Product).filter(Product.id == product_id, Product.creator_id == current_user.id).first()
    if not product: raise HTTPException(status_code=404, detail="原料不存在")
    if product.status != ProductStatus.ON_CHAIN: raise HTTPException(status_code=400, detail="仅已上链产品可修正")

    last_record = db.query(ProductRecord).filter(ProductRecord.product_id == product_id).order_by(ProductRecord.id.desc()).first()
    
    field_mapping = {'harvest_date': 'harvest_date', 'harvestDate': 'harvest_date', 'batch_no': 'batch_no', 'batchNo': 'batch_no', 'name': 'name', 'category': 'category', 'origin': 'origin', 'quantity': 'quantity', 'unit': 'unit'}
    db_field = field_mapping.get(amend_data.field, amend_data.field)

    amend_chain_data = json.dumps({"field": amend_data.field, "old_value": amend_data.old_value, "new_value": amend_data.new_value}, ensure_ascii=False)

    background_tasks.add_task(
        background_amend_product,
        product.id, current_user.id, current_user.real_name or current_user.username,
        amend_chain_data, amend_data.reason, last_record.id if last_record else 0,
        db_field, amend_data.new_value
    )
    product.status = ProductStatus.PENDING_CHAIN
    db.commit()
    
    # 立即返回一个临时响应（因为前端期望 RecordResponse）
    # 实际上异步模式下 RecordResponse 可能无法立即提供所有数据
    return ProductRecord(
        product_id=product.id, stage=ProductStage.PRODUCER, action=RecordAction.AMEND,
        data=amend_chain_data, remark=amend_data.reason, operator_id=current_user.id,
        operator_name=current_user.real_name or current_user.username, created_at=datetime.now()
    )

def background_resubmit_product(product_id: int, user_id: int, operator_name: str, resubmit_data_str: str):
    """后台处理重新提交"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product: return

        success, tx_hash, block_number = blockchain_client.add_record(
            trace_code=product.trace_code, stage=0, action=5, # Action.CREATE
            data=resubmit_data_str, remark="重新提交", operator_name=operator_name
        )

        if success:
            product.current_stage = ProductStage.PROCESSOR
            product.current_holder_id = None
            product.status = ProductStatus.ON_CHAIN
            product.tx_hash, product.block_number = tx_hash, block_number
            db.add(ProductRecord(
                product_id=product.id, stage=ProductStage.PRODUCER, action=RecordAction.CREATE,
                data=resubmit_data_str, remark="重新提交", operator_id=user_id, operator_name=operator_name,
                tx_hash=tx_hash, block_number=block_number
            ))
            db.commit()
        else:
            product.status = ProductStatus.CHAIN_FAILED
            db.commit()
    except Exception as e:
        print(f"❌ Background resubmit error: {e}")
        db.rollback()
    finally:
        db.close()

@router.post("/products/{product_id}/resubmit")
async def resubmit_rejected_product(
    product_id: int,
    data: ResubmitRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重新提交 (异步)"""
    check_producer_role(current_user)
    product = db.query(Product).filter(Product.id == product_id, Product.current_holder_id == current_user.id).first()
    if not product: raise HTTPException(status_code=404, detail="产品不存在")

    if data.name: product.name = data.name
    if data.category: product.category = data.category
    if data.origin: product.origin = data.origin
    if data.quantity: product.quantity = data.quantity
    if data.unit: product.unit = data.unit
    db.commit()

    resubmit_data_str = json.dumps({
        "action": "resubmit", "name": product.name, "category": product.category,
        "origin": product.origin, "quantity": product.quantity, "unit": product.unit
    }, ensure_ascii=False)

    background_tasks.add_task(
        background_resubmit_product,
        product.id, current_user.id, current_user.real_name or current_user.username,
        resubmit_data_str
    )
    product.status = ProductStatus.PENDING_CHAIN
    db.commit()
    return {"message": "重新提交请求已发送，后台处理中"}


@router.get("/rejected")
async def get_rejected_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取被退回的产品列表
    - 当前持有者为当前用户
    - 当前阶段为原料商 (PRODUCER)
    - 有退回记录
    """
    check_producer_role(current_user)

    # 查询当前持有且有退回记录的产品
    products = db.query(Product).filter(
        Product.current_holder_id == current_user.id,
        Product.current_stage == ProductStage.PRODUCER
    ).all()

    result = []
    for p in products:
        # 检查是否有退回记录
        reject_record = db.query(ProductRecord).filter(
            ProductRecord.product_id == p.id,
            ProductRecord.action == RecordAction.REJECT
        ).order_by(ProductRecord.created_at.desc()).first()

        if reject_record:
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
                "origin": p.origin,
                "quantity": p.quantity,
                "unit": p.unit,
                "reject_reason": reject_data.get("reason", reject_record.remark or ""),
                "reject_issues": reject_data.get("issues", ""),
                "rejected_at": reject_record.created_at.isoformat() if reject_record.created_at else None,
                "rejected_by": reject_record.operator_name,
                "status": "rejected"
            })

    return result


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
