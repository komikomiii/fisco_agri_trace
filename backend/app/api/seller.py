"""
Seller (销售商) API
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

        # 解析入库记录数据
        warehouse = "未入库"
        if stock_in_record:
            try:
                if isinstance(stock_in_record.data, str):
                    data = json.loads(stock_in_record.data)
                else:
                    data = stock_in_record.data
                warehouse = data.get("warehouse", "未入库") if data else "未入库"
            except:
                warehouse = "未入库"

        result.append({
            "id": product.id,
            "trace_code": product.trace_code,
            "name": product.name,
            "category": product.category,
            "quantity": product.quantity,
            "unit": product.unit,
            "available_quantity": available_quantity,
            "origin": product.origin,
            "warehouse": warehouse,
            "status": product.status,
            "stock_in_time": stock_in_record.created_at.isoformat() if stock_in_record else None
        })

    return result


@router.get("/products/sold")
async def list_sold_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取上架记录列表
    - 有上架记录（SELL action）
    - 由当前销售商操作
    """
    check_seller_role(current_user)

    # 查询上架记录
    sell_records = db.query(ProductRecord).filter(
        ProductRecord.operator_id == current_user.id,
        ProductRecord.action == RecordAction.SELL
    ).order_by(ProductRecord.created_at.desc()).all()

    result = []
    for record in sell_records:
        product = db.query(Product).filter(Product.id == record.product_id).first()
        if product:
            # 从记录数据中获取上架信息
            listing_info = {}
            if record.data:
                try:
                    listing_info = json.loads(record.data) if isinstance(record.data, str) else record.data
                except:
                    listing_info = {}

            # 直接从新格式获取价格和位置，兼容旧格式
            price = listing_info.get("price") or listing_info.get("buyer_phone", "")
            shelf_location = listing_info.get("shelf_location") or listing_info.get("buyer_name", "")

            # 尝试解析价格为浮点数
            try:
                price = float(price) if price else 0
            except:
                price = 0

            result.append({
                "id": product.id,
                "trace_code": product.trace_code,
                "name": product.name,
                "category": product.category,
                "origin": product.origin,
                "quantity": listing_info.get("quantity", product.quantity),
                "unit": product.unit,
                "shelf_location": shelf_location,  # 上架位置
                "price": price,  # 价格
                "listing_time": record.created_at.isoformat() if record.created_at else None,
                "tx_hash": record.tx_hash,
                "block_number": record.block_number
            })

    return result


def background_stock_in(product_id: int, user_id: int, operator_name: str, chain_data_str: str, warehouse: str):
    """后台处理入库"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product: return

        success, tx_hash, block_number = blockchain_client.add_record(
            trace_code=product.trace_code, stage=3, action=7,
            data=chain_data_str, remark=f"入库: {warehouse}",
            operator_name=operator_name
        )

        if success:
            product.status = ProductStatus.ON_CHAIN
            db.add(ProductRecord(
                product_id=product.id, stage=ProductStage.SELLER, action=RecordAction.STOCK_IN,
                data=chain_data_str, remark=f"入库: {warehouse}",
                operator_id=user_id, operator_name=operator_name,
                tx_hash=tx_hash, block_number=block_number
            ))
            db.commit()
    except Exception as e:
        print(f"❌ Background stock-in error: {e}")
        db.rollback()
    finally:
        db.close()

def background_sell_product(product_id: int, user_id: int, operator_name: str, chain_data_str: str, remark: str):
    """后台处理销售/上架"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product: return

        success, tx_hash, block_number = blockchain_client.add_record(
            trace_code=product.trace_code, stage=3, action=8,
            data=chain_data_str, remark=remark,
            operator_name=operator_name
        )

        if success:
            product.status = ProductStatus.ON_CHAIN
            db.add(ProductRecord(
                product_id=product.id, stage=ProductStage.SELLER, action=RecordAction.SELL,
                data=chain_data_str, remark=remark,
                operator_id=user_id, operator_name=operator_name,
                tx_hash=tx_hash, block_number=block_number
            ))
            db.commit()
    except Exception as e:
        print(f"❌ Background sell error: {e}")
        db.rollback()
    finally:
        db.close()

@router.post("/products/{product_id}/stock-in")
async def stock_in_product(
    product_id: int,
    stock_data: StockInRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """入库 (异步)"""
    check_seller_role(current_user)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or product.current_stage != ProductStage.SELLER or product.current_holder_id != current_user.id:
        raise HTTPException(status_code=400, detail="产品不存在或无权操作")

    chain_data_str = json.dumps({
        "trace_code": product.trace_code, "action": "stock_in",
        "warehouse": stock_data.warehouse, "quantity": stock_data.quantity or product.quantity,
        "seller": current_user.real_name or current_user.username,
        "timestamp": datetime.now().isoformat()
    }, ensure_ascii=False)

    background_tasks.add_task(
        background_stock_in,
        product.id, current_user.id, current_user.real_name or current_user.username,
        chain_data_str, stock_data.warehouse
    )
    product.status = ProductStatus.PENDING_CHAIN
    db.commit()
    return {"message": "入库请求已提交"}

@router.post("/products/{product_id}/sell")
async def sell_product(
    product_id: int,
    sell_data: SellRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """销售/上架 (异步)"""
    check_seller_role(current_user)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or product.current_stage != ProductStage.SELLER or product.current_holder_id != current_user.id:
        raise HTTPException(status_code=400, detail="产品不存在或无权操作")

    chain_data_str = json.dumps({
        "trace_code": product.trace_code, "action": "shelf_listing",
        "quantity": sell_data.quantity, "price": sell_data.buyer_phone,
        "shelf_location": sell_data.buyer_name, "seller": current_user.real_name or current_user.username,
        "timestamp": datetime.now().isoformat()
    }, ensure_ascii=False)

    background_tasks.add_task(
        background_sell_product,
        product.id, current_user.id, current_user.real_name or current_user.username,
        chain_data_str, f"上架: {sell_data.buyer_name}, 价格: {sell_data.buyer_phone}"
    )
    product.status = ProductStatus.PENDING_CHAIN
    db.commit()
    return {"message": "上架请求已提交"}


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
