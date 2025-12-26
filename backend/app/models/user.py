"""
User Model
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    PRODUCER = "producer"      # 原料商
    PROCESSOR = "processor"    # 加工商
    INSPECTOR = "inspector"    # 质检员
    SELLER = "seller"          # 销售商
    CONSUMER = "consumer"      # 消费者


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    real_name = Column(String(100))
    phone = Column(String(20))
    company = Column(String(200))  # 企业名称
    address = Column(String(500))  # 地址
    blockchain_address = Column(String(100))  # 区块链账户地址
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
