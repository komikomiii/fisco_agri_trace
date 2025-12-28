"""
Seller (销售商) API
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

router = APIRouter(prefix="/seller", tags=["销售商"])


# Pydantic Models
class StockInRequest(BaseModel):
    """入库请求"""
    product_id: int
    quantity: Optional[float] = None  # 入库数量（可部分入库）
    warehouse: str = "主仓库"  # 仓库位置
    notes: Optional[str] = None


class SellRequest(BaseModel):
    """销售请求"""
    product_id: int
    quantity: float  # 销售数量
    buyer_name: str  # 买家名称
    buyer_phone: Optional[str] = None  # 买家电话
    notes: Optional[str] = None


def check_seller_role(user: User):
    """检查是否为销售商"""
    if user.role != UserRole.SELLER:
        raise HTTPException(status_code=403, detail="只有销售商可以执行此操作")


@router.get("/products/inventory")
async def list_inventory_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取库存产品列表
    - 产品当前阶段为 SELLER
    - 持有者为当前销售商
    """
    check_seller_role(current_user)

    # 查询当前在销售阶段且由当前销售商持有的产品
    products = db.query(Product).filter(
        Product.current_stage == ProductStage.SELLER,
        Product.current_holder_id == current_user.id
    ).all()

    result = []
    for product in products:
        # 获取最近的入库记录
        stock_in_record = db.query(ProductRecord).filter(
            ProductRecord.product_id == product.id,
            ProductRecord.action == RecordAction.STOCK_IN
        ).first()

        # 获取已销售总量
        sell_records = db.query(ProductRecord).filter(
            ProductRecord.product_id == product.id,
            ProductRecord.action == RecordAction.SELL
        ).all()

        sold_quantity = 0
        for record in sell_records:
            try:
                data = json.loads(record.data) if isinstance(record.data, str) else record.data
                sold_quantity += data.get("quantity", 0)
            except:
                pass

        # 计算剩余库存
        available_quantity = (product.quantity or 0) - sold_quantity

        result.append({
            "id": product.id,
            "trace_code": product.trace_code,
            "name": product.name,
            "category": product.category,
            "quantity": product.quantity,
            "unit": product.unit,
            "available_quantity": available_quantity,
            "origin": product.origin,
            "warehouse": stock_in_record.data.get("warehouse", "未入库") if stock_in_record and stock_in_record.data else "未入库",
            "stock_in_time": stock_in_record.created_at.isoformat() if stock_in_record else None
        })

    return result


@router.get("/products/sold")
async def list_sold_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取已售出产品列表
    - 有销售记录
    - 由当前销售商操作
    """
    check_seller_role(current_user)

    # 查询销售记录
    sell_records = db.query(ProductRecord).filter(
        ProductRecord.operator_id == current_user.id,
        ProductRecord.action == RecordAction.SELL
    ).order_by(ProductRecord.created_at.desc()).all()

    result = []
    for record in sell_records:
        product = db.query(Product).filter(Product.id == record.product_id).first()
        if product:
            # 从记录数据中获取销售信息
            sell_info = {}
            if record.data:
                try:
                    sell_info = json.loads(record.data) if isinstance(record.data, str) else record.data
                except:
                    sell_info = {}

            result.append({
                "id": product.id,
                "trace_code": product.trace_code,
                "name": product.name,
                "quantity": sell_info.get("quantity", 0),
                "unit": product.unit,
                "buyer_name": sell_info.get("buyer_name", ""),
                "sell_time": record.created_at.isoformat() if record.created_at else None,
                "tx_hash": record.tx_hash
            })

    return result


@router.post("/products/{product_id}/stock-in")
async def stock_in_product(
    product_id: int,
    stock_data: StockInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    产品入库
    1. 验证产品在销售商阶段
    2. 调用智能合约记录入库操作
    3. 更新产品记录
    """
    check_seller_role(current_user)

    # 1. 获取产品
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    # 2. 验证产品状态
    if product.current_stage != ProductStage.SELLER:
        raise HTTPException(status_code=400, detail="产品不在销售阶段")

    if product.current_holder_id != current_user.id:
        raise HTTPException(status_code=400, detail="该产品未分配给当前销售商")

    # 3. 检查是否已经入库
    existing_stock_in = db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.action == RecordAction.STOCK_IN
    ).first()

    if existing_stock_in:
        raise HTTPException(status_code=400, detail="该产品已入库")

    # 4. 准备链上数据
    chain_data = {
        "trace_code": product.trace_code,
        "action": "stock_in",
        "warehouse": stock_data.warehouse,
        "quantity": stock_data.quantity or product.quantity,
        "notes": stock_data.notes,
        "seller": current_user.real_name or current_user.username,
        "timestamp": datetime.now().isoformat()
    }

    # 5. 调用智能合约
    success, tx_hash, block_number = blockchain_client.add_record(
        trace_code=product.trace_code,
        stage=3,  # ProductStage.SELLER
        action=7,  # RecordAction.STOCK_IN
        data=json.dumps(chain_data, ensure_ascii=False),
        remark=f"入库: {stock_data.warehouse}",
        operator_name=current_user.real_name or current_user.username
    )

    if not success:
        raise HTTPException(status_code=500, detail="区块链上链失败")

    # 6. 创建入库记录
    record = ProductRecord(
        product_id=product.id,
        stage=ProductStage.SELLER,
        action=RecordAction.STOCK_IN,
        data=json.dumps(chain_data, default=str, ensure_ascii=False),
        remark=f"入库: {stock_data.warehouse}",
        operator_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        tx_hash=tx_hash,
        block_number=block_number
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "入库成功",
        "product_id": product.id,
        "trace_code": product.trace_code,
        "tx_hash": tx_hash,
        "block_number": block_number
    }


