"""
Product and Traceability Models
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ProductStatus(str, enum.Enum):
    DRAFT = "DRAFT"                    # 草稿
    PENDING_CHAIN = "PENDING_CHAIN"    # 待上链
    ON_CHAIN = "ON_CHAIN"              # 已上链
    CHAIN_FAILED = "CHAIN_FAILED"      # 上链失败
    TERMINATED = "TERMINATED"          # 已终止
    INVALIDATED = "INVALIDATED"        # 已作废


class ProductStage(str, enum.Enum):
    PRODUCER = "producer"      # 原料阶段
    PROCESSOR = "processor"    # 加工阶段
    INSPECTOR = "inspector"    # 质检阶段
    SELLER = "seller"          # 销售阶段
    SOLD = "sold"              # 已售出


class RecordAction(str, enum.Enum):
    CREATE = "create"          # 创建
    HARVEST = "harvest"        # 采收
    RECEIVE = "receive"        # 接收
    PROCESS = "process"        # 加工
    SEND_INSPECT = "send_inspect"  # 送检
    START_INSPECT = "start_inspect"  # 开始检测
    INSPECT = "inspect"        # 质检
    REJECT = "reject"          # 退回
    TERMINATE = "terminate"    # 终止
    STOCK_IN = "stock_in"      # 入库
    SELL = "sell"              # 销售
    AMEND = "amend"            # 修正


class Product(Base):
    """产品/原料主表"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    trace_code = Column(String(50), unique=True, index=True)  # 溯源码 (上链后生成)
    name = Column(String(200), nullable=False)  # 产品名称
    category = Column(String(100))  # 品类
    status = Column(Enum(ProductStatus), default=ProductStatus.DRAFT)
    current_stage = Column(Enum(ProductStage), default=ProductStage.PRODUCER)

    # 原料信息
    origin = Column(String(200))  # 产地
    batch_no = Column(String(50))  # 批次号
    quantity = Column(Float)  # 数量
    unit = Column(String(20))  # 单位
    harvest_date = Column(DateTime)  # 采收日期

    # 分配方式
    distribution_type = Column(String(20), default="pool")  # pool=公共池, assigned=指定发送
    assigned_processor_id = Column(Integer, ForeignKey("users.id"))  # 指定的加工商ID

    # 区块链信息
    tx_hash = Column(String(100))  # 创建交易哈希
    block_number = Column(Integer)  # 区块高度

    # 作废信息
    invalidated_at = Column(DateTime)  # 作废时间
    invalidated_by = Column(Integer, ForeignKey("users.id"))  # 作废操作人
    invalidated_reason = Column(Text)  # 作废原因

    # 关联
    creator_id = Column(Integer, ForeignKey("users.id"))
    current_holder_id = Column(Integer, ForeignKey("users.id"))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    records = relationship("ProductRecord", back_populates="product")


class ProductRecord(Base):
    """产品流转记录"""
    __tablename__ = "product_records"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    stage = Column(Enum(ProductStage), nullable=False)
    action = Column(Enum(RecordAction), nullable=False)

    # 操作数据 (JSON格式存储)
    data = Column(Text)  # JSON: 具体操作数据
    remark = Column(Text)  # 备注

    # 操作人
    operator_id = Column(Integer, ForeignKey("users.id"))
    operator_name = Column(String(100))

    # 区块链信息
    tx_hash = Column(String(100))
    block_number = Column(Integer)

    # 修正记录关联
    previous_record_id = Column(Integer, ForeignKey("product_records.id"))
    amend_reason = Column(Text)  # 修正原因

    created_at = Column(DateTime, server_default=func.now())

    # 关系
    product = relationship("Product", back_populates="records")