@router.post("/products/{product_id}/sell")
async def sell_product(
    product_id: int,
    sell_data: SellRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    销售产品
    1. 验证产品在销售商阶段
    2. 检查库存是否充足
    3. 调用智能合约记录销售操作
    4. 转移产品到 SOLD 阶段
    5. 更新产品记录
    """
    check_seller_role(current_user)

    # 1. 获取产品
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    # 2. 验证产品状态
    if product.current_stage != ProductStage.SELLER:
        raise HTTPException(status_code=400, detail="产品不在销售阶段")

    if product.current_holder_id != current_user.id:
        raise HTTPException(status_code=400, detail="该产品未分配给当前销售商")

    # 3. 检查库存
    # 获取已销售总量
    sell_records = db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.action == RecordAction.SELL
    ).all()

    sold_quantity = 0
    for record in sell_records:
        try:
            data = json.loads(record.data) if isinstance(record.data, str) else record.data
            sold_quantity += data.get("quantity", 0)
        except:
            pass

    available_quantity = (product.quantity or 0) - sold_quantity

    if sell_data.quantity > available_quantity:
        raise HTTPException(
            status_code=400,
            detail=f"库存不足。可用: {available_quantity} {product.unit}, 请求: {sell_data.quantity} {product.unit}"
        )

    # 4. 准备链上数据
    chain_data = {
        "trace_code": product.trace_code,
        "action": "sell",
        "quantity": sell_data.quantity,
        "buyer_name": sell_data.buyer_name,
        "buyer_phone": sell_data.buyer_phone,
        "notes": sell_data.notes,
        "seller": current_user.real_name or current_user.username,
        "timestamp": datetime.now().isoformat()
    }

    # 5. 调用智能合约记录销售
    success, tx_hash, block_number = blockchain_client.add_record(
        trace_code=product.trace_code,
        stage=3,  # ProductStage.SELLER
        action=8,  # RecordAction.SELL
        data=json.dumps(chain_data, ensure_ascii=False),
        remark=f"销售 {sell_data.quantity} {product.unit} 给 {sell_data.buyer_name}",
        operator_name=current_user.real_name or current_user.username
    )

    if not success:
        raise HTTPException(status_code=500, detail="区块链上链失败")

    # 6. 如果全部售完，转移产品到 SOLD 阶段
    is_fully_sold = (sell_data.quantity >= available_quantity)

    if is_fully_sold:
        # 转移到已售出阶段
        transfer_data = {
            "from_stage": "seller",
            "to_stage": "sold",
            "reason": "产品已售完",
            "quantity": sell_data.quantity
        }

        transfer_success, transfer_tx_hash, transfer_block = blockchain_client.transfer_product(
            trace_code=product.trace_code,
            new_holder=current_user.blockchain_address or current_user.username,
            new_stage="sold",
            data=json.dumps(transfer_data, ensure_ascii=False),
            remark=f"销售商转移已售产品",
            operator_name=current_user.real_name or current_user.username
        )

        if not transfer_success:
            raise HTTPException(status_code=500, detail="转移产品状态失败")

        # 更新产品状态
        product.current_stage = ProductStage.SOLD
        product.tx_hash = transfer_tx_hash
        product.block_number = transfer_block

        final_tx_hash = transfer_tx_hash
        final_block_number = transfer_block
    else:
        final_tx_hash = tx_hash
        final_block_number = block_number

    product.updated_at = datetime.now()

    # 7. 创建销售记录
    record = ProductRecord(
        product_id=product.id,
        stage=ProductStage.SELLER,
        action=RecordAction.SELL,
        data=json.dumps(chain_data, default=str, ensure_ascii=False),
        remark=f"销售 {sell_data.quantity} {product.unit} 给 {sell_data.buyer_name}",
        operator_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        tx_hash=final_tx_hash,
        block_number=final_block_number
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "销售成功",
        "product_id": product.id,
        "trace_code": product.trace_code,
        "quantity": sell_data.quantity,
        "buyer_name": sell_data.buyer_name,
        "is_fully_sold": is_fully_sold,
        "remaining_quantity": available_quantity - sell_data.quantity,
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
    check_seller_role(current_user)

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
    获取销售商统计数据
    """
    check_seller_role(current_user)

    # 库存产品数量
    inventory_count = db.query(Product).filter(
        Product.current_stage == ProductStage.SELLER,
        Product.current_holder_id == current_user.id
    ).count()

    # 已售出产品数量（销售记录数）
    sold_count = db.query(ProductRecord).filter(
        ProductRecord.operator_id == current_user.id,
        ProductRecord.action == RecordAction.SELL
    ).count()

    # 计算销售额
    total_sales_quantity = 0
    sell_records = db.query(ProductRecord).filter(
        ProductRecord.operator_id == current_user.id,
        ProductRecord.action == RecordAction.SELL
    ).all()

    for record in sell_records:
        try:
            data = json.loads(record.data) if isinstance(record.data, str) else record.data
            total_sales_quantity += data.get("quantity", 0)
        except:
            pass

    return {
        "inventory_count": inventory_count,
        "sold_count": sold_count,
        "total_sales_quantity": round(total_sales_quantity, 2)
    }
